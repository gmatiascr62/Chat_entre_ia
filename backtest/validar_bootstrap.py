"""Valida el bootstrap por bloques de operaciones con datos SINTÉTICOS de media conocida.

Mide la cobertura: en qué porcentaje de simulaciones el intervalo [p2,5 ; p97,5] contiene la media verdadera,
y con qué frecuencia el límite inferior (p2,5) queda por encima de ella (falso positivo de "ventaja").
Uso: python -m backtest.validar_bootstrap  -> escribe resultados/validacion_bootstrap.md
"""
from pathlib import Path

import numpy as np

from .metricas import bootstrap_bloques

SIMULACIONES = 1000
REPETICIONES = 2000  # menos que las 10.000 oficiales, para que tarde poco; no cambia la cobertura de forma apreciable


def secuencia(rng, n, phi, colas):
    """Resultados por operación con autocorrelación AR(1) 'phi' y colas pesadas (t de Student) si 'colas'."""
    ruido = rng.standard_t(3, n) / np.sqrt(3) if colas else rng.normal(0, 1, n)
    x = np.empty(n)
    x[0] = ruido[0]
    for i in range(1, n):
        x[i] = phi * x[i - 1] + np.sqrt(1 - phi ** 2) * ruido[i]
    return 0.01 * x  # media verdadera 0, desvío 1% por operación


def cobertura(n, phi, colas, semilla=7):
    rng = np.random.default_rng(semilla)
    dentro = falsos = 0
    for k in range(SIMULACIONES):
        m = bootstrap_bloques(secuencia(rng, n, phi, colas), reps=REPETICIONES, semilla=k)
        lo, hi = np.percentile(m, [2.5, 97.5])
        dentro += lo <= 0 <= hi
        falsos += lo > 0
    return dentro / SIMULACIONES, falsos / SIMULACIONES


def main():
    filas = []
    for n in (30, 60, 100):
        for phi in (0.0, 0.3, 0.6):
            for colas in (False, True):
                cob, fp = cobertura(n, phi, colas)
                filas.append(f"| {n} | {phi} | {'t(3)' if colas else 'normal'} | {cob * 100:.1f}% | {fp * 100:.1f}% |")
                print(filas[-1], flush=True)
    texto = "\n".join([
        "# Validación del bootstrap por bloques de operaciones (datos sintéticos)", "",
        f"{SIMULACIONES} simulaciones por fila, {REPETICIONES} repeticiones de bootstrap, bloques de 5 operaciones. "
        "Media verdadera = 0. Ideal: cobertura 95% y falsos positivos (p2,5 > 0) 2,5%.", "",
        "| Operaciones | Autocorrelación | Distribución | Cobertura del 95% | Falsos positivos (p2,5 > 0) |",
        "|---|---|---|---|---|", *filas, ""])
    Path(__file__).resolve().parent.parent.joinpath("resultados", "validacion_bootstrap.md").write_text(texto)


if __name__ == "__main__":
    main()
