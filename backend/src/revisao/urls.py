from django.urls import path

from revisao.views import FilaView

urlpatterns = [
    path("lotes/<int:pk>/fila/", FilaView.as_view(), name="fila"),
]
