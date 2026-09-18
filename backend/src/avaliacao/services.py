"""Rodadas de pré-avaliação: criação, execução, retomada e status (FR-008–FR-014).

Custo: antes de cada chamada o worker **reserva** o custo previsto por chamada
com um UPDATE condicional (`acumulado + previsto <= teto`). Se a reserva falha, a
rodada pausa e a execução fica PENDENTE, retomável depois de elevar o teto.
Terminada a chamada, o acumulado é ajustado pelo custo real.

Cache: a unidade é a rodada. Execução CONCLUIDA nunca é refeita; retomar só
reenfileira PENDENTE e FALHOU (FR-011). Reaplicação é rodada nova (FR-022).
"""

import secrets
from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.db import IntegrityError, transaction
from django.db.models import Count, F, Max, Q, prefetch_related_objects
from django.utils import timezone

from avaliacao import prompt
from avaliacao.consolidacao import consolidar
from avaliacao.estimativa import estimar
from avaliacao.models import Consolidado, Execucao, Rodada, Trecho
from avaliacao.sementes import semente
from avaliacao.validacao import SEM_EVIDENCIA, validar
from conectores.llm import ErroLLM, IAIndisponivel, get_llm
from conectores.precos import custo_usd
from core.exceptions import ErroDeNegocio
from lotes.models import Lote, Resposta
from rubricas.services import congelar

OK, RETENTAR, FALHOU, PULAR, PAUSADA = "OK", "RETENTAR", "FALHOU", "PULAR", "PAUSADA"
FINALIZADAS = (Rodada.Status.CONCLUIDA, Rodada.Status.COM_FALHAS)


def rodada_de_referencia(lote: Lote) -> Rodada | None:
    """A rodada cujas sugestões são mostradas: a última finalizada (ou a última)."""
    rodadas = lote.rodadas.order_by("-numero")
    return rodadas.filter(status__in=FINALIZADAS).first() or rodadas.first()


def exigir_nivel_pago(lote: Lote) -> None:
    """Dado real só vai ao Google com chave paga (research R9, decisão do orientador)."""
    if lote.provedor_llm != "dumb" and not lote.sintetico and not settings.GEMINI_PAID_TIER:
        raise ErroDeNegocio(
            "Lote com respostas reais só pode ser pré-avaliado com chave de projeto com "
            "faturamento (GEMINI_PAID_TIER=true). O nível gratuito não é usado.",
            codigo="nivel_gratuito",
        )


def enfileirar(ids: list[int]) -> None:
    from avaliacao.tasks import executar_execucao

    for execucao_id in ids:
        executar_execucao.delay(execucao_id)


@transaction.atomic
def criar_rodada(
    lote: Lote,
    usuario,
    reaplicacao: bool = False,
    confirmar: bool = False,
    teto_usd: Decimal | None = None,
) -> Rodada:
    if not confirmar:
        raise ErroDeNegocio(
            "Confirme a estimativa de custo para executar.", codigo="confirmacao_necessaria"
        )
    exigir_nivel_pago(lote)
    lote = Lote.objects.select_for_update().get(pk=lote.pk)
    anteriores = lote.rodadas.all()
    if reaplicacao:
        if not anteriores.filter(numero=1, status__in=FINALIZADAS).exists():
            raise ErroDeNegocio(
                "A reaplicação exige a rodada 1 concluída.", codigo="sem_rodada_concluida"
            )
    elif anteriores.exists():
        raise ErroDeNegocio(
            "Este lote já foi pré-avaliado; use a reaplicação.",
            codigo="rodada_existente",
            status_code=409,
        )
    if not lote.respostas.exists():
        raise ErroDeNegocio("O lote não tem respostas.", codigo="sem_respostas")

    congelar(lote.versao_rubrica)
    estimativa = estimar(lote)
    numero = (anteriores.aggregate(m=Max("numero"))["m"] or 0) + 1
    rodada = Rodada.objects.create(
        lote=lote,
        numero=numero,
        semente_base=secrets.randbelow(2**31),
        versao_prompt=prompt.VERSAO_PROMPT,
        provedor=lote.provedor_llm,
        modelo=lote.modelo_llm,
        custo_estimado_usd=Decimal(str(estimativa["custo_estimado_usd"])),
        custo_previsto_chamada_usd=estimativa["custo_previsto_chamada_usd"],
        teto_usd=teto_usd if teto_usd is not None else lote.teto_usd,
        confirmada_por=usuario,
        status=Rodada.Status.EM_EXECUCAO,
    )

    criterios = list(lote.versao_rubrica.criterios.all())
    agora = timezone.now()
    novas = []
    for resposta in lote.respostas.exclude(aviso=Resposta.Aviso.LONGA):
        vazia = resposta.aviso == Resposta.Aviso.VAZIA
        for criterio in criterios:
            for indice in range(1, lote.n_execucoes + 1):
                execucao = Execucao(
                    rodada=rodada,
                    resposta=resposta,
                    criterio=criterio,
                    indice=indice,
                    semente=semente(rodada.semente_base, resposta.id, criterio.id, indice),
                )
                if vazia:
                    # Resposta vazia: "sem evidência" sem chamar o modelo.
                    execucao.status = Execucao.Status.CONCLUIDA
                    execucao.valida = True
                    execucao.nivel_codigo = SEM_EVIDENCIA
                    execucao.justificativa = "Resposta vazia."
                    execucao.concluida_em = agora
                novas.append(execucao)
    Execucao.objects.bulk_create(novas, batch_size=1000)
    _apos_criar_execucoes(rodada)

    pendentes = list(
        rodada.execucoes.filter(status=Execucao.Status.PENDENTE).values_list("id", flat=True)
    )
    transaction.on_commit(lambda: enfileirar(pendentes))
    if not pendentes:
        atualizar_status_rodada(rodada)
    return rodada


def _apos_criar_execucoes(rodada: Rodada) -> None:
    """Consolida os pares que já nascem concluídos (respostas vazias)."""
    pares = (
        rodada.execucoes.filter(resposta__aviso=Resposta.Aviso.VAZIA)
        .values_list("resposta_id", "criterio_id")
        .distinct()
    )
    for resposta_id, criterio_id in pares:
        recalcular_consolidado(rodada, resposta_id, criterio_id)


def _apos_concluir(execucao: Execucao) -> None:
    recalcular_consolidado(execucao.rodada, execucao.resposta_id, execucao.criterio_id)


def recalcular_consolidado(rodada: Rodada, resposta_id: int, criterio_id: int):
    """Consolida o par se todas as execuções dele saíram da fila (FR-014).

    Cada worker verifica depois de gravar a própria execução: o último a
    terminar sempre enxerga as demais concluídas e consolida.
    """
    execucoes = Execucao.objects.filter(
        rodada=rodada, resposta_id=resposta_id, criterio_id=criterio_id
    )
    if execucoes.filter(
        status__in=[Execucao.Status.PENDENTE, Execucao.Status.EM_ANDAMENTO]
    ).exists():
        return None
    lote = rodada.lote
    votos = list(
        execucoes.filter(status=Execucao.Status.CONCLUIDA, valida=True).values_list(
            "indice", "nivel_codigo"
        )
    )
    r = consolidar(votos, lote.limiar_acordo, lote.min_validas)
    nivel_modal = (
        Execucao.objects.filter(
            rodada=rodada,
            resposta_id=resposta_id,
            criterio_id=criterio_id,
            nivel_codigo=r.modal,
            nivel__isnull=False,
        )
        .values_list("nivel_id", flat=True)
        .first()
        if r.modal
        else None
    )
    campos = {
        "estado": r.estado,
        "modal_codigo": r.modal or "",
        "nivel_modal_id": nivel_modal,
        "acordo": r.acordo,
        "n_validas": r.n_validas,
        "distribuicao": r.distribuicao,
        "limiar_usado": lote.limiar_acordo,
        "min_validas_usado": lote.min_validas,
    }
    chave = {"rodada": rodada, "resposta_id": resposta_id, "criterio_id": criterio_id}
    try:
        with transaction.atomic():
            consolidado, _ = Consolidado.objects.update_or_create(**chave, defaults=campos)
    except IntegrityError:
        # Dois workers consolidando o mesmo par ao mesmo tempo: o segundo atualiza.
        Consolidado.objects.filter(**chave).update(**campos)
        consolidado = Consolidado.objects.get(**chave)
    return consolidado


def recalcular_rodada(rodada: Rodada) -> int:
    pares = rodada.execucoes.values_list("resposta_id", "criterio_id").distinct()
    return sum(1 for r, c in pares if recalcular_consolidado(rodada, r, c) is not None)


def _limite_de_abandono():
    return timezone.now() - timedelta(seconds=settings.EXECUCAO_ABANDONADA_APOS_S)


@transaction.atomic
def retomar(rodada: Rodada, teto_usd: Decimal | None = None) -> Rodada:
    """Reenfileira PENDENTE e FALHOU, e recupera EM_ANDAMENTO abandonada.

    Seguro repetir: a tarefa ignora execução que não esteja PENDENTE, então
    mensagem duplicada na fila não gera chamada duplicada.
    """
    rodada = Rodada.objects.select_for_update().get(pk=rodada.pk)
    if teto_usd is not None:
        rodada.teto_usd = teto_usd
    rodada.execucoes.filter(status=Execucao.Status.FALHOU).update(
        status=Execucao.Status.PENDENTE, tentativas=0, erro=None
    )
    rodada.execucoes.filter(
        status=Execucao.Status.EM_ANDAMENTO, iniciada_em__lt=_limite_de_abandono()
    ).update(status=Execucao.Status.PENDENTE, iniciada_em=None)
    rodada.status = Rodada.Status.EM_EXECUCAO
    rodada.concluida_em = None
    rodada.save(update_fields=["teto_usd", "status", "concluida_em"])
    pendentes = list(
        rodada.execucoes.filter(status=Execucao.Status.PENDENTE).values_list("id", flat=True)
    )
    transaction.on_commit(lambda: enfileirar(pendentes))
    if not pendentes:
        atualizar_status_rodada(rodada)
    return rodada


def progresso(rodada: Rodada) -> dict:
    c = rodada.execucoes.aggregate(
        total=Count("id"),
        pendentes=Count(
            "id",
            filter=Q(status__in=[Execucao.Status.PENDENTE, Execucao.Status.EM_ANDAMENTO]),
        ),
        concluidas=Count("id", filter=Q(status=Execucao.Status.CONCLUIDA)),
        invalidas=Count("id", filter=Q(status=Execucao.Status.CONCLUIDA, valida=False)),
        falhas=Count("id", filter=Q(status=Execucao.Status.FALHOU)),
    )
    return c


def atualizar_status_rodada(rodada: Rodada) -> None:
    execucoes = Execucao.objects.filter(rodada_id=rodada.pk)
    if execucoes.filter(
        status__in=[Execucao.Status.PENDENTE, Execucao.Status.EM_ANDAMENTO]
    ).exists():
        return
    falhas = execucoes.filter(status=Execucao.Status.FALHOU).exists()
    final = Rodada.Status.COM_FALHAS if falhas else Rodada.Status.CONCLUIDA
    Rodada.objects.filter(pk=rodada.pk).exclude(status=final).update(
        status=final, concluida_em=timezone.now()
    )


def _reservar(rodada_id: int, previsto: Decimal) -> bool:
    return bool(
        Rodada.objects.filter(
            pk=rodada_id, custo_acumulado_usd__lte=F("teto_usd") - previsto
        ).update(custo_acumulado_usd=F("custo_acumulado_usd") + previsto)
    )


def _ajustar(rodada_id: int, diferenca: Decimal) -> None:
    if not diferenca:
        return
    Rodada.objects.filter(pk=rodada_id).update(
        custo_acumulado_usd=F("custo_acumulado_usd") + diferenca
    )


def processar_execucao(execucao_id: int, tentativa: int = 0) -> str:
    """Executa uma avaliação. Devolve OK, RETENTAR, FALHOU, PULAR ou PAUSADA."""
    with transaction.atomic():
        execucao = (
            Execucao.objects.select_for_update(of=("self",))
            .select_related("rodada", "rodada__lote", "resposta", "criterio")
            .get(pk=execucao_id)
        )
        abandonada = (
            execucao.status == Execucao.Status.EM_ANDAMENTO
            and execucao.iniciada_em is not None
            and execucao.iniciada_em < _limite_de_abandono()
        )
        if execucao.status != Execucao.Status.PENDENTE and not abandonada:
            return PULAR
        rodada = execucao.rodada
        previsto = rodada.custo_previsto_chamada_usd
        if not _reservar(rodada.pk, previsto):
            Rodada.objects.filter(pk=rodada.pk, status=Rodada.Status.EM_EXECUCAO).update(
                status=Rodada.Status.PAUSADA_TETO
            )
            return PAUSADA
        execucao.status = Execucao.Status.EM_ANDAMENTO
        execucao.tentativas += 1
        execucao.iniciada_em = timezone.now()
        execucao.save(update_fields=["status", "tentativas", "iniciada_em"])

    criterio = execucao.criterio
    prefetch_related_objects([criterio], "niveis")
    sistema, usuario = prompt.montar(
        rodada.lote.enunciado, criterio, execucao.resposta.texto, rodada.versao_prompt
    )
    try:
        resultado = get_llm(rodada.provedor, rodada.modelo).avaliar(
            sistema, usuario, prompt.esquema(criterio), execucao.semente, execucao.indice
        )
    except (IAIndisponivel, ErroLLM) as exc:
        _ajustar(rodada.pk, -previsto)
        execucao.erro = str(exc)[:1000]
        passageira = isinstance(exc, IAIndisponivel)
        if passageira and tentativa < settings.LLM_MAX_TENTATIVAS:
            execucao.status = Execucao.Status.PENDENTE
            execucao.save(update_fields=["status", "erro"])
            return RETENTAR
        execucao.status = Execucao.Status.FALHOU
        execucao.save(update_fields=["status", "erro"])
        _apos_concluir(execucao)
        atualizar_status_rodada(rodada)
        return FALHOU

    verificacao = validar(execucao.resposta.texto, resultado.texto, prompt.codigos(criterio))
    real = custo_usd(
        rodada.modelo,
        resultado.tokens_entrada,
        resultado.tokens_saida + resultado.tokens_raciocinio,
    )
    niveis = {n.codigo: n for n in criterio.niveis.all()}
    with transaction.atomic():
        _ajustar(rodada.pk, real - previsto)
        execucao.status = Execucao.Status.CONCLUIDA
        execucao.valida = verificacao.valida
        execucao.motivo_invalidez = verificacao.motivo_invalidez
        execucao.nivel_codigo = verificacao.nivel_codigo
        execucao.nivel = niveis.get(verificacao.nivel_codigo)
        execucao.justificativa = verificacao.justificativa
        execucao.resposta_bruta = resultado.texto
        execucao.tokens_entrada = resultado.tokens_entrada
        execucao.tokens_saida = resultado.tokens_saida
        execucao.tokens_raciocinio = resultado.tokens_raciocinio
        execucao.custo_usd = real
        execucao.latencia_ms = resultado.latencia_ms
        execucao.erro = None
        execucao.concluida_em = timezone.now()
        execucao.save()
        Trecho.objects.bulk_create(
            Trecho(
                execucao=execucao,
                texto_citado=t.texto_citado,
                localizado=t.localizado,
                inicio=t.inicio,
                fim=t.fim,
            )
            for t in verificacao.trechos
        )
    _apos_concluir(execucao)
    atualizar_status_rodada(rodada)
    return OK
