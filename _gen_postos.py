"""
_gen_postos.py - DEV: monta a tabela dos 33 postos 'Referencial' do RJ com coords.

Le _pnct/vmda2022.xlsx, filtra RJ + classificacao='Referencial', extrai um nome de
lugar das descricoes e geocodifica via Nominatim (validando bbox do RJ). Salva
_pnct/postos_rj.csv (br, km, vmda, lat, lon, label). Roda uma vez (rate-limit ~1/s).
"""
import csv
import json
import os
import re
import time
import urllib.parse
import urllib.request

import openpyxl

RJ_BBOX = (-23.45, -20.70, -44.95, -40.90)  # lat_min, lat_max, lon_min, lon_max
UA = {"User-Agent": "tcc-pavimentos-ufrj/1.0"}
DIR = os.path.dirname(os.path.abspath(__file__))


def referenciais():
    wb = openpyxl.load_workbook(os.path.join(DIR, "_pnct", "vmda2022.xlsx"),
                                read_only=True, data_only=True)
    ws = wb["SNV202301B"]
    rows = ws.iter_rows(values_only=True)
    H = list(next(rows))
    idx = {h: i for i, h in enumerate(H)}
    g = lambda r, c: r[idx[c]] if c in idx else None
    out = []
    for r in rows:
        if g(r, "sg_uf") != "RJ":
            continue
        cl = str(g(r, "classificação") or g(r, "classificacao") or "").strip()
        if cl != "Referencial":
            continue
        tot = (g(r, "VMDa_C") or 0) + (g(r, "VMDa_D") or 0)
        out.append({"br": int(round(float(g(r, "vl_br")))),
                    "km": g(r, "vl_km_inic"),
                    "li": str(g(r, "ds_local_i") or "").strip(),
                    "lf": str(g(r, "ds_local_f") or "").strip(),
                    "vmda": round(tot)})
    return out


def candidatos(desc):
    """Nomes de lugar plausiveis extraidos de uma descricao de trecho."""
    cands = []
    for p in re.findall(r"\(([^)]*)\)", desc):
        p = p.strip()
        if re.fullmatch(r"[ABC]", p):
            continue
        p = re.sub(r"\b(BR|RJ|MG)-?\d+[A-Z]?", "", p)
        p = re.sub(r"^\s*(ACESSO|ENTR|TREVO|DIV|IN[IÍ]CIO|FIM)\b", "", p, flags=re.I)
        p = re.sub(r"^\s*(A|AO|AOS|P/|PARA|DE|DO|DA)\b", "", p, flags=re.I)
        p = p.strip(" /-.")
        if len(p) >= 4:
            cands.append(p)
    return cands


def geocode(q):
    url = ("https://nominatim.openstreetmap.org/search?q="
           + urllib.parse.quote(f"{q}, Rio de Janeiro, Brasil")
           + "&format=json&limit=1&countrycodes=br")
    try:
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=15) as r:
            d = json.load(r)
    except Exception:
        return None
    if not d:
        return None
    lat, lon = float(d[0]["lat"]), float(d[0]["lon"])
    la0, la1, lo0, lo1 = RJ_BBOX
    if la0 <= lat <= la1 and lo0 <= lon <= lo1:
        return round(lat, 5), round(lon, 5)
    return None


def main():
    refs = referenciais()
    print(f"postos Referencial: {len(refs)}")
    achados = []
    for p in refs:
        coord = None
        usado = ""
        for q in candidatos(p["li"]) + candidatos(p["lf"]):
            coord = geocode(q)
            time.sleep(1.1)
            if coord:
                usado = q
                break
        if coord:
            achados.append({**p, "lat": coord[0], "lon": coord[1], "lugar": usado})
            print(f"  OK BR-{p['br']:03d} VMDa={p['vmda']:>7,} -> {usado} {coord}")
        else:
            print(f"  -- BR-{p['br']:03d} km{p['km']} sem geocode ({p['li'][:30]})")
    out = os.path.join(DIR, "_pnct", "postos_rj.csv")
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["br", "km", "vmda", "lat", "lon", "lugar", "li", "lf"])
        w.writeheader()
        for a in achados:
            w.writerow({k: a.get(k) for k in w.fieldnames})
    print(f"\ngeocodificados: {len(achados)}/{len(refs)} -> {out}")


if __name__ == "__main__":
    main()
