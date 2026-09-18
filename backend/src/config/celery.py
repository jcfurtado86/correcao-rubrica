"""Worker Celery: uma tarefa por execução de pré-avaliação (research R8)."""

import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("correcao")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
