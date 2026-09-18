"""Gemini via SDK `google-genai` (research R2, R3, R8).

Decisões medidas no piloto de 2026-09-18:
- **Sem temperatura explícita.** Para o Gemini 3 o Google recomenda não baixá-la,
  e a variação que se quer medir é a do modelo como é usado de fato.
- **Semente por execução, nunca fixa.** Com a mesma semente o 3.6-flash repetiu a
  resposta byte a byte: semente fixa esconde a instabilidade em vez de medi-la.
"""

import time

import httpx
from django.conf import settings

from conectores.llm import ErroLLM, IAIndisponivel, LLMProvider, ResultadoLLM, registrar_provedor

CODIGOS_PASSAGEIROS = {408, 429, 500, 502, 503, 504}


class GeminiLLMProvider(LLMProvider):
    nome = "gemini"

    def __init__(self, modelo: str | None = None):
        super().__init__(modelo or settings.GEMINI_MODEL)
        self._api_key = settings.GEMINI_API_KEY

    def avaliar(self, sistema, usuario, esquema, semente, indice=1):
        if not self._api_key:
            raise ErroLLM("GEMINI_API_KEY não configurada.")
        from google import genai
        from google.genai import errors, types

        config = types.GenerateContentConfig(
            system_instruction=sistema,
            response_mime_type="application/json",
            response_json_schema=esquema,
            seed=semente,
        )
        # O cliente fica numa variável local até a resposta chegar. Encadeado
        # (`genai.Client(...).models...`), ele é coletado e fecha a conexão HTTP
        # no meio da chamada (armadilha registrada no Extenda).
        cliente = genai.Client(api_key=self._api_key)
        inicio = time.monotonic()
        try:
            resposta = cliente.models.generate_content(
                model=self.modelo, contents=usuario, config=config
            )
        except errors.APIError as exc:
            if exc.code in CODIGOS_PASSAGEIROS:
                raise IAIndisponivel(f"Gemini {exc.code}: {exc.status}") from exc
            raise ErroLLM(f"Gemini {exc.code}: {exc.status}") from exc
        except (httpx.TransportError, TimeoutError, ConnectionError) as exc:
            raise IAIndisponivel(f"Falha de rede: {type(exc).__name__}") from exc
        latencia = int((time.monotonic() - inicio) * 1000)
        uso = resposta.usage_metadata
        return ResultadoLLM(
            texto=resposta.text or "",
            tokens_entrada=(uso.prompt_token_count or 0) if uso else 0,
            tokens_saida=(uso.candidates_token_count or 0) if uso else 0,
            tokens_raciocinio=(uso.thoughts_token_count or 0) if uso else 0,
            latencia_ms=latencia,
        )


registrar_provedor("gemini", GeminiLLMProvider)
