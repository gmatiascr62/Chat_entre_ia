"""Métricas, bootstrap por bloques y clasificación (estrategia_A_v0.txt, secciones 9 y 10)."""
import numpy as np
import pandas as pd

from .motor import Simulacion

MIN_OPERACIONES = 30
BLOQUE = 5
REPETICIONES = 10_000
SEMILLA = 12345
PERCENTIL_DECISION = 1.0   # ver resultados/validacion_bootstrap.md y estrategia_A_v0.txt, sección 9
BLOQUE_DIAS = 20


def bootstrap_bloques(retornos: np.ndarray, bloque: int = BLOQUE, reps: int = REPETICIONES,
                      semilla: int = SEMILLA) -> np.ndarray:
    """Bootstrap circular por bloques de la media de 'retornos' (en orden temporal). Devuelve las medias remuestreadas."""
    n = len(retornos)
    rng = np.random.default_rng(semilla)
    nb = int(np.ceil(n / bloque))
    inicios = rng.integers(0, n, size=(reps, nb))
    idx = (inicios[:, :, None] + np.arange(bloque)[None, None, :]) % n
    muestras = retornos[idx.reshape(reps, -1)[:, :n]]
    return muestras.mean(axis=1)


def resumen(sim: Simulacion) -> dict:
    eq = sim.equity
    cap = sim.params.capital
    ops = sim.operaciones
    pnl = np.array([o.pnl for o in ops])
    ret = np.array([o.retorno for o in ops])
    ganan = pnl[pnl > 0].sum()
    pierden = -pnl[pnl < 0].sum()
    pico = np.maximum.accumulate(np.concatenate([[cap], eq]))[1:]
    dd = float((eq / pico - 1).min())
    anios = (sim.fechas[-1] - sim.fechas[0]).total_seconds() / (365.25 * 86400)
    rent = eq[-1] / cap - 1
    cagr = (eq[-1] / cap) ** (1 / anios) - 1 if anios > 0 else np.nan
    total = pnl.sum()
    top3 = np.sort(pnl)[::-1][:3].sum() / total if total > 0 else np.nan
    r = {
        "rentabilidad_neta": rent,
        "cagr": cagr,
        "dd_max": dd,
        "rent_dd": cagr / abs(dd) if dd < 0 else np.nan,
        "operaciones": len(ops),
        "tasa_aciertos": float((pnl > 0).mean()) if len(ops) else np.nan,
        "factor_beneficio": ganan / pierden if pierden > 0 else (np.inf if ganan > 0 else np.nan),
        "expectativa": float(ret.mean()) if len(ops) else np.nan,
        "exposicion": float(sim.en_posicion.mean()),
        "costos_totales": sim.costos_totales,
        "concentracion_top3": top3,
        "alerta_concentracion": bool(top3 > 0.5) if total > 0 else False,
        "bootstrap_p2_5": np.nan,
        "bootstrap_p1": np.nan,
        "bootstrap_temporal_p1": np.nan,
    }
    if len(ops) >= MIN_OPERACIONES:
        medias = bootstrap_bloques(ret)
        r["bootstrap_p2_5"] = float(np.percentile(medias, 2.5))
        r["bootstrap_p1"] = float(np.percentile(medias, PERCENTIL_DECISION))
    # Informativo: bloques de 20 días de retornos diarios de la equity (incluye los días sin posición)
    diario = pd.Series(eq, index=sim.fechas).resample("1D").last().dropna().pct_change().dropna().to_numpy()
    if len(diario) >= 2 * BLOQUE_DIAS:
        r["bootstrap_temporal_p1"] = float(np.percentile(bootstrap_bloques(diario, bloque=BLOQUE_DIAS),
                                                         PERCENTIL_DECISION))
    return r


def por_anio(sim: Simulacion) -> pd.Series:
    eq = pd.Series(sim.equity, index=sim.fechas)
    fin = eq.groupby(eq.index.year).last()
    previo = fin.shift(1).fillna(sim.params.capital)
    return fin / previo - 1


def clasificar(base: dict, doble: dict, ref_ema_base: dict) -> tuple[str, list[str]]:
    """Clasificación de la sección 10. Solo debe aplicarse a resultados de VALIDACIÓN."""
    motivos = []
    if base["operaciones"] < MIN_OPERACIONES:
        return "INCONCLUSA", [f"{base['operaciones']} operaciones (< {MIN_OPERACIONES})"]
    if not base["expectativa"] > 0 or not base["factor_beneficio"] > 1:
        return "RECHAZADA", ["expectativa ≤ 0 o factor de beneficio ≤ 1 con costos base"]
    for nombre, r in (("costos base", base), ("costos dobles", doble)):
        if not (r["expectativa"] > 0 and r["factor_beneficio"] > 1.2):
            motivos.append(f"no cumple expectativa > 0 y FB > 1,2 con {nombre}")
    if not base["bootstrap_p1"] > 0:
        motivos.append(f"percentil {PERCENTIL_DECISION:g} del bootstrap por bloques de operaciones ≤ 0")
    if not base["rent_dd"] > ref_ema_base["rent_dd"]:
        motivos.append("no supera a EMA(200) sola en rentabilidad/drawdown")
    return ("INCONCLUSA", motivos) if motivos else ("CANDIDATA", ["cumple a), b) y c)"])
