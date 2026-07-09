"""
_gen_solos_display.py - DEV: gera versao LEVE da pedologia RJ p/ desenhar no mapa.

Le _solos/solos_rj.min.geojson (26 MB, preciso, usado na consulta) e produz
_solos/solos_rj.display.geojson (simplificado p/ render no Leaflet):
  - simplifica cada anel por Douglas-Peucker (iterativo) + arredonda coords,
  - descarta aneis/poligonos degenerados,
  - guarda so {ordem, textura, aashto, cor} por feicao (cor por grupo AASHTO).
NAO e usado na consulta de solo (essa usa o .min, preciso). So p/ visual.
"""
import json
import os

import solos_rj  # reaproveita textura_para_aashto

DIR = os.path.join(os.path.dirname(__file__), "_solos")
SRC = os.path.join(DIR, "solos_rj.min.geojson")
OUT = os.path.join(DIR, "solos_rj.display.geojson")

EPS = 0.0025      # tolerancia de simplificacao (~250 m)
CASAS = 4         # casas decimais nas coords

# Cor por grupo AASHTO (verde=bom subleito -> vermelho=ruim); cinza=sem solo.
CORES = {
    "A2-4 / A2-5": "#2e7d32",   # arenoso (CBR alto)
    "A4":          "#9e9d24",   # medio
    "A6":          "#ef6c00",   # argiloso
    "A7-5 / A7-6": "#c62828",   # muito argiloso (CBR baixo)
    None:          "#9e9e9e",   # urbano/rocha/ilha (sem textura)
}


def _perp(p, a, b):
    (x, y), (x1, y1), (x2, y2) = p, a, b
    dx, dy = x2 - x1, y2 - y1
    if dx == 0 and dy == 0:
        return ((x - x1) ** 2 + (y - y1) ** 2) ** 0.5
    t = ((x - x1) * dx + (y - y1) * dy) / (dx * dx + dy * dy)
    t = max(0.0, min(1.0, t))
    px, py = x1 + t * dx, y1 + t * dy
    return ((x - px) ** 2 + (y - py) ** 2) ** 0.5


def _dp(points, eps):
    """Douglas-Peucker iterativo (sem estourar recursao em aneis grandes)."""
    n = len(points)
    if n < 3:
        return points
    keep = [False] * n
    keep[0] = keep[-1] = True
    stack = [(0, n - 1)]
    while stack:
        i, j = stack.pop()
        dmax, idx = 0.0, -1
        for k in range(i + 1, j):
            d = _perp(points[k], points[i], points[j])
            if d > dmax:
                dmax, idx = d, k
        if dmax > eps and idx != -1:
            keep[idx] = True
            stack.append((i, idx))
            stack.append((idx, j))
    return [p for p, k in zip(points, keep) if k]


def _ring(ring):
    r = [[round(x, CASAS), round(y, CASAS)] for x, y in ring]
    # remove duplicados consecutivos
    out = [r[0]]
    for p in r[1:]:
        if p != out[-1]:
            out.append(p)
    out = _dp(out, EPS)
    if len(out) >= 4 and out[0] != out[-1]:
        out.append(out[0])
    return out if len(out) >= 4 else None


def main():
    src = json.load(open(SRC, encoding="utf-8"))
    feats = []
    for f in src["features"]:
        p = f["properties"]
        aashto, _ = solos_rj.textura_para_aashto(p.get("textura", ""))
        g = f["geometry"]
        polys = g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]]
        novos = []
        for poly in polys:
            aneis = [r for r in (_ring(ring) for ring in poly) if r]
            if aneis:
                novos.append(aneis)
        if not novos:
            continue
        feats.append({
            "type": "Feature",
            "properties": {"ordem": p.get("ordem", ""), "textura": p.get("textura", ""),
                           "aashto": aashto or "—", "cor": CORES.get(aashto)},
            "geometry": {"type": "MultiPolygon", "coordinates": novos},
        })
    out = {"type": "FeatureCollection", "features": feats}
    json.dump(out, open(OUT, "w", encoding="utf-8"), ensure_ascii=False,
              separators=(",", ":"))
    print("gerado:", OUT)
    print("feicoes:", len(feats), "| tamanho:",
          round(os.path.getsize(OUT) / 1e6, 2), "MB")


if __name__ == "__main__":
    main()
