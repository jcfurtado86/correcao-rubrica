"""Interface única de provedor de LLM (Princípio VI; padrão da factory do Extenda).

O domínio só conhece `LLMProvider.avaliar`: recebe o prompt de sistema, o prompt
do usuário, o esquema JSON exigido e a semente da execução, e devolve o texto
JSON cru com o consumo. Trocar de provedor é trocar `LLM_PROVIDER` (FR-012).

Duas famílias de erro, porque o tratamento é oposto:
- `IAIndisponivel`: passageiro (429, 5xx, rede). A tarefa tenta de novo, com
  espera crescente (research R8). O piloto recebeu 503 na primeira rajada.
- `ErroLLM`: não adianta repetir (chave inválida, requisição malformada).
"""

from dataclasses import dataclass

from django.conf import settings


@dataclass(frozen=True)
class ResultadoLLM:
    texto: str
    tokens_entrada: int
    tokens_saida: int
    tokens_raciocinio: int
    latencia_ms: int


class IAIndisponivel(RuntimeError):
    """Falha passageira do provedor: vale tentar de novo."""


class ErroLLM(RuntimeError):
    """Falha que não se resolve repetindo a chamada."""


class LLMProvider:
    nome: str = "abstrato"

    def __init__(self, modelo: str | None = None):
        self.modelo = modelo or "desconhecido"

    def avaliar(
        self, sistema: str, usuario: str, esquema: dict, semente: int, indice: int = 1
    ) -> ResultadoLLM:
        """`indice` só serve ao dublê roteirizado; provedores reais o ignoram."""
        raise NotImplementedError


_PROVEDORES: dict[str, type[LLMProvider]] = {}


def registrar_provedor(nome: str, classe: type[LLMProvider]) -> None:
    _PROVEDORES[nome] = classe


def get_llm(nome: str | None = None, modelo: str | None = None) -> LLMProvider:
    # Importa os adaptadores para que se registrem; imports tardios evitam que
    # um provedor não usado exija sua biblioteca.
    from conectores import duble, gemini  # noqa: F401

    escolhido = nome or settings.LLM_PROVIDER
    try:
        classe = _PROVEDORES[escolhido]
    except KeyError as exc:
        raise ValueError(f"Provedor de LLM desconhecido: {escolhido!r}") from exc
    return classe(modelo=modelo)


def modelo_padrao(provedor: str) -> str:
    if provedor == "gemini":
        return settings.GEMINI_MODEL
    if provedor == "dumb":
        return "dublê"
    return "desconhecido"
