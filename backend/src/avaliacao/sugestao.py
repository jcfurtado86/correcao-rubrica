"""Sugestão por critério no formato de contracts/api.md ("Sugestao").

É aqui que o Princípio III vira regra de apresentação: divergente, sem
evidência e indeterminado **nunca** saem com `nivel_sugerido`; e na condição
SEM_APOIO do estudo nada da pré-avaliação sai do servidor (FR-025).
"""

from avaliacao.consolidacao import representativa_por_nivel
from avaliacao.models import Consolidado, Execucao

SEM_APOIO = "SEM_APOIO"
INDISPONIVEL = "INDISPONIVEL"  # par sem consolidado: resposta longa ou rodada em curso
ROTULO_SEM_EVIDENCIA = "Sem evidência"


def _nivel(execucao) -> dict:
    if execucao.nivel is None:
        return {
            "id": None,
            "codigo": execucao.nivel_codigo,
            "rotulo": ROTULO_SEM_EVIDENCIA,
            "ordem": None,
        }
    n = execucao.nivel
    return {"id": n.id, "codigo": n.codigo, "rotulo": n.rotulo, "ordem": n.ordem}


def _trechos(execucao) -> list[dict]:
    return [
        {"inicio": t.inicio, "fim": t.fim, "texto": t.texto_citado}
        for t in execucao.trechos.all()
        if t.localizado
    ]


def _alternativas(consolidado, representativas) -> list[dict]:
    itens = []
    for codigo, votos in consolidado.distribuicao.items():
        execucao = representativas.get(codigo)
        if execucao is None:
            continue
        itens.append(
            {
                "nivel": _nivel(execucao),
                "votos": votos,
                "justificativa": execucao.justificativa,
                "trechos": _trechos(execucao),
            }
        )
    return sorted(itens, key=lambda a: (-a["votos"], a["nivel"]["ordem"] or 99))


def sugestao(criterio, consolidado, execucoes_validas, condicao="COM_APOIO") -> dict:
    if condicao == SEM_APOIO:
        return {"criterio": criterio.id, "estado": "OCULTO"}
    if consolidado is None:
        return {"criterio": criterio.id, "estado": INDISPONIVEL, "nivel_sugerido": None}
    representativas = representativa_por_nivel(execucoes_validas)
    base = {
        "criterio": criterio.id,
        "estado": consolidado.estado,
        "nivel_sugerido": None,
        "acordo": {
            "votos": consolidado.distribuicao.get(consolidado.modal_codigo, 0),
            "validas": consolidado.n_validas,
        },
    }
    if consolidado.estado == Consolidado.Estado.CONVERGENTE:
        execucao = representativas[consolidado.modal_codigo]
        base.update(
            {
                "nivel_sugerido": _nivel(execucao),
                "justificativa": execucao.justificativa,
                "trechos": _trechos(execucao),
            }
        )
    elif consolidado.estado == Consolidado.Estado.SEM_EVIDENCIA:
        execucao = representativas.get(consolidado.modal_codigo)
        base["justificativa"] = execucao.justificativa if execucao else ""
    else:
        base["alternativas"] = _alternativas(consolidado, representativas)
    return base


def sugestoes_da_resposta(resposta, rodada, condicao="COM_APOIO") -> list[dict]:
    criterios = list(resposta.lote.versao_rubrica.criterios.all())
    if condicao == SEM_APOIO or rodada is None:
        return [sugestao(c, None, [], condicao) for c in criterios]
    consolidados = {
        c.criterio_id: c for c in Consolidado.objects.filter(rodada=rodada, resposta=resposta)
    }
    validas: dict[int, list] = {}
    for e in (
        Execucao.objects.filter(
            rodada=rodada, resposta=resposta, status=Execucao.Status.CONCLUIDA, valida=True
        )
        .select_related("nivel")
        .prefetch_related("trechos")
    ):
        validas.setdefault(e.criterio_id, []).append(e)
    return [sugestao(c, consolidados.get(c.id), validas.get(c.id, []), condicao) for c in criterios]
