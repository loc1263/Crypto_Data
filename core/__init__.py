"""
core — Descargador cuantitativo de datos crypto vía ccxt/Binance.

Mapa de módulos:
    config      — config.json, opciones de timeframe/rango del menú.
    exchange    — normalización de símbolos e instancias ccxt.
    utils       — helpers genéricos (nombres de archivo, serialización JSON).
    sources/    — descargas desde Binance (OHLCV, order book, ticker, futuros).
    indicators  — métricas de mercado, indicadores técnicos, patrones de vela.
    merge       — fusión de fuentes por índice temporal + columnas de export.
    exports/    — funciones exportar_* que arman los CSV/JSON finales.
    cli         — menú interactivo por consola (punto de entrada de main()).
"""
