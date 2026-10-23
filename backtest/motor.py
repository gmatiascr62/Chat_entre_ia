"""Indicadores, señales y simulación de la Estrategia A v0 y sus referencias.

Ver estrategia_A_v0.txt, secciones 3 a 8. Todas las señales usan solo velas cerradas hasta t;
las órdenes se ejecutan en la vela t+1.
"""
from dataclasses import dataclass, field, replace

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class Params:
    ruptura: int = 20
    salida: int = 10
    ema: int = 200
    atr: int = 14
    k_atr: float = 2.0
    riesgo: float = 0.005
    comision: float = 0.001
    desliz: float = 0.0005
    ventana_no_operar: int = 21
    capital: float = 10_000.0

    def costos_dobles(self) -> "Params":
        return replace(self, comision=self.comision * 2, desliz=self.desliz * 2)


@dataclass
class Operacion:
    senal: pd.Timestamp       # vela cuyo cierre generó la entrada
    entrada: pd.Timestamp     # vela en cuya apertura se compró
    precio_entrada: float     # con deslizamiento
    stop: float
    cantidad: float
    capital_inicial: float    # efectivo antes de entrar
    salida: pd.Timestamp = None
    precio_salida: float = np.nan  # con deslizamiento
    motivo: str = ""
    pnl: float = np.nan       # neto de comisiones y deslizamiento
    costos: float = 0.0       # comisiones + deslizamiento pagados

    @property
    def retorno(self) -> float:
        return self.pnl / self.capital_inicial


@dataclass
class Simulacion:
    operaciones: list
    fechas: pd.DatetimeIndex
    equity: np.ndarray
    en_posicion: np.ndarray
    params: Params
    costos_totales: float = 0.0
    extra: dict = field(default_factory=dict)


def ema(x: np.ndarray, n: int) -> np.ndarray:
    out = np.full(len(x), np.nan)
    if len(x) < n:
        return out
    a = 2.0 / (n + 1)
    out[n - 1] = x[:n].mean()
    for i in range(n, len(x)):
        out[i] = a * x[i] + (1 - a) * out[i - 1]
    return out


def atr_wilder(h: np.ndarray, l: np.ndarray, c: np.ndarray, n: int) -> np.ndarray:
    tr = np.empty(len(c))
    tr[0] = h[0] - l[0]
    pc = c[:-1]
    tr[1:] = np.maximum(h[1:] - l[1:], np.maximum(np.abs(h[1:] - pc), np.abs(l[1:] - pc)))
    out = np.full(len(c), np.nan)
    if len(c) < n:
        return out
    out[n - 1] = tr[:n].mean()
    for i in range(n, len(c)):
        out[i] = (out[i - 1] * (n - 1) + tr[i]) / n
    return out


def indicadores(df: pd.DataFrame, p: Params) -> dict:
    h, l, c = (df[k].to_numpy(float) for k in ("high", "low", "close"))
    return {
        "ema": ema(c, p.ema),
        "atr": atr_wilder(h, l, c, p.atr),
        # máximo/mínimo de las velas ANTERIORES: shift(1) excluye la vela actual
        "max_ruptura": df["high"].rolling(p.ruptura).max().shift(1).to_numpy(),
        "min_salida": df["low"].rolling(p.salida).min().shift(1).to_numpy(),
        "bloqueo": df["anomala"].astype(float).rolling(p.ventana_no_operar, min_periods=1).max()
                     .to_numpy() > 0,
    }


def senales(df: pd.DataFrame, ind: dict, estrategia: str) -> tuple[np.ndarray, np.ndarray]:
    c = df["close"].to_numpy(float)
    with np.errstate(invalid="ignore"):
        if estrategia == "A":
            entrada = (c > ind["max_ruptura"]) & (c > ind["ema"])
            salida = c < ind["min_salida"]
        elif estrategia == "EMA":
            entrada = c > ind["ema"]
            salida = c < ind["ema"]
        else:
            raise ValueError(estrategia)
    completos = ~np.isnan(ind["ema"]) & ~np.isnan(ind["atr"]) & ~np.isnan(ind["max_ruptura"])
    entrada = entrada & completos & ~ind["bloqueo"]
    return entrada, salida


def simular(df: pd.DataFrame, estrategia: str, p: Params, inicio: pd.Timestamp,
            fin: pd.Timestamp) -> Simulacion:
    """Simula sobre las velas con fecha en [inicio, fin]. Las velas anteriores a inicio solo calientan indicadores;
    las posteriores a fin no se usan (se recortan antes de calcular nada)."""
    df = df.loc[df["fecha"] <= fin].reset_index(drop=True)
    ind = indicadores(df, p)
    entrada, salida = senales(df, ind, estrategia)
    i0 = int((df["fecha"] < inicio).sum())
    o, h, l, c = (df[k].to_numpy(float) for k in ("open", "high", "low", "close"))
    fechas = df["fecha"]
    n = len(df)
    f, s = p.comision, p.desliz

    cash = p.capital
    qty = 0.0
    op = None
    ops = []
    pend_entrada = pend_salida = False
    atr_senal = np.nan
    costos = 0.0
    equity = np.empty(n - i0)
    en_pos = np.zeros(n - i0, dtype=bool)

    def cerrar(i, precio_bruto, motivo):
        nonlocal cash, qty, op, costos
        fill = precio_bruto * (1 - s)
        com = qty * fill * f
        cash += qty * fill - com
        op.costos += com + qty * (precio_bruto - fill)
        costos += com + qty * (precio_bruto - fill)
        op.salida, op.precio_salida, op.motivo = fechas.iloc[i], fill, motivo
        op.pnl = cash - op.capital_inicial
        ops.append(op)
        qty, op = 0.0, None

    for i in range(i0, n):
        # 1) órdenes pendientes, a la apertura
        if pend_salida and qty > 0:
            cerrar(i, o[i], "canal" if estrategia == "A" else "cruce_ema")
        if pend_entrada and qty == 0:
            fill = o[i] * (1 + s)
            stop = o[i] - p.k_atr * atr_senal
            stop_fill = stop * (1 - s)
            perdida_unidad = (fill - stop_fill) + f * fill + f * stop_fill
            if stop > 0 and perdida_unidad > 0:
                cantidad = min(cash * p.riesgo / perdida_unidad, cash / (fill * (1 + f)))
                com = cantidad * fill * f
                op = Operacion(senal=fechas.iloc[i - 1], entrada=fechas.iloc[i], precio_entrada=fill, stop=stop,
                               cantidad=cantidad, capital_inicial=cash)
                op.costos = com + cantidad * (fill - o[i])
                costos += op.costos
                cash -= cantidad * fill + com
                qty = cantidad
        pend_entrada = pend_salida = False

        # 2) stop intravela (también en la vela de entrada)
        if qty > 0:
            if o[i] <= op.stop:
                cerrar(i, o[i], "stop_hueco")
            elif l[i] <= op.stop:
                cerrar(i, op.stop, "stop")

        # 3) señales al cierre, para ejecutar en la vela siguiente
        if i < n - 1:
            if qty > 0 and salida[i]:
                pend_salida = True
            elif qty == 0 and entrada[i]:
                pend_entrada = True
                atr_senal = ind["atr"][i]

        if i == n - 1 and qty > 0:
            cerrar(i, c[i], "fin_periodo")
        en_pos[i - i0] = qty > 0 or (ops and ops[-1].salida == fechas.iloc[i])
        equity[i - i0] = cash + qty * c[i]

    return Simulacion(ops, pd.DatetimeIndex(fechas.iloc[i0:]), equity, en_pos, p, costos)


def comprar_y_mantener(df: pd.DataFrame, p: Params, inicio: pd.Timestamp, fin: pd.Timestamp) -> Simulacion:
    df = df.loc[(df["fecha"] >= inicio) & (df["fecha"] <= fin)].reset_index(drop=True)
    o0 = df["open"].iloc[0]
    fill = o0 * (1 + p.desliz)
    qty = p.capital / (fill * (1 + p.comision))
    c = df["close"].to_numpy(float)
    equity = qty * c
    salida = c[-1] * (1 - p.desliz)
    equity[-1] = qty * salida * (1 - p.comision)
    costos = qty * fill * p.comision + qty * (fill - o0) + qty * salida * p.comision + qty * (c[-1] - salida)
    op = Operacion(senal=df["fecha"].iloc[0], entrada=df["fecha"].iloc[0], precio_entrada=fill, stop=0.0,
                   cantidad=qty, capital_inicial=p.capital, salida=df["fecha"].iloc[-1], precio_salida=salida,
                   motivo="fin_periodo", pnl=equity[-1] - p.capital, costos=costos)
    return Simulacion([op], pd.DatetimeIndex(df["fecha"]), equity, np.ones(len(df), dtype=bool), p, costos)
