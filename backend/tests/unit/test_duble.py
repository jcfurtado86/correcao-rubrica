import json

import pytest

from conectores.duble import FRASE_INVENTADA, DubleLLMProvider

ESQUEMA = {"properties": {"nivel": {"enum": ["N1", "N2", "N3", "N4", "SEM_EVIDENCIA"]}}}
TEXTO = "Verificação confere se construímos certo o produto. Validação confere o produto certo."


def _avaliar(cenario, indice, semente=1):
    usuario = f"RESPOSTA:\n<<<\n{TEXTO} [[cenario:{cenario}]]\n>>>"
    return DubleLLMProvider().avaliar("sistema", usuario, ESQUEMA, semente, indice)


@pytest.mark.parametrize(
    ("cenario", "esperado"),
    [
        ("unanime", ["N2"] * 5),
        ("4-1", ["N2", "N2", "N2", "N2", "N3"]),
        ("3-2", ["N2", "N2", "N2", "N3", "N3"]),
        ("2-2-1", ["N2", "N2", "N3", "N3", "N1"]),
        ("sem_evidencia", ["SEM_EVIDENCIA"] * 5),
        ("trecho_inventado", ["N2"] * 5),
    ],
)
def test_roteiros_produzem_a_sequencia_esperada(cenario, esperado):
    niveis = [json.loads(_avaliar(cenario, i).texto)["nivel"] for i in range(1, 6)]
    assert niveis == esperado


def test_trecho_e_substring_real_exceto_no_inventado():
    for i in range(1, 6):
        saida = json.loads(_avaliar("unanime", i).texto)
        assert all(t in TEXTO for t in saida["trechos"])
    inventados = [json.loads(_avaliar("trecho_inventado", i).texto)["trechos"] for i in (1, 2)]
    assert inventados == [[FRASE_INVENTADA], [FRASE_INVENTADA]]


def test_json_invalido():
    with pytest.raises(json.JSONDecodeError):
        json.loads(_avaliar("json_invalido", 1).texto)


def test_sem_evidencia_nao_cita_trecho():
    assert json.loads(_avaliar("sem_evidencia", 3).texto)["trechos"] == []


def test_registra_prompts_para_auditoria():
    _avaliar("unanime", 1)
    assert len(DubleLLMProvider.prompts_recebidos) == 1


def test_modo_pseudoaleatorio_e_deterministico():
    usuario = f"<<<\n{TEXTO}\n>>>"
    a = DubleLLMProvider().avaliar("s", usuario, ESQUEMA, 7).texto
    b = DubleLLMProvider().avaliar("s", usuario, ESQUEMA, 7).texto
    assert a == b
