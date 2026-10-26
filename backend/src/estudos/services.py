"""Serviços do estudo: criação, convites, início, tarefa do participante (FR-024/025)."""

import secrets

from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.db import transaction
from django.db.models import Count, Max
from django.utils import timezone
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from avaliacao.models import Consolidado, Rodada
from core.exceptions import ErroDeNegocio
from core.models import Usuario
from estudos.alocacao import (
    CELULAS,
    alocar_participantes,
    blocos,
    condicao,
    dividir_metades,
    ordem_do_bloco,
)
from estudos.models import AlocacaoResposta, Estudo, Participacao, Questionario
from revisao.models import Decisao
from revisao.services import abrir_sessao


def criar_estudo(pesquisador, titulo: str, lote, rodada) -> Estudo:
    if not pesquisador.eh_pesquisador:
        raise ErroDeNegocio("Somente pesquisador.", codigo="sem_permissao", status_code=403)
    if lote.dono_id != pesquisador.id:
        raise ErroDeNegocio("O lote comum precisa ser seu.", codigo="lote_invalido")
    if rodada.lote_id != lote.id:
        raise ErroDeNegocio("A rodada não é deste lote.", codigo="rodada_invalida")
    if rodada.status != Rodada.Status.CONCLUIDA:
        raise ErroDeNegocio("A rodada precisa estar concluída.", codigo="rodada_nao_concluida")
    return Estudo.objects.create(
        pesquisador=pesquisador,
        titulo=titulo,
        lote=lote,
        rodada=rodada,
        semente_alocacao=secrets.randbelow(2**31),
    )


def link_de_senha(usuario) -> str:
    uid = urlsafe_base64_encode(force_bytes(usuario.pk))
    token = default_token_generator.make_token(usuario)
    return f"{settings.FRONTEND_URL}/definir-senha/{uid}/{token}/"


def link_do_participante(estudo: Estudo, posicao: int) -> dict:
    """Novo link de definição de senha para um participante, em qualquer fase do estudo.

    Serve para entregar o acesso sem e-mail (oficina) e para senha esquecida ou link expirado.
    Gerar um link não altera a senha atual: ela só muda quando o link é usado.
    """
    participacao = estudo.participacoes.select_related("docente").filter(posicao=posicao).first()
    if participacao is None:
        raise ErroDeNegocio(
            "Participante não encontrado.", codigo="nao_encontrado", status_code=404
        )
    return {"email": participacao.docente.email, "link": link_de_senha(participacao.docente)}


@transaction.atomic
def convidar(estudo: Estudo, emails: list[str]) -> list[dict]:
    if estudo.status == Estudo.Status.ENCERRADO:
        raise ErroDeNegocio(
            "O estudo foi encerrado; não entram novos participantes.", codigo="estudo_encerrado"
        )
    # Com o estudo em andamento, quem entra depois recebe a próxima célula do rodízio,
    # a mesma que teria recebido se tivesse sido convidado antes do início.
    em_andamento = estudo.status == Estudo.Status.EM_ANDAMENTO
    proxima = (estudo.participacoes.aggregate(m=Max("posicao"))["m"] or 0) + 1
    convites = []
    for email in dict.fromkeys(e.strip().lower() for e in emails if e and e.strip()):
        usuario = Usuario.objects.filter(email=email).first()
        if usuario is None:
            usuario = Usuario.objects.create_user(email, None, nome=email.split("@")[0])
        if usuario.id == estudo.pesquisador_id:
            raise ErroDeNegocio(
                "O pesquisador não participa do próprio estudo.", codigo="convite_invalido"
            )
        participacao, criada = Participacao.objects.get_or_create(
            estudo=estudo, docente=usuario, defaults={"posicao": proxima}
        )
        if criada:
            if em_andamento:
                participacao.braco, participacao.ordem = CELULAS[(proxima - 1) % len(CELULAS)]
                participacao.save(update_fields=["braco", "ordem"])
            proxima += 1
        link = link_de_senha(usuario) if not usuario.has_usable_password() else None
        if link:
            send_mail(
                f"Convite: {estudo.titulo}",
                "Você foi convidada(o) a participar de um estudo de correção assistida "
                f"por rubrica.\nDefina sua senha em: {link}\n",
                settings.DEFAULT_FROM_EMAIL,
                [email],
                fail_silently=True,
            )
        convites.append({"email": email, "link": link, "posicao": participacao.posicao})
    return convites


def _nao_convergentes(estudo: Estudo) -> set[int]:
    return set(
        Consolidado.objects.filter(rodada=estudo.rodada)
        .exclude(estado=Consolidado.Estado.CONVERGENTE)
        .values_list("resposta_id", flat=True)
    )


@transaction.atomic
def iniciar(estudo: Estudo) -> dict:
    estudo = Estudo.objects.select_for_update().get(pk=estudo.pk)
    if estudo.status != Estudo.Status.PREPARACAO:
        raise ErroDeNegocio("O estudo já foi iniciado.", codigo="estudo_iniciado")
    participacoes = list(estudo.participacoes.order_by("posicao"))
    if not participacoes:
        raise ErroDeNegocio("Convide ao menos um participante.", codigo="sem_participantes")
    elegiveis = list(estudo.lote.respostas.filter(aviso__isnull=True).values_list("id", flat=True))
    dificeis = _nao_convergentes(estudo)
    metades = dividir_metades([(r, r in dificeis) for r in elegiveis], estudo.semente_alocacao)
    AlocacaoResposta.objects.bulk_create(
        AlocacaoResposta(estudo=estudo, resposta_id=r, metade=m) for r, m in metades.items()
    )
    for participacao, (braco, ordem) in zip(
        participacoes, alocar_participantes(len(participacoes)), strict=True
    ):
        participacao.braco, participacao.ordem = braco, ordem
        participacao.save(update_fields=["braco", "ordem"])
    estudo.status = Estudo.Status.EM_ANDAMENTO
    estudo.iniciado_em = timezone.now()
    estudo.save(update_fields=["status", "iniciado_em"])
    valores = list(metades.values())
    return {
        "metade_A": valores.count("A"),
        "metade_B": valores.count("B"),
        "participantes": [
            {"posicao": p.posicao, "docente": p.docente.email, "braco": p.braco, "ordem": p.ordem}
            for p in participacoes
        ],
    }


def encerrar(estudo: Estudo) -> None:
    estudo.status = Estudo.Status.ENCERRADO
    estudo.save(update_fields=["status"])


def participacao_de(estudo: Estudo, usuario) -> Participacao:
    participacao = estudo.participacoes.filter(docente=usuario).first()
    if participacao is None:
        raise ErroDeNegocio("Não encontrado.", codigo="nao_encontrado", status_code=404)
    return participacao


def condicao_da_resposta(participacao: Participacao, resposta_id: int) -> str:
    alocacao = AlocacaoResposta.objects.filter(
        estudo_id=participacao.estudo_id, resposta_id=resposta_id
    ).first()
    if alocacao is None:
        raise ErroDeNegocio("Resposta fora do estudo.", codigo="nao_encontrado", status_code=404)
    return condicao(alocacao.metade, participacao.braco)


def _finalizadas(participacao: Participacao) -> set[int]:
    n_criterios = participacao.estudo.lote.versao_rubrica.criterios.count()
    return set(
        Decisao.objects.filter(participacao=participacao, vigente=True)
        .values("resposta_id")
        .annotate(n=Count("id"))
        .filter(n=n_criterios)
        .values_list("resposta_id", flat=True)
    )


def minha_tarefa(participacao: Participacao) -> dict:
    estudo = participacao.estudo
    if estudo.status == Estudo.Status.PREPARACAO:
        return {
            "iniciado": False,
            "concluido": False,
            "bloco_atual": None,
            "proxima_resposta": None,
        }
    feitas = _finalizadas(participacao)
    por_metade: dict[str, list[int]] = {"A": [], "B": []}
    for resposta_id, metade in estudo.alocacoes.values_list("resposta_id", "metade"):
        por_metade[metade].append(resposta_id)
    progresso = []
    atual = None
    proxima = None
    for numero, (metade, cond) in enumerate(
        blocos(participacao.braco, participacao.ordem), start=1
    ):
        ordem = ordem_do_bloco(por_metade[metade], estudo.semente_alocacao, participacao.id)
        pendentes = [r for r in ordem if r not in feitas]
        progresso.append(
            {
                "bloco": numero,
                "condicao": cond,
                "feitas": len(ordem) - len(pendentes),
                "total": len(ordem),
            }
        )
        if atual is None and pendentes:
            atual = {"numero": numero, "de": 2, "metade": metade, "condicao": cond}
            proxima = pendentes[0]
    concluido = atual is None
    if concluido and participacao.concluida_em is None:
        participacao.concluida_em = timezone.now()
        participacao.save(update_fields=["concluida_em"])
    codigo = (
        estudo.lote.respostas.filter(pk=proxima).values_list("codigo", flat=True).first()
        if proxima
        else None
    )
    return {
        "iniciado": True,
        "concluido": concluido,
        "participante": codigo_do_participante(participacao),
        "consentimento": participacao.consentimento_em is not None,
        "questionario_enviado": Questionario.objects.filter(participacao=participacao).exists(),
        "bloco_atual": atual,
        "proxima_resposta": {"id": proxima, "codigo": codigo} if proxima else None,
        "progresso": progresso,
    }


def abrir_sessao_do_estudo(participacao: Participacao, resposta):
    """A condição vem da alocação, nunca do cliente (FR-025)."""
    if participacao.estudo.status != Estudo.Status.EM_ANDAMENTO:
        raise ErroDeNegocio("O estudo não está em andamento.", codigo="estudo_fechado")
    if participacao.consentimento_em is None:
        raise ErroDeNegocio(
            "Aceite o termo de consentimento antes de começar.", codigo="sem_consentimento"
        )
    cond = condicao_da_resposta(participacao, resposta.id)
    return abrir_sessao(
        participacao.docente,
        resposta,
        condicao=cond,
        participacao=participacao,
        rodada=participacao.estudo.rodada,
    )


def codigo_do_participante(participacao: Participacao) -> str:
    anteriores = participacao.estudo.participacoes.filter(posicao__lte=participacao.posicao)
    return f"P{anteriores.count():02d}"


def enviar_questionario(participacao: Participacao, dados: dict) -> Questionario:
    """Instrumentos 4 e 5: uma única resposta, só depois dos dois blocos."""
    if not minha_tarefa(participacao)["concluido"]:
        raise ErroDeNegocio(
            "Conclua os dois blocos antes de responder ao questionário.",
            codigo="estudo_nao_concluido",
        )
    if Questionario.objects.filter(participacao=participacao).exists():
        raise ErroDeNegocio("O questionário já foi enviado.", codigo="questionario_enviado")
    return Questionario.objects.create(participacao=participacao, **dados)


def registrar_consentimento(participacao: Participacao, autoriza_imagem: bool) -> None:
    """TCLE aceito uma vez; a autorização de imagem pode ser revista depois."""
    if participacao.consentimento_em is None:
        participacao.consentimento_em = timezone.now()
    participacao.autoriza_imagem = autoriza_imagem
    participacao.save(update_fields=["consentimento_em", "autoriza_imagem"])
