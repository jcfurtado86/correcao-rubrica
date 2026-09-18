"""Sessões de correção e decisões docentes (data-model.md, revisao; Princípio I).

A decisão é o único caminho para uma nota existir. Cada decisão guarda a foto do
que a docente viu (estado e nível sugerido) e o tempo ativo acumulado; decidir de
novo o mesmo critério cria outra decisão, e a anterior fica no histórico.
"""

from django.conf import settings
from django.db import models


class Condicao(models.TextChoices):
    COM_APOIO = "COM_APOIO", "Com apoio"
    SEM_APOIO = "SEM_APOIO", "Sem apoio"


class SessaoCorrecao(models.Model):
    docente = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="sessoes"
    )
    resposta = models.ForeignKey("lotes.Resposta", on_delete=models.CASCADE, related_name="sessoes")
    condicao = models.CharField(max_length=9, choices=Condicao.choices, default=Condicao.COM_APOIO)
    rodada = models.ForeignKey(
        "avaliacao.Rodada", on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )
    aberta_em = models.DateTimeField(auto_now_add=True)
    # Tempo ativo no momento da última decisão: é a métrica (FR-020). Sessão sem
    # decisão fica com 0 e não entra na conta.
    tempo_ativo_ms = models.PositiveIntegerField(default=0)
    # Último valor recebido pela batida periódica (diagnóstico, não é métrica).
    tempo_total_ms = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["-aberta_em"]
        verbose_name = "sessão de correção"
        verbose_name_plural = "sessões de correção"

    def __str__(self):
        return f"{self.resposta} · {self.docente} · {self.condicao}"


class Decisao(models.Model):
    class Tipo(models.TextChoices):
        CONFIRMACAO = "CONFIRMACAO", "Confirmação da sugestão"
        ALTERACAO = "ALTERACAO", "Alteração da sugestão"
        ESCOLHA = "ESCOLHA", "Escolha sem sugestão"
        CEGA = "CEGA", "Condição sem apoio"

    class EstadoExibido(models.TextChoices):
        CONVERGENTE = "CONVERGENTE", "Convergente"
        DIVERGENTE = "DIVERGENTE", "Divergente"
        SEM_EVIDENCIA = "SEM_EVIDENCIA", "Sem evidência"
        INDETERMINADO = "INDETERMINADO", "Indeterminado"
        INDISPONIVEL = "INDISPONIVEL", "Sem pré-avaliação"
        OCULTO = "OCULTO", "Oculto (sem apoio)"

    sessao = models.ForeignKey(SessaoCorrecao, on_delete=models.CASCADE, related_name="decisoes")
    # Desnormalizados da sessão para a restrição de vigência única.
    resposta = models.ForeignKey(
        "lotes.Resposta", on_delete=models.CASCADE, related_name="decisoes"
    )
    docente = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="decisoes"
    )
    criterio = models.ForeignKey("rubricas.Criterio", on_delete=models.PROTECT, related_name="+")
    nivel = models.ForeignKey("rubricas.Nivel", on_delete=models.PROTECT, related_name="+")
    estado_exibido = models.CharField(max_length=13, choices=EstadoExibido.choices)
    nivel_sugerido = models.ForeignKey(
        "rubricas.Nivel", on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )
    tipo = models.CharField(max_length=11, choices=Tipo.choices)
    motivo = models.TextField(blank=True)
    tempo_ativo_ms = models.PositiveIntegerField(default=0)
    substitui = models.OneToOneField(
        "self", on_delete=models.PROTECT, null=True, blank=True, related_name="substituida_por"
    )
    vigente = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["criado_em", "id"]
        verbose_name = "decisão"
        verbose_name_plural = "decisões"
        constraints = [
            models.UniqueConstraint(
                fields=["resposta", "criterio", "docente"],
                condition=models.Q(vigente=True),
                name="decisao_vigente_unica",
            )
        ]

    def __str__(self):
        return f"{self.resposta} · {self.criterio}: {self.nivel.codigo} ({self.tipo})"
