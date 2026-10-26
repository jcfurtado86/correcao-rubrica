from rest_framework import serializers

from avaliacao.models import Rodada
from estudos.models import Questionario
from lotes.models import Lote


class EstudoEntrada(serializers.Serializer):
    titulo = serializers.CharField(max_length=200)
    lote = serializers.PrimaryKeyRelatedField(queryset=Lote.objects.all())
    rodada = serializers.PrimaryKeyRelatedField(queryset=Rodada.objects.all())


class ConvitesEntrada(serializers.Serializer):
    emails = serializers.ListField(child=serializers.EmailField(), min_length=1, max_length=50)


def _escala():
    return serializers.IntegerField(min_value=1, max_value=5)


class QuestionarioEntrada(serializers.Serializer):
    nivel = serializers.ChoiceField(choices=Questionario.Nivel.choices)
    tempo_docencia = serializers.ChoiceField(choices=Questionario.Tempo.choices)
    uso_ia = serializers.ChoiceField(choices=Questionario.UsoIA.choices)
    o_que_ajudou = serializers.CharField(max_length=3000, allow_blank=True, required=False)
    o_que_mudaria = serializers.CharField(max_length=3000, allow_blank=True, required=False)

    def get_fields(self):
        campos = super().get_fields()
        for i in range(1, 6):
            campos[f"apoio_{i}"] = _escala()
        for i in range(1, 11):
            campos[f"sus_{i}"] = _escala()
        return campos


class ConsentimentoEntrada(serializers.Serializer):
    aceito = serializers.BooleanField()
    autoriza_imagem = serializers.BooleanField()

    def validate_aceito(self, valor):
        if not valor:
            raise serializers.ValidationError("É preciso aceitar o termo para participar.")
        return valor
