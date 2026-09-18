"""Montagem de cenários pela API (mais rápido que pela interface)."""

import json
import time
from pathlib import Path

import requests

from comum import BASE, DOCENTE, RAIZ

API = BASE + "/api"


class Cliente:
    def __init__(self, credenciais=DOCENTE):
        r = requests.post(f"{API}/auth/token/", json={"email": credenciais[0], "password": credenciais[1]})
        r.raise_for_status()
        self.s = requests.Session()
        self.s.headers["Authorization"] = f"Bearer {r.json()['access']}"

    def get(self, caminho, **kw):
        r = self.s.get(API + caminho, **kw)
        r.raise_for_status()
        return r.json() if "json" in r.headers.get("content-type", "") else r

    def post(self, caminho, corpo=None, **kw):
        r = self.s.post(API + caminho, json=corpo, **kw) if "files" not in kw else self.s.post(API + caminho, **kw)
        if r.status_code >= 400:
            raise AssertionError(f"{caminho}: {r.status_code} {r.text[:300]}")
        return r.json() if r.content else None


RUBRICA_4x4 = json.loads((RAIZ / "e2e" / "rubrica_4x4.json").read_text(encoding="utf-8"))


def lote_avaliado(cliente: Cliente, titulo: str, rubrica=None, n_execucoes=5) -> dict:
    """Cria rubrica 4×4, lote sintético, importa a turma fictícia e roda a rodada 1."""
    rubrica = rubrica or cliente.post("/rubricas/", RUBRICA_4x4)
    lote = cliente.post(
        "/lotes/",
        {
            "titulo": titulo,
            "enunciado": (RAIZ / "dados_sinteticos" / "enunciado.txt").read_text(encoding="utf-8").strip(),
            "versao_rubrica": rubrica["versao"]["id"],
            "sintetico": True,
            "n_execucoes": n_execucoes,
        },
    )
    arquivo = RAIZ / "dados_sinteticos" / "turma_ficticia.xlsx"
    with open(arquivo, "rb") as f:
        cliente.post(
            f"/lotes/{lote['id']}/importacao/",
            files={"arquivo": (arquivo.name, f)},
            data={
                "coluna_resposta": "Resposta 1",
                "colunas_identificacao": ["Sobrenome", "Nome", "Endereço de email", "Número de identificação"],
            },
        )
    rodada = cliente.post(f"/lotes/{lote['id']}/rodadas/", {"confirmar": True})
    esperar_rodada(cliente, rodada["id"])
    return {"rubrica": rubrica, "lote": lote, "rodada": rodada}


def esperar_rodada(cliente: Cliente, rodada_id: int, limite=300):
    fim = time.time() + limite
    while time.time() < fim:
        r = cliente.get(f"/rodadas/{rodada_id}/")
        if r["status"] in ("CONCLUIDA", "COM_FALHAS"):
            return r
        time.sleep(1)
    raise AssertionError(f"rodada {rodada_id} não terminou")
