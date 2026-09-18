"""Fila de correção (FR-016): não convergentes primeiro.

A resposta herda o pior estado entre seus critérios. INDISPONIVEL (sem
pré-avaliação, como a resposta longa) conta como não convergente: exige
atenção integral da docente.
"""

from collections import Counter

from avaliacao.models import Consolidado
from avaliacao.services import rodada_de_referencia
from avaliacao.sugestao import INDISPONIVEL

PRIORIDADE = {
    "INDETERMINADO": 0,
    "DIVERGENTE": 1,
    "SEM_EVIDENCIA": 2,
    INDISPONIVEL: 3,
    "CONVERGENTE": 4,
}


def decisoes_por_resposta(lote, docente, participacao=None) -> dict[int, int]:
    """Número de critérios com decisão vigente por resposta."""
    from django.db.models import Count

    from revisao.models import Decisao

    filtro = {"resposta__lote": lote, "docente": docente, "vigente": True}
    if hasattr(Decisao, "participacao"):
        filtro["participacao"] = participacao
    return dict(
        Decisao.objects.filter(**filtro)
        .values_list("resposta_id")
        .annotate(n=Count("id"))
        .values_list("resposta_id", "n")
    )


def montar_fila(lote, docente, participacao=None, respostas=None) -> dict:
    rodada = rodada_de_referencia(lote)
    criterios = list(lote.versao_rubrica.criterios.values_list("id", flat=True))
    estados: dict[tuple[int, int], str] = {}
    if rodada is not None:
        estados = {
            (r, c): e
            for r, c, e in Consolidado.objects.filter(rodada=rodada).values_list(
                "resposta_id", "criterio_id", "estado"
            )
        }
    decididos = decisoes_por_resposta(lote, docente, participacao)
    respostas = respostas if respostas is not None else lote.respostas.all()
    contagem: Counter = Counter()
    itens = []
    for resposta in respostas.order_by("codigo"):
        dos_criterios = [estados.get((resposta.id, c), INDISPONIVEL) for c in criterios]
        contagem.update(dos_criterios)
        pior = min(dos_criterios, key=lambda e: PRIORIDADE[e]) if dos_criterios else INDISPONIVEL
        n_decididos = decididos.get(resposta.id, 0)
        itens.append(
            {
                "resposta": resposta.id,
                "codigo": resposta.codigo,
                "estado_pior": pior,
                "estados": dict(Counter(dos_criterios)),
                "n_decididos": n_decididos,
                "n_criterios": len(criterios),
                "finalizada": bool(criterios) and n_decididos == len(criterios),
            }
        )
    itens.sort(key=lambda i: (i["estado_pior"] == "CONVERGENTE", i["codigo"]))
    return {
        "rodada": rodada.numero if rodada else None,
        "contagem": dict(contagem),
        "respostas": itens,
    }
