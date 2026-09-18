"""US6 de ponta a ponta (quickstart V9): exportar e importar modelo de rubrica."""

import json
import re
import time

from playwright.sync_api import expect

from api import Cliente
from comum import BASE, PESQUISADOR, RAIZ, capturar, entrar, navegador

sufixo = time.strftime("%H%M%S")
docente = Cliente()
modelo = json.loads((RAIZ / "docs" / "modelos" / "verificacao-validacao.json").read_text(encoding="utf-8"))
modelo["titulo"] = f"Modelo público {sufixo}"
rubrica = docente.post("/rubricas/", {k: v for k, v in modelo.items() if k != "versao_formato"})

p, b = navegador()
ctx = b.new_context(accept_downloads=True, viewport={"width": 1400, "height": 1000})
page = ctx.new_page()
entrar(page)
page.goto(f"{BASE}/rubricas/{rubrica['id']}")
with page.expect_download() as baixado:
    page.get_by_role("button", name="Exportar modelo").click()
caminho = RAIZ / "e2e" / "capturas" / f"modelo-{sufixo}.json"
baixado.value.save_as(str(caminho))
exportado = json.loads(caminho.read_text(encoding="utf-8"))
assert exportado["versao_formato"] == 1 and exportado["titulo"] == modelo["titulo"]
assert "docente@" not in caminho.read_text(encoding="utf-8")

# outra pessoa (o pesquisador) importa o modelo pela interface
outro = b.new_context(viewport={"width": 1400, "height": 1000}).new_page()
entrar(outro, PESQUISADOR)
outro.goto(f"{BASE}/rubricas")
outro.get_by_label("Importar modelo de rubrica").set_input_files(str(caminho))
expect(outro).to_have_url(re.compile(r"/rubricas/\d+$"))
expect(outro.get_by_label("Título")).to_have_value(modelo["titulo"])
expect(outro.get_by_label("Nome")).to_have_count(4)
capturar(outro, "us6-01-importado")
novo_id = int(outro.url.rsplit("/", 1)[-1])
copia = Cliente(PESQUISADOR).get(f"/rubricas/{novo_id}/")
originais = [(c["nome"], c["tipo"], [n["descritor"] for n in c["niveis"]]) for c in rubrica["versao"]["criterios"]]
importados = [(c["nome"], c["tipo"], [n["descritor"] for n in c["niveis"]]) for c in copia["versao"]["criterios"]]
assert originais == importados
b.close()
p.stop()
print(f"US6 e2e OK (rubrica {rubrica['id']} → {novo_id})")
