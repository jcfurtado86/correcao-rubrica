"""Estudo com docentes, protocolo A (data-model.md, estudos; research R12).

As respostas elegíveis do lote comum são divididas em metades A e B. Cada
participante corrige uma metade sem apoio e a outra com apoio (braço), numa das
duas ordens. Assim cada resposta recebe decisões cegas de um grupo e assistidas
do outro.
"""

from django.conf import settings
from django.db import models


class Estudo(models.Model):
    class Status(models.TextChoices):
        PREPARACAO = "PREPARACAO", "Em preparação"
        EM_ANDAMENTO = "EM_ANDAMENTO", "Em andamento"
        ENCERRADO = "ENCERRADO", "Encerrado"

    pesquisador = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="estudos_criados"
    )
    titulo = models.CharField(max_length=200)
    lote = models.ForeignKey("lotes.Lote", on_delete=models.PROTECT, related_name="estudos")
    rodada = models.ForeignKey("avaliacao.Rodada", on_delete=models.PROTECT, related_name="+")
    semente_alocacao = models.BigIntegerField()
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PREPARACAO)
    criado_em = models.DateTimeField(auto_now_add=True)
    iniciado_em = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-criado_em"]

    def __str__(self):
        return self.titulo


class AlocacaoResposta(models.Model):
    class Metade(models.TextChoices):
        A = "A", "Metade A"
        B = "B", "Metade B"

    estudo = models.ForeignKey(Estudo, on_delete=models.CASCADE, related_name="alocacoes")
    resposta = models.ForeignKey("lotes.Resposta", on_delete=models.PROTECT, related_name="+")
    metade = models.CharField(max_length=1, choices=Metade.choices)

    class Meta:
        ordering = ["estudo", "resposta"]
        constraints = [
            models.UniqueConstraint(fields=["estudo", "resposta"], name="alocacao_unica")
        ]
        verbose_name = "alocação de resposta"
        verbose_name_plural = "alocações de respostas"

    def __str__(self):
        return f"{self.estudo} · {self.resposta} · {self.metade}"


class Participacao(models.Model):
    class Ordem(models.TextChoices):
        SEM_PRIMEIRO = "SEM_PRIMEIRO", "Sem apoio primeiro"
        COM_PRIMEIRO = "COM_PRIMEIRO", "Com apoio primeiro"

    estudo = models.ForeignKey(Estudo, on_delete=models.CASCADE, related_name="participacoes")
    docente = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="participacoes"
    )
    posicao = models.PositiveIntegerField()
    braco = models.PositiveSmallIntegerField(null=True, blank=True)  # 1 ou 2, ao iniciar
    ordem = models.CharField(max_length=12, choices=Ordem.choices, blank=True)
    concluida_em = models.DateTimeField(null=True, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["estudo", "posicao"]
        constraints = [
            models.UniqueConstraint(fields=["estudo", "docente"], name="participacao_unica"),
            models.UniqueConstraint(fields=["estudo", "posicao"], name="posicao_unica"),
        ]
        verbose_name = "participação"
        verbose_name_plural = "participações"

    def __str__(self):
        return f"{self.estudo} · {self.docente}"
