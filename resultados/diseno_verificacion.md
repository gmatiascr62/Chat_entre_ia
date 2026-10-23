# Verificación cruzada — período de diseño

Motor vs. reimplementación independiente (backtest/verificacion.py), costos base, todas las operaciones.

COINCIDEN
Operaciones motor: 98 | reimplementación: 98


Primeras 5 operaciones (para revisión manual contra datos/BTCUSDT-4h.csv):

- Señal 2018-01-02 16:00:00+00:00: cierre=14732.75 > máx 20 previos=14050.11; entrada 2018-01-02 20:00:00+00:00 apertura=14710.02 (con desliz. 14717.3750); stop=13170.7610; salida 2018-01-08 12:00:00+00:00 por canal a 15406.2930; PnL=20.83 USDT
- Señal 2018-02-17 00:00:00+00:00: cierre=10459.04 > máx 20 previos=10323.37; entrada 2018-02-17 04:00:00+00:00 apertura=10459.04 (con desliz. 10464.2695); stop=9764.9025; salida 2018-02-21 16:00:00+00:00 por canal a 10537.3687; PnL=3.60 USDT
- Señal 2018-02-27 04:00:00+00:00: cierre=10600.0 > máx 20 previos=10496.97; entrada 2018-02-27 08:00:00+00:00 apertura=10600.0 (con desliz. 10605.3000); stop=9876.3972; salida 2018-03-06 12:00:00+00:00 por canal a 10930.5320; PnL=20.18 USDT
- Señal 2018-04-13 04:00:00+00:00: cierre=8093.01 > máx 20 previos=8012.23; entrada 2018-04-13 08:00:00+00:00 apertura=8100.0 (con desliz. 8104.0500); stop=7621.6754; salida 2018-05-01 04:00:00+00:00 por canal a 8934.0307; PnL=81.35 USDT
- Señal 2018-05-03 12:00:00+00:00: cierre=9442.28 > máx 20 previos=9369.21; entrada 2018-05-03 16:00:00+00:00 apertura=9442.0 (con desliz. 9446.7210); stop=9108.8290; salida 2018-05-06 12:00:00+00:00 por canal a 9532.2115; PnL=9.33 USDT
