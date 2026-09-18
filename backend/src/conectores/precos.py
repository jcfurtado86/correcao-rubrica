"""Tabela de preços por modelo, com vigência (research R2).

US$ por 1 milhão de tokens. Na Gemini API a saída inclui os tokens de raciocínio.
O preço do 3.6/3.8-flash dobra em 2027-01-01, e o estudo pode cruzar a virada:
por isso cada entrada tem data de início.
"""

from datetime import date
from decimal import Decimal

MILHAO = Decimal(1_000_000)

# (modelo, vigente a partir de, entrada, saída)
TABELA: list[tuple[str, date, Decimal, Decimal]] = [
    ("gemini-3.6-flash", date(2000, 1, 1), Decimal("0.75"), Decimal("3.75")),
    ("gemini-3.6-flash", date(2027, 1, 1), Decimal("1.50"), Decimal("7.50")),
    ("gemini-3.8-flash", date(2000, 1, 1), Decimal("0.75"), Decimal("3.75")),
    ("gemini-3.8-flash", date(2027, 1, 1), Decimal("1.50"), Decimal("7.50")),
    ("gemini-2.5-flash", date(2000, 1, 1), Decimal("0.30"), Decimal("2.50")),
    ("gemini-2.5-flash-lite", date(2000, 1, 1), Decimal("0.10"), Decimal("0.40")),
    ("dublê", date(2000, 1, 1), Decimal("0"), Decimal("0")),
]


class ModeloSemPreco(ValueError):
    pass


def preco_vigente(modelo: str, data: date | None = None) -> tuple[Decimal, Decimal]:
    data = data or date.today()
    candidatos = [(inicio, e, s) for m, inicio, e, s in TABELA if m == modelo and inicio <= data]
    if not candidatos:
        raise ModeloSemPreco(f"Sem preço cadastrado para o modelo {modelo!r}.")
    _, entrada, saida = max(candidatos)
    return entrada, saida


def custo_usd(
    modelo: str, tokens_entrada: int, tokens_saida_mais_raciocinio: int, data: date | None = None
) -> Decimal:
    entrada, saida = preco_vigente(modelo, data)
    return (
        Decimal(tokens_entrada) * entrada + Decimal(tokens_saida_mais_raciocinio) * saida
    ) / MILHAO
