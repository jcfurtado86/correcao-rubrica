"""US4: painel, reaplicação e exportação reproduzível (quickstart V6, SC-006)."""

import io
import json
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

from avaliacao.services import criar_rodada
from revisao.services import abrir_sessao, registrar_decisao
from tests import fabricas

pytestmark = pytest.mark.django_db
RAIZ = Path(__file__).resolve().parents[3]
SCRIPT = RAIZ / "analysis" / "reproduzir_metricas.py"

ARQUIVOS = {
    "metadados.json",
    "respostas.csv",
    "execucoes.csv",
    "consolidados.csv",
    "decisoes.csv",
    "sessoes.csv",
    "metricas.json",
}
COLUNAS = {
    "execucoes.csv": "rodada,codigo,criterio,indice,semente,status,valida,motivo_invalidez,"
    "nivel_codigo,nivel_ordem,n_trechos,n_trechos_localizados,tokens_entrada,tokens_saida,"
    "tokens_raciocinio,custo_usd,latencia_ms,tentativas",
    "consolidados.csv": "rodada,codigo,criterio,estado,modal_codigo,nivel_modal_ordem,acordo,"
    "n_validas,distribuicao_json,limiar_usado",
    "decisoes.csv": "decisao_id,docente,dono_do_lote,participante,codigo,criterio,condicao,"
    "estado_exibido,nivel_sugerido_ordem,nivel_decidido_ordem,tipo,tem_motivo,tempo_ativo_ms,"
    "vigente,substitui,instante",
    "sessoes.csv": "sessao_id,docente,dono_do_lote,participante,codigo,condicao,rodada,"
    "tempo_ativo_ms,n_decisoes,aberta_em",
    "respostas.csv": "codigo,n_caracteres,n_substituicoes,aviso,metade",
}


@pytest.fixture
def lote_completo(docente, django_capture_on_commit_callbacks):
    lote = fabricas.lote_importado(docente)
    with django_capture_on_commit_callbacks(execute=True):
        criar_rodada(lote, docente, confirmar=True)
    with django_capture_on_commit_callbacks(execute=True):
        criar_rodada(lote, docente, confirmar=True, reaplicacao=True)
    criterios = list(lote.versao_rubrica.criterios.order_by("ordem"))
    for i, resposta in enumerate(lote.respostas.order_by("codigo")[:12]):
        sessao, _ = abrir_sessao(docente, resposta)
        for j, c in enumerate(criterios):
            nivel = c.niveis.get(ordem=1 + (i + j) % 4)
            registrar_decisao(sessao, c.id, nivel.id, "motivo" if j == 0 else "", 1000 * (i + 1))
    return lote


def test_painel_tem_as_metricas_por_criterio(lote_completo, api):
    r = api.get(f"/api/lotes/{lote_completo.id}/painel/")
    assert r.status_code == 200
    painel = r.json()
    assert painel["rodada"] == 1 and painel["rodadas"] == [1, 2]
    assert len(painel["criterios"]) == 4
    c = painel["criterios"][0]
    for chave in (
        "estados",
        "taxa_divergencia",
        "taxa_nao_convergente",
        "acordo_medio",
        "fleiss",
        "concordancia",
        "seletiva",
        "estabilidade",
        "distribuicao_decidida",
    ):
        assert chave in c, chave
    assert {"n", "exata", "adjacente", "qwk"} <= set(c["concordancia"])
    assert c["concordancia"]["n"] > 0
    assert c["estabilidade"]["n"] > 0
    assert set(painel["por_tipo"]) == {"OBJETIVO", "INTERPRETATIVO"}
    assert painel["tempo"]["n_respostas"] == 12


def test_limiar_recalcula_sem_gravar(lote_completo, api):
    from avaliacao.models import Consolidado

    antes = list(Consolidado.objects.values_list("estado", flat=True).order_by("id"))
    p08 = api.get(f"/api/lotes/{lote_completo.id}/painel/").json()
    p06 = api.get(f"/api/lotes/{lote_completo.id}/painel/?limiar=0.6").json()
    assert p06["limiar"] == 0.6 and p06["recalculado"] is True
    assert p06["total"]["estados"].get("DIVERGENTE", 0) < p08["total"]["estados"].get(
        "DIVERGENTE", 0
    )
    assert list(Consolidado.objects.values_list("estado", flat=True).order_by("id")) == antes


def test_exportacao_e_reproducao_independente(lote_completo, api, tmp_path):
    r = api.get(f"/api/lotes/{lote_completo.id}/exportacao.zip")
    assert r.status_code == 200 and r["Content-Type"] == "application/zip"
    conteudo = b"".join(r.streaming_content) if r.streaming else r.content
    arquivo = tmp_path / "exportacao.zip"
    arquivo.write_bytes(conteudo)
    with zipfile.ZipFile(io.BytesIO(conteudo)) as z:
        assert ARQUIVOS <= set(z.namelist())
        for nome, colunas in COLUNAS.items():
            assert z.read(nome).decode("utf-8").splitlines()[0] == colunas, nome
        texto = z.read("respostas.csv").decode("utf-8") + z.read("decisoes.csv").decode("utf-8")
        assert "motivo" not in z.read("decisoes.csv").decode("utf-8").splitlines()[1]
        metadados = json.loads(z.read("metadados.json"))
        assert metadados["rubrica"]["hash"] and len(metadados["rodadas"]) == 2
    # nada identificável: nem e-mail de docente, nem texto de resposta sem pedir
    assert "@" not in texto
    saida = subprocess.run(
        [sys.executable, str(SCRIPT), str(arquivo)], capture_output=True, text=True, timeout=120
    )
    assert saida.returncode == 0, saida.stdout + saida.stderr
    assert "OK: 0 divergências" in saida.stdout


def test_exportacao_com_texto_e_motivos_so_quando_pedido(lote_completo, api):
    r = api.get(f"/api/lotes/{lote_completo.id}/exportacao.zip?incluir_texto=1&incluir_motivos=1")
    conteudo = b"".join(r.streaming_content) if r.streaming else r.content
    with zipfile.ZipFile(io.BytesIO(conteudo)) as z:
        assert z.read("respostas.csv").decode("utf-8").splitlines()[0].endswith(",texto")
        assert z.read("decisoes.csv").decode("utf-8").splitlines()[0].endswith(",motivo")


def test_outra_docente_nao_ve_painel(lote_completo, cliente, outra_docente):
    assert cliente(outra_docente).get(f"/api/lotes/{lote_completo.id}/painel/").status_code == 404
