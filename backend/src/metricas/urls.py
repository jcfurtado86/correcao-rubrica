from django.urls import path

from metricas.views import ExportacaoView, PainelView

urlpatterns = [
    path("lotes/<int:pk>/painel/", PainelView.as_view(), name="painel"),
    path("lotes/<int:pk>/exportacao.zip", ExportacaoView.as_view(), name="exportacao"),
]
