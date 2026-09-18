"""Semente de cada execução (research R3).

Distinta por execução: semente fixa fez o Gemini repetir a resposta byte a byte
no piloto, o que esconde a instabilidade em vez de medi-la. Derivada da
`semente_base` da rodada: recalcular a mesma rodada dá as mesmas sementes
(auditoria); a reaplicação sorteia outra base.
"""

import hashlib


def semente(semente_base: int, resposta_id: int, criterio_id: int, indice: int) -> int:
    chave = f"{semente_base}:{resposta_id}:{criterio_id}:{indice}".encode()
    return int(hashlib.sha256(chave).hexdigest(), 16) % 2**31
