"""
_proto_nicegui.py - PROTOTIPO (DEV) da tela de Resultado em NiceGUI.

Objetivo: comparar visualmente com o Streamlit (Fase 1.7 do PLANO_UX) e decidir
se vale migrar a camada de UI. NAO faz parte do app; usa o MESMO backend
(calculos/lcca/sensibilidade/recomenda_subbase) com o espectro do manual.

Rodar:  python _proto_nicegui.py   ->  http://localhost:8502
"""
from __future__ import annotations

import base64
import io

from nicegui import ui

import calculos as c
import lcca as lc
import recomenda_subbase as rsb
import sensibilidade as sens
from validar_e2e import ESPECTRO_ES

# ---------------- dados (mesmo caso do manual) ----------------
P = c.ParametrosProjeto(
    fctk_mpa=4.8, k_mpa_m=100.0, fsc=1.2,
    acostamento=c.TipoAcostamento.SEM_CONCRETO,
    com_barras_transferencia=False,
    espectro=[c.FaixaCarga(c.TipoEixo.SIMPLES, carga, n) for carga, n in ESPECTRO_ES])
RES = c.dimensionar(P)
CURVA = c.curva_sensibilidade(P)
N_TOTAL = sum(f.repeticoes_previstas for f in P.espectro)
LCCA = lc.comparar(RES.h_cm, "Solo-cimento", 15.0, N_TOTAL)
REC = rsb.recomendar(N_TOTAL, 50.0)
H_B, LINHAS = sens.tornado(P)

AMBAR = "#C8861F"
ASFALTO = "#2E3A40"


def _fig_b64(fig) -> str:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=130, bbox_inches="tight")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def _fmt(x: float, dec: int = 1) -> str:
    return f"{x:.{dec}f}".replace(".", ",")


def barra(rotulo: str, pct: float) -> None:
    cor = "#2e7d32" if pct < 70 else (AMBAR if pct <= 100 else "#c62828")
    with ui.column().classes("w-full gap-1"):
        with ui.row().classes("w-full justify-between"):
            ui.label(rotulo).classes("text-sm font-semibold text-slate-700")
            ui.label(f"{_fmt(pct)}%").classes("text-sm font-bold").style(f"color:{cor}")
        with ui.element("div").classes("w-full h-3 rounded-full bg-slate-100 overflow-hidden"):
            ui.element("div").classes("h-full rounded-full transition-all") \
                .style(f"width:{min(pct, 100):.1f}%;background:{cor}")


ui.add_head_html("""
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap" rel="stylesheet">
<style>
  * { font-family: 'Inter', sans-serif; }
  body { background: #F6F8FA; }
</style>""")

with ui.column().classes("w-full max-w-3xl mx-auto p-4 gap-4"):

    # cabecalho
    with ui.row().classes("w-full items-center gap-3 bg-white rounded-2xl p-4 shadow-sm border border-slate-100"):
        ui.label("🛣️").classes("text-2xl bg-amber-50 rounded-xl px-3 py-1")
        with ui.column().classes("gap-0"):
            ui.label("Dimensionamento de Pavimentos Rígidos") \
                .classes("text-lg font-extrabold tracking-tight text-slate-800")
            ui.label("Método PCA 1984 — DNIT IPR-714 · protótipo NiceGUI") \
                .classes("text-xs text-slate-400")
        ui.space()
        ui.badge("Etapa 7 de 7", color="amber").props("outline")

    # cartao-heroi
    with ui.column().classes("w-full items-center rounded-2xl p-8 gap-1 shadow-lg") \
            .style(f"background:linear-gradient(115deg,{ASFALTO},#3D4A52)"):
        ui.label("ESPESSURA DA PLACA DE CONCRETO") \
            .classes("text-xs tracking-widest text-slate-300")
        with ui.row().classes("items-baseline gap-1"):
            ui.label(_fmt(RES.h_cm)).classes("text-7xl font-extrabold").style(f"color:{AMBAR}")
            ui.label("cm").classes("text-2xl font-semibold text-slate-200")
        ui.badge("✓ APROVADA — fadiga e erosão ≤ 100%", color="green").classes("mt-2 px-3 py-1")

    # consumos
    with ui.card().classes("w-full rounded-2xl shadow-sm border border-slate-100 gap-3"):
        ui.label("Consumo dos critérios").classes("font-bold text-slate-800")
        barra("Fadiga", RES.soma_fadiga_pct)
        barra("Erosão", RES.soma_erosao_pct)
        ui.label("Menor espessura (passo 0,5 cm) em que fadiga E erosão ficam ≤ 100% — "
                 "critério duplo do PCA 1984.").classes("text-xs text-slate-400")

    # curva h x consumo (ECharts interativo)
    with ui.card().classes("w-full rounded-2xl shadow-sm border border-slate-100"):
        ui.label("Espessura × consumo").classes("font-bold text-slate-800")
        hs = [r.h_cm for r in CURVA]
        ui.echart({
            "tooltip": {"trigger": "axis"},
            "legend": {"bottom": 0},
            "grid": {"left": 45, "right": 20, "top": 20, "bottom": 55},
            "xAxis": {"type": "category", "data": [f"{h:g}" for h in hs],
                      "name": "h (cm)", "nameLocation": "middle", "nameGap": 28},
            "yAxis": {"type": "value", "max": 200, "name": "consumo (%)"},
            "series": [
                {"name": "Fadiga (%)", "type": "line", "smooth": True, "showSymbol": False,
                 "lineStyle": {"width": 3}, "color": "#1565C0",
                 "data": [round(min(r.soma_fadiga_pct, 200), 1) for r in CURVA]},
                {"name": "Erosão (%)", "type": "line", "smooth": True, "showSymbol": False,
                 "lineStyle": {"width": 3}, "color": AMBAR,
                 "data": [round(min(r.soma_erosao_pct, 200), 1) for r in CURVA],
                 "markLine": {"symbol": "none", "lineStyle": {"color": "#c62828"},
                              "label": {"formatter": "limite 100%"},
                              "data": [{"yAxis": 100}]}},
            ],
        }).classes("w-full h-64")

    # LCCA
    with ui.card().classes("w-full rounded-2xl shadow-sm border border-slate-100 gap-3"):
        ui.label("💰 Custo de ciclo de vida (30 anos, 8% a.a.)").classes("font-bold text-slate-800")
        with ui.row().classes("w-full gap-3"):
            for nome, vpl, capex in (("Rígido", LCCA.vpl_rigido, LCCA.rigido.capex_m2),
                                     ("Flexível (ref.)", LCCA.vpl_flexivel, LCCA.flexivel.capex_m2)):
                with ui.column().classes("flex-1 bg-slate-50 rounded-xl p-4 gap-0"):
                    ui.label(nome).classes("text-xs text-slate-400 font-semibold")
                    ui.label(f"R$ {_fmt(vpl, 2)}/m²").classes("text-2xl font-extrabold text-slate-800")
                    ui.label(f"CAPEX R$ {_fmt(capex, 2)}/m²").classes("text-xs text-slate-400")
        anos = list(range(LCCA.horizonte + 1))
        ui.echart({
            "tooltip": {"trigger": "axis"},
            "legend": {"bottom": 0},
            "grid": {"left": 50, "right": 20, "top": 20, "bottom": 55},
            "xAxis": {"type": "category", "data": anos, "name": "ano",
                      "nameLocation": "middle", "nameGap": 28},
            "yAxis": {"type": "value", "name": "R$/m² (VP)"},
            "series": [
                {"name": "Rígido", "type": "line", "step": "end", "showSymbol": False,
                 "lineStyle": {"width": 3}, "color": ASFALTO,
                 "data": [round(v, 2) for v in LCCA.rigido.acumulado_vp(LCCA.horizonte, LCCA.taxa)]},
                {"name": "Flexível (ref.)", "type": "line", "step": "end", "showSymbol": False,
                 "lineStyle": {"width": 3}, "color": AMBAR,
                 "data": [round(v, 2) for v in LCCA.flexivel.acumulado_vp(LCCA.horizonte, LCCA.taxa)]},
            ],
        }).classes("w-full h-64")

    # sensibilidade (matplotlib embutido, como hoje)
    with ui.expansion("🔬 Análise de sensibilidade (tornado)").classes(
            "w-full bg-white rounded-2xl shadow-sm border border-slate-100"):
        ui.image(_fig_b64(sens.grafico_tornado(H_B, LINHAS))).classes("w-full")

    # recomendacao de sub-base
    with ui.card().classes("w-full rounded-2xl shadow-sm border border-slate-100 gap-2"):
        ui.label("🧱 Recomendação de sub-base").classes("font-bold text-slate-800")
        ui.label(f"Recomendada: {REC.tipo_recomendado} — {REC.justificativa}") \
            .classes("text-sm text-slate-600")
        ui.table(
            columns=[{"name": "t", "label": "Sub-base", "field": "t", "align": "left"},
                     {"name": "k", "label": "k efetivo", "field": "k"},
                     {"name": "c", "label": "R$/m³", "field": "c"},
                     {"name": "g", "label": "Ganho de k", "field": "g"}],
            rows=[{"t": o["tipo"],
                   "k": (round(o["k_efetivo"]) if o["k_efetivo"] is not None else "—"),
                   "c": o["custo_m3"],
                   "g": (round(o["ganho_k"]) if o["ganho_k"] is not None else "—")}
                  for o in REC.opcoes],
        ).classes("w-full").props("flat dense")

    with ui.row().classes("w-full justify-end gap-2 pb-8"):
        ui.button("⬇️ Baixar relatório PDF").props("outline color=grey-8 rounded")
        ui.button("↻ Recomeçar", color="amber-8").props("rounded").classes("text-white")


ui.run(port=8502, reload=False, show=False, title="Protótipo NiceGUI — Resultado")
