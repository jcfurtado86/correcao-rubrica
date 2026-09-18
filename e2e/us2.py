"""US2 de ponta a ponta (quickstart V4): fila prioriza não convergentes; divergente sem nível."""

import re
import time

from playwright.sync_api import expect

from api import Cliente, lote_avaliado
from comum import BASE, capturar, entrar, navegador

cliente = Cliente()
cenario = lote_avaliado(cliente, f"US2 {time.strftime('%H%M%S')}")
lote_id = cenario["lote"]["id"]

fila = cliente.get(f"/lotes/{lote_id}/fila/")
assert fila["contagem"].get("DIVERGENTE", 0) > 0 and fila["contagem"].get("CONVERGENTE", 0) > 0, fila["contagem"]

p, b = navegador()
page = b.new_page(viewport={"width": 1400, "height": 1000})
erros_console = []
page.on("console", lambda m: m.type == "error" and erros_console.append(m.text))
entrar(page)

# Fila: contagem por estado e não convergentes no topo
page.goto(f"{BASE}/lotes/{lote_id}/fila")
expect(page.get_by_text("respostas finalizadas")).to_be_visible()
linhas = page.locator("tbody tr")
expect(linhas).to_have_count(40)
selos = [linhas.nth(i).locator(".selo").inner_text() for i in range(40)]
vistos_convergente = False
for s in selos:
    if s == "Convergente":
        vistos_convergente = True
    else:
        assert not vistos_convergente, f"não convergente depois de convergente: {selos}"
capturar(page, "us2-01-fila")

# Resposta divergente: sem nível sugerido, com distribuição e alternativas
divergente = next(
    r for r in fila["respostas"]
    if r["estados"].get("DIVERGENTE") == 4
)
page.goto(f"{BASE}/lotes/{lote_id}/respostas/{divergente['resposta']}")
cartoes = page.locator("section.cartao")
expect(cartoes).to_have_count(4)
for i in range(4):
    cartao = cartoes.nth(i)
    expect(cartao.locator(".selo")).to_contain_text("Divergente")
    expect(cartao.get_by_test_id("nivel-sugerido")).to_have_count(0)
    expect(cartao.get_by_text("Distribuição:")).to_be_visible()
assert page.get_by_test_id("texto-resposta").locator("mark").count() > 0
capturar(page, "us2-02-divergente")

# Resposta convergente: nível sugerido com acordo k/n
convergente = next(r for r in fila["respostas"] if r["estado_pior"] == "CONVERGENTE")
page.goto(f"{BASE}/lotes/{lote_id}/respostas/{convergente['resposta']}")
expect(page.locator("section.cartao").first.get_by_test_id("nivel-sugerido")).to_be_visible()
expect(page.locator("section.cartao .selo").first).to_have_text(re.compile(r"Convergente \d/\d"))
capturar(page, "us2-03-convergente")

assert not erros_console, erros_console
b.close()
p.stop()
print(f"US2 e2e OK (lote {lote_id}; contagem {fila['contagem']})")
