"""
ui.py - Identidade visual e componentes de UI do assistente (tema infra/ambar).

Paleta: cinza-asfalto (#2E3A40) + ambar (#E8A33D). Helpers:
  injetar_css()      - CSS global (esconde chrome do Streamlit, cartao, botoes, stepper)
  cabecalho()        - faixa superior asfalto com titulo
  stepper(atual)     - barra de progresso das 5 etapas
  pergunta()         - titulo grande de uma tela
  resumo_sidebar()   - resumo das escolhas (contexto enquanto avanca)
"""
from __future__ import annotations

import streamlit as st

ASFALTO = "#2E3A40"
ASFALTO_2 = "#3D4A52"
AMBAR = "#E8A33D"
AMBAR_ESC = "#C8861F"
CINZA = "#ECEFF1"
CINZA_BORDA = "#CFD8DC"
TEXTO = "#22303A"

ETAPAS = [
    (1, "Início"),
    (2, "Viabilidade"),
    (3, "Fundação"),
    (4, "Tráfego"),
    (5, "Concreto"),
    (6, "Mem. cálculo"),
    (7, "Resultado"),
]


def injetar_css() -> None:
    st.markdown(f"""
    <style>
      @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap');

      #MainMenu, footer, header [data-testid="stToolbar"] {{ visibility: hidden; }}
      .block-container {{ padding-top: 1.1rem; max-width: 860px; }}

      /* ---- tipografia Omni-like (Inter), sem tocar nas fontes de icone ---- */
      .stApp h1, .stApp h2, .stApp h3, .stApp h4,
      .stApp p, .stApp label, .stMarkdown, .stButton button p,
      .pergunta, .ajuda, .cab, .heroi, .feito, .consumo, .step, .step-info,
      .resumo-item, input, textarea {{
        font-family: 'Inter', 'Segoe UI', sans-serif !important;
      }}

      /* ---- visual clean: fundo suave + cartoes com sombra leve ---- */
      .stApp {{ background: #F7F9FA; }}

      /* inputs flat de borda fina (estilo Omni) */
      [data-baseweb="input"], [data-baseweb="select"] > div,
      [data-baseweb="textarea"] {{
        border-radius: 10px !important; border-color: #E3E8EC !important;
      }}
      [data-baseweb="input"]:focus-within, [data-baseweb="select"] > div:focus-within {{
        border-color: {AMBAR_ESC} !important;
      }}
      div[data-testid="stVerticalBlockBorderWrapper"] {{
        background: #fff; border: 1px solid #EDF0F2; border-radius: 16px;
        box-shadow: 0 1px 2px rgba(20,30,40,.04), 0 10px 28px -20px rgba(20,30,40,.28);
        animation: aparecer .28s ease;
      }}
      @keyframes aparecer {{ from {{ opacity: 0; transform: translateY(12px); }}
                             to   {{ opacity: 1; transform: none; }} }}

      /* cartao compacto de etapa concluida (fluxo vertical) */
      .feito {{ background: #fff; border: 1px solid #EDF0F2; border-radius: 12px;
                padding: .5rem .9rem; margin: .15rem 0; font-size: .9rem;
                color: #7a8a92; display: flex; align-items: baseline; gap: .45rem;
                box-shadow: 0 1px 2px rgba(20,30,40,.03); }}
      .feito .check {{ color: #2e7d32; font-weight: 800; }}
      .feito b {{ color: {TEXTO}; }}
      .feito .res {{ overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}

      .pergunta {{ font-size: 1.55rem; font-weight: 800; color: {TEXTO};
                   letter-spacing: -.015em; margin: .15rem 0 .2rem; line-height: 1.22; }}
      .ajuda {{ color: #5b6b73; font-size: .95rem; margin-bottom: 1.1rem; line-height: 1.5; }}

      .stButton > button {{ border-radius: 10px; font-weight: 700;
                            border: 1px solid #E3E8EC; background: #fff; }}
      .stButton > button:hover {{ border-color: {AMBAR_ESC}; color: {AMBAR_ESC}; }}
      .stButton > button[kind="primary"] {{ background: {AMBAR_ESC};
                            border-color: {AMBAR_ESC}; color: #fff; }}
      .stButton > button[kind="primary"]:hover {{ background: #A96F15; border-color: #A96F15; }}

      /* cabecalho claro e flat (estilo Omni: branco + 1 acento) */
      .cab {{ background: #fff; border: 1px solid #EDF0F2;
              color: {TEXTO}; border-radius: 16px; padding: .8rem 1.1rem;
              display: flex; align-items: center; gap: .75rem; margin-bottom: .9rem;
              box-shadow: 0 1px 2px rgba(20,30,40,.04); }}
      .cab .ico {{ font-size: 1.35rem; background: #FDF3E2; border-radius: 12px;
                   padding: .35rem .55rem; }}
      .cab .tit {{ font-size: 1.2rem; font-weight: 800; letter-spacing: -.015em; }}
      .cab .sub {{ font-size: .8rem; color: #7a8a92; }}

      /* stepper responsivo */
      .stepper {{ display: flex; gap: .35rem; margin: .1rem 0 1rem; }}
      .step {{ flex: 1 1 0; min-width: 0; text-align: center; font-size: .74rem;
               color: #9aa8ae; border-top: 3px solid #E8ECEF; padding-top: .35rem;
               font-weight: 600; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
      .step.on {{ color: {ASFALTO}; border-top-color: {AMBAR}; }}
      .step.done {{ color: {AMBAR_ESC}; border-top-color: {AMBAR}; }}
      @media (max-width: 680px) {{ .step {{ font-size: .6rem; }} }}

      /* resumo lateral */
      .resumo-item {{ font-size: .9rem; margin: .15rem 0; color: {TEXTO}; }}
      .resumo-item b {{ color: {ASFALTO}; }}

      /* cartao-heroi do resultado */
      .heroi {{ background: linear-gradient(115deg, {ASFALTO}, {ASFALTO_2});
                color: #fff; border-radius: 16px; padding: 1.3rem 1.5rem;
                text-align: center; margin: .3rem 0 1rem; }}
      .heroi .rotulo {{ font-size: .85rem; opacity: .75; text-transform: uppercase;
                        letter-spacing: .08em; }}
      .heroi .valor {{ font-size: 3.2rem; font-weight: 800; line-height: 1.1;
                       color: {AMBAR}; }}
      .heroi .unid {{ font-size: 1.4rem; font-weight: 600; opacity: .9; }}
      .heroi .selo {{ display: inline-block; margin-top: .4rem; padding: .2rem .8rem;
                      border-radius: 999px; font-size: .82rem; font-weight: 700; }}
      .heroi .selo.ok {{ background: #2e7d32; color: #fff; }}
      .heroi .selo.falha {{ background: #c62828; color: #fff; }}

      /* barra de consumo (fadiga/erosao) */
      .consumo {{ margin: .35rem 0 .6rem; }}
      .consumo .rot {{ display: flex; justify-content: space-between;
                       font-size: .88rem; font-weight: 600; color: {TEXTO}; }}
      .consumo .trilho {{ background: {CINZA}; border-radius: 999px; height: 12px;
                          overflow: hidden; margin-top: .2rem; }}
      .consumo .preenche {{ height: 100%; border-radius: 999px; }}

      /* progresso textual do stepper */
      .step-info {{ font-size: .8rem; color: #7a8a92; margin: -0.6rem 0 .9rem; }}
    </style>
    """, unsafe_allow_html=True)


def cabecalho() -> None:
    st.markdown(f"""
    <div class="cab">
      <div class="ico">🛣️</div>
      <div>
        <div class="tit">Dimensionamento de Pavimentos Rígidos</div>
        <div class="sub">Método PCA 1984 — DNIT IPR-714 · TCC UFRJ-POLI</div>
      </div>
    </div>
    """, unsafe_allow_html=True)


def stepper(etapa_atual: int) -> None:
    blocos = []
    for num, rot in ETAPAS:
        cls = "step on" if num == etapa_atual else ("step done" if num < etapa_atual else "step")
        marca = "✓ " if num < etapa_atual else f"{num}. "
        blocos.append(f'<div class="{cls}">{marca}{rot}</div>')
    total = len(ETAPAS)
    faltam = total - etapa_atual
    info = ("Última etapa — seu resultado está pronto abaixo." if faltam == 0 else
            f"Etapa {etapa_atual} de {total} · falta {faltam} para o resultado." if faltam == 1 else
            f"Etapa {etapa_atual} de {total} · faltam {faltam} para o resultado.")
    st.markdown(f'<div class="stepper">{"".join(blocos)}</div>'
                f'<div class="step-info">{info}</div>', unsafe_allow_html=True)


def cartao_feito(idx: int, titulo: str, resumo: str) -> bool:
    """Cartao compacto de etapa concluida no fluxo vertical.

    Retorna True se o usuario clicou em editar (voltar aquela etapa).
    """
    c1, c2 = st.columns([11, 1])
    res = f'<span class="res">— {resumo}</span>' if resumo else ""
    c1.markdown(f'<div class="feito"><span class="check">✓</span>'
                f'<b>{titulo}</b>{res}</div>', unsafe_allow_html=True)
    return c2.button("✏️", key=f"edit_{idx}", help=f"Editar: {titulo}")


def progresso(atual: int, total: int, rotulo: str = "Critério") -> None:
    """Barra de progresso de sub-etapa (ex.: criterio 2 de 6 da viabilidade)."""
    pct = 100.0 * atual / total
    st.markdown(f"""
    <div class="consumo">
      <div class="rot"><span>{rotulo} {atual} de {total}</span><span>{atual}/{total}</span></div>
      <div class="trilho"><div class="preenche" style="width:{pct:.0f}%;
           background:{AMBAR};"></div></div>
    </div>
    """, unsafe_allow_html=True)


def resultado_destaque(h_cm: float, aprovada: bool) -> None:
    """Cartao-heroi do resultado: a espessura em destaque + selo de status."""
    selo = ('<span class="selo ok">✓ APROVADA — fadiga e erosão ≤ 100%</span>'
            if aprovada else
            '<span class="selo falha">✗ REPROVADA — reveja os parâmetros</span>')
    st.markdown(f"""
    <div class="heroi">
      <div class="rotulo">Espessura da placa de concreto</div>
      <div class="valor">{f"{h_cm:.1f}".replace(".", ",")}<span class="unid"> cm</span></div>
      <div>{selo}</div>
    </div>
    """, unsafe_allow_html=True)


def barra_consumo(rotulo: str, pct: float) -> None:
    """Barra de consumo com cor semantica: verde <70, ambar 70-100, vermelho >100."""
    cor = "#2e7d32" if pct < 70 else (AMBAR_ESC if pct <= 100 else "#c62828")
    largura = min(pct, 100.0)
    st.markdown(f"""
    <div class="consumo">
      <div class="rot"><span>{rotulo}</span><span>{f"{pct:.1f}".replace(".", ",")}%</span></div>
      <div class="trilho"><div class="preenche" style="width:{largura:.1f}%;
           background:{cor};"></div></div>
    </div>
    """, unsafe_allow_html=True)


def pergunta(texto: str, ajuda: str = "") -> None:
    html = f'<div class="pergunta">{texto}</div>'
    if ajuda:
        html += f'<div class="ajuda">{ajuda}</div>'
    st.markdown(html, unsafe_allow_html=True)


def resumo_sidebar() -> None:
    """Resumo das escolhas feitas ate aqui (contexto na barra lateral)."""
    ss = st.session_state
    with st.sidebar:
        st.markdown("### 📋 Resumo do projeto")
        itens: list[str] = []
        sub = ss.get("subleito")
        if sub is not None and getattr(sub, "municipio", None):
            itens.append(f"<b>Local:</b> {sub.municipio}")
        if sub is not None and getattr(sub, "classe_aashto", None):
            itens.append(f"<b>Solo:</b> {sub.ordem_sibcs} · AASHTO {sub.classe_aashto}")
        if ss.get("k0"):
            itens.append(f"<b>k0 subleito:</b> {ss['k0']:.0f} MPa/m")
        if ss.get("tipo_sb"):
            itens.append(f"<b>Sub-base:</b> {ss['tipo_sb']}")
        if ss.get("k_efetivo"):
            itens.append(f"<b>k efetivo:</b> {ss['k_efetivo']:.0f} MPa/m")
        if ss.get("vmda"):
            itens.append(f"<b>VMDa:</b> {ss['vmda']:,.0f} veíc/dia")
        if ss.get("n_pesados"):
            itens.append(f"<b>Eixos (período):</b> {ss['n_pesados']:,.0f}")
        if ss.get("triagem_score") is not None:
            itens.append(f"<b>Viabilidade:</b> {ss['triagem_score']}/36")
        if itens:
            st.markdown("".join(f'<div class="resumo-item">{i}</div>' for i in itens),
                        unsafe_allow_html=True)
        else:
            st.caption("Suas escolhas aparecerão aqui conforme você avança.")
