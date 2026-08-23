"""Fusión de todas las fuentes por índice temporal y columnas de exportación."""

import pandas as pd


def merge_all_sources(
    ohlcv: pd.DataFrame,
    funding: pd.DataFrame | None = None,
    oi: pd.DataFrame | None = None,
    ls_ratio: pd.DataFrame | None = None,
    fut_taker: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """
    Hace left join de todas las fuentes sobre el índice del OHLCV.
    Las fuentes con menor resolución (funding cada 8h) se forward-fill.
    """
    df = ohlcv.copy()
    sources = {
        "funding":   (funding,   True),
        "oi":        (oi,        False),
        "ls_ratio":  (ls_ratio,  False),
        "fut_taker": (fut_taker, False),
    }
    for name, (src, ffill) in sources.items():
        if src is not None and not src.empty:
            df = df.join(src, how="left")
            if ffill:
                ffill_cols = [c for c in src.columns if c in df.columns]
                df[ffill_cols] = df[ffill_cols].infer_objects().ffill()
        else:
            print(f"  [INFO] Fuente '{name}' omitida (vacía o no disponible).")
    return df


EXPORT_COLUMNS_SPOT = [
    "Open", "High", "Low", "Close", "Volume", "Volumen_USD",
    "Rango_Dia", "Volatilidad_Diaria", "Precio_Medio", "Precio_Tipico",
    "Variacion", "Variacion_%", "Tendencia_Alcista", "Cambio_Absoluto", "Cambio_%",
    "Taker_Buy_Vol", "Taker_Sell_Vol", "Taker_Buy_USDT", "Taker_Sell_USDT",
    "Volume_Delta", "Volume_Delta_%", "Taker_Pressure", "Num_Trades", "Avg_Trade_Size",
]

EXPORT_COLUMNS_TECHNICAL = [
    "EMA20", "EMA50", "EMA200", "RSI14",
    "MACD_Line", "MACD_Signal", "MACD_Hist",
    "True_Range", "ATR14", "ATR14_%",
    "Vol_MA20", "Vol_Spike_Ratio", "High_20", "Low_20", "New_High_20", "New_Low_20",
]

EXPORT_COLUMNS_PATTERNS = [
    "Doji", "Hammer", "Shooting_Star",
    "Bullish_Engulfing", "Bearish_Engulfing",
    "Bullish_Harami", "Bearish_Harami",
    "Morning_Star", "Evening_Star",
]

EXPORT_COLUMNS_FUTURES = [
    "Funding_Rate", "Funding_Rate_Acum_8h", "Funding_Mark_Price", "Funding_Extreme",
    "OI_Amount", "OI_Value_USDT", "OI_Change_%", "OI_Price_Diverge",
    "LS_Ratio", "LS_Long_Pct", "LS_Short_Pct",
    "Fut_Buy_Vol", "Fut_Sell_Vol", "Fut_Buy_Sell_Ratio", "Fut_Delta_Vol", "Fut_Delta_%",
]

EXPORT_COLUMNS_ORDERBOOK = [
    "OB_Spread", "OB_Spread_%", "OB_Mid_Price",
    "OB_Bid_Depth", "OB_Ask_Depth", "OB_Imbalance",
    "OB_Bid_USDT_Depth", "OB_Ask_USDT_Depth",
]

EXPORT_COLUMNS_TICKER = [
    "Ticker_VWAP", "Ticker_Volume_24h", "Ticker_Change_24h_%",
    "Ticker_High_24h", "Ticker_Low_24h", "Ticker_Price_vs_VWAP_%",
]


def build_export_columns(df: pd.DataFrame) -> list[str]:
    all_cols = (
        EXPORT_COLUMNS_SPOT
        + EXPORT_COLUMNS_TECHNICAL
        + EXPORT_COLUMNS_PATTERNS
        + EXPORT_COLUMNS_FUTURES
        + EXPORT_COLUMNS_ORDERBOOK
        + EXPORT_COLUMNS_TICKER
    )
    return [c for c in all_cols if c in df.columns]
