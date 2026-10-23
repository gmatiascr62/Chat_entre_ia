"""Descarga, verificación y limpieza de velas spot de Binance (data.binance.vision).

Ver estrategia_A_v0.txt, secciones 1 y 7.
"""
import hashlib
import io
import logging
import urllib.request
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

URL = "https://data.binance.vision/data/spot/monthly/klines/{par}/{iv}/{par}-{iv}-{mes}.zip"
INTERVALO_MS = {"1h": 3_600_000, "4h": 14_400_000}
COLUMNAS = ["open_time", "open", "high", "low", "close", "volume"]

log = logging.getLogger("datos")


def meses(desde: str, hasta: str) -> list[str]:
    return [p.strftime("%Y-%m") for p in pd.period_range(desde, hasta, freq="M")]


def _bajar(url: str) -> bytes:
    with urllib.request.urlopen(url, timeout=120) as r:
        return r.read()


def descargar_mes(par: str, iv: str, mes: str, cache: Path) -> pd.DataFrame:
    """Devuelve las velas de un mes. Falla (excepción) si no se puede descargar o el checksum no coincide:
    un mes faltante no se rellena en silencio."""
    destino = cache / f"{par}-{iv}-{mes}.csv"
    if not destino.exists():
        url = URL.format(par=par, iv=iv, mes=mes)
        log.info("Descargando %s", url)
        contenido = _bajar(url)
        esperado = _bajar(url + ".CHECKSUM").decode().split()[0].lower()
        obtenido = hashlib.sha256(contenido).hexdigest()
        if obtenido != esperado:
            raise ValueError(f"Checksum distinto en {url}: esperado {esperado}, obtenido {obtenido}")
        with zipfile.ZipFile(io.BytesIO(contenido)) as z:
            nombre = z.namelist()[0]
            crudo = z.read(nombre).decode()
        cache.mkdir(parents=True, exist_ok=True)
        destino.write_text(crudo)
    df = pd.read_csv(destino, header=None, usecols=range(6), names=COLUMNAS, dtype=str)
    if not df.empty and not df.iloc[0, 0].strip().isdigit():  # algunos archivos traen encabezado
        df = df.iloc[1:]
    df = df.astype({"open_time": "int64", "open": float, "high": float, "low": float,
                    "close": float, "volume": float})
    # Desde 2025 Binance publica los timestamps spot en microsegundos.
    micro = df["open_time"] > 10**14
    df.loc[micro, "open_time"] = df.loc[micro, "open_time"] // 1000
    return df


def cargar(par: str, iv: str, desde: str, hasta: str, cache: Path) -> pd.DataFrame:
    partes = [descargar_mes(par, iv, m, cache) for m in meses(desde, hasta)]
    return pd.concat(partes, ignore_index=True)


def limpiar(df: pd.DataFrame, iv: str, etiqueta: str) -> pd.DataFrame:
    """Procedimiento fijo de limpieza (sección 7). No elimina velas por su contenido: solo duplicados.
    Agrega la columna 'anomala' y registra cada problema en el log."""
    paso = INTERVALO_MS[iv]
    df = df.sort_values("open_time", kind="stable")
    dup = df["open_time"].duplicated(keep="first")
    for t in df.loc[dup, "open_time"]:
        log.warning("[%s] timestamp duplicado eliminado: %s", etiqueta, _fecha(t))
    df = df.loc[~dup].reset_index(drop=True)

    desalineadas = df["open_time"] % paso != 0
    for t in df.loc[desalineadas, "open_time"]:
        log.warning("[%s] vela no alineada a %s: %s", etiqueta, iv, _fecha(t))

    dif = df["open_time"].diff()
    hueco = (dif != paso) & dif.notna()
    for i in np.flatnonzero(hueco.to_numpy()):
        faltan = int(dif.iloc[i] // paso) - 1
        log.warning("[%s] hueco de datos: %d vela(s) faltante(s) entre %s y %s", etiqueta, faltan,
                    _fecha(df["open_time"].iloc[i - 1]), _fecha(df["open_time"].iloc[i]))

    vol0 = df["volume"] <= 0
    for t in df.loc[vol0, "open_time"]:
        log.warning("[%s] vela con volumen 0: %s", etiqueta, _fecha(t))

    o, h, l, c = (df[k] for k in ("open", "high", "low", "close"))
    invalida = (h < np.maximum(o, c)) | (l > np.minimum(o, c)) | (l <= 0)
    for _, fila in df.loc[invalida].iterrows():
        log.warning("[%s] OHLC inconsistente en %s: o=%s h=%s l=%s c=%s", etiqueta, _fecha(fila.open_time),
                    fila.open, fila.high, fila.low, fila.close)

    df["anomala"] = (hueco | vol0 | invalida).to_numpy()
    df["fecha"] = pd.to_datetime(df["open_time"], unit="ms", utc=True)
    log.info("[%s] %d velas de %s a %s; duplicadas=%d huecos=%d volumen0=%d inconsistentes=%d", etiqueta,
             len(df), df["fecha"].iloc[0], df["fecha"].iloc[-1], int(dup.sum()), int(hueco.sum()),
             int(vol0.sum()), int(invalida.sum()))
    return df


def agregar_4h(df1h: pd.DataFrame, desfase_horas: int) -> pd.DataFrame:
    """Reconstruye velas de 4h desde velas de 1h ya limpias. La vela empieza en las horas desfase, desfase+4, ...
    (UTC). Un grupo con menos de 4 velas de 1h, o con alguna vela anómala, queda marcado como anómalo."""
    h = INTERVALO_MS["1h"]
    paso = INTERVALO_MS["4h"]
    inicio = (df1h["open_time"] - desfase_horas * h) // paso * paso + desfase_horas * h
    g = df1h.groupby(inicio.to_numpy(), sort=True)
    out = pd.DataFrame({
        "open_time": g["open_time"].first().index.astype("int64"),
        "open": g["open"].first().to_numpy(),
        "high": g["high"].max().to_numpy(),
        "low": g["low"].min().to_numpy(),
        "close": g["close"].last().to_numpy(),
        "volume": g["volume"].sum().to_numpy(),
    })
    incompleta = (g.size().to_numpy() < 4) | (g["open_time"].first().to_numpy() != out["open_time"].to_numpy())
    out["anomala"] = incompleta | g["anomala"].any().to_numpy()
    dif = out["open_time"].diff()
    out["anomala"] |= ((dif != paso) & dif.notna()).to_numpy()
    out["fecha"] = pd.to_datetime(out["open_time"], unit="ms", utc=True)
    return out


def _fecha(ms) -> str:
    return pd.Timestamp(int(ms), unit="ms", tz="UTC").strftime("%Y-%m-%d %H:%M UTC")
