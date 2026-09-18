"""Exportação dos dados de pesquisa (contracts/exportacao.md, FR-023, SC-006).

Nenhum arquivo contém identificador de estudante ou nome/e-mail de docente:
docentes viram D01…, participantes de estudo P01…, respostas ficam pelo código.
O texto das respostas e os motivos das decisões só saem quando pedidos.
"""

import csv
import io
import json
import zipfile
from datetime import UTC, datetime

from django.core.serializers.json import DjangoJSONEncoder
from django.db.models import Count

from avaliacao.models import Consolidado, Execucao
from metricas.painel import painel_do_lote
from revisao.models import Decisao, SessaoCorrecao
from rubricas.services import conteudo_canonico

VERSAO_SISTEMA = "0.1.0"


def _b(valor) -> str:
    if valor is None:
        return ""
    return "1" if valor else "0"


def _csv(cabecalho: list[str], linhas: list[list]) -> str:
    saida = io.StringIO()
    escritor = csv.writer(saida, lineterminator="\n")
    escritor.writerow(cabecalho)
    escritor.writerows(["" if v is None else v for v in linha] for linha in linhas)
    return saida.getvalue()


class Pseudonimos:
    """D01, D02… (ou P01…) na ordem em que cada pessoa aparece nos registros."""

    def __init__(self, prefixo: str):
        self.prefixo = prefixo
        self.mapa: dict[int, str] = {}

    def __call__(self, pessoa_id) -> str:
        if pessoa_id is None:
            return ""
        if pessoa_id not in self.mapa:
            self.mapa[pessoa_id] = f"{self.prefixo}{len(self.mapa) + 1:02d}"
        return self.mapa[pessoa_id]


def _participacao_id(obj):
    return getattr(obj, "participacao_id", None)


def arquivos_do_lote(
    lote,
    incluir_texto=False,
    incluir_motivos=False,
    metades=None,
    filtro_estudo=None,
    participantes_fixos=None,
    incluir_metricas_lote=True,
):
    """Dicionário {nome do arquivo: conteúdo}. `filtro_estudo` restringe sessões e
    decisões às de um estudo (usado na exportação do estudo)."""
    versao = lote.versao_rubrica
    criterios = list(versao.criterios.prefetch_related("niveis").order_by("ordem"))
    ordem_criterio = {c.id: c.ordem for c in criterios}
    ordem_nivel = {n.id: n.ordem for c in criterios for n in c.niveis.all()}
    ordem_por_codigo = {(c.id, n.codigo): n.ordem for c in criterios for n in c.niveis.all()}
    respostas = list(lote.respostas.order_by("codigo"))
    codigo = {r.id: r.codigo for r in respostas}
    rodadas = list(lote.rodadas.order_by("numero"))
    numero = {r.id: r.numero for r in rodadas}
    metades = metades or {}
    docentes = Pseudonimos("D")
    participantes = Pseudonimos("P")
    if participantes_fixos:
        participantes.mapa.update(participantes_fixos)

    metadados = {
        "lote": {
            "titulo": lote.titulo,
            "enunciado": lote.enunciado,
            "n_execucoes": lote.n_execucoes,
            "limiar_acordo": float(lote.limiar_acordo),
            "min_validas": lote.min_validas,
            "provedor": lote.provedor_llm,
            "modelo": lote.modelo_llm,
            "sintetico": lote.sintetico,
        },
        "rubrica": {
            "titulo": versao.rubrica.titulo,
            "versao": versao.numero,
            "hash": versao.hash,
            "criterios": [
                {**cc, "peso": float(cc["peso"])} for cc in conteudo_canonico(versao)["criterios"]
            ],
        },
        "rodadas": [
            {
                "numero": r.numero,
                "status": r.status,
                "provedor": r.provedor,
                "modelo": r.modelo,
                "versao_prompt": r.versao_prompt,
                "semente_base": r.semente_base,
                "custo_estimado_usd": float(r.custo_estimado_usd),
                "custo_acumulado_usd": float(r.custo_acumulado_usd),
            }
            for r in rodadas
        ],
        "versao_sistema": VERSAO_SISTEMA,
        "exportado_em": datetime.now(UTC).isoformat(),
    }

    cab_respostas = ["codigo", "n_caracteres", "n_substituicoes", "aviso", "metade"]
    if incluir_texto:
        cab_respostas.append("texto")
    linhas_respostas = []
    for r in respostas:
        linha = [r.codigo, len(r.texto), r.n_substituicoes, r.aviso, metades.get(r.id)]
        if incluir_texto:
            linha.append(r.texto)
        linhas_respostas.append(linha)

    execucoes = (
        Execucao.objects.filter(rodada__lote=lote)
        .annotate(n_trechos=Count("trechos"))
        .order_by("rodada__numero", "resposta__codigo", "criterio__ordem", "indice")
    )
    n_localizados = dict(
        Execucao.objects.filter(rodada__lote=lote, trechos__localizado=True)
        .values_list("id")
        .annotate(n=Count("trechos"))
        .values_list("id", "n")
    )
    linhas_execucoes = [
        [
            numero[e.rodada_id],
            codigo[e.resposta_id],
            ordem_criterio[e.criterio_id],
            e.indice,
            e.semente,
            e.status,
            _b(e.valida),
            e.motivo_invalidez,
            e.nivel_codigo,
            ordem_nivel.get(e.nivel_id),
            e.n_trechos,
            n_localizados.get(e.id, 0),
            e.tokens_entrada,
            e.tokens_saida,
            e.tokens_raciocinio,
            float(e.custo_usd),
            e.latencia_ms,
            e.tentativas,
        ]
        for e in execucoes
    ]

    linhas_consolidados = [
        [
            numero[x.rodada_id],
            codigo[x.resposta_id],
            ordem_criterio[x.criterio_id],
            x.estado,
            x.modal_codigo,
            ordem_por_codigo.get((x.criterio_id, x.modal_codigo)),
            float(x.acordo),
            x.n_validas,
            json.dumps(x.distribuicao, sort_keys=True),
            float(x.limiar_usado),
        ]
        for x in Consolidado.objects.filter(rodada__lote=lote).order_by(
            "rodada__numero", "resposta__codigo", "criterio__ordem"
        )
    ]

    sessoes = SessaoCorrecao.objects.filter(resposta__lote=lote).annotate(n=Count("decisoes"))
    decisoes = Decisao.objects.filter(resposta__lote=lote)
    if filtro_estudo is not None:
        sessoes = sessoes.filter(**filtro_estudo)
        decisoes = decisoes.filter(**filtro_estudo)
    # Pseudônimos atribuídos na ordem cronológica das sessões, iguais nos dois arquivos.
    for s in sessoes.order_by("id"):
        docentes(s.docente_id)
        participantes(_participacao_id(s))

    cab_decisoes = [
        "decisao_id",
        "docente",
        "dono_do_lote",
        "participante",
        "codigo",
        "criterio",
        "condicao",
        "estado_exibido",
        "nivel_sugerido_ordem",
        "nivel_decidido_ordem",
        "tipo",
        "tem_motivo",
        "tempo_ativo_ms",
        "vigente",
        "substitui",
        "instante",
    ]
    if incluir_motivos:
        cab_decisoes.append("motivo")
    linhas_decisoes = []
    for d in decisoes.select_related("sessao").order_by("id"):
        linha = [
            d.id,
            docentes(d.docente_id),
            _b(d.docente_id == lote.dono_id),
            participantes(_participacao_id(d)),
            codigo[d.resposta_id],
            ordem_criterio[d.criterio_id],
            d.sessao.condicao,
            d.estado_exibido,
            ordem_nivel.get(d.nivel_sugerido_id),
            ordem_nivel[d.nivel_id],
            d.tipo,
            _b(bool(d.motivo)),
            d.tempo_ativo_ms,
            _b(d.vigente),
            d.substitui_id,
            d.criado_em.isoformat(),
        ]
        if incluir_motivos:
            linha.append(d.motivo)
        linhas_decisoes.append(linha)

    linhas_sessoes = [
        [
            s.id,
            docentes(s.docente_id),
            _b(s.docente_id == lote.dono_id),
            participantes(_participacao_id(s)),
            codigo[s.resposta_id],
            s.condicao,
            numero.get(s.rodada_id),
            s.tempo_ativo_ms,
            s.n,
            s.aberta_em.isoformat(),
        ]
        for s in sessoes.order_by("id")
    ]

    arquivos = {
        "metadados.json": json.dumps(
            metadados, ensure_ascii=False, indent=1, cls=DjangoJSONEncoder
        ),
        "respostas.csv": _csv(cab_respostas, linhas_respostas),
        "execucoes.csv": _csv(
            [
                "rodada",
                "codigo",
                "criterio",
                "indice",
                "semente",
                "status",
                "valida",
                "motivo_invalidez",
                "nivel_codigo",
                "nivel_ordem",
                "n_trechos",
                "n_trechos_localizados",
                "tokens_entrada",
                "tokens_saida",
                "tokens_raciocinio",
                "custo_usd",
                "latencia_ms",
                "tentativas",
            ],
            linhas_execucoes,
        ),
        "consolidados.csv": _csv(
            [
                "rodada",
                "codigo",
                "criterio",
                "estado",
                "modal_codigo",
                "nivel_modal_ordem",
                "acordo",
                "n_validas",
                "distribuicao_json",
                "limiar_usado",
            ],
            linhas_consolidados,
        ),
        "decisoes.csv": _csv(cab_decisoes, linhas_decisoes),
        "sessoes.csv": _csv(
            [
                "sessao_id",
                "docente",
                "dono_do_lote",
                "participante",
                "codigo",
                "condicao",
                "rodada",
                "tempo_ativo_ms",
                "n_decisoes",
                "aberta_em",
            ],
            linhas_sessoes,
        ),
    }
    if incluir_metricas_lote:
        metricas = {
            "limiar": float(lote.limiar_acordo),
            "por_rodada": {str(r.numero): painel_do_lote(lote, r.numero) for r in rodadas},
        }
        arquivos["metricas.json"] = json.dumps(
            metricas, ensure_ascii=False, indent=1, cls=DjangoJSONEncoder
        )
    return arquivos


def zipar(arquivos: dict[str, str]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as z:
        for nome, conteudo in arquivos.items():
            z.writestr(nome, conteudo)
    return buffer.getvalue()
