"""
Fuentes de futuros perpetuos: funding rate, open interest, long/short ratio
y taker buy/sell ratio (sustituto de liquidaciones históricas).

Open interest, long/short ratio y taker ratio comparten la misma restricción
y forma de paginación — endpoints `fapiData*` de Binance, llamados directo
vía ccxt (`exchange.fapiDataGet*`) porque `since`/`startTime` no funciona de
forma confiable en el wrapper normal de ccxt para estos endpoints en
particular. `_download_fapi_history()` generaliza esa paginación; cada
función pública solo aporta el endpoint y cómo mapear cada fila cruda a
columnas.

Funding rate usa un endpoint distinto (`exchange.fetch_funding_rate_history`,
sí soportado por ccxt) y necesita su propio manejo de resolución/timeframe,
así que se mantiene aparte.
"""

import time
from typing import Callable

import pandas as pd

from ..exchange import futures_symbol, init_exchange, spot_symbol

# Binance solo acepta estos periodos en los endpoints fapiData de OI/L-S/taker.
# Timeframes no soportados se mapean al más cercano disponible.
_BINANCE_FAPI_PERIOD_MAP = {
    "1m": "5m", "3m": "5m", "5m": "5m",
    "15m": "15m", "30m": "30m",
    "1h": "1h", "2h": "2h", "4h": "4h",
    "6h": "6h", "8h": "6h", "12h": "12h",
    "1d": "1d", "3d": "1d", "1w": "1d",
}
_FAPI_MAX_LOOKBACK_MS = 30 * 24 * 60 * 60 * 1000   # Binance limita a ~30 días


def _fapi_period(timeframe: str) -> str:
    """Convierte un timeframe ccxt al periodo válido para los endpoints fapiData."""
    p = _BINANCE_FAPI_PERIOD_MAP.get(timeframe)
    if p is None:
        raise ValueError(
            f"Timeframe '{timeframe}' sin mapeo a periodo fapi. "
            f"Usa uno de: {list(_BINANCE_FAPI_PERIOD_MAP)}"
        )
    if p != timeframe:
        print(f"  [INFO] Timeframe '{timeframe}' mapeado a periodo fapi '{p}'.")
    return p


def _download_fapi_history(
    symbol: str,
    timeframe: str,
    range_ms: int,
    exchange_name: str,
    endpoint_name: str,
    row_mapper: Callable[[dict], dict],
    label: str,
    sleep_seconds: float = 0.5,
) -> pd.DataFrame:
    """
    Pagina un endpoint `fapiData*` de Binance en ventanas de 500 velas,
    recortado a los últimos `_FAPI_MAX_LOOKBACK_MS` (~30 días).

    `endpoint_name` es el nombre del método ccxt raw (ej. "fapiDataGetOpenInterestHist").
    `row_mapper(raw_row) -> dict` debe incluir siempre la clave "timestamp".
    `label` se usa en los mensajes de aviso (ej. "open interest").
    """
    exchange = init_exchange(exchange_name, "future")
    period   = _fapi_period(timeframe)
    sym_raw  = spot_symbol(symbol).replace("/", "")
    step_ms  = exchange.parse_timeframe(timeframe) * 1000
    batch_ms = 500 * step_ms

    now   = exchange.milliseconds()
    since = max(now - range_ms, now - _FAPI_MAX_LOOKBACK_MS + step_ms)
    rows: list[dict] = []
    fetch = getattr(exchange, endpoint_name)

    while since < now:
        end_time = min(since + batch_ms, now)
        try:
            batch = fetch({
                "symbol":    sym_raw,
                "period":    period,
                "limit":     500,
                "startTime": since,
                "endTime":   end_time,
            })
        except Exception as e:
            print(f"  [AVISO] {label} batch error: {e}")
            break
        if not batch:
            break
        rows.extend(row_mapper(r) for r in batch)
        if len(batch) < 500:
            break
        since = int(batch[-1]["timestamp"]) + step_ms
        time.sleep(sleep_seconds)

    if not rows:
        print(f"  [AVISO] Sin datos de {label} para '{symbol}'.")
        return pd.DataFrame()

    fmt = "%Y-%m-%d" if timeframe == "1d" else "%Y-%m-%d %H:%M"
    df = pd.DataFrame(rows).drop_duplicates(subset=["timestamp"]).sort_values("timestamp")
    df["Fecha"] = pd.to_datetime(df["timestamp"], unit="ms").dt.strftime(fmt)
    df.set_index("Fecha", inplace=True)
    df.drop(columns=["timestamp"], inplace=True)
    return df


def download_funding_rate_history(
    symbol: str,
    timeframe: str,
    range_ms: int,
    exchange_name: str = "binance",
    sleep_seconds: float = 0.5,
) -> pd.DataFrame:
    """
    Descarga el historial de funding rate (cada 8h) para el perpetuo.

    Columnas:
        Funding_Rate         — tasa de funding en el período (0.0001 = 0.01%)
        Funding_Rate_Acum_8h — funding acumulado en las últimas 8 velas (1 día)
        Funding_Mark_Price   — mark price en el momento del funding

    NOTA (bug corregido): el funding se publica cada 8h con timestamps tipo
    "AAAA-MM-DD HH:MM". Si el OHLCV al que se va a unir es diario ("1d"),
    su índice es solo "AAAA-MM-DD" (sin hora) — un join por índice exacto
    contra timestamps con hora nunca calza y toda la columna queda NaN.
    Por eso aquí se recibe `timeframe` y, si es diario, se colapsan los
    ~3 eventos de funding de cada día a una sola fila (el último valor del
    día) para que el índice quede en el mismo formato que el OHLCV diario.
    """
    exchange = init_exchange(exchange_name, "future")
    sym = futures_symbol(symbol)
    since = exchange.milliseconds() - range_ms
    rows: list[dict] = []

    while True:
        batch = exchange.fetch_funding_rate_history(sym, since=since, limit=1000)
        if not batch:
            break
        for r in batch:
            rows.append({
                "timestamp":        r["timestamp"],
                "Funding_Rate":     r.get("fundingRate"),
                "Funding_Mark_Price": r.get("markPrice"),
            })
        if len(batch) < 1000:
            break
        since = batch[-1]["timestamp"] + 1
        time.sleep(sleep_seconds)

    if not rows:
        print(f"  [AVISO] Sin datos de funding rate para '{symbol}'.")
        return pd.DataFrame()

    df = pd.DataFrame(rows).drop_duplicates(subset=["timestamp"]).sort_values("timestamp")
    df["Funding_Rate_Acum_8h"] = df["Funding_Rate"].rolling(3).sum()

    fmt = "%Y-%m-%d" if timeframe == "1d" else "%Y-%m-%d %H:%M"
    df["Fecha"] = pd.to_datetime(df["timestamp"], unit="ms").dt.strftime(fmt)
    df.drop(columns=["timestamp"], inplace=True)

    if timeframe == "1d":
        # Varias filas de 8h caen en la misma fecha → colapsar a 1 fila/día
        # (último valor del día, más cercano al cierre diario).
        df = df.groupby("Fecha", as_index=True).last()
    else:
        df.set_index("Fecha", inplace=True)

    return df


def download_open_interest_history(
    symbol: str,
    timeframe: str,
    range_ms: int,
    exchange_name: str = "binance",
    sleep_seconds: float = 0.5,
) -> pd.DataFrame:
    """
    Descarga el historial de open interest usando el endpoint raw de Binance
    fapiDataGetOpenInterestHist (evita el bug de startTime en ccxt).

    Limitación de Binance: máximo ~30 días de histórico para periodos ≤1h.

    Columnas:
        OI_Amount       — contratos abiertos en unidades base (DOGE)
        OI_Value_USDT   — OI valorado en USDT
        OI_Change_%     — variación porcentual del OI respecto a la vela anterior
    """
    def row_mapper(r: dict) -> dict:
        return {
            "timestamp":     int(r["timestamp"]),
            "OI_Amount":     float(r["sumOpenInterest"]),
            "OI_Value_USDT": float(r["sumOpenInterestValue"]),
        }

    df = _download_fapi_history(
        symbol, timeframe, range_ms, exchange_name,
        endpoint_name="fapiDataGetOpenInterestHist",
        row_mapper=row_mapper,
        label="open interest",
        sleep_seconds=sleep_seconds,
    )
    if not df.empty:
        df["OI_Change_%"] = df["OI_Value_USDT"].pct_change() * 100
    return df


def download_long_short_ratio(
    symbol: str,
    timeframe: str,
    range_ms: int,
    exchange_name: str = "binance",
    sleep_seconds: float = 0.5,
) -> pd.DataFrame:
    """
    Descarga el ratio long/short de cuentas usando el endpoint raw
    fapiDataGetGlobalLongShortAccountRatio (evita el bug de startTime en ccxt).

    Limitación de Binance: máximo ~30 días de histórico.

    Columnas:
        LS_Ratio        — long / short  (>2 = multitud excesivamente larga → señal contrarian bajista)
        LS_Long_Pct     — % de cuentas en posición long
        LS_Short_Pct    — % de cuentas en posición short
    """
    def row_mapper(r: dict) -> dict:
        return {
            "timestamp":    int(r["timestamp"]),
            "LS_Ratio":     float(r["longShortRatio"]),
            "LS_Long_Pct":  float(r["longAccount"]),
            "LS_Short_Pct": float(r["shortAccount"]),
        }

    return _download_fapi_history(
        symbol, timeframe, range_ms, exchange_name,
        endpoint_name="fapiDataGetGlobalLongShortAccountRatio",
        row_mapper=row_mapper,
        label="long/short ratio",
        sleep_seconds=sleep_seconds,
    )


def download_futures_taker_ratio(
    symbol: str,
    timeframe: str,
    range_ms: int,
    exchange_name: str = "binance",
    sleep_seconds: float = 0.5,
) -> pd.DataFrame:
    """
    Descarga el ratio taker buy/sell de futuros perpetuos usando
    fapiDataGetTakerlongshortRatio.

    NOTA TÉCNICA: Binance no expone liquidaciones históricas de mercado vía
    REST (solo stream WebSocket en tiempo real). Este endpoint es el sustituto
    disponible: mide el volumen de órdenes de mercado compradoras vs
    vendedoras en futuros perpetuos, capturando la misma presión agresiva que
    generan las liquidaciones en cascada.

    Columnas:
        Fut_Buy_Vol        — volumen taker comprador en futuros (USDT)
        Fut_Sell_Vol       — volumen taker vendedor en futuros (USDT)
        Fut_Buy_Sell_Ratio — buy_vol / sell_vol  (>1 = presión compradora en futuros)
        Fut_Delta_Vol      — Fut_Buy_Vol − Fut_Sell_Vol  (positivo = dominio comprador)
        Fut_Delta_%        — delta relativo al volumen total de futuros
    """
    def row_mapper(r: dict) -> dict:
        buy_vol  = float(r.get("buyVol",  0) or 0)
        sell_vol = float(r.get("sellVol", 0) or 0)
        total    = buy_vol + sell_vol
        return {
            "timestamp":          int(r["timestamp"]),
            "Fut_Buy_Vol":        buy_vol,
            "Fut_Sell_Vol":       sell_vol,
            "Fut_Buy_Sell_Ratio": float(r.get("buySellRatio", 0) or 0),
            "Fut_Delta_Vol":      buy_vol - sell_vol,
            "Fut_Delta_%":        ((buy_vol - sell_vol) / total * 100) if total else None,
        }

    return _download_fapi_history(
        symbol, timeframe, range_ms, exchange_name,
        endpoint_name="fapiDataGetTakerlongshortRatio",
        row_mapper=row_mapper,
        label="futures taker ratio",
        sleep_seconds=sleep_seconds,
    )
