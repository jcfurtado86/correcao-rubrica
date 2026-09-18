"""Auditoria de identificadores (SC-003, quickstart V1).

Procura, sem acento e sem caixa e com limite de palavra, cada identificador
plantado em todas as colunas de texto de todos os modelos, ou nos textos
informados (logs, prompts). Devolve {onde: ocorrências} só com o que achou.
"""

import re

from django.apps import apps
from django.db import models

from lotes.anonimizacao import dobrar

CAMPOS_DE_TEXTO = (models.CharField, models.TextField, models.JSONField)


def _padrao(identificadores: list[str]) -> re.Pattern:
    alvos = sorted({dobrar(i.strip()) for i in identificadores if i.strip()}, key=len, reverse=True)
    return re.compile(r"(?<!\w)(?:" + "|".join(re.escape(a) for a in alvos) + r")(?!\w)")


def _contar(padrao: re.Pattern, valores) -> int:
    total = 0
    for valor in valores:
        if valor is None:
            continue
        total += len(padrao.findall(dobrar(str(valor))))
    return total


def procurar_identificadores(
    identificadores: list[str], textos: dict[str, list[str]] | None = None
) -> dict[str, int]:
    padrao = _padrao(identificadores)
    achados: dict[str, int] = {}
    if textos is not None:
        for onde, lista in textos.items():
            n = _contar(padrao, lista)
            if n:
                achados[onde] = n
        return achados
    for modelo in apps.get_models():
        for campo in modelo._meta.get_fields():
            if not isinstance(campo, CAMPOS_DE_TEXTO) or not getattr(campo, "column", None):
                continue
            valores = modelo._default_manager.values_list(campo.name, flat=True).iterator()
            n = _contar(padrao, valores)
            if n:
                achados[f"{modelo._meta.label}.{campo.name}"] = n
    return achados
