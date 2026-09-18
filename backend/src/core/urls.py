from django.urls import path

from core.autenticacao import MeView, ObtencaoDeToken, RenovacaoDeToken

urlpatterns = [
    path("auth/token/", ObtencaoDeToken.as_view(), name="token"),
    path("auth/token/refresh/", RenovacaoDeToken.as_view(), name="token-refresh"),
    path("auth/me/", MeView.as_view(), name="me"),
]
