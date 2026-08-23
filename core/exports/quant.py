"""
Exportación cuantitativa completa (opción 5: todas las fuentes fusionadas)
y su variante multi-timeframe (opción 6: 5m/15m/1h/4h/1d/1w en una corrida).
"""

from datetime import datetime
from pathlib import Path

from ..config import OUTPUT_DIR
from ..indicators import add_all_technical_analysis, add_derived_quant_metrics, add_market_metrics
from ..merge import build_export_columns, merge_all_sources
from ..sources import (
    download_funding_rate_history,
    download_futures_taker_ratio,
    download_long_short_ratio,
    download_ohlcv_taker,
    download_open_interest_history,
    fetch_orderbook_metrics,
    fetch_ticker_metrics,
)
from ..utils import normalize_symbol_for_filename


def exportar_csv_quant_completo(
    symbol: str,
    timeframe: str,
    range_label: str,
    range_ms: int,
    exchange_name: str = "binance",
    filename: str | None = None,
) -> str:
    """
    Descarga y fusiona todas las fuentes disponibles:
        - OHLCV + taker buy/sell volume (spot)
        - Funding rate histórico (futuros)
        - Open interest histórico (futuros)
        - Long/short ratio (futuros)
        - Liquidaciones agregadas (futuros)
        - Ticker 24h snapshot (spot)
        - Order book snapshot (spot)

    Genera un CSV con todos los campos alineados por timestamp.
    """
    print(f"\n{'='*60}")
    print(f"  Exportación cuantitativa completa")
    print(f"  Símbolo: {symbol} | TF: {timeframe} | Rango: {range_label}")
    print(f"{'='*60}")

    # --- 1. OHLCV con taker volume ---
    print("[1/6] Descargando OHLCV + taker volume...")
    ohlcv = download_ohlcv_taker(symbol, timeframe, range_ms, exchange_name)
    ohlcv = add_market_metrics(ohlcv)
    ohlcv = add_all_technical_analysis(ohlcv)

    # --- 2. Funding rate ---
    print("[2/6] Descargando funding rate...")
    try:
        funding = download_funding_rate_history(symbol, timeframe, range_ms, exchange_name)
    except Exception as e:
        print(f"  [AVISO] Funding rate no disponible: {e}")
        funding = None

    # --- 3. Open interest ---
    print("[3/6] Descargando open interest...")
    try:
        oi = download_open_interest_history(symbol, timeframe, range_ms, exchange_name)
    except Exception as e:
        print(f"  [AVISO] Open interest no disponible: {e}")
        oi = None

    # --- 4. Long/short ratio ---
    print("[4/6] Descargando long/short ratio...")
    try:
        ls = download_long_short_ratio(symbol, timeframe, range_ms, exchange_name)
    except Exception as e:
        print(f"  [AVISO] Long/short ratio no disponible: {e}")
        ls = None

    # --- 5. Futures taker buy/sell ratio ---
    print("[5/6] Descargando futures taker ratio...")
    try:
        fut_taker = download_futures_taker_ratio(symbol, timeframe, range_ms, exchange_name)
    except Exception as e:
        print(f"  [AVISO] Futures taker ratio no disponible: {e}")
        fut_taker = None

    # --- 6. Snapshot ticker + order book ---
    print("[6/6] Obteniendo snapshot de ticker y order book...")
    ticker_metrics = {}
    ob_metrics = {}
    try:
        ticker_metrics = fetch_ticker_metrics(symbol, exchange_name)
    except Exception as e:
        print(f"  [AVISO] Ticker no disponible: {e}")
    try:
        ob_metrics = fetch_orderbook_metrics(symbol, exchange_name)
    except Exception as e:
        print(f"  [AVISO] Order book no disponible: {e}")

    # --- Fusión ---
    print("\nFusionando fuentes...")
    df = merge_all_sources(ohlcv, funding=funding, oi=oi, ls_ratio=ls,
                           fut_taker=fut_taker)
    df = add_derived_quant_metrics(df)

    # Añadir ticker y OB como columnas constantes (snapshot del momento de descarga)
    for key, val in {**ticker_metrics, **ob_metrics}.items():
        if key not in ("OB_Timestamp",):
            df[key] = val

    # Exportar
    cols = build_export_columns(df)
    df_export = df[cols].copy()
    df_export.index.name = "Fecha"

    fecha_gen = datetime.now().strftime("%Y-%m-%d")
    safe_symbol = normalize_symbol_for_filename(symbol)
    if filename is None:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        filename = OUTPUT_DIR / f"{fecha_gen}_{safe_symbol}_{timeframe}_{range_label.replace(' ','_')}_quant.csv"
    df_export.to_csv(filename, encoding="utf-8", float_format="%.10f")

    n_cols = len(df_export.columns)
    n_rows = len(df_export)
    print(f"\n{'='*60}")
    print(f"  CSV generado: {filename}")
    print(f"  Filas: {n_rows:,} | Columnas: {n_cols}")
    print(f"  Fuentes incluidas:")
    print(f"    OHLCV + Taker Vol    : {'Si' if 'Taker_Buy_Vol' in df.columns else 'No'}")
    print(f"    EMA20/50/200 + RSI14 : {'Si' if 'RSI14' in df.columns else 'No'}")
    print(f"    MACD + ATR14         : {'Si' if 'MACD_Hist' in df.columns else 'No'}")
    print(f"    Rolling 20 (Vol/S-R) : {'Si' if 'High_20' in df.columns else 'No'}")
    print(f"    Patrones de vela     : {'Si' if 'Doji' in df.columns else 'No'}")
    print(f"    Order Book           : {'Si' if 'OB_Spread' in df.columns else 'No'}")
    print(f"    Funding Rate         : {'Si' if 'Funding_Rate' in df.columns else 'No'}")
    print(f"    Open Interest        : {'Si' if 'OI_Amount' in df.columns else 'No'}")
    print(f"    Long/Short Ratio     : {'Si' if 'LS_Ratio' in df.columns else 'No'}")
    print(f"    Futures Taker Ratio  : {'Si' if 'Fut_Buy_Sell_Ratio' in df.columns else 'No'}")
    print(f"    Ticker 24h           : {'Si' if 'Ticker_VWAP' in df.columns else 'No'}")
    print(f"{'='*60}")

    return str(Path(filename).resolve())


# Reemplaza el flujo manual de "subir 6 capturas de TradingView, un timeframe
# a la vez". Cada timeframe se descarga nativo desde Binance (no resampleado
# desde 5m) para poder pedir suficiente historia por timeframe sin explotar
# el número de filas: un EMA200 diario necesita ~200 velas de historia, un
# EMA200 semanal necesita ~200 semanas — cosas muy distintas de rango.
MTF_TIMEFRAMES = ["5m", "15m", "1h", "4h", "1d", "1w"]

# Rango por defecto (en días) por timeframe — pensado para que EMA200/RSI14/
# ATR14 tengan suficiente warmup sin descargar más filas de las necesarias.
MTF_DEFAULT_RANGE_DAYS = {
    "5m":  2,
    "15m": 7,
    "1h":  30,
    "4h":  90,
    "1d":  400,
    "1w":  1825,   # ~5 años, para que EMA200 semanal tenga warmup real
}


def exportar_multi_timeframe(
    symbol: str,
    exchange_name: str = "binance",
    timeframes: list[str] | None = None,
    range_days_map: dict[str, int] | None = None,
    output_dir: str | None = None,
) -> list[str]:
    """
    Descarga y enriquece el símbolo en varios timeframes en una sola
    corrida (por defecto: 5m, 15m, 1h, 4h, 1d, 1w — el mismo set que un
    chequeo manual de gráficos 1W→5M en TradingView), cada uno con OHLCV +
    order flow + funding/OI/L-S + EMA/RSI/MACD/ATR/rolling 20 + patrones
    de vela.

    Genera un CSV *_quant.csv por timeframe dentro de una subcarpeta
    'output/AAAA-MM-DD_SIMBOLO_MTF/'. Toma varios minutos: cada timeframe
    repite las mismas descargas (funding, OI, L/S, taker ratio, etc.) que
    la opción 5 individual.
    """
    timeframes     = timeframes or MTF_TIMEFRAMES
    range_days_map = range_days_map or MTF_DEFAULT_RANGE_DAYS
    safe_symbol    = normalize_symbol_for_filename(symbol)
    fecha_gen      = datetime.now().strftime("%Y-%m-%d")
    out_dir        = Path(output_dir) if output_dir else OUTPUT_DIR / f"{fecha_gen}_{safe_symbol}_MTF"
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n{'='*60}")
    print(f"  Exportación multi-timeframe: {symbol}")
    print(f"  Timeframes: {', '.join(timeframes)}")
    print(f"  Carpeta de salida: {out_dir.resolve()}")
    print(f"{'='*60}")

    generated: list[str] = []
    for tf in timeframes:
        days        = range_days_map.get(tf, 30)
        range_ms    = days * 24 * 60 * 60 * 1000
        range_label = f"{days}d"
        print(f"\n--- Timeframe {tf} ({range_label}) ---")
        filename = out_dir / f"{fecha_gen}_{safe_symbol}_{tf}_{range_label}_quant.csv"
        try:
            ruta = exportar_csv_quant_completo(
                symbol, timeframe=tf, range_label=range_label, range_ms=range_ms,
                exchange_name=exchange_name,
                filename=str(filename),
            )
            generated.append(ruta)
        except Exception as e:
            print(f"  [AVISO] Fallo en timeframe {tf}: {e}")

    print(f"\n{'='*60}")
    print(f"  Multi-timeframe completo: {len(generated)}/{len(timeframes)} archivos generados")
    for g in generated:
        print(f"    - {g}")
    print(f"{'='*60}")
    return generated
