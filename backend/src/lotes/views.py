from django.db.models import Count
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from core.exceptions import ErroDeNegocio
from core.permissions import pode_ver_lote
from lotes.importacao import importar, previa
from lotes.models import Lote
from lotes.serializers import LoteEntrada, LoteResumo, RespostaResumo


def lote_do_dono(request, pk) -> Lote:
    return get_object_or_404(Lote, pk=pk, dono=request.user)


def lote_visivel(request, pk) -> Lote:
    lote = get_object_or_404(Lote, pk=pk)
    if not pode_ver_lote(request.user, lote):
        raise ErroDeNegocio("Não encontrado.", codigo="nao_encontrado", status_code=404)
    return lote


def detalhe(lote: Lote) -> dict:
    dados = LoteResumo(Lote.objects.annotate(n_respostas=Count("respostas")).get(pk=lote.pk)).data
    avisos = dict(
        lote.respostas.exclude(aviso__isnull=True)
        .values_list("aviso")
        .annotate(n=Count("id"))
        .values_list("aviso", "n")
    )
    versao = lote.versao_rubrica
    dados.update(
        {
            "avisos": avisos,
            "versao": {"id": versao.id, "numero": versao.numero, "rubrica": versao.rubrica_id},
            "rodadas": [
                {"id": r.id, "numero": r.numero, "status": r.status, "modelo": r.modelo}
                for r in lote.rodadas.order_by("numero")
            ],
        }
    )
    return dados


class LotesView(APIView):
    def get(self, request):
        lotes = (
            Lote.objects.filter(dono=request.user)
            .annotate(n_respostas=Count("respostas"))
            .select_related("versao_rubrica__rubrica")
        )
        return Response(LoteResumo(lotes, many=True).data)

    def post(self, request):
        entrada = LoteEntrada(data=request.data, dono=request.user)
        entrada.is_valid(raise_exception=True)
        dados = dict(entrada.validated_data)
        lote = Lote(dono=request.user, **dados)
        lote.full_clean()
        lote.save()
        return Response(detalhe(lote), status=status.HTTP_201_CREATED)


class LoteView(APIView):
    def get(self, request, pk):
        return Response(detalhe(lote_visivel(request, pk)))


def _arquivo(request):
    arquivo = request.FILES.get("arquivo")
    if arquivo is None:
        raise ErroDeNegocio("Envie o arquivo no campo “arquivo”.", codigo="sem_arquivo")
    return arquivo


class PreviaView(APIView):
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, pk):
        lote_do_dono(request, pk)
        return Response(previa(_arquivo(request)))


class ImportacaoView(APIView):
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, pk):
        lote = lote_do_dono(request, pk)
        colunas_id = request.data.getlist("colunas_identificacao")
        gerar_chave = str(request.data.get("gerar_chave", "")).lower() in {"1", "true", "sim", "on"}
        resultado = importar(
            lote,
            _arquivo(request),
            request.data.get("coluna_resposta", ""),
            colunas_id,
            gerar_chave,
        )
        return Response(resultado, status=status.HTTP_201_CREATED)


class RespostasView(APIView):
    def get(self, request, pk):
        lote = lote_visivel(request, pk)
        return Response(RespostaResumo(lote.respostas.order_by("codigo"), many=True).data)
