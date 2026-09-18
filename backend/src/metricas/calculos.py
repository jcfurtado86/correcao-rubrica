"""Métricas do TCC como funções puras (research R10).

Recebem listas e dicionários simples, sem ORM, para que o painel e o script
independente de reprodução (analysis/) apliquem as mesmas definições. Valores
indefinidos (amostra pequena, variância zero) saem como None, nunca como NaN.

Convenções:
- Níveis entram pela **posição ordinal** (1..k). Pares cujo modal é
  SEM_EVIDENCIA ou inexistente ficam fora das concordâncias ordinais.
- Pares (ia, docente) = (ordem do nível modal da rodada, ordem do nível decidido).
"""

import math
import statistics
import warnings

NAO_CONVERGENTES = {"DIVERGENTE", "SEM_EVIDENCIA", "INDETERMINADO"}


def _razao(numerador: int, denominador: int) -> float | None:
    return numerador / denominador if denominador else None


def _numero(valor) -> float | None:
    if valor is None:
        return None
    valor = float(valor)
    return None if math.isnan(valor) or math.isinf(valor) else valor


def concordancia_exata(pares: list[tuple[int, int]]) -> float | None:
    return _razao(sum(1 for a, b in pares if a == b), len(pares))


def concordancia_adjacente(pares: list[tuple[int, int]]) -> float | None:
    return _razao(sum(1 for a, b in pares if abs(a - b) <= 1), len(pares))


def kappa_ponderado(pares: list[tuple[int, int]], categorias: list[int]) -> float | None:
    """κ de Cohen com peso quadrático (QWK), como no sklearn."""
    if len(pares) < 2:
        return None
    from sklearn.metrics import cohen_kappa_score

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        valor = cohen_kappa_score(
            [a for a, _ in pares], [b for _, b in pares], weights="quadratic", labels=categorias
        )
    return _numero(valor)


def resumo_concordancia(pares: list[tuple[int, int]], categorias: list[int]) -> dict:
    return {
        "n": len(pares),
        "exata": concordancia_exata(pares),
        "adjacente": concordancia_adjacente(pares),
        "qwk": kappa_ponderado(pares, categorias),
    }


def seletiva(itens: list[tuple[str, int, int]]) -> dict:
    """Concordância exata separada por estado (hipótese SC-008a) e cobertura.

    `itens`: (estado, ordem do modal, ordem decidida).
    """
    convergentes = [(a, b) for e, a, b in itens if e == "CONVERGENTE"]
    outros = [(a, b) for e, a, b in itens if e != "CONVERGENTE"]
    return {
        "cobertura": _razao(len(convergentes), len(itens)),
        "n_convergentes": len(convergentes),
        "n_nao_convergentes": len(outros),
        "exata_convergentes": concordancia_exata(convergentes),
        "exata_nao_convergentes": concordancia_exata(outros),
    }


def taxa(estados: list[str], alvo: set[str]) -> float | None:
    return _razao(sum(1 for e in estados if e in alvo), len(estados))


def media(valores: list[float]) -> float | None:
    return statistics.fmean(valores) if valores else None


def mediana(valores: list[float]) -> float | None:
    return statistics.median(valores) if valores else None


def tabela_fleiss(votos_por_item: list[list[str]]) -> list[list[int]]:
    """Itens × categorias (ordem alfabética dos códigos), com a contagem de votos."""
    categorias = sorted({v for votos in votos_por_item for v in votos})
    return [[votos.count(cat) for cat in categorias] for votos in votos_por_item]


def fleiss(tabela: list[list[int]]) -> float | None:
    """κ de Fleiss entre as N execuções (itens com o mesmo número de votos)."""
    if len(tabela) < 2 or not tabela[0] or len(tabela[0]) < 2:
        return None
    import numpy as np
    from statsmodels.stats.inter_rater import fleiss_kappa

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return _numero(fleiss_kappa(np.array(tabela)))


def krippendorff_ordinal(dados: list[list[float]]) -> float | None:
    """α de Krippendorff ordinal. `dados`: avaliadores × itens, NaN para ausente."""
    import numpy as np

    matriz = np.array(dados, dtype=float)
    valores = matriz[~np.isnan(matriz)]
    if matriz.ndim != 2 or matriz.shape[0] < 2 or len(np.unique(valores)) < 2:
        return None
    import krippendorff

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return _numero(krippendorff.alpha(reliability_data=matriz, level_of_measurement="ordinal"))


def estabilidade(pares: list[tuple[int, int]], categorias: list[int]) -> dict:
    """Modal da rodada 1 × modal da reaplicação, por par (resposta, critério)."""
    return {
        "n": len(pares),
        "exata": concordancia_exata(pares),
        "qwk": kappa_ponderado(pares, categorias),
    }


def ancoragem(concordancia_assistidos: float | None, concordancia_cegos: float | None):
    """Quanto a concordância sobe quando o docente vê a sugestão (protocolo A)."""
    if concordancia_assistidos is None or concordancia_cegos is None:
        return None
    return concordancia_assistidos - concordancia_cegos
