"""Estimativa de chamadas e custo antes da execução (research R7, FR-010).

Entrada: tamanho real dos prompts montados (caracteres/4). Saída: o valor de
configuração (p75 do piloto, com raciocínio) até o lote ter 10 execuções
concluídas; daí em diante, a média observada no próprio lote.
"""

from decimal import Decimal

from django.conf import settings
from django.db.models import Avg, F

from avaliacao import prompt
from conectores.precos import custo_usd, preco_vigente

MINIMO_PARA_MEDIA = 10


def respostas_elegiveis(lote):
    """Respostas que geram chamada ao modelo: sem aviso (nem vazia, nem longa)."""
    return lote.respostas.filter(aviso__isnull=True)


def _media_observada(lote):
    from avaliacao.models import Execucao

    concluidas = Execucao.objects.filter(
        rodada__lote=lote, status=Execucao.Status.CONCLUIDA, resposta__aviso__isnull=True
    )
    if concluidas.count() < MINIMO_PARA_MEDIA:
        return None
    medias = concluidas.aggregate(
        entrada=Avg("tokens_entrada"), saida=Avg(F("tokens_saida") + F("tokens_raciocinio"))
    )
    return medias["entrada"], medias["saida"]


def estimar(lote) -> dict:
    criterios = list(lote.versao_rubrica.criterios.prefetch_related("niveis"))
    respostas = list(respostas_elegiveis(lote).only("texto"))
    n = lote.n_execucoes
    n_chamadas = len(respostas) * len(criterios) * n

    observada = _media_observada(lote)
    if observada:
        tokens_entrada = int(observada[0] * n_chamadas)
        tokens_saida = int(observada[1] * n_chamadas)
    else:
        caracteres = sum(
            len(s) + len(u)
            for r in respostas
            for c in criterios
            for s, u in [prompt.montar(lote.enunciado, c, r.texto)]
        )
        tokens_entrada = (caracteres // 4) * n
        tokens_saida = settings.TOKENS_SAIDA_ESTIMADOS * n_chamadas

    custo = custo_usd(lote.modelo_llm, tokens_entrada, tokens_saida)
    entrada, saida = preco_vigente(lote.modelo_llm)
    return {
        "n_chamadas": n_chamadas,
        "respostas_elegiveis": len(respostas),
        "criterios": len(criterios),
        "n_execucoes": n,
        "tokens_entrada_est": tokens_entrada,
        "tokens_saida_est": tokens_saida,
        "custo_estimado_usd": float(custo.quantize(Decimal("0.0001"))),
        "custo_previsto_chamada_usd": (custo / n_chamadas) if n_chamadas else Decimal(0),
        "teto_usd": float(lote.teto_usd),
        "base_saida": "observada" if observada else "configuracao",
        "preco_vigente": {
            "modelo": lote.modelo_llm,
            "entrada_por_milhao": float(entrada),
            "saida_por_milhao": float(saida),
        },
    }
