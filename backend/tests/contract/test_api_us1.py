"""Contrato da API da US1 (contracts/api.md: Rubricas, Lotes e importação, Rodadas)."""

import copy

import pytest

from lotes.models import Resposta
from tests import fabricas

pytestmark = pytest.mark.django_db


def _criar_rubrica(api):
    r = api.post("/api/rubricas/", fabricas.RUBRICA_PADRAO, format="json")
    assert r.status_code == 201, r.content
    return r.json()


def test_criar_e_listar_rubrica(api):
    corpo = _criar_rubrica(api)
    assert corpo["titulo"] == "Verificação e validação"
    versao = corpo["versao"]
    assert versao["numero"] == 1 and versao["congelada"] is False
    criterio = versao["criterios"][0]
    assert criterio["ordem"] == 1 and criterio["tipo"] == "OBJETIVO"
    assert [n["codigo"] for n in criterio["niveis"]] == ["N1", "N2", "N3", "N4"]
    assert [n["ordem"] for n in criterio["niveis"]] == [1, 2, 3, 4]
    lista = api.get("/api/rubricas/").json()
    assert lista[0]["id"] == corpo["id"]
    assert lista[0]["versao_vigente"]["numero"] == 1


def test_rubrica_exige_criterio_e_dois_niveis(api):
    sem_criterio = {**fabricas.RUBRICA_PADRAO, "criterios": []}
    assert api.post("/api/rubricas/", sem_criterio, format="json").status_code == 400
    um_nivel = copy.deepcopy(fabricas.RUBRICA_PADRAO)
    um_nivel["criterios"][0]["niveis"] = um_nivel["criterios"][0]["niveis"][:1]
    assert api.post("/api/rubricas/", um_nivel, format="json").status_code == 400


def test_editar_rubrica_nao_congelada_mantem_versao(api):
    corpo = _criar_rubrica(api)
    novo = {**fabricas.RUBRICA_PADRAO, "titulo": "Novo título"}
    r = api.put(f"/api/rubricas/{corpo['id']}/", novo, format="json")
    assert r.status_code == 200
    assert r.json()["versao"]["numero"] == 1
    assert r.json()["titulo"] == "Novo título"


def test_editar_rubrica_congelada_cria_nova_versao(api):
    from rubricas.models import VersaoRubrica
    from rubricas.services import congelar

    corpo = _criar_rubrica(api)
    congelar(VersaoRubrica.objects.get(id=corpo["versao"]["id"]))
    r = api.put(f"/api/rubricas/{corpo['id']}/", fabricas.RUBRICA_PADRAO, format="json")
    assert r.status_code == 201
    assert r.json()["versao"]["numero"] == 2
    assert r.json()["versao"]["congelada"] is False


def test_outra_docente_nao_ve_rubrica(api, cliente, outra_docente):
    corpo = _criar_rubrica(api)
    assert cliente(outra_docente).get(f"/api/rubricas/{corpo['id']}/").status_code == 404
    assert cliente(outra_docente).get("/api/rubricas/").json() == []


def _criar_lote(api, versao_id, **extras):
    corpo = {"titulo": "Turma A", "enunciado": "Explique...", "versao_rubrica": versao_id, **extras}
    r = api.post("/api/lotes/", corpo, format="json")
    assert r.status_code == 201, r.content
    return r.json()


def test_criar_lote_com_padroes(api):
    rubrica = _criar_rubrica(api)
    lote = _criar_lote(api, rubrica["versao"]["id"])
    assert lote["n_execucoes"] == 5
    assert lote["limiar_acordo"] == 0.8
    assert lote["min_validas"] == 3
    assert lote["provedor_llm"] == "dumb"


def test_lote_valida_parametros(api):
    rubrica = _criar_rubrica(api)
    v = rubrica["versao"]["id"]
    corpo = {"titulo": "T", "enunciado": "E", "versao_rubrica": v}
    assert (
        api.post("/api/lotes/", {**corpo, "limiar_acordo": 0.5}, format="json").status_code == 400
    )
    assert api.post("/api/lotes/", {**corpo, "n_execucoes": 11}, format="json").status_code == 400
    assert (
        api.post(
            "/api/lotes/", {**corpo, "n_execucoes": 3, "min_validas": 4}, format="json"
        ).status_code
        == 400
    )


def test_lote_com_rubrica_de_outra_docente_recusado(api, cliente, outra_docente):
    rubrica = _criar_rubrica(api)
    r = cliente(outra_docente).post(
        "/api/lotes/",
        {"titulo": "T", "enunciado": "E", "versao_rubrica": rubrica["versao"]["id"]},
        format="json",
    )
    assert r.status_code == 400


def test_previa_e_importacao(api):
    rubrica = _criar_rubrica(api)
    lote = _criar_lote(api, rubrica["versao"]["id"], sintetico=True)
    r = api.post(
        f"/api/lotes/{lote['id']}/importacao/previa/",
        {"arquivo": fabricas.arquivo_turma()},
        format="multipart",
    )
    assert r.status_code == 200
    assert set(r.json()) == {"colunas", "amostra", "total_linhas"}
    assert Resposta.objects.count() == 0

    dados = {
        "arquivo": fabricas.arquivo_turma(),
        "coluna_resposta": "Resposta 1",
        "colunas_identificacao": fabricas.COLUNAS_ID,
        "gerar_chave": "true",
    }
    r = api.post(f"/api/lotes/{lote['id']}/importacao/", dados, format="multipart")
    assert r.status_code == 201, r.content
    corpo = r.json()
    assert corpo["n_respostas"] == 40
    assert corpo["chave_reidentificacao"]["conteudo_base64"]
    assert {"codigo", "tipo"} == set(corpo["avisos"][0])

    dados["arquivo"] = fabricas.arquivo_turma()
    r = api.post(f"/api/lotes/{lote['id']}/importacao/", dados, format="multipart")
    assert r.status_code == 409
    assert r.json()["codigo"] == "ja_importado"

    detalhe = api.get(f"/api/lotes/{lote['id']}/").json()
    assert detalhe["n_respostas"] == 40
    respostas = api.get(f"/api/lotes/{lote['id']}/respostas/").json()
    assert len(respostas) == 40
    assert {"id", "codigo", "n_caracteres", "aviso"} <= set(respostas[0])
    assert "texto" not in respostas[0]


def test_rodada_estimativa_confirmacao_progresso_e_retomar(api, django_capture_on_commit_callbacks):
    rubrica = _criar_rubrica(api)
    lote = _criar_lote(api, rubrica["versao"]["id"], sintetico=True)
    api.post(
        f"/api/lotes/{lote['id']}/importacao/",
        {
            "arquivo": fabricas.arquivo_turma(),
            "coluna_resposta": "Resposta 1",
            "colunas_identificacao": fabricas.COLUNAS_ID,
        },
        format="multipart",
    )
    est = api.post(f"/api/lotes/{lote['id']}/rodadas/estimativa/", {}, format="json")
    assert est.status_code == 200
    assert {
        "n_chamadas",
        "tokens_entrada_est",
        "tokens_saida_est",
        "custo_estimado_usd",
        "teto_usd",
        "preco_vigente",
    } <= set(est.json())
    assert est.json()["n_chamadas"] == 37 * 4 * 5  # 40 − 2 vazias − 1 longa

    r = api.post(f"/api/lotes/{lote['id']}/rodadas/", {"reaplicacao": False}, format="json")
    assert r.status_code == 400 and r.json()["codigo"] == "confirmacao_necessaria"

    with django_capture_on_commit_callbacks(execute=True):
        r = api.post(f"/api/lotes/{lote['id']}/rodadas/", {"confirmar": True}, format="json")
    assert r.status_code == 201
    rodada_id = r.json()["id"]
    prog = api.get(f"/api/rodadas/{rodada_id}/").json()
    assert {
        "status",
        "pendentes",
        "concluidas",
        "invalidas",
        "falhas",
        "custo_acumulado_usd",
        "teto_usd",
    } <= set(prog)
    assert prog["status"] == "CONCLUIDA" and prog["pendentes"] == 0

    r = api.post(f"/api/rodadas/{rodada_id}/retomar/", {}, format="json")
    assert r.status_code == 200


def test_execucoes_da_resposta(api, cliente, outra_docente, django_capture_on_commit_callbacks):
    rubrica = _criar_rubrica(api)
    lote = _criar_lote(api, rubrica["versao"]["id"], sintetico=True)
    api.post(
        f"/api/lotes/{lote['id']}/importacao/",
        {
            "arquivo": fabricas.arquivo_turma(),
            "coluna_resposta": "Resposta 1",
            "colunas_identificacao": fabricas.COLUNAS_ID,
        },
        format="multipart",
    )
    with django_capture_on_commit_callbacks(execute=True):
        api.post(f"/api/lotes/{lote['id']}/rodadas/", {"confirmar": True}, format="json")
    resposta = Resposta.objects.filter(lote_id=lote["id"], aviso__isnull=True).first()
    r = api.get(f"/api/respostas/{resposta.id}/execucoes/")
    assert r.status_code == 200
    corpo = r.json()
    assert corpo["codigo"] == resposta.codigo and corpo["texto"] == resposta.texto
    execucao = corpo["criterios"][0]["execucoes"][0]
    assert {
        "indice",
        "status",
        "valida",
        "motivo_invalidez",
        "nivel_codigo",
        "justificativa",
        "trechos",
    } <= set(execucao)
    assert cliente(outra_docente).get(f"/api/respostas/{resposta.id}/execucoes/").status_code == 404
