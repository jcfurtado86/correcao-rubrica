"""Alocação do protocolo A (research R12). Funções puras.

- Metades A/B estratificadas por "a resposta tem critério não convergente?",
  para que as duas metades tenham dificuldade parecida.
- Participantes em rodízio pelas 4 células (braço × ordem), na ordem do convite.
- Dentro de cada bloco, ordem das respostas embaralhada por participante
  (reprodutível), para não confundir efeito de ordem com efeito de condição.
"""

import hashlib
import random

# Rodízio: os dois primeiros já cobrem os dois braços e as duas ordens.
CELULAS = [(1, "SEM_PRIMEIRO"), (2, "COM_PRIMEIRO"), (2, "SEM_PRIMEIRO"), (1, "COM_PRIMEIRO")]


def dividir_metades(itens: list[tuple[int, bool]], semente: int) -> dict[int, str]:
    """`itens`: (id da resposta, é não convergente). Devolve {id: "A" | "B"}."""
    sorteio = random.Random(semente)
    metades: dict[int, str] = {}
    contagem = {"A": 0, "B": 0}
    for estrato in (True, False):
        ids = sorted(i for i, e in itens if e is estrato)
        sorteio.shuffle(ids)
        # Cada estrato começa pela metade que está menor: equilíbrio total ±1.
        primeira = "A" if contagem["A"] <= contagem["B"] else "B"
        segunda = "B" if primeira == "A" else "A"
        for posicao, resposta_id in enumerate(ids):
            metade = primeira if posicao % 2 == 0 else segunda
            metades[resposta_id] = metade
            contagem[metade] += 1
    return metades


def alocar_participantes(n: int) -> list[tuple[int, str]]:
    return [CELULAS[i % len(CELULAS)] for i in range(n)]


def condicao(metade: str, braco: int) -> str:
    """Braço 1: A sem apoio, B com apoio. Braço 2: o inverso."""
    sem_apoio = "A" if braco == 1 else "B"
    return "SEM_APOIO" if metade == sem_apoio else "COM_APOIO"


def blocos(braco: int, ordem: str) -> list[tuple[str, str]]:
    sem = ("A" if braco == 1 else "B", "SEM_APOIO")
    com = ("B" if braco == 1 else "A", "COM_APOIO")
    return [sem, com] if ordem == "SEM_PRIMEIRO" else [com, sem]


def ordem_do_bloco(ids: list[int], semente: int, participacao_id: int) -> list[int]:
    chave = hashlib.sha256(f"{semente}:{participacao_id}".encode()).hexdigest()
    embaralhados = sorted(ids)
    random.Random(int(chave, 16)).shuffle(embaralhados)
    return embaralhados
