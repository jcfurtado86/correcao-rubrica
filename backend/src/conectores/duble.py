"""Dublê determinístico do modelo (research R14): testes e desenvolvimento offline.

Dois modos:
- **roteirizado**: se o texto da resposta contém `[[cenario:X]]`, o nível de cada
  execução segue o roteiro X pelo índice da execução. É o que permite testar a
  consolidação com distribuições conhecidas (quickstart V4).
- **pseudoaleatório**: sem marcador, o nível sai do hash do texto, com um desvio
  de um nível em ~1 de cada 5 sementes. Imita um modelo que quase sempre
  concorda consigo mesmo.

Em ambos, o trecho citado é uma frase real da resposta (substring literal),
exceto no roteiro `trecho_inventado`.
"""

import hashlib
import json
import re

from conectores.llm import LLMProvider, ResultadoLLM, registrar_provedor

MARCADOR = re.compile(r"\[\[cenario:([a-z0-9_\-]+)\]\]")
RESPOSTA = re.compile(r"<<<\n(.*)\n>>>", re.S)
FRASE_INVENTADA = "esta frase não existe na resposta do estudante"

# Roteiro -> nível por índice 1..5, como posição na lista de níveis (0 = 1º nível).
# "SE" = SEM_EVIDENCIA; "INV" = nível 2 com trecho inventado; "JSON" = saída quebrada.
ROTEIROS: dict[str, list] = {
    "unanime": [1, 1, 1, 1, 1],
    "4-1": [1, 1, 1, 1, 2],
    "3-2": [1, 1, 1, 2, 2],
    "2-2-1": [1, 1, 2, 2, 0],
    "sem_evidencia": ["SE"] * 5,
    "trecho_inventado": ["INV", "INV", 1, 1, 1],
    "json_invalido": ["JSON"] * 5,
}


def primeira_frase(texto: str) -> str | None:
    for pedaco in re.finditer(r"[^.!?\n]+", texto):
        frase = pedaco.group(0).strip()
        if len(frase.split()) >= 3:
            return frase
    return None


class DubleLLMProvider(LLMProvider):
    nome = "dumb"
    #: Todos os prompts recebidos, para a auditoria de identificadores (SC-003).
    prompts_recebidos: list[tuple[str, str]] = []

    def __init__(self, modelo: str | None = None):
        super().__init__("dublê")

    def avaliar(self, sistema, usuario, esquema, semente, indice=1):
        DubleLLMProvider.prompts_recebidos.append((sistema, usuario))
        achado = RESPOSTA.search(usuario)
        texto = achado.group(1) if achado else ""
        enum = esquema["properties"]["nivel"]["enum"]
        niveis = [c for c in enum if c != "SEM_EVIDENCIA"]
        marcador = MARCADOR.search(texto)
        texto_limpo = MARCADOR.sub("", texto)
        frase = primeira_frase(texto_limpo)

        if marcador and marcador.group(1) in ROTEIROS:
            passo = ROTEIROS[marcador.group(1)][(indice - 1) % 5]
        else:
            base = int(hashlib.sha256(texto.encode()).hexdigest(), 16) % len(niveis)
            passo = min(base + 1, len(niveis) - 1) if semente % 5 == 0 else base

        if passo == "JSON":
            saida = '{nivel: "N1", justificativa'
        elif passo == "SE" or frase is None:
            saida = json.dumps(
                {
                    "nivel": "SEM_EVIDENCIA",
                    "justificativa": "A resposta não trata do critério.",
                    "trechos": [],
                },
                ensure_ascii=False,
            )
        else:
            posicao = 1 if passo == "INV" else passo
            codigo = niveis[min(posicao, len(niveis) - 1)]
            trecho = FRASE_INVENTADA if passo == "INV" else frase
            saida = json.dumps(
                {
                    "nivel": codigo,
                    "justificativa": f"Dublê: nível {codigo} pelo trecho citado.",
                    "trechos": [trecho],
                },
                ensure_ascii=False,
            )
        return ResultadoLLM(
            texto=saida,
            tokens_entrada=len(sistema + usuario) // 4,
            tokens_saida=150,
            tokens_raciocinio=0,
            latencia_ms=1,
        )


registrar_provedor("dumb", DubleLLMProvider)
