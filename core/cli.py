"""Menú interactivo por consola — punto de entrada del programa."""

from .config import RANGE_OPTIONS_MS, TIMEFRAME_OPTIONS, load_config
from .exports import (
    exportar_csv_365_dias,
    exportar_csv_personalizado,
    exportar_csv_quant_completo,
    exportar_csv_ultimos_30_dias,
    exportar_json_indicadores,
    exportar_multi_timeframe,
)


def main() -> None:
    cfg = load_config()
    exchange_name: str = cfg.get("exchange", "binance")
    symbols_list: list[str] = cfg.get("symbols", [])
    default_symbol: str = cfg.get("default_symbol", symbols_list[0] if symbols_list else "DOGE/USDT")
    simbolos = {str(i + 1): sym for i, sym in enumerate(symbols_list)}

    def seleccionar_simbolo() -> str:
        print("\nElige la cripto:")
        for key, sym in simbolos.items():
            print(f"  {key}. {sym}")
        op = input(f"Opción ({'/'.join(simbolos.keys())}): ").strip()
        return simbolos.get(op, default_symbol)

    def seleccionar_timeframe() -> str:
        print("\nElige el periodo de las velas:")
        for key, tf in TIMEFRAME_OPTIONS.items():
            print(f"  {key}. {tf}")
        op = input("Opción (1/2/3/4/5): ").strip()
        return TIMEFRAME_OPTIONS.get(op, "1h")

    def seleccionar_rango() -> tuple[str, int]:
        print("\nElige el rango de datos:")
        for key, (label, _) in RANGE_OPTIONS_MS.items():
            print(f"  {key}. {label}")
        op = input(f"Opción ({'/'.join(RANGE_OPTIONS_MS.keys())}): ").strip()
        return RANGE_OPTIONS_MS.get(op, ("7d", 7 * 24 * 60 * 60 * 1000))

    while True:
        print("\n" + "="*55)
        print("  CryptoData — Descargador Cuantitativo (ccxt/Binance)")
        print("="*55)
        print("  1. CSV últimos 30 días           (OHLCV básico)")
        print("  2. CSV últimos 365 días          (OHLCV básico)")
        print("  3. JSON indicadores último día   (OHLCV básico)")
        print("  4. CSV personalizado por TF/rango (OHLCV básico)")
        print("  ─────────────────────────────────────────────────")
        print("  5. CSV cuantitativo COMPLETO     (todas las fuentes)")
        print("  ─────────────────────────────────────────────────")
        print("  6. CSV MULTI-TIMEFRAME COMPLETO  (5m,15m,1h,4h,1d,1w)")
        print("     una carpeta con un CSV quant por timeframe")
        print("  ─────────────────────────────────────────────────")
        print("  0. Salir")
        print("="*55)
        opcion = input("\nElige una opción: ").strip()

        if opcion == "1":
            symbol = seleccionar_simbolo()
            ruta = exportar_csv_ultimos_30_dias(symbol, exchange_name=exchange_name)
            print(f"CSV generado: {ruta}")

        elif opcion == "2":
            symbol = seleccionar_simbolo()
            ruta = exportar_csv_365_dias(symbol, exchange_name=exchange_name)
            print(f"CSV generado: {ruta}")

        elif opcion == "3":
            symbol = seleccionar_simbolo()
            ruta = exportar_json_indicadores(symbol, exchange_name=exchange_name)
            print(f"JSON generado: {ruta}")

        elif opcion == "4":
            symbol = seleccionar_simbolo()
            timeframe = seleccionar_timeframe()
            range_label, range_ms = seleccionar_rango()
            ruta = exportar_csv_personalizado(
                symbol, timeframe=timeframe, range_label=range_label,
                range_ms=range_ms, exchange_name=exchange_name,
            )
            print(f"CSV generado: {ruta}")

        elif opcion == "5":
            symbol = seleccionar_simbolo()
            timeframe = seleccionar_timeframe()
            range_label, range_ms = seleccionar_rango()
            ruta = exportar_csv_quant_completo(
                symbol, timeframe=timeframe, range_label=range_label,
                range_ms=range_ms, exchange_name=exchange_name,
            )
            print(f"\nArchivo final: {ruta}")

        elif opcion == "6":
            symbol = seleccionar_simbolo()
            rutas = exportar_multi_timeframe(symbol, exchange_name=exchange_name)
            print(f"\n{len(rutas)} archivo(s) generado(s).")

        elif opcion == "0":
            print("Saliendo...")
            break

        else:
            print("Opción no válida.")
