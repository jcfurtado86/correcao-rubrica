"""Login por e-mail com JWT (simplejwt). Sem autocadastro: contas pelo admin ou
por convite de estudo (plan.md, "Desvios registrados")."""

from django.contrib.auth import password_validation
from django.contrib.auth.tokens import default_token_generator
from django.core.exceptions import ValidationError
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from rest_framework import serializers
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView


class ObtencaoDeToken(TokenObtainPairView):
    throttle_scope = "login"


class RenovacaoDeToken(TokenRefreshView):
    throttle_scope = "login"


class UsuarioSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    email = serializers.EmailField()
    nome = serializers.CharField()
    papel = serializers.CharField()


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(UsuarioSerializer(request.user).data)


class DefinirSenhaView(APIView):
    """Link do convite (e de redefinição): define a senha de quem foi convidado.

    O token do Django se invalida quando a senha muda, então o link vale uma vez.
    """

    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_scope = "login"

    def post(self, request):
        from core.exceptions import ErroDeNegocio
        from core.models import Usuario

        try:
            pk = force_str(urlsafe_base64_decode(str(request.data.get("uid", ""))))
            usuario = Usuario.objects.get(pk=pk)
        except (Usuario.DoesNotExist, ValueError, TypeError, OverflowError) as exc:
            raise ErroDeNegocio("Link inválido ou expirado.", codigo="link_invalido") from exc
        if not default_token_generator.check_token(usuario, str(request.data.get("token", ""))):
            raise ErroDeNegocio("Link inválido ou expirado.", codigo="link_invalido")
        senha = str(request.data.get("senha", ""))
        try:
            password_validation.validate_password(senha, usuario)
        except ValidationError as exc:
            raise ErroDeNegocio(" ".join(exc.messages), codigo="senha_fraca") from exc
        usuario.set_password(senha)
        usuario.save(update_fields=["password"])
        return Response({"email": usuario.email})
