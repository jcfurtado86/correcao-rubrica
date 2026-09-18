from django.urls import path

from revisao.views import DecisoesView, FilaView, HistoricoView, NotasView, SessaoView, SessoesView

urlpatterns = [
    path("lotes/<int:pk>/fila/", FilaView.as_view(), name="fila"),
    path("lotes/<int:pk>/notas.csv", NotasView.as_view(), name="notas"),
    path("respostas/<int:pk>/sessoes/", SessoesView.as_view(), name="sessoes"),
    path("respostas/<int:pk>/historico/", HistoricoView.as_view(), name="historico"),
    path("sessoes/<int:pk>/", SessaoView.as_view(), name="sessao"),
    path("sessoes/<int:pk>/decisoes/", DecisoesView.as_view(), name="decisoes"),
]
