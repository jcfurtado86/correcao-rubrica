from django.urls import path

from estudos.views import (
    ConsentimentoView,
    ConvitesView,
    CriteriosDoEstudoView,
    EncerrarView,
    EstudosView,
    EstudoView,
    ExportacaoDoEstudoView,
    IniciarView,
    LinkDeSenhaView,
    MinhaTarefaView,
    PainelDoEstudoView,
    QuestionarioView,
    SessaoDoEstudoView,
)

urlpatterns = [
    path("estudos/", EstudosView.as_view(), name="estudos"),
    path("estudos/<int:pk>/", EstudoView.as_view(), name="estudo"),
    path("estudos/<int:pk>/convites/", ConvitesView.as_view(), name="convites"),
    path("estudos/<int:pk>/iniciar/", IniciarView.as_view(), name="iniciar"),
    path(
        "estudos/<int:pk>/participantes/<int:posicao>/link-senha/",
        LinkDeSenhaView.as_view(),
        name="link-senha",
    ),
    path("estudos/<int:pk>/encerrar/", EncerrarView.as_view(), name="encerrar"),
    path("estudos/<int:pk>/minha-tarefa/", MinhaTarefaView.as_view(), name="minha-tarefa"),
    path("estudos/<int:pk>/questionario/", QuestionarioView.as_view(), name="questionario"),
    path("estudos/<int:pk>/consentimento/", ConsentimentoView.as_view(), name="consentimento"),
    path("estudos/<int:pk>/criterios/", CriteriosDoEstudoView.as_view(), name="criterios-estudo"),
    path(
        "estudos/<int:pk>/respostas/<int:rid>/sessoes/",
        SessaoDoEstudoView.as_view(),
        name="sessao-estudo",
    ),
    path("estudos/<int:pk>/painel/", PainelDoEstudoView.as_view(), name="painel-estudo"),
    path(
        "estudos/<int:pk>/exportacao.zip",
        ExportacaoDoEstudoView.as_view(),
        name="exportacao-estudo",
    ),
]
