"""
app_nicegui.py - Assistente de dimensionamento (versao NiceGUI - PLANO PRINCIPAL).

Migracao a partir da versao Streamlit (app.py/telas.py/ui.py), que fica mantida
como PLANO B (fallback) em C:\\Users\\PEDRO\\tcc_pavimentos. O backend de calculo
(calculos.py, estagio3.py, tabelas_pca.py, lcca.py, sensibilidade.py,
recomenda_subbase.py, resultados.py, dados _pnct/_solos/_mun/_clima/_sicro) e
IDENTICO e reusado sem alteracao nas duas versoes.

Rodar:  python app_nicegui.py   ->  http://localhost:8503
"""
from __future__ import annotations

from nicegui import ui

import state_ng as sng
import telas_ng as tg
import ui_ng as ung

# tela_id -> (funcao_render, etapa 1..7)
TELAS = {
    "modo":           (tg.render_modo,           1),
    "rodovia":        (tg.render_rodovia,        1),
    "local_mapa":     (tg.render_local_mapa,     1),
    "triagem_resumo": (tg.render_triagem_resumo, 2),
    "local_manual":   (tg.render_local_manual,   3),
    "subbase":        (tg.render_subbase,        3),
    "trafego":        (tg.render_trafego,        4),
    "concreto":       (tg.render_concreto,       5),
    "memoria":        (tg.render_memoria,        6),
    "resultado":      (tg.render_resultado,      7),
}
for _i, _k in enumerate(tg._CRIT_ORDEM, 1):
    TELAS[f"crit_{_k}"] = (tg.render_criterio(_k, _i), 2)


def sequencia(s: dict) -> list[str]:
    """Ordem das telas conforme o MODO do projeto (identico ao app.py Streamlit)."""
    modo = s.get("modo_projeto", "rodovia")
    crit = [f"crit_{k}" for k in tg._CRIT_ORDEM] + ["triagem_resumo"]
    fim = ["subbase", "trafego", "concreto", "memoria", "resultado"]
    if modo == "rodovia":
        sub = s.get("subleito")
        tem_solo = sub is not None and getattr(sub, "classe_aashto", None)
        extra = [] if tem_solo else ["local_manual"]
        return ["modo", "rodovia"] + crit + extra + fim
    if modo == "local":
        return ["modo", "local_mapa"] + crit + fim
    return ["modo"] + crit + ["local_manual"] + fim


@ui.page("/")
def main_page():
    ung.head()
    s = sng.get()
    s.setdefault("passo", 0)

    conteudo = ui.column().classes("w-full gap-3")

    @ui.refreshable
    def render_all():
        seq = sequencia(s)
        s["_seq"] = seq  # p/ telas pularem a etapas especificas (ex.: falha de h)
        passo = max(0, min(s["passo"], len(seq) - 1))
        s["passo"] = passo
        tela_id = seq[passo]
        render, etapa = TELAS[tela_id]

        ung.cabecalho()
        ung.stepper(etapa, frac=passo / max(1, len(seq) - 1))

        # etapas concluidas -> linhas discretas (clique = editar)
        if passo > 0:
            with ui.column().classes("w-full max-w-3xl mx-auto gap-0 mb-2"):
                for i in range(passo):
                    tid = seq[i]

                    def _editar(i=i):
                        s["passo"] = i
                        render_all.refresh()
                        ung.rolar_para_topo()

                    ung.cartao_feito(tg.titulo_de(tid), tg.resumo_de(s, tid), _editar)

        valido = render(s, render_all.refresh)

        rotulo_avancar = {"concreto": "Calcular espessura →", "memoria": "Ver resultado →"} \
            .get(tela_id, "Avançar →")
        with ui.row().classes("w-full max-w-3xl mx-auto items-center justify-end gap-3 mt-1 mb-16"):
            if tela_id != "resultado":
                def _avancar():
                    s["passo"] = passo + 1
                    render_all.refresh()
                    ung.rolar_para_fim()

                if not valido:
                    ui.label("Complete a etapa para avançar").classes("text-xs text-slate-400")
                ui.button(rotulo_avancar, on_click=_avancar) \
                    .props("color=amber-8 unelevated no-caps rounded size=lg") \
                    .classes("text-white font-bold px-8").set_enabled(valido)
            else:
                def _recomecar():
                    sng.reset()
                    s["passo"] = 0
                    render_all.refresh()

                ui.button("↻ Recomeçar", on_click=_recomecar).props("outline no-caps rounded")

    with conteudo:
        render_all()


ui.run(port=8503, reload=False, show=False, title="Dimensionamento de Pavimentos Rígidos",
      favicon="🛣️", storage_secret="tcc-pavimentos-dev")
