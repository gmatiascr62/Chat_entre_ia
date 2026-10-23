"""Corre la Estrategia A v0 y sus referencias SOLO en el período de diseño (2018-01-01 a 2022-12-31).

Uso: python -m backtest.correr_diseno
Escribe resultados/, logs/errores.log, datos/ y agrega una entrada a registro_experimentos.txt.
No descarga datos posteriores a 2022-12: la validación no se mira hasta verificar código y costos.
"""
import logging
import os
import subprocess
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from . import datos, metricas
from .motor import Params, comprar_y_mantener, simular
from .verificacion import operaciones_ingenuas

RAIZ = Path(__file__).resolve().parent.parent
RESULTADOS = RAIZ / "resultados"
LOGS = RAIZ / "logs"
DATOS = RAIZ / "datos"
CACHE = RAIZ / "cache"
REGISTRO = RAIZ / "registro_experimentos.txt"

VERSION = "Estrategia A v0"
PAR = "BTCUSDT"
DATOS_DESDE = "2017-08"
DATOS_HASTA = "2022-12"  # fin del período de diseño: NO cambiar sin decisión explícita (validación)
INICIO = pd.Timestamp("2018-01-01", tz="UTC")
FIN = pd.Timestamp("2022-12-31 23:59", tz="UTC")
RUPTURAS_SENSIBILIDAD = [10, 15, 20, 30, 40, 55]

log = logging.getLogger("diseno")


def configurar_logs():
    LOGS.mkdir(exist_ok=True)
    fmt = logging.Formatter("%(asctime)s | %(levelname)-7s | %(name)s | %(module)s:%(lineno)d | %(message)s")
    archivo = logging.FileHandler(LOGS / "errores.log", mode="w", encoding="utf-8")
    archivo.setFormatter(fmt)
    consola = logging.StreamHandler(sys.stdout)
    consola.setFormatter(fmt)
    raiz = logging.getLogger()
    raiz.setLevel(logging.INFO)
    raiz.handlers = [archivo, consola]


def commit_actual() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=RAIZ, text=True).strip()
    except Exception:
        return "desconocido"


def fmt_pct(x, decimales=2):
    return "n/d" if x is None or (isinstance(x, float) and np.isnan(x)) else f"{x * 100:.{decimales}f}%"


def fmt_num(x):
    return "n/d" if x is None or (isinstance(x, float) and np.isnan(x)) else f"{x:.2f}"


def fila(nombre, r):
    return (f"| {nombre} | {fmt_pct(r['rentabilidad_neta'])} | {fmt_pct(r['cagr'])} | {fmt_pct(r['dd_max'])} | "
            f"{fmt_num(r['rent_dd'])} | {r['operaciones']} | {fmt_pct(r['tasa_aciertos'])} | "
            f"{fmt_num(r['factor_beneficio'])} | {fmt_pct(r['expectativa'])} | {fmt_pct(r['exposicion'])} | "
            f"{r['costos_totales']:.0f} | {fmt_pct(r['concentracion_top3'])}"
            f"{' ⚠' if r['alerta_concentracion'] else ''} | {fmt_pct(r['bootstrap_p2_5'])} | {fmt_pct(r['bootstrap_p1'])} | "
            f"{fmt_pct(r['bootstrap_temporal_p1'], 3)} |")


ENCABEZADO = ("| Escenario | Rent. neta | CAGR | DD máx | CAGR/DD | Ops | Aciertos | FB | Expectativa/op | "
              "Exposición | Costos (USDT) | Top-3 / beneficio | Bootstrap ops p2,5 | Bootstrap ops p1 | "
              "Bootstrap temporal p1 (diario) |\n"
              "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")


def operaciones_csv(sim, ruta):
    filas = [{"senal": o.senal, "entrada": o.entrada, "precio_entrada": o.precio_entrada, "stop": o.stop,
              "cantidad": o.cantidad, "salida": o.salida, "precio_salida": o.precio_salida, "motivo": o.motivo,
              "pnl_usdt": o.pnl, "retorno": o.retorno, "costos_usdt": o.costos} for o in sim.operaciones]
    pd.DataFrame(filas).to_csv(ruta, index=False)


def verificar(df4: pd.DataFrame, sim_a) -> tuple[bool, str]:
    """Compara TODAS las operaciones del motor contra la reimplementación independiente sobre los datos reales."""
    d = df4.loc[df4["fecha"] <= FIN].reset_index(drop=True)
    i0 = int((d["fecha"] < INICIO).sum())
    ref = operaciones_ingenuas(d.to_dict("records"), i0)
    lineas = [f"Operaciones motor: {len(sim_a.operaciones)} | reimplementación: {len(ref)}", ""]
    ok = len(ref) == len(sim_a.operaciones)
    for k, (op, r) in enumerate(zip(sim_a.operaciones, ref)):
        iguales = (op.entrada == d["fecha"].iloc[r["entrada"]] and op.salida == d["fecha"].iloc[r["salida"]]
                   and op.motivo == r["motivo"] and np.isclose(op.precio_entrada, r["precio_entrada"], rtol=1e-12)
                   and np.isclose(op.precio_salida, r["precio_salida"], rtol=1e-12)
                   and np.isclose(op.pnl, r["pnl"], rtol=1e-9, atol=1e-9))
        if not iguales:
            ok = False
            lineas.append(f"DIFERENCIA en operación {k + 1}: motor={vars(op)} reimplementación={r}")
            log.error("Verificación cruzada: diferencia en operación %d: motor=%s ref=%s", k + 1, vars(op), r)
    lineas.insert(0, "COINCIDEN" if ok else "NO COINCIDEN")
    # Detalle de las 5 primeras operaciones para revisión manual contra datos/BTCUSDT-4h.csv
    lineas += ["", "Primeras 5 operaciones (para revisión manual contra datos/BTCUSDT-4h.csv):", ""]
    for r in ref[:5]:
        i, j, s = r["senal"], r["entrada"], r["salida"]
        lineas.append(
            f"- Señal {d['fecha'].iloc[i]}: cierre={d['close'].iloc[i]} > máx 20 previos="
            f"{d['high'].iloc[i - 20:i].max()}; entrada {d['fecha'].iloc[j]} apertura={d['open'].iloc[j]} "
            f"(con desliz. {r['precio_entrada']:.4f}); stop={r['stop']:.4f}; salida {d['fecha'].iloc[s]} "
            f"por {r['motivo']} a {r['precio_salida']:.4f}; PnL={r['pnl']:.2f} USDT")
    return ok, "\n".join(lineas)


def main():
    configurar_logs()
    commit = commit_actual()
    ahora = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    log.info("Inicio corrida de DISEÑO | %s | commit %s | datos %s a %s", VERSION, commit, DATOS_DESDE, DATOS_HASTA)
    for d in (RESULTADOS, DATOS):
        d.mkdir(exist_ok=True)

    crudo4 = datos.cargar(PAR, "4h", DATOS_DESDE, DATOS_HASTA, CACHE)
    crudo1 = datos.cargar(PAR, "1h", DATOS_DESDE, DATOS_HASTA, CACHE)
    df4 = datos.limpiar(crudo4, "4h", f"{PAR} 4h")
    df1 = datos.limpiar(crudo1, "1h", f"{PAR} 1h")
    if df4["fecha"].max() > FIN or df1["fecha"].max() > FIN:
        raise RuntimeError("Hay datos posteriores al período de diseño: se aborta para no mirar la validación")
    df4.drop(columns="fecha").to_csv(DATOS / f"{PAR}-4h.csv", index=False)
    df1.drop(columns="fecha").to_csv(DATOS / f"{PAR}-1h.csv", index=False)

    base = Params()
    doble = base.costos_dobles()
    sims, res = {}, {}
    for nombre, p in (("base", base), ("costos x2", doble)):
        sims[f"A {nombre}"] = simular(df4, "A", p, INICIO, FIN)
        sims[f"EMA(200) sola {nombre}"] = simular(df4, "EMA", p, INICIO, FIN)
        sims[f"Comprar y mantener {nombre}"] = comprar_y_mantener(df4, p, INICIO, FIN)
    for k, s in sims.items():
        res[k] = metricas.resumen(s)
        log.info("%s: %s", k, {a: (round(b, 6) if isinstance(b, float) else b) for a, b in res[k].items()})

    desfases = {}
    for dh in range(4):
        d4 = datos.agregar_4h(df1, dh)
        n_anom = int(d4["anomala"].sum())
        log.info("Velas 4h desde 1h con desfase %dh: %d velas, %d anómalas", dh, len(d4), n_anom)
        for est in ("A", "EMA"):
            desfases[(dh, est)] = metricas.resumen(simular(d4, est, base, INICIO, FIN))

    rupturas = {n: metricas.resumen(simular(df4, "A", Params(ruptura=n), INICIO, FIN))
                for n in RUPTURAS_SENSIBILIDAD}

    ok, texto_verif = verificar(df4, sims["A base"])
    (RESULTADOS / "diseno_verificacion.md").write_text(
        "# Verificación cruzada — período de diseño\n\nMotor vs. reimplementación independiente "
        "(backtest/verificacion.py), costos base, todas las operaciones.\n\n" + texto_verif + "\n")
    if not ok:
        log.error("La verificación cruzada FALLÓ: los resultados no deben usarse hasta resolverlo")

    operaciones_csv(sims["A base"], RESULTADOS / "diseno_operaciones_A.csv")
    operaciones_csv(sims["EMA(200) sola base"], RESULTADOS / "diseno_operaciones_EMA.csv")
    pd.DataFrame({k: pd.Series(s.equity, index=s.fechas) for k, s in sims.items() if "base" in k}) \
        .to_csv(RESULTADOS / "diseno_equity.csv", index_label="fecha")

    anual = pd.DataFrame({k: metricas.por_anio(s) for k, s in sims.items() if "base" in k})
    md = [f"# Resultados — período de DISEÑO ({INICIO.date()} a {FIN.date()})", "",
          f"{VERSION} (ver estrategia_A_v0.txt). BTC/USDT spot, velas de 4h de Binance. Capital inicial "
          f"{base.capital:,.0f} USDT. Corrida: {ahora}, commit {commit}.", "",
          "**Estos son datos de diseño.** No sirven para aprobar ni rechazar la estrategia: la clasificación "
          "(sección 10) se aplica solo en validación. La validación todavía no se miró.", "",
          f"Verificación cruzada motor vs. reimplementación: **{'COINCIDEN' if ok else 'NO COINCIDEN'}** "
          "(detalle en diseno_verificacion.md).", "",
          "## Escenarios principales", "", ENCABEZADO]
    md += [fila(k, r) for k, r in res.items()]
    md += ["", "CAGR/DD = CAGR / |drawdown máximo|. Expectativa/op = media del resultado neto de cada operación "
           "sobre el capital al entrar. Bootstrap ops = percentiles 2,5 y 1 de la expectativa por operación "
           "remuestreando bloques de 5 operaciones (10.000 repeticiones; n/d con menos de 30 operaciones). El p1 es el "
           "propuesto para decidir (ver resultados/validacion_bootstrap.md). Bootstrap temporal = percentil 1 del retorno "
           "diario medio de la equity remuestreando bloques de 20 días (solo informativo). "
           "⚠ = alerta de concentración (> 50%).", "",
           "## Resultado por año (costos base)", "",
           "| Año | " + " | ".join(anual.columns) + " |", "|---|" + "---|" * len(anual.columns)]
    md += [f"| {a} | " + " | ".join(fmt_pct(v) for v in fila_a) + " |" for a, fila_a in anual.iterrows()]
    md += ["", "## Sensibilidad: alineación de las velas de 4h (reconstruidas desde 1h, costos base)", "",
           "Se informan todas; no se elige la mejor. Desfase 0h debería parecerse a las velas oficiales.", "",
           ENCABEZADO]
    md += [fila(f"{'A' if est == 'A' else 'EMA(200) sola'} desfase {dh}h", r) for (dh, est), r in desfases.items()]
    md += ["", "## Sensibilidad: velas de ruptura (Estrategia A, costos base)", "",
           "Solo para ver si el resultado depende de un valor puntual. El parámetro sigue fijo en 20.", "",
           ENCABEZADO]
    md += [fila(f"A ruptura {n}", r) for n, r in rupturas.items()]
    (RESULTADOS / "diseno_resumen.md").write_text("\n".join(md) + "\n")

    a, e = res["A base"], res["EMA(200) sola base"]
    with REGISTRO.open("a", encoding="utf-8") as f:
        f.write(f"\n{ahora} | commit {commit} | {VERSION} | DISEÑO {INICIO.date()}..{FIN.date()} | "
                f"verificación={'OK' if ok else 'FALLA'} | A base: ops={a['operaciones']} "
                f"rent={fmt_pct(a['rentabilidad_neta'])} DD={fmt_pct(a['dd_max'])} FB={fmt_num(a['factor_beneficio'])} "
                f"CAGR/DD={fmt_num(a['rent_dd'])} | EMA sola base: ops={e['operaciones']} "
                f"rent={fmt_pct(e['rentabilidad_neta'])} CAGR/DD={fmt_num(e['rent_dd'])} | sensibilidad informada, no usada "
                f"para elegir: velas 4h desde 1h con desfases 0-3h y rupturas {RUPTURAS_SENSIBILIDAD} | "
                f"corrida automática (GitHub Actions run {os.environ.get('GITHUB_RUN_ID', 'local')})\n")
    log.info("Fin corrida de DISEÑO. Verificación cruzada: %s", "OK" if ok else "FALLA")
    return 0 if ok else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        configurar_logs() if not logging.getLogger().handlers else None
        logging.getLogger("diseno").critical("Error no controlado:\n%s", traceback.format_exc())
        sys.exit(1)
