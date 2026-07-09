"""
app.py - Assistente de dimensionamento de pavimentos rigidos (PCA 1984 / IPR-714).

Orquestrador do wizard: monta a sequencia de telas conforme o caminho escolhido,
controla a navegacao (Voltar/Avancar) e o progresso (stepper). As telas estao em
telas.py; o backend de calculo nao muda.
"""
from __future__ import annotations

import streamlit as st
import streamlit.components.v1 as components

import ui
import telas

st.set_page_config(page_title="Dimensionamento de Pavimento Rígido",
                   page_icon="🛣️", layout="centered", initial_sidebar_state="expanded")
ui.injetar_css()
ui.cabecalho()

# tela_id -> (funcao de render, etapa 1..7)
TELAS = {
    "modo":           (telas.tela_modo,           1),
    "rodovia":        (telas.tela_rodovia,        1),
    "local_mapa":     (telas.tela_local_mapa,     1),
    "triagem_resumo": (telas.tela_triagem_resumo, 2),
    "local_manual":   (telas.tela_local_manual,   3),
    "subbase":        (telas.tela_subbase,        3),
    "trafego":        (telas.tela_trafego,        4),
    "concreto":       (telas.tela_concreto,       5),
    "memoria":        (telas.tela_memoria,        6),
    "resultado":      (telas.tela_resultado,      7),
}
# telas de criterio da viabilidade (uma por criterio, com barra de progresso)
for _i, _k in enumerate(telas._CRIT_ORDEM, 1):
    TELAS[f"crit_{_k}"] = (telas.tela_criterio(_k, _i), 2)


def sequencia() -> list[str]:
    """Ordem das telas conforme o MODO do projeto (rodovia / localizacao / manual)."""
    ss = st.session_state
    modo = ss.get("modo_projeto", "rodovia")
    crit = [f"crit_{k}" for k in telas._CRIT_ORDEM] + ["triagem_resumo"]
    fim = ["subbase", "trafego", "concreto", "memoria", "resultado"]
    if modo == "rodovia":
        sub = ss.get("subleito")
        tem_solo = sub is not None and getattr(sub, "classe_aashto", None)
        extra = [] if tem_solo else ["local_manual"]
        return ["modo", "rodovia"] + crit + extra + fim
    if modo == "local":
        return ["modo", "local_mapa"] + crit + fim
    return ["modo"] + crit + ["local_manual"] + fim


st.session_state.setdefault("passo", 0)
seq = sequencia()
passo = max(0, min(st.session_state["passo"], len(seq) - 1))
st.session_state["passo"] = passo
tela_id = seq[passo]
render, etapa = TELAS[tela_id]

ui.stepper(etapa)

# --- fluxo VERTICAL: etapas concluidas empilhadas em cartoes compactos ---
for _i in range(passo):
    _tid = seq[_i]
    if ui.cartao_feito(_i, telas.titulo_de(_tid), telas.resumo_de(_tid)):
        st.session_state["passo"] = _i
        st.rerun()

valido = render()
ui.resumo_sidebar()

# --- navegacao (voltar = clicar no ✏️ de um cartao acima) ---
st.write("")
_ROTULO_AVANCAR = {"concreto": "Calcular espessura →", "memoria": "Ver resultado →"}
_, col_a = st.columns([1.6, 1])
if tela_id != "resultado":
    rotulo = _ROTULO_AVANCAR.get(tela_id, "Avançar →")
    if col_a.button(rotulo, type="primary", use_container_width=True, disabled=not valido):
        st.session_state["passo"] = passo + 1
        st.rerun()
    if not valido:
        col_a.caption("Complete a etapa para avançar.")
else:
    if col_a.button("↻ Recomeçar", use_container_width=True):
        st.session_state["passo"] = 0
        st.rerun()

# rola suavemente ate a etapa ativa quando o passo muda
if st.session_state.get("_scroll_passo") != passo:
    st.session_state["_scroll_passo"] = passo
    components.html("""
    <script>
      setTimeout(() => {
        const doc = window.parent.document;
        const alvo = doc.querySelector('section.main')
                  || doc.querySelector('[data-testid="stMain"]');
        if (alvo) alvo.scrollTo({top: alvo.scrollHeight, behavior: 'smooth'});
        else window.parent.scrollTo({top: 1e6, behavior: 'smooth'});
      }, 200);
    </script>""", height=0)
