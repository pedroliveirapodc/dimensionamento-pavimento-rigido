"""
solos_rj.py - Consulta OFFLINE do solo do subleito por coordenada (RJ).

Fonte: camada de pedologia do EMBRAPA GeoInfo (geonode:solos_rj_lat_long_wgs84_1),
RJ inteiro, 2807 poligonos com classe SiBCS (ordem) e classe textural (textura_1).
Baixada uma vez via WFS e enxugada em _solos/solos_rj.min.geojson (so os campos
uteis + coords arredondadas). Consulta = point-in-polygon puro-Python (sem shapely/
GDAL -> sem dependencia compilada).

Saida: classe textural -> grupo AASHTO estimado (heuristica documentada). NUNCA e
um CBR medido; e ESTIMATIVA de partida para o Estagio 3, a confirmar com ensaio.
"""
from __future__ import annotations

import json
import os
from functools import lru_cache

_ARQUIVO = os.path.join(os.path.dirname(__file__), "_solos", "solos_rj.min.geojson")

# Distancia maxima (graus ~0,7° ≈ 78 km) ao solo mapeado mais proximo; alem disso
# considera-se o ponto fora da cobertura (RJ) e nao se estima o solo.
_MAX_DIST_GRAUS = 0.7

# Classe textural (EMBRAPA) -> grupo AASHTO + CBR tipico. Prioridade do mais
# critico (argila plastica) ao melhor (arenoso): em texturas compostas (horizonte
# A/B, ex. "media/argilosa") adota-se o termo mais desfavoravel = conservador.
_PRIORIDADE = [
    ("organica",       "A7-5 / A7-6", 3),   # solo organico - muito fraco
    ("muito argilosa", "A7-5 / A7-6", 4),
    ("argilosa",       "A6",          5),
    ("media",          "A4",          8),
    ("arenosa",        "A2-4 / A2-5", 20),
]


def textura_para_aashto(textura: str) -> tuple[str | None, float | None]:
    """Classe textural EMBRAPA -> (grupo AASHTO, CBR tipico). (None,None) se vazio."""
    tl = (textura or "").lower()
    for kw, classe, cbr in _PRIORIDADE:
        if kw in tl:
            return classe, cbr
    return None, None


def _in_ring(x: float, y: float, ring: list) -> bool:
    inside = False
    n = len(ring); j = n - 1
    for i in range(n):
        xi, yi = ring[i]; xj, yj = ring[j]
        if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / (yj - yi) + xi):
            inside = not inside
        j = i
    return inside


def _in_poly(x: float, y: float, poly: list) -> bool:
    if not _in_ring(x, y, poly[0]):
        return False
    return not any(_in_ring(x, y, h) for h in poly[1:])


def _polys(geom: dict) -> list:
    return geom["coordinates"] if geom["type"] == "MultiPolygon" else [geom["coordinates"]]


@lru_cache(maxsize=1)
def _carregar() -> list[dict]:
    """Le o GeoJSON e pre-calcula bbox + centroide de cada feicao (uma vez)."""
    with open(_ARQUIVO, encoding="utf-8") as f:
        fs = json.load(f)["features"]
    out = []
    for feat in fs:
        polys = _polys(feat["geometry"])
        xs = [p[0] for poly in polys for ring in poly for p in ring]
        ys = [p[1] for poly in polys for ring in poly for p in ring]
        cx = sum(xs) / len(xs); cy = sum(ys) / len(ys)
        out.append({
            "props": feat["properties"],
            "polys": polys,
            "bbox": (min(xs), min(ys), max(xs), max(ys)),
            "cent": (cx, cy),
        })
    return out


def consultar(lon: float, lat: float) -> dict | None:
    """
    Solo do subleito na coordenada (lon, lat) no RJ.
    Retorna {ordem, textura, sbcs, classe_aashto, cbr_tipico, via} ou None se a
    base nao carregar / coordenada fora do RJ. Se o ponto cair em poligono sem
    textura (area urbana, ilha, afloramento), usa o solo COM textura mais proximo.
    """
    try:
        feats = _carregar()
    except (FileNotFoundError, ValueError):
        return None

    contendo = None
    for f in feats:
        x0, y0, x1, y1 = f["bbox"]
        if not (x0 <= lon <= x1 and y0 <= lat <= y1):
            continue
        if any(_in_poly(lon, lat, poly) for poly in f["polys"]):
            contendo = f
            break

    via = "no local"
    alvo = contendo
    if alvo is None or not alvo["props"].get("textura"):
        # fallback: feicao COM textura de centroide mais proximo
        melhor, dist = None, float("inf")
        for f in feats:
            if not f["props"].get("textura"):
                continue
            cx, cy = f["cent"]
            d = (cx - lon) ** 2 + (cy - lat) ** 2
            if d < dist:
                dist, melhor = d, f
        # ponto muito longe de qualquer solo mapeado (fora do RJ) -> sem estimativa
        if melhor is None or dist > _MAX_DIST_GRAUS ** 2:
            return None
        alvo = melhor
        via = "solo mais proximo com textura"

    p = alvo["props"]
    classe, cbr = textura_para_aashto(p.get("textura", ""))
    return {
        "ordem": p.get("ordem", ""),
        "textura": p.get("textura", ""),
        "sbcs": p.get("sbcs", ""),
        "classe_aashto": classe,
        "cbr_tipico": cbr,
        "via": via,
    }


if __name__ == "__main__":
    for nome, lon, lat in [("Rio/Maracana", -43.23, -22.91),
                           ("Campos", -41.33, -21.75),
                           ("Resende", -44.45, -22.47),
                           ("Itaperuna", -41.89, -21.20)]:
        r = consultar(lon, lat)
        if r:
            print(f"{nome:13} {r['ordem'][:12]:12} | {r['textura'][:30]:30} "
                  f"-> {r['classe_aashto']} CBR~{r['cbr_tipico']} ({r['via']})")
