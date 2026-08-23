"""Normalización de símbolos e inicialización de instancias ccxt."""


def spot_symbol(symbol: str) -> str:
    """Convierte 'DOGE-USD' o 'DOGEUSDT' → 'DOGE/USDT' (formato ccxt spot)."""
    s = symbol.replace("-", "/")
    if "/" not in s and s.endswith("USDT"):
        s = s[:-4] + "/USDT"
    return s


def futures_symbol(symbol: str) -> str:
    """Devuelve el símbolo en formato ccxt para perpetuos: 'DOGE/USDT:USDT'."""
    base = spot_symbol(symbol)
    if ":" not in base:
        quote = base.split("/")[-1]
        base = f"{base}:{quote}"
    return base


def init_exchange(exchange_name: str = "binance", market_type: str = "spot"):
    """
    Crea instancia ccxt con el tipo de mercado indicado.

    Para futuros fuerza defaultSubType='linear' → fapi.binance.com (USDT-margined).
    Sin esto ccxt resuelve a dapi (coin-margined) para algunos simbolos como DOGE,
    causando el error: 'binance GET https://dapi.binance.com/dapi/v1/exchangeInfo'
    """
    try:
        import ccxt
    except ImportError as exc:
        raise SystemExit("Falta 'ccxt'. Instalala con: pip install ccxt") from exc
    options: dict = {"defaultType": market_type}
    if market_type == "future":
        options["defaultSubType"] = "linear"
    return getattr(ccxt, exchange_name)({"options": options})
