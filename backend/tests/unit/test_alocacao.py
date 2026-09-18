import pytest

from estudos.alocacao import alocar_participantes, blocos, condicao, dividir_metades, ordem_do_bloco


def _itens(n_nao_conv, n_conv):
    return [(i, True) for i in range(n_nao_conv)] + [(100 + i, False) for i in range(n_conv)]


@pytest.mark.parametrize(("nc", "c"), [(10, 27), (9, 28), (1, 1), (0, 12), (7, 0), (3, 4)])
def test_metades_equilibradas_no_total_e_por_estrato(nc, c):
    itens = _itens(nc, c)
    metades = dividir_metades(itens, semente=42)
    assert set(metades) == {i for i, _ in itens}
    a = [i for i, m in metades.items() if m == "A"]
    b = [i for i, m in metades.items() if m == "B"]
    assert abs(len(a) - len(b)) <= 1
    for estrato in (True, False):
        ids = {i for i, e in itens if e is estrato}
        assert abs(sum(1 for i in a if i in ids) - sum(1 for i in b if i in ids)) <= 1


def test_metades_deterministicas_pela_semente():
    itens = _itens(10, 27)
    assert dividir_metades(itens, 7) == dividir_metades(itens, 7)
    assert dividir_metades(itens, 7) != dividir_metades(itens, 8)


def test_oito_participantes_dois_por_celula():
    celulas = alocar_participantes(8)
    assert len(celulas) == 8
    for celula in [
        (1, "SEM_PRIMEIRO"),
        (1, "COM_PRIMEIRO"),
        (2, "SEM_PRIMEIRO"),
        (2, "COM_PRIMEIRO"),
    ]:
        assert celulas.count(celula) == 2


def test_dois_participantes_cobrem_os_dois_bracos_e_as_duas_ordens():
    (b1, o1), (b2, o2) = alocar_participantes(2)
    assert {b1, b2} == {1, 2} and {o1, o2} == {"SEM_PRIMEIRO", "COM_PRIMEIRO"}


@pytest.mark.parametrize(
    ("metade", "braco", "esperada"),
    [("A", 1, "SEM_APOIO"), ("B", 1, "COM_APOIO"), ("A", 2, "COM_APOIO"), ("B", 2, "SEM_APOIO")],
)
def test_tabela_de_condicoes(metade, braco, esperada):
    assert condicao(metade, braco) == esperada


def test_blocos_seguem_a_ordem():
    assert blocos(1, "SEM_PRIMEIRO") == [("A", "SEM_APOIO"), ("B", "COM_APOIO")]
    assert blocos(1, "COM_PRIMEIRO") == [("B", "COM_APOIO"), ("A", "SEM_APOIO")]
    assert blocos(2, "SEM_PRIMEIRO") == [("B", "SEM_APOIO"), ("A", "COM_APOIO")]


def test_ordem_do_bloco_embaralha_por_participante_de_forma_reproduzivel():
    ids = list(range(20))
    a = ordem_do_bloco(ids, semente=1, participacao_id=10)
    assert sorted(a) == ids
    assert a == ordem_do_bloco(ids, semente=1, participacao_id=10)
    assert a != ordem_do_bloco(ids, semente=1, participacao_id=11)
