from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.exceptions import ErroDeNegocio
from core.permissions import EhPesquisador
from estudos.models import Estudo
from estudos.serializers import (
    ConsentimentoEntrada,
    ConvitesEntrada,
    EstudoEntrada,
    QuestionarioEntrada,
)
from estudos.services import (
    abrir_sessao_do_estudo,
    convidar,
    criar_estudo,
    encerrar,
    enviar_questionario,
    iniciar,
    link_do_participante,
    minha_tarefa,
    participacao_de,
    registrar_consentimento,
)
from lotes.models import Resposta
from metricas.estudo import arquivos_do_estudo, painel_do_estudo
from metricas.exportacao import zipar


def estudo_json(estudo: Estudo, papel: str) -> dict:
    return {
        "id": estudo.id,
        "titulo": estudo.titulo,
        "status": estudo.status,
        "papel": papel,
        "lote": estudo.lote_id,
        "lote_titulo": estudo.lote.titulo,
        "rodada": estudo.rodada.numero,
        "n_participantes": estudo.participacoes.count(),
        "criado_em": estudo.criado_em,
    }


def estudo_do_pesquisador(request, pk) -> Estudo:
    estudo = get_object_or_404(Estudo.objects.select_related("lote", "rodada"), pk=pk)
    if estudo.pesquisador_id != request.user.id:
        if estudo.participacoes.filter(docente=request.user).exists():
            raise ErroDeNegocio("Somente o pesquisador.", codigo="sem_permissao", status_code=403)
        raise ErroDeNegocio("Não encontrado.", codigo="nao_encontrado", status_code=404)
    return estudo


class EstudosView(APIView):
    def get(self, request):
        criados = Estudo.objects.filter(pesquisador=request.user).select_related("lote", "rodada")
        participa = Estudo.objects.filter(participacoes__docente=request.user).select_related(
            "lote", "rodada"
        )
        return Response(
            [estudo_json(e, "PESQUISADOR") for e in criados]
            + [estudo_json(e, "PARTICIPANTE") for e in participa]
        )

    def post(self, request):
        if not request.user.eh_pesquisador:
            raise ErroDeNegocio("Somente pesquisador.", codigo="sem_permissao", status_code=403)
        entrada = EstudoEntrada(data=request.data)
        entrada.is_valid(raise_exception=True)
        dados = entrada.validated_data
        estudo = criar_estudo(request.user, dados["titulo"], dados["lote"], dados["rodada"])
        return Response(estudo_json(estudo, "PESQUISADOR"), status=status.HTTP_201_CREATED)


class EstudoView(APIView):
    def get(self, request, pk):
        estudo = get_object_or_404(Estudo.objects.select_related("lote", "rodada"), pk=pk)
        if estudo.pesquisador_id == request.user.id:
            return Response(estudo_json(estudo, "PESQUISADOR"))
        participacao_de(estudo, request.user)
        return Response(estudo_json(estudo, "PARTICIPANTE"))


class ConvitesView(APIView):
    permission_classes = [EhPesquisador]

    def post(self, request, pk):
        estudo = estudo_do_pesquisador(request, pk)
        entrada = ConvitesEntrada(data=request.data)
        entrada.is_valid(raise_exception=True)
        convites = convidar(estudo, entrada.validated_data["emails"])
        return Response({"convites": convites}, status=status.HTTP_201_CREATED)


class LinkDeSenhaView(APIView):
    permission_classes = [EhPesquisador]

    def post(self, request, pk, posicao):
        return Response(link_do_participante(estudo_do_pesquisador(request, pk), posicao))


class IniciarView(APIView):
    permission_classes = [EhPesquisador]

    def post(self, request, pk):
        return Response(iniciar(estudo_do_pesquisador(request, pk)))


class EncerrarView(APIView):
    permission_classes = [EhPesquisador]

    def post(self, request, pk):
        encerrar(estudo_do_pesquisador(request, pk))
        return Response({"status": "ENCERRADO"})


class MinhaTarefaView(APIView):
    def get(self, request, pk):
        estudo = get_object_or_404(Estudo, pk=pk)
        return Response(minha_tarefa(participacao_de(estudo, request.user)))


class ConsentimentoView(APIView):
    """TCLE (Instrumento 2): aceite com confirmação, antes do primeiro bloco."""

    def post(self, request, pk):
        participacao = participacao_de(get_object_or_404(Estudo, pk=pk), request.user)
        entrada = ConsentimentoEntrada(data=request.data)
        entrada.is_valid(raise_exception=True)
        registrar_consentimento(participacao, entrada.validated_data["autoriza_imagem"])
        return Response({"consentimento": True})


class QuestionarioView(APIView):
    """Instrumentos 4 e 5, respondidos pelo participante no fim do estudo."""

    def get(self, request, pk):
        participacao = participacao_de(get_object_or_404(Estudo, pk=pk), request.user)
        return Response({"enviado": hasattr(participacao, "questionario")})

    def post(self, request, pk):
        participacao = participacao_de(get_object_or_404(Estudo, pk=pk), request.user)
        entrada = QuestionarioEntrada(data=request.data)
        entrada.is_valid(raise_exception=True)
        enviar_questionario(participacao, entrada.validated_data)
        return Response({"enviado": True}, status=status.HTTP_201_CREATED)


class SessaoDoEstudoView(APIView):
    def post(self, request, pk, rid):
        estudo = get_object_or_404(Estudo.objects.select_related("rodada"), pk=pk)
        participacao = participacao_de(estudo, request.user)
        resposta = get_object_or_404(Resposta, pk=rid, lote_id=estudo.lote_id)
        _, conteudo = abrir_sessao_do_estudo(participacao, resposta)
        return Response(conteudo, status=status.HTTP_201_CREATED)


class PainelDoEstudoView(APIView):
    def get(self, request, pk):
        return Response(painel_do_estudo(estudo_do_pesquisador(request, pk)))


class ExportacaoDoEstudoView(APIView):
    def get(self, request, pk):
        estudo = estudo_do_pesquisador(request, pk)
        sim = {"1", "true", "sim"}
        conteudo = zipar(
            arquivos_do_estudo(
                estudo,
                incluir_texto=str(request.query_params.get("incluir_texto", "")).lower() in sim,
                incluir_motivos=str(request.query_params.get("incluir_motivos", "")).lower() in sim,
            )
        )
        resposta = HttpResponse(conteudo, content_type="application/zip")
        resposta["Content-Disposition"] = f'attachment; filename="exportacao-estudo{estudo.id}.zip"'
        return resposta


class CriteriosDoEstudoView(APIView):
    """Rubrica do lote comum, para a tela do participante (que não acessa o lote)."""

    def get(self, request, pk):
        from rubricas.serializers import CriterioSaida

        estudo = get_object_or_404(Estudo.objects.select_related("lote__versao_rubrica"), pk=pk)
        if estudo.pesquisador_id != request.user.id:
            participacao_de(estudo, request.user)
        criterios = estudo.lote.versao_rubrica.criterios.prefetch_related("niveis").order_by(
            "ordem"
        )
        return Response(CriterioSaida(criterios, many=True).data)
