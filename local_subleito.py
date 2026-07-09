"""
local_subleito.py - Localizacao (CEP) -> estimativa do subleito (solo/CBR/k0).

Objetivo (Ponto 1): a partir de um CEP, sinalizar ao usuario o solo provavel do
subleito e um k0/CBR de partida para o Estagio 3 - que ele SEMPRE confirma com
ensaio local. NUNCA substitui sondagem/CBR de campo; e uma ESTIMATIVA orientativa.

Cadeia de dados (RJ):
  CEP --ViaCEP--> municipio/UF/regiao/IBGE                 [solido, rapido, gratis]
  municipio --Nominatim/OSM--> coordenada (centroide)      [online]
  coordenada --solos_rj (EMBRAPA, OFFLINE)--> solo+textura [pedologia RJ empacotada]
  textura --> classe AASHTO --> CBR/k0 (estagio3.k_de_solo) [abacos IPR-714, validados]

Cobertura de solo: RJ (camada estadual do EMBRAPA). Fora do RJ, retorna so o
contexto do municipio e o usuario informa o solo/CBR manualmente no Estagio 3.
"""
from __future__ import annotations

import json
import urllib.parse
import urllib.request
from dataclasses import dataclass

import estagio3 as e3
import solos_rj

_TIMEOUT = 12
_UA = {"User-Agent": "tcc-pavimentos-ufrj/1.0"}


@dataclass
class Subleito:
    """Estimativa de subleito a partir da localizacao."""
    cep: str
    bairro: str
    municipio: str
    uf: str
    regiao: str
    ibge: str
    # coordenada usada na estimativa (centroide do municipio p/ CEP, ou o ponto clicado)
    lat: float | None = None
    lon: float | None = None
    # solo (preenchido quando ha dado de pedologia para a coordenada)
    ordem_sibcs: str | None = None     # ex.: ARGISSOLO, LATOSSOLO
    textura: str | None = None         # classe textural EMBRAPA
    classe_aashto: str | None = None
    cbr_estimado: float | None = None
    k0_estimado: float | None = None   # MPa/m
    fonte_solo: str = "nao determinado"
    confianca: str = "—"


def _get_json(url: str):
    req = urllib.request.Request(url, headers=_UA)
    with urllib.request.urlopen(req, timeout=_TIMEOUT) as r:
        return json.load(r)


def geocodificar_cep(cep: str) -> dict | None:
    """CEP -> {cep, bairro, municipio, uf, regiao, ibge}. None se invalido."""
    cep_num = "".join(ch for ch in str(cep) if ch.isdigit())
    if len(cep_num) != 8:
        return None
    try:
        d = _get_json(f"https://viacep.com.br/ws/{cep_num}/json/")
    except Exception:
        return None
    if not d or d.get("erro"):
        return None
    return {
        "cep": d.get("cep", cep_num),
        "bairro": d.get("bairro", ""),
        "municipio": d.get("localidade", ""),
        "uf": d.get("uf", ""),
        "regiao": d.get("regiao", ""),
        "ibge": d.get("ibge", ""),
    }


def coordenada_municipio(municipio: str, uf: str) -> tuple[float, float] | None:
    """Centroide do municipio via Nominatim/OSM -> (lat, lon). None se nao achar."""
    q = urllib.parse.quote(f"{municipio}, {uf}, Brasil")
    url = (f"https://nominatim.openstreetmap.org/search?q={q}"
           "&format=json&limit=1&countrycodes=br")
    try:
        d = _get_json(url)
    except Exception:
        return None
    if not d:
        return None
    return float(d[0]["lat"]), float(d[0]["lon"])


def sugerir_subleito(cep: str, consultar_solo: bool = True) -> Subleito | None:
    """
    CEP -> Subleito estimado. Geocodifica sempre (ViaCEP). Para CEPs do RJ, tenta
    estimar o solo via pedologia EMBRAPA (offline); fora do RJ os campos de solo
    ficam vazios p/ o usuario informar no Estagio 3.
    """
    g = geocodificar_cep(cep)
    if g is None:
        return None
    s = Subleito(cep=g["cep"], bairro=g["bairro"], municipio=g["municipio"],
                 uf=g["uf"], regiao=g["regiao"], ibge=g["ibge"])
    if not consultar_solo or s.uf != "RJ":
        return s

    coord = coordenada_municipio(s.municipio, s.uf)
    if coord is None:
        return s
    lat, lon = coord
    s.lat, s.lon = lat, lon
    _aplicar_solo(s, solos_rj.consultar(lon, lat))
    return s


def _aplicar_solo(s: Subleito, solo: dict | None) -> None:
    """Preenche os campos de solo do Subleito a partir do retorno de solos_rj."""
    if not (solo and solo.get("classe_aashto")):
        return
    s.ordem_sibcs = solo["ordem"]
    s.textura = solo["textura"]
    s.classe_aashto = solo["classe_aashto"]
    s.cbr_estimado = solo["cbr_tipico"]
    s.k0_estimado = e3.k_de_solo(solo["classe_aashto"])  # Quadro 3 do IPR-714
    proximidade = "" if solo["via"] == "no local" else " (solo proximo)"
    s.fonte_solo = f"Pedologia EMBRAPA (RJ){proximidade}"
    s.confianca = "estimativa por textura do solo — confirmar com CBR local"


def subleito_por_coordenada(lat: float, lon: float) -> Subleito:
    """
    Estima o subleito a partir de um ponto marcado no mapa (lat, lon) - sem CEP,
    sem rede. Usa direto a pedologia EMBRAPA (RJ). Se o ponto estiver fora do RJ,
    os campos de solo ficam vazios (consultar retorna None / sem textura).
    """
    s = Subleito(cep="", bairro="", municipio=f"ponto ({lat:.4f}, {lon:.4f})",
                 uf="RJ", regiao="", ibge="", lat=lat, lon=lon)
    _aplicar_solo(s, solos_rj.consultar(lon, lat))
    return s


if __name__ == "__main__":
    for cep in ["28013-000", "20271110", "27523-000"]:  # Campos, Rio, Resende
        s = sugerir_subleito(cep)
        if s is None:
            print(cep, "-> CEP invalido"); continue
        print(f"{cep}: {s.bairro}, {s.municipio}/{s.uf}")
        if s.classe_aashto:
            print(f"    solo: {s.ordem_sibcs} ({s.textura}) -> AASHTO {s.classe_aashto} "
                  f"| CBR~{s.cbr_estimado} | k0~{s.k0_estimado:.0f} MPa/m")
            print(f"    fonte: {s.fonte_solo} | {s.confianca}")
        else:
            print("    solo: nao estimado (informar no Estagio 3)")
