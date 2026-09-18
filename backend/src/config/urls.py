from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

APPS_COM_ROTAS = ["core", "rubricas", "lotes", "avaliacao", "revisao", "estudos", "metricas"]


def _rotas_das_apps():
    from importlib import import_module
    from importlib.util import find_spec

    rotas = []
    for app in APPS_COM_ROTAS:
        if find_spec(f"{app}.urls") is not None:
            rotas.append(path("api/", include(import_module(f"{app}.urls"))))
    return rotas


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="docs"),
    *_rotas_das_apps(),
]
