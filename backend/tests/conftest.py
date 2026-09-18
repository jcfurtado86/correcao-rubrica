import pytest
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from conectores.duble import DubleLLMProvider
from config.celery import app as celery_app
from core.models import Usuario


@pytest.fixture(autouse=True)
def _dublê(settings):
    """Nenhum teste chama o modelo real (constituição, portões de qualidade).

    As tarefas Celery rodam na hora, dentro do teste, sem broker. O flag é
    aplicado a cada teste porque a configuração do app é recarregada depois
    da importação deste arquivo.
    """
    settings.LLM_PROVIDER = "dumb"
    settings.GEMINI_PAID_TIER = False
    settings.CELERY_TASK_ALWAYS_EAGER = True
    settings.CELERY_TASK_EAGER_PROPAGATES = True
    celery_app.conf.task_always_eager = True
    celery_app.conf.task_eager_propagates = True
    DubleLLMProvider.prompts_recebidos.clear()
    yield
    DubleLLMProvider.prompts_recebidos.clear()


@pytest.fixture
def docente(db):
    return Usuario.objects.create_user("docente@exemplo.org", "senha-forte-123", nome="Docente")


@pytest.fixture
def outra_docente(db):
    return Usuario.objects.create_user("outra@exemplo.org", "senha-forte-123", nome="Outra")


@pytest.fixture
def pesquisador(db):
    return Usuario.objects.create_user(
        "pesquisa@exemplo.org",
        "senha-forte-123",
        nome="Pesquisador",
        papel=Usuario.Papel.PESQUISADOR,
    )


@pytest.fixture
def cliente():
    """`cliente(usuario)` devolve um APIClient autenticado por JWT; sem usuário, anônimo."""

    def _fabrica(usuario=None):
        api = APIClient()
        if usuario is not None:
            token = RefreshToken.for_user(usuario).access_token
            api.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        return api

    return _fabrica


@pytest.fixture
def api(cliente, docente):
    return cliente(docente)
