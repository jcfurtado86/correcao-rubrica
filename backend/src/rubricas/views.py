from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from rubricas.models import Rubrica
from rubricas.serializers import RubricaEntrada, RubricaResumo, rubrica_completa
from rubricas.services import atualizar_rubrica, criar_rubrica


class RubricasView(APIView):
    def get(self, request):
        rubricas = Rubrica.objects.filter(dono=request.user).prefetch_related("versoes")
        return Response(RubricaResumo(rubricas, many=True).data)

    def post(self, request):
        entrada = RubricaEntrada(data=request.data)
        entrada.is_valid(raise_exception=True)
        rubrica = criar_rubrica(request.user, entrada.validated_data)
        return Response(rubrica_completa(rubrica), status=status.HTTP_201_CREATED)


class RubricaView(APIView):
    def _rubrica(self, request, pk):
        return get_object_or_404(Rubrica, pk=pk, dono=request.user)

    def get(self, request, pk):
        return Response(rubrica_completa(self._rubrica(request, pk)))

    def put(self, request, pk):
        rubrica = self._rubrica(request, pk)
        entrada = RubricaEntrada(data=request.data)
        entrada.is_valid(raise_exception=True)
        versao, nova = atualizar_rubrica(rubrica, entrada.validated_data)
        codigo = status.HTTP_201_CREATED if nova else status.HTTP_200_OK
        return Response(rubrica_completa(rubrica, versao), status=codigo)
