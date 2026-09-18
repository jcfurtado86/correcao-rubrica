"""Montagem do prompt versionado e do esquema de saída (research R4).

Uma chamada por par (resposta, critério): o critério isolado evita que um
critério contamine o julgamento do outro e torna a divergência mensurável
critério a critério. O que é igual para todas as respostas de um critério
(instruções, enunciado, critério) vem antes da resposta, o que favorece o
cache de prefixo do provedor.
"""

from functools import cache
from pathlib import Path

from avaliacao.validacao import SEM_EVIDENCIA

VERSAO_PROMPT = "avaliar_criterio_v1"
_ARQUIVO = Path(__file__).resolve().parent / "prompts" / f"{VERSAO_PROMPT}.md"


@cache
def _modelo() -> tuple[str, str]:
    conteudo = _ARQUIVO.read_text(encoding="utf-8")
    _, resto = conteudo.split("<!-- SISTEMA -->", 1)
    sistema, usuario = resto.split("<!-- USUARIO -->", 1)
    return sistema.strip(), usuario.strip()


def _niveis(criterio) -> str:
    linhas = []
    for n in criterio.niveis.all():
        linha = f"- {n.codigo} — {n.rotulo} ({n.pontuacao} pts)"
        linhas.append(f"{linha}: {n.descritor}" if n.descritor else linha)
    return "\n".join(linhas)


def montar(enunciado: str, criterio, texto_resposta: str) -> tuple[str, str]:
    sistema, usuario = _modelo()
    return sistema, usuario.format(
        enunciado=enunciado.strip(),
        criterio_nome=criterio.nome,
        criterio_descricao=criterio.descricao or "",
        niveis=_niveis(criterio),
        resposta=texto_resposta,
    )


def codigos(criterio) -> list[str]:
    return [n.codigo for n in criterio.niveis.all()]


def esquema(criterio) -> dict:
    """contracts/llm-saida.schema.json, com o enum do critério."""
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["nivel", "justificativa", "trechos"],
        "properties": {
            "nivel": {"type": "string", "enum": [*codigos(criterio), SEM_EVIDENCIA]},
            "justificativa": {"type": "string"},
            "trechos": {"type": "array", "items": {"type": "string"}},
        },
    }
