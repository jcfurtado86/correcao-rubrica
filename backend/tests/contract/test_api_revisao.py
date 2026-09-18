"""Contrato da revisão (contracts/api.md, seção Revisão)."""

import pytest

from avaliacao.services import criar_rodada
from tests import fabricas

pytestmark = pytest.mark.django_db


@pytest.fixture
def lote_avaliado(docente, django_capture_on_commit_callbacks):
    lote = fabricas.lote_importado(docente)
    with django_capture_on_commit_callbacks(execute=True):
        criar_rodada(lote, docente, confirmar=True)
    return lote


def test_abrir_sessao(lote_avaliado, api):
    resposta = lote_avaliado.respostas.filter(aviso__isnull=True).first()
    r = api.post(f"/api/respostas/{resposta.id}/sessoes/")
    assert r.status_code == 201
    corpo = r.json()
    assert {
        "sessao",
        "resposta",
        "codigo",
        "texto",
        "condicao",
        "rodada",
        "criterios",
        "decisoes_vigentes",
    } <= set(corpo)
    assert corpo["condicao"] == "COM_APOIO"
    assert len(corpo["criterios"]) == 4
    assert {"criterio", "estado"} <= set(corpo["criterios"][0])


def test_decidir_patch_e_historico(lote_avaliado, api):
    resposta = lote_avaliado.respostas.filter(aviso__isnull=True).first()
    criterio = lote_avaliado.versao_rubrica.criterios.first()
    n1, n2 = list(criterio.niveis.order_by("ordem"))[:2]
    sessao = api.post(f"/api/respostas/{resposta.id}/sessoes/").json()["sessao"]

    r = api.post(
        f"/api/sessoes/{sessao}/decisoes/",
        {"criterio": criterio.id, "nivel": n1.id, "tempo_ativo_ms": 1200},
        format="json",
    )
    assert r.status_code == 201
    assert {
        "id",
        "criterio",
        "nivel",
        "tipo",
        "estado_exibido",
        "nivel_sugerido",
        "motivo",
        "vigente",
        "criado_em",
    } <= set(r.json())
    api.post(
        f"/api/sessoes/{sessao}/decisoes/",
        {"criterio": criterio.id, "nivel": n2.id, "motivo": "revisei", "tempo_ativo_ms": 2500},
        format="json",
    )
    assert (
        api.patch(f"/api/sessoes/{sessao}/", {"tempo_ativo_ms": 4000}, format="json").status_code
        == 200
    )

    historico = api.get(f"/api/respostas/{resposta.id}/historico/").json()
    assert len(historico) == 2
    assert [h["vigente"] for h in historico] == [False, True]
    assert historico[1]["motivo"] == "revisei"

    reaberta = api.post(f"/api/respostas/{resposta.id}/sessoes/").json()
    assert reaberta["decisoes_vigentes"][0]["nivel"] == n2.id


def test_tempo_negativo_recusado(lote_avaliado, api):
    resposta = lote_avaliado.respostas.first()
    criterio = lote_avaliado.versao_rubrica.criterios.first()
    sessao = api.post(f"/api/respostas/{resposta.id}/sessoes/").json()["sessao"]
    r = api.post(
        f"/api/sessoes/{sessao}/decisoes/",
        {"criterio": criterio.id, "nivel": criterio.niveis.first().id, "tempo_ativo_ms": -5},
        format="json",
    )
    assert r.status_code == 400


def test_outra_docente_nao_abre_sessao(lote_avaliado, cliente, outra_docente):
    resposta = lote_avaliado.respostas.first()
    assert cliente(outra_docente).post(f"/api/respostas/{resposta.id}/sessoes/").status_code == 404


def test_notas_csv_vazio_tem_cabecalho(lote_avaliado, api):
    r = api.get(f"/api/lotes/{lote_avaliado.id}/notas.csv")
    assert r.status_code == 200
    assert r.content.decode("utf-8").splitlines()[0].startswith("codigo,")
