"""Cria a rubrica de exemplo "Verificação e validação" (quickstart, "Subir").

Uso: manage.py carregar_exemplo [--email pessoa@exemplo.org]
Sem --email, usa o primeiro superusuário. A planilha sintética fica em
dados_sinteticos/turma_ficticia.xlsx para ser importada pela interface.
"""

import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from core.models import Usuario
from rubricas.modelo import importar

MODELO = Path(__file__).resolve().parents[5] / "docs" / "modelos" / "verificacao-validacao.json"


class Command(BaseCommand):
    help = "Cria a rubrica 4×4 de exemplo para um usuário."

    def add_arguments(self, parser):
        parser.add_argument("--email", help="Dono da rubrica (padrão: primeiro superusuário).")
        parser.add_argument("--modelo", default=str(MODELO), help="Arquivo de modelo JSON.")

    def handle(self, *args, email=None, modelo=None, **opcoes):
        dono = (
            Usuario.objects.filter(email=email).first()
            if email
            else Usuario.objects.filter(is_superuser=True).order_by("id").first()
        )
        if dono is None:
            raise CommandError("Usuário não encontrado. Crie um com createsuperuser.")
        caminho = Path(modelo)
        if not caminho.exists():
            raise CommandError(f"Modelo não encontrado: {caminho}")
        rubrica = importar(dono, json.loads(caminho.read_text(encoding="utf-8")))
        self.stdout.write(f"Rubrica “{rubrica.titulo}” criada para {dono.email} (id {rubrica.id}).")
        self.stdout.write(
            "Importe dados_sinteticos/turma_ficticia.xlsx pela interface (Lotes → Novo lote)."
        )
