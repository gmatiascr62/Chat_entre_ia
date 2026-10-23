# Resultados — período de DISEÑO (2018-01-01 a 2022-12-31)

Estrategia A v0 (ver estrategia_A_v0.txt). BTC/USDT spot, velas de 4h de Binance. Capital inicial 10,000 USDT. Corrida: 2026-10-23 20:41 UTC, commit f7b907e.

**Estos son datos de diseño.** No sirven para aprobar ni rechazar la estrategia: la clasificación (sección 10) se aplica solo en validación. La validación todavía no se miró.

Verificación cruzada motor vs. reimplementación: **COINCIDEN** (detalle en diseno_verificacion.md).

## Escenarios principales

| Escenario | Rent. neta | CAGR | DD máx | CAGR/DD | Ops | Aciertos | FB | Expectativa/op | Exposición | Costos (USDT) | Top-3 / beneficio | Bootstrap ops p2,5 | Bootstrap ops p1 | Bootstrap temporal p1 (diario) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A base | 48.88% | 8.29% | -5.28% | 1.57 | 98 | 41.84% | 2.64 | 0.42% | 29.84% | 527 | 47.63% | 0.17% | 0.13% | 0.005% |
| EMA(200) sola base | 100.07% | 14.88% | -14.45% | 1.03 | 150 | 14.67% | 3.43 | 0.55% | 48.47% | 909 | 102.15% ⚠ | -0.03% | -0.07% | 0.002% |
| Comprar y mantener base | 20.25% | 3.76% | -81.42% | 0.05 | 1 | 100.00% | inf | 20.25% | 100.00% | 33 | 100.00% ⚠ | n/d | n/d | -0.124% |
| A costos x2 | 38.04% | 6.66% | -5.40% | 1.23 | 98 | 37.76% | 2.31 | 0.34% | 29.84% | 921 | 51.95% ⚠ | 0.12% | 0.08% | 0.002% |
| EMA(200) sola costos x2 | 75.63% | 11.93% | -14.26% | 0.84 | 150 | 14.67% | 2.82 | 0.45% | 48.47% | 1545 | 112.82% ⚠ | -0.07% | -0.10% | -0.002% |
| Comprar y mantener costos x2 | 19.89% | 3.70% | -81.42% | 0.05 | 1 | 100.00% | inf | 19.89% | 100.00% | 66 | 100.00% ⚠ | n/d | n/d | -0.124% |

CAGR/DD = CAGR / |drawdown máximo|. Expectativa/op = media del resultado neto de cada operación sobre el capital al entrar. Bootstrap ops = percentiles 2,5 y 1 de la expectativa por operación remuestreando bloques de 5 operaciones (10.000 repeticiones; n/d con menos de 30 operaciones). El p1 es el propuesto para decidir (ver resultados/validacion_bootstrap.md). Bootstrap temporal = percentil 1 del retorno diario medio de la equity remuestreando bloques de 20 días (solo informativo). ⚠ = alerta de concentración (> 50%).

## Resultado por año (costos base)

| Año | A base | EMA(200) sola base | Comprar y mantener base |
|---|---|---|---|
| 2018 | 1.66% | -4.24% | -73.04% |
| 2019 | 13.41% | 31.13% | 94.31% |
| 2020 | 21.05% | 48.32% | 301.98% |
| 2021 | 8.49% | 10.70% | 59.79% |
| 2022 | -1.67% | -2.95% | -64.26% |

## Sensibilidad: alineación de las velas de 4h (reconstruidas desde 1h, costos base)

Se informan todas; no se elige la mejor. Desfase 0h debería parecerse a las velas oficiales.

| Escenario | Rent. neta | CAGR | DD máx | CAGR/DD | Ops | Aciertos | FB | Expectativa/op | Exposición | Costos (USDT) | Top-3 / beneficio | Bootstrap ops p2,5 | Bootstrap ops p1 | Bootstrap temporal p1 (diario) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A desfase 0h | 44.95% | 7.71% | -5.28% | 1.46 | 97 | 42.27% | 2.54 | 0.40% | 29.19% | 516 | 50.99% ⚠ | 0.16% | 0.11% | 0.004% |
| EMA(200) sola desfase 0h | 101.63% | 15.06% | -14.45% | 1.04 | 148 | 14.86% | 3.48 | 0.56% | 48.26% | 902 | 100.85% ⚠ | -0.03% | -0.07% | 0.002% |
| A desfase 1h | 36.16% | 6.37% | -5.04% | 1.26 | 108 | 35.19% | 2.09 | 0.30% | 26.86% | 554 | 61.91% ⚠ | 0.07% | 0.04% | 0.001% |
| EMA(200) sola desfase 1h | 81.89% | 12.71% | -14.06% | 0.90 | 150 | 14.00% | 2.99 | 0.47% | 48.17% | 860 | 101.60% ⚠ | -0.06% | -0.09% | -0.002% |
| A desfase 2h | 40.14% | 6.98% | -5.22% | 1.34 | 105 | 39.05% | 2.23 | 0.33% | 28.99% | 548 | 58.87% ⚠ | 0.09% | 0.05% | 0.001% |
| EMA(200) sola desfase 2h | 86.29% | 13.25% | -14.70% | 0.90 | 147 | 14.97% | 3.42 | 0.50% | 48.35% | 803 | 97.18% ⚠ | -0.03% | -0.07% | -0.001% |
| A desfase 3h | 40.45% | 7.03% | -5.00% | 1.41 | 101 | 35.64% | 2.30 | 0.35% | 27.85% | 523 | 58.39% ⚠ | 0.11% | 0.07% | 0.002% |
| EMA(200) sola desfase 3h | 87.59% | 13.41% | -14.34% | 0.93 | 144 | 15.97% | 3.43 | 0.51% | 48.09% | 849 | 94.57% ⚠ | -0.02% | -0.05% | 0.001% |

## Sensibilidad: velas de ruptura (Estrategia A, costos base)

Solo para ver si el resultado depende de un valor puntual. El parámetro sigue fijo en 20.

| Escenario | Rent. neta | CAGR | DD máx | CAGR/DD | Ops | Aciertos | FB | Expectativa/op | Exposición | Costos (USDT) | Top-3 / beneficio | Bootstrap ops p2,5 | Bootstrap ops p1 | Bootstrap temporal p1 (diario) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A ruptura 10 | 48.83% | 8.28% | -6.52% | 1.27 | 120 | 38.33% | 2.28 | 0.34% | 33.94% | 646 | 47.14% | 0.11% | 0.07% | 0.004% |
| A ruptura 15 | 46.27% | 7.90% | -6.09% | 1.30 | 109 | 39.45% | 2.35 | 0.36% | 31.67% | 584 | 49.52% | 0.10% | 0.06% | 0.003% |
| A ruptura 20 | 48.88% | 8.29% | -5.28% | 1.57 | 98 | 41.84% | 2.64 | 0.42% | 29.84% | 527 | 47.63% | 0.17% | 0.13% | 0.005% |
| A ruptura 30 | 48.75% | 8.27% | -5.67% | 1.46 | 86 | 39.53% | 2.74 | 0.48% | 27.13% | 480 | 49.90% | 0.12% | 0.07% | 0.004% |
| A ruptura 40 | 50.67% | 8.55% | -5.06% | 1.69 | 78 | 39.74% | 3.13 | 0.54% | 25.88% | 433 | 46.13% | 0.16% | 0.10% | 0.005% |
| A ruptura 55 | 39.13% | 6.83% | -5.29% | 1.29 | 76 | 38.16% | 2.63 | 0.45% | 23.72% | 391 | 47.99% | 0.09% | 0.03% | 0.002% |
