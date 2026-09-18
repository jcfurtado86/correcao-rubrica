import base64
import csv
import io

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from openpyxl import Workbook

from core.exceptions import ErroDeNegocio
from lotes.importacao import importar, ler_planilha, previa
from lotes.models import Resposta
from tests import fabricas

pytestmark = pytest.mark.django_db


def _csv(linhas, sep=",", bom=False):
    buf = io.StringIO()
    escritor = csv.writer(buf, delimiter=sep)
    for linha in linhas:
        escritor.writerow(linha)
    dados = buf.getvalue().encode("utf-8")
    if bom:
        dados = b"\xef\xbb\xbf" + dados
    return SimpleUploadedFile("respostas.csv", dados)


def _xlsx(linhas):
    livro = Workbook()
    for linha in linhas:
        livro.active.append(linha)
    buf = io.BytesIO()
    livro.save(buf)
    return SimpleUploadedFile("respostas.xlsx", buf.getvalue())


LINHAS = [
    ["Nome", "Email", "Resposta"],
    ["Débora", "d@x.org", "Texto um"],
    ["Igor", "i@x.org", "Dois"],
]


@pytest.mark.parametrize(
    "arquivo",
    [
        lambda: _csv(LINHAS, ","),
        lambda: _csv(LINHAS, ";"),
        lambda: _csv(LINHAS, ";", bom=True),
        lambda: _xlsx(LINHAS),
    ],
    ids=["csv-virgula", "csv-ponto-e-virgula", "csv-bom", "xlsx"],
)
def test_le_csv_e_xlsx(arquivo):
    colunas, linhas = ler_planilha(arquivo())
    assert colunas == ["Nome", "Email", "Resposta"]
    assert linhas[0] == {"Nome": "Débora", "Email": "d@x.org", "Resposta": "Texto um"}


def test_xlsx_com_numero_vira_texto_sem_ponto_zero():
    _, linhas = ler_planilha(_xlsx([["Mat", "R"], [2021123456, "a"]]))
    assert linhas[0]["Mat"] == "2021123456"


def test_recusa_arquivo_acima_de_10_mb(settings):
    grande = SimpleUploadedFile("x.csv", b"a," * (settings.LIMITE_UPLOAD_BYTES // 2 + 10))
    with pytest.raises(ErroDeNegocio) as erro:
        ler_planilha(grande)
    assert erro.value.codigo == "arquivo_grande"


def test_recusa_mais_de_1000_linhas():
    linhas = [["Nome", "R"]] + [[f"n{i}", "r"] for i in range(1001)]
    with pytest.raises(ErroDeNegocio) as erro:
        ler_planilha(_csv(linhas))
    assert erro.value.codigo == "linhas_demais"


def test_previa_nao_grava_nada(docente):
    r = previa(fabricas.arquivo_turma())
    assert r["total_linhas"] == 40
    assert len(r["amostra"]) == 5
    assert "Resposta 1" in r["colunas"]
    assert Resposta.objects.count() == 0


def test_importacao_da_turma_ficticia(docente):
    lote = fabricas.lote(docente)
    r = importar(
        lote,
        fabricas.arquivo_turma("xlsx"),
        "Resposta 1",
        fabricas.COLUNAS_ID,
        gerar_chave=True,
        semente=1,
    )
    assert r["n_respostas"] == 40
    tipos = sorted(a["tipo"] for a in r["avisos"])
    assert tipos.count("VAZIA") == 2 and tipos.count("LONGA") == 1 and tipos.count("DUPLICADA") == 2
    codigos = list(lote.respostas.order_by("codigo").values_list("codigo", flat=True))
    assert codigos == [f"R{i:03d}" for i in range(1, 41)]
    assert lote.respostas.filter(aviso="VAZIA").count() == 2
    assert lote.respostas.filter(aviso="LONGA").count() == 1


def test_codigos_nao_seguem_a_ordem_do_arquivo(docente):
    lote = fabricas.lote_importado(docente)
    _, linhas = ler_planilha(fabricas.arquivo_turma())
    textos_arquivo = [linha["Resposta 1"][:40] for linha in linhas[:10]]
    textos_por_codigo = [r.texto[:40] for r in lote.respostas.order_by("codigo")[:10]]
    assert textos_por_codigo != textos_arquivo


def test_chave_de_reidentificacao_so_na_resposta(docente):
    lote = fabricas.lote(docente)
    r = importar(lote, fabricas.arquivo_turma(), "Resposta 1", fabricas.COLUNAS_ID, True, semente=1)
    chave = r["chave_reidentificacao"]
    conteudo = base64.b64decode(chave["conteudo_base64"]).decode("utf-8")
    linhas = list(csv.reader(io.StringIO(conteudo)))
    assert linhas[0] == ["codigo", "identificador"]
    assert len(linhas) == 41
    assert " | " in linhas[1][1]
    assert chave["nome_arquivo"].startswith("chave-")
    # Nada da chave no retorno fora dela
    sem_chave = {k: v for k, v in r.items() if k != "chave_reidentificacao"}
    assert "@alunos.exemplo.edu.br" not in str(sem_chave)


def test_sem_chave_quando_nao_pedida(docente):
    lote = fabricas.lote(docente)
    r = importar(
        lote, fabricas.arquivo_turma(), "Resposta 1", fabricas.COLUNAS_ID, False, semente=1
    )
    assert r["chave_reidentificacao"] is None


def test_importacao_unica_por_lote(docente):
    lote = fabricas.lote_importado(docente)
    with pytest.raises(ErroDeNegocio) as erro:
        importar(lote, fabricas.arquivo_turma(), "Resposta 1", fabricas.COLUNAS_ID, False)
    assert erro.value.codigo == "ja_importado"


def test_coluna_de_resposta_inexistente(docente):
    lote = fabricas.lote(docente)
    with pytest.raises(ErroDeNegocio) as erro:
        importar(lote, fabricas.arquivo_turma(), "Nao existe", fabricas.COLUNAS_ID, False)
    assert erro.value.codigo == "coluna_invalida"


def test_exige_ao_menos_uma_coluna_de_identificacao(docente):
    lote = fabricas.lote(docente)
    with pytest.raises(ErroDeNegocio) as erro:
        importar(lote, fabricas.arquivo_turma(), "Resposta 1", [], False)
    assert erro.value.codigo == "coluna_invalida"
