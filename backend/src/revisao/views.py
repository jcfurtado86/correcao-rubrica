from rest_framework.response import Response
from rest_framework.views import APIView

from lotes.views import lote_visivel
from revisao.fila import montar_fila


class FilaView(APIView):
    def get(self, request, pk):
        lote = lote_visivel(request, pk)
        return Response(montar_fila(lote, request.user))
