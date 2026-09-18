"""SC-003: nenhum identificador plantado sobrevive à carga (banco, logs, prompts)."""

import logging

import pytest

from avaliacao.services import criar_rodada
from conectores.duble import DubleLLMProvider
from lotes.auditoria import procurar_identificadores
from tests import fabricas

pytestmark = pytest.mark.django_db


def test_nenhum_identificador_no_banco_nos_logs_nem_nos_prompts(
    docente, django_capture_on_commit_callbacks, caplog
):
    caplog.set_level(logging.DEBUG)
    lote = fabricas.lote_importado(docente, sintetico=False)
    with django_capture_on_commit_callbacks(execute=True):
        criar_rodada(lote, docente, confirmar=True)

    plantados = fabricas.identificadores_plantados()
    assert len(plantados) > 100

    no_banco = procurar_identificadores(plantados)
    assert no_banco == {}, f"identificadores no banco: {no_banco}"

    nos_logs = procurar_identificadores(plantados, textos={"logs": [caplog.text]})
    assert nos_logs == {}

    prompts = [s + "\n" + u for s, u in DubleLLMProvider.prompts_recebidos]
    assert len(prompts) > 0
    nos_prompts = procurar_identificadores(plantados, textos={"prompts": prompts})
    assert nos_prompts == {}


def test_auditoria_encontra_identificador_quando_ele_existe(docente):
    from lotes.models import Resposta

    lote = fabricas.lote(docente)
    Resposta.objects.create(lote=lote, codigo="R001", texto="Meu nome é Péricles Vasconcelos.")
    achados = procurar_identificadores(["Péricles", "Vasconcelos"])
    assert achados == {"lotes.Resposta.texto": 2}
