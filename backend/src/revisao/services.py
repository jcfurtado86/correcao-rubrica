"""Sessão de correção e decisão docente (FR-017–FR-020, Princípio I).

Não existe operação que decida vários critérios ou várias respostas de uma vez
(FR-018): cada chamada registra uma decisão, numa sessão aberta daquela resposta.
"""

from decimal import Decimal

from django.db import transaction

from avaliacao.models import Consolidado
from avaliacao.services import rodada_de_referencia
from avaliacao.sugestao import INDISPONIVEL, SEM_APOIO, sugestoes_da_resposta
from core.exceptions import ErroDeNegocio
from revisao.models import Condicao, Decisao, SessaoCorrecao
from rubricas.models import Criterio, Nivel


def _vigentes(resposta, docente, participacao=None):
    filtro = {"resposta": resposta, "docente": docente, "vigente": True}
    if hasattr(Decisao, "participacao"):
        filtro["participacao"] = participacao
    return Decisao.objects.filter(**filtro)


def decisao_json(d: Decisao) -> dict:
    return {
        "id": d.id,
        "criterio": d.criterio_id,
        "nivel": d.nivel_id,
        "nivel_codigo": d.nivel.codigo,
        "tipo": d.tipo,
        "estado_exibido": d.estado_exibido,
        "nivel_sugerido": d.nivel_sugerido_id,
        "motivo": d.motivo,
        "tempo_ativo_ms": d.tempo_ativo_ms,
        "vigente": d.vigente,
        "substitui": d.substitui_id,
        "criado_em": d.criado_em,
    }


def abrir_sessao(docente, resposta, condicao=Condicao.COM_APOIO, participacao=None):
    """Abre a sessão e devolve (sessão, conteúdo para a tela)."""
    rodada = rodada_de_referencia(resposta.lote) if condicao == Condicao.COM_APOIO else None
    extras = {"participacao": participacao} if hasattr(SessaoCorrecao, "participacao") else {}
    sessao = SessaoCorrecao.objects.create(
        docente=docente, resposta=resposta, condicao=condicao, rodada=rodada, **extras
    )
    vigentes = _vigentes(resposta, docente, participacao).select_related("nivel")
    return sessao, {
        "sessao": sessao.id,
        "resposta": resposta.id,
        "codigo": resposta.codigo,
        "texto": resposta.texto,
        "aviso": resposta.aviso,
        "condicao": condicao,
        "rodada": rodada.numero if rodada else None,
        "criterios": sugestoes_da_resposta(resposta, rodada, condicao),
        "decisoes_vigentes": [decisao_json(d) for d in vigentes],
    }


def _o_que_foi_exibido(sessao: SessaoCorrecao, criterio: Criterio):
    if sessao.condicao == SEM_APOIO:
        return Decisao.EstadoExibido.OCULTO, None
    if sessao.rodada is None:
        return INDISPONIVEL, None
    consolidado = Consolidado.objects.filter(
        rodada=sessao.rodada, resposta=sessao.resposta, criterio=criterio
    ).first()
    if consolidado is None:
        return INDISPONIVEL, None
    sugerido = consolidado.nivel_modal if consolidado.estado == "CONVERGENTE" else None
    return consolidado.estado, sugerido


@transaction.atomic
def registrar_decisao(sessao: SessaoCorrecao, criterio_id, nivel_id, motivo: str, tempo_ativo_ms):
    resposta = sessao.resposta
    try:
        criterio = Criterio.objects.get(pk=criterio_id, versao_id=resposta.lote.versao_rubrica_id)
    except (Criterio.DoesNotExist, ValueError, TypeError) as exc:
        raise ErroDeNegocio(
            "Critério não pertence à rubrica do lote.", codigo="criterio_invalido"
        ) from exc
    try:
        nivel = Nivel.objects.get(pk=nivel_id, criterio=criterio)
    except (Nivel.DoesNotExist, ValueError, TypeError) as exc:
        raise ErroDeNegocio("Nível não pertence ao critério.", codigo="nivel_invalido") from exc
    try:
        tempo = int(tempo_ativo_ms)
    except (TypeError, ValueError) as exc:
        raise ErroDeNegocio("Tempo ativo inválido.", codigo="tempo_invalido") from exc
    if tempo < 0:
        raise ErroDeNegocio("Tempo ativo inválido.", codigo="tempo_invalido")

    estado, sugerido = _o_que_foi_exibido(sessao, criterio)
    if sessao.condicao == SEM_APOIO:
        tipo = Decisao.Tipo.CEGA
    elif sugerido is None:
        tipo = Decisao.Tipo.ESCOLHA
    elif sugerido.pk == nivel.pk:
        tipo = Decisao.Tipo.CONFIRMACAO
    else:
        tipo = Decisao.Tipo.ALTERACAO

    participacao = getattr(sessao, "participacao", None)
    anterior = (
        _vigentes(resposta, sessao.docente, participacao)
        .select_for_update()
        .filter(criterio=criterio)
        .first()
    )
    if anterior:
        anterior.vigente = False
        anterior.save(update_fields=["vigente"])
    extras = {"participacao": participacao} if hasattr(Decisao, "participacao") else {}
    decisao = Decisao.objects.create(
        sessao=sessao,
        resposta=resposta,
        docente=sessao.docente,
        criterio=criterio,
        nivel=nivel,
        estado_exibido=estado,
        nivel_sugerido=sugerido,
        tipo=tipo,
        motivo=(motivo or "").strip(),
        tempo_ativo_ms=tempo,
        substitui=anterior,
        **extras,
    )
    SessaoCorrecao.objects.filter(pk=sessao.pk).update(
        tempo_ativo_ms=tempo, tempo_total_ms=max(tempo, sessao.tempo_total_ms)
    )
    sessao.tempo_ativo_ms = tempo
    return decisao


def atualizar_tempo(sessao: SessaoCorrecao, tempo_ativo_ms) -> None:
    try:
        tempo = int(tempo_ativo_ms)
    except (TypeError, ValueError) as exc:
        raise ErroDeNegocio("Tempo ativo inválido.", codigo="tempo_invalido") from exc
    if tempo < 0:
        raise ErroDeNegocio("Tempo ativo inválido.", codigo="tempo_invalido")
    SessaoCorrecao.objects.filter(pk=sessao.pk, tempo_total_ms__lt=tempo).update(
        tempo_total_ms=tempo
    )


def finalizada(resposta, docente, participacao=None) -> bool:
    n_criterios = resposta.lote.versao_rubrica.criterios.count()
    return n_criterios > 0 and _vigentes(resposta, docente, participacao).count() == n_criterios


def nota(resposta, docente, participacao=None) -> Decimal:
    return sum(
        (
            d.nivel.pontuacao * d.criterio.peso
            for d in _vigentes(resposta, docente, participacao).select_related("nivel", "criterio")
        ),
        Decimal(0),
    )


def notas_do_lote(lote, docente) -> tuple[list[str], list[list]]:
    """(cabeçalho, linhas) só com respostas finalizadas (FR-019)."""
    criterios = list(lote.versao_rubrica.criterios.order_by("ordem"))
    cabecalho = ["codigo", *[c.nome for c in criterios], "nota_total"]
    por_resposta: dict[int, dict[int, Decisao]] = {}
    filtro = {"resposta__lote": lote, "docente": docente, "vigente": True}
    if hasattr(Decisao, "participacao"):
        filtro["participacao__isnull"] = True
    for d in Decisao.objects.filter(**filtro).select_related("nivel", "criterio"):
        por_resposta.setdefault(d.resposta_id, {})[d.criterio_id] = d
    linhas = []
    for resposta in lote.respostas.order_by("codigo"):
        decisoes = por_resposta.get(resposta.id, {})
        if len(decisoes) != len(criterios):
            continue
        pontos = [decisoes[c.id].nivel.pontuacao * c.peso for c in criterios]
        linhas.append([resposta.codigo, *[float(p) for p in pontos], float(sum(pontos))])
    return cabecalho, linhas
