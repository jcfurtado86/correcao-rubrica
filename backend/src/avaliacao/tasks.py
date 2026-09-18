"""Tarefa Celery: uma por execução (research R8).

A lógica mora em `services.processar_execucao`, testável sem worker. Aqui fica
só a política de nova tentativa: falha passageira (429/5xx/rede) volta para a
fila com espera exponencial e variação aleatória, até LLM_MAX_TENTATIVAS.

Em modo síncrono (testes, `task_always_eager`) a nova tentativa é feita em laço,
sem espera: com `task_eager_propagates` o Celery propaga o `Retry` em vez de
reexecutar a tarefa.
"""

import random

from celery import shared_task
from django.conf import settings


def espera(tentativa: int) -> int:
    base = min(2 ** (tentativa + 1), 120)
    return base + random.randint(0, base)


@shared_task(bind=True, acks_late=True, rate_limit=settings.LLM_RATE_LIMIT, max_retries=None)
def executar_execucao(self, execucao_id: int):
    from avaliacao.services import RETENTAR, processar_execucao

    tentativa = self.request.retries
    while True:
        resultado = processar_execucao(execucao_id, tentativa=tentativa)
        if resultado != RETENTAR:
            return resultado
        if not self.request.is_eager:
            raise self.retry(countdown=espera(tentativa))
        tentativa += 1
