from django.urls import path

from avaliacao.views import (
    EstimativaView,
    ExecucoesDaRespostaView,
    ModelosView,
    RetomarView,
    RodadasView,
    RodadaView,
    SugestoesDaRespostaView,
)

urlpatterns = [
    path("modelos/", ModelosView.as_view(), name="modelos"),
    path("lotes/<int:pk>/rodadas/estimativa/", EstimativaView.as_view(), name="estimativa"),
    path("lotes/<int:pk>/rodadas/", RodadasView.as_view(), name="rodadas"),
    path("rodadas/<int:pk>/", RodadaView.as_view(), name="rodada"),
    path("rodadas/<int:pk>/retomar/", RetomarView.as_view(), name="retomar"),
    path("respostas/<int:pk>/execucoes/", ExecucoesDaRespostaView.as_view(), name="execucoes"),
    path("respostas/<int:pk>/sugestoes/", SugestoesDaRespostaView.as_view(), name="sugestoes"),
]
