from datetime import date
from decimal import Decimal

import pytest

from avaliacao.models import Execucao, Rodada
from avaliacao.sementes import semente
from avaliacao.services import criar_rodada, retomar
from conectores import precos
from conectores.duble import DubleLLMProvider
from conectores.llm import IAIndisponivel
from core.exceptions import ErroDeNegocio
from tests import fabricas

pytestmark = pytest.mark.django_db


def _rodar(lote, usuario, capturar, **kw):
    with capturar(execute=True):
        return criar_rodada(lote, usuario, confirmar=True, **kw)


def test_rodada_cria_n_execucoes_por_par_elegivel(docente, django_capture_on_commit_callbacks):
    lote = fabricas.lote_importado(docente)
    rodada = _rodar(lote, docente, django_capture_on_commit_callbacks)
    rodada.refresh_from_db()
    elegiveis = lote.respostas.exclude(aviso="LONGA").count()  # VAZIA gera execução sem chamada
    assert Execucao.objects.filter(rodada=rodada).count() == elegiveis * 4 * 5
    assert rodada.status == Rodada.Status.CONCLUIDA


def test_vazia_vira_sem_evidencia_sem_chamar_o_provedor(
    docente, django_capture_on_commit_callbacks
):
    lote = fabricas.lote_importado(docente)
    rodada = _rodar(lote, docente, django_capture_on_commit_callbacks)
    vazias = Execucao.objects.filter(rodada=rodada, resposta__aviso="VAZIA")
    assert vazias.count() == 2 * 4 * 5
    assert set(vazias.values_list("nivel_codigo", flat=True)) == {"SEM_EVIDENCIA"}
    assert all(vazias.values_list("valida", flat=True))
    textos_enviados = "".join(u for _, u in DubleLLMProvider.prompts_recebidos)
    assert "<<<\n\n>>>" not in textos_enviados
    n_chamadas = len(DubleLLMProvider.prompts_recebidos)
    assert n_chamadas == (lote.respostas.filter(aviso__isnull=True).count()) * 4 * 5


def test_longa_nao_gera_execucao(docente, django_capture_on_commit_callbacks):
    lote = fabricas.lote_importado(docente)
    rodada = _rodar(lote, docente, django_capture_on_commit_callbacks)
    assert not Execucao.objects.filter(rodada=rodada, resposta__aviso="LONGA").exists()


def test_execucoes_validas_tem_trecho_localizado(docente, django_capture_on_commit_callbacks):
    lote = fabricas.lote_importado(docente)
    rodada = _rodar(lote, docente, django_capture_on_commit_callbacks)
    validas = Execucao.objects.filter(rodada=rodada, valida=True).exclude(
        nivel_codigo="SEM_EVIDENCIA"
    )
    assert validas.exists()
    for ex in validas.prefetch_related("trechos")[:50]:
        for t in ex.trechos.all():
            assert t.localizado
            assert ex.resposta.texto[t.inicio : t.fim]


def test_trecho_inventado_e_json_invalido(docente, django_capture_on_commit_callbacks):
    lote = fabricas.lote_importado(docente)
    rodada = _rodar(lote, docente, django_capture_on_commit_callbacks)
    inventado = lote.respostas.get(texto__contains="[[cenario:trecho_inventado]]")
    invalidas = Execucao.objects.filter(rodada=rodada, resposta=inventado, valida=False)
    assert set(invalidas.values_list("motivo_invalidez", flat=True)) == {"TRECHO_NAO_LOCALIZADO"}
    assert invalidas.count() == 2 * 4
    quebrado = lote.respostas.get(texto__contains="[[cenario:json_invalido]]")
    motivos = Execucao.objects.filter(rodada=rodada, resposta=quebrado).values_list(
        "motivo_invalidez", flat=True
    )
    assert set(motivos) == {"JSON_INVALIDO"}


def test_falha_passageira_em_todas_as_tentativas_vira_falhou(
    docente, django_capture_on_commit_callbacks, monkeypatch, settings
):
    settings.LLM_MAX_TENTATIVAS = 2
    chamadas = {"n": 0}

    def sempre_503(self, *a, **kw):
        chamadas["n"] += 1
        raise IAIndisponivel("Gemini 503: UNAVAILABLE")

    monkeypatch.setattr(DubleLLMProvider, "avaliar", sempre_503)
    lote = fabricas.lote(docente)
    from lotes.models import Resposta

    Resposta.objects.create(lote=lote, codigo="R001", texto="Uma resposta qualquer com texto.")
    rodada = _rodar(lote, docente, django_capture_on_commit_callbacks)
    rodada.refresh_from_db()
    execucoes = Execucao.objects.filter(rodada=rodada)
    assert set(execucoes.values_list("status", flat=True)) == {"FALHOU"}
    assert all("503" in e for e in execucoes.values_list("erro", flat=True))
    assert chamadas["n"] == execucoes.count() * 3  # 1 tentativa + 2 novas
    assert rodada.status == Rodada.Status.COM_FALHAS
    assert rodada.custo_acumulado_usd == 0


def _preco_do_duble(monkeypatch):
    monkeypatch.setattr(
        precos,
        "TABELA",
        precos.TABELA + [("dublê", date(2001, 1, 1), Decimal("1000"), Decimal("1000"))],
    )


def test_teto_pausa_e_retomar_conclui_sem_refazer(
    docente, django_capture_on_commit_callbacks, monkeypatch
):
    _preco_do_duble(monkeypatch)
    lote = fabricas.lote(docente)
    from lotes.models import Resposta

    for i in range(3):
        Resposta.objects.create(
            lote=lote, codigo=f"R{i + 1:03d}", texto=f"Resposta número {i} com texto."
        )
    rodada = _rodar(lote, docente, django_capture_on_commit_callbacks, teto_usd=Decimal("2"))
    rodada.refresh_from_db()
    assert rodada.status == Rodada.Status.PAUSADA_TETO
    concluidas = Execucao.objects.filter(rodada=rodada, status="CONCLUIDA").count()
    pendentes = Execucao.objects.filter(rodada=rodada, status="PENDENTE").count()
    assert concluidas > 0 and pendentes > 0
    assert rodada.custo_acumulado_usd <= Decimal("2")

    chamadas_antes = len(DubleLLMProvider.prompts_recebidos)
    with django_capture_on_commit_callbacks(execute=True):
        retomar(rodada, teto_usd=Decimal("1000"))
    rodada.refresh_from_db()
    assert rodada.status == Rodada.Status.CONCLUIDA
    assert len(DubleLLMProvider.prompts_recebidos) - chamadas_antes == pendentes


def test_lote_real_com_gemini_exige_nivel_pago(docente, settings):
    settings.GEMINI_PAID_TIER = False
    lote = fabricas.lote(
        docente, sintetico=False, provedor_llm="gemini", modelo_llm="gemini-3.6-flash"
    )
    with pytest.raises(ErroDeNegocio) as erro:
        criar_rodada(lote, docente, confirmar=True)
    assert erro.value.codigo == "nivel_gratuito"


def test_sem_confirmacao_recusa(docente):
    lote = fabricas.lote_importado(docente)
    with pytest.raises(ErroDeNegocio) as erro:
        criar_rodada(lote, docente, confirmar=False)
    assert erro.value.codigo == "confirmacao_necessaria"


def test_reaplicacao_exige_rodada_1_concluida(docente):
    lote = fabricas.lote_importado(docente)
    with pytest.raises(ErroDeNegocio) as erro:
        criar_rodada(lote, docente, confirmar=True, reaplicacao=True)
    assert erro.value.codigo == "sem_rodada_concluida"


def test_sementes_distintas_por_indice_e_reproduziveis(docente, django_capture_on_commit_callbacks):
    lote = fabricas.lote_importado(docente)
    rodada = _rodar(lote, docente, django_capture_on_commit_callbacks)
    ex = Execucao.objects.filter(rodada=rodada, resposta__aviso__isnull=True).first()
    irmas = Execucao.objects.filter(rodada=rodada, resposta=ex.resposta, criterio=ex.criterio)
    sementes = list(irmas.values_list("semente", flat=True))
    assert len(set(sementes)) == 5
    for e in irmas:
        assert e.semente == semente(rodada.semente_base, e.resposta_id, e.criterio_id, e.indice)


def test_confirmar_rodada_congela_rubrica_e_lote(docente, django_capture_on_commit_callbacks):
    lote = fabricas.lote_importado(docente)
    _rodar(lote, docente, django_capture_on_commit_callbacks)
    lote.versao_rubrica.refresh_from_db()
    assert lote.versao_rubrica.congelada
    assert len(lote.versao_rubrica.hash) == 64


def test_retomar_recupera_execucao_abandonada_e_ignora_duplicata(
    docente, django_capture_on_commit_callbacks, settings
):
    from datetime import timedelta

    from django.utils import timezone

    from avaliacao.services import processar_execucao
    from lotes.models import Resposta

    lote = fabricas.lote(docente)
    Resposta.objects.create(lote=lote, codigo="R001", texto="Uma resposta qualquer com texto.")
    with django_capture_on_commit_callbacks(execute=False):
        rodada = criar_rodada(lote, docente, confirmar=True)
    execucoes = list(Execucao.objects.filter(rodada=rodada))
    # Simula worker que caiu no meio de uma execução há mais de 10 min.
    abandonada = execucoes[0]
    abandonada.status = Execucao.Status.EM_ANDAMENTO
    abandonada.iniciada_em = timezone.now() - timedelta(
        seconds=settings.EXECUCAO_ABANDONADA_APOS_S + 5
    )
    abandonada.save()
    # E outra que está mesmo em andamento agora (não pode ser tocada).
    viva = execucoes[1]
    viva.status = Execucao.Status.EM_ANDAMENTO
    viva.iniciada_em = timezone.now()
    viva.save()

    with django_capture_on_commit_callbacks(execute=True):
        retomar(rodada)
    abandonada.refresh_from_db()
    viva.refresh_from_db()
    assert abandonada.status == Execucao.Status.CONCLUIDA
    assert viva.status == Execucao.Status.EM_ANDAMENTO
    # Mensagem duplicada na fila não gera nova chamada.
    antes = len(DubleLLMProvider.prompts_recebidos)
    assert processar_execucao(abandonada.id) == "PULAR"
    assert len(DubleLLMProvider.prompts_recebidos) == antes
