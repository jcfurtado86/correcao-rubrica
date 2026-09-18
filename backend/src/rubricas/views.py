import json

from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils.text import slugify
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from core.exceptions import ErroDeNegocio
from rubricas.modelo import exportar, importar
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


class ModeloView(APIView):
    def get(self, request, pk):
        rubrica = get_object_or_404(Rubrica, pk=pk, dono=request.user)
        conteudo = json.dumps(exportar(rubrica.versao_vigente), ensure_ascii=False, indent=2)
        resposta = HttpResponse(conteudo, content_type="application/json; charset=utf-8")
        nome = slugify(rubrica.titulo) or "rubrica"
        resposta["Content-Disposition"] = f'attachment; filename="modelo-{nome}.json"'
        return resposta


class ImportarModeloView(APIView):
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        arquivo = request.FILES.get("arquivo")
        if arquivo is None or arquivo.size > 1024 * 1024:
            raise ErroDeNegocio("Envie o arquivo JSON do modelo (até 1 MB).", codigo="sem_arquivo")
        try:
            dados = json.loads(arquivo.read().decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ErroDeNegocio(
                "O arquivo não é um JSON válido.", codigo="modelo_invalido"
            ) from exc
        rubrica = importar(request.user, dados)
        return Response(rubrica_completa(rubrica), status=status.HTTP_201_CREATED)
