"""
telas.py - Renderizadores das telas do assistente (wizard).

Cada funcao desenha UMA tela, le/grava em st.session_state e retorna `valido`
(bool) indicando se da p/ avancar. O backend (calculos, estagio3, ...) e reusado
sem alteracao. app.py orquestra a ordem das telas e a navegacao.
"""
from __future__ import annotations

import math
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
import folium
from streamlit_folium import st_folium

import calculos as c
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
import ui

ss = st.session_state


# ---------------------------------------------------------------
# loaders cacheados
# ---------------------------------------------------------------
@st.cache_data(show_spinner="Lendo postos do PNCT...")
def _pnct_rj():
    try:
        return pnct.carregar_trechos()
    except Exception:
        return []


@st.cache_data(show_spinner=False)
def _municipios():
    """Divisas municipais do RJ (IBGE) p/ desenhar no mapa. None se indisponivel."""
    import json
    import os
    p = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                     "_mun", "rj_municipios.min.geojson")
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


@st.cache_data(show_spinner=False)
def _postos():
    """Postos 'Referencial' do PNCT/RJ geocodificados (lista de dicts). [] se faltar."""
    import csv
    import os
    p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_pnct", "postos_rj.csv")
    try:
        with open(p, encoding="utf-8") as f:
            out = []
            for r in csv.DictReader(f):
                out.append({"br": int(r["br"]), "km": float(r["km"]),
                            "vmda": int(r["vmda"]),
                            "lat": float(r["lat"]), "lon": float(r["lon"]),
                            "lugar": r["lugar"]})
            return sorted(out, key=lambda d: -d["vmda"])
    except Exception:
        return []


def _posto_mais_proximo(lat, lon, postos):
    return min(postos, key=lambda p: (p["lat"] - lat) ** 2 + (p["lon"] - lon) ** 2, default=None)


def _haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Distancia great-circle em km."""
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2
         + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2))
         * math.sin(dlon / 2) ** 2)
    return R * 2 * math.asin(math.sqrt(a))


# ---------------------------------------------------------------
# ETAPA 1 - Local & Fundacao
# ---------------------------------------------------------------
# ---------------------------------------------------------------
# ETAPA 0 - Modo do projeto (carrega pre-definicoes p/ todo o fluxo)
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


def tela_modo() -> bool:
    with st.container(border=True):
        ui.pergunta("Como você quer montar o projeto?",
                    "A escolha vale para todas as etapas — dados pré-definidos ficam "
                    "sempre marcados com a origem e podem ser ajustados.")
        atual = ss.get("modo_projeto", "rodovia")
        sel = st.radio(
            "modo", list(_MODOS),
            format_func=lambda k: f"{_MODOS[k][0]} — {_MODOS[k][1]}",
            index=list(_MODOS).index(atual), label_visibility="collapsed",
            key="w_modo_projeto")
        ss["modo_projeto"] = sel
        if sel != "manual":
            st.caption("Cobertura dos dados automáticos: Estado do RJ "
                       "(PNCT, EMBRAPA, NASA POWER, SICRO).")
    return True


def _prefill_triagem(force: bool = False) -> None:
    """Deriva criterios da triagem a partir do local/rodovia ja escolhidos.

    force=True re-deriva (usar quando o local/rodovia MUDA); force=False so
    preenche o que ainda nao existe.
    """
    fontes = ss.setdefault("tri_fonte", {})

    def _set(k: str, val, fonte: str) -> None:
        if val is None:
            return
        if force or f"tri_{k}" not in ss:
            ss[f"tri_{k}"] = val
            fontes[k] = fonte

    sub = ss.get("subleito")
    if sub is not None and getattr(sub, "cbr_estimado", None) is not None:
        _set("cbr", tri.cat_cbr(sub.cbr_estimado),
             f"CBR ≈ {sub.cbr_estimado}% estimado do solo {sub.classe_aashto} "
             "(pedologia EMBRAPA)")
    ponto = ss.get("ponto_obra")
    if ponto:
        precip = clima.precip_por_coordenada(ponto[0], ponto[1])
        if precip is not None:
            _set("clima", tri.cat_precip(precip),
                 f"precipitação ≈ {precip:.0f} mm/ano no local "
                 "(normal climatológica NASA POWER)")
    if ss.get("vmda"):
        esp_est = pt.espectro_de_projeto(pt.PERFIS["rodovia"], float(ss["vmda"]),
                                         20, 0.5, 1.0, 0.03)
        n_est = sum(f.repeticoes_previstas for f in esp_est)
        _set("traf", tri.cat_trafego(n_est),
             f"N ≈ {n_est:,.0f} eixos em 20 anos, estimado do VMDa "
             f"{ss['vmda']:,.0f} (PNCT/DNIT)".replace(",", "."))


def tela_rodovia() -> bool:
    with st.container(border=True):
        ui.pergunta("Em qual rodovia será o dimensionamento?",
                    "Clique num pino 🛣️ para escolher o posto de contagem PNCT/DNIT. "
                    "O tráfego real, o solo e o clima do trecho pré-definem o projeto.")
        postos = _postos()
        if not postos:
            st.warning("Postos do PNCT indisponíveis. Volte e escolha outro modo.")
            return False
        sel = ss.get("posto_sel")
        mapa = folium.Map(location=[-22.2, -42.8], zoom_start=7, control_scale=True)
        mun = _municipios()
        if mun is not None:
            folium.GeoJson(mun, style_function=lambda f: {"fillOpacity": 0.0, "color": "#546E7A",
                                                          "weight": 0.8, "dashArray": "4"},
                           tooltip=folium.GeoJsonTooltip(fields=["municipio"], aliases=[""])).add_to(mapa)
        for p in postos:
            escolhido = sel and abs(p["lat"] - sel["lat"]) < 1e-6 and abs(p["lon"] - sel["lon"]) < 1e-6
            folium.Marker([p["lat"], p["lon"]],
                          tooltip=f"BR-{p['br']:03d} · {p['lugar']} · VMDa {p['vmda']:,}",
                          icon=folium.Icon(color="red" if escolhido else "orange",
                                           icon="road", prefix="fa")).add_to(mapa)
        md = st_folium(mapa, width=620, height=320,
                       returned_objects=["last_object_clicked"], key="w_mapa_rod")
        if md and md.get("last_object_clicked"):
            la = md["last_object_clicked"]["lat"]; lo = md["last_object_clicked"]["lng"]
            p = _posto_mais_proximo(la, lo, postos)
            if p and ss.get("posto_sel") != p:
                ss["posto_sel"] = p
                ss["vmda"] = p["vmda"]
                ss["ponto_obra"] = [p["lat"], p["lon"]]
                ss["subleito"] = ls.subleito_por_coordenada(p["lat"], p["lon"])
                sub = ss["subleito"]
                if sub and sub.classe_aashto:
                    ss["k0"] = sub.k0_estimado
                    ss["cbr_val"] = sub.cbr_estimado
                    ss["municipio"] = sub.municipio
                _prefill_triagem(force=True)
                st.rerun()
        sel = ss.get("posto_sel")
        if not sel:
            st.info("Clique num pino para escolher o trecho.")
            return False
        st.success(f"Trecho: **BR-{sel['br']:03d}** ({sel['lugar']}) · VMDa real "
                   f"**{sel['vmda']:,}** veíc/dia (PNCT {pnct.ANO_BASE})")
        sub = ss.get("subleito")
        if sub and sub.classe_aashto:
            st.caption(f"Solo no trecho: **{sub.ordem_sibcs}** · AASHTO {sub.classe_aashto} · "
                       f"CBR≈{sub.cbr_estimado} · k0 ≈ {sub.k0_estimado:.0f} MPa/m (EMBRAPA). "
                       "⚠️ Coordenada do posto é aproximada — confirme o solo com ensaio local.")
        else:
            st.caption("⚠️ Solo não identificado na coordenada do posto — você informará "
                       "o subleito na etapa Fundação.")
    return True


def tela_local_mapa() -> bool:
    with st.container(border=True):
        ui.pergunta("Onde fica a obra?",
                    "Clique no mapa no local aproximado (cobertura de solo: RJ) ou informe o CEP.")
        mapa = folium.Map(location=[-22.2, -42.8], zoom_start=7, control_scale=True,
                          tiles="OpenStreetMap")
        mun = _municipios()
        if mun is not None:
            folium.GeoJson(mun, name="Municipios",
                           style_function=lambda f: {"fillOpacity": 0.0, "color": "#546E7A",
                                                     "weight": 1.0, "dashArray": "4"},
                           highlight_function=lambda f: {"fillOpacity": 0.08, "weight": 2,
                                                         "color": "#E8A33D"},
                           tooltip=folium.GeoJsonTooltip(fields=["municipio"], aliases=[""])
                           ).add_to(mapa)
        if ss.get("ponto_obra"):
            folium.Marker(ss["ponto_obra"], tooltip="Local da obra",
                          icon=folium.Icon(color="red")).add_to(mapa)
        md = st_folium(mapa, width=620, height=320,
                       returned_objects=["last_clicked"], key="w_mapa")
        if md and md.get("last_clicked"):
            lat = round(md["last_clicked"]["lat"], 6)
            lon = round(md["last_clicked"]["lng"], 6)
            if ss.get("ponto_obra") != [lat, lon]:
                ss["ponto_obra"] = [lat, lon]
                ss["subleito"] = ls.subleito_por_coordenada(lat, lon)
                ss.pop("posto_sel", None)  # novo local -> re-sugerir o posto de trafego
                _prefill_triagem(force=True)
                st.rerun()

        cep = st.text_input("ou informe o CEP", placeholder="00000-000")
        if st.button("Estimar pelo CEP"):
            sub_cep = ls.sugerir_subleito(cep) if cep else None
            ss["subleito"] = sub_cep
            if sub_cep is not None and sub_cep.lat is not None:
                ss["ponto_obra"] = [sub_cep.lat, sub_cep.lon]  # CEP define o local p/ o trafego
            else:
                ss.pop("ponto_obra", None)
            ss.pop("posto_sel", None)  # novo local -> re-sugerir o posto de trafego
            _prefill_triagem(force=True)

        sub = ss.get("subleito")
        if sub and sub.classe_aashto:
            ss["k0"] = sub.k0_estimado
            ss["cbr_val"] = sub.cbr_estimado
            ss["municipio"] = sub.municipio
            st.success(f"**{sub.ordem_sibcs}** ({sub.textura}) · AASHTO **{sub.classe_aashto}** · "
                       f"CBR≈{sub.cbr_estimado} · **k0 ≈ {sub.k0_estimado:.0f} MPa/m**")
            st.caption(f"⚠️ {sub.confianca}")
            return True
        elif sub is not None:
            st.warning("Sem dado de solo para este ponto (fora do RJ). Tente outro ponto "
                       "ou volte e escolha **Inserir manualmente**.")
    return ss.get("subleito") is not None and ss["subleito"].classe_aashto is not None


def tela_local_manual() -> bool:
    with st.container(border=True):
        ui.pergunta("Qual o subleito?", "Informe o CBR, o tipo de solo, ou o k0 direto.")
        metodo = st.radio("Como definir o k0?", ["Pelo CBR", "Pelo tipo de solo", "Valor direto"],
                          horizontal=True, key="w_metodo_k0")
        if metodo == "Pelo CBR":
            cbr = st.number_input(
                "CBR do subleito (%)", 1.0, 100.0,
                float(ss.get("cbr_val") or 5.0), 0.5, key="w_cbr",
                help="Índice de Suporte Califórnia do subleito. Típico: argilas 2–8%, "
                     "siltes 4–10%, solos granulares 10–30%. Convertido em k0 pela "
                     "Figura 11 do IPR-714.")
            ss["k0"] = e3.k_de_cbr(cbr)
            ss["cbr_val"] = cbr
        elif metodo == "Pelo tipo de solo":
            classes = list(e3.QUADRO_3_SOLO_K)
            solo = st.selectbox(
                "Tipo de solo (AASHTO)", classes, key="w_solo",
                help="Classificação AASHTO do subleito → faixa de k0 pelo Quadro 3 "
                     "do IPR-714 (adota-se o ponto médio da faixa).")
            ss["k0"] = e3.k_de_solo(solo)
            ss["cbr_val"] = None
        else:
            ss["k0"] = st.number_input(
                "k0 do subleito (MPa/m)", 10.0, 150.0,
                float(ss.get("k0") or 50.0), 5.0, key="w_k0dir",
                help="Coeficiente de recalque no topo do subleito (ensaio de placa "
                     "ou correlação). O IPR-714 limita o k de projeto a 150 MPa/m.")
            ss["cbr_val"] = None
        st.caption(f"k0 do subleito ≈ **{ss['k0']:.0f} MPa/m**")
    return True


def tela_subbase() -> bool:
    with st.container(border=True):
        ui.pergunta("Qual sub-base sobre o subleito?",
                    "A sub-base eleva o coeficiente de recalque k e reduz a erosão.")
        sub = ss.get("subleito")
        solo_nome = (sub.ordem_sibcs.title()
                     if sub and getattr(sub, "ordem_sibcs", None) else None)
        if solo_nome:
            st.caption(f"Subleito detectado: **{solo_nome}** · CBR≈{sub.cbr_estimado} · "
                       f"k0 ≈ {ss.get('k0', 50):.0f} MPa/m")

        def _fmt_sb(t):
            if t == "Sem sub-base" and solo_nome:
                return f"Sem sub-base (sobre {solo_nome})"
            return t

        tipo = st.selectbox("Tipo de sub-base", list(e3.TIPOS_SUBBASE),
                            format_func=_fmt_sb, key="w_tipo_sb",
                            help="Sub-bases cimentadas (solo-cimento, BGTC, CCR) elevam "
                                 "mais o k do que a granular — Figuras 18–21 do IPR-714. "
                                 "A recomendação com custo (SICRO) aparece no Resultado.")
        esp = 0.0
        if e3.TIPOS_SUBBASE[tipo] is not None:
            esp = st.slider("Espessura da sub-base (cm)", 10, 30, ss.get("esp_sb", 15), 1,
                            key="w_esp_sb",
                            help="O ganho de k cresce com a espessura da camada "
                                 "(interpolação das Figuras 18–21 do IPR-714). Usual: 10–20 cm.")
        k0 = ss.get("k0", 50.0)
        k = e3.k_efetivo(k0, tipo, esp)
        ss["tipo_sb"] = tipo
        ss["esp_sb"] = esp
        ss["k_efetivo"] = k
        st.success(f"k efetivo (topo da sub-base) = **{k:.0f} MPa/m**")
        if k >= e3.K_MAX_TOPO_SUBBASE:
            st.caption("⚠️ Limitado a 150 MPa/m (recomendação IPR-714).")
    return True


# ---------------------------------------------------------------
# ETAPA 2 - Trafego
# ---------------------------------------------------------------
_DEFAULT = pd.DataFrame([
    {"tipo": "simples", "carga_tf": 8.0, "repeticoes": 238_118},
    {"tipo": "simples", "carga_tf": 10.0, "repeticoes": 310_404},
    {"tipo": "simples", "carga_tf": 12.0, "repeticoes": 242_438},
    {"tipo": "simples", "carga_tf": 14.0, "repeticoes": 65_889},
    {"tipo": "simples", "carga_tf": 15.0, "repeticoes": 39_296},
    {"tipo": "simples", "carga_tf": 16.0, "repeticoes": 5_565},
    {"tipo": "tandem_duplo", "carga_tf": 20.0, "repeticoes": 17_808},
    {"tipo": "tandem_triplo", "carga_tf": 26.0, "repeticoes": 12_243},
])
_EIXO = {"simples": c.TipoEixo.SIMPLES, "tandem_duplo": c.TipoEixo.TANDEM_DUPLO,
         "tandem_triplo": c.TipoEixo.TANDEM_TRIPLO}


def _montar_espectro(df: pd.DataFrame) -> list[c.FaixaCarga]:
    faixas = []
    for _, r in df.iterrows():
        if pd.isna(r["carga_tf"]) or pd.isna(r["repeticoes"]):
            continue
        faixas.append(c.FaixaCarga(_EIXO[r["tipo"]], float(r["carga_tf"]), float(r["repeticoes"])))
    return faixas


def _trafego_comum(vmda: float) -> bool:
    """Parte comum (perfil + periodo + avancado + editor) -> espectro em ss."""
    cA, cB = st.columns(2)
    perfil_key = cA.selectbox("Perfil de composição da frota", list(pt.PERFIS),
                              format_func=lambda k: pt.PERFIS[k].nome, key="w_perfil",
                              help="Distribuição da frota por classe de veículo (perfil de "
                                   "referência, editável abaixo). Eixos e cargas legais por "
                                   "classe: Manual de Estudos de Tráfego IPR-723, Figura 13.")
    periodo = cB.number_input("Período de projeto (anos)", 5, 40, ss.get("periodo", 20), 1,
                              key="w_periodo",
                              help="Vida útil de projeto. Pavimento rígido: tipicamente "
                                   "20–30 anos (o exemplo do IPR-714 usa 20).")
    with st.expander("Parâmetros avançados (crescimento, fatores)"):
        cC, cD, cE = st.columns(3)
        cresc = cC.number_input("Crescimento (%/ano)", 0.0, 10.0, 3.0, 0.5, key="w_cresc",
                                help="Taxa geométrica de crescimento anual do tráfego "
                                     "(acumulada como juros compostos no período).")
        f_sent = cD.slider("Fator de sentido", 0.3, 1.0, 0.5, 0.05, key="w_fsent",
                           help="Fração do VMDa no sentido de projeto. 0,5 = fluxo "
                                "equilibrado nos dois sentidos.")
        f_faixa = cE.slider("Fator de faixa", 0.3, 1.0, 1.0, 0.05, key="w_ffaixa",
                            help="Fração do tráfego do sentido que usa a faixa mais "
                                 "carregada. 1,0 = pista simples (1 faixa por sentido).")
    ss["periodo"] = periodo
    ss["vmda"] = vmda
    esp_ger = pt.espectro_de_projeto(pt.PERFIS[perfil_key], float(vmda), int(periodo),
                                     f_sent, f_faixa, cresc / 100.0)
    base_df = pd.DataFrame([{"tipo": f.eixo.value, "carga_tf": f.carga_tf,
                             "repeticoes": round(f.repeticoes_previstas)} for f in esp_ger])
    st.caption(f"{pt.PERFIS[perfil_key].descricao} · eixos via Manual IPR-723 (Fig.13). "
               "Edite abaixo se quiser ajustar eixo a eixo.")
    key = f"w_ed_{perfil_key}_{int(vmda)}_{periodo}"
    df = st.data_editor(base_df, num_rows="dynamic", use_container_width=True, key=key,
                        column_config={
                            "tipo": st.column_config.SelectboxColumn("Tipo de eixo", options=list(_EIXO)),
                            "carga_tf": st.column_config.NumberColumn("Carga (tf)", min_value=1.0),
                            "repeticoes": st.column_config.NumberColumn("Repetições", min_value=0)})
    espectro = _montar_espectro(df)
    ss["espectro"] = espectro
    ss["n_pesados"] = sum(f.repeticoes_previstas for f in espectro)
    st.caption(f"Total de eixos solicitantes: **{ss['n_pesados']:,.0f}**")
    return len(espectro) > 0


def tela_trafego() -> bool:
    with st.container(border=True):
        modo_proj = ss.get("modo_projeto", "manual")
        # Modo RODOVIA: o posto ja foi escolhido no inicio -> VMDa pre-definido
        if modo_proj == "rodovia" and ss.get("posto_sel"):
            sel = ss["posto_sel"]
            ui.pergunta("Confirme o tráfego do trecho",
                        "O volume veio do posto escolhido no início — ajuste a "
                        "composição e o período abaixo, se quiser.")
            st.success(f"VMDa **{sel['vmda']:,}** veíc/dia — BR-{sel['br']:03d} "
                       f"({sel['lugar']}), PNCT/DNIT {pnct.ANO_BASE}")
            st.caption("💡 Pré-definido pela rodovia escolhida no início. Para usar "
                       "outro volume, volte à 1ª etapa ou edite o espectro abaixo.")
            return _trafego_comum(sel["vmda"])
        ui.pergunta("Quanto tráfego pesado a via recebe?",
                    "Escolha a rodovia no mapa (volume real de um posto do PNCT/DNIT) ou "
                    "informe o VMDa manualmente. Você pode alternar a qualquer momento.")
        op = st.radio("Como informar o tráfego",
                      ["📍 Marcar no mapa (rodovia do PNCT)", "✏️ Digitar manualmente"],
                      horizontal=True, label_visibility="collapsed",
                      index=0 if ss.get("traf_modo2", "mapa") == "mapa" else 1,
                      key="w_traf_modo2")
        ss["traf_modo2"] = "mapa" if op.startswith("📍") else "manual"
        if ss["traf_modo2"] == "mapa":
            postos = _postos()
            if not postos:
                st.warning("Postos do PNCT indisponíveis. Volte e escolha **Digitar manualmente**.")
                return False
            # sugere o posto mais proximo do local da obra (se houver)
            if "posto_sel" not in ss and ss.get("ponto_obra"):
                ss["posto_sel"] = _posto_mais_proximo(ss["ponto_obra"][0], ss["ponto_obra"][1], postos)
            mapa = folium.Map(location=[-22.2, -42.8], zoom_start=7, control_scale=True)
            mun = _municipios()
            if mun is not None:
                folium.GeoJson(mun, style_function=lambda f: {"fillOpacity": 0.0, "color": "#546E7A",
                                                              "weight": 0.8, "dashArray": "4"},
                               tooltip=folium.GeoJsonTooltip(fields=["municipio"], aliases=[""])).add_to(mapa)
            sel = ss.get("posto_sel")
            for p in postos:
                escolhido = sel and abs(p["lat"] - sel["lat"]) < 1e-6 and abs(p["lon"] - sel["lon"]) < 1e-6
                folium.Marker([p["lat"], p["lon"]],
                              tooltip=f"BR-{p['br']:03d} · {p['lugar']} · VMDa {p['vmda']:,}",
                              icon=folium.Icon(color="red" if escolhido else "orange",
                                               icon="road", prefix="fa")).add_to(mapa)
            md = st_folium(mapa, width=620, height=320,
                           returned_objects=["last_object_clicked"], key="w_mapa_traf")
            if md and md.get("last_object_clicked"):
                la = md["last_object_clicked"]["lat"]; lo = md["last_object_clicked"]["lng"]
                p = _posto_mais_proximo(la, lo, postos)
                if p and ss.get("posto_sel") != p:
                    ss["posto_sel"] = p
                    st.rerun()
            sel = ss.get("posto_sel")
            if not sel:
                st.info("Clique num pino (🛣️ rodovia) para escolher o posto de tráfego.")
                return False
            st.success(f"Posto: **BR-{sel['br']:03d}** ({sel['lugar']}) · VMDa **{sel['vmda']:,}** "
                       f"veic/dia · PNCT/DNIT ano-base {pnct.ANO_BASE}")
            if ss.get("modo_projeto") == "local" and ss.get("ponto_obra"):
                st.caption("💡 Posto sugerido pela localização da obra — clique em outro "
                           "pino para trocar.")
            vmda = sel["vmda"]
        else:
            vmda = st.number_input("VMDa (veic/dia)", 100, 300_000, ss.get("vmda_man", 8000), 100,
                                   key="w_vmda",
                                   help="Volume Médio Diário anual, nos dois sentidos. Fontes "
                                        "típicas: contagem local, concessionária ou PNCT/DNIT.")
            ss["vmda_man"] = vmda
        return _trafego_comum(vmda)


# ---------------------------------------------------------------
# ETAPA 2 - Viabilidade (go/no-go) - UM criterio por tela
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
    "vida": "O rígido se paga em horizontes longos (20–30 anos) pela baixa manutenção. "
            "Peso 2.",
    "cbr": "Subleito fraco penaliza menos o rígido do que o flexível — a placa vence o "
           "vão. Peso 2.",
    "manut": "Se interditar a via para manutenção frequente é difícil ou caro, o rígido "
             "leva vantagem (menos intervenções). Peso 2.",
    "clima": "Chuva alta degrada mais o asfalto (bombeamento de finos, desagregação). "
             "Peso 2.",
    "usina": "Distância à usina de concreto encarece o transporte do material. Peso 1.",
}


def tela_criterio(k: str, idx: int):
    """Fabrica o renderizador da tela do criterio k (idx = posicao 1..6)."""
    def render() -> bool:
        rot, fmt, _peso = tri.PERGUNTAS[k]
        with st.container(border=True):
            ui.progresso(idx, len(_CRIT_ORDEM), "Critério")
            ui.pergunta(_CRIT_TITULO[k], _CRIT_AJUDA[k])
            opts = list(fmt.keys())
            ss.setdefault(f"tri_{k}", opts[len(opts) // 2])
            st.select_slider(rot, options=opts, key=f"tri_{k}",
                             format_func=lambda x, f=fmt: f[x])
            fonte = (ss.get("tri_fonte") or {}).get(k)
            if fonte and ss.get("modo_projeto") in ("rodovia", "local"):
                origem = ("pela rodovia escolhida" if ss.get("modo_projeto") == "rodovia"
                          else "pela localização")
                st.info(f"💡 Valor pré-definido {origem}: {fonte}. "
                        "Ajuste acima se tiver dado melhor.")
        return True
    return render


# ---------------------------------------------------------------
# Titulo/resumo por tela (cartoes compactos do fluxo vertical)
# ---------------------------------------------------------------
def titulo_de(tela_id: str) -> str:
    fixos = {"modo": "Modo do projeto", "rodovia": "Rodovia",
             "local_mapa": "Local da obra", "triagem_resumo": "Viabilidade",
             "local_manual": "Subleito", "subbase": "Sub-base",
             "trafego": "Tráfego", "concreto": "Concreto",
             "memoria": "Memória de cálculo", "resultado": "Resultado"}
    if tela_id.startswith("crit_"):
        return tri.PERGUNTAS[tela_id[5:]][0]
    return fixos.get(tela_id, tela_id)


def resumo_de(tela_id: str) -> str:
    """Resumo de 1 linha da escolha feita naquela tela (p/ o cartao concluido)."""
    try:
        if tela_id == "modo":
            return _MODOS.get(ss.get("modo_projeto", ""), ("—",))[0]
        if tela_id == "rodovia":
            s = ss.get("posto_sel")
            return (f"BR-{s['br']:03d} ({s['lugar']}) · VMDa {s['vmda']:,}"
                    .replace(",", ".") if s else "—")
        if tela_id == "local_mapa":
            sub = ss.get("subleito")
            if sub is not None and sub.classe_aashto:
                onde = sub.municipio or "ponto marcado"
                return f"{onde} · {sub.classe_aashto} · k0 ≈ {sub.k0_estimado:.0f} MPa/m"
            return "—"
        if tela_id.startswith("crit_"):
            k = tela_id[5:]
            v = ss.get(f"tri_{k}")
            return tri.PERGUNTAS[k][1].get(v, "—")
        if tela_id == "triagem_resumo":
            sc = ss.get("triagem_score")
            if sc is None:
                return "—"
            emoji, _n, _t = tri.recomendacao(sc)
            return f"{emoji} score {sc}/{tri.SCORE_MAX}"
        if tela_id == "local_manual":
            return f"k0 = {ss.get('k0', 0):.0f} MPa/m"
        if tela_id == "subbase":
            return (f"{ss.get('tipo_sb', '—')} · k efetivo "
                    f"{ss.get('k_efetivo', 0):.0f} MPa/m")
        if tela_id == "trafego":
            return (f"VMDa {ss.get('vmda', 0):,.0f} · "
                    f"{ss.get('n_pesados', 0):,.0f} eixos no período").replace(",", ".")
        if tela_id == "concreto":
            return (f"fctk {ss.get('fctk', 4.8):.1f} MPa · FSC {ss.get('fsc', 1.2):.1f} · "
                    f"acostamento {ss.get('acost', 'Sem').lower()} · "
                    f"barras {ss.get('barras', 'Sem').lower()}")
        if tela_id == "memoria":
            r = ss.get("dim_resultado")
            return f"h = {r.h_cm:.1f} cm".replace(".", ",") if r else "—"
    except Exception:
        return "—"
    return ""


def tela_triagem_resumo() -> bool:
    with st.container(border=True):
        ui.pergunta("Vale a pena usar pavimento rígido?",
                    "Resultado da triagem — orientativo: você pode prosseguir para o "
                    "dimensionamento de qualquer forma.")
        vals = {k: ss.get(f"tri_{k}", 1) for k in _CRIT_ORDEM}
        sc = tri.score(vals)
        ss["triagem_score"] = sc
        emoji, _nivel, texto = tri.recomendacao(sc)
        pct = 100 * sc / tri.SCORE_MAX
        st.markdown(f"### {emoji} Score {sc}/{tri.SCORE_MAX} ({pct:.0f}%)")
        (st.success if pct >= 70 else st.warning if pct >= 40 else st.error)(texto)
        fontes = ss.get("tri_fonte") or {}
        st.dataframe(pd.DataFrame([{
            "Critério": tri.PERGUNTAS[k][0],
            "Resposta": tri.PERGUNTAS[k][1][vals[k]],
            "Peso": tri.PESOS[k],
            "Origem": ("automática (local)" if k in fontes and
                       ss.get("modo_projeto") in ("rodovia", "local") else "manual"),
        } for k in _CRIT_ORDEM]), hide_index=True, use_container_width=True)
        if pct < 70:
            st.caption("💰 Na tela de Resultado o app compara o custo de ciclo de vida "
                       "(LCCA) rígido × flexível para apoiar essa decisão.")
    return True


# ---------------------------------------------------------------
# ETAPA 4 - Concreto & Placa
# ---------------------------------------------------------------
def tela_concreto() -> bool:
    with st.container(border=True):
        ui.pergunta("Como será o concreto da placa?",
                    "Acostamento e barras mudam as tabelas do método; fctk e FSC "
                    "têm defaults do manual — ajuste se tiver dado de projeto.")
        cA, cB = st.columns(2)
        acost = cA.radio("Acostamento de concreto", ["Sem", "Com"], key="w_acost",
                         help="Acostamento de concreto ligado à placa reduz a tensão de "
                              "borda e a erosão (muda os Quadros 12–23 do IPR-714). "
                              "Reduz bastante a espessura necessária.")
        barras = cB.radio("Barras de transferência", ["Sem", "Com"], key="w_barras",
                          help="Barras de aço lisas nas juntas transversais transferem "
                               "carga entre placas e reduzem a erosão (Quadros 16–23). "
                               "Prática usual em rodovias.")
        with st.expander("Parâmetros do concreto (avançado)"):
            fctk = st.number_input("Resistência à tração na flexão fctk (MPa)",
                                   3.0, 6.0, ss.get("fctk", 4.8), 0.1, key="w_fctk",
                                   help="Resistência característica à tração na flexão aos "
                                        "28 dias (ensaio NBR 12142). O exemplo do IPR-714 "
                                        "usa 4,8 MPa; usual em pavimentos: 4,5–5,0 MPa.")
            fsc = st.select_slider("Fator de segurança de cargas (FSC)",
                                   options=[1.0, 1.1, 1.2, 1.3, 1.4, 1.5],
                                   value=ss.get("fsc", 1.2), key="w_fsc",
                                   help="Quadro 9 do IPR-714: 1,0 estacionamentos/vias "
                                        "secundárias · 1,1 volume moderado de pesados · "
                                        "1,2 alto volume · até 1,5 casos especiais.")
        ss["acost"] = acost
        ss["barras"] = barras
        ss["fctk"] = fctk
        ss["fsc"] = fsc
    return True


# ---------------------------------------------------------------
# Helpers da memoria de calculo
# ---------------------------------------------------------------
def _v(x, dec=2):
    return f"{x:.{dec}f}".replace(".", ",")


def _bignum(n):
    import math
    if n >= 1e19:
        return r"\text{ilimitado}"
    if n >= 1e5:
        e = int(math.floor(math.log10(n))); m = n / 10 ** e
        return rf"{_v(m, 2)}\times10^{{{e}}}"
    return f"{n:,.0f}".replace(",", ".")


def _param_do_estado() -> c.ParametrosProjeto:
    return c.ParametrosProjeto(
        fctk_mpa=ss.get("fctk", 4.8), k_mpa_m=ss.get("k_efetivo", 50.0), fsc=ss.get("fsc", 1.2),
        acostamento=(c.TipoAcostamento.COM_CONCRETO if ss.get("acost") == "Com"
                     else c.TipoAcostamento.SEM_CONCRETO),
        com_barras_transferencia=(ss.get("barras") == "Com"),
        espectro=ss.get("espectro") or [])


def _memoria_faixa(d, fsc: float) -> None:
    triplo = d.faixa.eixo == c.TipoEixo.TANDEM_TRIPLO
    extra = r"\,/\,3" if triplo else ""
    st.markdown("**1. Carga efetiva** (carga × FSC" + (", tandem triplo ÷3" if triplo else "") + "):")
    st.latex(rf"P_{{ef}} = {_v(d.faixa.carga_tf)} \times {_v(fsc)}{extra} = {_v(d.carga_efetiva)}\ \text{{tf}}")
    st.markdown("**2. Tensão equivalente** (interpolada dos Quadros 12–15, função de *h* e *k*):")
    st.latex(rf"\sigma_{{eq}} = {_v(d.sigma_eq, 3)}\ \text{{MPa}}")
    st.markdown("**3. Relação de tensões** (a tensão escala com a carga elevada a 0,94):")
    st.latex(rf"SR = \frac{{\sigma_{{eq}}}}{{f_{{ctk}}}}\left(\frac{{P_{{ef}}}}{{P_{{pad}}}}\right)^{{0{{,}}94}}"
             rf" = \frac{{{_v(d.sigma_eq, 3)}}}{{{_v(d.mr)}}}"
             rf"\left(\frac{{{_v(d.carga_efetiva)}}}{{{_v(d.carga_padrao)}}}\right)^{{0{{,}}94}} = {_v(d.sr, 3)}")
    st.markdown("**4. Repetições admissíveis — fadiga** (equações PCA, ábaco da Fig. 27):")
    if d.n_adm_fadiga >= 1e19:
        st.latex(rf"SR = {_v(d.sr, 3)} < 0{{,}}45 \Rightarrow N_f = \text{{ilimitado}}")
    elif d.sr < 0.55:
        st.latex(rf"N_f = \left(\frac{{4{{,}}2577}}{{SR - 0{{,}}4325}}\right)^{{3{{,}}268}} = {_bignum(d.n_adm_fadiga)}")
    else:
        st.latex(rf"\log_{{10}} N_f = 11{{,}}737 - 12{{,}}077\,SR \Rightarrow N_f = {_bignum(d.n_adm_fadiga)}")
    st.markdown("**5. Consumo de fadiga:**")
    st.latex(rf"CF = \frac{{N_{{prev}}}}{{N_f}}\times 100 = {_v(d.consumo_fadiga_pct)}\%")
    st.markdown("**6. Erosão** (fator de erosão dos Quadros 16–23; repetições pelo ábaco Fig. 28/29):")
    st.latex(rf"FE = {_v(d.fator_erosao, 3)} \qquad N_e = {_bignum(d.n_adm_erosao)}")
    st.markdown("**7. Consumo de erosão:**")
    st.latex(rf"CE = \frac{{N_{{prev}}}}{{N_e}}\times 100 = {_v(d.consumo_erosao_pct)}\%")


# ---------------------------------------------------------------
# ETAPA 5 - Memoria de calculo (transparencia)
# ---------------------------------------------------------------
def tela_memoria() -> bool:
    ui.pergunta("Memória de cálculo",
                "Como a espessura é obtida, passo a passo — método PCA 1984 (DNIT IPR-714).")
    if not (ss.get("espectro") or []):
        st.warning("Sem espectro de tráfego. Volte à etapa de Tráfego.")
        return True
    p = _param_do_estado()
    res = c.dimensionar(p)
    ss["dim_param"] = p
    ss["dim_resultado"] = res
    if res is None:
        st.error("Nenhuma espessura entre 10 e 40 cm atendeu aos critérios "
                 "(Σ fadiga e Σ erosão ≤ 100%). Reveja k, fctk ou o tráfego.")
        return True

    ac = ss.get("acost", "Sem"); ba = ss.get("barras", "Sem")
    st.markdown(f"**Premissas:** f_ctk = {_v(p.fctk_mpa, 1)} MPa · k = {p.k_mpa_m:.0f} MPa/m · "
                f"FSC = {_v(p.fsc)} · acostamento {ac} · barras {ba}.")
    st.markdown("**Critério:** testa-se *h* de 10 a 40 cm e adota-se a **menor** espessura cujo "
                "consumo de **fadiga** e de **erosão** fique ≤ 100%.")
    st.success(f"Espessura adotada: **h = {res.h_cm:.1f} cm**")
    st.divider()
    st.markdown(f"#### Verificação de h = {res.h_cm:.1f} cm, por classe de eixo")
    for d in res.detalhes:
        rot = (f"{d.faixa.eixo.value} · {_v(d.faixa.carga_tf, 1)} tf · "
               f"{d.faixa.repeticoes_previstas:,.0f} rep. → "
               f"fadiga {_v(d.consumo_fadiga_pct)}% / erosão {_v(d.consumo_erosao_pct)}%")
        with st.expander(rot):
            _memoria_faixa(d, p.fsc)
    st.divider()
    st.markdown(f"**Somatório — fadiga:** Σ CF = **{_v(res.soma_fadiga_pct, 1)} %** · "
                f"**erosão:** Σ CE = **{_v(res.soma_erosao_pct, 1)} %**")
    ok = res.soma_fadiga_pct <= 100 and res.soma_erosao_pct <= 100
    (st.success if ok else st.error)(
        f"Ambos os critérios {'≤' if ok else '>'} 100% → h = {res.h_cm:.1f} cm "
        f"{'aprovada' if ok else 'reprovada'}.")
    return True


# ---------------------------------------------------------------
# ETAPA 6 - Resultado
# ---------------------------------------------------------------
@st.cache_data(show_spinner=False)
def _tornado_cached(fctk: float, k: float, fsc: float, acost_val: str,
                    barras: bool, espectro_t: tuple):
    """Tornado cacheado por parametros hashables (recalcula so quando algo muda)."""
    espectro = [c.FaixaCarga(c.TipoEixo(t), carga, rep)
                for t, carga, rep in espectro_t]
    p = c.ParametrosProjeto(
        fctk_mpa=fctk, k_mpa_m=k, fsc=fsc,
        acostamento=c.TipoAcostamento(acost_val),
        com_barras_transferencia=barras, espectro=espectro)
    return sens.tornado(p)


def tela_resultado() -> bool:
    ui.pergunta("Resultado do dimensionamento")
    if not (ss.get("espectro") or []):
        st.warning("Sem espectro de tráfego. Volte à etapa de Tráfego.")
        return True
    p = ss.get("dim_param") or _param_do_estado()
    resultado = ss["dim_resultado"] if "dim_resultado" in ss else c.dimensionar(p)
    curva = c.curva_sensibilidade(p)

    if resultado is None:
        st.error("Nenhuma espessura entre 10 e 40 cm satisfez os critérios. "
                 "Reveja k, fctk ou o tráfego (detalhes na Memória de cálculo).")
    else:
        aprovada = (resultado.soma_fadiga_pct <= 100
                    and resultado.soma_erosao_pct <= 100)
        ui.resultado_destaque(resultado.h_cm, aprovada)
        ui.barra_consumo("Consumo de fadiga", resultado.soma_fadiga_pct)
        ui.barra_consumo("Consumo de erosão", resultado.soma_erosao_pct)
        st.caption("Menor espessura (passo 0,5 cm) em que fadiga E erosão ficam ≤ 100% "
                   "— critério duplo do método PCA 1984 (IPR-714). "
                   "O passo a passo está na etapa Memória de cálculo.")

    hs = [r.h_cm for r in curva]
    fig, ax = plt.subplots(figsize=(8, 3.6))
    ax.plot(hs, [min(r.soma_fadiga_pct, 200) for r in curva], label="Fadiga (%)", marker=".")
    ax.plot(hs, [min(r.soma_erosao_pct, 200) for r in curva], label="Erosão (%)", marker=".")
    ax.axhline(100, color="#c62828", ls="--", lw=1, label="Limite 100%")
    if resultado:
        ax.axvline(resultado.h_cm, color="#2e7d32", ls=":", lw=1.5, label=f"h = {resultado.h_cm:.1f} cm")
    ax.set_xlabel("Espessura h (cm)"); ax.set_ylabel("Consumo (%)"); ax.set_ylim(0, 200)
    ax.legend(); ax.grid(alpha=0.3)
    st.pyplot(fig)

    # Analise de sensibilidade (tornado) — reativa, com cache por parametros
    if resultado is not None:
        with st.expander("🔬 Análise de sensibilidade (tornado)"):
            st.caption("Cada parâmetro é variado em ±20% (demais fixos) e o "
                       "dimensionamento é refeito. As barras mostram o efeito "
                       "na espessura final (Δh, cm).")
            espectro_t = tuple((f.eixo.value, f.carga_tf, f.repeticoes_previstas)
                               for f in p.espectro)
            try:
                with st.spinner("Calculando (±20% em cada parâmetro)…"):
                    h_b, linhas = _tornado_cached(
                        p.fctk_mpa, p.k_mpa_m, p.fsc, p.acostamento.value,
                        p.com_barras_transferencia, espectro_t)
                st.pyplot(sens.grafico_tornado(h_b, linhas))
                if any(ln.estourou for ln in linhas):
                    st.warning("Em algum cenário nenhuma espessura ≤ 40 cm "
                               "atendeu os critérios (barra truncada em 40,5 cm).")
            except ValueError as exc:
                st.error(str(exc))

    # Recomendacao de sub-base + custo
    st.markdown("#### 🧱 Recomendação de sub-base")
    rec = rsb.recomendar(ss.get("n_pesados", 0), ss.get("k0", 50.0))
    st.caption(f"Tráfego **{rec.nivel_trafego}** · subleito **{rec.nivel_subleito}** "
               f"(k0 ≈ {ss.get('k0', 50):.0f})")
    escolhido = ss.get("tipo_sb")
    if rec.tipo_recomendado == escolhido:
        st.success(f"Recomendado: **{rec.tipo_recomendado}** — coincide com a sua escolha. {rec.justificativa}")
    else:
        st.info(f"Recomendado: **{rec.tipo_recomendado}** (você escolheu *{escolhido}*). {rec.justificativa}")
    st.dataframe(pd.DataFrame([{
        "Sub-base": o["tipo"],
        "k efetivo (MPa/m)": (round(o["k_efetivo"]) if o["k_efetivo"] is not None else None),
        "Custo (R$/m³)": o["custo_m3"],
        "Ganho de k": (round(o["ganho_k"]) if o["ganho_k"] is not None else None),
        "": ("★ recomendada" if o["nota"] else
             ("💰 custo-efetiva" if o["tipo"] == rec.mais_custo_efetiva else "")),
    } for o in rec.opcoes]), use_container_width=True, hide_index=True)
    st.caption(f"k efetivo p/ {rsb.ESP_REF_CM:.0f} cm · {rec.ressalva}")

    # --- Custo de ciclo de vida (LCCA) ---
    lcca_res = None
    if resultado is not None:
        st.markdown("#### 💰 Custo de ciclo de vida (LCCA)")
        st.caption("Comparação em VPL por m²: rígido dimensionado × flexível de "
                   "**referência** (não dimensionado — CBUQ pela tabela do IPR-719 "
                   "+ base granular). Custos SICRO RJ jan/2026.")
        n_total = sum(f.repeticoes_previstas for f in p.espectro)
        cA, cB, cC = st.columns(3)
        horizonte = cA.slider("Horizonte (anos)", 20, 40, lc.HORIZONTE_PADRAO,
                              5, key="w_lcca_hor")
        taxa = cB.slider("Taxa de desconto (% a.a.)", 4.0, 12.0,
                         lc.TAXA_DESCONTO_PADRAO * 100, 0.5, key="w_lcca_tx") / 100
        esp_cbuq = cC.number_input(
            "CBUQ do flexível (cm)", 5.0, 20.0,
            lc.espessura_cbuq_cm(n_total), 0.5, key="w_lcca_cbuq",
            help="Default: tabela de espessura mínima do IPR-719 pela faixa de N.")
        lcca_res = lc.comparar(
            h_cm=resultado.h_cm,
            tipo_subbase=ss.get("tipo_sb") or "Sem sub-base",
            esp_subbase_cm=float(ss.get("esp_sb") or 0),
            n_eixo_padrao=n_total, horizonte=horizonte, taxa=taxa,
            esp_cbuq_cm=esp_cbuq)
        c1, c2 = st.columns(2)
        c1.metric("VPL rígido", f"R$ {lcca_res.vpl_rigido:,.2f}/m²".replace(",", "@").replace(".", ",").replace("@", "."),
                  f"CAPEX R$ {lcca_res.rigido.capex_m2:.2f}/m²".replace(".", ","),
                  delta_color="off")
        c2.metric("VPL flexível (ref.)", f"R$ {lcca_res.vpl_flexivel:,.2f}/m²".replace(",", "@").replace(".", ",").replace("@", "."),
                  f"CAPEX R$ {lcca_res.flexivel.capex_m2:.2f}/m²".replace(".", ","),
                  delta_color="off")
        anos = list(range(horizonte + 1))
        figl, axl = plt.subplots(figsize=(8, 3.2))
        axl.step(anos, lcca_res.rigido.acumulado_vp(horizonte, taxa),
                 where="post", label="Rígido", color="#2E3A40", lw=2)
        axl.step(anos, lcca_res.flexivel.acumulado_vp(horizonte, taxa),
                 where="post", label="Flexível (ref.)", color="#E8A33D", lw=2)
        if lcca_res.ano_cruzamento:
            axl.axvline(lcca_res.ano_cruzamento, color="#c62828", ls=":",
                        label=f"Cruzamento (ano {lcca_res.ano_cruzamento})")
        axl.set_xlabel("Ano"); axl.set_ylabel("Custo acumulado (VP, R$/m²)")
        axl.legend(); axl.grid(alpha=0.3)
        st.pyplot(figl)
        if lcca_res.vantagem_rigido:
            msg = f"No horizonte de {horizonte} anos, o **rígido** tem menor custo de ciclo de vida"
            if lcca_res.ano_cruzamento:
                msg += f" — o custo acumulado cruza no ano {lcca_res.ano_cruzamento}"
            st.success(msg + ".")
        else:
            st.info(f"No horizonte de {horizonte} anos, o **flexível de referência** "
                    "resulta mais barato em VPL. Fatores não monetizados aqui "
                    "(interrupções de tráfego nos recapes, vida residual, CO₂) "
                    "tendem a favorecer o rígido — discuta na análise.")
        with st.expander("Memória de custos (de onde veio cada número)"):
            for alt in (lcca_res.rigido, lcca_res.flexivel):
                st.markdown(f"**{alt.nome}** — CAPEX R$ {alt.capex_m2:.2f}/m²".replace(".", ","))
                for ln_ in alt.memoria:
                    st.caption("• " + ln_)
            st.caption(f"Manutenção: rígido = resselagem anos {lc.ANOS_SELAGEM} + reparo "
                       f"{lc.FRAC_AREA_REPARO:.0%} das placas no ano {lc.ANO_REPARO_PLACAS}; "
                       f"flexível = recape {lc.RECAP_ESP_CM:.0f} cm anos {lc.ANOS_RECAP} "
                       f"+ conserva {lc.CONSERVA_FLEX_FRAC:.1%}/ano. Fonte: SICRO RJ jan/2026.")

    # --- Exportar PDF ---
    st.markdown("---")
    st.markdown("#### 📄 Exportar relatório")
    if resultado is not None:
        sub = ss.get("subleito")
        ctx = rel.ContextoRelatorio(
            local=ss.get("municipio") or (ss.get("ponto_obra") and
                  f"({ss['ponto_obra'][0]:.4f}, {ss['ponto_obra'][1]:.4f})"),
            tipo_solo=((sub.ordem_sibcs + " · AASHTO " + sub.classe_aashto)
                       if sub and sub.classe_aashto else None),
            cbr_estimado=(sub.cbr_estimado if sub else ss.get("cbr_val")),
            k0_subleito=ss.get("k0"),
            tipo_subbase=ss.get("tipo_sb"),
            esp_subbase_cm=(ss.get("esp_sb") or 0) or None,
            vmda=ss.get("vmda") or ss.get("vmda_man"),
            periodo_anos=ss.get("periodo"),
            triagem_score=ss.get("triagem_score"),
            triagem_score_max=float(tri.SCORE_MAX),
            subbase_recomendada=rec.tipo_recomendado,
            subbase_justificativa=rec.justificativa,
        )
        try:
            pdf_bytes = rel.gerar_pdf(p, resultado, curva, ctx, lcca_res=lcca_res)
            st.download_button(
                label="⬇️ Baixar Relatório em PDF",
                data=pdf_bytes,
                file_name="relatorio_pavimento_rigido.pdf",
                mime="application/pdf",
                type="primary",
                use_container_width=True,
            )
        except Exception as e:
            st.error(f"Erro ao gerar PDF: {e}")
    else:
        st.info("Corrija os parâmetros para gerar o PDF.")
    return True
