"""Uso: manage.py auditar_identificadores <identificadores.txt> [--logs arq ...]

Sai com código 1 se encontrar qualquer identificador (quickstart V1, SC-003).
"""

import sys
from pathlib import Path

from django.core.management.base import BaseCommand

from lotes.auditoria import procurar_identificadores


class Command(BaseCommand):
    help = "Procura identificadores plantados no banco e em arquivos de log."

    def add_arguments(self, parser):
        parser.add_argument("arquivo", help="Um identificador por linha.")
        parser.add_argument("--logs", nargs="*", default=[], help="Arquivos de log a varrer.")

    def handle(self, *args, arquivo, logs, **opcoes):
        identificadores = [
            linha.strip()
            for linha in Path(arquivo).read_text(encoding="utf-8").splitlines()
            if linha.strip()
        ]
        achados = procurar_identificadores(identificadores)
        if logs:
            textos = {
                f"log:{c}": [Path(c).read_text(encoding="utf-8", errors="replace")] for c in logs
            }
            achados.update(procurar_identificadores(identificadores, textos=textos))
        self.stdout.write(f"{len(identificadores)} identificadores procurados.")
        for onde, n in sorted(achados.items()):
            self.stdout.write(f"  {onde}: {n}")
        total = sum(achados.values())
        self.stdout.write(f"Total: {total} ocorrência(s).")
        if total:
            sys.exit(1)
