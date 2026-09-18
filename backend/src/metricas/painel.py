"""Painel de consistência (FR-021, FR-022; research R10).

Duas camadas:
- `dados_do_lote` lê o banco e monta uma estrutura neutra (listas e dicionários);
- `calcular_painel` é puro e só vê essa estrutura.

O script independente `analysis/reproduzir_metricas.py` monta a mesma estrutura a
partir dos CSVs exportados e reimplementa o cálculo; o painel é reproduzível
quando os dois concordam (SC-006).

Padrões: rodada 1 (a original) como base; estabilidade contra a outra rodada
(2, ou 1 se a base for a 2); concordância com as decisões vigentes do dono do
lote, fora de estudo.
"""

from collections import Counter
from decimal import Decimal

from avaliacao.consolidacao import consolidar
from avaliacao.models import Consolidado, Execucao
from metricas import calculos as c

TIPOS = ("OBJETIVO", "INTERPRETATIVO")


# ---------------------------------------------------------------------------
# cálculo puro


def _bloco(pares: list[dict], categorias: list[int], n_execucoes: int) -> dict:
    estados = [p["estado"] for p in pares]
    ordinais = [p for p in pares if p["modal_ordem"] is not None]
    concordancia = [
        (p["modal_ordem"], p["decidido"]) for p in ordinais if p["decidido"] is not None
    ]
    selecao = [
        (p["estado"], p["modal_ordem"], p["decidido"])
        for p in ordinais
        if p["decidido"] is not None
    ]
    estabilidade = [
        (p["modal_ordem"], p["modal_outra"]) for p in ordinais if p["modal_outra"] is not None
    ]
    completos = [
        [codigo for _, codigo in p["votos"]] for p in pares if len(p["votos"]) == n_execucoes
    ]
    decididos = Counter(p["decidido_codigo"] for p in pares if p["decidido_codigo"])
    return {
        "n_pares": len(pares),
        "estados": dict(sorted(Counter(estados).items())),
        "taxa_divergencia": c.taxa(estados, {"DIVERGENTE"}),
        "taxa_nao_convergente": c.taxa(estados, c.NAO_CONVERGENTES),
        "acordo_medio": c.media([p["acordo"] for p in pares if p["n_validas"] > 0]),
        "fleiss": c.fleiss(c.tabela_fleiss(completos)),
        "concordancia": c.resumo_concordancia(concordancia, categorias),
        "seletiva": c.seletiva(selecao),
        "estabilidade": c.estabilidade(estabilidade, categorias) if estabilidade else None,
        "distribuicao_decidida": dict(sorted(decididos.items())),
    }


def calcular_painel(dados: dict) -> dict:
    """`dados`: criterios, pares, tempos_por_resposta, n_execucoes (ver dados_do_lote)."""
    criterios = dados["criterios"]
    n = dados["n_execucoes"]
    por_criterio = []
    for criterio in criterios:
        categorias = [nv["ordem"] for nv in criterio["niveis"]]
        pares = [p for p in dados["pares"] if p["criterio"] == criterio["ordem"]]
        por_criterio.append(
            {
                "criterio": criterio["ordem"],
                "nome": criterio["nome"],
                "tipo": criterio["tipo"],
                **_bloco(pares, categorias, n),
            }
        )
    todas = sorted({nv["ordem"] for cr in criterios for nv in cr["niveis"]})
    por_tipo = {}
    for tipo in TIPOS:
        ordens = {cr["ordem"] for cr in criterios if cr["tipo"] == tipo}
        pares = [p for p in dados["pares"] if p["criterio"] in ordens]
        estados = [p["estado"] for p in pares]
        concordancia = [
            (p["modal_ordem"], p["decidido"])
            for p in pares
            if p["modal_ordem"] is not None and p["decidido"] is not None
        ]
        por_tipo[tipo] = {
            "n_pares": len(pares),
            "taxa_divergencia": c.taxa(estados, {"DIVERGENTE"}),
            "taxa_nao_convergente": c.taxa(estados, c.NAO_CONVERGENTES),
            "exata": c.concordancia_exata(concordancia),
        }
    tempos = dados["tempos_por_resposta"]
    return {
        "criterios": por_criterio,
        "total": _bloco(dados["pares"], todas, n),
        "por_tipo": por_tipo,
        "tempo": {
            "n_respostas": len(tempos),
            "mediana_ms": c.mediana(tempos),
            "media_ms": c.media(tempos),
        },
    }


# ---------------------------------------------------------------------------
# leitura do banco


def _filtro_fora_de_estudo(modelo) -> dict:
    return {"participacao__isnull": True} if hasattr(modelo, "participacao") else {}


def decisoes_do_dono(lote) -> dict[tuple[int, int], tuple[int, str]]:
    from revisao.models import Decisao

    return {
        (r, cr): (ordem, codigo)
        for r, cr, ordem, codigo in Decisao.objects.filter(
            resposta__lote=lote, docente=lote.dono, vigente=True, **_filtro_fora_de_estudo(Decisao)
        ).values_list("resposta_id", "criterio_id", "nivel__ordem", "nivel__codigo")
    }


def tempos_do_dono(lote) -> list[int]:
    """Tempo ativo por resposta: soma das sessões do dono que têm decisão.

    `Exists` e não `Count`: juntar as decisões antes do `Sum` multiplicaria o
    tempo de cada sessão pelo número de decisões (bug pego pela reprodução
    independente, SC-006).
    """
    from django.db.models import Exists, OuterRef, Sum

    from revisao.models import Decisao, SessaoCorrecao

    por_resposta = (
        SessaoCorrecao.objects.filter(
            resposta__lote=lote, docente=lote.dono, **_filtro_fora_de_estudo(SessaoCorrecao)
        )
        .filter(Exists(Decisao.objects.filter(sessao=OuterRef("pk"))))
        .values("resposta_id")
        .annotate(total=Sum("tempo_ativo_ms"))
    )
    return sorted(int(x["total"]) for x in por_resposta)


def votos_da_rodada(rodada) -> dict[tuple[int, int], list[tuple[int, str]]]:
    votos: dict[tuple[int, int], list[tuple[int, str]]] = {}
    for r, cr, indice, codigo in (
        Execucao.objects.filter(rodada=rodada, status=Execucao.Status.CONCLUIDA, valida=True)
        .order_by("indice")
        .values_list("resposta_id", "criterio_id", "indice", "nivel_codigo")
    ):
        votos.setdefault((r, cr), []).append((indice, codigo))
    return votos


def estados_da_rodada(rodada, limiar=None, votos=None) -> dict[tuple[int, int], dict]:
    """Estado, modal e acordo por par; com `limiar`, recalculados em memória (sem gravar)."""
    lote = rodada.lote
    saida = {}
    for cons in Consolidado.objects.filter(rodada=rodada):
        chave = (cons.resposta_id, cons.criterio_id)
        if limiar is None:
            saida[chave] = {
                "estado": cons.estado,
                "modal_codigo": cons.modal_codigo,
                "acordo": float(cons.acordo),
                "n_validas": cons.n_validas,
            }
        else:
            r = consolidar((votos or {}).get(chave, []), limiar, lote.min_validas)
            saida[chave] = {
                "estado": r.estado,
                "modal_codigo": r.modal or "",
                "acordo": float(r.acordo),
                "n_validas": r.n_validas,
            }
    return saida


def dados_do_lote(lote, rodada, limiar=None) -> dict:
    criterios = list(lote.versao_rubrica.criterios.prefetch_related("niveis").order_by("ordem"))
    ordem_do_nivel = {(cr.id, nv.codigo): nv.ordem for cr in criterios for nv in cr.niveis.all()}
    ordem_do_criterio = {cr.id: cr.ordem for cr in criterios}
    codigos = dict(lote.respostas.values_list("id", "codigo"))
    votos = votos_da_rodada(rodada)
    estados = estados_da_rodada(rodada, limiar, votos)
    outra = lote.rodadas.filter(numero=2 if rodada.numero == 1 else 1).first()
    estados_outra = estados_da_rodada(outra) if outra else {}
    decididos = decisoes_do_dono(lote)
    pares = []
    for (r, cr), e in sorted(
        estados.items(), key=lambda kv: (codigos[kv[0][0]], ordem_do_criterio[kv[0][1]])
    ):
        outra_e = estados_outra.get((r, cr))
        decidido = decididos.get((r, cr))
        pares.append(
            {
                "resposta": codigos[r],
                "criterio": ordem_do_criterio[cr],
                "estado": e["estado"],
                "modal_ordem": ordem_do_nivel.get((cr, e["modal_codigo"])),
                "acordo": e["acordo"],
                "n_validas": e["n_validas"],
                "votos": votos.get((r, cr), []),
                "modal_outra": ordem_do_nivel.get((cr, outra_e["modal_codigo"]))
                if outra_e
                else None,
                "decidido": decidido[0] if decidido else None,
                "decidido_codigo": decidido[1] if decidido else None,
            }
        )
    return {
        "criterios": [
            {
                "ordem": cr.ordem,
                "nome": cr.nome,
                "tipo": cr.tipo,
                "niveis": [{"ordem": nv.ordem, "codigo": nv.codigo} for nv in cr.niveis.all()],
            }
            for cr in criterios
        ],
        "pares": pares,
        "tempos_por_resposta": tempos_do_dono(lote),
        "n_execucoes": lote.n_execucoes,
    }


def painel_do_lote(lote, numero_rodada: int | None = None, limiar=None) -> dict:
    rodadas = list(lote.rodadas.order_by("numero"))
    if not rodadas:
        return {"rodada": None, "rodadas": [], "limiar": float(lote.limiar_acordo), "criterios": []}
    rodada = next((r for r in rodadas if r.numero == numero_rodada), None) or rodadas[0]
    recalculado = limiar is not None and Decimal(str(limiar)) != lote.limiar_acordo
    painel = calcular_painel(dados_do_lote(lote, rodada, limiar if recalculado else None))
    return {
        "rodada": rodada.numero,
        "rodadas": [r.numero for r in rodadas],
        "limiar": float(limiar) if limiar is not None else float(lote.limiar_acordo),
        "recalculado": recalculado,
        "modelo": rodada.modelo,
        "custo": {
            "estimado_usd": float(rodada.custo_estimado_usd),
            "acumulado_usd": float(rodada.custo_acumulado_usd),
        },
        **painel,
    }
