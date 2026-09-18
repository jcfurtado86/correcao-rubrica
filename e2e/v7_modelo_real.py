"""Quickstart V7: lote sintético com modelo real (padrão: gemini-3.6-flash).

Uso: python3 e2e/v7_modelo_real.py [provedor] [modelo] [n_respostas] [n_execucoes]
Usa só respostas "normais" da turma fictícia (sem marcadores do dublê nem dados
pessoais plantados) e a rubrica pública de docs/modelos. Aborta se a estimativa
passar de LIMITE_USD. Relata validade, motivos de invalidez, tokens, custo real ×
estimado, latência, tentativas e o tempo total.
"""

import csv
import io
import json
import statistics
import sys
import time
import zipfile
from collections import Counter

from api import Cliente, esperar_rodada
from comum import RAIZ

LIMITE_USD = 2.0
provedor = sys.argv[1] if len(sys.argv) > 1 else "gemini"
modelo = sys.argv[2] if len(sys.argv) > 2 else "gemini-3.6-flash"
n_respostas = int(sys.argv[3]) if len(sys.argv) > 3 else 10
n_execucoes = int(sys.argv[4]) if len(sys.argv) > 4 else 5

linhas = list(csv.DictReader(open(RAIZ / "dados_sinteticos" / "turma_ficticia.csv", encoding="utf-8"), delimiter=";"))
normais = linhas[18 : 18 + n_respostas]  # linhas sem roteiro nem identificador no texto
buffer = io.StringIO()
escritor = csv.DictWriter(buffer, fieldnames=list(linhas[0].keys()), delimiter=";")
escritor.writeheader()
escritor.writerows(normais)

cliente = Cliente()
modelo_json = json.loads((RAIZ / "docs" / "modelos" / "verificacao-validacao.json").read_text(encoding="utf-8"))
rubrica = cliente.post("/rubricas/", {k: v for k, v in modelo_json.items() if k != "versao_formato"})
lote = cliente.post("/lotes/", {
    "titulo": f"V7 {modelo} {time.strftime('%H%M%S')}",
    "enunciado": (RAIZ / "dados_sinteticos" / "enunciado.txt").read_text(encoding="utf-8").strip(),
    "versao_rubrica": rubrica["versao"]["id"],
    "sintetico": True,
    "provedor_llm": provedor,
    "modelo_llm": modelo,
    "n_execucoes": n_execucoes,
    "teto_usd": "3",
})
cliente.post(
    f"/lotes/{lote['id']}/importacao/",
    files={"arquivo": ("v7.csv", buffer.getvalue().encode("utf-8"))},
    data={"coluna_resposta": "Resposta 1", "colunas_identificacao": ["Sobrenome", "Nome", "Endereço de email", "Número de identificação"]},
)
est = cliente.post(f"/lotes/{lote['id']}/rodadas/estimativa/", {})
print(f"Estimativa: {est['n_chamadas']} chamadas, US$ {est['custo_estimado_usd']:.4f} ({est['base_saida']})")
if est["custo_estimado_usd"] > LIMITE_USD:
    sys.exit(f"Abortado: estimativa acima de US$ {LIMITE_USD}")

inicio = time.time()
rodada = cliente.post(f"/lotes/{lote['id']}/rodadas/", {"confirmar": True})
final = esperar_rodada(cliente, rodada["id"], limite=1800)
duracao = time.time() - inicio

zip_bytes = cliente.s.get(f"http://localhost:5183/api/lotes/{lote['id']}/exportacao.zip").content
with zipfile.ZipFile(io.BytesIO(zip_bytes)) as z:
    execucoes = list(csv.DictReader(io.StringIO(z.read("execucoes.csv").decode("utf-8"))))
    consolidados = list(csv.DictReader(io.StringIO(z.read("consolidados.csv").decode("utf-8"))))
concluidas = [e for e in execucoes if e["status"] == "CONCLUIDA"]
validas = [e for e in concluidas if e["valida"] == "1"]
motivos = Counter(e["motivo_invalidez"] for e in concluidas if e["valida"] == "0")
tentativas = Counter(int(e["tentativas"]) for e in execucoes)
estados = Counter(c["estado"] for c in consolidados)
media = lambda campo: statistics.fmean(int(e[campo]) for e in concluidas) if concluidas else 0  # noqa: E731
latencias = sorted(int(e["latencia_ms"]) for e in concluidas)

relatorio = {
    "modelo": modelo,
    "lote": lote["id"],
    "chamadas": len(execucoes),
    "status_rodada": final["status"],
    "duracao_s": round(duracao, 1),
    "concluidas": len(concluidas),
    "falhas": final["falhas"],
    "validas_pct": round(100 * len(validas) / max(len(concluidas), 1), 1),
    "motivos_invalidez": dict(motivos),
    "tentativas": dict(sorted(tentativas.items())),
    "tokens_medios": {"entrada": round(media("tokens_entrada")), "saida": round(media("tokens_saida")), "raciocinio": round(media("tokens_raciocinio"))},
    "latencia_ms": {"mediana": latencias[len(latencias) // 2] if latencias else None, "p95": latencias[int(len(latencias) * 0.95)] if latencias else None},
    "custo_estimado_usd": round(est["custo_estimado_usd"], 4),
    "custo_real_usd": round(final["custo_acumulado_usd"], 4),
    "real_sobre_estimado": round(final["custo_acumulado_usd"] / est["custo_estimado_usd"], 3) if est["custo_estimado_usd"] else None,
    "estados": dict(estados),
}
print(json.dumps(relatorio, ensure_ascii=False, indent=1))
(RAIZ / "e2e" / "capturas" / f"v7-{modelo.replace('/', '_')}.json").write_text(json.dumps(relatorio, ensure_ascii=False, indent=1))
