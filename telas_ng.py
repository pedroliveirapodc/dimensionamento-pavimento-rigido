"""
telas_ng.py - Renderizadores das telas do wizard (versao NiceGUI).

Mesma logica de dominio de telas.py (Streamlit): cada tela le/grava o dict de
estado `s` e retorna `valido`. Como o NiceGUI e orientado a eventos (nao rerun
automatico), cada handler de input chama `refresh()` no final para redesenhar
a tela ativa - e o equivalente do st.rerun().

O backend (calculos, estagio3, tabelas, LCCA, sensibilidade, PDF...) e o MESMO
usado pela versao Streamlit, sem nenhuma alteracao.
"""
from __future__ import annotations

import re
import csv
import json
import math
import os

from nicegui import ui

import calculos as c
import tabelas_pca as tabp
import estagio3 as e3
import perfis_trafego as pt
import pnct_dados as pnct
import local_subleito as ls
import recomenda_subbase as rsb
import lcca as lc
import resultados as rel
import sensibilidade as sens
import triagem as tri
import clima
import ui_ng as ung

_DIR = os.path.dirname(os.path.abspath(__file__))


# ---------------------------------------------------------------
# loaders (cache simples em modulo - mesmos dados p/ todas as abas)
# ---------------------------------------------------------------
_cache: dict = {}


def _pnct_rj():
    if "pnct" not in _cache:
        try:
            _cache["pnct"] = pnct.carregar_trechos()
        except Exception:
            _cache["pnct"] = []
    return _cache["pnct"]


def _municipios():
    if "mun" not in _cache:
        p = os.path.join(_DIR, "_mun", "rj_municipios.min.geojson")
        try:
            with open(p, encoding="utf-8") as f:
                _cache["mun"] = json.load(f)
        except Exception:
            _cache["mun"] = None
    return _cache["mun"]


def _postos():
    if "postos" not in _cache:
        p = os.path.join(_DIR, "_pnct", "postos_rj.csv")
        try:
            with open(p, encoding="utf-8") as f:
                out = []
                for r in csv.DictReader(f):
                    out.append({"br": int(r["br"]), "km": float(r["km"]),
                                "vmda": int(r["vmda"]),
                                "lat": float(r["lat"]), "lon": float(r["lon"]),
                                "lugar": r["lugar"]})
                _cache["postos"] = sorted(out, key=lambda d: -d["vmda"])
        except Exception:
            _cache["postos"] = []
    return _cache["postos"]


def _mask_fora_rj():
    """Aneis p/ o poligono-mascara: retangulo grande com FUROS nos municipios
    do RJ (fillRule evenodd do Leaflet) -> tudo fora do estado fica acinzentado."""
    if "mask" not in _cache:
        mun = _municipios()
        rings: list = [[[-60.0, -100.0], [25.0, -100.0], [25.0, -10.0], [-60.0, -10.0]]]
        if mun is not None:
            for feat in mun.get("features", []):
                g = feat.get("geometry") or {}
                polys = ([g["coordinates"]] if g.get("type") == "Polygon"
                         else g.get("coordinates", []) if g.get("type") == "MultiPolygon" else [])
                for p in polys:
                    rings.append([[lat, lon] for lon, lat in p[0]])
        _cache["mask"] = rings
    return _cache["mask"]


def _posto_mais_proximo(lat, lon, postos):
    return min(postos, key=lambda p: (p["lat"] - lat) ** 2 + (p["lon"] - lon) ** 2, default=None)


def _haversine(lat1, lon1, lat2, lon2) -> float:
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2))
         * math.sin(dlon / 2) ** 2)
    return R * 2 * math.asin(math.sqrt(a))


# ---------------------------------------------------------------
# helper de mapa (Leaflet): clique -> callback(lat, lon)
# ---------------------------------------------------------------
def mapa_rj(*, center=(-22.2, -42.8), zoom=7, height="320px",
           marcadores: list[tuple[float, float, str, str]] = (),
           selecionado: tuple[float, float, str] | None = None,
           on_click=None):
    """Mapa do RJ com divisas municipais + marcadores (lat, lon, cor, tooltip).

    marcadores: circleMarkers coloridos c/ tooltip no hover.
    selecionado: (lat, lon, html) -> PINO Leaflet clássico com POP-UP ABERTO
                 sinalizando o local escolhido.
    Popups/tooltips exigem bind apos o mapa inicializar (run_layer_method e
    descartado antes do 'init'), por isso o ui.timer + m.initialized().
    """
    m = ui.leaflet(center=center, zoom=zoom).classes("w-full").style(f"height:{height}")
    mun = _municipios()
    if mun is not None:
        # mascara: fora do RJ fica cinza (nao selecionavel)
        m.generic_layer(name="polygon", args=[_mask_fora_rj(), {
            "stroke": False, "fillColor": "#77848B", "fillOpacity": 0.35,
            "interactive": False}])
        for feat in mun.get("features", []):
            m.generic_layer(name="geoJSON", args=[feat, {
                "style": {"color": "#546E7A", "weight": 0.8, "fillOpacity": 0, "dashArray": "4"}}])
    _CORES = {"red": "#c62828", "orange": "#E8A33D", "blue": "#1565C0"}
    circulos = []
    for lat, lon, cor, tip in marcadores:
        lay = m.generic_layer(name="circleMarker", args=[
            {"lat": lat, "lng": lon},
            {"radius": 8, "color": "#fff", "weight": 2, "fillColor": _CORES.get(cor, "#E8A33D"),
             "fillOpacity": 0.95}])
        circulos.append((lay, tip))
    pino = m.marker(latlng=(selecionado[0], selecionado[1])) if selecionado else None

    async def _pos_init():
        await m.initialized()
        for lay, tip in circulos:
            if tip:
                lay.run_method("bindTooltip", tip)
            # destaque no hover (marcador cresce) + clique no circulo = clique no mapa
            lay.run_method(":on", "'mouseover'",
                           "(e) => e.target.setStyle({radius: 13, weight: 3})")
            lay.run_method(":on", "'mouseout'",
                           "(e) => e.target.setStyle({radius: 8, weight: 2})")
            lay.run_method(":on", "'click'",
                           "(e) => e.target._map.fire('click', e)")
        if pino is not None and selecionado is not None:
            pino.run_method("bindPopup", selecionado[2])
            pino.run_method("openPopup")

    ui.timer(0.1, _pos_init, once=True)

    if on_click:
        def _handle(e):
            latlng = e.args.get("latlng", {})
            if "lat" in latlng and "lng" in latlng:
                on_click(round(latlng["lat"], 6), round(latlng["lng"], 6))
        m.on("map-click", _handle)
    return m


# ---------------------------------------------------------------
# ETAPA 1 - Modo do projeto
# ---------------------------------------------------------------
_MODOS = {
    "rodovia": ("🛣️ Pela rodovia",
                "Escolho um trecho real (posto PNCT/DNIT) e o app pré-define o que "
                "puder: tráfego real, solo, clima e viabilidade."),
    "local":   ("📍 Pela localização",
                "Marco o ponto da obra no mapa (ou CEP): solo, clima e tráfego vêm "
                "estimados para o local, e eu ajusto o que quiser."),
    "manual":  ("✏️ Manual",
                "Informo todos os parâmetros eu mesmo (nenhum dado pré-definido)."),
}


def render_modo(s: dict, refresh) -> bool:
    with ui.column().classes("w-full max-w-3xl mx-auto cartao p-8 gap-3 aparecer"):
        ung.pergunta("Como você quer montar o projeto?",
                    "A escolha vale para todas as etapas — dados pré-definidos ficam "
                    "sempre marcados com a origem e podem ser ajustados.")
        # grava o padrao exibido: antes so era gravado ao clicar, e as etapas
        # seguintes liam o padrao como "manual" (VMDa do posto era ignorado)
        atual = s.setdefault("modo_projeto", "rodovia")

        def _set(modo):
            s["modo_projeto"] = modo
            refresh()

        for k, (tit, desc) in _MODOS.items():
            ativo = atual == k
            with ui.row().classes(
                "w-full items-center gap-3 p-3 rounded-xl cursor-pointer border transition"
            ).style(f"border-color:{'#C8861F' if ativo else '#EDF0F2'};"
                    f"background:{'#FDF3E2' if ativo else '#fff'}") \
                    .on("click", lambda _, k=k: _set(k)):
                ui.icon("radio_button_checked" if ativo else "radio_button_unchecked") \
                    .classes("text-2xl").style(f"color:{'#C8861F' if ativo else '#CBD5E1'}")
                with ui.column().classes("gap-0"):
                    ui.label(tit).classes("font-bold").style(f"color:{ung.TEXTO}")
                    ui.label(desc).classes("text-sm text-slate-500")
        if atual != "manual":
            ui.label("Cobertura dos dados automáticos: Estado do RJ "
                     "(PNCT, EMBRAPA, NASA POWER, SICRO).").classes("text-xs text-slate-400 mt-1")
    return True


def _local_relatorio(s: dict) -> str | None:
    """Local para o relatorio: municipio (se houver) + coordenada em formato BR."""
    pto = s.get("ponto_obra")
    coord = (f"lat. {pto[0]:.4f}; long. {pto[1]:.4f}".replace(".", ",")
             .replace("lat,", "lat.").replace("long,", "long.")) if pto else None
    mun = s.get("municipio")
    if mun and not str(mun).strip().lower().startswith("ponto"):
        return f"{mun} ({coord})" if coord else str(mun)
    return coord


def _n_estimado(s: dict) -> float | None:
    """N de eixos estimado p/ pre-selecoes ANTES da etapa de trafego:
    usa o espectro real se ja existir; senao estima do VMDa (perfil rodovia,
    20 anos — mesma premissa do prefill da triagem)."""
    if s.get("n_pesados"):
        return s["n_pesados"]
    if s.get("vmda"):
        esp = pt.espectro_de_projeto(pt.PERFIS["rodovia"], float(s["vmda"]), 20, 0.5, 1.0, 0.03)
        return sum(f.repeticoes_previstas for f in esp)
    return None


def _prefill_triagem(s: dict, force: bool = False) -> None:
    fontes = s.setdefault("tri_fonte", {})

    def _set(k: str, val, fonte: str) -> None:
        if val is None:
            return
        if force or f"tri_{k}" not in s:
            s[f"tri_{k}"] = val
            fontes[k] = fonte

    sub = s.get("subleito")
    if sub is not None and getattr(sub, "cbr_estimado", None) is not None:
        _set("cbr", tri.cat_cbr(sub.cbr_estimado),
             f"CBR ≈ {sub.cbr_estimado}% estimado do solo {sub.classe_aashto} (pedologia EMBRAPA)")
    ponto = s.get("ponto_obra")
    if ponto:
        precip = clima.precip_por_coordenada(ponto[0], ponto[1])
        if precip is not None:
            _set("clima", tri.cat_precip(precip),
                 f"precipitação ≈ {precip:.0f} mm/ano no local (normal climatológica NASA POWER)")
    n_est = _n_estimado(s)
    if n_est:
        _set("traf", tri.cat_trafego(n_est),
             f"N ≈ {n_est:,.0f} eixos em 20 anos, estimado do VMDa {s['vmda']:,.0f} (PNCT/DNIT)"
             .replace(",", "."))


# ---------------------------------------------------------------
# ETAPA - Rodovia (modo "rodovia")
# ---------------------------------------------------------------
def render_rodovia(s: dict, refresh) -> bool:
    with ui.column().classes("w-full max-w-3xl mx-auto cartao p-8 gap-3 aparecer"):
        ung.pergunta("Em qual rodovia será o dimensionamento?",
                    "Clique perto de um pino 🛣️ para escolher o posto de contagem "
                    "PNCT/DNIT. O tráfego real, o solo e o clima do trecho pré-definem o projeto.")
        postos = _postos()
        if not postos:
            ui.label("Postos do PNCT indisponíveis. Volte e escolha outro modo.") \
                .classes("text-red-600")
            return False

        def _clique(lat, lon):
            p = _posto_mais_proximo(lat, lon, postos)
            if p and _haversine(lat, lon, p["lat"], p["lon"]) > 40.0:
                ui.notify("Área fora do RJ (região cinza) — clique num marcador "
                          "de rodovia dentro do estado.", type="warning")
                return
            if p and s.get("posto_sel") != p:
                s["posto_sel"] = p
                s["vmda"] = p["vmda"]
                s["ponto_obra"] = [p["lat"], p["lon"]]
                s["subleito"] = ls.subleito_por_coordenada(p["lat"], p["lon"])
                sub = s["subleito"]
                if sub and sub.classe_aashto:
                    s["k0"] = sub.k0_estimado
                    s["cbr_val"] = sub.cbr_estimado
                    s["municipio"] = sub.municipio
                s.pop("sb_prefill_feita", None)  # novo local -> re-sugerir sub-base
                _prefill_triagem(s, force=True)
                refresh()

        sel = s.get("posto_sel")
        marcadores = [(p["lat"], p["lon"], "orange",
                      f"BR-{p['br']:03d} · {p['lugar']} · VMDa {p['vmda']:,}".replace(",", "."))
                      for p in postos if p is not sel]
        pop = (f"<b>📍 BR-{sel['br']:03d}</b><br>{sel['lugar']}<br>"
               f"VMDa <b>{sel['vmda']:,}</b> veíc/dia".replace(",", ".")) if sel else None
        mapa_rj(marcadores=marcadores,
                selecionado=(sel["lat"], sel["lon"], pop) if sel else None,
                center=(sel["lat"], sel["lon"]) if sel else (-22.2, -42.8),
                zoom=8 if sel else 7,
                on_click=_clique)

        if not sel:
            ui.label("Clique perto de um pino para escolher o trecho.").classes("text-slate-500 mt-2")
            return False
        with ui.column().classes("mt-2 gap-1"):
            ui.label(f"Trecho: BR-{sel['br']:03d} ({sel['lugar']}) · VMDa real "
                     f"{sel['vmda']:,} veíc/dia (PNCT {pnct.ANO_BASE})".replace(",", ".")) \
                .classes("text-green-700 font-semibold")
            sub = s.get("subleito")
            if sub and sub.classe_aashto:
                ui.label(f"Solo no trecho: {sub.ordem_sibcs} · AASHTO {sub.classe_aashto} · "
                         f"CBR≈{sub.cbr_estimado} · k0 ≈ {sub.k0_estimado:.0f} MPa/m (EMBRAPA). "
                         "⚠️ Coordenada do posto é aproximada — confirme o solo com ensaio local.") \
                    .classes("text-xs text-slate-500")
            else:
                ui.label("⚠️ Solo não identificado na coordenada do posto — você informará "
                         "o subleito na etapa Fundação.").classes("text-xs text-slate-500")
    return True


# ---------------------------------------------------------------
# ETAPA - Local pelo mapa/CEP (modo "local")
# ---------------------------------------------------------------
def render_local_mapa(s: dict, refresh) -> bool:
    with ui.column().classes("w-full max-w-3xl mx-auto cartao p-8 gap-3 aparecer"):
        ung.pergunta("Onde fica a obra?",
                    "Clique no mapa no local aproximado (cobertura de solo: RJ) ou informe o CEP.")

        def _clique(lat, lon):
            if s.get("ponto_obra") != [lat, lon]:
                s["ponto_obra"] = [lat, lon]
                s["subleito"] = ls.subleito_por_coordenada(lat, lon)
                s.pop("posto_sel", None)
                s.pop("sb_prefill_feita", None)  # novo local -> re-sugerir sub-base
                _prefill_triagem(s, force=True)
                refresh()

        ponto = s.get("ponto_obra")
        sub_atual = s.get("subleito")
        pop_local = None
        if ponto:
            partes = ["<b>📍 Local da obra</b>"]
            if sub_atual and sub_atual.classe_aashto:
                if sub_atual.municipio:
                    partes.append(sub_atual.municipio)
                partes.append(f"{sub_atual.ordem_sibcs} · AASHTO {sub_atual.classe_aashto}")
            pop_local = "<br>".join(partes)
        mapa_rj(selecionado=(ponto[0], ponto[1], pop_local) if ponto else None,
                center=(ponto[0], ponto[1]) if ponto else (-22.2, -42.8),
                zoom=9 if ponto else 7,
                on_click=_clique)

        cep_input = ui.input("ou informe o CEP", placeholder="00000-000").classes("w-64")

        def _estimar_cep():
            cep = cep_input.value
            sub_cep = ls.sugerir_subleito(cep) if cep else None
            s["subleito"] = sub_cep
            if sub_cep is not None and sub_cep.lat is not None:
                s["ponto_obra"] = [sub_cep.lat, sub_cep.lon]
            else:
                s.pop("ponto_obra", None)
            s.pop("posto_sel", None)
            s.pop("sb_prefill_feita", None)  # novo local -> re-sugerir sub-base
            _prefill_triagem(s, force=True)
            refresh()

        ui.button("Estimar pelo CEP", on_click=_estimar_cep).props("outline no-caps rounded").classes("w-fit")

        sub = s.get("subleito")
        if sub and sub.classe_aashto:
            s["k0"] = sub.k0_estimado
            s["cbr_val"] = sub.cbr_estimado
            s["municipio"] = sub.municipio
            ui.label(f"{sub.ordem_sibcs} ({sub.textura}) · AASHTO {sub.classe_aashto} · "
                     f"CBR≈{sub.cbr_estimado} · k0 ≈ {sub.k0_estimado:.0f} MPa/m") \
                .classes("text-green-700 font-semibold mt-1")
            ui.label(f"⚠️ {sub.confianca}").classes("text-xs text-slate-500")
            return True
        elif sub is not None:
            ui.label("Sem dado de solo para este ponto (fora do RJ). Tente outro ponto "
                     "ou escolha o modo Manual.").classes("text-amber-700")
    return s.get("subleito") is not None and s["subleito"].classe_aashto is not None


# ---------------------------------------------------------------
# ETAPA - Subleito manual
# ---------------------------------------------------------------
def render_local_manual(s: dict, refresh) -> bool:
    with ui.column().classes("w-full max-w-3xl mx-auto cartao p-8 gap-3 aparecer"):
        ung.pergunta("Qual o subleito?", "Informe o CBR, o tipo de solo, ou o k0 direto.")
        metodo = ui.toggle(["Pelo CBR", "Pelo tipo de solo", "Valor direto"],
                           value=s.get("metodo_k0", "Pelo CBR")).classes("w-fit")

        cont = ui.column().classes("w-full gap-1")

        def _rebuild():
            s["metodo_k0"] = metodo.value
            cont.clear()
            with cont:
                if metodo.value == "Pelo CBR":
                    cbr_in = ui.number(
                        "CBR do subleito (%)", value=float(s.get("cbr_val") or 5.0),
                        min=2.0, max=100.0, step=0.5,
                    ).props("outlined dense").classes("w-64")
                    ui.label("Típico: argilas 2–8%, siltes 4–10%, solos granulares 10–30%. "
                             "Convertido em k0 pela Figura 11 do IPR-714.") \
                        .classes("text-xs text-slate-400")

                    def _upd_cbr(e):
                        s["k0"] = e3.k_de_cbr(e.value)
                        s["cbr_val"] = e.value
                        _rotulo.text = f"k0 do subleito ≈ {s['k0']:.0f} MPa/m"

                    cbr_in.on_value_change(_upd_cbr)
                    s["k0"] = e3.k_de_cbr(cbr_in.value)
                    s["cbr_val"] = cbr_in.value
                elif metodo.value == "Pelo tipo de solo":
                    classes = list(e3.QUADRO_3_SOLO_K)
                    sel = ui.select(classes, value=classes[0], label="Tipo de solo (AASHTO)") \
                        .props("outlined dense").classes("w-64")

                    def _upd_solo(e):
                        s["k0"] = e3.k_de_solo(e.value)
                        s["cbr_val"] = None
                        _rotulo.text = f"k0 do subleito ≈ {s['k0']:.0f} MPa/m"

                    sel.on_value_change(_upd_solo)
                    s["k0"] = e3.k_de_solo(sel.value)
                    s["cbr_val"] = None
                else:
                    k0_in = ui.number(
                        "k0 do subleito (MPa/m)", value=float(s.get("k0") or 50.0),
                        min=20.0, max=150.0, step=5.0,
                    ).props("outlined dense").classes("w-64")

                    def _upd_k0(e):
                        s["k0"] = e.value
                        s["cbr_val"] = None
                        _rotulo.text = f"k0 do subleito ≈ {s['k0']:.0f} MPa/m"

                    k0_in.on_value_change(_upd_k0)
                    s["k0"] = k0_in.value
                    s["cbr_val"] = None
                _rotulo = ui.label(f"k0 do subleito ≈ {s.get('k0', 50):.0f} MPa/m") \
                    .classes("text-sm font-semibold mt-1")

        metodo.on_value_change(lambda _: _rebuild())
        _rebuild()
    return True


# ---------------------------------------------------------------
# ETAPA - Sub-base
# ---------------------------------------------------------------
def render_subbase(s: dict, refresh) -> bool:
    with ui.column().classes("w-full max-w-3xl mx-auto cartao p-8 gap-3 aparecer"):
        ung.pergunta("Qual sub-base sobre o subleito?",
                    "A sub-base eleva o coeficiente de recalque k e reduz a erosão.")
        sub = s.get("subleito")
        solo_nome = sub.ordem_sibcs.title() if sub and getattr(sub, "ordem_sibcs", None) else None
        if solo_nome:
            ui.label(f"Subleito detectado: {solo_nome} · CBR≈{sub.cbr_estimado} · "
                     f"k0 ≈ {s.get('k0', 50):.0f} MPa/m").classes("text-xs text-slate-500")

        # pre-selecao pelo local (modos rodovia/local): tipo RECOMENDADO por
        # trafego (N estimado) + subleito (k0) — sugestao, sempre editavel
        rec_sb = None
        modo_proj = s.get("modo_projeto", "rodovia")
        if modo_proj in ("rodovia", "local") and s.get("k0"):
            n_est = _n_estimado(s)
            if n_est:
                rec_sb = rsb.recomendar(n_est, s.get("k0", 50.0))
                if not s.get("sb_prefill_feita"):
                    s["tipo_sb"] = rec_sb.tipo_recomendado
                    s["sb_prefill_feita"] = True

        opcoes = {t: (f"Sem sub-base (sobre {solo_nome})" if t == "Sem sub-base" and solo_nome else t)
                  for t in e3.TIPOS_SUBBASE}
        tipo_sel = ui.select(opcoes, value=s.get("tipo_sb", "Sem sub-base"),
                             label="Tipo de sub-base").props("outlined dense").classes("w-80")

        sugestao = ui.label("").classes("text-xs text-amber-700 bg-amber-50 rounded-lg p-2")

        def _upd_sugestao():
            if rec_sb is None:
                sugestao.set_visibility(False)
                return
            origem = "pela rodovia escolhida" if modo_proj == "rodovia" else "pela localização"
            if tipo_sel.value == rec_sb.tipo_recomendado:
                sugestao.text = (f"💡 Pré-selecionada {origem}: {rec_sb.tipo_recomendado} — "
                                 f"tráfego {rec_sb.nivel_trafego} + subleito {rec_sb.nivel_subleito} "
                                 f"(k0 ≈ {s.get('k0', 50):.0f} MPa/m). Ajuste se quiser.")
            else:
                sugestao.text = (f"Sugerida {origem}: {rec_sb.tipo_recomendado} "
                                 f"(tráfego {rec_sb.nivel_trafego} + subleito "
                                 f"{rec_sb.nivel_subleito}) — você escolheu outra, sem problema.")
            sugestao.set_visibility(True)

        esp_row = ui.column().classes("w-full")
        resumo = ui.label("").classes("text-green-700 font-semibold mt-1")
        aviso = ui.label("").classes("text-xs text-amber-700")

        def _recalc():
            tipo = tipo_sel.value
            esp = 0.0
            esp_row.clear()
            if e3.TIPOS_SUBBASE[tipo] is not None:
                # espessura herdada de "Sem sub-base" e 0: usar 15 cm (padrao)
                if not s.get("esp_sb") or s["esp_sb"] < 10:
                    s["esp_sb"] = 15
                with esp_row:
                    esp_slider = ui.slider(min=10, max=30, step=1, value=s.get("esp_sb", 15)) \
                        .props("label-always").classes("w-80 mt-10")
                    esp_lbl = ui.label(f"{esp_slider.value:.0f} cm").classes("text-sm")

                    def _upd(e):
                        s["esp_sb"] = e.value
                        esp_lbl.text = f"{e.value:.0f} cm"
                        _recalc_valores()

                    esp_slider.on_value_change(_upd)
                esp = s.get("esp_sb", 15)
            s["tipo_sb"] = tipo
            s["esp_sb"] = esp
            _upd_sugestao()
            _recalc_valores()

        def _recalc_valores():
            k0 = s.get("k0", 50.0)
            k = e3.k_efetivo(k0, s["tipo_sb"], s.get("esp_sb", 0.0))
            s["k_efetivo"] = k
            resumo.text = f"k efetivo (topo da sub-base) = {k:.0f} MPa/m"
            aviso.text = "⚠️ Limitado a 150 MPa/m (recomendação IPR-714)." if k >= e3.K_MAX_TOPO_SUBBASE else ""

        tipo_sel.on_value_change(lambda _: _recalc())
        _recalc()
    return True


# ---------------------------------------------------------------
# ETAPA - Trafego
# ---------------------------------------------------------------
_EIXO = {"simples": c.TipoEixo.SIMPLES, "tandem_duplo": c.TipoEixo.TANDEM_DUPLO,
         "tandem_triplo": c.TipoEixo.TANDEM_TRIPLO}
_EIXO_LABEL = {"simples": "Simples", "tandem_duplo": "Tandem duplo", "tandem_triplo": "Tandem triplo"}


def _rotulo_eixo(faixa: c.FaixaCarga) -> str:
    """
    Rotulo do eixo p/ exibicao — distingue eixo simples DIANTEIRO (direcional,
    rodagem simples, ate ~6,5tf) de TRASEIRO (rodagem dupla, >6,5tf), pedido
    da orientadora (23/08/2026, Bloco A): "sinalizar eixos simples traseiro E
    dianteiro". O calculo (calculos.py) ja trata os dois como faixas
    SEPARADAS do espectro (cargas diferentes = FaixaCarga diferentes) — isso
    so melhora o RÓTULO, nao muda o resultado numerico.
    """
    if faixa.eixo == c.TipoEixo.SIMPLES:
        # limite legal: 6,0tf direcional (dianteiro) / 10,0tf rodagem dupla
        # (traseiro) -- ver veiculos_dnit.CM_ES_DIRECIONAL/CM_ESRD. Corte no
        # meio do caminho (6,5tf) para tambem classificar cargas intermediarias
        # (ex.: contagem classificatoria real, nao so o limite legal exato).
        return "Simples dianteiro" if faixa.carga_tf <= 6.5 else "Simples traseiro"
    return _EIXO_LABEL.get(faixa.eixo.value, faixa.eixo.value)


def _trafego_comum(s: dict, refresh, vmda: float) -> bool:
    with ui.row().classes("w-full gap-4"):
        perfil_sel = ui.select({k: v.nome for k, v in pt.PERFIS.items()},
                               value=s.get("perfil", "rodovia"),
                               label="Perfil de composição da frota").props("outlined dense").classes("flex-1")
        periodo_in = ui.number("Período de projeto (anos)", value=s.get("periodo", 20),
                               min=5, max=40, step=1).props("outlined dense").classes("w-48")

    with ui.expansion("Parâmetros avançados (crescimento, fatores)").classes("w-full"):
        with ui.row().classes("w-full gap-4"):
            cresc_in = ui.number("Crescimento (%/ano)", value=s.get("cresc", 3.0),
                                 min=0.0, max=10.0, step=0.5).props("outlined dense").classes("w-40")
            fsent_in = ui.number("Fator de sentido", value=s.get("fsent", 0.5),
                                 min=0.3, max=1.0, step=0.05).props("outlined dense").classes("w-40")
            ffaixa_in = ui.number("Fator de faixa", value=s.get("ffaixa", 1.0),
                                  min=0.3, max=1.0, step=0.05).props("outlined dense").classes("w-40")
            fcarga_in = ui.number("Fator de carga (% do limite legal)",
                                  value=s.get("fcarga", 100.0),
                                  min=30.0, max=100.0, step=5.0).props("outlined dense").classes("w-56")
        ui.label("Fator de carga: quanto os eixos realmente carregam em relação ao limite "
                 "legal (6/10/17/25,5 tf). Sem pesquisa de carga (posto de pesagem) do "
                 "trecho, mantenha 100% (conservador). Se tiver uma contagem "
                 "classificatória real, edite a tabela abaixo diretamente — ela entra "
                 "100% no dimensionamento, sem passar por este fator.") \
            .classes("text-xs text-slate-400")

    caption = ui.label("").classes("text-xs text-slate-500")
    grid = ui.aggrid({
        "columnDefs": [
            {"field": "tipo", "headerName": "Tipo de eixo", "editable": True,
             "cellEditor": "agSelectCellEditor",
             "cellEditorParams": {"values": list(_EIXO)}},
            {"field": "carga_tf", "headerName": "Carga (tf)", "editable": True, "type": "numericColumn"},
            {"field": "repeticoes", "headerName": "Repetições", "editable": True, "type": "numericColumn"},
        ],
        "rowData": [],
        "domLayout": "autoHeight",
    }).classes("w-full")
    total_lbl = ui.label("").classes("text-sm mt-1")
    btns = ui.row().classes("gap-2 mt-1")
    with btns:
        ui.button("+ linha", on_click=lambda: _add_row()).props("outline dense size=sm")

    def _add_row():
        rows = grid.options["rowData"]
        rows.append({"tipo": "simples", "carga_tf": 10.0, "repeticoes": 0})
        grid.update()
        _sync()

    def _gerar_base():
        esp_ger = pt.espectro_de_projeto(pt.PERFIS[perfil_sel.value], float(vmda), int(periodo_in.value),
                                         fsent_in.value, ffaixa_in.value, cresc_in.value / 100.0,
                                         fcarga_in.value / 100.0)
        grid.options["rowData"] = [
            {"tipo": f.eixo.value, "carga_tf": round(f.carga_tf, 2), "repeticoes": round(f.repeticoes_previstas)}
            for f in esp_ger]
        grid.update()
        caption.text = (f"{pt.PERFIS[perfil_sel.value].descricao} · eixos via Manual IPR-723 (Fig.13). "
                       "Edite a tabela abaixo se quiser ajustar eixo a eixo.")
        _sync()

    def _sync():
        rows = grid.options["rowData"]
        espectro = [c.FaixaCarga(_EIXO[r["tipo"]], float(r["carga_tf"]), float(r["repeticoes"]))
                    for r in rows if r.get("carga_tf") is not None and r.get("repeticoes") is not None]
        s["espectro"] = espectro
        s["n_pesados"] = sum(f.repeticoes_previstas for f in espectro)
        s["periodo"] = periodo_in.value
        s["perfil"] = perfil_sel.value
        s["cresc"] = cresc_in.value
        s["fsent"] = fsent_in.value
        s["ffaixa"] = ffaixa_in.value
        s["fcarga"] = fcarga_in.value
        s["vmda"] = vmda
        total_lbl.text = f"Total de eixos solicitantes: {s['n_pesados']:,.0f}".replace(",", ".")

    def _on_cell_changed(e):
        args = e.args
        rows = grid.options["rowData"]
        row_id = args.get("rowIndex")
        field = args.get("colId")
        val = args.get("newValue")
        if row_id is not None and 0 <= row_id < len(rows):
            try:
                rows[row_id][field] = (val if field == "tipo" else float(val))
            except (TypeError, ValueError):
                pass
        _sync()

    grid.on("cellValueChanged", _on_cell_changed)
    for w in (perfil_sel, periodo_in, cresc_in, fsent_in, ffaixa_in, fcarga_in):
        w.on_value_change(lambda _: _gerar_base())

    _gerar_base()
    return len(s.get("espectro") or []) > 0


def render_trafego(s: dict, refresh) -> bool:
    with ui.column().classes("w-full max-w-3xl mx-auto cartao p-8 gap-3 aparecer"):
        modo_proj = s.get("modo_projeto", "rodovia")
        if modo_proj == "rodovia" and s.get("posto_sel"):
            sel = s["posto_sel"]
            ung.pergunta("Confirme o tráfego do trecho",
                        "O volume veio do posto escolhido no início — ajuste a "
                        "composição e o período abaixo, se quiser.")
            ui.label(f"VMDa {sel['vmda']:,} veíc/dia — BR-{sel['br']:03d} ({sel['lugar']}), "
                     f"PNCT/DNIT {pnct.ANO_BASE}".replace(",", ".")).classes("text-green-700 font-semibold")
            ui.label("💡 Pré-definido pela rodovia escolhida no início.").classes("text-xs text-amber-700")
            return _trafego_comum(s, refresh, sel["vmda"])

        # ENXUGAMENTO/Bloco A (23/08/2026, pedido da orientadora): o posto do
        # PNCT so deveria ser sugerido quando NAO ha dado do local, e por
        # ultimo na hierarquia -- nao como opcao padrao. "Digitar" (que cobre
        # tanto VMDa estimado quanto CONTAGEM CLASSIFICATORIA real, editando
        # a tabela abaixo) passou a ser a opcao 1 e o default; o posto PNCT
        # virou a opcao 2, rotulada explicitamente como recurso de ultimo caso.
        ung.pergunta("Quanto tráfego pesado a via recebe?",
                    "Informe o VMDa (ou uma contagem classificatória real, editando a "
                    "tabela abaixo). Só use o posto do PNCT/DNIT se não tiver dado do "
                    "trecho.")
        modo_traf = ui.toggle(["✏️ Digitar (VMDa ou contagem real)",
                               "📍 Sem dado do local: usar posto do PNCT"],
                              value=s.get("traf_modo_lbl", "✏️ Digitar (VMDa ou contagem real)"))
        corpo = ui.column().classes("w-full gap-2")

        def _rebuild():
            s["traf_modo_lbl"] = modo_traf.value
            corpo.clear()
            with corpo:
                if modo_traf.value.startswith("📍"):
                    postos = _postos()
                    if not postos:
                        ui.label("Postos do PNCT indisponíveis. Escolha Digitar manualmente.") \
                            .classes("text-red-600")
                        return
                    if "posto_sel" not in s and s.get("ponto_obra"):
                        s["posto_sel"] = _posto_mais_proximo(s["ponto_obra"][0], s["ponto_obra"][1], postos)

                    def _clique(lat, lon):
                        p = _posto_mais_proximo(lat, lon, postos)
                        if p and _haversine(lat, lon, p["lat"], p["lon"]) > 40.0:
                            ui.notify("Área fora do RJ (região cinza) — clique num "
                                      "marcador de rodovia dentro do estado.", type="warning")
                            return
                        if p and s.get("posto_sel") != p:
                            s["posto_sel"] = p
                            refresh()

                    sel = s.get("posto_sel")
                    marcadores = [(p["lat"], p["lon"], "orange",
                                  f"BR-{p['br']:03d} · {p['lugar']} · VMDa {p['vmda']:,}".replace(",", "."))
                                  for p in postos if p is not sel]
                    pop = (f"<b>📍 BR-{sel['br']:03d}</b><br>{sel['lugar']}<br>"
                           f"VMDa <b>{sel['vmda']:,}</b> veíc/dia".replace(",", ".")) if sel else None
                    mapa_rj(marcadores=marcadores,
                            selecionado=(sel["lat"], sel["lon"], pop) if sel else None,
                            center=(sel["lat"], sel["lon"]) if sel else (-22.2, -42.8),
                            zoom=8 if sel else 7,
                            on_click=_clique)
                    sel = s.get("posto_sel")
                    if not sel:
                        ui.label("Clique perto de um pino para escolher o posto.").classes("text-slate-500")
                        return
                    ui.label(f"Posto: BR-{sel['br']:03d} ({sel['lugar']}) · VMDa {sel['vmda']:,} veíc/dia "
                             f"· PNCT/DNIT {pnct.ANO_BASE}".replace(",", ".")).classes("text-green-700 font-semibold")
                    _trafego_comum(s, refresh, sel["vmda"])
                else:
                    vmda_in = ui.number("VMDa (veíc/dia)", value=s.get("vmda_man", 8000),
                                       min=100, max=300_000, step=100).props("outlined dense").classes("w-56")
                    ui.label("Tem uma contagem classificatória real do trecho (feita antes de "
                             "pavimentar)? Prefira editar a tabela de eixos diretamente, faixa "
                             "a faixa, abaixo — ela entra 100% no dimensionamento, sem passar "
                             "pelo perfil-tipo nem pelo fator de carga.").classes("text-xs text-slate-400")

                    def _upd(e):
                        s["vmda_man"] = e.value
                        refresh()

                    vmda_in.on_value_change(_upd)
                    _trafego_comum(s, refresh, vmda_in.value)

        modo_traf.on_value_change(lambda _: _rebuild())
        _rebuild()
    return len(s.get("espectro") or []) > 0


# ---------------------------------------------------------------
# ETAPA - Viabilidade: 1 criterio por tela
# ---------------------------------------------------------------
_CRIT_ORDEM = ("traf", "vida", "cbr", "manut", "clima", "usina")
_CRIT_TITULO = {
    "traf": "Quanto tráfego pesado a via terá?",
    "vida": "Por quantos anos o pavimento deve durar?",
    "cbr": "Como é o subleito da região?",
    "manut": "Como será a manutenção futura da via?",
    "clima": "Quanto chove na região?",
    "usina": "Há usina de concreto acessível?",
}
_CRIT_AJUDA = {
    "traf": "Tráfego pesado intenso favorece o rígido: a placa distribui a carga e não "
            "sofre afundamento de trilha de roda. Peso 3 no score.",
    "vida": "O rígido se paga em horizontes longos (20–30 anos) pela baixa manutenção. Peso 2.",
    "cbr": "Subleito fraco penaliza menos o rígido do que o flexível — a placa vence o vão. Peso 2.",
    "manut": "Se interditar a via para manutenção frequente é difícil ou caro, o rígido leva "
             "vantagem. Peso 2.",
    "clima": "Chuva alta degrada mais o asfalto (bombeamento de finos, desagregação). Peso 2.",
    "usina": "Distância à usina de concreto encarece o transporte do material. Peso 1.",
}


def render_criterio(k: str, idx: int):
    def render(s: dict, refresh) -> bool:
        rot, fmt, _peso = tri.PERGUNTAS[k]
        with ui.column().classes("w-full max-w-3xl mx-auto cartao p-8 gap-3 aparecer"):
            ui.label(f"CRITÉRIO {idx} DE {len(_CRIT_ORDEM)}") \
                .classes("text-[.68rem] font-bold tracking-widest rounded-full "
                         "bg-amber-50 px-3 py-1 w-fit").style(f"color:{ung.AMBAR_ESC}")
            ung.pergunta(_CRIT_TITULO[k], _CRIT_AJUDA[k])
            opts = list(fmt.keys())
            s.setdefault(f"tri_{k}", opts[len(opts) // 2])

            def _set(v):
                s[f"tri_{k}"] = v
                refresh()

            for v in opts:
                ativo = s[f"tri_{k}"] == v
                with ui.row().classes(
                    "w-full items-center gap-3 px-4 py-3 rounded-xl cursor-pointer "
                    "border transition"
                ).style(f"border-color:{'#C8861F' if ativo else '#EDF0F2'};"
                        f"background:{'#FDF3E2' if ativo else '#fff'}") \
                        .on("click", lambda _, v=v: _set(v)):
                    ui.icon("radio_button_checked" if ativo else "radio_button_unchecked") \
                        .classes("text-2xl") \
                        .style(f"color:{'#C8861F' if ativo else '#CBD5E1'}")
                    ui.label(fmt[v]).classes(
                        "text-lg font-bold" if ativo else "text-lg text-slate-500") \
                        .style(f"color:{ung.TEXTO}" if ativo else "")
            fonte = (s.get("tri_fonte") or {}).get(k)
            if fonte and s.get("modo_projeto") in ("rodovia", "local"):
                origem = ("pela rodovia escolhida" if s.get("modo_projeto") == "rodovia" else "pela localização")
                ui.label(f"💡 Valor pré-definido {origem}: {fonte}. Ajuste acima se tiver dado melhor.") \
                    .classes("text-xs text-amber-700 bg-amber-50 rounded-lg p-2 mt-1")
        return True
    return render


def render_triagem_resumo(s: dict, refresh) -> bool:
    with ui.column().classes("w-full max-w-3xl mx-auto cartao p-8 gap-3 aparecer"):
        ung.pergunta("Vale a pena usar pavimento rígido?",
                    "Resultado da triagem — orientativo: você pode prosseguir para o "
                    "dimensionamento de qualquer forma.")
        vals = {k: s.get(f"tri_{k}", 1) for k in _CRIT_ORDEM}
        sc = tri.score(vals)
        s["triagem_score"] = sc
        emoji, _nivel, texto = tri.recomendacao(sc)
        pct = 100 * sc / tri.SCORE_MAX
        ui.label(f"{emoji} Score {sc}/{tri.SCORE_MAX} ({pct:.0f}%)").classes("text-xl font-extrabold")
        cor = "positive" if pct >= 70 else "warning" if pct >= 40 else "negative"
        ui.label(texto).classes(f"text-{cor}-8 font-semibold" if cor != "warning" else "text-amber-700 font-semibold")
        fontes = s.get("tri_fonte") or {}
        rows = [{"Critério": tri.PERGUNTAS[k][0], "Resposta": tri.PERGUNTAS[k][1][vals[k]],
                "Peso": tri.PESOS[k],
                "Origem": ("automática (local)" if k in fontes and s.get("modo_projeto") in ("rodovia", "local")
                           else "manual")} for k in _CRIT_ORDEM]
        ui.table(columns=[{"name": k, "label": k, "field": k} for k in rows[0]],
                 rows=rows, row_key="Critério").classes("w-full").props("flat dense")
    return True


# ---------------------------------------------------------------
# ETAPA - Concreto
# ---------------------------------------------------------------
def render_concreto(s: dict, refresh) -> bool:
    # ENXUGAMENTO (23/08/2026, pedido da orientadora): fctk fixo (4,8 MPa, o
    # mesmo valor do exemplo do manual) e FSC automatico pelo volume de
    # trafego (Quadro 9) -- deixaram de ser campos editaveis. Historico do
    # comportamento anterior (campos ui.number com os defaults e ranges) fica
    # no git, commit "Corrige modelo de erosao...", caso precise reverter.
    n_total = sum(f.repeticoes_previstas for f in (s.get("espectro") or []))
    fsc_auto = c.fsc_automatico(n_total)
    with ui.column().classes("w-full max-w-3xl mx-auto cartao p-8 gap-3 aparecer"):
        ung.pergunta("Como será o concreto da placa?",
                    "Acostamento e barras mudam as tabelas do método.")
        with ui.row().classes("w-full gap-10"):
            with ui.column().classes("gap-1"):
                ui.label("Acostamento de concreto").classes("text-base font-bold") \
                    .style(f"color:{ung.TEXTO}")
                acost = ui.toggle(["Sem", "Com"], value=s.get("acost", "Sem")) \
                    .props("no-caps toggle-color=amber-8 size=lg")
            with ui.column().classes("gap-1"):
                ui.label("Barras de transferência").classes("text-base font-bold") \
                    .style(f"color:{ung.TEXTO}")
                barras = ui.toggle(["Sem", "Com"], value=s.get("barras", "Sem")) \
                    .props("no-caps toggle-color=amber-8 size=lg")
        ui.label(f"fctk = {c.FCTK_PADRAO_MPA:.1f} MPa (NBR 12142, 28 dias — valor do exemplo "
                 f"do IPR-714) · FSC = {fsc_auto:.1f} automático pelo volume de tráfego "
                 f"previsto ({n_total:,.0f} repetições — Quadro 9 IPR-714)".replace(",", ".")) \
            .classes("text-xs text-slate-400")

        def _sync():
            s["acost"] = acost.value
            s["barras"] = barras.value
            s["fctk"] = c.FCTK_PADRAO_MPA
            s["fsc"] = c.fsc_automatico(
                sum(f.repeticoes_previstas for f in (s.get("espectro") or [])))

        for w in (acost, barras):
            w.on_value_change(lambda _: _sync())
        _sync()
    return True


# ---------------------------------------------------------------
# Helpers da memoria de calculo (MathJax)
# ---------------------------------------------------------------
def _v(x, dec=2):
    return f"{x:.{dec}f}".replace(".", ",")


def _milhar(n):
    """Inteiro com ponto de milhar (5.099.997), sem mexer na virgula decimal."""
    return f"{n:,.0f}".replace(",", ".")


def _virgula_tex(html):
    """Dentro das formulas \\[...\\], troca 0,563 por 0{,}563: no TeX a virgula
    vira pontuacao e ganha espaco depois ('0, 563'); entre chaves, nao."""
    return re.sub(r"\\\[(.*?)\\\]",
                  lambda m: re.sub(r"(\d),(\d)", r"\1{,}\2", m.group(0)),
                  html, flags=re.S)


def _bignum(n):
    if n >= 1e19:
        return r"\text{ilimitado}"
    if n >= 1e5:
        e = int(math.floor(math.log10(n)))
        m = n / 10 ** e
        return rf"{_v(m, 2)}\times10^{{{e}}}"
    return f"{n:,.0f}".replace(",", ".")


def _param_do_estado(s: dict) -> c.ParametrosProjeto:
    return c.ParametrosProjeto(
        fctk_mpa=c.FCTK_PADRAO_MPA, k_mpa_m=s.get("k_efetivo", 50.0),
        fsc=s.get("fsc") or c.fsc_automatico(
            sum(f.repeticoes_previstas for f in (s.get("espectro") or []))),
        acostamento=(c.TipoAcostamento.COM_CONCRETO if s.get("acost") == "Com"
                     else c.TipoAcostamento.SEM_CONCRETO),
        com_barras_transferencia=(s.get("barras") == "Com"),
        espectro=s.get("espectro") or [])


# Nome dos quadros do IPR-714, por identidade da tabela (p/ citar a fonte na memoria)
_NOME_QUADRO = {
    id(tabp.Q12_ES_ETD_PSAC): "Quadro 12 — σ_eq ES/ETD, sem acostamento",
    id(tabp.Q13_ETT_PSAC): "Quadro 13 — σ_eq ETT, sem acostamento",
    id(tabp.Q14_ES_ETD_PCAC): "Quadro 14 — σ_eq ES/ETD, com acostamento",
    id(tabp.Q15_ETT_PCAC): "Quadro 15 — σ_eq ETT, com acostamento",
    id(tabp.Q16_ES_ETD_JSP_PSAC): "Quadro 16 — FE ES/ETD, sem barras, sem acostamento",
    id(tabp.Q17_ETT_JSP_PSAC): "Quadro 17 — FE ETT, sem barras, sem acostamento",
    id(tabp.Q18_ES_ETD_JSP_PCAC): "Quadro 18 — FE ES/ETD, sem barras, com acostamento",
    id(tabp.Q19_ETT_JSP_PCAC): "Quadro 19 — FE ETT, sem barras, com acostamento",
    id(tabp.Q20_ES_ETD_JCP_PSAC): "Quadro 20 — FE ES/ETD, com barras, sem acostamento",
    id(tabp.Q21_ETT_JCP_PSAC): "Quadro 21 — FE ETT, com barras, sem acostamento",
    id(tabp.Q22_ES_ETD_JCP_PCAC): "Quadro 22 — FE ES/ETD, com barras, com acostamento",
    id(tabp.Q23_ETT_JCP_PCAC): "Quadro 23 — FE ETT, com barras, com acostamento",
}


def _interp_html(det: dict, simbolo: str, h_cm: float, k: float, dec: int = 3) -> str:
    """Demonstra a interpolacao bilinear: 4 cantos da tabela + as 3 contas."""
    exato_h = det["h1"] == det["h2"]
    exato_k = det["k1"] == det["k2"]
    linhas = [
        f"<p class='text-xs' style='color:#64748b'>Células vizinhas da tabela "
        f"(h em cm × k em MPa/m):</p>",
        "<table style='border-collapse:collapse;font-size:0.8rem;margin:2px 0 6px 12px'>"
        f"<tr><td style='padding:2px 10px'></td>"
        f"<td style='padding:2px 10px'><b>k={det['k1']:g}</b></td>"
        f"<td style='padding:2px 10px'><b>k={det['k2']:g}</b></td></tr>"
        f"<tr><td style='padding:2px 10px'><b>h={det['h1']:g}</b></td>"
        f"<td style='padding:2px 10px'>{_v(det['v11'], dec)}</td>"
        f"<td style='padding:2px 10px'>{_v(det['v12'], dec)}</td></tr>"
        f"<tr><td style='padding:2px 10px'><b>h={det['h2']:g}</b></td>"
        f"<td style='padding:2px 10px'>{_v(det['v21'], dec)}</td>"
        f"<td style='padding:2px 10px'>{_v(det['v22'], dec)}</td></tr></table>",
    ]
    if exato_h and exato_k:
        linhas.append(rf"\[{simbolo} = {_v(det['valor'], dec)}\ \text{{(valor direto da tabela)}}\]")
        return "".join(linhas)
    if not exato_k:
        linhas.append(
            rf"\[{simbolo}(h{{=}}{det['h1']:g}) = {_v(det['v11'], dec)} + "
            rf"\tfrac{{{k:g}-{det['k1']:g}}}{{{det['k2']:g}-{det['k1']:g}}}"
            rf"\,({_v(det['v12'], dec)} - {_v(det['v11'], dec)}) = {_v(det['vh1'], dec)}\]")
        if not exato_h:
            linhas.append(
                rf"\[{simbolo}(h{{=}}{det['h2']:g}) = {_v(det['v21'], dec)} + "
                rf"{_v(det['tk'], 3)}\,({_v(det['v22'], dec)} - {_v(det['v21'], dec)})"
                rf" = {_v(det['vh2'], dec)}\]")
    if not exato_h:
        linhas.append(
            rf"\[{simbolo} = {_v(det['vh1'], dec)} + "
            rf"\tfrac{{{h_cm:g}-{det['h1']:g}}}{{{det['h2']:g}-{det['h1']:g}}}"
            rf"\,({_v(det['vh2'], dec)} - {_v(det['vh1'], dec)}) = {_v(det['valor'], dec)}\]")
    else:
        linhas.append(rf"\[{simbolo} = {_v(det['valor'], dec)}\]")
    return "".join(linhas)


def _memoria_faixa_html(d, p: c.ParametrosProjeto, h_cm: float) -> str:
    fsc = p.fsc
    triplo = d.faixa.eixo == c.TipoEixo.TANDEM_TRIPLO
    extra = r"\,/\,3" if triplo else ""
    partes = [
        f"<p><b>1. Carga efetiva</b> (carga × FSC{', tandem triplo ÷3' if triplo else ''}):</p>",
        rf"\[P_{{ef}} = {_v(d.faixa.carga_tf)} \times {_v(fsc)}{extra} = {_v(d.carga_efetiva)}\ \text{{tf}}\]",
    ]

    # --- 2. Tensao equivalente: quadro usado + interpolacao demonstrada ---
    tbl_t, kx_t, col_t = c._TENSAO[(p.acostamento, d.faixa.eixo)]
    det_t = tabp.consultar_detalhado(tbl_t, kx_t, h_cm, p.k_mpa_m, col_t)
    partes += [
        f"<p><b>2. Tensão equivalente</b> — {_NOME_QUADRO.get(id(tbl_t), 'Quadros 12–15')} "
        f"(IPR-714), interpolação bilinear em h = {_v(h_cm, 1)} cm, "
        f"k = {p.k_mpa_m:g} MPa/m:</p>",
        _interp_html(det_t, r"\sigma_{eq}", h_cm, p.k_mpa_m),
        rf"\[\boxed{{\sigma_{{eq}} = {_v(d.sigma_eq, 3)}\ \text{{MPa}}}}\]",
        "<p><b>3. Relação de tensões</b> (a tensão tabelada vale para o eixo-padrão "
        f"de {_v(d.carga_padrao)} tf; escala com a carga elevada a 0,94 — IPR-714 §4.6.2.3.3):</p>",
        rf"\[SR = \frac{{\sigma_{{eq}}}}{{f_{{ctk}}}}\left(\frac{{P_{{ef}}}}{{P_{{pad}}}}\right)^{{0{{,}}94}}"
        rf" = \frac{{{_v(d.sigma_eq, 3)}}}{{{_v(d.mr)}}}"
        rf"\left(\frac{{{_v(d.carga_efetiva)}}}{{{_v(d.carga_padrao)}}}\right)^{{0{{,}}94}} = {_v(d.sr, 3)}\]",
        "<p><b>4. Repetições admissíveis — fadiga</b> (equações PCA, ábaco da Fig. 27):</p>",
    ]
    if d.n_adm_fadiga >= 1e19:
        partes.append(rf"\[SR = {_v(d.sr, 3)} < 0{{,}}45 \Rightarrow N_f = \text{{ilimitado}}\]")
    elif d.sr < 0.55:
        partes.append(
            rf"\[0{{,}}45 \le SR < 0{{,}}55 \Rightarrow "
            rf"N_f = \left(\frac{{4{{,}}2577}}{{SR - 0{{,}}4325}}\right)^{{3{{,}}268}}"
            rf" = \left(\frac{{4{{,}}2577}}{{{_v(d.sr, 3)} - 0{{,}}4325}}\right)^{{3{{,}}268}}"
            rf" = {_bignum(d.n_adm_fadiga)}\]")
    else:
        partes.append(
            rf"\[SR \ge 0{{,}}55 \Rightarrow \log_{{10}} N_f = 11{{,}}737 - 12{{,}}077\times{_v(d.sr, 3)}"
            rf" = {_v(11.737 - 12.077 * d.sr, 3)} \Rightarrow N_f = {_bignum(d.n_adm_fadiga)}\]")
    partes += [
        "<p><b>5. Consumo de fadiga:</b></p>",
        rf"\[CF = \frac{{N_{{prev}}}}{{N_f}}\times 100 = "
        rf"\frac{{{_bignum(d.faixa.repeticoes_previstas)}}}{{{_bignum(d.n_adm_fadiga)}}}"
        rf"\times 100 = {_v(d.consumo_fadiga_pct)}\%\]",
    ]

    # --- 6. Erosao: quadro usado + interpolacao + equacao de Packard por extenso ---
    tbl_e, kx_e, col_e = c._EROSAO[(p.acostamento, p.com_barras_transferencia, d.faixa.eixo)]
    det_e = tabp.consultar_detalhado(tbl_e, kx_e, h_cm, p.k_mpa_m, col_e)
    partes += [
        f"<p><b>6. Fator de erosão</b> — {_NOME_QUADRO.get(id(tbl_e), 'Quadros 16–23')} "
        f"(IPR-714), mesma interpolação bilinear:</p>",
        _interp_html(det_e, "FE", h_cm, p.k_mpa_m, dec=2),
        rf"\[\boxed{{FE = {_v(d.fator_erosao, 3)}}}\]",
        "<p><b>7. Repetições admissíveis — erosão</b> (leitura direta da "
        "Figura 28/29 digitalizada — nomograma de 3 escalas: carga | fator de "
        "erosão | N admissível; a reta que liga carga e FE é estendida até a "
        "escala de N):</p>",
    ]
    com_ac = p.acostamento == c.TipoAcostamento.COM_CONCRETO
    nomo = c._NOMO[p.acostamento]
    divisor = c._CARGA_DIVISOR_EROSAO[d.faixa.eixo]
    carga_equiv = min(max(d.carga_efetiva / divisor, nomo["carga_min"]), nomo["carga_max"])
    ef = min(max(d.fator_erosao, nomo["ef_min"]), nomo["ef_max"])
    p1 = nomo["a1"] + nomo["b1"] * math.log(carga_equiv)
    p2 = nomo["a2"] + nomo["b2"] * ef
    p3 = p1 + (p2 - p1) * nomo["w"] + nomo["offset"]
    divisor_txt = "" if divisor == 1.0 else rf" \div {_v(divisor,0)}"
    fig = "28 (sem acostamento)" if not com_ac else "29 (com acostamento)"
    partes.append(
        rf"\[\text{{Figura {fig}}}\]"
        rf"\[P_{{ef}}{divisor_txt} = {_v(carga_equiv, 3)}\ \text{{tf (escala de carga)}}"
        rf" \qquad FE = {_v(ef, 3)}\ \text{{(escala do fator de erosão)}}\]"
        rf"\[\text{{reta carga}}\to\text{{FE, estendida até a escala de N}}"
        rf" \;(w={_v(nomo['w'],3)})\]")
    a3, b3, c3 = nomo["a3"], nomo["b3"], nomo["c3"]
    if c3 == 0.0:
        log_ne_calc = (p3 - a3) / b3
    else:
        disc = b3 * b3 - 4 * c3 * (a3 - p3)
        log_ne_calc = None if disc < 0 else max(
            (-b3 + disc ** 0.5) / (2 * c3), (-b3 - disc ** 0.5) / (2 * c3))
    if d.n_adm_erosao >= c.N_ILIMITADO:
        partes.append(
            rf"\[\text{{reta cruza acima do topo impresso da escala (10}}^8"
            rf"\text{{)}} \Rightarrow N_e = \text{{ilimitado}}\]")
    else:
        partes.append(
            rf"\[\log_{{10}} N_e \approx {_v(log_ne_calc, 3) if log_ne_calc else '-'}"
            rf" \Rightarrow N_e = {_bignum(d.n_adm_erosao)}\]")
    partes += [
        "<p><b>8. Consumo de erosão:</b></p>",
        rf"\[CE = \frac{{N_{{prev}}}}{{N_e}}\times 100 = "
        rf"\frac{{{_bignum(d.faixa.repeticoes_previstas)}}}{{{_bignum(d.n_adm_erosao)}}}"
        rf"\times 100 = {_v(d.consumo_erosao_pct)}\%\]",
    ]
    return _virgula_tex("".join(partes))


def _ir_para(s: dict, refresh, tela_id: str) -> None:
    """Pula direto p/ uma etapa da sequencia (ex.: corrigir apos falha de h)."""
    seq = s.get("_seq") or []
    if tela_id in seq:
        s["passo"] = seq.index(tela_id)
        refresh()
        ung.rolar_para_topo()


def _painel_falha_h(s: dict, refresh, p: c.ParametrosProjeto) -> None:
    """Quando nenhuma h <= H_MAX atende: mostra a CONTA na maior espessura
    (por que falha, qual criterio governa) + atalhos p/ refazer as etapas
    que alimentam o dimensionamento."""
    ui.label(f"Nenhuma espessura entre {c.H_MIN_CM:.0f} e {c.H_MAX_CM:.0f} cm "
             "atendeu aos critérios do PCA 1984.").classes("text-red-600 font-bold")
    ui.label(f"Esse é o intervalo coberto pelas tabelas do IPR-714 (Quadros 12 a 23). "
             f"Uma placa acima de {c.H_MAX_CM:.0f} cm estaria fora do domínio do método "
             "e não é calculada por extrapolação.").classes("text-sm text-slate-600")

    # diagnostico calculado NA PAGINA: verificacao na espessura maxima
    diag = c.verificar_espessura(c.H_MAX_CM, p)
    governa = "erosão" if diag.soma_erosao_pct > diag.soma_fadiga_pct else "fadiga"
    ui.label(f"Verificação na espessura máxima (h = {c.H_MAX_CM:.0f} cm):") \
        .classes("font-semibold mt-1")
    ung.barra_consumo("Consumo de fadiga", diag.soma_fadiga_pct)
    ung.barra_consumo("Consumo de erosão", diag.soma_erosao_pct)
    ui.label(f"O critério que governa a falha é a {governa}. Veja a conta por "
             "classe de eixo:").classes("text-sm text-slate-600")
    for d in diag.detalhes:
        rot = (f"{_rotulo_eixo(d.faixa)} · "
               f"{_v(d.faixa.carga_tf, 1)} tf · {_milhar(d.faixa.repeticoes_previstas)} rep. → "
               f"fadiga {_v(d.consumo_fadiga_pct)}% / erosão {_v(d.consumo_erosao_pct)}%")
        with ui.expansion(rot).classes("w-full"):
            ui.html(_memoria_faixa_html(d, p, c.H_MAX_CM))
    ung.mathjax_typeset()

    # atalhos: repetir as etapas que alimentam o dimensionamento
    ui.label("O que fazer? Ajuste uma das entradas e refaça a partir dela:") \
        .classes("font-semibold mt-2")
    sugestoes = [
        ("🧱 Sub-base / fundação", "subbase",
         "Sub-base cimentada (BGTC/CCR) eleva o k e reduz muito a erosão."),
        ("🏗️ Concreto da placa", "concreto",
         "Acostamento de concreto e barras de transferência reduzem a espessura "
         "necessária."),
        ("🚚 Tráfego", "trafego",
         "Confira as cargas e repetições do espectro — um exagero no N "
         "inviabiliza qualquer espessura."),
    ]
    with ui.column().classes("w-full gap-2"):
        for rotulo, tela_id, dica in sugestoes:
            with ui.row().classes("w-full items-center gap-3 p-2 rounded-xl border") \
                    .style("border-color:#EDF0F2"):
                ui.button(rotulo, on_click=lambda _, t=tela_id: _ir_para(s, refresh, t)) \
                    .props("outline no-caps rounded").classes("w-56")
                ui.label(dica).classes("text-xs text-slate-500")


def render_memoria(s: dict, refresh) -> bool:
    with ui.column().classes("w-full max-w-3xl mx-auto cartao p-8 gap-3 aparecer"):
        ung.pergunta("Memória de cálculo",
                    "Como a espessura é obtida, passo a passo — método PCA 1984 (DNIT IPR-714).")
        if not (s.get("espectro") or []):
            ui.label("Sem espectro de tráfego. Volte à etapa de Tráfego.").classes("text-amber-700")
            return True
        p = _param_do_estado(s)
        res = c.dimensionar(p)
        s["dim_param"] = p
        s["dim_resultado"] = res
        if res is None:
            _painel_falha_h(s, refresh, p)
            return True
        ac = s.get("acost", "Sem")
        ba = s.get("barras", "Sem")
        ui.label(f"Premissas: fctk = {_v(p.fctk_mpa, 1)} MPa · k = {p.k_mpa_m:.0f} MPa/m · "
                 f"FSC = {_v(p.fsc)} · acostamento {ac} · barras {ba}.").classes("text-sm")
        for aviso in getattr(res, "avisos", []):
            ui.label("⚠️ " + aviso).classes("text-xs text-amber-700")

        # --- 0. Fundacao: de onde vem o k do sistema ---
        if s.get("k0"):
            with ui.expansion("🏔️ 0. Fundação — como o k do sistema foi obtido").classes("w-full"):
                k0 = float(s.get("k0", 50.0))
                tipo_sb = s.get("tipo_sb", "Sem sub-base")
                esp_sb = s.get("esp_sb", 0)
                kef = float(s.get("k_efetivo", k0))
                html = [
                    f"<p><b>k0 do subleito</b> = {_v(k0, 0)} MPa/m "
                    "(CBR → k0 pela Figura 11 ou solo → k0 pelo Quadro 3 do IPR-714, "
                    "conforme escolhido na etapa Fundação).</p>",
                ]
                if tipo_sb and tipo_sb != "Sem sub-base":
                    html.append(
                        f"<p><b>Sub-base:</b> {tipo_sb}, {esp_sb:g} cm → interpolação "
                        "bilinear (k0 × espessura) no ábaco correspondente "
                        "(Figs. 18–21 do IPR-714):</p>"
                        rf"\[k_0 = {_v(k0, 0)} \xrightarrow{{\ \text{{{tipo_sb}, {esp_sb:g} cm}}\ }} "
                        rf"k_{{ef}} = {_v(kef, 0)}\ \text{{MPa/m}}\]")
                    if kef >= e3.K_MAX_TOPO_SUBBASE - 1e-9:
                        html.append("<p class='text-xs' style='color:#b45309'>k limitado ao teto "
                                    f"de {e3.K_MAX_TOPO_SUBBASE:g} MPa/m do IPR-714.</p>")
                else:
                    html.append(rf"<p>Sem sub-base → \(k_{{ef}} = k_0 = {_v(kef, 0)}\) MPa/m.</p>")
                ui.html("".join(html))

        # --- 0b. Espectro de trafego usado (com a majoracao pelo FSC) ---
        with ui.expansion(f"🚚 0b. Espectro de tráfego ({len(p.espectro)} faixas) e "
                          "majoração pelo FSC").classes("w-full"):
            ui.label(f"Cada carga do espectro é multiplicada pelo FSC = {_v(p.fsc)} "
                     "(Quadro 9); tandem triplo entra no ábaco de eixo simples com 1/3 da carga.") \
                .classes("text-xs text-slate-500")
            linhas_esp = []
            for fx in p.espectro:
                pef = c._carga_efetiva(fx, p.fsc)
                linhas_esp.append({
                    "eixo": _rotulo_eixo(fx),
                    "carga": _v(fx.carga_tf, 1),
                    "pef": _v(pef, 2),
                    "n": f"{fx.repeticoes_previstas:,.0f}".replace(",", "."),
                })
            ui.table(rows=linhas_esp, columns=[
                {"name": "eixo", "label": "Eixo", "field": "eixo", "align": "left"},
                {"name": "carga", "label": "Carga (tf)", "field": "carga"},
                {"name": "pef", "label": "P_ef = carga × FSC (tf)", "field": "pef"},
                {"name": "n", "label": "N previsto", "field": "n"},
            ], pagination=8).classes("w-full")

        ui.label(f"Critério: testa-se h de {c.H_MIN_CM:.0f} a {c.H_MAX_CM:.0f} cm (número inteiro, "
                 "intervalo das tabelas do IPR-714) e adota-se a menor espessura "
                 "cujo consumo de fadiga E de erosão fique ≤ 100%.").classes("text-sm text-slate-500")

        # --- Busca iterativa da espessura (o loop, demonstrado) ---
        with ui.expansion(f"🔁 Busca iterativa: h = {c.H_MIN_CM:g} → {res.h_cm:g} cm").classes("w-full"):
            ui.label("Cada linha é uma espessura-tentativa verificada contra o espectro "
                     "inteiro; a primeira que passa nos dois critérios é adotada.") \
                .classes("text-xs text-slate-500")
            linhas_h = []
            h_it = c.H_MIN_CM
            while h_it <= res.h_cm + 1e-9:
                r_it = c.verificar_espessura(h_it, p)
                linhas_h.append({
                    "h": _v(h_it, 1),
                    "cf": _v(r_it.soma_fadiga_pct, 1) + " %",
                    "ce": _v(r_it.soma_erosao_pct, 1) + " %",
                    "st": "✅ aprovada" if r_it.aprovada else
                          ("✗ erosão" if r_it.soma_erosao_pct > 100 else "✗ fadiga"),
                })
                h_it += c.H_PASSO_CM
            ui.table(rows=linhas_h, columns=[
                {"name": "h", "label": "h (cm)", "field": "h"},
                {"name": "cf", "label": "Σ fadiga", "field": "cf"},
                {"name": "ce", "label": "Σ erosão", "field": "ce"},
                {"name": "st", "label": "Verificação", "field": "st"},
            ], pagination=10).classes("w-full")

        ui.label(f"Espessura adotada: h = {res.h_cm:.1f} cm").classes("text-green-700 font-bold mt-1")
        ui.separator()
        ui.label(f"Verificação de h = {res.h_cm:.1f} cm, por classe de eixo — conta completa") \
            .classes("font-bold")
        ui.label("Abra cada faixa para ver TODAS as etapas: quadro consultado, interpolação "
                 "bilinear célula a célula, SR, equações de fadiga e de erosão com os valores "
                 "substituídos.").classes("text-xs text-slate-500")
        for d in res.detalhes:
            rot = (f"{_rotulo_eixo(d.faixa)} · {_v(d.faixa.carga_tf, 1)} tf · "
                   f"{_milhar(d.faixa.repeticoes_previstas)} rep. → fadiga {_v(d.consumo_fadiga_pct)}% / "
                   f"erosão {_v(d.consumo_erosao_pct)}%")
            with ui.expansion(rot).classes("w-full"):
                ui.html(_memoria_faixa_html(d, p, res.h_cm))
        ung.mathjax_typeset()
        ui.separator()
        ui.label(f"Somatório — fadiga: Σ CF = {_v(res.soma_fadiga_pct, 1)}% · "
                 f"erosão: Σ CE = {_v(res.soma_erosao_pct, 1)}%").classes("font-semibold")
        ok = res.soma_fadiga_pct <= 100 and res.soma_erosao_pct <= 100
        ui.label(f"Ambos os critérios {'≤' if ok else '>'} 100% → h = {res.h_cm:.1f} cm "
                 f"{'aprovada' if ok else 'reprovada'}.") \
            .classes("text-green-700 font-semibold" if ok else "text-red-600 font-semibold")
    return True


# ---------------------------------------------------------------
# ETAPA - Resultado
# ---------------------------------------------------------------
def _tornado_cached(fctk, k, fsc, acost_val, barras, espectro_t):
    key = ("tornado", fctk, k, fsc, acost_val, barras, espectro_t)
    if key in _cache:
        return _cache[key]
    espectro = [c.FaixaCarga(c.TipoEixo(t), carga, rep) for t, carga, rep in espectro_t]
    p = c.ParametrosProjeto(fctk_mpa=fctk, k_mpa_m=k, fsc=fsc,
                            acostamento=c.TipoAcostamento(acost_val),
                            com_barras_transferencia=barras, espectro=espectro)
    val = sens.tornado(p)
    _cache[key] = val
    return val


def _echart_curva(curva, h_marcado):
    hs = [r.h_cm for r in curva]
    return {
        "tooltip": {"trigger": "axis"},
        "legend": {"bottom": 0},
        "grid": {"left": 45, "right": 20, "top": 20, "bottom": 55},
        "xAxis": {"type": "category", "data": [f"{h:g}" for h in hs],
                  "name": "h (cm)", "nameLocation": "middle", "nameGap": 28},
        "yAxis": {"type": "value", "max": 200, "name": "consumo (%)"},
        "series": [
            {"name": "Fadiga (%)", "type": "line", "smooth": True, "showSymbol": False,
             "lineStyle": {"width": 3}, "color": "#1565C0",
             "data": [round(min(r.soma_fadiga_pct, 200), 1) for r in curva]},
            {"name": "Erosão (%)", "type": "line", "smooth": True, "showSymbol": False,
             "lineStyle": {"width": 3}, "color": ung.AMBAR,
             "data": [round(min(r.soma_erosao_pct, 200), 1) for r in curva],
             "markLine": {"symbol": "none", "lineStyle": {"color": "#c62828"},
                          "label": {"formatter": "limite 100%"}, "data": [{"yAxis": 100}]}},
            {"name": f"h = {h_marcado:.1f} cm", "type": "line", "data": [],
             "markLine": {"symbol": "none", "lineStyle": {"color": "#2e7d32", "type": "dashed"},
                          "data": [{"xAxis": f"{h_marcado:g}"}]}},
        ],
    }


def _echart_capex(r) -> dict:
    """Barras empilhadas horizontais: decomposicao do CAPEX por componente,
    com o codigo SICRO de cada fatia no tooltip."""
    cats = ["Asfalto (ref.)", "Rígido"]
    paleta = ["#2E3A40", "#C8861F", "#6B7B84", "#E8C88A", "#9DB2BB", "#F0E2C8"]
    series = []
    i = 0
    for alt, idx in ((r.rigido, 1), (r.flexivel, 0)):
        for nome, val, fonte in alt.componentes:
            if val <= 0:
                continue
            data = [None, None]
            data[idx] = round(val, 2)
            series.append({
                "name": nome, "type": "bar", "stack": "capex",
                "color": paleta[i % len(paleta)],
                "data": data,
                "tooltip": {"formatter": f"{nome}<br>R$ " + f"{val:.2f}".replace(".", ",")
                            + f"/m² · {fonte}"},
            })
            i += 1
    return {
        "tooltip": {},
        "grid": {"left": 95, "right": 30, "top": 8, "bottom": 25},
        "xAxis": {"type": "value", "name": "R$/m²"},
        "yAxis": {"type": "category", "data": cats},
        "series": series,
    }


def _echart_lcca(lcca_res):
    anos = list(range(lcca_res.horizonte + 1))
    serie_rigido = {
        "name": "Rígido", "type": "line", "step": "end", "showSymbol": False,
        "lineStyle": {"width": 3}, "color": ung.ASFALTO,
        "data": [round(v, 2) for v in lcca_res.rigido.acumulado_vp(lcca_res.horizonte, lcca_res.taxa)]}
    if lcca_res.ano_cruzamento:
        serie_rigido["markLine"] = {
            "symbol": "none", "lineStyle": {"color": "#c62828", "type": "dotted", "width": 2},
            "label": {"formatter": f"a partir do ano {lcca_res.ano_cruzamento}\no rígido é mais barato",
                      "position": "insideEndTop", "fontSize": 10},
            "data": [{"xAxis": lcca_res.ano_cruzamento}]}
    return {
        "tooltip": {"trigger": "axis"},
        "legend": {"bottom": 0},
        "grid": {"left": 55, "right": 20, "top": 20, "bottom": 55},
        "xAxis": {"type": "category", "data": anos, "name": "ano", "nameLocation": "middle", "nameGap": 28},
        "yAxis": {"type": "value", "name": "R$/m² (VP)"},
        "series": [
            serie_rigido,
            {"name": "Asfalto (ref.)", "type": "line", "step": "end", "showSymbol": False,
             "lineStyle": {"width": 3}, "color": ung.AMBAR,
             "data": [round(v, 2) for v in lcca_res.flexivel.acumulado_vp(lcca_res.horizonte, lcca_res.taxa)]},
        ],
    }


def _echart_timeline(r) -> dict:
    """Linha do tempo dos gastos: bolha = evento de custo (tamanho ∝ valor)."""
    cats = ["Asfalto (ref.)", "Rígido"]
    series = []
    for alt, idx, cor in ((r.rigido, 1, ung.ASFALTO), (r.flexivel, 0, ung.AMBAR)):
        pontos: dict[int, list[tuple[str, float]]] = {0: [("Construção (CAPEX)", alt.capex_m2)]}
        for ev in alt.eventos:
            if ev.custo_m2 >= 1.0 and 0 < ev.ano <= r.horizonte:
                pontos.setdefault(ev.ano, []).append((ev.descricao, ev.custo_m2))
        dados = []
        for ano, evs in sorted(pontos.items()):
            custo = sum(cst for _, cst in evs)
            desc = "<br>".join(f"{d} — R$ " + f"{cst:.2f}".replace(".", ",") + "/m²"
                               for d, cst in evs)
            dados.append({
                "value": [ano, idx],
                "symbolSize": max(10.0, min(42.0, 6 + custo ** 0.5 * 3.5)),
                "tooltip": {"formatter": f"<b>Ano {ano}</b><br>{desc}"},
            })
        series.append({"name": cats[idx], "type": "scatter", "data": dados,
                       "color": cor, "itemStyle": {"opacity": 0.85}})
    return {
        "tooltip": {"trigger": "item"},
        "grid": {"left": 95, "right": 30, "top": 10, "bottom": 30},
        "xAxis": {"type": "value", "min": 0, "max": r.horizonte, "name": "ano",
                  "splitLine": {"lineStyle": {"type": "dashed", "opacity": 0.4}}},
        "yAxis": {"type": "category", "data": cats},
        "series": series,
    }


def _linhas_ano_a_ano(r) -> list[dict]:
    """Tabela da conta inteira: ano, evento, custo nominal, fator, VP, acumulado."""
    def fmt(v, dec=2):
        return ("R$ " + f"{v:.{dec}f}").replace(".", ",")

    rows = []
    for alt in (r.rigido, r.flexivel):
        nome = "Rígido" if "Rígido" in alt.nome else "Asfalto"
        desc_por_ano: dict[int, list[str]] = {}
        for ev in alt.eventos:
            desc_por_ano.setdefault(ev.ano, []).append(ev.descricao)
        acc = 0.0
        for t, custo in enumerate(alt.fluxo_anual(r.horizonte)):
            if custo <= 0:
                continue
            fator = 1 / (1 + r.taxa) ** t
            vp = custo * fator
            acc += vp
            evento = ("Construção (CAPEX)" if t == 0
                      else " + ".join(dict.fromkeys(desc_por_ano.get(t, ["Manutenção"]))))
            rows.append({"alt": nome, "ano": t, "evento": evento,
                         "nominal": fmt(custo), "fator": f"{fator:.3f}".replace(".", ","),
                         "vp": fmt(vp), "acum": fmt(acc)})
    return rows


def render_resultado(s: dict, refresh) -> bool:
    with ui.column().classes("w-full max-w-3xl mx-auto gap-4 aparecer"):
        ung.pergunta("Resultado do dimensionamento")
        if not (s.get("espectro") or []):
            ui.label("Sem espectro de tráfego. Volte à etapa de Tráfego.").classes("text-amber-700")
            return True
        p = s.get("dim_param") or _param_do_estado(s)
        resultado = s["dim_resultado"] if "dim_resultado" in s else c.dimensionar(p)
        curva = c.curva_sensibilidade(p)

        if resultado is None:
            with ui.column().classes("w-full cartao p-8 gap-2"):
                _painel_falha_h(s, refresh, p)
        else:
            with ui.column().classes("w-full cartao p-8 gap-3"):
                aprovada = resultado.soma_fadiga_pct <= 100 and resultado.soma_erosao_pct <= 100
                ung.resultado_destaque(resultado.h_cm, aprovada)
                ung.barra_consumo("Consumo de fadiga", resultado.soma_fadiga_pct)
                ung.barra_consumo("Consumo de erosão", resultado.soma_erosao_pct)
                ui.label("Menor espessura (número inteiro de cm) em que fadiga E erosão ficam "
                         "≤ 100% — critério duplo do método PCA 1984 (IPR-714).") \
                    .classes("text-xs text-slate-400")

            with ui.column().classes("w-full cartao p-8 gap-3"):
                ui.label("Espessura × consumo").classes("font-bold")
                ui.echart(_echart_curva(curva, resultado.h_cm)).classes("w-full h-64")
            # ENXUGAMENTO (23/08/2026, pedido da orientadora): "deixar apenas o
            # dimensionamento" -- removidos daqui os painéis de análise de
            # sensibilidade (tornado), recomendação de sub-base e custo de
            # ciclo de vida (LCCA). O código-fonte (sensibilidade.py,
            # recomenda_subbase.py, lcca.py) continua intacto e funcional;
            # histórico completo da UI removida está no git (commit "Corrige
            # modelo de erosao..." e anteriores) e documentado na memória do
            # projeto, caso valha a pena reincorporar como "trabalhos futuros".

        # Exportar PDF
        with ui.column().classes("w-full cartao p-8 gap-3"):
            ui.label("📄 Exportar relatório").classes("font-bold")
            if resultado is not None:
                def _baixar_pdf():
                    sub = s.get("subleito")
                    rec = rsb.recomendar(s.get("n_pesados", 0), s.get("k0", 50.0))
                    ctx = rel.ContextoRelatorio(
                        local=_local_relatorio(s),
                        tipo_solo=((sub.ordem_sibcs + " · AASHTO " + sub.classe_aashto)
                                   if sub and sub.classe_aashto else None),
                        cbr_estimado=(sub.cbr_estimado if sub else s.get("cbr_val")),
                        k0_subleito=s.get("k0"), tipo_subbase=s.get("tipo_sb"),
                        esp_subbase_cm=(s.get("esp_sb") or 0) or None,
                        vmda=s.get("vmda") or s.get("vmda_man"), periodo_anos=s.get("periodo"),
                        triagem_score=s.get("triagem_score"), triagem_score_max=float(tri.SCORE_MAX),
                        subbase_recomendada=rec.tipo_recomendado, subbase_justificativa=rec.justificativa)
                    try:
                        pdf_bytes = rel.gerar_pdf(p, resultado, curva, ctx, lcca_res=s.get("_lcca_res"))
                        ui.download(pdf_bytes, filename="relatorio_pavimento_rigido.pdf")
                    except Exception as e:
                        ui.notify(f"Erro ao gerar PDF: {e}", type="negative")

                ui.button("⬇️ Baixar relatório em PDF", on_click=_baixar_pdf) \
                    .props("color=amber-8 unelevated no-caps rounded").classes("text-white")
            else:
                ui.label("Corrija os parâmetros para gerar o PDF.").classes("text-slate-500")
    return True


# ---------------------------------------------------------------
# Titulo/resumo por tela (cartoes compactos do fluxo vertical)
# ---------------------------------------------------------------
def titulo_de(tela_id: str) -> str:
    fixos = {"modo": "Modo do projeto", "rodovia": "Rodovia", "local_mapa": "Local da obra",
             "triagem_resumo": "Viabilidade", "local_manual": "Subleito", "subbase": "Sub-base",
             "trafego": "Tráfego", "concreto": "Concreto", "memoria": "Memória de cálculo",
             "resultado": "Resultado"}
    if tela_id.startswith("crit_"):
        return tri.PERGUNTAS[tela_id[5:]][0]
    return fixos.get(tela_id, tela_id)


def resumo_de(s: dict, tela_id: str) -> str:
    try:
        if tela_id == "modo":
            return _MODOS.get(s.get("modo_projeto", ""), ("—",))[0]
        if tela_id == "rodovia":
            sel = s.get("posto_sel")
            return (f"BR-{sel['br']:03d} ({sel['lugar']}) · VMDa {sel['vmda']:,}".replace(",", ".")
                    if sel else "—")
        if tela_id == "local_mapa":
            sub = s.get("subleito")
            if sub is not None and sub.classe_aashto:
                onde = sub.municipio or "ponto marcado"
                return f"{onde} · {sub.classe_aashto} · k0 ≈ {sub.k0_estimado:.0f} MPa/m"
            return "—"
        if tela_id.startswith("crit_"):
            k = tela_id[5:]
            v = s.get(f"tri_{k}")
            return tri.PERGUNTAS[k][1].get(v, "—")
        if tela_id == "triagem_resumo":
            sc = s.get("triagem_score")
            if sc is None:
                return "—"
            emoji, _n, _t = tri.recomendacao(sc)
            return f"{emoji} score {sc}/{tri.SCORE_MAX}"
        if tela_id == "local_manual":
            return f"k0 = {s.get('k0', 0):.0f} MPa/m"
        if tela_id == "subbase":
            return f"{s.get('tipo_sb', '—')} · k efetivo {s.get('k_efetivo', 0):.0f} MPa/m"
        if tela_id == "trafego":
            return (f"VMDa {s.get('vmda', 0):,.0f} · {s.get('n_pesados', 0):,.0f} eixos no período"
                    .replace(",", "."))
        if tela_id == "concreto":
            return (f"fctk {s.get('fctk', 4.8):.1f} MPa · FSC {s.get('fsc', 1.2):.1f} · "
                    f"acostamento {s.get('acost', 'Sem').lower()} · barras {s.get('barras', 'Sem').lower()}")
        if tela_id == "memoria":
            r = s.get("dim_resultado")
            return f"h = {r.h_cm:.1f} cm".replace(".", ",") if r else "—"
    except Exception:
        return "—"
    return ""
