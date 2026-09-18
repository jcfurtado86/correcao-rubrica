"""Métricas do estudo (protocolo A): cegos × assistidos, ancoragem, referência
humana e tempo por condição (research R10, R12)."""

import math
from collections import defaultdict

from django.db.models import Exists, OuterRef, Sum

from avaliacao.models import Consolidado
from metricas import calculos as c
from revisao.models import Decisao, SessaoCorrecao


def _participantes(estudo) -> dict[int, str]:
    return {
        p.id: f"P{i:02d}" for i, p in enumerate(estudo.participacoes.order_by("posicao"), start=1)
    }


def painel_do_estudo(estudo, incluir_emails=True) -> dict:
    lote, rodada = estudo.lote, estudo.rodada
    criterios = list(lote.versao_rubrica.criterios.prefetch_related("niveis").order_by("ordem"))
    ordem_nivel = {(cr.id, n.codigo): n.ordem for cr in criterios for n in cr.niveis.all()}
    categorias = sorted({n.ordem for cr in criterios for n in cr.niveis.all()})
    alocadas = set(estudo.alocacoes.values_list("resposta_id", flat=True))
    consolidados = {
        (x.resposta_id, x.criterio_id): (x.estado, ordem_nivel.get((x.criterio_id, x.modal_codigo)))
        for x in Consolidado.objects.filter(rodada=rodada, resposta_id__in=alocadas)
    }
    decisoes = list(
        Decisao.objects.filter(participacao__estudo=estudo, vigente=True).values_list(
            "participacao_id", "resposta_id", "criterio_id", "nivel__ordem", "sessao__condicao"
        )
    )

    por_condicao: dict[str, list[tuple[str, int, int]]] = {"SEM_APOIO": [], "COM_APOIO": []}
    matrizes: dict[str, dict[int, dict]] = {
        "SEM_APOIO": defaultdict(dict),
        "COM_APOIO": defaultdict(dict),
    }
    for participacao, r, cr, decidido, condicao in decisoes:
        estado, modal = consolidados.get((r, cr), (None, None))
        matrizes[condicao][participacao][(r, cr)] = decidido
        if modal is not None:
            por_condicao[condicao].append((estado, modal, decidido))

    def resumo(itens):
        pares = [(m, d) for _, m, d in itens]
        return {**c.resumo_concordancia(pares, categorias), "seletiva": c.seletiva(itens)}

    cegos, assistidos = resumo(por_condicao["SEM_APOIO"]), resumo(por_condicao["COM_APOIO"])

    def alfa(condicao):
        linhas = matrizes[condicao]
        itens = sorted({i for linha in linhas.values() for i in linha})
        dados = [[linha.get(i, math.nan) for i in itens] for linha in linhas.values()]
        return {
            "alfa": c.krippendorff_ordinal(dados) if dados else None,
            "avaliadores": len(dados),
            "itens": len(itens),
        }

    sessoes = (
        SessaoCorrecao.objects.filter(participacao__estudo=estudo)
        .filter(Exists(Decisao.objects.filter(sessao=OuterRef("pk"))))
        .values("participacao_id", "resposta_id", "condicao")
        .annotate(total=Sum("tempo_ativo_ms"))
    )
    tempos: dict[str, list[int]] = {"SEM_APOIO": [], "COM_APOIO": []}
    por_participante: dict[int, dict[str, list[int]]] = defaultdict(
        lambda: {"SEM_APOIO": [], "COM_APOIO": []}
    )
    for s in sessoes:
        tempos[s["condicao"]].append(int(s["total"]))
        por_participante[s["participacao_id"]][s["condicao"]].append(int(s["total"]))
    diferencas = [
        c.mediana(t["SEM_APOIO"]) - c.mediana(t["COM_APOIO"])
        for t in por_participante.values()
        if t["SEM_APOIO"] and t["COM_APOIO"]
    ]

    nomes = _participantes(estudo)
    from estudos.services import minha_tarefa

    participantes = []
    for p in estudo.participacoes.select_related("docente").order_by("posicao"):
        tarefa = minha_tarefa(p) if estudo.status != "PREPARACAO" else {"progresso": []}
        item = {
            "participante": nomes[p.id],
            "braco": p.braco,
            "ordem": p.ordem,
            "progresso": tarefa.get("progresso", []),
            "concluida": p.concluida_em is not None,
            "mediana_sem_apoio_ms": c.mediana(por_participante[p.id]["SEM_APOIO"]),
            "mediana_com_apoio_ms": c.mediana(por_participante[p.id]["COM_APOIO"]),
        }
        if incluir_emails:
            item["email"] = p.docente.email
        participantes.append(item)

    return {
        "estudo": estudo.id,
        "status": estudo.status,
        "rodada": rodada.numero,
        "cegos": cegos,
        "assistidos": assistidos,
        "ancoragem": {
            "exata": c.ancoragem(assistidos["exata"], cegos["exata"]),
            "exata_convergentes": c.ancoragem(
                assistidos["seletiva"]["exata_convergentes"],
                cegos["seletiva"]["exata_convergentes"],
            ),
        },
        "referencia_humana": {"cegos": alfa("SEM_APOIO"), "assistidos": alfa("COM_APOIO")},
        "tempo": {
            cond: {"n": len(v), "mediana_ms": c.mediana(v), "media_ms": c.media(v)}
            for cond, v in tempos.items()
        }
        | {"diferenca_pareada_mediana_ms": c.mediana(diferencas), "n_pareados": len(diferencas)},
        "participantes": participantes,
    }


def arquivos_do_estudo(estudo, incluir_texto=False, incluir_motivos=False) -> dict[str, str]:
    import csv
    import io
    import json

    from django.core.serializers.json import DjangoJSONEncoder

    from metricas.exportacao import arquivos_do_lote

    metades = dict(estudo.alocacoes.values_list("resposta_id", "metade"))
    nomes = _participantes(estudo)
    arquivos = arquivos_do_lote(
        estudo.lote,
        incluir_texto=incluir_texto,
        incluir_motivos=incluir_motivos,
        metades=metades,
        filtro_estudo={"participacao__estudo": estudo},
        participantes_fixos=nomes,
        incluir_metricas_lote=False,
    )
    saida = io.StringIO()
    escritor = csv.writer(saida, lineterminator="\n")
    escritor.writerow(["participante", "braco", "ordem"])
    for p in estudo.participacoes.order_by("posicao"):
        escritor.writerow([nomes[p.id], p.braco or "", p.ordem])
    arquivos["alocacao.csv"] = saida.getvalue()
    arquivos["metricas_estudo.json"] = json.dumps(
        painel_do_estudo(estudo, incluir_emails=False),
        ensure_ascii=False,
        indent=1,
        cls=DjangoJSONEncoder,
    )
    return arquivos
