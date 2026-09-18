from decimal import Decimal

import pytest

from avaliacao.consolidacao import consolidar, representativa_por_nivel


def _votos(*codigos):
    return [(i + 1, c) for i, c in enumerate(codigos)]


def test_unanime_convergente():
    r = consolidar(_votos("N3", "N3", "N3", "N3", "N3"), Decimal("0.8"), 3)
    assert r.estado == "CONVERGENTE" and r.modal == "N3" and r.acordo == Decimal("1")
    assert r.n_validas == 5 and r.distribuicao == {"N3": 5}


def test_4_1_convergente_no_limiar():
    r = consolidar(_votos("N2", "N2", "N2", "N2", "N3"), Decimal("0.8"), 3)
    assert r.estado == "CONVERGENTE" and r.modal == "N2" and r.acordo == Decimal("0.8")


def test_3_2_divergente_com_modal_guardado():
    r = consolidar(_votos("N2", "N2", "N2", "N3", "N3"), Decimal("0.8"), 3)
    assert r.estado == "DIVERGENTE"
    assert r.modal == "N2"  # guardado para a hipótese SC-008a, mas não exibido
    assert r.distribuicao == {"N2": 3, "N3": 2}


def test_2_2_1_divergente():
    r = consolidar(_votos("N2", "N2", "N3", "N3", "N1"), Decimal("0.8"), 3)
    assert r.estado == "DIVERGENTE"
    assert r.modal == "N2"  # empate: o nível que apareceu primeiro


def test_sem_evidencia_modal():
    r = consolidar(_votos(*["SEM_EVIDENCIA"] * 5), Decimal("0.8"), 3)
    assert r.estado == "SEM_EVIDENCIA" and r.modal == "SEM_EVIDENCIA"


def test_sem_evidencia_dividido_e_divergente():
    r = consolidar(_votos("SEM_EVIDENCIA", "SEM_EVIDENCIA", "N1", "N1", "N1"), Decimal("0.8"), 3)
    assert r.estado == "DIVERGENTE"


def test_poucas_validas_indeterminado():
    r = consolidar(_votos("N2", "N2"), Decimal("0.8"), 3)
    assert r.estado == "INDETERMINADO" and r.n_validas == 2


def test_nenhuma_valida_indeterminado_sem_modal():
    r = consolidar([], Decimal("0.8"), 3)
    assert r.estado == "INDETERMINADO" and r.modal is None and r.acordo == 0


def test_limiar_precisa_passar_de_meio():
    with pytest.raises(ValueError):
        consolidar(_votos("N1"), Decimal("0.5"), 1)


def test_recalculo_com_limiar_menor_muda_3_2_para_convergente():
    r = consolidar(_votos("N2", "N2", "N2", "N3", "N3"), Decimal("0.6"), 3)
    assert r.estado == "CONVERGENTE" and r.modal == "N2"


def test_limiar_1_exige_unanimidade():
    assert consolidar(_votos("N2", "N2", "N2", "N2", "N3"), Decimal("1"), 3).estado == "DIVERGENTE"


def test_representativa_e_a_de_menor_indice():
    class E:
        def __init__(self, indice, nivel_codigo):
            self.indice, self.nivel_codigo = indice, nivel_codigo

    execs = [E(4, "N3"), E(2, "N2"), E(5, "N3"), E(1, "N2")]
    rep = representativa_por_nivel(execs)
    assert rep["N2"].indice == 1 and rep["N3"].indice == 4
