"""US5: protocolo A com ocultação no servidor (quickstart V8)."""

import io
import json
import zipfile

import pytest

from avaliacao.services import criar_rodada
from core.models import Usuario
from estudos.models import AlocacaoResposta, Participacao
from tests import fabricas

pytestmark = pytest.mark.django_db
CHAVES_DA_PRE_AVALIACAO = {"nivel_sugerido", "acordo", "justificativa", "trechos", "alternativas"}


@pytest.fixture
def estudo(pesquisador, cliente, django_capture_on_commit_callbacks):
    lote = fabricas.lote_importado(pesquisador)
    with django_capture_on_commit_callbacks(execute=True):
        rodada = criar_rodada(lote, pesquisador, confirmar=True)
    api = cliente(pesquisador)
    r = api.post(
        "/api/estudos/",
        {"titulo": "Estudo piloto", "lote": lote.id, "rodada": rodada.id},
        format="json",
    )
    assert r.status_code == 201, r.content
    return {"api": api, "id": r.json()["id"], "lote": lote, "rodada": rodada}


def _convidar_e_iniciar(estudo, n=8):
    emails = [f"prof{i}@exemplo.org" for i in range(n)]
    r = estudo["api"].post(
        f"/api/estudos/{estudo['id']}/convites/", {"emails": emails}, format="json"
    )
    assert r.status_code == 201, r.content
    r = estudo["api"].post(f"/api/estudos/{estudo['id']}/iniciar/")
    assert r.status_code == 200, r.content
    return emails, r.json()


def test_so_pesquisador_cria_estudo(docente, api, django_capture_on_commit_callbacks):
    lote = fabricas.lote_importado(docente)
    with django_capture_on_commit_callbacks(execute=True):
        rodada = criar_rodada(lote, docente, confirmar=True)
    r = api.post(
        "/api/estudos/", {"titulo": "x", "lote": lote.id, "rodada": rodada.id}, format="json"
    )
    assert r.status_code == 403


def test_rodada_precisa_estar_concluida(pesquisador, cliente, django_capture_on_commit_callbacks):
    from avaliacao.models import Rodada

    lote = fabricas.lote_importado(pesquisador)
    with django_capture_on_commit_callbacks(execute=True):
        rodada = criar_rodada(lote, pesquisador, confirmar=True)
    Rodada.objects.filter(pk=rodada.pk).update(status="EM_EXECUCAO")
    r = cliente(pesquisador).post(
        "/api/estudos/", {"titulo": "x", "lote": lote.id, "rodada": rodada.id}, format="json"
    )
    assert r.status_code == 400 and r.json()["codigo"] == "rodada_nao_concluida"


def test_convite_cria_conta_e_link_de_senha(estudo, cliente):
    r = estudo["api"].post(
        f"/api/estudos/{estudo['id']}/convites/", {"emails": ["nova@exemplo.org"]}, format="json"
    )
    convite = r.json()["convites"][0]
    assert convite["email"] == "nova@exemplo.org" and "/definir-senha/" in convite["link"]
    usuario = Usuario.objects.get(email="nova@exemplo.org")
    assert not usuario.has_usable_password() and usuario.papel == "DOCENTE"
    uid, token = convite["link"].rstrip("/").split("/")[-2:]
    r = cliente().post(
        "/api/auth/definir-senha/",
        {"uid": uid, "token": token, "senha": "Senha#Forte2026"},
        format="json",
    )
    assert r.status_code == 200
    usuario.refresh_from_db()
    assert usuario.check_password("Senha#Forte2026")
    # o link não serve duas vezes
    r = cliente().post(
        "/api/auth/definir-senha/",
        {"uid": uid, "token": token, "senha": "Outra#2026x"},
        format="json",
    )
    assert r.status_code == 400


def test_iniciar_aloca_metades_e_celulas(estudo):
    _, alocacao = _convidar_e_iniciar(estudo)
    assert abs(alocacao["metade_A"] - alocacao["metade_B"]) <= 1
    assert (
        alocacao["metade_A"] + alocacao["metade_B"]
        == estudo["lote"].respostas.filter(aviso__isnull=True).count()
    )
    celulas = [(p["braco"], p["ordem"]) for p in alocacao["participantes"]]
    for celula in [
        (1, "SEM_PRIMEIRO"),
        (1, "COM_PRIMEIRO"),
        (2, "SEM_PRIMEIRO"),
        (2, "COM_PRIMEIRO"),
    ]:
        assert celulas.count(celula) == 2
    r = estudo["api"].post(
        f"/api/estudos/{estudo['id']}/convites/", {"emails": ["tarde@exemplo.org"]}, format="json"
    )
    assert r.status_code == 400 and r.json()["codigo"] == "estudo_iniciado"


def test_sem_apoio_nao_devolve_nada_da_pre_avaliacao(estudo, cliente):
    emails, _ = _convidar_e_iniciar(estudo)
    participacao = Participacao.objects.get(estudo_id=estudo["id"], docente__email=emails[0])
    api = cliente(participacao.docente)
    tarefa = api.get(f"/api/estudos/{estudo['id']}/minha-tarefa/").json()
    assert tarefa["bloco_atual"]["condicao"] == (
        "SEM_APOIO" if participacao.ordem == "SEM_PRIMEIRO" else "COM_APOIO"
    )
    metade_sem = "A" if participacao.braco == 1 else "B"
    resposta = (
        AlocacaoResposta.objects.filter(estudo_id=estudo["id"], metade=metade_sem).first().resposta
    )
    corpo = api.post(f"/api/estudos/{estudo['id']}/respostas/{resposta.id}/sessoes/").json()
    assert corpo["condicao"] == "SEM_APOIO"
    texto_json = json.dumps(corpo)
    for chave in CHAVES_DA_PRE_AVALIACAO:
        assert f'"{chave}"' not in texto_json, chave
    assert {s["estado"] for s in corpo["criterios"]} == {"OCULTO"}

    metade_com = "B" if metade_sem == "A" else "A"
    outra = (
        AlocacaoResposta.objects.filter(estudo_id=estudo["id"], metade=metade_com).first().resposta
    )
    corpo = api.post(f"/api/estudos/{estudo['id']}/respostas/{outra.id}/sessoes/").json()
    assert corpo["condicao"] == "COM_APOIO"
    assert {s["estado"] for s in corpo["criterios"]} != {"OCULTO"}


def test_participante_nao_acessa_lote_nem_execucoes(estudo, cliente):
    emails, _ = _convidar_e_iniciar(estudo)
    participante = Usuario.objects.get(email=emails[0])
    api = cliente(participante)
    lote = estudo["lote"]
    resposta = lote.respostas.first()
    assert api.get(f"/api/lotes/{lote.id}/").status_code == 404
    assert api.get(f"/api/respostas/{resposta.id}/execucoes/").status_code == 404
    assert api.get(f"/api/respostas/{resposta.id}/sugestoes/").status_code == 404
    assert api.post(f"/api/respostas/{resposta.id}/sessoes/").status_code == 404
    assert api.get(f"/api/estudos/{estudo['id']}/painel/").status_code == 403


def test_decisoes_do_estudo_nao_se_misturam_com_as_do_dono(estudo, cliente, pesquisador):
    from revisao.models import Decisao
    from revisao.services import abrir_sessao, registrar_decisao

    emails, _ = _convidar_e_iniciar(estudo, n=2)
    participante = Usuario.objects.get(email=emails[0])
    alocada = AlocacaoResposta.objects.filter(estudo_id=estudo["id"]).first().resposta
    criterio = estudo["lote"].versao_rubrica.criterios.first()
    api = cliente(participante)
    sessao = api.post(f"/api/estudos/{estudo['id']}/respostas/{alocada.id}/sessoes/").json()[
        "sessao"
    ]
    api.post(
        f"/api/sessoes/{sessao}/decisoes/",
        {"criterio": criterio.id, "nivel": criterio.niveis.first().id, "tempo_ativo_ms": 900},
        format="json",
    )
    # o dono corrige a mesma resposta fora do estudo
    s, _ = abrir_sessao(pesquisador, alocada)
    registrar_decisao(s, criterio.id, criterio.niveis.last().id, "", 100)
    assert Decisao.objects.filter(resposta=alocada, criterio=criterio, vigente=True).count() == 2
    fila_dono = cliente(pesquisador).get(f"/api/lotes/{estudo['lote'].id}/fila/").json()
    item = next(i for i in fila_dono["respostas"] if i["resposta"] == alocada.id)
    assert item["n_decididos"] == 1


def test_minha_tarefa_avanca_e_conclui(estudo, cliente):
    emails, _ = _convidar_e_iniciar(estudo, n=2)
    participacao = Participacao.objects.get(estudo_id=estudo["id"], docente__email=emails[0])
    api = cliente(participacao.docente)
    criterios = list(estudo["lote"].versao_rubrica.criterios.all())
    vistos = []
    while True:
        tarefa = api.get(f"/api/estudos/{estudo['id']}/minha-tarefa/").json()
        if tarefa["proxima_resposta"] is None:
            break
        rid = tarefa["proxima_resposta"]["id"]
        assert rid not in vistos
        vistos.append(rid)
        sessao = api.post(f"/api/estudos/{estudo['id']}/respostas/{rid}/sessoes/").json()["sessao"]
        for c in criterios:
            api.post(
                f"/api/sessoes/{sessao}/decisoes/",
                {"criterio": c.id, "nivel": c.niveis.first().id, "tempo_ativo_ms": 1000},
                format="json",
            )
    assert len(vistos) == AlocacaoResposta.objects.filter(estudo_id=estudo["id"]).count()
    assert tarefa["concluido"] is True
    participacao.refresh_from_db()
    assert participacao.concluida_em is not None


def test_painel_e_exportacao_do_estudo(estudo, cliente):
    emails, _ = _convidar_e_iniciar(estudo, n=4)
    criterios = list(estudo["lote"].versao_rubrica.criterios.all())
    for i, email in enumerate(emails):
        api = cliente(Usuario.objects.get(email=email))
        for _ in range(6):
            tarefa = api.get(f"/api/estudos/{estudo['id']}/minha-tarefa/").json()
            rid = tarefa["proxima_resposta"]["id"]
            sessao = api.post(f"/api/estudos/{estudo['id']}/respostas/{rid}/sessoes/").json()[
                "sessao"
            ]
            for j, c in enumerate(criterios):
                nivel = list(c.niveis.order_by("ordem"))[(i + j) % 4]
                api.post(
                    f"/api/sessoes/{sessao}/decisoes/",
                    {"criterio": c.id, "nivel": nivel.id, "tempo_ativo_ms": 1000 + 100 * i},
                    format="json",
                )
    painel = estudo["api"].get(f"/api/estudos/{estudo['id']}/painel/").json()
    assert {
        "cegos",
        "assistidos",
        "ancoragem",
        "referencia_humana",
        "tempo",
        "participantes",
    } <= set(painel)
    assert painel["cegos"]["n"] > 0 or painel["assistidos"]["n"] > 0
    assert len(painel["participantes"]) == 4
    assert {"SEM_APOIO", "COM_APOIO"} <= set(painel["tempo"])

    r = estudo["api"].get(f"/api/estudos/{estudo['id']}/exportacao.zip")
    assert r.status_code == 200
    with zipfile.ZipFile(io.BytesIO(r.content)) as z:
        nomes = set(z.namelist())
        assert {"alocacao.csv", "decisoes.csv", "sessoes.csv", "metricas_estudo.json"} <= nomes
        alocacao = z.read("alocacao.csv").decode("utf-8")
        assert alocacao.splitlines()[0] == "participante,braco,ordem"
        assert "P01" in alocacao and "@" not in alocacao
        decisoes = z.read("decisoes.csv").decode("utf-8")
        assert "P0" in decisoes and "@" not in decisoes
        respostas = z.read("respostas.csv").decode("utf-8").splitlines()
        assert any(linha.endswith(",A") or linha.endswith(",B") for linha in respostas[1:])
