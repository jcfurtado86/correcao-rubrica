import json

import pytest

from core.exceptions import ErroDeNegocio
from rubricas.modelo import exportar, importar
from tests import fabricas

pytestmark = pytest.mark.django_db


def test_ida_e_volta_preserva_a_rubrica(docente, outra_docente):
    original = fabricas.rubrica(docente)
    modelo = exportar(original.versao_vigente)
    copia = importar(outra_docente, json.loads(json.dumps(modelo)))
    assert copia.dono == outra_docente and copia.id != original.id
    assert exportar(copia.versao_vigente) == modelo
    assert copia.versao_vigente.numero == 1 and not copia.versao_vigente.congelada


def test_modelo_nao_carrega_dono_ids_nem_lotes(docente):
    modelo = exportar(fabricas.rubrica(docente).versao_vigente)
    texto = json.dumps(modelo)
    assert modelo["versao_formato"] == 1
    for proibido in ('"id"', '"dono"', '"lotes"', "docente@exemplo.org"):
        assert proibido not in texto
    assert set(modelo["criterios"][0]) == {"nome", "descricao", "peso", "tipo", "niveis"}
    assert set(modelo["criterios"][0]["niveis"][0]) == {"rotulo", "pontuacao", "descritor"}


def test_versao_de_formato_desconhecida_recusada(docente):
    modelo = exportar(fabricas.rubrica(docente).versao_vigente)
    modelo["versao_formato"] = 99
    with pytest.raises(ErroDeNegocio) as erro:
        importar(docente, modelo)
    assert erro.value.codigo == "modelo_invalido"


def test_modelo_invalido_recusado(docente):
    with pytest.raises(ErroDeNegocio):
        importar(docente, {"versao_formato": 1, "titulo": "x", "criterios": []})


def test_api_exportar_e_importar(api, cliente, outra_docente, docente):
    from django.core.files.uploadedfile import SimpleUploadedFile

    rubrica = fabricas.rubrica(docente)
    r = api.get(f"/api/rubricas/{rubrica.id}/modelo/")
    assert r.status_code == 200
    assert "attachment" in r["Content-Disposition"]
    arquivo = SimpleUploadedFile("modelo.json", r.content, content_type="application/json")
    r2 = cliente(outra_docente).post(
        "/api/rubricas/importar-modelo/", {"arquivo": arquivo}, format="multipart"
    )
    assert r2.status_code == 201, r2.content
    assert r2.json()["titulo"] == rubrica.titulo
    assert cliente(outra_docente).get(f"/api/rubricas/{rubrica.id}/modelo/").status_code == 404


def test_modelo_publico_do_repositorio_importa(docente):
    from pathlib import Path

    caminho = (
        Path(__file__).resolve().parents[3] / "docs" / "modelos" / "verificacao-validacao.json"
    )
    rubrica = importar(docente, json.loads(caminho.read_text(encoding="utf-8")))
    assert rubrica.versao_vigente.criterios.count() == 4
