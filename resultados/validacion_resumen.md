# Resultados — VALIDACIÓN ÚNICA (2023-01-01 a 2024-12-31)

Estrategia A v0, motor congelado en el commit f7b907e (hashes comprobados; ver logs/validacion_errores.log). BTC/USDT spot, velas oficiales de 4h de Binance. Capital inicial 10,000 USDT, sin posición heredada; los indicadores usan la historia desde 2017-08. Corrida: 2026-10-23 20:51 UTC, commit del repo ee9311f. La reserva 2025+ no se descargó.

## Clasificación (sección 10): **INCONCLUSA**

- percentil 1 del bootstrap por bloques de operaciones ≤ 0
- no supera a EMA(200) sola en rentabilidad/drawdown

| Criterio | Valor | ¿Cumple? |
|---|---|---|
| Operaciones ≥ 30 | 53 | sí |
| Expectativa > 0 (costos base) | 0.5231% | sí |
| FB > 1,2 (costos base) | 2.82 | sí |
| Expectativa > 0 (costos x2) | 0.3914% | sí |
| FB > 1,2 (costos x2) | 2.35 | sí |
| Bootstrap ops p1 > 0 | -0.0547% | no |
| CAGR/DD de A > CAGR/DD de EMA sola (costos base) | 2.37 vs 2.42 | no |

Verificación cruzada motor vs. reimplementación: **COINCIDEN**.

No es una recomendación de inversión ni una afirmación de rentabilidad futura. CANDIDATA significaría solo pasar a paper trading.

## Escenarios

| Escenario | Rent. neta | CAGR | DD máx | CAGR/DD | Ops | Aciertos | FB | Expectativa/op | Exposición | Costos (USDT) | Top-3 / beneficio | Bootstrap ops p2,5 | Bootstrap ops p1 | Bootstrap temporal p1 (diario) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A base | 30.29% | 14.14% | -5.95% | 2.37 | 53 | 33.96% | 2.82 | 0.52% | 35.16% | 371 | 84.99% ⚠ | 0.01% | -0.05% | -0.002% |
| EMA(200) sola base | 39.04% | 17.91% | -7.41% | 2.42 | 65 | 18.46% | 3.30 | 0.55% | 65.94% | 422 | 102.94% ⚠ | 0.01% | -0.06% | -0.005% |
| Comprar y mantener base | 464.00% | 137.39% | -30.01% | 4.58 | 1 | 100.00% | inf | 464.00% | 100.00% | 100 | 100.00% ⚠ | n/d | n/d | 0.054% |
| A costos x2 | 21.97% | 10.43% | -6.01% | 1.74 | 53 | 33.96% | 2.35 | 0.39% | 35.16% | 634 | 95.50% ⚠ | -0.04% | -0.10% | -0.006% |
| EMA(200) sola costos x2 | 28.84% | 13.50% | -7.78% | 1.73 | 65 | 18.46% | 2.64 | 0.42% | 65.94% | 726 | 114.51% ⚠ | -0.04% | -0.10% | -0.010% |
| Comprar y mantener costos x2 | 462.31% | 137.04% | -30.01% | 4.57 | 1 | 100.00% | inf | 462.31% | 100.00% | 199 | 100.00% ⚠ | n/d | n/d | 0.053% |

Uso del capital por operación de A: mediana 18.2%, máximo 39.3% (el resto queda en efectivo al 0%).

Bootstrap: bloques circulares de 5 operaciones, 10.000 repeticiones, semilla 12345; el percentil 1 se apoya en ~100 remuestreos de la cola y es una aproximación (ver resultados/validacion_bootstrap.md). Bootstrap temporal: bloques de 20 días de retornos diarios, solo informativo.

Valores exactos (A, costos base): p2,5 = 0.00014185063163033392, p1 = -0.0005471282386087421, temporal p1 = -2.1548191104679832e-05.

## Resultado por año (costos base)

| Año | A base | EMA(200) sola base | Comprar y mantener base |
|---|---|---|---|
| 2023 | 22.75% | 26.33% | 155.23% |
| 2024 | 6.14% | 10.06% | 120.97% |
