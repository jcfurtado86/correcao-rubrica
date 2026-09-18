from rest_framework import serializers

from avaliacao.models import Rodada
from lotes.models import Lote


class EstudoEntrada(serializers.Serializer):
    titulo = serializers.CharField(max_length=200)
    lote = serializers.PrimaryKeyRelatedField(queryset=Lote.objects.all())
    rodada = serializers.PrimaryKeyRelatedField(queryset=Rodada.objects.all())


class ConvitesEntrada(serializers.Serializer):
    emails = serializers.ListField(child=serializers.EmailField(), min_length=1, max_length=50)
