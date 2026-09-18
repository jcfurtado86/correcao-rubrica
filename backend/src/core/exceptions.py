"""Erros da API no formato de contracts/api.md: {"detail": "...", "codigo": "..."}."""

from django.core.exceptions import ValidationError as ErroDjango
from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.response import Response
from rest_framework.views import exception_handler


class ErroDeNegocio(APIException):
    """Regra de negócio violada. `codigo` é estável e testável; `detail`, legível."""

    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "Operação não permitida."
    default_code = "regra_de_negocio"

    def __init__(self, detail=None, codigo=None, status_code=None):
        super().__init__(detail=detail, code=codigo)
        self.codigo = codigo or self.default_code
        if status_code:
            self.status_code = status_code


def tratar_excecoes(exc, context):
    if isinstance(exc, ErroDjango):
        mensagens = exc.messages if hasattr(exc, "messages") else [str(exc)]
        return Response(
            {"detail": " ".join(mensagens), "codigo": "invalido"},
            status=status.HTTP_400_BAD_REQUEST,
        )
    resposta = exception_handler(exc, context)
    if resposta is None:
        return None
    codigo = getattr(exc, "codigo", None)
    dados = resposta.data
    if isinstance(dados, dict) and "detail" in dados:
        detalhe = dados["detail"]
        codigo = codigo or getattr(detalhe, "code", None) or "erro"
        resposta.data = {"detail": str(detalhe), "codigo": codigo}
    else:
        # Erros de validação de serializer: mantém os campos e acrescenta o código.
        resposta.data = {
            "detail": "Dados inválidos.",
            "codigo": codigo or "invalido",
            "campos": dados,
        }
    return resposta
