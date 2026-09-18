"""Consolidação das N execuções de um par (resposta, critério) (research R6).

Função pura. Só execuções **válidas** votam; `SEM_EVIDENCIA` é categoria de voto.
- menos válidas que o mínimo → INDETERMINADO;
- acordo do modal ≥ limiar → CONVERGENTE (ou SEM_EVIDENCIA, se o modal for ele);
- qualquer outro caso, inclusive empate → DIVERGENTE.

O modal é sempre devolvido (exibido só quando convergente): guardá-lo é o que
permite testar se a concordância com o docente é maior nos convergentes que nos
divergentes (hipótese SC-008a). Em empate, o modal é o nível que apareceu
primeiro (menor índice), para ser determinístico.
"""

from collections import Counter
from dataclasses import dataclass
from decimal import Decimal
from fractions import Fraction

SEM_EVIDENCIA = "SEM_EVIDENCIA"


@dataclass(frozen=True)
class Resultado:
    estado: str
    modal: str | None
    acordo: Decimal
    n_validas: int
    distribuicao: dict[str, int]


def consolidar(votos: list[tuple[int, str]], limiar, min_validas: int) -> Resultado:
    limiar = Fraction(str(limiar))
    if not (Fraction(1, 2) < limiar <= 1):
        raise ValueError("O limiar precisa estar em (0,5; 1,0].")
    ordenados = sorted(votos)
    n = len(ordenados)
    contagem = Counter(codigo for _, codigo in ordenados)
    distribuicao = dict(sorted(contagem.items()))
    if n == 0:
        return Resultado("INDETERMINADO", None, Decimal(0), 0, {})
    primeiro = {}
    for indice, codigo in ordenados:
        primeiro.setdefault(codigo, indice)
    modal = min(contagem, key=lambda c: (-contagem[c], primeiro[c]))
    votos_modal = contagem[modal]
    acordo = (Decimal(votos_modal) / Decimal(n)).quantize(Decimal("0.001"))
    if n < min_validas:
        estado = "INDETERMINADO"
    elif Fraction(votos_modal, n) >= limiar:
        estado = SEM_EVIDENCIA if modal == SEM_EVIDENCIA else "CONVERGENTE"
    else:
        estado = "DIVERGENTE"
    return Resultado(estado, modal, acordo, n, distribuicao)


def representativa_por_nivel(execucoes) -> dict:
    """Para cada nível votado, a execução válida de menor índice."""
    escolhidas: dict = {}
    for execucao in sorted(execucoes, key=lambda e: e.indice):
        escolhidas.setdefault(execucao.nivel_codigo, execucao)
    return escolhidas
