from django.urls import path

from lotes.views import ImportacaoView, LotesView, LoteView, PreviaView, RespostasView

urlpatterns = [
    path("lotes/", LotesView.as_view(), name="lotes"),
    path("lotes/<int:pk>/", LoteView.as_view(), name="lote"),
    path("lotes/<int:pk>/importacao/previa/", PreviaView.as_view(), name="importacao-previa"),
    path("lotes/<int:pk>/importacao/", ImportacaoView.as_view(), name="importacao"),
    path("lotes/<int:pk>/respostas/", RespostasView.as_view(), name="respostas"),
]
