"""Verificação de âncora no servidor (research R5, Princípio II).

O trecho citado pelo modelo precisa existir no texto do estudante. A única
tolerância é de forma: espaços e quebras de linha, aspas e travessões
tipográficos, caixa, e pontuação sobrando no fim do trecho. Paráfrase,
reticências e trechos com menos de 3 palavras não são âncora. Não há
correspondência aproximada.

`normalizar_com_mapa` guarda, para cada caractere normalizado, a posição do
caractere original: é o que permite devolver `inicio`/`fim` no texto guardado.
"""

import unicodedata

TIPOGRAFICOS = str.maketrans(
    {
        "“": '"',
        "”": '"',
        "„": '"',
        "«": '"',
        "»": '"',
        "‘": "'",
        "’": "'",
        "‚": "'",
        "–": "-",
        "—": "-",
        "−": "-",
        "‐": "-",
        "‑": "-",
        " ": " ",
    }
)
RETICENCIAS = ("...", "…")
PONTUACAO_FINAL = ".,;:!?"
ASPAS_DE_BORDA = "\"'“”‘’«» "
MIN_PALAVRAS = 3


def normalizar_com_mapa(texto: str) -> tuple[str, list[int]]:
    saida: list[str] = []
    mapa: list[int] = []
    for posicao, caractere in enumerate(texto):
        normalizado = unicodedata.normalize("NFKC", caractere).translate(TIPOGRAFICOS).casefold()
        for c in normalizado:
            if c.isspace():
                if not saida or saida[-1] == " ":
                    continue
                c = " "
            saida.append(c)
            mapa.append(posicao)
    while saida and saida[-1] == " ":
        saida.pop()
        mapa.pop()
    return "".join(saida), mapa


def normalizar(texto: str) -> str:
    return normalizar_com_mapa(texto)[0]


def localizar(texto: str, trecho: str) -> tuple[int, int] | None:
    alvo = normalizar(unicodedata.normalize("NFC", trecho))
    if not alvo:
        return None
    normalizado, mapa = normalizar_com_mapa(texto)
    posicao = normalizado.find(alvo)
    if posicao < 0:
        return None
    return mapa[posicao], mapa[posicao + len(alvo) - 1] + 1


def verificar_trecho(texto: str, trecho: str) -> tuple[str | None, int | None, int | None]:
    """(motivo de invalidez ou None, início, fim)."""
    bruto = (trecho or "").strip().strip(ASPAS_DE_BORDA).strip()
    if any(r in bruto for r in RETICENCIAS):
        return "TRECHO_NAO_LOCALIZADO", None, None
    posicao = localizar(texto, bruto)
    if posicao is None:
        sem_pontuacao = bruto.rstrip(PONTUACAO_FINAL).rstrip()
        if sem_pontuacao and sem_pontuacao != bruto:
            posicao = localizar(texto, sem_pontuacao)
    inicio, fim = posicao if posicao else (None, None)
    if len(normalizar(bruto).split()) < MIN_PALAVRAS:
        return "TRECHO_CURTO", inicio, fim
    if posicao is None:
        return "TRECHO_NAO_LOCALIZADO", None, None
    return None, inicio, fim
