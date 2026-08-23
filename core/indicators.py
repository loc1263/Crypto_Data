"""
Métricas de mercado, indicadores técnicos y patrones de vela — todo
calculado desde OHLC/Close, sin depender de ninguna fuente externa.
"""

import numpy as np
import pandas as pd


def add_market_metrics(data: pd.DataFrame) -> pd.DataFrame:
    df = data.copy()
    df["Rango_Dia"]        = df["High"] - df["Low"]
    df["Variacion"]        = df["Close"] - df["Open"]
    df["Variacion_%"]      = ((df["Close"] - df["Open"]) / df["Open"]) * 100
    df["Precio_Medio"]     = (df["High"] + df["Low"]) / 2
    df["Precio_Tipico"]    = (df["High"] + df["Low"] + df["Close"]) / 3
    df["Volatilidad_Diaria"]= (df["High"] - df["Low"]) / df["Open"]
    df["Volumen_USD"]      = df["Volume"] * df["Close"]
    df["Tendencia_Alcista"]= df["Close"] > df["Open"]
    df["Cambio_Absoluto"]  = df["Close"].diff()
    df["Cambio_%"]         = df["Close"].pct_change() * 100
    return df


def _wilder_rma(values: np.ndarray, period: int) -> np.ndarray:
    """
    Suavizado de Wilder (RMA) — la misma media móvil que usa el RSI clásico
    (y que TradingView usa internamente para "RSI (Wilder)").

    Se seedea con el promedio simple de los primeros `period` valores y
    luego se suaviza recursivamente: rma[i] = (rma[i-1]*(period-1) + x[i]) / period.
    Distinto de una EMA estándar (ewm con adjust=False usa el primer dato
    como seed en vez de una SMA), por eso se implementa aparte.
    """
    n = len(values)
    result = np.full(n, np.nan)
    if n < period:
        return result
    seed = np.nanmean(values[:period])
    result[period - 1] = seed
    prev = seed
    for i in range(period, n):
        prev = (prev * (period - 1) + values[i]) / period
        result[i] = prev
    return result


def add_technical_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    Indicadores técnicos clásicos sobre el precio de cierre, con la misma
    metodología usada en el backtest de CLAUDE.md: EMA20/50/200 (pandas
    ewm) y RSI14 con suavizado de Wilder (RMA), no una media simple de
    ganancias/pérdidas.

    Columnas nuevas:
        EMA20, EMA50, EMA200 — medias móviles exponenciales de Close
        RSI14                — RSI de 14 periodos (Wilder/RMA), 0-100
    """
    df = df.copy()

    df["EMA20"]  = df["Close"].ewm(span=20, adjust=False).mean()
    df["EMA50"]  = df["Close"].ewm(span=50, adjust=False).mean()
    df["EMA200"] = df["Close"].ewm(span=200, adjust=False).mean()

    delta = df["Close"].diff()
    gain  = delta.clip(lower=0).to_numpy()
    loss  = (-delta.clip(upper=0)).to_numpy()

    avg_gain = _wilder_rma(gain, 14)
    avg_loss = _wilder_rma(loss, 14)

    with np.errstate(divide="ignore", invalid="ignore"):
        rs  = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
    rsi = np.where(avg_loss == 0, 100.0, rsi)              # sin pérdidas → RSI 100
    rsi = np.where((avg_gain == 0) & (avg_loss == 0), 50.0, rsi)  # sin movimiento → neutral
    df["RSI14"] = rsi

    return df


def add_macd(df: pd.DataFrame, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.DataFrame:
    """
    MACD clásico (12,26,9) sobre Close.

    Columnas nuevas:
        MACD_Line   — EMA_fast - EMA_slow
        MACD_Signal — EMA de `signal` periodos de MACD_Line
        MACD_Hist   — MACD_Line - MACD_Signal (histograma)
    """
    df = df.copy()
    ema_fast = df["Close"].ewm(span=fast, adjust=False).mean()
    ema_slow = df["Close"].ewm(span=slow, adjust=False).mean()
    df["MACD_Line"]   = ema_fast - ema_slow
    df["MACD_Signal"] = df["MACD_Line"].ewm(span=signal, adjust=False).mean()
    df["MACD_Hist"]   = df["MACD_Line"] - df["MACD_Signal"]
    return df


def add_atr(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
    """
    ATR14 (Average True Range, suavizado de Wilder/RMA) — igual metodología
    que CLAUDE.md. Útil para dimensionar SL/TP según volatilidad real del
    activo en vez de un número fijo.

    Columnas nuevas:
        True_Range — max(High-Low, |High-PrevClose|, |Low-PrevClose|)
        ATR14      — RMA de 14 periodos de True_Range
        ATR14_%    — ATR14 / Close × 100 (volatilidad relativa, comparable entre activos)
    """
    df = df.copy()
    prev_close = df["Close"].shift(1)
    tr = pd.concat([
        df["High"] - df["Low"],
        (df["High"] - prev_close).abs(),
        (df["Low"] - prev_close).abs(),
    ], axis=1).max(axis=1)
    df["True_Range"] = tr
    df["ATR14"]   = _wilder_rma(tr.to_numpy(), period)
    df["ATR14_%"] = df["ATR14"] / df["Close"] * 100
    return df


def add_rolling_stats(df: pd.DataFrame, window: int = 20) -> pd.DataFrame:
    """
    Estadísticas rolling de 20 velas (misma ventana que usa CLAUDE.md para
    "nuevo mínimo/máximo de 20 velas" y "spike de volumen >2.5x").

    Columnas nuevas:
        Vol_MA20        — media móvil simple de Volume (20 velas)
        Vol_Spike_Ratio — Volume / Vol_MA20 (>2.5 = spike de volumen)
        High_20         — máximo de High en las últimas 20 velas (incluye la actual)
        Low_20          — mínimo de Low en las últimas 20 velas (incluye la actual)
        New_High_20     — True si la vela actual marca nuevo máximo de 20 velas
        New_Low_20      — True si la vela actual marca nuevo mínimo de 20 velas
    """
    df = df.copy()
    df["Vol_MA20"]        = df["Volume"].rolling(window).mean()
    df["Vol_Spike_Ratio"] = df["Volume"] / df["Vol_MA20"].replace(0, float("nan"))
    df["High_20"]         = df["High"].rolling(window).max()
    df["Low_20"]          = df["Low"].rolling(window).min()
    df["New_High_20"]     = df["High"] >= df["High_20"]
    df["New_Low_20"]      = df["Low"] <= df["Low_20"]
    return df


def add_candlestick_patterns(
    df: pd.DataFrame,
    doji_threshold: float = 0.1,
    wick_ratio: float = 2.0,
    small_wick_ratio: float = 1.0,
) -> pd.DataFrame:
    """
    Flags booleanos de patrones de vela clásicos, calculados desde OHLC
    (sin mirar el gráfico). Individuales, duales y de tres velas.

    NOTA: las definiciones de Morning/Evening Star omiten el requisito
    clásico de "gap" entre velas — cripto opera 24/7 y los gaps reales
    son raros, así que se usa solo tamaño de cuerpo + cierre más allá
    del punto medio de la primera vela (estándar en TA de cripto).

    Columnas nuevas:
        Doji, Hammer, Shooting_Star,
        Bullish_Engulfing, Bearish_Engulfing,
        Bullish_Harami, Bearish_Harami,
        Morning_Star, Evening_Star
    """
    df = df.copy()
    o, h, l, c = df["Open"], df["High"], df["Low"], df["Close"]

    body  = (c - o).abs()
    rng   = (h - l).replace(0, float("nan"))
    body_pct = body / rng

    body_top    = pd.concat([o, c], axis=1).max(axis=1)
    body_bottom = pd.concat([o, c], axis=1).min(axis=1)
    upper_wick  = h - body_top
    lower_wick  = body_bottom - l

    bullish = c > o
    bearish = c < o

    # --- Individuales ---
    df["Doji"] = body_pct <= doji_threshold

    df["Hammer"] = (
        (lower_wick >= wick_ratio * body) &
        (upper_wick <= small_wick_ratio * body) &
        (body_pct <= 0.35)
    )
    df["Shooting_Star"] = (
        (upper_wick >= wick_ratio * body) &
        (lower_wick <= small_wick_ratio * body) &
        (body_pct <= 0.35)
    )

    # --- Duales (vela actual vs anterior) ---
    prev_o, prev_c = o.shift(1), c.shift(1)
    prev_top    = pd.concat([prev_o, prev_c], axis=1).max(axis=1)
    prev_bottom = pd.concat([prev_o, prev_c], axis=1).min(axis=1)
    prev_bullish = prev_c > prev_o
    prev_bearish = prev_c < prev_o

    engulfs   = (body_top >= prev_top) & (body_bottom <= prev_bottom)
    contained = (body_top <= prev_top) & (body_bottom >= prev_bottom)

    df["Bullish_Engulfing"] = engulfs & bullish & prev_bearish
    df["Bearish_Engulfing"] = engulfs & bearish & prev_bullish
    df["Bullish_Harami"]    = contained & bullish & prev_bearish
    df["Bearish_Harami"]    = contained & bearish & prev_bullish

    # --- Tres velas (Morning/Evening Star) ---
    c1_o, c1_c = o.shift(2), c.shift(2)
    c1_body    = (c1_c - c1_o).abs()
    c1_mid     = (c1_o + c1_c) / 2
    c1_bullish = c1_c > c1_o
    c1_bearish = c1_c < c1_o

    c2_o, c2_c = o.shift(1), c.shift(1)
    c2_body    = (c2_c - c2_o).abs()
    c2_small   = c2_body <= 0.3 * c1_body.replace(0, float("nan"))

    c3_body    = body  # vela actual
    c3_confirms = c3_body >= 0.5 * c1_body.replace(0, float("nan"))

    df["Morning_Star"] = c1_bearish & c2_small & bullish & c3_confirms & (c > c1_mid)
    df["Evening_Star"] = c1_bullish & c2_small & bearish & c3_confirms & (c < c1_mid)

    return df


def add_all_technical_analysis(df: pd.DataFrame) -> pd.DataFrame:
    """Orquesta todos los indicadores/patrones técnicos sobre Close/OHLC."""
    df = add_technical_indicators(df)   # EMA20/50/200 + RSI14
    df = add_macd(df)
    df = add_atr(df)
    df = add_rolling_stats(df)
    df = add_candlestick_patterns(df)
    return df


def add_derived_quant_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """
    Indicadores cuantitativos calculados sobre el DataFrame enriquecido.

    Columnas nuevas:
        Taker_Pressure      — Taker_Buy_Vol / Volume  (>0.6 = presión compradora spot)
        OI_Price_Diverge    — (OI_Change_% − Cambio_%) / 2  (divergencia OI vs precio)
        Funding_Extreme     — True si |Funding_Rate| > 0.001  (señal contrarian)
        Fut_Spot_Delta_Diff — Fut_Delta_% − Volume_Delta_%  (divergencia futuros vs spot)
    """
    df = df.copy()

    if "Taker_Buy_Vol" in df.columns and "Volume" in df.columns:
        df["Taker_Pressure"] = df["Taker_Buy_Vol"] / df["Volume"].replace(0, float("nan"))

    if "OI_Change_%" in df.columns and "Cambio_%" in df.columns:
        df["OI_Price_Diverge"] = (df["OI_Change_%"] - df["Cambio_%"]) / 2

    if "Funding_Rate" in df.columns:
        df["Funding_Extreme"] = df["Funding_Rate"].abs() > 0.001

    if "Fut_Delta_%" in df.columns and "Volume_Delta_%" in df.columns:
        df["Fut_Spot_Delta_Diff"] = df["Fut_Delta_%"] - df["Volume_Delta_%"]

    return df
