"""
Tests de core/exchange.py — normalización de símbolos (puras, sin red) e
inicialización de instancias ccxt (`init_exchange` solo configura el cliente
localmente, no dispara ninguna llamada de red al construirse).
"""

from core.exchange import futures_symbol, init_exchange, spot_symbol


def test_spot_symbol_passthrough_when_already_slash_format():
    assert spot_symbol("DOGE/USDT") == "DOGE/USDT"


def test_spot_symbol_converts_concatenated_usdt_pair():
    assert spot_symbol("DOGEUSDT") == "DOGE/USDT"


def test_spot_symbol_dash_usd_quirk():
    # NOTA (ver mejoras_pendientes.md): el docstring de spot_symbol() dice
    # que "DOGE-USD" -> "DOGE/USDT", pero el código solo reemplaza '-' por
    # '/' y no fuerza el quote a USDT cuando ya hay un separador. El
    # resultado real es "DOGE/USD" (quote USD, no USDT). Este test fija el
    # comportamiento actual como regresión; si se corrige la función, hay
    # que actualizar este test a la vez que el docstring.
    assert spot_symbol("DOGE-USD") == "DOGE/USD"


def test_futures_symbol_appends_quote_suffix():
    assert futures_symbol("BTC/USDT") == "BTC/USDT:USDT"


def test_futures_symbol_idempotent_when_already_has_suffix():
    assert futures_symbol("BTC/USDT:USDT") == "BTC/USDT:USDT"


def test_init_exchange_spot_uses_expected_market_type():
    exchange = init_exchange("binance", "spot")
    assert exchange.options["defaultType"] == "spot"
    # Nuestro código solo fuerza defaultSubType="linear" para "future"; para
    # "spot" queda el default propio de ccxt (None), sin overridearlo.
    assert exchange.options.get("defaultSubType") is None


def test_init_exchange_future_forces_linear_subtype():
    # Sin esto ccxt puede resolver a dapi (coin-margined) para algunos
    # símbolos en vez de fapi (USDT-margined) — ver docstring de init_exchange.
    exchange = init_exchange("binance", "future")
    assert exchange.options["defaultType"] == "future"
    assert exchange.options["defaultSubType"] == "linear"
