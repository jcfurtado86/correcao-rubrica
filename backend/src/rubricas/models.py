"""Rubricas versionadas (data-model.md, rubricas).

Versão usada por um lote pré-avaliado fica **congelada** (FR-002): nem ela nem
seus critérios e níveis mudam mais. Editar gera versão nova.
"""

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models


class VersaoCongelada(Exception):
    pass


class Rubrica(models.Model):
    dono = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="rubricas"
    )
    titulo = models.CharField(max_length=200)
    descricao = models.TextField(blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-criado_em"]

    def __str__(self):
        return self.titulo

    @property
    def versao_vigente(self) -> "VersaoRubrica":
        return self.versoes.order_by("-numero").first()


class VersaoRubrica(models.Model):
    rubrica = models.ForeignKey(Rubrica, on_delete=models.CASCADE, related_name="versoes")
    numero = models.PositiveIntegerField()
    congelada = models.BooleanField(default=False)
    hash = models.CharField(max_length=64, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["rubrica", "numero"], name="versao_unica_por_rubrica")
        ]
        ordering = ["rubrica", "numero"]
        verbose_name = "versão de rubrica"
        verbose_name_plural = "versões de rubrica"

    def __str__(self):
        return f"{self.rubrica} v{self.numero}"

    def delete(self, *args, **kwargs):
        if self.congelada:
            raise VersaoCongelada("Versão congelada não pode ser apagada.")
        return super().delete(*args, **kwargs)


class _ProtegidoPelaVersao(models.Model):
    """Critério e nível herdam o congelamento da versão a que pertencem."""

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        if self.pk and self._versao().congelada:
            raise VersaoCongelada("Versão congelada não aceita alteração.")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if self._versao().congelada:
            raise VersaoCongelada("Versão congelada não aceita alteração.")
        return super().delete(*args, **kwargs)

    def _versao(self) -> VersaoRubrica:
        raise NotImplementedError


class Criterio(_ProtegidoPelaVersao):
    class Tipo(models.TextChoices):
        OBJETIVO = "OBJETIVO", "Objetivo"
        INTERPRETATIVO = "INTERPRETATIVO", "Interpretativo"

    versao = models.ForeignKey(VersaoRubrica, on_delete=models.CASCADE, related_name="criterios")
    ordem = models.PositiveIntegerField()
    nome = models.CharField(max_length=200)
    descricao = models.TextField(blank=True)
    peso = models.DecimalField(
        max_digits=6, decimal_places=2, default=1, validators=[MinValueValidator(0)]
    )
    tipo = models.CharField(max_length=14, choices=Tipo.choices, default=Tipo.INTERPRETATIVO)

    class Meta:
        ordering = ["versao", "ordem"]
        constraints = [
            models.UniqueConstraint(fields=["versao", "ordem"], name="ordem_unica_de_criterio"),
            models.CheckConstraint(condition=models.Q(peso__gte=0), name="peso_nao_negativo"),
        ]
        verbose_name = "critério"

    def __str__(self):
        return self.nome

    def _versao(self):
        return self.versao


class Nivel(_ProtegidoPelaVersao):
    criterio = models.ForeignKey(Criterio, on_delete=models.CASCADE, related_name="niveis")
    ordem = models.PositiveIntegerField()
    codigo = models.CharField(max_length=8)
    rotulo = models.CharField(max_length=100)
    descritor = models.TextField(blank=True)
    pontuacao = models.DecimalField(max_digits=6, decimal_places=2)

    class Meta:
        ordering = ["criterio", "ordem"]
        constraints = [
            models.UniqueConstraint(fields=["criterio", "ordem"], name="ordem_unica_de_nivel"),
            models.UniqueConstraint(fields=["criterio", "codigo"], name="codigo_unico_de_nivel"),
        ]
        verbose_name = "nível"
        verbose_name_plural = "níveis"

    def __str__(self):
        return f"{self.codigo} {self.rotulo}"

    def _versao(self):
        return self.criterio.versao
