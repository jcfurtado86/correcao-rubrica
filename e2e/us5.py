"""US5 de ponta a ponta (quickstart V8): protocolo A, convite, ocultação no servidor."""

import csv
import io
import json
import re
import time
import zipfile
from collections import Counter

from playwright.sync_api import expect

from api import Cliente, lote_avaliado
from comum import BASE, PESQUISADOR, capturar, entrar, navegador

sufixo = time.strftime("%H%M%S")
pesquisador = Cliente(PESQUISADOR)
cenario = lote_avaliado(pesquisador, f"Lote comum {sufixo}")
lote_id = cenario["lote"]["id"]

p, b = navegador()
ctx = b.new_context(accept_downloads=True, viewport={"width": 1400, "height": 1000})
page = ctx.new_page()
erros_console = []
page.on("console", lambda m: m.type == "error" and erros_console.append(m.text))
entrar(page, PESQUISADOR)

# 1. pesquisador cria o estudo pela interface
page.get_by_role("link", name="Estudos").click()
page.get_by_label("Título").fill(f"Estudo piloto {sufixo}")
page.get_by_label("Lote comum").select_option(value=str(lote_id))
page.get_by_role("button", name="Criar estudo").click()
expect(page).to_have_url(re.compile(r"/estudos/\d+$"))
estudo_id = int(page.url.rstrip("/").split("/")[-1])

# 2. convida 8 docentes e inicia
emails = [f"prof{i}.{sufixo}@exemplo.org" for i in range(8)]
page.get_by_label("E-mails dos participantes").fill("\n".join(emails))
page.get_by_role("button", name="Convidar").click()
links = page.locator("input[readonly]")
expect(links).to_have_count(8)
link_p1 = links.first.input_value()
link_p2 = links.nth(1).input_value()
page.get_by_role("button", name=re.compile(r"^Iniciar estudo")).click()
expect(page.get_by_text("Estudo iniciado: metade A com")).to_be_visible()
painel = pesquisador.get(f"/estudos/{estudo_id}/painel/")
celulas = Counter((x["braco"], x["ordem"]) for x in painel["participantes"])
assert set(celulas.values()) == {2} and len(celulas) == 4, celulas
capturar(page, "us5-01-estudo-iniciado")

# 3. participante 1 define a senha pelo link e entra
participante = b.new_context(viewport={"width": 1400, "height": 1000})
pp = participante.new_page()
pp.goto(link_p1.replace("http://localhost:5183", BASE))
pp.get_by_label("Nova senha").fill("Prof#Estudo2026")
pp.get_by_label("Confirme a senha").fill("Prof#Estudo2026")
pp.get_by_role("button", name="Salvar senha").click()
expect(pp.get_by_text("Senha definida")).to_be_visible()
entrar(pp, (emails[0], "Prof#Estudo2026"))
pp.get_by_role("link", name="Estudos").click()
pp.get_by_role("link", name=f"Estudo piloto {sufixo}").click()
expect(pp.get_by_test_id("faixa-bloco")).to_be_visible()

# 4. corrige respostas; na condição sem apoio, o servidor só manda OCULTO.
# Guarda os corpos de todas as aberturas de sessão (o StrictMode do React, em
# desenvolvimento, abre duas vezes e descarta o corpo da primeira).
corpos = []


def _guardar(resposta):
    if re.search(r"/api/estudos/\d+/respostas/\d+/sessoes/$", resposta.url):
        try:
            corpos.append(resposta.json())
        except Exception:
            pass


pp.on("response", _guardar)
condicoes_vistas = set()
for _ in range(3):
    faixa = pp.get_by_test_id("faixa-bloco").inner_text()
    condicao = "SEM_APOIO" if "sem apoio" in faixa else "COM_APOIO"
    corpos.clear()
    pp.reload()
    expect(pp.locator("section.cartao")).to_have_count(4)
    pp.wait_for_timeout(300)
    assert corpos, "nenhuma sessão aberta"
    corpo = corpos[-1]
    assert corpo["condicao"] == condicao, (corpo["condicao"], condicao)
    if condicao == "SEM_APOIO":
        texto = json.dumps(corpo)
        for chave in ("nivel_sugerido", "acordo", "justificativa", "trechos", "alternativas"):
            assert f'"{chave}"' not in texto, chave
        expect(pp.get_by_test_id("nivel-sugerido")).to_have_count(0)
        expect(pp.get_by_test_id("faixa-bloco")).to_contain_text("sem apoio")
        expect(pp.locator("section.cartao .selo")).to_have_text(["Sem apoio"] * 4)
        capturar(pp, "us5-02-sem-apoio")
    condicoes_vistas.add(condicao)
    expect(pp.locator("section.cartao")).to_have_count(4)
    pp.locator("h1").click()
    time.sleep(1)
    for _ in range(4):
        pp.keyboard.press("2")
        time.sleep(0.25)
    expect(pp.get_by_test_id("finalizada")).to_be_visible()
    pp.get_by_role("button", name="Próxima resposta").click()
    time.sleep(0.5)

# 4b. participante 2 (braço 2, com apoio primeiro) recebe as sugestões
p2 = b.new_context(viewport={"width": 1400, "height": 1000}).new_page()
p2.goto(link_p2.replace("http://localhost:5183", BASE))
p2.get_by_label("Nova senha").fill("Prof#Estudo2026")
p2.get_by_label("Confirme a senha").fill("Prof#Estudo2026")
p2.get_by_role("button", name="Salvar senha").click()
expect(p2.get_by_text("Senha definida")).to_be_visible()
entrar(p2, (emails[1], "Prof#Estudo2026"))
p2.goto(f"{BASE}/estudos/{estudo_id}/participar")
expect(p2.get_by_test_id("faixa-bloco")).to_contain_text("com apoio")
expect(p2.locator("section.cartao")).to_have_count(4)
assert p2.locator("section.cartao .selo").filter(has_text="Sem apoio").count() == 0
capturar(p2, "us5-02b-com-apoio")
condicoes_vistas.add("COM_APOIO")

# 5. o participante não acessa o lote nem as execuções
pp.goto(f"{BASE}/lotes/{lote_id}")
expect(pp.get_by_text("Não encontrado", exact=False)).to_be_visible()

# 6. painel do estudo registra o progresso e a exportação sai pseudonimizada
page.reload()
expect(page.locator("tbody tr").first).to_contain_text("3/")
capturar(page, "us5-03-painel-estudo")
with page.expect_download() as baixado:
    page.get_by_role("button", name="Exportar dados (ZIP)").click()
with zipfile.ZipFile(baixado.value.path()) as z:
    alocacao = z.read("alocacao.csv").decode("utf-8")
    decisoes = list(csv.DictReader(io.StringIO(z.read("decisoes.csv").decode("utf-8"))))
assert alocacao.splitlines()[0] == "participante,braco,ordem" and len(alocacao.splitlines()) == 9
assert "@" not in alocacao + json.dumps(decisoes)
assert {d["participante"] for d in decisoes} == {"P01"}
assert len(decisoes) == 12

assert not [e for e in erros_console if "404" not in e], erros_console
b.close()
p.stop()
print(f"US5 e2e OK (estudo {estudo_id}; condições vistas: {sorted(condicoes_vistas)})")
