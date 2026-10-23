"""Pruebas del motor con datos SINTÉTICOS. Sirven solo para verificar el código; no son resultados de mercado."""
import numpy as np
import pandas as pd
import pytest

from backtest import datos, metricas
from backtest.motor import Params, atr_wilder, comprar_y_mantener, ema, indicadores, senales, simular
from backtest.verificacion import operaciones_ingenuas

P = Params()
T0 = pd.Timestamp("2018-01-01", tz="UTC")


def serie(n=3000, semilla=1, vol=0.02, deriva=0.0004):
    rng = np.random.default_rng(semilla)
    c = 10_000 * np.exp(np.cumsum(rng.normal(deriva, vol, n)))
    o = np.concatenate([[c[0]], c[:-1]]) * np.exp(rng.normal(0, vol / 4, n))  # huecos de apertura
    h = np.maximum(o, c) * np.exp(np.abs(rng.normal(0, vol / 2, n)))
    l = np.minimum(o, c) * np.exp(-np.abs(rng.normal(0, vol / 2, n)))
    return marco(o, h, l, c)


def marco(o, h, l, c, vol=None):
    n = len(c)
    fecha = pd.date_range(T0 - pd.Timedelta(hours=4 * 250), periods=n, freq="4h", tz="UTC")
    return pd.DataFrame({"open": o, "high": h, "low": l, "close": c,
                         "volume": np.ones(n) if vol is None else vol, "anomala": np.zeros(n, dtype=bool),
                         "fecha": fecha})


def fin(df):
    return df["fecha"].iloc[-1]


# ---------- indicadores ----------

def test_ema_a_mano():
    x = np.array([1.0, 2, 3, 4, 5])
    e = ema(x, 3)
    assert np.isnan(e[:2]).all()
    assert e[2] == pytest.approx(2.0)          # media de 1,2,3
    assert e[3] == pytest.approx(0.5 * 4 + 0.5 * 2.0)
    assert e[4] == pytest.approx(0.5 * 5 + 0.5 * 3.0)


def test_atr_wilder_a_mano():
    h = np.array([10.0, 12, 11, 13])
    l = np.array([8.0, 9, 9, 10])
    c = np.array([9.0, 11, 10, 12])
    a = atr_wilder(h, l, c, 2)
    # TR = [2, max(3,3,0)=3, max(2,0,2)=2, max(3,3,0)=3]
    assert a[1] == pytest.approx(2.5)
    assert a[2] == pytest.approx((2.5 + 2) / 2)
    assert a[3] == pytest.approx((2.25 + 3) / 2)


def test_canal_excluye_vela_actual():
    df = serie(300)
    ind = indicadores(df, P)
    i = 250
    assert ind["max_ruptura"][i] == df["high"].iloc[i - 20:i].max()
    assert ind["min_salida"][i] == df["low"].iloc[i - 10:i].min()


# ---------- ejecución, stop, costos y sizing (casos construidos a mano) ----------

def caso_base(n_previas=260):
    """Serie plana con ruido mínimo y luego una ruptura en la vela 'k'. Devuelve df y k."""
    o = np.full(n_previas, 100.0)
    c = np.full(n_previas, 100.0)
    h = np.full(n_previas, 101.0)
    l = np.full(n_previas, 99.0)
    return o, h, l, c


def armar(extra):
    o, h, l, c = caso_base()
    for (oo, hh, ll, cc) in extra:
        o = np.append(o, oo); h = np.append(h, hh); l = np.append(l, ll); c = np.append(c, cc)
    return marco(o, h, l, c)


def test_entrada_en_apertura_siguiente_y_stop_con_hueco():
    # vela k cierra en 105 > máximo previo 101 y > EMA (~100): señal. Entrada en apertura de k+1 = 106.
    # ATR en k: TR previos = 2; TR de k = max(110-100, |110-100|, |100-100|) = 10 -> ATR = (2*13+10)/14
    df = armar([(100, 110, 100, 105), (106, 107, 104, 106), (90, 95, 85, 92), (92, 93, 91, 92)])
    sim = simular(df, "A", P, T0, fin(df))
    assert len(sim.operaciones) == 1
    op = sim.operaciones[0]
    k = 260
    atr_k = (2 * 13 + 10) / 14
    assert op.entrada == df["fecha"].iloc[k + 1]
    assert op.precio_entrada == pytest.approx(106 * 1.0005)
    assert op.stop == pytest.approx(106 - 2 * atr_k)
    # vela k+2 abre en 90, por debajo del stop: sale a la apertura con deslizamiento, no al stop
    assert op.motivo == "stop_hueco"
    assert op.precio_salida == pytest.approx(90 * (1 - 0.0005))


def test_stop_intravela_y_sizing_con_costos():
    df = armar([(100, 110, 100, 105), (106, 107, 104, 106), (105, 105.5, 90, 95), (95, 96, 94, 95)])
    sim = simular(df, "A", P, T0, fin(df))
    op = sim.operaciones[0]
    assert op.motivo == "stop"
    assert op.precio_salida == pytest.approx(op.stop * (1 - 0.0005))
    # al saltar el stop exacto, la pérdida (con comisiones y deslizamiento) es exactamente el 0,5% del capital
    assert op.pnl == pytest.approx(-0.005 * P.capital, rel=1e-9)
    # costos registrados = comisiones + deslizamiento de ambos lados
    q = op.cantidad
    esperado = q * op.precio_entrada * 0.001 + q * 106 * 0.0005 + q * op.precio_salida * 0.001 \
        + q * (op.stop - op.precio_salida)
    assert op.costos == pytest.approx(esperado)


def test_salida_por_canal_en_apertura_siguiente():
    # tras entrar, el precio sube y luego cierra por debajo del mínimo de las 10 velas previas sin tocar el stop
    subida = [(100, 110, 100, 105)] + [(106 + i, 108 + i, 105 + i, 107 + i) for i in range(12)]
    caida = [(118, 118.5, 106, 106.5), (106.8, 107, 105, 106)]  # cierre 106,5 < mínimo previo 107
    df = armar(subida + caida)
    sim = simular(df, "A", P, T0, fin(df))
    op = sim.operaciones[0]
    k_caida = 260 + len(subida)
    assert op.motivo == "canal"
    assert op.salida == df["fecha"].iloc[k_caida + 1]
    assert op.precio_salida == pytest.approx(106.8 * (1 - 0.0005))


def test_tope_de_capital_sin_apalancamiento():
    # ATR minúsculo -> el sizing por riesgo pediría más de lo disponible; debe topearse al efectivo
    n = 260
    o = np.full(n, 100.0); c = np.full(n, 100.0); h = np.full(n, 100.01); l = np.full(n, 99.99)
    o = np.append(o, [100, 100.2, 100.3]); h = np.append(h, [100.2, 100.3, 100.4])
    l = np.append(l, [100, 100.1, 100.2]); c = np.append(c, [100.15, 100.25, 100.35])
    df = marco(o, h, l, c)
    sim = simular(df, "A", P, T0, fin(df))
    op = sim.operaciones[0]
    assert op.cantidad * op.precio_entrada * 1.001 == pytest.approx(P.capital)


def test_bloqueo_por_volumen_cero():
    df = armar([(100, 110, 100, 105), (106, 107, 104, 106), (106, 107, 105, 106)])
    df = datos.limpiar(df.assign(open_time=(df["fecha"].astype("int64") // 10**6),
                                 volume=np.r_[np.ones(250), 0, np.ones(len(df) - 251)]).drop(columns="anomala"),
                       "4h", "test")
    sim = simular(df, "A", P, T0, fin(df))
    assert sim.operaciones == []


def test_costos_dobles_empeoran():
    df = serie()
    a = simular(df, "A", P, T0, fin(df))
    b = simular(df, "A", P.costos_dobles(), T0, fin(df))
    assert len(a.operaciones) > 10
    assert b.costos_totales > a.costos_totales
    assert b.equity[-1] < a.equity[-1]


# ---------- anti look-ahead ----------

@pytest.mark.parametrize("corte", [500, 1200, 2100])
@pytest.mark.parametrize("estrategia", ["A", "EMA"])
def test_sin_look_ahead(corte, estrategia):
    df = serie()
    alterado = df.copy()
    rng = np.random.default_rng(99)
    futuro = alterado.index > corte
    factor = np.exp(np.cumsum(rng.normal(0, 0.05, futuro.sum())))
    for k in ("open", "high", "low", "close"):
        alterado.loc[futuro, k] = alterado.loc[futuro, k] * factor
    ind1, ind2 = indicadores(df, P), indicadores(alterado, P)
    for k in ind1:
        np.testing.assert_array_equal(ind1[k][:corte + 1], ind2[k][:corte + 1])
    s1, s2 = senales(df, ind1, estrategia), senales(alterado, ind2, estrategia)
    for x, y in zip(s1, s2):
        np.testing.assert_array_equal(x[:corte + 1], y[:corte + 1])
    a = simular(df, estrategia, P, T0, fin(df))
    b = simular(alterado, estrategia, P, T0, fin(df))
    t = df["fecha"].iloc[corte]
    ca = [vars(o) for o in a.operaciones if o.salida <= t]
    cb = [vars(o) for o in b.operaciones if o.salida <= t]
    assert ca == cb and len(ca) > 0
    m = a.fechas <= t
    np.testing.assert_array_equal(a.equity[m], b.equity[m])


def test_recorte_en_fin_ignora_datos_posteriores():
    df = serie()
    corte = df["fecha"].iloc[2000]
    a = simular(df, "A", P, T0, corte)
    b = simular(df.iloc[:2001], "A", P, T0, corte)
    assert [vars(o) for o in a.operaciones] == [vars(o) for o in b.operaciones]


# ---------- verificación cruzada contra la reimplementación ingenua ----------

@pytest.mark.parametrize("semilla", [1, 2, 3])
def test_motor_coincide_con_reimplementacion(semilla):
    df = serie(semilla=semilla)
    df.loc[1500, "anomala"] = True
    sim = simular(df, "A", P, T0, fin(df))
    i0 = int((df["fecha"] < T0).sum())
    ref = operaciones_ingenuas(df.to_dict("records"), i0)
    assert len(sim.operaciones) == len(ref) > 10
    for op, r in zip(sim.operaciones, ref):
        assert op.entrada == df["fecha"].iloc[r["entrada"]]
        assert op.salida == df["fecha"].iloc[r["salida"]]
        assert op.motivo == r["motivo"]
        assert op.precio_entrada == pytest.approx(r["precio_entrada"], rel=1e-12)
        assert op.precio_salida == pytest.approx(r["precio_salida"], rel=1e-12)
        assert op.pnl == pytest.approx(r["pnl"], rel=1e-9, abs=1e-9)


# ---------- referencias, métricas y clasificación ----------

def test_comprar_y_mantener():
    df = serie()
    sim = comprar_y_mantener(df, P, T0, fin(df))
    d = df[df["fecha"] >= T0]
    q = P.capital / (d["open"].iloc[0] * 1.0005 * 1.001)
    assert sim.equity[-1] == pytest.approx(q * d["close"].iloc[-1] * 0.9995 * 0.999)


def test_metricas_basicas():
    df = serie()
    sim = simular(df, "A", P, T0, fin(df))
    r = metricas.resumen(sim)
    assert r["operaciones"] == len(sim.operaciones)
    assert r["rentabilidad_neta"] == pytest.approx(sim.equity[-1] / P.capital - 1)
    pnl = sum(o.pnl for o in sim.operaciones)
    assert sim.equity[-1] == pytest.approx(P.capital + pnl)  # todo el resultado viene de operaciones cerradas
    assert -1 < r["dd_max"] <= 0
    assert 0 < r["exposicion"] < 1


def test_bootstrap_determinista_y_razonable():
    x = np.random.default_rng(0).normal(0.01, 0.02, 200)
    a = metricas.bootstrap_bloques(x)
    assert np.array_equal(a, metricas.bootstrap_bloques(x))
    assert abs(a.mean() - x.mean()) < 0.001
    assert np.percentile(a, 2.5) < x.mean() < np.percentile(a, 97.5)


def test_etiqueta_salida_ema():
    df = serie()
    motivos = {o.motivo for o in simular(df, "EMA", P, T0, fin(df)).operaciones}
    assert "canal" not in motivos and "cruce_ema" in motivos
    assert "cruce_ema" not in {o.motivo for o in simular(df, "A", P, T0, fin(df)).operaciones}


def test_clasificar():
    ok = {"operaciones": 40, "expectativa": 0.01, "factor_beneficio": 1.5, "bootstrap_p1": 0.001, "rent_dd": 1.0}
    ref = {"rent_dd": 0.5}
    assert metricas.clasificar(ok, ok, ref)[0] == "CANDIDATA"
    assert metricas.clasificar({**ok, "operaciones": 29}, ok, ref)[0] == "INCONCLUSA"
    assert metricas.clasificar({**ok, "expectativa": -0.01}, ok, ref)[0] == "RECHAZADA"
    assert metricas.clasificar(ok, {**ok, "factor_beneficio": 1.1}, ref)[0] == "INCONCLUSA"
    assert metricas.clasificar({**ok, "bootstrap_p1": -0.001}, ok, ref)[0] == "INCONCLUSA"
    assert metricas.clasificar(ok, ok, {"rent_dd": 2.0})[0] == "INCONCLUSA"


# ---------- datos ----------

def test_limpiar_registra_duplicados_y_huecos(caplog):
    t = np.array([0, 1, 1, 2, 4, 5]) * datos.INTERVALO_MS["4h"]
    df = pd.DataFrame({"open_time": t, "open": 1.0, "high": 1.0, "low": 1.0, "close": 1.0, "volume": 1.0})
    with caplog.at_level("WARNING"):
        out = datos.limpiar(df, "4h", "test")
    assert len(out) == 5
    assert out["anomala"].tolist() == [False, False, False, True, False]
    assert "duplicado" in caplog.text and "hueco" in caplog.text


@pytest.mark.parametrize("desfase", [0, 1, 2, 3])
def test_agregar_4h(desfase):
    h = datos.INTERVALO_MS["1h"]
    n = 48
    rng = np.random.default_rng(desfase)
    c = 100 + rng.normal(0, 1, n).cumsum()
    df = pd.DataFrame({"open_time": np.arange(n) * h, "open": c - 0.1, "high": c + 1, "low": c - 1,
                       "close": c, "volume": 1.0, "anomala": False})
    out = datos.agregar_4h(df, desfase)
    assert (out["open_time"] % (4 * h) == desfase * h).all()
    completa = out.iloc[1] if desfase else out.iloc[0]
    k = int(completa["open_time"] // h)
    assert completa["open"] == df["open"][k]
    assert completa["close"] == df["close"][k + 3]
    assert completa["high"] == df["high"][k:k + 4].max()
    assert completa["low"] == df["low"][k:k + 4].min()
    assert not completa["anomala"]
    if desfase:
        assert out["anomala"].iloc[0]  # primer grupo incompleto
