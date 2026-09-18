"""Modelos que a docente pode escolher para um lote (R2: modelo é parâmetro do lote)."""

from django.conf import settings

from conectores.precos import preco_vigente

GEMINI = ["gemini-3.6-flash", "gemini-3.8-flash", "gemini-2.5-flash", "gemini-2.5-flash-lite"]


def modelos_disponiveis() -> list[dict]:
    itens = [
        {"provedor": "dumb", "modelo": "dublê", "rotulo": "Dublê (teste, sem custo e sem rede)"}
    ]
    if settings.GEMINI_API_KEY:
        itens += [{"provedor": "gemini", "modelo": m, "rotulo": f"Google {m}"} for m in GEMINI]
    for item in itens:
        entrada, saida = preco_vigente(item["modelo"])
        item["entrada_por_milhao"] = float(entrada)
        item["saida_por_milhao"] = float(saida)
    return itens
