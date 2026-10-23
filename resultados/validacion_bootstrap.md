# Validación del bootstrap por bloques de operaciones (datos sintéticos)

1000 simulaciones por fila, 2000 repeticiones de bootstrap, bloques de 5 operaciones. Media verdadera = 0. Ideal: cobertura 95% y falsos positivos (p2,5 > 0) 2,5%.

| Operaciones | Autocorrelación | Distribución | Cobertura del 95% | Falsos positivos (p2,5 > 0) |
|---|---|---|---|---|
| 30 | 0.0 | normal | 88.3% | 5.1% |
| 30 | 0.0 | t(3) | 87.7% | 5.9% |
| 30 | 0.3 | normal | 84.8% | 6.6% |
| 30 | 0.3 | t(3) | 85.2% | 7.1% |
| 30 | 0.6 | normal | 76.6% | 11.6% |
| 30 | 0.6 | t(3) | 77.6% | 11.0% |
| 60 | 0.0 | normal | 89.7% | 4.5% |
| 60 | 0.0 | t(3) | 91.9% | 4.5% |
| 60 | 0.3 | normal | 86.6% | 6.4% |
| 60 | 0.3 | t(3) | 89.3% | 5.9% |
| 60 | 0.6 | normal | 80.0% | 10.0% |
| 60 | 0.6 | t(3) | 82.8% | 9.0% |
| 100 | 0.0 | normal | 91.8% | 3.8% |
| 100 | 0.0 | t(3) | 93.3% | 3.5% |
| 100 | 0.3 | normal | 89.7% | 4.5% |
| 100 | 0.3 | t(3) | 91.3% | 4.6% |
| 100 | 0.6 | normal | 85.3% | 6.9% |
| 100 | 0.6 | t(3) | 84.3% | 7.7% |
Lectura: el bootstrap por bloques de operaciones es demasiado estrecho con muestras chicas y con autocorrelación
alta. Con el percentil 2,5, la tasa de falsos positivos va del 3,5% al 11,6% según el caso, contra el 2,5% nominal.

Calibración para el caso esperado en validación (~40 operaciones, colas pesadas t(3); 1000 simulaciones):

| Autocorrelación | Falsos positivos p2,5 | p1 | p0,5 |
|---|---|---|---|
| 0,0 | 5,1% | 2,7% | 1,7% |
| 0,2 | 5,5% | 3,5% | 2,5% |
| 0,3 | 7,5% | 5,8% | 4,5% |

Autocorrelación medida en las 98 operaciones de diseño de A: lag 1 = −0,144, lag 2 = −0,107, lag 3 = −0,028
(no significativas: ±0,20 con n = 98). Propuesta: decidir con el percentil 1.
