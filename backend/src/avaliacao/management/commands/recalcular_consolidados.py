from django.core.management.base import BaseCommand

from avaliacao.models import Rodada
from avaliacao.services import recalcular_rodada


class Command(BaseCommand):
    help = "Recalcula os consolidados de uma rodada a partir das execuções gravadas."

    def add_arguments(self, parser):
        parser.add_argument("--rodada", type=int, required=True)

    def handle(self, *args, rodada, **opcoes):
        n = recalcular_rodada(Rodada.objects.get(pk=rodada))
        self.stdout.write(f"{n} pares consolidados.")
