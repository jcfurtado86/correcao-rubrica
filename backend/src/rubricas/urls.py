from django.urls import path

from rubricas.views import RubricasView, RubricaView

urlpatterns = [
    path("rubricas/", RubricasView.as_view(), name="rubricas"),
    path("rubricas/<int:pk>/", RubricaView.as_view(), name="rubrica"),
]
