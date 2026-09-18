from rest_framework import serializers

from rubricas.models import Criterio, Nivel, Rubrica, VersaoRubrica


class NivelEntrada(serializers.Serializer):
    rotulo = serializers.CharField(max_length=100)
    pontuacao = serializers.DecimalField(max_digits=6, decimal_places=2)
    descritor = serializers.CharField(allow_blank=True, required=False, default="")


class CriterioEntrada(serializers.Serializer):
    nome = serializers.CharField(max_length=200)
    descricao = serializers.CharField(allow_blank=True, required=False, default="")
    peso = serializers.DecimalField(max_digits=6, decimal_places=2, min_value=0, default=1)
    tipo = serializers.ChoiceField(
        choices=Criterio.Tipo.choices, default=Criterio.Tipo.INTERPRETATIVO
    )
    niveis = NivelEntrada(many=True, min_length=2)


class RubricaEntrada(serializers.Serializer):
    titulo = serializers.CharField(max_length=200)
    descricao = serializers.CharField(allow_blank=True, required=False, default="")
    criterios = CriterioEntrada(many=True, min_length=1)


class NivelSaida(serializers.ModelSerializer):
    class Meta:
        model = Nivel
        fields = ["id", "ordem", "codigo", "rotulo", "descritor", "pontuacao"]


class CriterioSaida(serializers.ModelSerializer):
    niveis = NivelSaida(many=True)

    class Meta:
        model = Criterio
        fields = ["id", "ordem", "nome", "descricao", "peso", "tipo", "niveis"]


class VersaoSaida(serializers.ModelSerializer):
    criterios = CriterioSaida(many=True)
    em_uso = serializers.SerializerMethodField()

    class Meta:
        model = VersaoRubrica
        fields = ["id", "numero", "congelada", "hash", "em_uso", "criterios"]

    def get_em_uso(self, versao):
        return versao.lotes.exists()


class VersaoResumo(serializers.ModelSerializer):
    class Meta:
        model = VersaoRubrica
        fields = ["id", "numero", "congelada"]


class RubricaResumo(serializers.ModelSerializer):
    versao_vigente = VersaoResumo()
    n_criterios = serializers.SerializerMethodField()

    class Meta:
        model = Rubrica
        fields = ["id", "titulo", "descricao", "versao_vigente", "n_criterios", "criado_em"]

    def get_n_criterios(self, rubrica):
        return rubrica.versao_vigente.criterios.count()


def rubrica_completa(rubrica: Rubrica, versao: VersaoRubrica | None = None) -> dict:
    versao = versao or rubrica.versao_vigente
    return {
        "id": rubrica.id,
        "titulo": rubrica.titulo,
        "descricao": rubrica.descricao,
        "versao": VersaoSaida(versao).data,
    }
