import logging

import pytest
from django.core.management import call_command

from core.logs import FiltroSemTexto
from rubricas.models import Rubrica


def _registro(**extras):
    r = logging.LogRecord("x", logging.INFO, __file__, 1, "mensagem %s", ("curta",), None)
    for k, v in extras.items():
        setattr(r, k, v)
    return r


def test_filtro_remove_campos_de_texto_de_estudante():
    r = _registro(texto="Sou Fulano, matrícula 2021", justificativa="…", resposta_bruta="{…}")
    assert FiltroSemTexto().filter(r)
    assert r.texto == r.justificativa == r.resposta_bruta == "[removido]"


def test_filtro_trunca_mensagem_longa():
    r = logging.LogRecord("x", logging.INFO, __file__, 1, "a" * 2000, (), None)
    FiltroSemTexto().filter(r)
    assert len(r.getMessage()) < 600 and r.getMessage().endswith("[truncado]")


@pytest.mark.django_db
def test_carregar_exemplo_cria_rubrica_para_o_superusuario(django_user_model):
    su = django_user_model.objects.create_superuser("admin@exemplo.org", "Senha#Forte2026")
    call_command("carregar_exemplo")
    rubrica = Rubrica.objects.get(dono=su)
    assert rubrica.versao_vigente.criterios.count() == 4
    tipos = sorted(rubrica.versao_vigente.criterios.values_list("tipo", flat=True))
    assert tipos == ["INTERPRETATIVO", "INTERPRETATIVO", "OBJETIVO", "OBJETIVO"]
