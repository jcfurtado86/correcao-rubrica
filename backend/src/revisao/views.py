import csv
import io

from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.exceptions import ErroDeNegocio
from lotes.models import Resposta
from lotes.views import lote_do_dono, lote_visivel
from revisao.fila import montar_fila
from revisao.models import Decisao, SessaoCorrecao
from revisao.services import (
    abrir_sessao,
    atualizar_tempo,
    decisao_json,
    notas_do_lote,
    registrar_decisao,
)


class FilaView(APIView):
    def get(self, request, pk):
        lote = lote_visivel(request, pk)
        return Response(montar_fila(lote, request.user))


class SessoesView(APIView):
    def post(self, request, pk):
        resposta = get_object_or_404(Resposta, pk=pk, lote__dono=request.user)
        _, conteudo = abrir_sessao(request.user, resposta)
        return Response(conteudo, status=status.HTTP_201_CREATED)


def _sessao_do_usuario(request, pk) -> SessaoCorrecao:
    return get_object_or_404(
        SessaoCorrecao.objects.select_related("resposta__lote"), pk=pk, docente=request.user
    )


class SessaoView(APIView):
    def patch(self, request, pk):
        sessao = _sessao_do_usuario(request, pk)
        atualizar_tempo(sessao, request.data.get("tempo_ativo_ms"))
        return Response({"sessao": sessao.id})


class DecisoesView(APIView):
    """Uma decisão por chamada. Lista no corpo é recusada (FR-018)."""

    def post(self, request, pk):
        sessao = _sessao_do_usuario(request, pk)
        if not isinstance(request.data, dict):
            raise ErroDeNegocio("Envie uma decisão por vez.", codigo="decisao_em_lote_proibida")
        decisao = registrar_decisao(
            sessao,
            request.data.get("criterio"),
            request.data.get("nivel"),
            request.data.get("motivo", ""),
            request.data.get("tempo_ativo_ms", 0),
        )
        return Response(decisao_json(decisao), status=status.HTTP_201_CREATED)


class HistoricoView(APIView):
    def get(self, request, pk):
        resposta = get_object_or_404(Resposta, pk=pk, lote__dono=request.user)
        decisoes = (
            Decisao.objects.filter(resposta=resposta, docente=request.user)
            .select_related("nivel")
            .order_by("criado_em", "id")
        )
        return Response([decisao_json(d) for d in decisoes])


class NotasView(APIView):
    def get(self, request, pk):
        lote = lote_do_dono(request, pk)
        cabecalho, linhas = notas_do_lote(lote, request.user)
        saida = io.StringIO()
        escritor = csv.writer(saida)
        escritor.writerow(cabecalho)
        escritor.writerows(linhas)
        resposta = HttpResponse(saida.getvalue(), content_type="text/csv; charset=utf-8")
        resposta["Content-Disposition"] = f'attachment; filename="notas-lote{lote.id}.csv"'
        return resposta
