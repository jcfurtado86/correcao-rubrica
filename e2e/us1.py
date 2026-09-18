"""US1 de ponta a ponta pela interface (quickstart V1–V3), com o dublê."""

import re
import sys
import time

from playwright.sync_api import expect

from comum import BASE, RAIZ, capturar, entrar, manage, navegador

sufixo = time.strftime("%H%M%S")
p, b = navegador()
ctx = b.new_context(accept_downloads=True, viewport={"width": 1400, "height": 1000})
page = ctx.new_page()
erros_console = []
page.on("console", lambda m: m.type == "error" and erros_console.append(m.text))

# 1. login
entrar(page)

# 2. rubrica com 2 critérios pela interface
page.get_by_role("link", name="Rubricas").click()
page.get_by_role("button", name="Nova rubrica").click()
page.get_by_label("Título").fill(f"Verificação e validação e2e {sufixo}")
page.get_by_label("Nome").first.fill("Exemplificação")
page.get_by_label("Descrição do critério").first.fill("Exemplos de verificação e de validação.")
page.get_by_role("button", name="Adicionar critério").click()
page.get_by_label("Nome").nth(1).fill("Distinção")
page.get_by_label("Tipo").nth(1).select_option("OBJETIVO")
page.get_by_role("button", name="Salvar rubrica").click()
expect(page.get_by_text("Rubrica salva (versão 1).")).to_be_visible()
capturar(page, "us1-01-rubrica")

# 3. lote sintético
page.get_by_role("link", name="Lotes").click()
page.get_by_role("button", name="Novo lote").click()
page.get_by_label("Título").fill(f"Turma fictícia {sufixo}")
page.get_by_label("Enunciado da questão").fill(
    (RAIZ / "dados_sinteticos" / "enunciado.txt").read_text(encoding="utf-8").strip()
)
page.get_by_label("Rubrica").select_option(label=f"Verificação e validação e2e {sufixo} (v1)")
page.get_by_label("Lote sintético").check()
page.get_by_role("button", name="Criar e importar respostas").click()
expect(page).to_have_url(re.compile(r"/lotes/\d+/importar$"))
lote_id = re.search(r"/lotes/(\d+)/", page.url).group(1)

# 4. importação com prévia, mapeamento automático e chave
page.locator("input[type=file]").set_input_files(str(RAIZ / "dados_sinteticos" / "turma_ficticia.xlsx"))
expect(page.get_by_text("Prévia (40 linhas)")).to_be_visible()
assert page.get_by_label("Coluna com a resposta do estudante").input_value() == "Resposta 1"
for coluna in ["Sobrenome", "Nome", "Endereço de email", "Número de identificação"]:
    expect(page.get_by_label(coluna, exact=True)).to_be_checked()
capturar(page, "us1-02-previa")
with page.expect_download() as baixado:
    page.get_by_role("button", name="Importar e anonimizar").click()
chave = baixado.value
assert chave.suggested_filename.startswith("chave-"), chave.suggested_filename
conteudo_chave = open(chave.path(), encoding="utf-8").read()
assert conteudo_chave.startswith("codigo,identificador") and conteudo_chave.count("\n") == 41
expect(page.get_by_text("40 respostas carregadas e anonimizadas")).to_be_visible()
expect(page.get_by_text("Guarde este arquivo. Ele não poderá ser gerado de novo.")).to_be_visible()
capturar(page, "us1-03-importado")

# 5. estimativa, confirmação e progresso até concluir
page.get_by_role("button", name="Pré-avaliar").click()
expect(page.get_by_text("370 chamadas")).to_be_visible()  # 37 elegíveis × 2 critérios × 5
capturar(page, "us1-04-estimativa")
page.get_by_role("button", name="Confirmar e executar").click()
expect(page.get_by_text("Concluída", exact=True)).to_be_visible(timeout=180_000)
capturar(page, "us1-05-rodada")

# 6–7. inspeção: trechos destacados que existem no texto, e o cenário de trecho
# inventado aparece como execução inválida
page.goto(f"{BASE}/lotes/{lote_id}")
codigos = page.get_by_role("link", name=re.compile(r"^R0\d\d$"))
codigos.first.wait_for()  # a lista de respostas carrega depois do lote
n = codigos.count()
assert n == 40, n
com_destaque = achou_invalida = False
for i in range(n):
    page.goto(f"{BASE}/lotes/{lote_id}")
    page.get_by_role("link", name=re.compile(r"^R0\d\d$")).nth(i).click()
    texto = page.get_by_test_id("texto-resposta")
    texto.wait_for()
    if not com_destaque and texto.locator("mark").count() > 0:
        com_destaque = True
        capturar(page, "us1-06-inspecao")
    if not achou_invalida and page.get_by_text("trecho não encontrado no texto").count() > 0:
        achou_invalida = True
        capturar(page, "us1-07-trecho-inventado")
    if com_destaque and achou_invalida:
        break
assert com_destaque, "nenhum trecho destacado"
assert achou_invalida, "cenário trecho_inventado não apareceu"

# 8. auditoria de identificadores no banco do stack (V1)
r = manage("auditar_identificadores", "/dados_sinteticos/identificadores_plantados.txt")
print(r.stdout.strip())
assert r.returncode == 0, r.stdout + r.stderr

assert not erros_console, f"erros no console: {erros_console}"
b.close()
p.stop()
print(f"US1 e2e OK (lote {lote_id})")
sys.exit(0)
