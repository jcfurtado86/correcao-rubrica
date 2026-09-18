from datetime import date
from decimal import Decimal

import pytest

from conectores.precos import ModeloSemPreco, custo_usd, preco_vigente


def test_preco_do_36_flash_em_2026():
    assert preco_vigente("gemini-3.6-flash", date(2026, 12, 31)) == (
        Decimal("0.75"),
        Decimal("3.75"),
    )


def test_preco_dobra_na_virada_de_2027():
    assert preco_vigente("gemini-3.6-flash", date(2027, 1, 1)) == (Decimal("1.50"), Decimal("7.50"))


def test_custo_inclui_raciocinio_como_saida():
    # 1M de entrada + 1M de saída (visível + raciocínio) = 0,75 + 3,75
    assert custo_usd("gemini-3.6-flash", 1_000_000, 1_000_000, date(2026, 9, 18)) == Decimal("4.5")


def test_duble_nao_custa():
    assert custo_usd("dublê", 10_000, 10_000) == 0


def test_modelo_desconhecido_levanta_erro():
    with pytest.raises(ModeloSemPreco):
        preco_vigente("modelo-inexistente")
