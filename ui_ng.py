"""
ui_ng.py - Tema e componentes visuais da versao NiceGUI (identidade Omni-like:
flat, clean, 1 acento). Espelha ui.py (Streamlit) nos nomes de funcao para
facilitar a leitura cruzada entre as duas versoes durante a migracao.
"""
from __future__ import annotations

from nicegui import ui

ASFALTO = "#2E3A40"
ASFALTO_2 = "#3D4A52"
AMBAR = "#E8A33D"
AMBAR_ESC = "#C8861F"
TEXTO = "#22303A"
VERDE = "#2e7d32"
VERMELHO = "#c62828"

ETAPAS = [
    (1, "Início"),
    (2, "Viabilidade"),
    (3, "Fundação"),
    (4, "Tráfego"),
    (5, "Concreto"),
    (6, "Mem. cálculo"),
    (7, "Resultado"),
]


def head() -> None:
    """CSS global + fontes (chamar 1x por pagina, antes de qualquer elemento)."""
    ui.add_head_html(f"""
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap" rel="stylesheet">
    <script src="https://cdnjs.cloudflare.com/ajax/libs/mathjax/3.2.2/es5/tex-mml-chtml.js"></script>
    <style>
      /* fonte no body (herdada por tudo) — NUNCA usar '*', pois mataria a fonte
         Material Icons e os icones virariam texto ("keyboard_arrow_down") */
      body {{ font-family: 'Inter', 'Segoe UI', sans-serif; background: #F7F9FA; }}
      .nicegui-content {{ padding: 1.1rem 1rem 3rem; }}
      .q-field__control {{ border-radius: 10px !important; }}
      .cartao {{ background: #fff; border: 1px solid #EDF0F2; border-radius: 16px;
                 box-shadow: 0 1px 2px rgba(20,30,40,.04), 0 10px 28px -20px rgba(20,30,40,.28); }}
      /* etapas concluidas: linhas discretas ("ghost"), clicaveis */
      .feito {{ display: flex; align-items: center; gap: .55rem;
                padding: .3rem .75rem; border-radius: 10px; cursor: pointer;
                color: #8a99a0; font-size: .85rem; transition: background .15s; }}
      .feito:hover {{ background: #fff; box-shadow: 0 1px 2px rgba(20,30,40,.05); }}
      .feito b {{ color: {TEXTO}; font-weight: 600; }}
      .feito .lapis {{ opacity: 0; transition: opacity .15s; margin-left: auto; }}
      .feito:hover .lapis {{ opacity: 1; }}
      /* transicao vertical entre etapas: o cartao novo desliza de baixo p/ cima */
      @keyframes aparecer {{ from {{ opacity:0; transform: translateY(56px);}} to {{opacity:1; transform:none;}} }}
      .aparecer {{ animation: aparecer .7s cubic-bezier(.22,.8,.35,1); }}
    </style>
    """)


def cabecalho() -> None:
    """Barra superior compacta (estilo Omni: minima, 1 acento)."""
    with ui.row().classes("w-full max-w-3xl mx-auto items-center gap-2.5 py-1 mb-1"):
        ui.label("🛣️").classes("text-lg bg-amber-50 rounded-lg px-2 py-0.5")
        ui.label("Dimensionamento de Pavimentos Rígidos") \
            .classes("text-base font-extrabold tracking-tight").style(f"color:{TEXTO}")
        ui.label("· PCA 1984 / DNIT IPR-714").classes("text-xs text-slate-400 hidden sm:block")


def stepper(etapa_atual: int, frac: float = 0.0) -> None:
    """Progresso minimalista: nome da etapa + 'X de 7' + barra fina continua.

    frac = fracao do fluxo ja percorrida (0..1), p/ a barra andar dentro da etapa.
    """
    total = len(ETAPAS)
    nome = dict(ETAPAS).get(etapa_atual, "")
    with ui.column().classes("w-full max-w-3xl mx-auto gap-1 mb-2"):
        with ui.row().classes("w-full justify-between items-baseline"):
            ui.label(nome).classes("text-sm font-bold").style(f"color:{TEXTO}")
            ui.label("Seu resultado está pronto abaixo" if etapa_atual == total
                     else f"Etapa {etapa_atual} de {total}") \
                .classes("text-xs text-slate-400")
        with ui.element("div").classes("w-full rounded-full overflow-hidden") \
                .style("height:4px;background:#E8ECEF"):
            ui.element("div").classes("h-full rounded-full") \
                .style(f"width:{max(4.0, 100 * frac):.1f}%;background:{AMBAR};"
                       "transition:width .3s ease")


def pergunta(texto: str, ajuda: str = "") -> None:
    ui.label(texto).classes("text-2xl font-extrabold tracking-tight").style(f"color:{TEXTO}")
    if ajuda:
        ui.label(ajuda).classes("text-sm text-slate-500 mb-1").style("line-height:1.5")


def cartao_feito(titulo: str, resumo: str, on_editar) -> None:
    """Linha discreta de etapa concluida — a linha INTEIRA e clicavel p/ editar."""
    with ui.element("div").classes("feito w-full max-w-3xl mx-auto") \
            .on("click", lambda _: on_editar()):
        ui.label("✓").style(f"color:{VERDE};font-weight:800;font-size:.8rem")
        ui.html(f"<b>{titulo}</b>" + (f"&ensp;<span>{resumo}</span>" if resumo else "")) \
            .classes("overflow-hidden text-ellipsis whitespace-nowrap")
        ui.icon("edit").classes("lapis text-slate-400 text-sm")


def resultado_destaque(h_cm: float, aprovada: bool) -> None:
    selo_cor = "green" if aprovada else "red"
    selo_txt = ("✓ APROVADA — fadiga e erosão ≤ 100%" if aprovada
                else "✗ REPROVADA — reveja os parâmetros")
    with ui.column().classes("w-full items-center rounded-2xl p-8 gap-1 shadow-lg") \
            .style(f"background:linear-gradient(115deg,{ASFALTO},{ASFALTO_2})"):
        ui.label("ESPESSURA DA PLACA DE CONCRETO").classes("text-xs tracking-widest text-slate-300")
        with ui.row().classes("items-baseline gap-1"):
            ui.label(f"{h_cm:.1f}".replace(".", ",")).classes("text-7xl font-extrabold").style(f"color:{AMBAR}")
            ui.label("cm").classes("text-2xl font-semibold text-slate-200")
        ui.badge(selo_txt, color=selo_cor).classes("mt-2 px-3 py-1")


def barra_consumo(rotulo: str, pct: float) -> None:
    cor = VERDE if pct < 70 else (AMBAR_ESC if pct <= 100 else VERMELHO)
    with ui.column().classes("w-full gap-1 my-1"):
        with ui.row().classes("w-full justify-between"):
            ui.label(rotulo).classes("text-sm font-semibold").style(f"color:{TEXTO}")
            ui.label(f"{pct:.1f}".replace(".", ",") + "%").classes("text-sm font-bold").style(f"color:{cor}")
        with ui.element("div").classes("w-full h-3 rounded-full bg-slate-100 overflow-hidden"):
            ui.element("div").classes("h-full rounded-full").style(
                f"width:{min(pct, 100):.1f}%;background:{cor}")


# rolagem vertical LENTA com easing (behavior:'smooth' nativo e rapido demais)
_JS_ROLAR = """
(() => {
  setTimeout(() => {
    const destino = %s;
    const inicio = window.scrollY;
    const dist = destino - inicio;
    if (Math.abs(dist) < 4) return;
    const dur = 900, t0 = performance.now();
    const ease = t => t < .5 ? 2*t*t : -1 + (4 - 2*t)*t;
    const passo = agora => {
      const p = Math.min(1, (agora - t0) / dur);
      window.scrollTo(0, inicio + dist * ease(p));
      if (p < 1) requestAnimationFrame(passo);
    };
    requestAnimationFrame(passo);
  }, 140);
})();
"""


def rolar_para_fim() -> None:
    ui.run_javascript(_JS_ROLAR % "document.body.scrollHeight")


def rolar_para_topo() -> None:
    ui.run_javascript(_JS_ROLAR % "0")


def mathjax_typeset() -> None:
    """Chamar apos renderizar formulas em ui.html(...) para o MathJax processar.

    Usa ui.timer p/ garantir que o cliente ja esta conectado (run_javascript
    direto durante o build da pagina pode ser descartado).
    """
    ui.timer(0.3, lambda: ui.run_javascript(
        "if (window.MathJax) { MathJax.typesetPromise(); }"), once=True)
