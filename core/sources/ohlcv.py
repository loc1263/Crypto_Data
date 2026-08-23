"""
OHLCV spot: klines básicos (ccxt fetch_ohlcv) y klines enriquecidos con
taker buy/sell volume + número de trades (endpoint raw de Binance).
"""

import time

import pandas as pd

from ..exchange import init_exchange, spot_symbol


def download_ohlcv_taker(
    symbol: str,
    timeframe: str,
    range_ms: int,
    exchange_name: str = "binance",
    batch_size: int = 1000,
    sleep_seconds: float = 0.5,
) -> pd.DataFrame:
    """
    Descarga OHLCV + takerBuyBaseAssetVolume + takerBuyQuoteAssetVolume
    + numberOfTrades usando el endpoint raw de Binance klines.

    Columnas extra añadidas:
        Taker_Buy_Vol   — volumen comprado por takers (agresores de compra)
        Taker_Sell_Vol  — volumen vendido por takers  (total_vol − taker_buy)
        Taker_Buy_USDT  — equivalente en USDT del taker buy
        Taker_Sell_USDT — equivalente en USDT del taker sell
        Volume_Delta    — Taker_Buy_Vol − Taker_Sell_Vol  (presión neta)
        Volume_Delta_%  — Volume_Delta / Volume × 100
        Num_Trades      — número de trades individuales en la vela
        Avg_Trade_Size  — tamaño promedio de trade (Vol / Num_Trades)
    """
    exchange = init_exchange(exchange_name, "spot")
    mkt = spot_symbol(symbol)
    step_ms = exchange.parse_timeframe(timeframe) * 1000
    since = exchange.milliseconds() - range_ms

    rows: list[dict] = []
    while True:
        raw = exchange.publicGetKlines({
            "symbol": mkt.replace("/", ""),
            "interval": timeframe,
            "startTime": since,
            "limit": batch_size,
        })
        if not raw:
            break
        for k in raw:
            rows.append({
                "timestamp":       int(k[0]),
                "Open":            float(k[1]),
                "High":            float(k[2]),
                "Low":             float(k[3]),
                "Close":           float(k[4]),
                "Volume":          float(k[5]),
                "Taker_Buy_Vol":   float(k[9]),
                "Taker_Buy_USDT":  float(k[10]),
                "Num_Trades":      int(k[8]),
            })
        if len(raw) < batch_size:
            break
        since = int(raw[-1][0]) + step_ms
        time.sleep(sleep_seconds)

    if not rows:
        raise SystemExit(f"Sin datos OHLCV para '{symbol}'.")

    df = pd.DataFrame(rows).drop_duplicates(subset=["timestamp"]).sort_values("timestamp")

    df["Taker_Sell_Vol"]   = df["Volume"]        - df["Taker_Buy_Vol"]
    df["Taker_Sell_USDT"]  = df["Volume"] * df["Close"] - df["Taker_Buy_USDT"]
    df["Volume_Delta"]     = df["Taker_Buy_Vol"] - df["Taker_Sell_Vol"]
    df["Volume_Delta_%"]   = (df["Volume_Delta"] / df["Volume"].replace(0, float("nan"))) * 100
    df["Avg_Trade_Size"]   = df["Volume"] / df["Num_Trades"].replace(0, float("nan"))

    fmt = "%Y-%m-%d" if timeframe == "1d" else "%Y-%m-%d %H:%M"
    df["Fecha"] = pd.to_datetime(df["timestamp"], unit="ms").dt.strftime(fmt)
    df.set_index("Fecha", inplace=True)
    df.drop(columns=["timestamp"], inplace=True)
    return df


def download_ohlcv(symbol: str, limit: int = 30, exchange_name: str = "binance") -> pd.DataFrame:
    exchange = init_exchange(exchange_name, "spot")
    mkt = spot_symbol(symbol)
    ohlcv = exchange.fetch_ohlcv(mkt, timeframe="1d", limit=limit)
    if not ohlcv:
        raise SystemExit(f"Sin datos para '{symbol}'.")
    df = pd.DataFrame(ohlcv, columns=["timestamp", "Open", "High", "Low", "Close", "Volume"])
    df["Fecha"] = pd.to_datetime(df["timestamp"], unit="ms").dt.strftime("%Y-%m-%d")
    df.set_index("Fecha", inplace=True)
    df.drop(columns=["timestamp"], inplace=True)
    return df


def download_ohlcv_paginado(
    symbol: str,
    days: int = 365,
    exchange_name: str = "binance",
    batch_size: int = 100,
    sleep_seconds: float = 0.5,
) -> pd.DataFrame:
    exchange = init_exchange(exchange_name, "spot")
    mkt = spot_symbol(symbol)
    ms_per_day = 24 * 60 * 60 * 1000
    since = exchange.milliseconds() - days * ms_per_day
    all_ohlcv: list = []
    while True:
        batch = exchange.fetch_ohlcv(mkt, timeframe="1d", since=since, limit=batch_size)
        if not batch:
            break
        all_ohlcv.extend(batch)
        if len(batch) < batch_size:
            break
        since = batch[-1][0] + ms_per_day
        time.sleep(sleep_seconds)
    if not all_ohlcv:
        raise SystemExit(f"Sin datos para '{symbol}'.")
    df = pd.DataFrame(all_ohlcv, columns=["timestamp", "Open", "High", "Low", "Close", "Volume"])
    df.drop_duplicates(subset=["timestamp"], inplace=True)
    df["Fecha"] = pd.to_datetime(df["timestamp"], unit="ms").dt.strftime("%Y-%m-%d")
    df.set_index("Fecha", inplace=True)
    df.drop(columns=["timestamp"], inplace=True)
    return df


def download_ohlcv_timeframe_range(
    symbol: str,
    timeframe: str,
    range_ms: int,
    exchange_name: str = "binance",
    batch_size: int = 1000,
    sleep_seconds: float = 0.5,
) -> pd.DataFrame:
    exchange = init_exchange(exchange_name, "spot")
    mkt = spot_symbol(symbol)
    since = exchange.milliseconds() - range_ms
    step_ms = exchange.parse_timeframe(timeframe) * 1000
    all_ohlcv: list = []
    while True:
        batch = exchange.fetch_ohlcv(mkt, timeframe=timeframe, since=since, limit=batch_size)
        if not batch:
            break
        all_ohlcv.extend(batch)
        if len(batch) < batch_size:
            break
        next_since = batch[-1][0] + step_ms
        if next_since <= since:
            break
        since = next_since
        time.sleep(sleep_seconds)
    if not all_ohlcv:
        raise SystemExit(f"Sin datos para '{symbol}'.")
    df = pd.DataFrame(all_ohlcv, columns=["timestamp", "Open", "High", "Low", "Close", "Volume"])
    df.drop_duplicates(subset=["timestamp"], inplace=True)
    fmt = "%Y-%m-%d" if timeframe == "1d" else "%Y-%m-%d %H:%M"
    df["Fecha"] = pd.to_datetime(df["timestamp"], unit="ms").dt.strftime(fmt)
    df.set_index("Fecha", inplace=True)
    df.drop(columns=["timestamp"], inplace=True)
    return df
