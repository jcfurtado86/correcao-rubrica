"""Lotes e respostas anonimizadas (data-model.md, lotes).

`Resposta` não tem campo algum de identificador: nome, e-mail e matrícula do
estudante nunca chegam ao banco (Princípio IV). O texto guardado já passou pela
anonimização na carga.
"""

from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


def _teto_padrao():
    return Decimal(str(settings.TETO_USD_PADRAO))


def _provedor_padrao():
    return settings.LLM_PROVIDER


def _modelo_padrao():
    from conectores.llm import modelo_padrao

    return modelo_padrao(settings.LLM_PROVIDER)


class Lote(models.Model):
    dono = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="lotes"
    )
    titulo = models.CharField(max_length=200)
    enunciado = models.TextField()
    versao_rubrica = models.ForeignKey(
        "rubricas.VersaoRubrica", on_delete=models.PROTECT, related_name="lotes"
    )
    n_execucoes = models.PositiveSmallIntegerField(
        default=5, validators=[MinValueValidator(1), MaxValueValidator(10)]
    )
    limiar_acordo = models.DecimalField(max_digits=3, decimal_places=2, default=Decimal("0.80"))
    min_validas = models.PositiveSmallIntegerField(default=3, validators=[MinValueValidator(1)])
    provedor_llm = models.CharField(max_length=20, default=_provedor_padrao)
    modelo_llm = models.CharField(max_length=60, default=_modelo_padrao)
    teto_usd = models.DecimalField(max_digits=8, decimal_places=2, default=_teto_padrao)
    sintetico = models.BooleanField(
        default=False, help_text="Lote de teste; pode usar provedor fora do nível pago."
    )
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-criado_em"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(limiar_acordo__gt=Decimal("0.5"), limiar_acordo__lte=1),
                name="limiar_entre_meio_e_um",
            ),
            models.CheckConstraint(
                condition=models.Q(n_execucoes__gte=1, n_execucoes__lte=10),
                name="n_execucoes_1_a_10",
            ),
            models.CheckConstraint(
                condition=models.Q(min_validas__gte=1, min_validas__lte=models.F("n_execucoes")),
                name="min_validas_ate_n",
            ),
        ]

    def __str__(self):
        return self.titulo

    def clean(self):
        erros = {}
        if not self.enunciado or not self.enunciado.strip():
            erros["enunciado"] = "O enunciado é obrigatório."
        if self.limiar_acordo is not None and not (Decimal("0.5") < self.limiar_acordo <= 1):
            erros["limiar_acordo"] = "O limiar precisa estar em (0,5; 1,0]."
        if self.n_execucoes is not None and not (1 <= self.n_execucoes <= 10):
            erros["n_execucoes"] = "Use de 1 a 10 execuções."
        if self.min_validas is not None and self.n_execucoes is not None:
            if not (1 <= self.min_validas <= self.n_execucoes):
                erros["min_validas"] = "O mínimo de válidas vai de 1 até o número de execuções."
        if erros:
            raise ValidationError(erros)

    @property
    def congelado(self) -> bool:
        return self.rodadas.exists()


class Resposta(models.Model):
    class Aviso(models.TextChoices):
        VAZIA = "VAZIA", "Vazia"
        LONGA = "LONGA", "Acima do limite"

    lote = models.ForeignKey(Lote, on_delete=models.CASCADE, related_name="respostas")
    codigo = models.CharField(max_length=10)
    texto = models.TextField(blank=True)
    hash_texto = models.CharField(max_length=64)
    n_substituicoes = models.PositiveIntegerField(default=0)
    aviso = models.CharField(  # noqa: DJ001 — null = sem aviso (contrato)
        max_length=5, choices=Aviso.choices, null=True, blank=True
    )
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["lote", "codigo"]
        constraints = [
            models.UniqueConstraint(fields=["lote", "codigo"], name="codigo_unico_por_lote")
        ]

    def __str__(self):
        return self.codigo

    def save(self, *args, **kwargs):
        import hashlib

        if self.pk:
            original = Resposta.objects.filter(pk=self.pk).values_list("texto", flat=True).first()
            if original is not None and original != self.texto:
                raise ValidationError("O texto da resposta é imutável depois da carga.")
        self.hash_texto = hashlib.sha256(self.texto.encode("utf-8")).hexdigest()
        return super().save(*args, **kwargs)
