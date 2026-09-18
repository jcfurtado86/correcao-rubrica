from decimal import Decimal, InvalidOperation

from django.http import HttpResponse
from rest_framework.response import Response
from rest_framework.views import APIView

from core.exceptions import ErroDeNegocio
from lotes.views import lote_visivel
from metricas.exportacao import arquivos_do_lote, zipar
from metricas.painel import painel_do_lote


def _limiar(valor):
    if valor in (None, ""):
        return None
    try:
        limiar = Decimal(valor)
    except InvalidOperation as exc:
        raise ErroDeNegocio("Limiar inválido.", codigo="invalido") from exc
    if not (Decimal("0.5") < limiar <= 1):
        raise ErroDeNegocio("O limiar precisa estar em (0,5; 1,0].", codigo="invalido")
    return limiar


def _sim(valor) -> bool:
    return str(valor).lower() in {"1", "true", "sim"}


class PainelView(APIView):
    def get(self, request, pk):
        lote = lote_visivel(request, pk)
        rodada = request.query_params.get("rodada")
        return Response(
            painel_do_lote(
                lote,
                int(rodada) if rodada and rodada.isdigit() else None,
                _limiar(request.query_params.get("limiar")),
            )
        )


class ExportacaoView(APIView):
    def get(self, request, pk):
        lote = lote_visivel(request, pk)
        conteudo = zipar(
            arquivos_do_lote(
                lote,
                incluir_texto=_sim(request.query_params.get("incluir_texto")),
                incluir_motivos=_sim(request.query_params.get("incluir_motivos")),
            )
        )
        resposta = HttpResponse(conteudo, content_type="application/zip")
        resposta["Content-Disposition"] = f'attachment; filename="exportacao-lote{lote.id}.zip"'
        return resposta
