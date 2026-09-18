"""US3: decisão docente registrada, histórico e notas (quickstart V5)."""

import csv
import io

import pytest

from avaliacao.models import Consolidado
from avaliacao.services import criar_rodada
from core.exceptions import ErroDeNegocio
from revisao.models import Decisao
from revisao.services import abrir_sessao, finalizada, nota, registrar_decisao
from tests import fabricas

pytestmark = pytest.mark.django_db


@pytest.fixture
def lote_avaliado(docente, django_capture_on_commit_callbacks):
    lote = fabricas.lote_importado(docente)
    with django_capture_on_commit_callbacks(execute=True):
        rodada = criar_rodada(lote, docente, confirmar=True)
    return lote, rodada


def _resposta(lote, cenario):
    return lote.respostas.get(texto__contains=f"[[cenario:{cenario}]]")


def test_tipo_da_decisao(lote_avaliado, docente):
    lote, rodada = lote_avaliado
    convergente = _resposta(lote, "unanime")
    sessao, _ = abrir_sessao(docente, convergente)
    criterios = list(lote.versao_rubrica.criterios.order_by("ordem"))
    sugerido = Consolidado.objects.get(
        rodada=rodada, resposta=convergente, criterio=criterios[0]
    ).nivel_modal
    outro = (
        criterios[1]
        .niveis.exclude(
            pk=Consolidado.objects.get(
                rodada=rodada, resposta=convergente, criterio=criterios[1]
            ).nivel_modal_id
        )
        .first()
    )

    d1 = registrar_decisao(sessao, criterios[0].id, sugerido.id, "", 1000)
    d2 = registrar_decisao(sessao, criterios[1].id, outro.id, "discordo do exemplo", 2000)
    assert (
        d1.tipo == "CONFIRMACAO"
        and d1.estado_exibido == "CONVERGENTE"
        and d1.nivel_sugerido == sugerido
    )
    assert d2.tipo == "ALTERACAO" and d2.motivo == "discordo do exemplo"

    divergente = _resposta(lote, "3-2")
    sessao2, _ = abrir_sessao(docente, divergente)
    nivel = criterios[0].niveis.first()
    d3 = registrar_decisao(sessao2, criterios[0].id, nivel.id, "", 500)
    assert d3.tipo == "ESCOLHA" and d3.estado_exibido == "DIVERGENTE" and d3.nivel_sugerido is None


def test_nova_decisao_substitui_a_anterior_e_preserva_historico(lote_avaliado, docente):
    lote, _ = lote_avaliado
    resposta = _resposta(lote, "unanime")
    criterio = lote.versao_rubrica.criterios.order_by("ordem").first()
    n1, n2 = list(criterio.niveis.order_by("ordem"))[:2]
    sessao, _ = abrir_sessao(docente, resposta)
    primeira = registrar_decisao(sessao, criterio.id, n1.id, "", 1000)
    segunda = registrar_decisao(sessao, criterio.id, n2.id, "mudei", 3000)
    primeira.refresh_from_db()
    assert not primeira.vigente and segunda.vigente and segunda.substitui == primeira
    assert Decisao.objects.filter(resposta=resposta, criterio=criterio, vigente=True).count() == 1
    assert Decisao.objects.filter(resposta=resposta, criterio=criterio).count() == 2


def test_nivel_de_outro_criterio_recusado(lote_avaliado, docente):
    lote, _ = lote_avaliado
    c1, c2 = list(lote.versao_rubrica.criterios.order_by("ordem"))[:2]
    sessao, _ = abrir_sessao(docente, lote.respostas.first())
    with pytest.raises(ErroDeNegocio) as erro:
        registrar_decisao(sessao, c1.id, c2.niveis.first().id, "", 0)
    assert erro.value.codigo == "nivel_invalido"


def test_criterio_de_outra_rubrica_recusado(lote_avaliado, docente):
    lote, _ = lote_avaliado
    outra = fabricas.rubrica(docente).versao_vigente.criterios.first()
    sessao, _ = abrir_sessao(docente, lote.respostas.first())
    with pytest.raises(ErroDeNegocio) as erro:
        registrar_decisao(sessao, outra.id, outra.niveis.first().id, "", 0)
    assert erro.value.codigo == "criterio_invalido"


def test_tempo_da_sessao_e_o_da_ultima_decisao(lote_avaliado, docente):
    lote, _ = lote_avaliado
    criterios = list(lote.versao_rubrica.criterios.order_by("ordem"))
    sessao, _ = abrir_sessao(docente, lote.respostas.first())
    registrar_decisao(sessao, criterios[0].id, criterios[0].niveis.first().id, "", 4000)
    registrar_decisao(sessao, criterios[1].id, criterios[1].niveis.first().id, "", 9000)
    sessao.refresh_from_db()
    assert sessao.tempo_ativo_ms == 9000


def test_finalizada_e_nota(lote_avaliado, docente):
    lote, _ = lote_avaliado
    resposta = lote.respostas.first()
    criterios = list(lote.versao_rubrica.criterios.order_by("ordem"))
    sessao, _ = abrir_sessao(docente, resposta)
    for c in criterios[:-1]:
        registrar_decisao(sessao, c.id, c.niveis.get(ordem=3).id, "", 1000)
    assert not finalizada(resposta, docente)
    registrar_decisao(sessao, criterios[-1].id, criterios[-1].niveis.get(ordem=4).id, "", 2000)
    assert finalizada(resposta, docente)
    assert nota(resposta, docente) == 2 * 3 + 3  # 3 critérios no N3 (2 pts) + 1 no N4 (3 pts)


def test_notas_csv_so_com_finalizadas(lote_avaliado, docente, api):
    lote, _ = lote_avaliado
    criterios = list(lote.versao_rubrica.criterios.order_by("ordem"))
    respostas = list(lote.respostas.order_by("codigo"))
    for r in respostas[:10]:
        sessao, _ = abrir_sessao(docente, r)
        for c in criterios:
            registrar_decisao(sessao, c.id, c.niveis.get(ordem=2).id, "", 1000)
    for r in respostas[10:15]:
        sessao, _ = abrir_sessao(docente, r)
        registrar_decisao(sessao, criterios[0].id, criterios[0].niveis.first().id, "", 1000)
    resposta_http = api.get(f"/api/lotes/{lote.id}/notas.csv")
    assert resposta_http.status_code == 200
    assert resposta_http["Content-Type"].startswith("text/csv")
    linhas = list(csv.reader(io.StringIO(resposta_http.content.decode("utf-8"))))
    assert linhas[0] == ["codigo", *[c.nome for c in criterios], "nota_total"]
    assert len(linhas) == 11
    assert [linha[0] for linha in linhas[1:]] == [r.codigo for r in respostas[:10]]
    assert all(float(linha[-1]) == 4.0 for linha in linhas[1:])  # 4 critérios × 1 pt × peso 1


def test_nao_existe_decisao_em_lote(lote_avaliado, docente, api):
    lote, _ = lote_avaliado
    sessao = api.post(f"/api/respostas/{lote.respostas.first().id}/sessoes/").json()
    criterio = lote.versao_rubrica.criterios.first()
    lista = [{"criterio": criterio.id, "nivel": criterio.niveis.first().id, "tempo_ativo_ms": 1}]
    r = api.post(f"/api/sessoes/{sessao['sessao']}/decisoes/", lista, format="json")
    assert r.status_code == 400
    assert Decisao.objects.count() == 0


def test_decisao_so_na_propria_sessao(lote_avaliado, docente, cliente, outra_docente):
    lote, _ = lote_avaliado
    sessao = cliente(docente).post(f"/api/respostas/{lote.respostas.first().id}/sessoes/").json()
    criterio = lote.versao_rubrica.criterios.first()
    r = cliente(outra_docente).post(
        f"/api/sessoes/{sessao['sessao']}/decisoes/",
        {"criterio": criterio.id, "nivel": criterio.niveis.first().id, "tempo_ativo_ms": 1},
        format="json",
    )
    assert r.status_code == 404


def test_fila_conta_decididos(lote_avaliado, docente, api):
    lote, _ = lote_avaliado
    resposta = lote.respostas.order_by("codigo").first()
    criterios = list(lote.versao_rubrica.criterios.all())
    sessao, _ = abrir_sessao(docente, resposta)
    for c in criterios:
        registrar_decisao(sessao, c.id, c.niveis.first().id, "", 10)
    item = next(
        i
        for i in api.get(f"/api/lotes/{lote.id}/fila/").json()["respostas"]
        if i["resposta"] == resposta.id
    )
    assert item["n_decididos"] == 4 and item["finalizada"] is True
