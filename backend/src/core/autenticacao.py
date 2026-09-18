"""Login por e-mail com JWT (simplejwt). Sem autocadastro: contas pelo admin ou
por convite de estudo (plan.md, "Desvios registrados")."""

from rest_framework import serializers
from rest_framework.permissions import IsAuthenticated
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
