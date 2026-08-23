"""ATR14 actual — consulta rápida de volatilidad de una cripto (opción 7 del menú)."""

from ..indicators import add_atr
from ..sources import download_ohlcv_timeframe_range
from .quant import MTF_DEFAULT_RANGE_DAYS


def calcular_atr_actual(
    symbol: str,
    timeframe: str,
    exchange_name: str = "binance",
) -> dict:
    """
    Descarga OHLCV reciente y calcula el ATR14 (Wilder/RMA) de la última vela
    cerrada, para dimensionar SL/TP según la volatilidad real del activo.

    El rango de descarga usa el mismo warmup por timeframe que la opción 6
    (`MTF_DEFAULT_RANGE_DAYS`) — de sobra para que el ATR14 (que converge en
    unas ~30-50 velas) ya no dependa del valor semilla inicial.

    Imprime el resultado en consola y también lo devuelve como dict
    (Close, ATR14, ATR14_%, fecha de la última vela).
    """
    days = MTF_DEFAULT_RANGE_DAYS.get(timeframe, 30)
    range_ms = days * 24 * 60 * 60 * 1000

    df = download_ohlcv_timeframe_range(
        symbol, timeframe=timeframe, range_ms=range_ms, exchange_name=exchange_name,
    )
    df = add_atr(df)

    last = df.iloc[-1]
    resultado = {
        "symbol": symbol,
        "timeframe": timeframe,
        "fecha": df.index[-1],
        "close": float(last["Close"]),
        "atr14": float(last["ATR14"]),
        "atr14_%": float(last["ATR14_%"]),
    }

    print(f"\n{'='*50}")
    print(f"  ATR14 actual — {symbol} ({timeframe})")
    print(f"{'='*50}")
    print(f"  Última vela cerrada : {resultado['fecha']}")
    print(f"  Close               : {resultado['close']:.8f}")
    print(f"  ATR14               : {resultado['atr14']:.8f}")
    print(f"  ATR14 %             : {resultado['atr14_%']:.4f}%")
    print(f"{'='*50}")

    return resultado
