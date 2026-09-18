"""Utilitários dos testes de ponta a ponta (stack do docker compose no ar).

Uso: python3 e2e/us1.py  (com `docker compose up -d` e usuários criados; ver README).
"""

import os
import re
import subprocess
import time
from pathlib import Path

from playwright.sync_api import Page, expect, sync_playwright

RAIZ = Path(__file__).resolve().parents[1]
BASE = os.environ.get("E2E_BASE", "http://localhost:5183")
CAPTURAS = RAIZ / "e2e" / "capturas"
CAPTURAS.mkdir(exist_ok=True)
DOCENTE = ("docente@exemplo.org", "Docente#2026")
PESQUISADOR = ("pesquisa@exemplo.org", "Pesquisa#2026")


def navegador():
    p = sync_playwright().start()
    b = p.chromium.launch(headless=True)
    return p, b


def entrar(page: Page, credenciais=DOCENTE):
    page.goto(f"{BASE}/entrar")
    page.get_by_label("E-mail").fill(credenciais[0])
    page.get_by_label("Senha").fill(credenciais[1])
    page.get_by_role("button", name="Entrar").click()
    expect(page).to_have_url(re.compile(r"/lotes$"))


def capturar(page: Page, nome: str):
    page.screenshot(path=str(CAPTURAS / f"{nome}.png"), full_page=True)


def manage(*args) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["docker", "compose", "exec", "-T", "backend", "python", "src/manage.py", *args],
        cwd=RAIZ, capture_output=True, text=True,
    )


def esperar(condicao, limite=180, intervalo=1.0, descricao="condição"):
    fim = time.time() + limite
    while time.time() < fim:
        if condicao():
            return
        time.sleep(intervalo)
    raise AssertionError(f"Tempo esgotado esperando {descricao}")
