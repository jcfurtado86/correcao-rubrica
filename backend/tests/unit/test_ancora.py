import json

import pytest

from avaliacao.ancora import localizar, normalizar_com_mapa, verificar_trecho
from avaliacao.validacao import validar

TEXTO = (
    "Verificação é conferir se o software foi construído\ncorretamente.  Validação é ver se "
    "construímos o “software certo” — aquele que o usuário precisa."
)
CODIGOS = ["N1", "N2", "N3", "N4"]


def _json(nivel, trechos, justificativa="ok"):
    return json.dumps({"nivel": nivel, "justificativa": justificativa, "trechos": trechos})


def test_trecho_exato_com_offsets_no_original():
    trecho = "conferir se o software foi construído"
    inicio, fim = localizar(TEXTO, trecho)
    assert TEXTO[inicio:fim] == trecho


def test_diferenca_de_espacos_e_quebra_de_linha():
    inicio, fim = localizar(TEXTO, "foi construído corretamente. Validação é ver")
    assert TEXTO[inicio:fim] == "foi construído\ncorretamente.  Validação é ver"


def test_aspas_e_travessao_tipograficos():
    inicio, fim = localizar(TEXTO, 'construímos o "software certo" - aquele que')
    assert TEXTO[inicio:fim] == "construímos o “software certo” — aquele que"


def test_caixa_diferente():
    assert localizar(TEXTO, "VALIDAÇÃO É VER SE") is not None


def test_nao_localizado():
    assert localizar(TEXTO, "testes unitários automatizados") is None


def test_mapa_aponta_para_o_original():
    normalizado, mapa = normalizar_com_mapa("A  “b”\nC")
    assert normalizado == 'a "b" c'
    assert len(mapa) == len(normalizado)
    assert mapa[-1] == len("A  “b”\nC") - 1


@pytest.mark.parametrize(
    ("trecho", "motivo"),
    [
        ("o software", "TRECHO_CURTO"),
        ("conferir se ... construído", "TRECHO_NAO_LOCALIZADO"),
        ("conferir se o software… construído", "TRECHO_NAO_LOCALIZADO"),
        ("frase que não está lá", "TRECHO_NAO_LOCALIZADO"),
        ("", "TRECHO_CURTO"),
    ],
)
def test_trechos_invalidos(trecho, motivo):
    assert verificar_trecho(TEXTO, trecho)[0] == motivo


def test_pontuacao_final_do_trecho_e_tolerada():
    motivo, inicio, fim = verificar_trecho(TEXTO, "aquele que o usuário precisa!")
    assert motivo is None
    assert TEXTO[inicio:fim] == "aquele que o usuário precisa"


def test_validacao_execucao_valida():
    r = validar(TEXTO, _json("N3", ["conferir se o software foi construído"]), CODIGOS)
    assert r.valida and r.motivo_invalidez is None and r.nivel_codigo == "N3"
    assert r.trechos[0].localizado and TEXTO[r.trechos[0].inicio : r.trechos[0].fim]


def test_sem_evidencia_com_trechos_e_incoerente():
    r = validar(TEXTO, _json("SEM_EVIDENCIA", ["conferir se o software foi"]), CODIGOS)
    assert not r.valida and r.motivo_invalidez == "INCOERENTE_SEM_EVIDENCIA"


def test_sem_evidencia_sem_trechos_e_valida():
    r = validar(TEXTO, _json("SEM_EVIDENCIA", []), CODIGOS)
    assert r.valida and r.nivel_codigo == "SEM_EVIDENCIA"


def test_nivel_sem_trecho():
    r = validar(TEXTO, _json("N2", []), CODIGOS)
    assert not r.valida and r.motivo_invalidez == "SEM_TRECHO"


def test_um_trecho_nao_localizado_entre_dois_invalida_a_execucao():
    r = validar(
        TEXTO,
        _json("N2", ["conferir se o software foi construído", "texto inventado aqui"]),
        CODIGOS,
    )
    assert not r.valida and r.motivo_invalidez == "TRECHO_NAO_LOCALIZADO"
    assert [t.localizado for t in r.trechos] == [True, False]


def test_json_invalido():
    r = validar(TEXTO, '{nivel: "N1"', CODIGOS)
    assert not r.valida and r.motivo_invalidez == "JSON_INVALIDO"


def test_json_sem_campos_obrigatorios():
    r = validar(TEXTO, json.dumps({"nivel": "N1"}), CODIGOS)
    assert r.motivo_invalidez == "JSON_INVALIDO"


def test_nivel_fora_do_enum():
    r = validar(TEXTO, _json("N9", ["conferir se o software foi construído"]), CODIGOS)
    assert r.motivo_invalidez == "NIVEL_FORA"
