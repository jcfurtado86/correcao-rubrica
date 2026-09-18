"""Piloto de variabilidade (research R3), executado em 2026-09-18.

Uso: GEMINI_API_KEY=... uv run --with google-genai python piloto_variabilidade.py [modelo] [N] [semente]
Sem semente: N execuções independentes. Com semente: todas usam a mesma (reprodutibilidade).
Imprime nível, trechos localizados/total, tokens (entrada, saída, raciocínio) e latência.
"""
import re, sys, time, json, unicodedata, asyncio
from pathlib import Path
from typing import Literal
from pydantic import BaseModel
from google import genai
from google.genai import types

MODEL = sys.argv[1] if len(sys.argv) > 1 else "gemini-2.5-flash"
N = int(sys.argv[2]) if len(sys.argv) > 2 else 5
SEED = int(sys.argv[3]) if len(sys.argv) > 3 else None
import os
key = os.environ["GEMINI_API_KEY"]
client = genai.Client(api_key=key)

ENUNCIADO = "Explique a diferença entre verificação e validação de software e dê um exemplo de cada uma."
CRITERIO = """Critério: Exemplificação (interpretativo)
Níveis:
- N1 (0 pts): não apresenta exemplos ou os exemplos não correspondem aos conceitos.
- N2 (1 pt): apresenta exemplo para apenas um dos conceitos, ou exemplos genéricos sem relação clara com o conceito.
- N3 (2 pts): apresenta exemplo para os dois conceitos, mas ao menos um é superficial ou parcialmente correto.
- N4 (3 pts): apresenta exemplos corretos, específicos e bem relacionados a cada conceito."""
RESPOSTA = """Verificação é quando a gente confere se o software foi construído do jeito certo, seguindo a especificação, e validação é ver se construímos o software certo, aquele que o cliente precisa.
Um exemplo de verificação seria fazer uma revisão do código ou rodar os testes unitários pra ver se as funções fazem o que o documento de requisitos pede.
Já na validação, podemos mostrar o sistema para o usuário e ver se ele gosta, tipo um teste com o cliente.
As duas coisas são importantes para a qualidade."""

class Saida(BaseModel):
    nivel: Literal["N1", "N2", "N3", "N4", "SEM_EVIDENCIA"]
    justificativa: str
    trechos: list[str]

SYSTEM = ("Você é um avaliador que aplica uma rubrica a uma resposta discursiva de estudante, "
          "julgando APENAS o critério informado. Escolha um nível da rubrica. Em 'trechos', copie "
          "literalmente (sem parafrasear, sem reticências) o(s) trecho(s) da resposta que sustentam o nível. "
          "Se a resposta não tratar do critério, use SEM_EVIDENCIA e deixe 'trechos' vazio.")

def norm(s):
    s = unicodedata.normalize("NFKC", s)
    s = s.translate(str.maketrans({"“": '"', "”": '"', "‘": "'", "’": "'", "–": "-", "—": "-"}))
    return re.sub(r"\s+", " ", s).strip().lower()

async def one(i):
    t = time.monotonic()
    r = await client.aio.models.generate_content(
        model=MODEL,
        contents=f"ENUNCIADO:\n{ENUNCIADO}\n\n{CRITERIO}\n\nRESPOSTA DO ESTUDANTE:\n<<<\n{RESPOSTA}\n>>>",
        config=types.GenerateContentConfig(system_instruction=SYSTEM,
            response_mime_type="application/json", response_schema=Saida, seed=SEED),
    )
    u = r.usage_metadata
    out = r.parsed
    ok = [norm(q) in norm(RESPOSTA) for q in out.trechos]
    return dict(i=i, nivel=out.nivel, trechos_ok=f"{sum(ok)}/{len(ok)}",
                inp=u.prompt_token_count, out=u.candidates_token_count, think=u.thoughts_token_count,
                s=round(time.monotonic()-t, 1), just=out.justificativa[:110], trechos=out.trechos, bad=[q for q, k in zip(out.trechos, ok) if not k])

async def retry(i):
    for a in range(6):
        try:
            return await one(i)
        except Exception as e:
            print(f"run {i} tentativa {a+1}: {str(e)[:60]}", flush=True)
            await asyncio.sleep(2 ** a * 3)
    return dict(i=i, nivel="FALHOU", trechos_ok="-", inp=0, out=0, think=0, s=0, just="", bad=[])

async def main():
    res = [await retry(i) for i in range(N)]
    for r in res: print(json.dumps(r, ensure_ascii=False))
    from collections import Counter
    print(MODEL, "distribuição:", dict(Counter(r["nivel"] for r in res)))
asyncio.run(main())
