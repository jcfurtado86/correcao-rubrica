"""US3 de ponta a ponta (quickstart V5): decisões, histórico e notas só de finalizadas."""

import csv
import io
import re
import time

from playwright.sync_api import expect

from api import Cliente, lote_avaliado
from comum import BASE, capturar, entrar, navegador

cliente = Cliente()
cenario = lote_avaliado(cliente, f"US3 {time.strftime('%H%M%S')}")
lote_id = cenario["lote"]["id"]
criterios = cenario["rubrica"]["versao"]["criterios"]

p, b = navegador()
ctx = b.new_context(accept_downloads=True, viewport={"width": 1400, "height": 1100})
page = ctx.new_page()
erros_console = []
page.on("console", lambda m: m.type == "error" and erros_console.append(m.text))
entrar(page)

# 1. primeira resposta da fila: decide por clique, com um motivo
page.goto(f"{BASE}/lotes/{lote_id}/fila")
page.locator("tbody tr a").first.click()
expect(page.locator("section.cartao")).to_have_count(4)
for i, c in enumerate(criterios):
    cartao = page.get_by_test_id(f"criterio-{c['id']}")
    if i == 0:
        cartao.get_by_placeholder("Motivo (opcional)").fill("teste de motivo")
    cartao.get_by_role("button", name=re.compile(r"N2 Parcial$")).click()
    expect(page.get_by_test_id(f"decidido-{c['id']}")).to_contain_text("N2")
expect(page.get_by_test_id("finalizada")).to_be_visible()
capturar(page, "us3-01-finalizada")

# 2. altera uma decisão: vira histórico
c0 = criterios[0]
page.get_by_test_id(f"criterio-{c0['id']}").get_by_role("button", name=re.compile(r"N3 Adequado$")).click()
expect(page.get_by_test_id(f"decidido-{c0['id']}")).to_contain_text("N3")
expect(page.get_by_test_id(f"criterio-{c0['id']}").get_by_placeholder("Motivo (opcional)")).to_have_value("")
page.get_by_text("Histórico de decisões").click()
expect(page.get_by_text("(substituída)")).to_have_count(1)
capturar(page, "us3-02-historico")

# 3. próxima da fila: decide pelo teclado (atalhos 1–9 e setas)
page.get_by_role("button", name=re.compile(r"^Próxima da fila")).click()
expect(page.locator("section.cartao")).to_have_count(4)
page.locator("h1").click()  # tira o foco de qualquer campo
time.sleep(1.5)  # tempo ativo mensurável
for _ in criterios:
    page.keyboard.press("4")
    time.sleep(0.3)
expect(page.get_by_test_id("finalizada")).to_be_visible()
capturar(page, "us3-03-teclado")

# 4. completa mais 8 respostas pela API e deixa 5 parciais
fila = cliente.get(f"/lotes/{lote_id}/fila/")["respostas"]
pendentes = [r for r in fila if not r["finalizada"]]
for r in pendentes[:8]:
    s = cliente.post(f"/respostas/{r['resposta']}/sessoes/")
    for c in criterios:
        cliente.post(f"/sessoes/{s['sessao']}/decisoes/", {"criterio": c["id"], "nivel": c["niveis"][0]["id"], "tempo_ativo_ms": 1000})
for r in pendentes[8:13]:
    s = cliente.post(f"/respostas/{r['resposta']}/sessoes/")
    c = criterios[0]
    cliente.post(f"/sessoes/{s['sessao']}/decisoes/", {"criterio": c["id"], "nivel": c["niveis"][0]["id"], "tempo_ativo_ms": 500})

# 5. tempo ativo registrado nas decisões feitas pela interface
primeira = fila[0]["resposta"]
historico = cliente.get(f"/respostas/{primeira}/historico/")
assert all(d["tempo_ativo_ms"] > 0 for d in historico), historico
assert historico[0]["motivo"] == "teste de motivo"
alterada = [d for d in historico if d["criterio"] == criterios[0]["id"]][-1]
assert alterada["motivo"] == "", "motivo não pode passar para a decisão seguinte"
assert historico[0]["tipo"] in ("CONFIRMACAO", "ALTERACAO", "ESCOLHA")

# 6. notas pela interface: só as 10 finalizadas
page.goto(f"{BASE}/lotes/{lote_id}")
expect(page.get_by_text("de 40 respostas finalizadas")).to_be_visible()
with page.expect_download() as baixado:
    page.get_by_role("button", name="Baixar notas (CSV)").click()
linhas = list(csv.reader(io.StringIO(open(baixado.value.path(), encoding="utf-8").read())))
assert linhas[0][0] == "codigo" and linhas[0][-1] == "nota_total", linhas[0]
assert len(linhas) == 11, len(linhas)
capturar(page, "us3-04-lote")

# 7. não há ação de decidir em lote na interface
assert page.get_by_role("button", name=re.compile(r"(aceitar|aprovar|confirmar) tod", re.I)).count() == 0

assert not erros_console, erros_console
b.close()
p.stop()
print(f"US3 e2e OK (lote {lote_id}; {len(linhas) - 1} respostas nas notas)")
