"""Ticker 24h — contexto de mercado spot (snapshot único)."""

from ..exchange import init_exchange, spot_symbol


def fetch_ticker_metrics(
    symbol: str,
    exchange_name: str = "binance",
) -> dict:
    """
    Retorna métricas del ticker 24h:
        Ticker_VWAP         — VWAP 24h de Binance
        Ticker_Volume_24h   — volumen en USDT últimas 24h
        Ticker_Change_24h_% — variación porcentual 24h
        Ticker_High_24h     — máximo 24h
        Ticker_Low_24h      — mínimo 24h
        Ticker_Price_vs_VWAP_% — posición del precio actual vs VWAP
    """
    exchange = init_exchange(exchange_name, "spot")
    t = exchange.fetch_ticker(spot_symbol(symbol))
    last = t.get("last") or t.get("close")
    vwap = t.get("vwap")
    return {
        "Ticker_VWAP":            vwap,
        "Ticker_Volume_24h":      t.get("quoteVolume"),
        "Ticker_Change_24h_%":    t.get("percentage"),
        "Ticker_High_24h":        t.get("high"),
        "Ticker_Low_24h":         t.get("low"),
        "Ticker_Price_vs_VWAP_%": round((last / vwap - 1) * 100, 4) if last and vwap else None,
    }
