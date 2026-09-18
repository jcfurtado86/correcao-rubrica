"""Rodadas, execuções e trechos (data-model.md, avaliacao).

Toda execução é persistida, e não só o consolidado (Princípio III): é o que
permite recalcular a consolidação com outro limiar sem chamar o modelo de novo,
e auditar cada julgamento (Princípio V).
"""

from django.conf import settings
from django.db import models


class Rodada(models.Model):
    class Status(models.TextChoices):
        ESTIMADA = "ESTIMADA", "Estimada"
        EM_EXECUCAO = "EM_EXECUCAO", "Em execução"
        PAUSADA_TETO = "PAUSADA_TETO", "Pausada pelo teto de custo"
        CONCLUIDA = "CONCLUIDA", "Concluída"
        COM_FALHAS = "COM_FALHAS", "Concluída com falhas"

    lote = models.ForeignKey("lotes.Lote", on_delete=models.CASCADE, related_name="rodadas")
    numero = models.PositiveIntegerField()
    semente_base = models.BigIntegerField()
    versao_prompt = models.CharField(max_length=60)
    provedor = models.CharField(max_length=20)
    modelo = models.CharField(max_length=60)
    custo_estimado_usd = models.DecimalField(max_digits=12, decimal_places=6, default=0)
    custo_previsto_chamada_usd = models.DecimalField(max_digits=12, decimal_places=8, default=0)
    custo_acumulado_usd = models.DecimalField(max_digits=12, decimal_places=6, default=0)
    teto_usd = models.DecimalField(max_digits=8, decimal_places=2)
    confirmada_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="rodadas_confirmadas"
    )
    status = models.CharField(max_length=13, choices=Status.choices, default=Status.ESTIMADA)
    criado_em = models.DateTimeField(auto_now_add=True)
    concluida_em = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["lote", "numero"]
        constraints = [
            models.UniqueConstraint(fields=["lote", "numero"], name="rodada_unica_por_lote")
        ]

    def __str__(self):
        return f"{self.lote} — rodada {self.numero}"


class Execucao(models.Model):
    class Status(models.TextChoices):
        PENDENTE = "PENDENTE", "Pendente"
        EM_ANDAMENTO = "EM_ANDAMENTO", "Em andamento"
        CONCLUIDA = "CONCLUIDA", "Concluída"
        FALHOU = "FALHOU", "Falhou"

    class Motivo(models.TextChoices):
        JSON_INVALIDO = "JSON_INVALIDO", "JSON inválido"
        NIVEL_FORA = "NIVEL_FORA", "Nível fora da rubrica"
        SEM_TRECHO = "SEM_TRECHO", "Nível sem trecho de apoio"
        TRECHO_NAO_LOCALIZADO = "TRECHO_NAO_LOCALIZADO", "Trecho não localizado no texto"
        TRECHO_CURTO = "TRECHO_CURTO", "Trecho curto demais"
        INCOERENTE_SEM_EVIDENCIA = "INCOERENTE_SEM_EVIDENCIA", "Sem evidência com trecho"

    rodada = models.ForeignKey(Rodada, on_delete=models.CASCADE, related_name="execucoes")
    resposta = models.ForeignKey(
        "lotes.Resposta", on_delete=models.CASCADE, related_name="execucoes"
    )
    criterio = models.ForeignKey(
        "rubricas.Criterio", on_delete=models.PROTECT, related_name="execucoes"
    )
    indice = models.PositiveSmallIntegerField()
    semente = models.BigIntegerField()
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PENDENTE)
    valida = models.BooleanField(null=True)
    # null (e não "") porque o contrato devolve `null` quando a execução é válida.
    motivo_invalidez = models.CharField(  # noqa: DJ001
        max_length=24, choices=Motivo.choices, null=True, blank=True
    )
    nivel_codigo = models.CharField(max_length=16, blank=True)
    nivel = models.ForeignKey(
        "rubricas.Nivel", on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )
    justificativa = models.TextField(blank=True)
    resposta_bruta = models.TextField(blank=True)
    tokens_entrada = models.PositiveIntegerField(default=0)
    tokens_saida = models.PositiveIntegerField(default=0)
    tokens_raciocinio = models.PositiveIntegerField(default=0)
    custo_usd = models.DecimalField(max_digits=12, decimal_places=8, default=0)
    latencia_ms = models.PositiveIntegerField(default=0)
    tentativas = models.PositiveSmallIntegerField(default=0)
    erro = models.TextField(null=True, blank=True)  # noqa: DJ001 — null = sem erro
    criado_em = models.DateTimeField(auto_now_add=True)
    iniciada_em = models.DateTimeField(null=True, blank=True)
    concluida_em = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["rodada", "resposta", "criterio", "indice"]
        constraints = [
            models.UniqueConstraint(
                fields=["rodada", "resposta", "criterio", "indice"], name="execucao_unica"
            )
        ]
        indexes = [models.Index(fields=["rodada", "status"])]
        verbose_name = "execução"
        verbose_name_plural = "execuções"

    def __str__(self):
        return f"{self.resposta} · {self.criterio} · #{self.indice}"


class Trecho(models.Model):
    execucao = models.ForeignKey(Execucao, on_delete=models.CASCADE, related_name="trechos")
    texto_citado = models.TextField()
    localizado = models.BooleanField(default=False)
    inicio = models.PositiveIntegerField(null=True, blank=True)
    fim = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        ordering = ["execucao", "id"]

    def __str__(self):
        return self.texto_citado[:60]
