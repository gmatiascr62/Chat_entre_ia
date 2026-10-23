"""Reimplementación independiente y deliberadamente ingenua de la Estrategia A v0.

No importa nada de motor.py: recalcula indicadores y operaciones con bucles simples en Python puro, para
contrastar contra el motor (estrategia_A_v0.txt, sección 11). Si ambos discrepan, hay un error en alguno.
"""


def _ema(c, n):
    out = [None] * len(c)
    if len(c) < n:
        return out
    out[n - 1] = sum(c[:n]) / n
    a = 2 / (n + 1)
    for i in range(n, len(c)):
        out[i] = a * c[i] + (1 - a) * out[i - 1]
    return out


def _atr(h, l, c, n):
    tr = [h[0] - l[0]] + [max(h[i] - l[i], abs(h[i] - c[i - 1]), abs(l[i] - c[i - 1])) for i in range(1, len(c))]
    out = [None] * len(c)
    if len(c) < n:
        return out
    out[n - 1] = sum(tr[:n]) / n
    for i in range(n, len(c)):
        out[i] = (out[i - 1] * (n - 1) + tr[i]) / n
    return out


def operaciones_ingenuas(velas, i0, comision=0.001, desliz=0.0005, capital=10_000.0, max_ops=None):
    """velas: lista de dicts con open/high/low/close/anomala (ya recortada al fin del período).
    i0: índice de la primera vela operable. Devuelve lista de dicts con índices y precios de cada operación."""
    o = [v["open"] for v in velas]
    h = [v["high"] for v in velas]
    l = [v["low"] for v in velas]
    c = [v["close"] for v in velas]
    an = [v["anomala"] for v in velas]
    e = _ema(c, 200)
    a = _atr(h, l, c, 14)
    n = len(velas)
    ops = []
    cash = capital
    pos = None

    def cerrar(i, precio, motivo):
        nonlocal cash, pos
        px = precio * (1 - desliz)
        cash += pos["cantidad"] * px * (1 - comision)
        pos.update(salida=i, precio_salida=px, motivo=motivo, pnl=cash - pos["capital_inicial"])
        ops.append(pos)
        pos = None

    i = i0
    while i < n and not (max_ops and len(ops) >= max_ops):
        if pos is None:
            # ¿el cierre de la vela i da señal de entrada?
            if 20 <= i < n - 1 and e[i] is not None and a[i] is not None and not any(an[i - 20:i + 1]) \
                    and c[i] > max(h[i - 20:i]) and c[i] > e[i]:
                j = i + 1
                fill = o[j] * (1 + desliz)
                stop = o[j] - 2 * a[i]
                sf = stop * (1 - desliz)
                q = min(cash * 0.005 / ((fill - sf) + comision * fill + comision * sf),
                        cash / (fill * (1 + comision)))
                pos = {"senal": i, "entrada": j, "precio_entrada": fill, "stop": stop, "cantidad": q,
                       "capital_inicial": cash}
                cash -= q * fill * (1 + comision)
                i = j  # la vela de entrada se procesa con posición (stop intravela incluido)
            else:
                i += 1
            continue
        if o[i] <= pos["stop"]:
            cerrar(i, o[i], "stop_hueco")   # sin avanzar: el cierre de i puede dar nueva entrada
        elif l[i] <= pos["stop"]:
            cerrar(i, pos["stop"], "stop")
        elif i == n - 1:
            cerrar(i, c[i], "fin_periodo")
        elif c[i] < min(l[i - 10:i]):
            cerrar(i + 1, o[i + 1], "canal")
            i += 1                          # vendido a la apertura de i+1; su cierre puede dar nueva entrada
        else:
            i += 1
    return ops
