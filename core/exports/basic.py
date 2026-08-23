"""
Exportaciones CSV/JSON "básicas" — solo OHLCV + métricas de mercado
derivadas (`add_market_metrics`), sin las fuentes de futuros/order book.
Corresponden a las opciones 1-4 del menú.
"""

import json
from datetime import datetime
from pathlib import Path

import pandas as pd

from ..config import OUTPUT_DIR
from ..indicators import add_market_metrics
from ..sources import download_ohlcv, download_ohlcv_paginado, download_ohlcv_timeframe_range
from ..utils import normalize_symbol_for_filename, serialize_value

# Columnas comunes a las tres exportaciones CSV básicas (1, 2 y 4).
_BASIC_EXPORT_COLUMNS = [
    "Open", "High", "Low", "Close", "Volume", "Volumen_USD", "Rango_Dia",
    "Volatilidad_Diaria", "Precio_Medio", "Precio_Tipico", "Variacion", "Variacion_%",
    "Tendencia_Alcista", "Cambio_Absoluto", "Cambio_%",
]


def _export_basic_csv(raw_data: pd.DataFrame, filename: str | Path) -> str:
    df = add_market_metrics(raw_data)
    cols = [c for c in _BASIC_EXPORT_COLUMNS if c in df.columns]
    df_export = df[cols].copy()
    df_export.index.name = "Fecha"
    df_export.to_csv(filename, encoding="utf-8", float_format="%.8f")
    return str(Path(filename).resolve())


def exportar_csv_ultimos_30_dias(symbol: str, filename: str | None = None, exchange_name: str = "binance") -> str:
    raw_data = download_ohlcv(symbol, limit=30, exchange_name=exchange_name)
    fecha_gen = datetime.now().strftime("%Y-%m-%d")
    safe_symbol = normalize_symbol_for_filename(symbol)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    filename = filename or OUTPUT_DIR / f"{fecha_gen}_{safe_symbol}_ultimos_30_dias.csv"
    return _export_basic_csv(raw_data, filename)


def exportar_csv_365_dias(symbol: str, filename: str | None = None, exchange_name: str = "binance") -> str:
    print(f"Descargando 365 días para {symbol}...")
    raw_data = download_ohlcv_paginado(symbol, days=365, exchange_name=exchange_name)
    fecha_gen = datetime.now().strftime("%Y-%m-%d")
    safe_symbol = normalize_symbol_for_filename(symbol)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    filename = filename or OUTPUT_DIR / f"{fecha_gen}_{safe_symbol}_ultimos_365_dias.csv"
    return _export_basic_csv(raw_data, filename)


def exportar_csv_personalizado(
    symbol: str,
    timeframe: str,
    range_label: str,
    range_ms: int,
    filename: str | None = None,
    exchange_name: str = "binance",
) -> str:
    print(f"Descargando {symbol} | {timeframe} | {range_label}...")
    raw_data = download_ohlcv_timeframe_range(symbol, timeframe=timeframe, range_ms=range_ms, exchange_name=exchange_name)
    fecha_gen = datetime.now().strftime("%Y-%m-%d")
    safe_symbol = normalize_symbol_for_filename(symbol)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    filename = filename or OUTPUT_DIR / f"{fecha_gen}_{safe_symbol}_{timeframe}_{range_label.replace(' ','_')}.csv"
    return _export_basic_csv(raw_data, filename)


def exportar_json_indicadores(symbol: str, exchange_name: str = "binance") -> str:
    raw_data = download_ohlcv(symbol, limit=30, exchange_name=exchange_name)
    df = add_market_metrics(raw_data)
    last_row = df.iloc[-1]
    last_date = df.index[-1]
    indicadores = {col: serialize_value(last_row[col]) for col in df.columns}
    payload = {
        "symbol": symbol,
        "exchange": exchange_name,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "last_market_timestamp": last_date,
        "indicators": indicadores,
    }
    fecha_gen = datetime.now().strftime("%Y-%m-%d")
    safe_symbol = normalize_symbol_for_filename(symbol)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    filename = OUTPUT_DIR / f"{fecha_gen}_{safe_symbol}_indicadores.json"
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    return str(Path(filename).resolve())
