"""Estudo com docentes, protocolo A (data-model.md, estudos; research R12).

As respostas elegíveis do lote comum são divididas em metades A e B. Cada
participante corrige uma metade sem apoio e a outra com apoio (braço), numa das
duas ordens. Assim cada resposta recebe decisões cegas de um grupo e assistidas
do outro.
"""

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
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
    # TCLE (Instrumento 2) aceito na própria ferramenta, antes do primeiro bloco
    consentimento_em = models.DateTimeField(null=True, blank=True)
    autoriza_imagem = models.BooleanField(null=True, blank=True)
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


ESCALA_1_A_5 = [MinValueValidator(1), MaxValueValidator(5)]


class Questionario(models.Model):
    """Instrumentos 4 (formulário do participante) e 5 (SUS), respondidos no fim do estudo.

    Fica ligado à participação, nunca ao e-mail: a análise usa o código P01, P02…
    """

    class Nivel(models.TextChoices):
        SO_GRADUACAO = "SO_GRADUACAO", "Só graduação"
        GRADUACAO_POS = "GRADUACAO_POS", "Graduação e pós-graduação"
        BASICA_GRADUACAO = "BASICA_GRADUACAO", "Educação básica e graduação"

    class Tempo(models.TextChoices):
        MENOS_5 = "MENOS_5", "Menos de 5 anos"
        DE_5_A_15 = "DE_5_A_15", "De 5 a 15 anos"
        MAIS_15 = "MAIS_15", "Mais de 15 anos"

    class UsoIA(models.TextChoices):
        NUNCA = "NUNCA", "Nunca"
        ALGUMAS = "ALGUMAS", "Algumas vezes"
        FREQUENTE = "FREQUENTE", "Com frequência"

    participacao = models.OneToOneField(
        Participacao, on_delete=models.CASCADE, related_name="questionario"
    )
    nivel = models.CharField(max_length=16, choices=Nivel.choices)
    tempo_docencia = models.CharField(max_length=10, choices=Tempo.choices)
    uso_ia = models.CharField(max_length=10, choices=UsoIA.choices)
    apoio_1 = models.PositiveSmallIntegerField(validators=ESCALA_1_A_5)
    apoio_2 = models.PositiveSmallIntegerField(validators=ESCALA_1_A_5)
    apoio_3 = models.PositiveSmallIntegerField(validators=ESCALA_1_A_5)
    apoio_4 = models.PositiveSmallIntegerField(validators=ESCALA_1_A_5)
    apoio_5 = models.PositiveSmallIntegerField(validators=ESCALA_1_A_5)
    o_que_ajudou = models.TextField(blank=True)
    o_que_mudaria = models.TextField(blank=True)
    sus_1 = models.PositiveSmallIntegerField(validators=ESCALA_1_A_5)
    sus_2 = models.PositiveSmallIntegerField(validators=ESCALA_1_A_5)
    sus_3 = models.PositiveSmallIntegerField(validators=ESCALA_1_A_5)
    sus_4 = models.PositiveSmallIntegerField(validators=ESCALA_1_A_5)
    sus_5 = models.PositiveSmallIntegerField(validators=ESCALA_1_A_5)
    sus_6 = models.PositiveSmallIntegerField(validators=ESCALA_1_A_5)
    sus_7 = models.PositiveSmallIntegerField(validators=ESCALA_1_A_5)
    sus_8 = models.PositiveSmallIntegerField(validators=ESCALA_1_A_5)
    sus_9 = models.PositiveSmallIntegerField(validators=ESCALA_1_A_5)
    sus_10 = models.PositiveSmallIntegerField(validators=ESCALA_1_A_5)
    enviado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "questionário"
        verbose_name_plural = "questionários"

    def __str__(self):
        return f"Questionário · {self.participacao}"

    @property
    def sus_escore(self) -> float:
        """Ímpares: resposta − 1; pares: 5 − resposta; soma × 2,5 (0 a 100)."""
        soma = sum(
            (v - 1) if i % 2 == 1 else (5 - v)
            for i, v in ((i, getattr(self, f"sus_{i}")) for i in range(1, 11))
        )
        return soma * 2.5
