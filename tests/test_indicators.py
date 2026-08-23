"""
Tests de core/indicators.py — toda la lógica de EMA/RSI/MACD/ATR/rolling y
patrones de vela, calculada desde OHLC/Close sin depender de red.

Los valores de referencia de RMA/ATR se calcularon a mano con period=2
(en vez del period=14 real) para que la recursión sea verificable con
lápiz y papel; ver comentarios junto a cada caso.
"""

import numpy as np
import pandas as pd
import pytest

from core.indicators import (
    _wilder_rma,
    add_all_technical_analysis,
    add_atr,
    add_candlestick_patterns,
    add_derived_quant_metrics,
    add_macd,
    add_market_metrics,
    add_rolling_stats,
    add_technical_indicators,
)


def _ohlc_df(rows: list[dict]) -> pd.DataFrame:
    """Arma un DataFrame OHLC mínimo (una fila por dict con O/H/L/C)."""
    return pd.DataFrame(
        [{"Open": r["O"], "High": r["H"], "Low": r["L"], "Close": r["C"]} for r in rows]
    )


# --- _wilder_rma (RMA de Wilder, base de RSI14/ATR14) ------------------

def test_wilder_rma_matches_hand_calculation():
    # values=[2,4,8,16], period=2:
    #   seed = mean([2,4]) = 3.0            -> idx1
    #   idx2 = (3.0*1 + 8) / 2  = 5.5
    #   idx3 = (5.5*1 + 16) / 2 = 10.75
    values = np.array([2.0, 4.0, 8.0, 16.0])
    result = _wilder_rma(values, period=2)
    assert np.isnan(result[0])
    assert result[1:] == pytest.approx([3.0, 5.5, 10.75])


def test_wilder_rma_returns_all_nan_when_shorter_than_period():
    values = np.array([1.0, 2.0, 3.0])
    result = _wilder_rma(values, period=5)
    assert np.all(np.isnan(result))


# --- RSI14 (casos límite documentados en el docstring) ------------------

def test_rsi_strictly_increasing_series_is_100():
    close = pd.Series(range(1, 21), dtype=float)  # sin pérdidas nunca
    df = pd.DataFrame({"Open": close, "High": close, "Low": close, "Close": close})
    out = add_technical_indicators(df)
    assert out["RSI14"].iloc[-1] == pytest.approx(100.0)


def test_rsi_strictly_decreasing_series_is_0():
    close = pd.Series(range(20, 0, -1), dtype=float)  # sin ganancias nunca
    df = pd.DataFrame({"Open": close, "High": close, "Low": close, "Close": close})
    out = add_technical_indicators(df)
    assert out["RSI14"].iloc[-1] == pytest.approx(0.0)


def test_rsi_flat_series_is_neutral_50():
    close = pd.Series([100.0] * 20)  # sin movimiento
    df = pd.DataFrame({"Open": close, "High": close, "Low": close, "Close": close})
    out = add_technical_indicators(df)
    assert out["RSI14"].iloc[-1] == pytest.approx(50.0)


def test_ema_columns_match_pandas_ewm_reference():
    close = pd.Series([10, 11, 12, 11, 13, 14, 13, 15, 16, 15], dtype=float)
    df = pd.DataFrame({"Open": close, "High": close + 0.5, "Low": close - 0.5, "Close": close})
    out = add_technical_indicators(df)
    for span, col in [(20, "EMA20"), (50, "EMA50"), (200, "EMA200")]:
        expected = close.ewm(span=span, adjust=False).mean()
        pd.testing.assert_series_equal(out[col], expected, check_names=False)


# --- MACD -----------------------------------------------------------------

def test_macd_hist_equals_line_minus_signal():
    close = pd.Series(np.linspace(100, 130, 40))
    df = pd.DataFrame({"Open": close, "High": close, "Low": close, "Close": close})
    out = add_macd(df)
    pd.testing.assert_series_equal(
        out["MACD_Hist"], out["MACD_Line"] - out["MACD_Signal"], check_names=False,
    )


# --- ATR14 (True Range calculado a mano, period=2 para verificar RMA) -----

def test_atr_true_range_and_atr_hand_calculation():
    df = _ohlc_df([
        {"O": 8.5, "H": 10, "L": 8, "C": 9},      # sin PrevClose -> TR = H-L = 2
        {"O": 9,   "H": 12, "L": 9, "C": 11},      # PrevClose=9   -> TR = max(3, 3, 0) = 3
        {"O": 11,  "H": 11, "L": 10, "C": 10.5},   # PrevClose=11  -> TR = max(1, 0, 1) = 1
        {"O": 10.5, "H": 13, "L": 10, "C": 12},    # PrevClose=10.5 -> TR = max(3, 2.5, 0.5) = 3
    ])
    out = add_atr(df, period=2)
    assert out["True_Range"].tolist() == pytest.approx([2, 3, 1, 3])
    # RMA period=2: seed=mean([2,3])=2.5 ; idx2=(2.5+1)/2=1.75 ; idx3=(1.75+3)/2=2.375
    assert np.isnan(out["ATR14"].iloc[0])
    assert out["ATR14"].iloc[1:].tolist() == pytest.approx([2.5, 1.75, 2.375])
    assert out["ATR14_%"].iloc[-1] == pytest.approx(2.375 / 12 * 100)


# --- Rolling 20 (probado con window=3 para que sea verificable a mano) ----

def test_rolling_stats_high_low_and_new_extremes():
    df = pd.DataFrame({
        "Open":  [0, 0, 0, 0, 0],
        "High":  [1, 2, 3, 4, 5],
        "Low":   [0, 1, 2, 3, 4],
        "Close": [1, 2, 3, 4, 5],
        "Volume": [10, 20, 30, 40, 50],
    })
    out = add_rolling_stats(df, window=3)
    assert out["Vol_MA20"].iloc[2:].tolist() == pytest.approx([20, 30, 40])
    assert out["Vol_Spike_Ratio"].iloc[2:].tolist() == pytest.approx([1.5, 40 / 30, 1.25])
    assert out["High_20"].iloc[2:].tolist() == pytest.approx([3, 4, 5])
    assert out["Low_20"].iloc[2:].tolist() == pytest.approx([0, 1, 2])
    # serie estrictamente creciente -> cada vela es nuevo máximo/mínimo de su ventana
    assert out["New_High_20"].iloc[2:].tolist() == [True, True, True]
    assert out["New_Low_20"].iloc[2:].tolist() == [False, False, False]


# --- Métricas de mercado ---------------------------------------------------

def test_add_market_metrics_basic_fields():
    df = pd.DataFrame({"Open": [100.0], "High": [105.0], "Low": [95.0], "Close": [110.0], "Volume": [10.0]})
    out = add_market_metrics(df)
    assert out["Variacion"].iloc[0] == pytest.approx(10.0)
    assert out["Variacion_%"].iloc[0] == pytest.approx(10.0)
    assert out["Rango_Dia"].iloc[0] == pytest.approx(10.0)
    assert bool(out["Tendencia_Alcista"].iloc[0]) is True


# --- Indicadores derivados combinados --------------------------------------

def test_add_derived_quant_metrics_computes_expected_values():
    df = pd.DataFrame({
        "Taker_Buy_Vol": [60.0],
        "Volume": [100.0],
        "OI_Change_%": [5.0],
        "Cambio_%": [1.0],
        "Funding_Rate": [0.002],
        "Fut_Delta_%": [10.0],
        "Volume_Delta_%": [4.0],
    })
    out = add_derived_quant_metrics(df)
    assert out["Taker_Pressure"].iloc[0] == pytest.approx(0.6)
    assert out["OI_Price_Diverge"].iloc[0] == pytest.approx((5.0 - 1.0) / 2)
    assert bool(out["Funding_Extreme"].iloc[0]) is True  # |0.002| > 0.001
    assert out["Fut_Spot_Delta_Diff"].iloc[0] == pytest.approx(6.0)


def test_add_derived_quant_metrics_skips_missing_source_columns():
    # Sin OI_Change_%/Cambio_% ni Fut_Delta_%/Volume_Delta_% no debe agregar
    # esas columnas derivadas (ni fallar).
    df = pd.DataFrame({"Funding_Rate": [0.0001]})
    out = add_derived_quant_metrics(df)
    assert "OI_Price_Diverge" not in out.columns
    assert "Fut_Spot_Delta_Diff" not in out.columns
    assert "Taker_Pressure" not in out.columns
    assert bool(out["Funding_Extreme"].iloc[0]) is False  # |0.0001| no supera 0.001


# --- Patrones de vela -------------------------------------------------------
# doji_threshold=0.1, wick_ratio=2.0, small_wick_ratio=1.0 (defaults)

def test_doji_detected_on_small_body():
    df = _ohlc_df([{"O": 10, "H": 11, "L": 9, "C": 10.05}])  # body_pct = 0.05/2 = 0.025
    out = add_candlestick_patterns(df)
    assert bool(out["Doji"].iloc[0]) is True
    assert bool(out["Hammer"].iloc[0]) is False
    assert bool(out["Shooting_Star"].iloc[0]) is False


def test_hammer_detected_on_long_lower_wick():
    # body=0.5, lower_wick=2 (>=2*body), upper_wick=0.1 (<=1*body), body_pct=0.5/2.6≈0.19
    df = _ohlc_df([{"O": 10, "H": 10.6, "L": 8, "C": 10.5}])
    out = add_candlestick_patterns(df)
    assert bool(out["Hammer"].iloc[0]) is True
    assert bool(out["Shooting_Star"].iloc[0]) is False


def test_shooting_star_detected_on_long_upper_wick():
    # body=0.5, upper_wick=2 (>=2*body), lower_wick=0.1 (<=1*body)
    df = _ohlc_df([{"O": 10, "H": 12, "L": 9.4, "C": 9.5}])
    out = add_candlestick_patterns(df)
    assert bool(out["Shooting_Star"].iloc[0]) is True
    assert bool(out["Hammer"].iloc[0]) is False


def test_bullish_engulfing():
    df = _ohlc_df([
        {"O": 10, "H": 10.1, "L": 8.9, "C": 9},      # bajista, body [9,10]
        {"O": 8.5, "H": 10.6, "L": 8.4, "C": 10.5},  # alcista, body [8.5,10.5] engulle
    ])
    out = add_candlestick_patterns(df)
    assert bool(out["Bullish_Engulfing"].iloc[1]) is True
    assert bool(out["Bearish_Engulfing"].iloc[1]) is False


def test_bearish_engulfing():
    df = _ohlc_df([
        {"O": 9, "H": 10.1, "L": 8.9, "C": 10},      # alcista, body [9,10]
        {"O": 10.5, "H": 10.6, "L": 8.4, "C": 8.5},  # bajista, body [8.5,10.5] engulle
    ])
    out = add_candlestick_patterns(df)
    assert bool(out["Bearish_Engulfing"].iloc[1]) is True
    assert bool(out["Bullish_Engulfing"].iloc[1]) is False


def test_bullish_harami():
    df = _ohlc_df([
        {"O": 10, "H": 10.1, "L": 7.9, "C": 8},      # bajista grande, body [8,10]
        {"O": 8.5, "H": 9.6, "L": 8.4, "C": 9.5},    # alcista chica, body [8.5,9.5] contenido
    ])
    out = add_candlestick_patterns(df)
    assert bool(out["Bullish_Harami"].iloc[1]) is True
    assert bool(out["Bearish_Harami"].iloc[1]) is False


def test_bearish_harami():
    df = _ohlc_df([
        {"O": 8, "H": 10.1, "L": 7.9, "C": 10},      # alcista grande, body [8,10]
        {"O": 9.5, "H": 9.6, "L": 8.4, "C": 8.5},    # bajista chica, body [8.5,9.5] contenido
    ])
    out = add_candlestick_patterns(df)
    assert bool(out["Bearish_Harami"].iloc[1]) is True
    assert bool(out["Bullish_Harami"].iloc[1]) is False


def test_morning_star():
    df = _ohlc_df([
        {"O": 10, "H": 10.1, "L": 6.9, "C": 7},      # c1 bajista grande, body=3, mid=8.5
        {"O": 6.9, "H": 7.1, "L": 6.8, "C": 7.0},    # c2 chica (body=0.1 <= 0.3*3)
        {"O": 7.0, "H": 9.1, "L": 6.9, "C": 9.0},    # c3 alcista, body=2 >= 0.5*3, cierra > mid
    ])
    out = add_candlestick_patterns(df)
    assert bool(out["Morning_Star"].iloc[2]) is True
    assert bool(out["Evening_Star"].iloc[2]) is False


def test_evening_star():
    df = _ohlc_df([
        {"O": 7, "H": 10.1, "L": 6.9, "C": 10},      # c1 alcista grande, body=3, mid=8.5
        {"O": 10.0, "H": 10.1, "L": 9.8, "C": 9.9},  # c2 chica (body=0.1 <= 0.3*3)
        {"O": 9.9, "H": 10.0, "L": 7.4, "C": 7.5},   # c3 bajista, body=2.4 >= 0.5*3, cierra < mid
    ])
    out = add_candlestick_patterns(df)
    assert bool(out["Evening_Star"].iloc[2]) is True
    assert bool(out["Morning_Star"].iloc[2]) is False


# --- Orquestador ------------------------------------------------------------

def test_add_all_technical_analysis_adds_every_expected_column():
    close = pd.Series(np.linspace(100, 130, 30))
    df = pd.DataFrame({
        "Open": close, "High": close + 1, "Low": close - 1, "Close": close,
        "Volume": np.linspace(1000, 2000, 30),
    })
    out = add_all_technical_analysis(df)
    expected_cols = {
        "EMA20", "EMA50", "EMA200", "RSI14",
        "MACD_Line", "MACD_Signal", "MACD_Hist",
        "True_Range", "ATR14", "ATR14_%",
        "Vol_MA20", "Vol_Spike_Ratio", "High_20", "Low_20", "New_High_20", "New_Low_20",
        "Doji", "Hammer", "Shooting_Star",
        "Bullish_Engulfing", "Bearish_Engulfing",
        "Bullish_Harami", "Bearish_Harami",
        "Morning_Star", "Evening_Star",
    }
    assert expected_cols.issubset(out.columns)
