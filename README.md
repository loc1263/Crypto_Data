# CryptoData — Descargador Cuantitativo de Datos Crypto

Herramienta de línea de comandos que descarga y combina datos de mercado de **Binance** (spot y futuros perpetuos) vía [ccxt](https://github.com/ccxt/ccxt), calcula indicadores cuantitativos derivados y exporta el resultado a **CSV**/**JSON** alineado por timestamp.

El punto de entrada es `criptodata.py`; toda la lógica vive en el paquete `core/`.

## Contenido 

- [Requisitos](#requisitos)
- [Configuración](#configuración)
- [Uso](#uso)
- [Estructura del paquete](#estructura-del-paquete)
- [Menú interactivo](#menú-interactivo)
- [Fuentes de datos y columnas generadas](#fuentes-de-datos-y-columnas-generadas)
- [Limitaciones conocidas](#limitaciones-conocidas)
- [Estructura de archivos generados](#estructura-de-archivos-generados)
- [Extender el proyecto](#extender-el-proyecto)

## Requisitos

- Python 3.10+ (usa sintaxis `list[str]`, `X | None`)
- Dependencias:
  ```bash
  pip install ccxt pandas
  ```
- Conexión a internet (usa los endpoints públicos de Binance, no requiere API key).

## Configuración

El programa lee `config.json` (mismo directorio que `criptodata.py`) al arrancar:

```json
{
    "exchange": "binance",
    "default_symbol": "DOGE/USDT",
    "symbols": [
        "DOGE/USDT",
        "BTC/USDT",
        "BNB/USDT",
        "ZEC/USDT"
    ]
}
```

- **exchange**: id de exchange ccxt a usar (por defecto `binance`).
- **default_symbol**: símbolo usado si la selección del menú es inválida.
- **symbols**: lista de símbolos ofrecidos en el menú interactivo (se numeran automáticamente).

Los símbolos se normalizan internamente (`core/exchange.py`):
- `spot_symbol()` convierte `"DOGE-USD"` / `"DOGEUSDT"` → `"DOGE/USDT"` (formato spot ccxt).
- `futures_symbol()` convierte a `"DOGE/USDT:USDT"` (formato perpetuo USDT-margined ccxt), forzando `defaultSubType="linear"` para evitar que ccxt resuelva por error al mercado coin-margined (`dapi`).

## Uso

```bash
python criptodata.py
```

100% interactivo por consola — no acepta argumentos de línea de comandos. Al ejecutar se muestra un menú.

## Estructura del paquete

```
CryptoData/
├── criptodata.py         # punto de entrada — solo llama a core.cli.main()
└── core/
    ├── config.py          # config.json, opciones de timeframe/rango del menú
    ├── exchange.py        # normalización de símbolos + instancias ccxt
    ├── utils.py           # helpers genéricos (nombre de archivo, serialización JSON)
    ├── indicators.py      # métricas de mercado, EMA/RSI/MACD/ATR, patrones de vela
    ├── merge.py            # fusión de fuentes por índice temporal + columnas de export
    ├── cli.py              # menú interactivo (main())
    ├── sources/            # descargas desde Binance
    │   ├── ohlcv.py         # OHLCV básico y OHLCV + taker volume/nº trades
    │   ├── orderbook.py     # order book L2 (snapshot)
    │   ├── ticker.py        # ticker 24h (snapshot)
    │   └── futures.py       # funding rate, open interest, long/short ratio, taker ratio
    └── exports/            # arman los CSV/JSON finales (una función por opción de menú)
        ├── basic.py         # opciones 1-4 (OHLCV básico)
        ├── quant.py         # opciones 5-6 (cuantitativo completo + multi-timeframe)
        └── atr.py           # opción 7 (ATR14 actual — no exporta archivo, solo imprime)
```

Cada módulo tiene una sola responsabilidad, así que agregar algo nuevo casi nunca implica tocar los demás:

- **¿Nueva fuente de datos?** (ej. otro endpoint de Binance, u otro exchange) → un archivo nuevo en `sources/`.
- **¿Nuevo indicador o patrón de vela?** → una función en `indicators.py`.
- **¿Nueva columna en el CSV final?** → agregarla a la lista `EXPORT_COLUMNS_*` correspondiente en `merge.py`.
- **¿Nueva opción de menú?** → una función `exportar_*` en `exports/` + una rama en `core/cli.py`.

`sources/futures.py` deduplica la paginación de los tres endpoints `fapiData*` de Binance (open interest, long/short ratio, taker ratio) en un solo helper (`_download_fapi_history`); cada función pública solo declara el endpoint y cómo mapear una fila cruda a columnas — agregar un cuarto endpoint `fapiData*` es una función de ~15 líneas, no otro bloque de paginación copiado.

## Menú interactivo

```
1. CSV últimos 30 días            (OHLCV básico)
2. CSV últimos 365 días           (OHLCV básico)
3. JSON indicadores último día    (OHLCV básico)
4. CSV personalizado por TF/rango (OHLCV básico)
─────────────────────────────────────────────────
5. CSV cuantitativo COMPLETO (todas las fuentes)
─────────────────────────────────────────────────
6. CSV MULTI-TIMEFRAME COMPLETO (5m,15m,1h,4h,1d,1w) — una carpeta con un CSV quant por timeframe
─────────────────────────────────────────────────
7. ATR14 actual (volatilidad, no exporta archivo)
─────────────────────────────────────────────────
0. Salir
```

Tras ejecutar cualquier opción (excepto `0`), el programa vuelve al menú principal en vez de terminar.

Para las opciones 1–2 solo se pide la cripto (de la lista de `config.json`). Para las opciones 4, 5 y 7 además se pide:
- **Timeframe**: `5m`, `15m`, `1h`, `4h`, `1d`.
- **Rango** (solo opciones 4 y 5): `24h`, `48h`, `7d`, `30d`, `60d`, `90d`, `180d`.

La opción 6 solo pide la cripto — el resto de timeframes y rangos son automáticos, ver sección siguiente. La opción 7 pide cripto y timeframe, pero no rango: el warmup de descarga se calcula solo (ver más abajo).

### Salidas por opción

| Opción | Función | Módulo | Archivo generado |
|---|---|---|---|
| 1 | `exportar_csv_ultimos_30_dias` | `core.exports.basic` | `output/AAAA-MM-DD_SIMBOLO_ultimos_30_dias.csv` |
| 2 | `exportar_csv_365_dias` | `core.exports.basic` | `output/AAAA-MM-DD_SIMBOLO_ultimos_365_dias.csv` |
| 3 | `exportar_json_indicadores` | `core.exports.basic` | `output/AAAA-MM-DD_SIMBOLO_indicadores.json` |
| 4 | `exportar_csv_personalizado` | `core.exports.basic` | `output/AAAA-MM-DD_SIMBOLO_TF_RANGO.csv` |
| 5 | `exportar_csv_quant_completo` | `core.exports.quant` | `output/AAAA-MM-DD_SIMBOLO_TF_RANGO_quant.csv` |
| 6 | `exportar_multi_timeframe` | `core.exports.quant` | carpeta `output/AAAA-MM-DD_SIMBOLO_MTF/` con un `_quant.csv` por timeframe |
| 7 | `calcular_atr_actual` | `core.exports.atr` | ninguno — solo imprime el resultado en consola |

### Opción 6 — Multi-timeframe automático

Descarga 6 timeframes en una sola corrida (`5m, 15m, 1h, 4h, 1d, 1w`) — el mismo set que revisar manualmente 1W→1D→4H→1H→15M→5M en TradingView. Cada timeframe se pide **nativo** a Binance (no resampleado desde 5m), con un rango por defecto pensado para que EMA200/RSI14/ATR14 tengan warmup real sin descargar filas de más:

| Timeframe | Rango por defecto | Por qué |
|---|---|---|
| 5m  | 2d   | foco en order flow/microestructura reciente |
| 15m | 7d   | contexto intradía |
| 1h  | 30d  | swing de corto plazo |
| 4h  | 90d  | EMA200 (4h) necesita ~33d de warmup |
| 1d  | 400d | EMA200 diaria necesita ~200 velas |
| 1w  | 1825d (~5 años) | EMA200 semanal necesita ~200 semanas |

**Nota:** funding/OI/L-S ratio siguen limitados a ~30 días de histórico por Binance (ver Limitaciones) independientemente del timeframe — en 1d/1w esas columnas vendrán con `NaN` para las velas más antiguas, es esperado.

Toma varios minutos: cada timeframe repite las mismas 6 descargas que una corrida individual de la opción 5 (ver `mejoras_pendientes.md` — es una optimización pendiente, no implementada todavía).

### Opción 7 — ATR14 actual

Consulta rápida de volatilidad: pide cripto y timeframe, descarga solo OHLCV (sin funding/OI/L-S/order book/ticker) y calcula el ATR14 (Wilder/RMA, `indicators.add_atr`) de la última vela cerrada. No genera ningún archivo — imprime `Close`, `ATR14` y `ATR14_%` directamente en consola.

El rango de descarga (warmup) se reutiliza de `MTF_DEFAULT_RANGE_DAYS` (la misma tabla de la opción 6) según el timeframe elegido, para que el ATR14 ya esté convergido (Wilder/RMA se estabiliza en unas ~30-50 velas) y no dependa del valor semilla inicial.

Pensada para chequear rápido el tamaño de SL/TP en `%` antes de operar, sin tener que abrir un CSV completo — ver sección 6 de `CLAUDE.md` sobre ajustar el stop/take a `ATR14_%` en vez de un número fijo.

## Fuentes de datos y columnas generadas

La opción **5** ("CSV cuantitativo completo") es la más rica: descarga y fusiona por timestamp todas las fuentes disponibles y agrega indicadores derivados.

### 1. OHLCV + taker buy/sell (spot, klines raw de Binance) — `sources/ohlcv.py`
`Open, High, Low, Close, Volume, Taker_Buy_Vol, Taker_Sell_Vol, Taker_Buy_USDT, Taker_Sell_USDT, Volume_Delta, Volume_Delta_%, Num_Trades, Avg_Trade_Size`

### 2. Métricas de mercado derivadas — `indicators.add_market_metrics`
`Rango_Dia, Variacion, Variacion_%, Precio_Medio, Precio_Tipico, Volatilidad_Diaria, Volumen_USD, Tendencia_Alcista, Cambio_Absoluto, Cambio_%`

### 3. Funding rate histórico (futuros perpetuos, cada 8h) — `sources/futures.py`
`Funding_Rate, Funding_Rate_Acum_8h, Funding_Mark_Price` (forward-fill hacia las velas de mayor resolución)

### 4. Open interest histórico (futuros) — `sources/futures.py`
`OI_Amount, OI_Value_USDT, OI_Change_%` — limitado a ~30 días de histórico por restricción de Binance.

### 5. Long/short ratio de cuentas (futuros) — `sources/futures.py`
`LS_Ratio, LS_Long_Pct, LS_Short_Pct` — un `LS_Ratio > 2` se interpreta como señal contrarian bajista (multitud excesivamente larga).

### 6. Taker buy/sell ratio de futuros (sustituto de liquidaciones) — `sources/futures.py`
`Fut_Buy_Vol, Fut_Sell_Vol, Fut_Buy_Sell_Ratio, Fut_Delta_Vol, Fut_Delta_%`

> Binance no expone liquidaciones históricas vía REST (solo WebSocket en vivo). Este bloque usa `fapiDataGetTakerlongshortRatio` como aproximación de la presión agresiva de mercado.

### 7. Indicadores y patrones técnicos — `indicators.py`

`add_all_technical_analysis()` orquesta cuatro bloques, todos calculados desde OHLC/Close — sin depender de leer un gráfico:

**EMA/RSI** (`add_technical_indicators`): `EMA20, EMA50, EMA200, RSI14`
- EMA20/50/200 vía `pandas.ewm`, misma metodología que el backtest de `CLAUDE.md`.
- RSI14 con suavizado de Wilder/RMA (no promedio simple) — coincide con el cálculo que usa TradingView por defecto.

**MACD** (`add_macd`): `MACD_Line, MACD_Signal, MACD_Hist` — MACD clásico (12,26,9).

**ATR** (`add_atr`): `True_Range, ATR14, ATR14_%` — suavizado de Wilder/RMA, para dimensionar SL/TP por volatilidad real del activo en vez de un número fijo. `ATR14_%` es comparable entre activos con precio muy distinto (BTC vs DOGE vs ZEC).

**Rolling 20** (`add_rolling_stats`): `Vol_MA20, Vol_Spike_Ratio, High_20, Low_20, New_High_20, New_Low_20` — misma ventana que usa `CLAUDE.md` para "spike de volumen >2.5x" y "nuevo mínimo/máximo de N velas".

**Patrones de vela** (`add_candlestick_patterns`): `Doji, Hammer, Shooting_Star, Bullish_Engulfing, Bearish_Engulfing, Bullish_Harami, Bearish_Harami, Morning_Star, Evening_Star` — flags booleanos calculados desde OHLC. Morning/Evening Star omiten el requisito clásico de "gap" entre velas porque cripto opera 24/7 y los gaps reales son raros; se valida solo tamaño de cuerpo + cierre más allá del punto medio de la primera vela.

### 8. Ticker 24h (spot, snapshot) — `sources/ticker.py`
`Ticker_VWAP, Ticker_Volume_24h, Ticker_Change_24h_%, Ticker_High_24h, Ticker_Low_24h, Ticker_Price_vs_VWAP_%`

### 9. Order book L2 (spot, snapshot) — `sources/orderbook.py`
`OB_Spread, OB_Spread_%, OB_Mid_Price, OB_Bid_Depth, OB_Ask_Depth, OB_Imbalance, OB_Bid_USDT_Depth, OB_Ask_USDT_Depth`

### 10. Indicadores cuantitativos derivados combinados — `indicators.add_derived_quant_metrics`
`Taker_Pressure` (presión compradora spot), `OI_Price_Diverge` (divergencia OI vs precio), `Funding_Extreme` (funding fuera de rango normal), `Fut_Spot_Delta_Diff` (divergencia futuros vs spot)

Todas las fuentes se combinan mediante `merge.merge_all_sources()` con un `left join` sobre el índice temporal del OHLCV; el funding rate (menor resolución, cada 8h) se propaga con forward-fill al resto de velas.

## Limitaciones conocidas

- **Open interest y long/short ratio**: Binance solo conserva ~30 días de histórico en esos endpoints; rangos mayores se recortan automáticamente.
- **Liquidaciones históricas**: Binance no las expone vía REST; se usa el ratio taker buy/sell de futuros como proxy de la presión agresiva de mercado.
- **Timeframes para OI/L-S/futures taker ratio**: se mapean al periodo válido más cercano soportado por los endpoints `fapiData` de Binance (ver `_BINANCE_FAPI_PERIOD_MAP` en `sources/futures.py`).
- **Sin modo no interactivo**: el menú es 100% por consola (`input()`); no hay forma de programarlo como tarea automática (cron / scheduled task) sin modificar `cli.py`.

## Estructura de archivos generados

Todos los archivos se guardan en la carpeta `output/` (junto a `criptodata.py`, se crea automáticamente si no existe), con el patrón:

```
output/AAAA-MM-DD_SIMBOLO[_TF_RANGO][_quant].csv|json
```

Donde `SIMBOLO` es el símbolo normalizado para nombre de archivo (caracteres no alfanuméricos → `_`), por ejemplo `DOGE/USDT` → `DOGE_USDT`.

La opción 6 (multi-timeframe) genera además una subcarpeta `output/AAAA-MM-DD_SIMBOLO_MTF/` con un CSV por timeframe.

## Extender el proyecto

Ver `mejoras_pendientes.md` para el backlog de mejoras conocidas (rendimiento de la opción 6, validación post-generación, vista cross-asset, etc.) — varias quedan más simples de implementar ahora que cada responsabilidad vive en su propio módulo.

**Nota:** el proyecto no tiene tests automatizados todavía (ver `mejoras_pendientes.md`, sección 4). Cualquier cambio en `indicators.py` (RSI/ATR/patrones de vela) o en la paginación de `sources/futures.py` debe verificarse a mano corriendo el programa y revisando el CSV generado.
