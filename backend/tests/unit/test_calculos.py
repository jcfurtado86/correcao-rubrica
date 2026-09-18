"""Métricas (research R10) contra valores calculados à mão ou pela biblioteca de referência."""

import math

import numpy as np
import pytest
from sklearn.metrics import cohen_kappa_score
from statsmodels.stats.inter_rater import fleiss_kappa

from metricas import calculos as c

PARES = [(1, 1), (2, 3), (3, 3), (4, 2)]


def test_concordancia_exata_e_adjacente():
    assert c.concordancia_exata(PARES) == 0.5
    assert c.concordancia_adjacente(PARES) == 0.75
    assert c.concordancia_exata([]) is None


def test_kappa_quadratico_igual_ao_sklearn():
    pares = [(1, 1), (2, 3), (3, 3), (4, 2), (2, 2), (1, 2), (4, 4)]
    esperado = cohen_kappa_score(
        [a for a, _ in pares], [b for _, b in pares], weights="quadratic", labels=[1, 2, 3, 4]
    )
    assert c.kappa_ponderado(pares, [1, 2, 3, 4]) == pytest.approx(esperado)


def test_kappa_indefinido_vira_none():
    assert c.kappa_ponderado([(2, 2), (2, 2)], [1, 2, 3]) is None
    assert c.kappa_ponderado([(1, 1)], [1, 2]) is None


def test_seletiva_e_cobertura():
    itens = [
        ("CONVERGENTE", 2, 2),
        ("CONVERGENTE", 3, 3),
        ("CONVERGENTE", 1, 2),
        ("DIVERGENTE", 2, 3),
        ("DIVERGENTE", 2, 2),
    ]
    r = c.seletiva(itens)
    assert r["cobertura"] == 0.6
    assert r["exata_convergentes"] == pytest.approx(2 / 3)
    assert r["exata_nao_convergentes"] == 0.5
    assert r["n_convergentes"] == 3 and r["n_nao_convergentes"] == 2


def test_taxas_de_divergencia():
    estados = ["CONVERGENTE", "DIVERGENTE", "SEM_EVIDENCIA", "INDETERMINADO"]
    assert c.taxa(estados, {"DIVERGENTE"}) == 0.25
    assert c.taxa(estados, c.NAO_CONVERGENTES) == 0.75
    assert c.taxa([], {"DIVERGENTE"}) is None


def test_fleiss_igual_ao_statsmodels():
    tabela = [[5, 0, 0], [3, 2, 0], [2, 2, 1], [0, 5, 0], [1, 1, 3]]
    assert c.fleiss(tabela) == pytest.approx(fleiss_kappa(np.array(tabela)))
    assert c.fleiss([[5, 0], [5, 0]]) is None  # uma só categoria: indefinido
    assert c.fleiss([]) is None


def test_tabela_fleiss_a_partir_de_votos():
    votos = [["N1", "N1", "N2"], ["N2", "N2", "N2"]]
    assert c.tabela_fleiss(votos) == [[2, 1], [0, 3]]


def test_krippendorff_ordinal():
    perfeito = [[1, 2, 3, 4], [1, 2, 3, 4]]
    assert c.krippendorff_ordinal(perfeito) == pytest.approx(1.0)
    com_falta = [[1, 2, 3, math.nan], [1, 2, 4, 4], [math.nan, 2, 3, 4]]
    import krippendorff

    esperado = krippendorff.alpha(reliability_data=com_falta, level_of_measurement="ordinal")
    assert c.krippendorff_ordinal(com_falta) == pytest.approx(esperado)
    assert c.krippendorff_ordinal([[1, 1], [1, 1]]) is None


def test_estabilidade_entre_rodadas():
    r = c.estabilidade([(1, 1), (2, 2), (3, 2)], [1, 2, 3])
    assert r["n"] == 3 and r["exata"] == pytest.approx(2 / 3)
    assert "qwk" in r


def test_ancoragem_e_mediana():
    assert c.ancoragem(0.8, 0.6) == pytest.approx(0.2)
    assert c.ancoragem(None, 0.6) is None
    assert c.mediana([3, 1, 2]) == 2
    assert c.mediana([1, 2]) == 1.5
    assert c.mediana([]) is None


def test_media():
    assert c.media([1, 2, 3, 4]) == 2.5
    assert c.media([]) is None
