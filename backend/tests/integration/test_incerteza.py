"""US2: a consolidação declara a incerteza (quickstart V4)."""

import pytest

from avaliacao.models import Consolidado
from avaliacao.services import criar_rodada
from tests import fabricas

pytestmark = pytest.mark.django_db

ESPERADO = {
    "unanime": ("CONVERGENTE", 5),
    "4-1": ("CONVERGENTE", 5),
    "3-2": ("DIVERGENTE", 5),
    "2-2-1": ("DIVERGENTE", 5),
    "sem_evidencia": ("SEM_EVIDENCIA", 5),
    "trecho_inventado": ("CONVERGENTE", 3),
    "json_invalido": ("INDETERMINADO", 0),
}


@pytest.fixture
def lote_avaliado(docente, django_capture_on_commit_callbacks):
    lote = fabricas.lote_importado(docente)
    with django_capture_on_commit_callbacks(execute=True):
        rodada = criar_rodada(lote, docente, confirmar=True)
    return lote, rodada


def test_cada_roteiro_termina_no_estado_esperado(lote_avaliado):
    lote, rodada = lote_avaliado
    for cenario, (estado, validas) in ESPERADO.items():
        resposta = lote.respostas.get(texto__contains=f"[[cenario:{cenario}]]")
        consolidados = Consolidado.objects.filter(rodada=rodada, resposta=resposta)
        assert consolidados.count() == 4, cenario
        assert set(consolidados.values_list("estado", flat=True)) == {estado}, cenario
        assert set(consolidados.values_list("n_validas", flat=True)) == {validas}, cenario


def test_todo_par_elegivel_consolidado(lote_avaliado):
    lote, rodada = lote_avaliado
    pares = lote.respostas.exclude(aviso="LONGA").count() * 4
    assert Consolidado.objects.filter(rodada=rodada).count() == pares


def test_vazias_viram_sem_evidencia(lote_avaliado):
    lote, rodada = lote_avaliado
    estados = Consolidado.objects.filter(rodada=rodada, resposta__aviso="VAZIA").values_list(
        "estado", flat=True
    )
    assert set(estados) == {"SEM_EVIDENCIA"}


def test_fila_prioriza_nao_convergentes(lote_avaliado, api):
    lote, _ = lote_avaliado
    fila = api.get(f"/api/lotes/{lote.id}/fila/").json()
    itens = fila["respostas"]
    assert len(itens) == 40
    prioridades = [0 if i["estado_pior"] != "CONVERGENTE" else 1 for i in itens]
    assert prioridades == sorted(prioridades)
    assert itens[0]["estado_pior"] in {
        "INDETERMINADO",
        "DIVERGENTE",
        "SEM_EVIDENCIA",
        "INDISPONIVEL",
    }
    assert set(fila["contagem"]) <= {
        "CONVERGENTE",
        "DIVERGENTE",
        "SEM_EVIDENCIA",
        "INDETERMINADO",
        "INDISPONIVEL",
    }


def test_sugestao_divergente_sai_sem_nivel_sugerido(lote_avaliado, api):
    lote, _ = lote_avaliado
    resposta = lote.respostas.get(texto__contains="[[cenario:3-2]]")
    corpo = api.get(f"/api/respostas/{resposta.id}/sugestoes/").json()
    for s in corpo["criterios"]:
        assert s["estado"] == "DIVERGENTE"
        assert s["nivel_sugerido"] is None
        assert s["acordo"] == {"votos": 3, "validas": 5}
        assert [a["votos"] for a in s["alternativas"]] == [3, 2]
        for alternativa in s["alternativas"]:
            assert alternativa["justificativa"]
            for t in alternativa["trechos"]:
                assert resposta.texto[t["inicio"] : t["fim"]] == t["texto"]


def test_sugestao_convergente(lote_avaliado, api):
    lote, _ = lote_avaliado
    resposta = lote.respostas.get(texto__contains="[[cenario:4-1]]")
    s = api.get(f"/api/respostas/{resposta.id}/sugestoes/").json()["criterios"][0]
    assert s["estado"] == "CONVERGENTE"
    assert s["nivel_sugerido"]["codigo"] == "N2"
    assert s["acordo"] == {"votos": 4, "validas": 5}
    assert s["trechos"] and s["justificativa"]


def test_resposta_longa_indisponivel(lote_avaliado, api):
    lote, _ = lote_avaliado
    longa = lote.respostas.get(aviso="LONGA")
    corpo = api.get(f"/api/respostas/{longa.id}/sugestoes/").json()
    assert {s["estado"] for s in corpo["criterios"]} == {"INDISPONIVEL"}


def test_outra_docente_nao_ve_sugestoes(lote_avaliado, cliente, outra_docente):
    lote, _ = lote_avaliado
    resposta = lote.respostas.first()
    assert cliente(outra_docente).get(f"/api/respostas/{resposta.id}/sugestoes/").status_code == 404


def test_comando_recalcula_consolidados(lote_avaliado):
    from django.core.management import call_command

    lote, rodada = lote_avaliado
    Consolidado.objects.filter(rodada=rodada).delete()
    call_command("recalcular_consolidados", rodada=rodada.id)
    assert (
        Consolidado.objects.filter(rodada=rodada).count()
        == lote.respostas.exclude(aviso="LONGA").count() * 4
    )
