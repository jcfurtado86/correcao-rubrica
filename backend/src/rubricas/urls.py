from django.urls import path

from rubricas.views import ImportarModeloView, ModeloView, RubricasView, RubricaView

urlpatterns = [
    path("rubricas/", RubricasView.as_view(), name="rubricas"),
    path("rubricas/<int:pk>/", RubricaView.as_view(), name="rubrica"),
    path("rubricas/<int:pk>/modelo/", ModeloView.as_view(), name="rubrica-modelo"),
    path("rubricas/importar-modelo/", ImportarModeloView.as_view(), name="rubrica-importar"),
]
