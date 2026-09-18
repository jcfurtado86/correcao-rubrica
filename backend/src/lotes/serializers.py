from decimal import Decimal

from django.conf import settings
from rest_framework import serializers

from conectores.llm import modelo_padrao
from lotes.models import Lote, Resposta
from rubricas.models import VersaoRubrica


class LoteEntrada(serializers.Serializer):
    titulo = serializers.CharField(max_length=200)
    enunciado = serializers.CharField()
    versao_rubrica = serializers.PrimaryKeyRelatedField(queryset=VersaoRubrica.objects.none())
    n_execucoes = serializers.IntegerField(min_value=1, max_value=10, default=5)
    limiar_acordo = serializers.DecimalField(
        max_digits=3, decimal_places=2, default=Decimal("0.80")
    )
    min_validas = serializers.IntegerField(min_value=1, default=3)
    provedor_llm = serializers.CharField(required=False)
    modelo_llm = serializers.CharField(required=False)
    teto_usd = serializers.DecimalField(max_digits=8, decimal_places=2, min_value=0, required=False)
    sintetico = serializers.BooleanField(default=False)

    def __init__(self, *args, dono=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["versao_rubrica"].queryset = VersaoRubrica.objects.filter(rubrica__dono=dono)

    def validate_limiar_acordo(self, valor):
        if not (Decimal("0.5") < valor <= 1):
            raise serializers.ValidationError("O limiar precisa estar em (0,5; 1,0].")
        return valor

    def validate(self, dados):
        if dados["min_validas"] > dados["n_execucoes"]:
            raise serializers.ValidationError(
                {"min_validas": "O mínimo de válidas não pode passar do número de execuções."}
            )
        provedor = dados.get("provedor_llm") or settings.LLM_PROVIDER
        modelo = dados.get("modelo_llm") or modelo_padrao(provedor)
        if "provedor_llm" in dados or "modelo_llm" in dados:
            from conectores.catalogo import modelos_disponiveis

            disponiveis = {(m["provedor"], m["modelo"]) for m in modelos_disponiveis()}
            if (provedor, modelo) not in disponiveis:
                raise serializers.ValidationError(
                    {"modelo_llm": "Modelo indisponível neste servidor."}
                )
        dados["provedor_llm"], dados["modelo_llm"] = provedor, modelo
        return dados


class LoteResumo(serializers.ModelSerializer):
    n_respostas = serializers.IntegerField(read_only=True)
    rubrica_titulo = serializers.CharField(source="versao_rubrica.rubrica.titulo", read_only=True)

    class Meta:
        model = Lote
        fields = [
            "id",
            "titulo",
            "enunciado",
            "versao_rubrica",
            "rubrica_titulo",
            "n_execucoes",
            "limiar_acordo",
            "min_validas",
            "provedor_llm",
            "modelo_llm",
            "teto_usd",
            "sintetico",
            "criado_em",
            "n_respostas",
        ]


class RespostaResumo(serializers.ModelSerializer):
    n_caracteres = serializers.SerializerMethodField()

    class Meta:
        model = Resposta
        fields = ["id", "codigo", "n_caracteres", "n_substituicoes", "aviso"]

    def get_n_caracteres(self, resposta):
        return len(resposta.texto)
