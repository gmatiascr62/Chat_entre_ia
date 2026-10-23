"""VALIDACIÓN única de la Estrategia A v0 (2023-01-01 a 2024-12-31), aprobada en Leer.txt.

Uso: python -m backtest.correr_validacion
- Se niega a correr si el motor no es exactamente el congelado en el commit f7b907e (hash de cada archivo).
- Se niega a correr si ya existe resultados/validacion_resumen.md: la validación se corre una sola vez.
- No descarga nada posterior a 2024-12 y aborta si aparece algún dato posterior: la reserva 2025+ sigue cerrada.
- Si alguna verificación falla, el resultado es INCONCLUSO por definición.
"""
import hashlib
import logging
import os
import sys
import traceback
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from . import datos, metricas
from .correr_diseno import ENCABEZADO, commit_actual, fila, fmt_num, fmt_pct, operaciones_csv
from .motor import Params, comprar_y_mantener, simular
from .verificacion import operaciones_ingenuas

RAIZ = Path(__file__).resolve().parent.parent
RESULTADOS = RAIZ / "resultados"
LOGS = RAIZ / "logs"
CACHE = RAIZ / "cache"
REGISTRO = RAIZ / "registro_experimentos.txt"
RESUMEN = RESULTADOS / "validacion_resumen.md"

VERSION = "Estrategia A v0"
COMMIT_CONGELADO = "f7b907e"
# Hash git (blob) de cada archivo del motor en el commit congelado
HASHES_CONGELADOS = {
    "backtest/datos.py": "c57cf238a661c85af5e48eedfe229d4787abe5a7",
    "backtest/motor.py": "b843571e9c6187cfe60266b8c9e235cf55c2e6fd",
    "backtest/metricas.py": "1b82579fcd3c87ee09ea63b16db17c2c11465689",
    "backtest/verificacion.py": "5a1e7e9f249c747671d4cbbf1d65918a0433c7ab",
}
PAR = "BTCUSDT"
DATOS_DESDE = "2017-08"   # historia previa: solo calienta indicadores
DATOS_HASTA = "2024-12"   # fin de validación: NO cambiar (la reserva 2025+ queda cerrada)
INICIO = pd.Timestamp("2023-01-01", tz="UTC")
FIN = pd.Timestamp("2024-12-31 23:59", tz="UTC")

log = logging.getLogger("validacion")


def configurar_logs():
    LOGS.mkdir(exist_ok=True)
    fmt = logging.Formatter("%(asctime)s | %(levelname)-7s | %(name)s | %(module)s:%(lineno)d | %(message)s")
    archivo = logging.FileHandler(LOGS / "validacion_errores.log", mode="w", encoding="utf-8")
    archivo.setFormatter(fmt)
    consola = logging.StreamHandler(sys.stdout)
    consola.setFormatter(fmt)
    raiz = logging.getLogger()
    raiz.setLevel(logging.INFO)
    raiz.handlers = [archivo, consola]


def hash_git(ruta: Path) -> str:
    contenido = ruta.read_bytes()
    return hashlib.sha1(b"blob %d\0" % len(contenido) + contenido).hexdigest()


def comprobar_motor_congelado() -> list[str]:
    errores = []
    for rel, esperado in HASHES_CONGELADOS.items():
        obtenido = hash_git(RAIZ / rel)
        log.info("Hash de %s: %s (congelado: %s)", rel, obtenido, esperado)
        if obtenido != esperado:
            errores.append(f"{rel} difiere del commit {COMMIT_CONGELADO}")
    return errores


def checksums(meses: list[str]) -> list[str]:
    """Checksums SHA-256 publicados por Binance para cada archivo usado (datos.descargar_mes ya los verificó al bajar
    cada mes; aquí se registran y se comparan con el CSV extraído en caché)."""
    lineas = []
    for mes in meses:
        url = datos.URL.format(par=PAR, iv="4h", mes=mes) + ".CHECKSUM"
        with urllib.request.urlopen(url, timeout=120) as r:
            publicado = r.read().decode().strip()
        csv = CACHE / f"{PAR}-4h-{mes}.csv"
        lineas.append(f"{publicado} | sha256 del CSV extraído: {hashlib.sha256(csv.read_bytes()).hexdigest()}")
    return lineas


def verificar(df4: pd.DataFrame, sim_a) -> tuple[bool, list[str]]:
    d = df4.loc[df4["fecha"] <= FIN].reset_index(drop=True)
    i0 = int((d["fecha"] < INICIO).sum())
    ref = operaciones_ingenuas(d.to_dict("records"), i0)
    ok = len(ref) == len(sim_a.operaciones)
    lineas = [f"Operaciones motor: {len(sim_a.operaciones)} | reimplementación: {len(ref)}", ""]
    for k, (op, r) in enumerate(zip(sim_a.operaciones, ref)):
        if not (op.entrada == d["fecha"].iloc[r["entrada"]] and op.salida == d["fecha"].iloc[r["salida"]]
                and op.motivo == r["motivo"] and np.isclose(op.precio_entrada, r["precio_entrada"], rtol=1e-12)
                and np.isclose(op.precio_salida, r["precio_salida"], rtol=1e-12)
                and np.isclose(op.pnl, r["pnl"], rtol=1e-9, atol=1e-9)):
            ok = False
            lineas.append(f"DIFERENCIA en operación {k + 1}: motor={vars(op)} reimplementación={r}")
            log.error("Verificación cruzada: diferencia en operación %d", k + 1)
    lineas.insert(0, "COINCIDEN" if ok else "NO COINCIDEN")
    return ok, lineas


def main():
    configurar_logs()
    if RESUMEN.exists():
        log.error("La validación ya se corrió (%s existe). No se vuelve a correr.", RESUMEN.name)
        return 2
    commit = commit_actual()
    ahora = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    log.info("Inicio VALIDACIÓN ÚNICA | %s | commit del repo %s | motor congelado %s | datos %s a %s",
             VERSION, commit, COMMIT_CONGELADO, DATOS_DESDE, DATOS_HASTA)

    fallas = comprobar_motor_congelado()
    if fallas:
        for f in fallas:
            log.error(f)
        log.error("El motor no es el congelado: se aborta sin mirar datos de validación")
        return 1

    crudo = datos.cargar(PAR, "4h", DATOS_DESDE, DATOS_HASTA, CACHE)
    df4 = datos.limpiar(crudo, "4h", f"{PAR} 4h")
    if df4["fecha"].max() > FIN:
        raise RuntimeError("Hay datos posteriores a 2024-12-31: se aborta para no tocar la reserva")
    sumas = checksums(datos.meses(DATOS_DESDE, DATOS_HASTA))
    RESULTADOS.mkdir(exist_ok=True)
    (RESULTADOS / "validacion_checksums.txt").write_text(
        "Checksums SHA-256 publicados por Binance (data.binance.vision) de los archivos usados en la validación\n"
        "(verificados contra cada ZIP al descargar), y sha256 del CSV extraído.\n\n" + "\n".join(sumas) + "\n")
    anom_val = df4.loc[(df4["fecha"] >= INICIO) & df4["anomala"], "fecha"]
    log.info("Velas anómalas dentro de validación: %d %s", len(anom_val), [str(x) for x in anom_val])

    base, doble = Params(), Params().costos_dobles()
    sims = {}
    for nombre, p in (("base", base), ("costos x2", doble)):
        sims[f"A {nombre}"] = simular(df4, "A", p, INICIO, FIN)
        sims[f"EMA(200) sola {nombre}"] = simular(df4, "EMA", p, INICIO, FIN)
        sims[f"Comprar y mantener {nombre}"] = comprar_y_mantener(df4, p, INICIO, FIN)
    res = {k: metricas.resumen(s) for k, s in sims.items()}
    for k, r in res.items():
        log.info("%s: %s", k, {a: (float(b) if isinstance(b, (float, np.floating)) else b) for a, b in r.items()})

    ok, lineas_verif = verificar(df4, sims["A base"])
    (RESULTADOS / "validacion_verificacion.md").write_text(
        "# Verificación cruzada — VALIDACIÓN\n\nMotor vs. reimplementación independiente, costos base, todas las "
        "operaciones.\n\n" + "\n".join(lineas_verif) + "\n")

    if ok:
        clase, motivos = metricas.clasificar(res["A base"], res["A costos x2"], res["EMA(200) sola base"])
    else:
        clase, motivos = "INCONCLUSA", ["la verificación cruzada no coincide (sección 11)"]
        log.error("Verificación cruzada FALLÓ: resultado INCONCLUSO por definición")
    log.info("CLASIFICACIÓN: %s | %s", clase, "; ".join(motivos))

    operaciones_csv(sims["A base"], RESULTADOS / "validacion_operaciones_A.csv")
    operaciones_csv(sims["EMA(200) sola base"], RESULTADOS / "validacion_operaciones_EMA.csv")
    pd.DataFrame({k: pd.Series(s.equity, index=s.fechas) for k, s in sims.items() if "base" in k}) \
        .to_csv(RESULTADOS / "validacion_equity.csv", index_label="fecha")

    a, ad, e = res["A base"], res["A costos x2"], res["EMA(200) sola base"]
    uso = [o.cantidad * o.precio_entrada * (1 + base.comision) / o.capital_inicial for o in sims["A base"].operaciones]
    anual = pd.DataFrame({k: metricas.por_anio(s) for k, s in sims.items() if "base" in k})
    criterios = [
        ("Operaciones ≥ 30", f"{a['operaciones']}", a["operaciones"] >= 30),
        ("Expectativa > 0 (costos base)", fmt_pct(a["expectativa"], 4), a["expectativa"] > 0),
        ("FB > 1,2 (costos base)", fmt_num(a["factor_beneficio"]), a["factor_beneficio"] > 1.2),
        ("Expectativa > 0 (costos x2)", fmt_pct(ad["expectativa"], 4), ad["expectativa"] > 0),
        ("FB > 1,2 (costos x2)", fmt_num(ad["factor_beneficio"]), ad["factor_beneficio"] > 1.2),
        ("Bootstrap ops p1 > 0", fmt_pct(a["bootstrap_p1"], 4), a["bootstrap_p1"] > 0),
        ("CAGR/DD de A > CAGR/DD de EMA sola (costos base)",
         f"{fmt_num(a['rent_dd'])} vs {fmt_num(e['rent_dd'])}", a["rent_dd"] > e["rent_dd"]),
    ]
    md = [f"# Resultados — VALIDACIÓN ÚNICA ({INICIO.date()} a {FIN.date()})", "",
          f"{VERSION}, motor congelado en el commit {COMMIT_CONGELADO} (hashes comprobados; ver "
          f"logs/validacion_errores.log). BTC/USDT spot, velas oficiales de 4h de Binance. Capital inicial "
          f"{base.capital:,.0f} USDT, sin posición heredada; los indicadores usan la historia desde {DATOS_DESDE}. "
          f"Corrida: {ahora}, commit del repo {commit}. La reserva 2025+ no se descargó.", "",
          f"## Clasificación (sección 10): **{clase}**", "",
          *[f"- {m}" for m in motivos], "",
          "| Criterio | Valor | ¿Cumple? |", "|---|---|---|",
          *[f"| {n} | {v} | {'sí' if c else 'no'} |" for n, v, c in criterios], "",
          f"Verificación cruzada motor vs. reimplementación: **{'COINCIDEN' if ok else 'NO COINCIDEN'}**.", "",
          "No es una recomendación de inversión ni una afirmación de rentabilidad futura. "
          "CANDIDATA significaría solo pasar a paper trading.", "",
          "## Escenarios", "", ENCABEZADO, *[fila(k, r) for k, r in res.items()], "",
          f"Uso del capital por operación de A: mediana {np.median(uso) * 100:.1f}%, máximo {max(uso) * 100:.1f}% "
          "(el resto queda en efectivo al 0%)." if uso else "A no hizo operaciones.", "",
          "Bootstrap: bloques circulares de 5 operaciones, 10.000 repeticiones, semilla 12345; el percentil 1 se "
          "apoya en ~100 remuestreos de la cola y es una aproximación (ver resultados/validacion_bootstrap.md). "
          "Bootstrap temporal: bloques de 20 días de retornos diarios, solo informativo.", "",
          f"Valores exactos (A, costos base): p2,5 = {a['bootstrap_p2_5']!r}, p1 = {a['bootstrap_p1']!r}, "
          f"temporal p1 = {a['bootstrap_temporal_p1']!r}.", "",
          "## Resultado por año (costos base)", "",
          "| Año | " + " | ".join(anual.columns) + " |", "|---|" + "---|" * len(anual.columns),
          *[f"| {y} | " + " | ".join(fmt_pct(v) for v in f) + " |" for y, f in anual.iterrows()]]
    RESUMEN.write_text("\n".join(md) + "\n")

    with REGISTRO.open("a", encoding="utf-8") as f:
        f.write(f"\n{ahora} | commit repo {commit}, motor {COMMIT_CONGELADO} | {VERSION} | VALIDACIÓN ÚNICA "
                f"{INICIO.date()}..{FIN.date()} | verificación={'OK' if ok else 'FALLA'} | CLASIFICACIÓN: {clase} | "
                f"A base: ops={a['operaciones']} rent={fmt_pct(a['rentabilidad_neta'])} DD={fmt_pct(a['dd_max'])} "
                f"FB={fmt_num(a['factor_beneficio'])} expect={fmt_pct(a['expectativa'], 4)} "
                f"p1={fmt_pct(a['bootstrap_p1'], 4)} CAGR/DD={fmt_num(a['rent_dd'])} | A x2: "
                f"FB={fmt_num(ad['factor_beneficio'])} expect={fmt_pct(ad['expectativa'], 4)} | EMA sola base: "
                f"ops={e['operaciones']} CAGR/DD={fmt_num(e['rent_dd'])} | GitHub Actions run "
                f"{os.environ.get('GITHUB_RUN_ID', 'local')}\n")
    log.info("Fin VALIDACIÓN ÚNICA")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        if not logging.getLogger().handlers:
            configurar_logs()
        logging.getLogger("validacion").critical("Error no controlado:\n%s", traceback.format_exc())
        sys.exit(1)
