"""
_gen_clima.py - DEV: gera _clima/clima_rj.csv (municipio -> precip media anual).

Para cada municipio do RJ (centroide da malha IBGE), busca a NORMAL CLIMATOLOGICA
de precipitacao na NASA POWER (media historica multi-anual; parametro PRECTOTCORR
em mm/dia -> x365.25 = mm/ano). Roda UMA vez; o app usa so o CSV (sem API em runtime).
"""
import csv
import json
import os
import time
import urllib.request

DIR = os.path.dirname(os.path.abspath(__file__))
MALHA = os.path.join(DIR, "_mun", "rj_municipios.min.geojson")
OUT = os.path.join(DIR, "_clima", "clima_rj.csv")
UA = {"User-Agent": "tcc-pavimentos-ufrj/1.0"}


def centroide(geom):
    xs, ys = [], []
    polys = geom["coordinates"] if geom["type"] == "MultiPolygon" else [geom["coordinates"]]
    for poly in polys:
        for ring in poly:
            for x, y in ring:
                xs.append(x); ys.append(y)
    return sum(ys) / len(ys), sum(xs) / len(xs)  # lat, lon


def precip_anual(lat, lon):
    url = ("https://power.larc.nasa.gov/api/temporal/climatology/point?"
           f"parameters=PRECTOTCORR&community=AG&longitude={lon:.4f}&latitude={lat:.4f}&format=JSON")
    try:
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=30) as r:
            d = json.load(r)
        ann = d["properties"]["parameter"]["PRECTOTCORR"]["ANN"]  # mm/dia
        return round(ann * 365.25)
    except Exception:
        return None


def main():
    os.makedirs(os.path.join(DIR, "_clima"), exist_ok=True)
    gj = json.load(open(MALHA, encoding="utf-8"))
    linhas = []
    for f in gj["features"]:
        nome = f["properties"]["municipio"]
        lat, lon = centroide(f["geometry"])
        mm = precip_anual(lat, lon)
        time.sleep(0.4)
        if mm is None:
            print(f"  -- {nome}: sem dado"); continue
        linhas.append({"municipio": nome, "lat": round(lat, 4), "lon": round(lon, 4), "precip_mm": mm})
        print(f"  {nome:32} {mm:>5} mm/ano")
    with open(OUT, "w", newline="", encoding="utf-8") as fp:
        w = csv.DictWriter(fp, fieldnames=["municipio", "lat", "lon", "precip_mm"])
        w.writeheader()
        w.writerows(linhas)
    mms = [x["precip_mm"] for x in linhas]
    print(f"\n{len(linhas)} municipios -> {OUT}")
    print(f"precip range: {min(mms)}..{max(mms)} mm/ano")


if __name__ == "__main__":
    main()
