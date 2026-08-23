# Velas Japonesas — Notas de proyecto (memoria persistente)

Este archivo resume hallazgos cuantitativos extraídos de los históricos reales del proyecto (BTC, DOGE, ZEC — velas 1h, 180 días, hasta 2026-07-22). El objetivo es que cualquier análisis futuro de estos activos se apoye en evidencia empírica de este mismo dataset, no solo en teoría clásica de price action.

Metodología: para cada "setup" se identificaron todas las velas históricas donde se cumple la condición, y se midió el retorno % del precio de cierre a +6h, +12h, +24h y +48h desde esa vela, junto con el % de casos con retorno positivo (winrate). Script reproducible: pandas, EMA20/50/200 (ewm), RSI14 (Wilder), ATR14, rolling 20 para volumen/máximos/mínimos.

**Limitación importante:** las ventanas de retorno se solapan (no son eventos independientes), la muestra cubre un solo régimen de ~6 meses, y varios setups tienen n bajo (<30). Tratar estos números como una guía direccional, no como probabilidades estadísticamente robustas. Antes de usar un patrón como señal fuerte en un informe, re-correr el backtest con datos más recientes si están disponibles.

---

## 1. Carácter de cada activo en este dataset (ene–jul 2026)

| Activo | Variación periodo | Rango horario medio | ATR14 medio | Funding medio | LS_Short_Pct medio |
|---|---|---|---|---|---|
| BTC | -26.3% (89,600→66,026) | 0.69% | 0.69% | +0.0000116 (positivo, leve) | 38.3% (mayoría larga) |
| DOGE | -41.5% (0.1248→0.0730) | 1.00% | 1.00% | +0.0000130 (positivo, leve) | 29.4% (mayoría larga) |
| ZEC | +39.5% (367.9→513.1), con pico +690 (20-may) y mínimo 184.6 (6-feb) | 1.89% | 1.89% | -0.0000353 (negativo) | 60.5% (mayoría corta) |

- BTC y DOGE estuvieron en tendencia bajista de fondo durante todo el periodo; ZEC tuvo un rally idiosincrático masivo (+274% de mínimo a máximo) seguido de una corrección fuerte que sigue en curso.
- ZEC es ~2.7x más volátil que BTC y ~1.9x más volátil que DOGE (ATR% horario). Ajustar el tamaño de stop-loss/take-profit en consecuencia — un SL "ajustado" en BTC puede ser demasiado ajustado en ZEC.
- Correlación de retornos horarios: BTC-DOGE 0.80 (alta, se mueven casi juntos), ZEC-BTC 0.52 y ZEC-DOGE 0.51 (moderada — ZEC tiene una narrativa propia y se desacopla más). No asumir que ZEC seguirá automáticamente los movimientos de BTC.
- Dato curioso: en ZEC el funding promedio es negativo y el LS_Short_Pct promedio es 60% (mayoría de cuentas cortas) a pesar de que el precio subió fuerte en el periodo — sugiere que el rally lo sostuvieron relativamente pocas cuentas grandes en largo mientras la mayoría de cuentas (probablemente retail) apostaban en corto. Es una pista de que LS_Ratio en ZEC no debe leerse de forma ingenua como "sentimiento del mercado" (ver sección 3).

---

## 2. Patrones con edge estadístico real (usar con más confianza)

**BTC**
- Funding extremo alto (>percentil 95): sesgo bajista consistente y creciente con el horizonte — 24h media -1.15%, 48h media -1.61% (winrate 40%). Señal contrarian de corto razonable en BTC.
- Cruce EMA20 sobre EMA50 (golden cross): sesgo alcista suave que crece con el horizonte, 48h +0.17% media / +0.30% mediana, winrate 57%. Cruce a la baja (death cross) es lo opuesto: 24h -0.46%, winrate 33%. El seguimiento de tendencia vía EMA20/50 funciona razonablemente en BTC.
- Nuevo mínimo de 24h con OI cayendo (liquidación de largos, no apertura de cortos nuevos): sesgo positivo en todos los horizontes (24h +0.23%, 48h +0.89%, winrate ~52-56%). Confirma que "flush" de largos apalancados en BTC tiende a preceder estabilización/recuperación, no continuación bajista.

**DOGE**
- RSI>70 cayendo por debajo de 68: señal bajista con edge real y creciente — 24h -1.16% (winrate 29%), 48h -2.05% (winrate 32%). Es el patrón con mayor edge encontrado en todo el dataset. Sobrecompra en DOGE sí tiende a corregir.
- Funding extremo bajo (<percentil 5): señal alcista contrarian fuerte — 24h +1.24% (winrate 60%), 48h +1.13% (winrate 68%). Cuando el funding de DOGE cae a niveles extremos negativos, el rebote posterior es el patrón más confiable de todo el estudio.

**ZEC**
- Spike de volumen (>2.5x promedio 20 velas) con vela alcista: momentum con continuación fuerte — 24h +1.86%, 48h +2.14% (winrate ~54-55%). En ZEC, los movimientos alcistas con volumen fuerte tienden a seguir, no a revertir.
- Cruce EMA20 sobre EMA50: 48h +2.96% media / +2.00% mediana, winrate 57%. Seguimiento de tendencia también funciona en ZEC, con mayor magnitud que en BTC (coherente con su mayor volatilidad).
- Pullback a EMA20 en tendencia bajista (precio < EMA200): a 48h, media +2.72% / mediana +1.04%, winrate 54% — en la fase correctiva actual, los rebotes hacia la EMA20 desde abajo han tendido a extenderse positivamente más de lo esperado.

---

## 3. Patrones SIN edge, o que funcionan al revés de lo esperado (cuidado)

Esto es lo más valioso del ejercicio: varios patrones "de manual" no se cumplieron en este dataset, o se comportaron de forma contraria a la teoría clásica. Marcar como advertencia en análisis futuros.

- **ZEC — LS_Short_Pct alto NO es contrarian, es confirmatorio.** Cuando LS_Short_Pct > 65% (mayoría de cuentas en corto), el precio de ZEC siguió cayendo con edge fuerte: 24h media -2.50% (winrate 27%), 48h -1.72% (winrate 34%). Es decir, en ZEC el consenso corto de la mayoría de cuentas ha tendido a tener razón, no a ser una trampa para short squeeze. **Corrección respecto al análisis anterior de ZEC (22-jul):** ahí se interpretó el LS_Short_Pct de 65% como "señal contrarian alcista débil". La evidencia de este backtest dice lo contrario — debería haberse leído como confirmación bajista. Tenerlo en cuenta la próxima vez.
- **ZEC — Hammer cerca de mínimo de 20 velas falla.** En vez de rebote, tiende a continuar la caída: 24h -1.24% (winrate 43%), 48h -0.95% (winrate 39%). "Comprar el hammer" en ZEC durante este periodo fue, en promedio, comprar antes de más caída.
- **ZEC — Shooting Star cerca de máximo de 20 velas también falla (al revés).** En lugar de reversión bajista, tendió a continuar subiendo: 24h +2.43% (winrate 61%), 48h +4.15% (winrate 63%). Consistente con que gran parte del periodo ZEC estuvo en tendencia alcista fuerte donde las señales de reversión bajista clásicas fueron mayormente ruido.
- **DOGE — Cruce EMA20 sobre EMA50 (golden cross) es señal tardía/bajista, no alcista.** 12h media -0.67% (winrate 31%), consistente en todos los horizontes negativo. En DOGE, para cuando el cruce se confirma, el movimiento ya se agotó — mejor tratarlo como señal de toma de ganancias que de entrada.
- **DOGE — Envolvente alcista (Bullish Engulfing) tiene edge negativo.** 24h -0.42% (winrate 43%), 48h -0.83% (winrate 43%). No usar como gatillo de entrada largo en DOGE sin confirmación adicional.
- **BTC/general — Engulfing (alcista o bajista) no mostró edge significativo en ningún horizonte** (retornos cercanos a 0%, winrate ~50%). Es el patrón de velas individual con menos utilidad predictiva de los testeados. Útil como contexto visual, no como señal aislada.
- **RSI<30 recuperando >32 (oversold bounce clásico) no tiene edge claro en ninguno de los 3 activos** — winrates entre 45-58% sin consistencia direccional a 24-48h. No asumir rebote automático solo por RSI bajo; combinar con volumen o estructura.

---

## 4. Guía práctica para análisis futuros

1. Antes de calificar un patrón de velas (hammer, shooting star, engulfing, doji) como señal de "Fiabilidad Alta", contrastarlo contra la sección 2/3 de este documento para ese activo específico. La fiabilidad de un patrón varía mucho por activo — lo que funciona en BTC no funciona igual en ZEC.
2. En ZEC, el LS_Ratio/LS_Short_Pct debe tratarse como señal de tendencia (confirmatoria), no como contrarian. En BTC y DOGE no se encontró edge claro en LS_Short_Pct — no usarlo como señal principal ahí.
3. El funding extremo sí tiene valor contrarian en BTC (extremo alto → bajista) y en DOGE (extremo bajo → alcista, la señal más fuerte del estudio), pero en ZEC el funding extremo bajo mostró sesgo bajista adicional (no rebote) — revisar el signo antes de aplicar la misma lógica a los tres activos por igual.
4. El seguimiento de tendencia vía cruces EMA20/50 funciona en BTC y ZEC pero no en DOGE (ahí llega tarde). Contexto de EMA200 (tendencia macro) sigue siendo válido como filtro en los tres.
5. Los "flush" de posiciones largas (nuevo mínimo + caída de OI, es decir liquidación, no apertura de cortos nuevos) tendieron a preceder estabilización/rebote en BTC. Vale la pena replicar este chequeo específico para ZEC con más datos cuando se acumule más historial post-corrección.
6. Ajustar siempre el tamaño de SL/TP a la volatilidad propia del activo (ATR14%): BTC ~0.7%, DOGE ~1.0%, ZEC ~1.9% por vela horaria. Un SL que tiene sentido en BTC puede saltar por ruido normal en ZEC.
7. Recordar que BTC y DOGE estuvieron en tendencia bajista de fondo y ZEC en una macro-tendencia alcista corrigiendo — la lectura de "confluencia con EMA200" debe ir siempre acompañada del contexto de tendencia dominante del activo, no solo del patrón de velas puntual.
8. Cuando se sumen más días de histórico (los CSV se actualizan), re-ejecutar este backtest — los tamaños de muestra actuales (n=15 a n=1000 según el setup) son limitados y las conclusiones pueden cambiar, especialmente para ZEC que solo tiene datos de un ciclo de rally + corrección.

---

## 5. Glosario rápido de columnas usadas (de los *_quant.csv)

- `Funding_Rate`: tasa de financiación del perpetuo por intervalo (positivo = largos pagan a cortos).
- `OI_Value_USDT` / `OI_Change_%`: interés abierto en USD y su variación — subir con el precio = convicción nueva; bajar con el precio en caída = liquidación/cierre de largos, no necesariamente presión vendedora nueva.
- `LS_Ratio`, `LS_Long_Pct`, `LS_Short_Pct`: proporción de cuentas (no de tamaño de posición) en largo vs. corto — ver advertencia sección 3 sobre su lectura contrarian.
- `Taker_Pressure`, `OB_Imbalance`: presión compradora/vendedora de mercado y desequilibrio del libro de órdenes en tiempo real de esa vela.
- `Ticker_Price_vs_VWAP_%`: desviación del precio respecto al VWAP de 24h del ticker.

Última actualización de este archivo: 2026-07-22, con datos hasta esa fecha. Volver a correr el backtest si se agregan CSV más recientes.
