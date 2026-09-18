from django.urls import path

from avaliacao.views import (
    EstimativaView,
    ExecucoesDaRespostaView,
    RetomarView,
    RodadasView,
    RodadaView,
)

urlpatterns = [
    path("lotes/<int:pk>/rodadas/estimativa/", EstimativaView.as_view(), name="estimativa"),
    path("lotes/<int:pk>/rodadas/", RodadasView.as_view(), name="rodadas"),
    path("rodadas/<int:pk>/", RodadaView.as_view(), name="rodada"),
    path("rodadas/<int:pk>/retomar/", RetomarView.as_view(), name="retomar"),
    path("respostas/<int:pk>/execucoes/", ExecucoesDaRespostaView.as_view(), name="execucoes"),
]
