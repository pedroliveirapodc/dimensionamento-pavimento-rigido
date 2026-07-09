"""
clima.py - Precipitacao media anual por municipio (RJ), de SERIE HISTORICA.

Fonte: normal climatologica da NASA POWER (media multi-anual; PRECTOTCORR), pre-
calculada por municipio em _clima/clima_rj.csv (ver _gen_clima.py). NAO usa API em
runtime - so o CSV embarcado. Valor usado no criterio de precipitacao da triagem.

Obs: a NASA POWER tem resolucao ~0,5 graus, entao suaviza extremos (serra/lagos);
e uma ESTIMATIVA de referencia, suficiente p/ a faixa (categoria) da triagem.
"""
from __future__ import annotations

import csv
import os
import unicodedata
from functools import lru_cache

_ARQ = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_clima", "clima_rj.csv")


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode()
    return s.strip().lower()


@lru_cache(maxsize=1)
def _dados() -> list[dict]:
    try:
        with open(_ARQ, encoding="utf-8") as f:
            return [{"municipio": r["municipio"], "norm": _norm(r["municipio"]),
                     "lat": float(r["lat"]), "lon": float(r["lon"]),
                     "precip": int(r["precip_mm"])} for r in csv.DictReader(f)]
    except Exception:
        return []


def precip_por_coordenada(lat: float, lon: float) -> int | None:
    """Precipitacao media anual (mm) do municipio de centroide mais proximo. None se vazio."""
    d = _dados()
    if not d:
        return None
    m = min(d, key=lambda x: (x["lat"] - lat) ** 2 + (x["lon"] - lon) ** 2)
    return m["precip"]


def precip_municipio(nome: str) -> int | None:
    """Precipitacao media anual (mm) pelo nome do municipio (RJ). None se nao achar."""
    alvo = _norm(nome)
    for x in _dados():
        if x["norm"] == alvo:
            return x["precip"]
    return None


if __name__ == "__main__":
    for nome, lat, lon in [("Rio de Janeiro", -22.9, -43.2), ("Campos", -21.75, -41.33),
                           ("Cabo Frio", -22.88, -42.02), ("Nova Friburgo", -22.28, -42.53)]:
        print(f"{nome:18} coord->{precip_por_coordenada(lat, lon)} mm | nome->{precip_municipio(nome)}")
