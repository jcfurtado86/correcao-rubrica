"""US4 de ponta a ponta (quickstart V6): painel, reaplicação, sensibilidade e reprodução."""

import subprocess
import sys
import time

from playwright.sync_api import expect

from api import Cliente, esperar_rodada, lote_avaliado
from comum import BASE, RAIZ, capturar, entrar, navegador

cliente = Cliente()
cenario = lote_avaliado(cliente, f"US4 {time.strftime('%H%M%S')}")
lote_id = cenario["lote"]["id"]
criterios = cenario["rubrica"]["versao"]["criterios"]

# decisões da docente em 15 respostas (pela API; a interface de decisão é a US3)
fila = cliente.get(f"/lotes/{lote_id}/fila/")["respostas"]
for i, r in enumerate(fila[:15]):
    s = cliente.post(f"/respostas/{r['resposta']}/sessoes/")
    for j, c in enumerate(criterios):
        nivel = c["niveis"][(i + j) % 2 + 1]  # N2 ou N3
        cliente.post(f"/sessoes/{s['sessao']}/decisoes/", {"criterio": c["id"], "nivel": nivel["id"], "tempo_ativo_ms": 2000 + 500 * i})

p, b = navegador()
ctx = b.new_context(accept_downloads=True, viewport={"width": 1400, "height": 1000})
page = ctx.new_page()
erros_console = []
page.on("console", lambda m: m.type == "error" and erros_console.append(m.text))
entrar(page)

# 1. painel antes da reaplicação
page.goto(f"{BASE}/lotes/{lote_id}/painel")
expect(page.get_by_text("concordância exata com a docente")).to_be_visible()
expect(page.get_by_text("reaplique o lote para medir")).to_be_visible()
capturar(page, "us4-01-painel")

# 2. reaplicação pela interface
page.get_by_role("button", name="Reaplicar lote").click()
expect(page.get_by_text("rodada nova e independente")).to_be_visible()
page.get_by_role("button", name="Confirmar e executar").click()
expect(page.get_by_text("Concluída", exact=True)).to_be_visible(timeout=180_000)
rodadas = cliente.get(f"/lotes/{lote_id}/rodadas/")
assert [r["numero"] for r in rodadas] == [1, 2], rodadas
esperar_rodada(cliente, rodadas[1]["id"])

# 3. painel com estabilidade
page.goto(f"{BASE}/lotes/{lote_id}/painel")
expect(page.get_by_text("reaplique o lote para medir")).to_have_count(0)
estab = page.locator(".kpi").filter(has_text="estabilidade entre rodadas").locator(".valor").inner_text()
assert estab.endswith("%"), estab
capturar(page, "us4-02-painel-reaplicado")

# 4. sensibilidade: limiar 0,6 recalcula sem gravar
div_antes = page.locator(".kpi").filter(has_text="divergência sinalizada").locator(".valor").inner_text()
page.get_by_label("Limiar de acordo").select_option("0.6")
expect(page.get_by_text("Estados recalculados só para esta visão")).to_be_visible()
div_depois = page.locator(".kpi").filter(has_text="divergência sinalizada").locator(".valor").inner_text()
assert int(div_depois.rstrip("%")) <= int(div_antes.rstrip("%")), (div_antes, div_depois)
capturar(page, "us4-03-sensibilidade")
page.get_by_label("Limiar de acordo").select_option("")
expect(page.locator(".kpi").filter(has_text="divergência sinalizada").locator(".valor")).to_have_text(div_antes)

# 5. dica ao focar pelo teclado
page.locator(".grafico .alvo").first.focus()
expect(page.locator(".dica")).to_be_visible()

# 6. exportação pela interface + script independente
with page.expect_download() as baixado:
    page.get_by_role("button", name="Exportar dados (ZIP)").click()
arquivo = RAIZ / "e2e" / "capturas" / "exportacao-us4.zip"
baixado.value.save_as(str(arquivo))
saida = subprocess.run(
    [str(RAIZ / "backend" / ".venv" / "bin" / "python"), str(RAIZ / "analysis" / "reproduzir_metricas.py"), str(arquivo)],
    capture_output=True, text=True,
)
print(saida.stdout.strip())
assert saida.returncode == 0 and "OK: 0 divergências" in saida.stdout, saida.stdout + saida.stderr

assert not erros_console, erros_console
b.close()
p.stop()
print(f"US4 e2e OK (lote {lote_id})")
sys.exit(0)
