"""
resultados.py - Exportacao do relatorio de dimensionamento em PDF.

Gera um PDF estruturado com: cabecalho, parametros do projeto, espectro
de trafego, resultado (espessura + consumos), resumo por faixa e
recomendacao de sub-base. O grafico h x consumo e embutido como imagem.

Uso:
    pdf_bytes = gerar_pdf(param, resultado, curva, contexto)
    st.download_button("Exportar PDF", pdf_bytes, "relatorio.pdf", "application/pdf")
"""
from __future__ import annotations

import io
import math
import datetime
from dataclasses import dataclass
from typing import Optional

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from fpdf import FPDF

import calculos as c
import lcca as lc

# Fonte com suporte Unicode (Windows). Se nao encontrar, cai para Helvetica (sem acentos).
_FONT_TTF = "C:/Windows/Fonts/arial.ttf"
_FONT_TTF_B = "C:/Windows/Fonts/arialbd.ttf"
_FONT_TTF_I = "C:/Windows/Fonts/ariali.ttf"
_USE_UNICODE = True


def _fontes_unicode() -> list[tuple[str, str, str]]:
    """Candidatas (regular, negrito, italico), na ordem de preferencia."""
    import os
    cands = [(_FONT_TTF, _FONT_TTF_B, _FONT_TTF_I)]
    ttf = os.path.join(matplotlib.get_data_path(), "fonts", "ttf")
    cands.append((os.path.join(ttf, "DejaVuSans.ttf"),
                  os.path.join(ttf, "DejaVuSans-Bold.ttf"),
                  os.path.join(ttf, "DejaVuSans-Oblique.ttf")))
    return [c for c in cands if all(os.path.exists(f) for f in c)]


# -----------------------------------------------------------------------
# Contexto extra (dados do session_state que nao estao em ParametrosProjeto)
# -----------------------------------------------------------------------
@dataclass
class ContextoRelatorio:
    local: Optional[str] = None
    tipo_solo: Optional[str] = None
    cbr_estimado: Optional[float] = None
    k0_subleito: Optional[float] = None
    tipo_subbase: Optional[str] = None
    esp_subbase_cm: Optional[float] = None
    vmda: Optional[int] = None
    periodo_anos: Optional[int] = None
    triagem_score: Optional[float] = None
    triagem_score_max: Optional[float] = None
    subbase_recomendada: Optional[str] = None
    subbase_justificativa: Optional[str] = None


# -----------------------------------------------------------------------
# Helpers internos
# -----------------------------------------------------------------------
def _v(x: float, dec: int = 2) -> str:
    return f"{x:.{dec}f}".replace(".", ",")


def _bignum(n: float) -> str:
    if n >= 1e19:
        return "ilimitado"
    if n >= 1e6:
        e = int(math.floor(math.log10(n)))
        m = n / 10 ** e
        return f"{m:.2f}x10^{e}".replace(".", ",")
    return f"{n:,.0f}".replace(",", ".")


def _tabela_lcca_anos(pdf: "RelatorioPDF", r: lc.ResultadoLCCA) -> None:
    """Tabela 'a conta inteira': ano a ano, nominal x fator = VP, acumulado."""
    pdf._sf("B", 9)
    pdf.cell(0, 5.5, "A conta, ano a ano (custo x fator de desconto = valor presente):", ln=True)
    larguras = (18, 9, 63, 22, 15, 23, 24)
    cab = ("Pav.", "Ano", "Evento", "Nominal", "Fator", "V. presente", "Acum. (VP)")
    pdf._sf("B", 7)
    pdf.set_fill_color(*_CINZA_ESCURO)
    pdf.set_text_color(255, 255, 255)
    pdf.set_x(18)
    for w, texto in zip(larguras, cab):
        pdf.cell(w, 5, texto, fill=True, align="C")
    pdf.ln(5)
    pdf.set_text_color(*_PRETO)
    pdf._sf("", 7)
    for i, ln_ in enumerate(lc.fluxo_detalhado(r)):
        if i % 2 == 0:
            pdf.set_fill_color(*_CINZA_CLARO)
        else:
            pdf.set_fill_color(255, 255, 255)
        pdf.set_x(18)
        celulas = (ln_["pavimento"], str(ln_["ano"]), ln_["evento"][:46],
                   f"R$ {_v(ln_['nominal'])}", f"{ln_['fator']:.3f}".replace(".", ","),
                   f"R$ {_v(ln_['vp'])}", f"R$ {_v(ln_['acumulado'])}")
        aligns = ("L", "C", "L", "R", "C", "R", "R")
        for w, texto, al in zip(larguras, celulas, aligns):
            pdf.cell(w, 4.4, texto, fill=True, align=al)
        pdf.ln(4.4)
    pdf._sf("I", 7)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 4.5, "O acumulado final de cada pavimento é o próprio VPL usado na comparação.",
             ln=True)
    pdf.set_text_color(*_PRETO)


def _grafico_lcca(r: lc.ResultadoLCCA) -> bytes:
    anos = list(range(r.horizonte + 1))
    acc_r = r.rigido.acumulado_vp(r.horizonte, r.taxa)
    acc_f = r.flexivel.acumulado_vp(r.horizonte, r.taxa)
    fig, ax = plt.subplots(figsize=(7, 3.0))
    ax.step(anos, acc_r, where="post", label="Rígido", color="#2E3A40", lw=1.8)
    ax.step(anos, acc_f, where="post", label="Flexível (ref.)", color="#E8A33D", lw=1.8)
    if r.ano_cruzamento:
        ax.axvline(r.ano_cruzamento, color="#c62828", ls=":", lw=1.2,
                   label=f"Cruzamento (ano {r.ano_cruzamento})")
    ax.set_xlabel("Ano")
    ax.set_ylabel("Custo acumulado (VP, R$/m²)")
    ax.legend(fontsize=8)
    ax.grid(alpha=0.3)
    fig.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=130)
    plt.close(fig)
    buf.seek(0)
    return buf.read()


def _grafico_curva(curva: list[c.ResultadoEspessura],
                   h_adotado: Optional[float]) -> bytes:
    hs = [r.h_cm for r in curva]
    fig, ax = plt.subplots(figsize=(7, 3.2))
    ax.plot(hs, [min(r.soma_fadiga_pct, 200) for r in curva],
            label="Fadiga (%)", marker=".", markersize=4, linewidth=1.5, color="#1565C0")
    ax.plot(hs, [min(r.soma_erosao_pct, 200) for r in curva],
            label="Erosão (%)", marker=".", markersize=4, linewidth=1.5, color="#E65100")
    ax.axhline(100, color="#c62828", ls="--", lw=1, label="Limite 100%")
    if h_adotado is not None:
        ax.axvline(h_adotado, color="#2e7d32", ls=":", lw=1.5,
                   label=f"h = {h_adotado:.0f} cm")
    ax.set_xlabel("Espessura h (cm)", fontsize=9)
    ax.set_ylabel("Consumo (%)", fontsize=9)
    ax.set_ylim(0, 210)
    ax.tick_params(labelsize=8)
    ax.legend(fontsize=8)
    ax.grid(alpha=0.3)
    fig.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=130)
    plt.close(fig)
    buf.seek(0)
    return buf.read()


# -----------------------------------------------------------------------
# Cores
# -----------------------------------------------------------------------
_CINZA_ESCURO = (46, 58, 64)
_AMBAR        = (232, 163, 61)
_CINZA_CLARO  = (245, 245, 245)
_PRETO        = (33, 33, 33)


# -----------------------------------------------------------------------
# Classe PDF
# -----------------------------------------------------------------------
class RelatorioPDF(FPDF):
    def __init__(self):
        super().__init__(orientation="P", unit="mm", format="A4")
        self.set_auto_page_break(auto=True, margin=18)
        self.set_margins(18, 18, 18)
        # Fonte Unicode (acentos, Σ, ≤): Arial no Windows; em Linux/macOS, a
        # DejaVu Sans que acompanha o matplotlib (dependencia ja instalada).
        # Helvetica (sem acentos) so como ultimo recurso.
        self._fn = "Helvetica"
        for regular, negrito, italico in _fontes_unicode():
            try:
                self.add_font("R", fname=regular)
                self.add_font("R", style="B", fname=negrito)
                self.add_font("R", style="I", fname=italico)
                self._fn = "R"
                break
            except Exception:
                continue
        self.add_page()

    def _sf(self, style: str = "", size: int = 9):
        self.set_font(self._fn, style, size)

    def header(self):
        self.set_fill_color(*_AMBAR)
        self.rect(0, 0, 210, 11, "F")
        self._sf("B", 9)
        self.set_text_color(255, 255, 255)
        self.set_xy(18, 2.5)
        self.cell(0, 6,
                  "Dimensionamento de Pavimento Rígido · Método PCA/1984 · DNIT IPR-714",
                  ln=False)
        self.set_text_color(*_PRETO)
        self.ln(12)

    def footer(self):
        self.set_y(-12)
        self._sf("I", 7)
        self.set_text_color(130, 130, 130)
        self.cell(0, 5,
                  f"Página {self.page_no()} · Gerado em "
                  f"{datetime.date.today().strftime('%d/%m/%Y')} | UFRJ-POLI TCC",
                  align="C")
        self.set_text_color(*_PRETO)

    def titulo_secao(self, texto: str):
        self.ln(3)
        self.set_fill_color(*_CINZA_ESCURO)
        self.set_text_color(255, 255, 255)
        self._sf("B", 9)
        self.cell(0, 7, f"  {texto}", ln=True, fill=True)
        self.set_text_color(*_PRETO)
        self.ln(1)

    def linha(self, rotulo: str, valor: str, destaque: bool = False):
        self._sf("B" if destaque else "", 9)
        self.set_x(18)
        self.cell(65, 5.5, rotulo, ln=False)
        self._sf("B" if destaque else "", 9)
        self.cell(0, 5.5, valor, ln=True)

    def linha_2col(self, r1: str, v1: str, r2: str, v2: str):
        self._sf("", 9)
        self.set_x(18)
        self.cell(42, 5.5, r1, ln=False)
        self._sf("B", 9)
        self.cell(30, 5.5, v1, ln=False)
        self._sf("", 9)
        self.cell(42, 5.5, r2, ln=False)
        self._sf("B", 9)
        self.cell(0, 5.5, v2, ln=True)


# -----------------------------------------------------------------------
# Funcao principal publica
# -----------------------------------------------------------------------
def gerar_pdf(
    param: c.ParametrosProjeto,
    resultado: Optional[c.ResultadoEspessura],
    curva: list[c.ResultadoEspessura],
    ctx: ContextoRelatorio,
    lcca_res: Optional[lc.ResultadoLCCA] = None,
) -> bytes:
    pdf = RelatorioPDF()

    # -- Titulo --
    pdf._sf("B", 14)
    pdf.set_text_color(*_CINZA_ESCURO)
    pdf.cell(0, 9, "Relatório de Dimensionamento de Pavimento Rígido",
             ln=True, align="C")
    pdf._sf("", 9)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 5,
             "Método PCA/1984 | Manual DNIT IPR-714 (seção 4.6.2) "
             "| Critério duplo: fadiga e erosão ≤ 100%",
             ln=True, align="C")
    pdf.set_text_color(*_PRETO)

    # -- 1. Identificacao --
    pdf.titulo_secao("1. Identificação")
    pdf.linha("Data de geração:", datetime.date.today().strftime("%d/%m/%Y"))
    if ctx.local:
        pdf.linha("Local da obra:", ctx.local)
    if ctx.triagem_score is not None and ctx.triagem_score_max:
        pct = 100 * ctx.triagem_score / ctx.triagem_score_max
        pdf.linha("Pontuação de viabilidade:",
                  f"{ctx.triagem_score:.0f}/{ctx.triagem_score_max:.0f} ({pct:.0f}%)")

    # -- 2. Parametros do Projeto --
    pdf.titulo_secao("2. Parâmetros do Projeto")
    pdf.linha_2col(
        "fctk (tração na flexão):", f"{_v(param.fctk_mpa, 1)} MPa",
        "FSC (segurança de cargas):", f"{_v(param.fsc)}")
    k_label = f"{param.k_mpa_m:.0f} MPa/m"
    if ctx.k0_subleito:
        k_label += f"  (no topo da sub-base; k0 do subleito = {ctx.k0_subleito:.0f})"
    pdf.linha("k (coef. de recalque):", k_label)
    pdf.linha_2col(
        "Acostamento de concreto:",
        "Sim" if param.acostamento == c.TipoAcostamento.COM_CONCRETO else "Não",
        "Barras de transferência:",
        "Sim" if param.com_barras_transferencia else "Não")
    if ctx.tipo_solo:
        pdf.linha("Solo do subleito:", ctx.tipo_solo)
    if ctx.cbr_estimado is not None and ctx.k0_subleito is not None:
        pdf.linha_2col(
            "CBR estimado:", f"{_v(ctx.cbr_estimado, 0)} %",
            "k0 do subleito:", f"{ctx.k0_subleito:.0f} MPa/m")
    if ctx.tipo_subbase:
        esp_str = f" | {ctx.esp_subbase_cm:.0f} cm" if ctx.esp_subbase_cm else ""
        pdf.linha("Sub-base adotada:", ctx.tipo_subbase + esp_str)

    # -- 3. Espectro de Trafego --
    pdf.titulo_secao("3. Espectro de Tráfego")
    if ctx.vmda is not None:
        periodo_str = f" | período de projeto de {ctx.periodo_anos} anos" if ctx.periodo_anos else ""
        pdf.linha("VMDa:", f"{ctx.vmda:,} veíc./dia".replace(",", ".") + periodo_str)
    total_rep = sum(f.repeticoes_previstas for f in param.espectro)
    pdf.linha("Total de repetições (eixos pesados):",
              f"{total_rep:,.0f}".replace(",", "."))
    pdf.ln(1)
    _tabela_espectro(pdf, param.espectro)

    # -- 4. Resultado --
    pdf.titulo_secao("4. Resultado")
    if resultado is None:
        pdf._sf("", 9)
        pdf.multi_cell(0, 5.5,
                       f"Nenhuma espessura entre {c.H_MIN_CM:.0f} e {c.H_MAX_CM:.0f} cm (intervalo das tabelas do IPR-714) atendeu aos critérios "
                       "(ΣCF e ΣCE ≤ 100%). Reveja os parâmetros.")
    else:
        pdf.set_fill_color(*_CINZA_CLARO)
        pdf._sf("B", 13)
        pdf.set_text_color(*_CINZA_ESCURO)
        pdf.cell(0, 9, f"  Espessura adotada:  h = {resultado.h_cm:.0f} cm",
                 ln=True, fill=True)
        pdf.set_text_color(*_PRETO)
        pdf._sf("", 9)
        pdf.ln(1)
        pdf.linha_2col(
            "Consumo de fadiga (ΣCF):", f"{_v(resultado.soma_fadiga_pct, 1)} %",
            "Consumo de erosão (ΣCE):", f"{_v(resultado.soma_erosao_pct, 1)} %")
        ok = resultado.soma_fadiga_pct <= 100 and resultado.soma_erosao_pct <= 100
        pdf._sf("I", 8)
        pdf.set_text_color(0, 100, 0)
        status = "aprovada" if ok else "reprovada"
        pdf.cell(0, 5,
                 f"  Ambos os critérios {'≤' if ok else '>'} 100%: espessura {status}",
                 ln=True)
        pdf.set_text_color(*_PRETO)

        # -- 5. Resumo por faixa --
        pdf.titulo_secao("5. Resumo por Faixa de Carga")
        _tabela_faixas(pdf, resultado)

        # -- 6. Grafico --
        pdf.titulo_secao("6. Gráfico Espessura × Consumo")
        try:
            img_bytes = _grafico_curva(curva, resultado.h_cm)
            pdf.image(io.BytesIO(img_bytes), x=18, w=170)
        except Exception:
            pdf._sf("I", 8)
            pdf.cell(0, 5, "(Gráfico indisponível)", ln=True)

    # -- 7. Recomendacao de Sub-base --
    if ctx.subbase_recomendada:
        pdf.titulo_secao("7. Sugestão de Sub-base")
        pdf._sf("B", 9)
        pdf.cell(0, 5.5, f"Sub-base sugerida pela ferramenta: {ctx.subbase_recomendada}", ln=True)
        if ctx.tipo_subbase:
            pdf._sf("", 9)
            pdf.cell(0, 5.5, f"Sub-base adotada no projeto: {ctx.tipo_subbase}", ln=True)
        if ctx.subbase_justificativa:
            pdf._sf("", 8)
            pdf.set_text_color(80, 80, 80)
            pdf.multi_cell(0, 4.5, ctx.subbase_justificativa + " A sugestão considera apenas o "
                           "nível de tráfego e a qualidade do subleito; a escolha final "
                           "é do projetista.")
            pdf.set_text_color(*_PRETO)

    # -- 8. Custo de ciclo de vida (opcional) --
    n_sec = 8
    if lcca_res is not None:
        pdf.titulo_secao("8. Custo de Ciclo de Vida (LCCA) - rigido vs. asfalto")
        r = lcca_res
        # numero-chave: custo anual equivalente (CAUE = VPL x FRC)
        pdf.set_fill_color(*_CINZA_CLARO)
        pdf._sf("B", 11)
        pdf.set_text_color(*_CINZA_ESCURO)
        pdf.cell(0, 8,
                 f"  Custo por ano:  rigido R$ {_v(r.caue_rigido)}/m2·ano   |   "
                 f"asfalto R$ {_v(r.caue_flexivel)}/m2·ano",
                 ln=True, fill=True)
        pdf.set_text_color(*_PRETO)
        pdf.ln(1)
        pdf.linha_2col(
            "CAPEX rigido:", f"R$ {_v(r.rigido.capex_m2)}/m2",
            "CAPEX asfalto:", f"R$ {_v(r.flexivel.capex_m2)}/m2")
        pdf.linha_2col(
            f"VPL rigido ({r.horizonte}a):", f"R$ {_v(r.vpl_rigido)}/m2",
            f"VPL asfalto ({r.horizonte}a):", f"R$ {_v(r.vpl_flexivel)}/m2")
        pdf.linha("Taxa de desconto:", f"{r.taxa:.1%}".replace(".", ","))
        conclusao = ("No horizonte analisado, o pavimento RIGIDO apresenta menor "
                     "custo de ciclo de vida."
                     if r.vantagem_rigido else
                     "No horizonte analisado, o pavimento FLEXIVEL de referencia "
                     "apresenta menor custo de ciclo de vida.")
        if r.ano_cruzamento:
            conclusao += f" Cruzamento do custo acumulado no ano {r.ano_cruzamento}."
        pdf._sf("I", 8)
        pdf.multi_cell(0, 4.5, conclusao)
        pdf._sf("", 9)
        try:
            pdf.image(io.BytesIO(_grafico_lcca(r)), x=18, w=170)
        except Exception:
            pdf._sf("I", 8)
            pdf.cell(0, 5, "(Gráfico indisponível)", ln=True)

        # decomposicao do CAPEX (fonte SICRO por componente)
        pdf.ln(1)
        pdf._sf("B", 9)
        pdf.cell(0, 5.5, "Decomposição do custo de construção (SICRO RJ jan/2026):", ln=True)
        pdf._sf("", 8)
        pdf.set_text_color(70, 70, 70)
        for alt in (r.rigido, r.flexivel):
            pdf._sf("B", 8)
            pdf.cell(0, 4.6, f"{alt.nome} - R$ {_v(alt.capex_m2)}/m2:", ln=True)
            pdf._sf("", 8)
            for nome_c, val_c, fonte_c in alt.componentes:
                pdf.set_x(22)
                pdf.cell(0, 4.4, f"- {nome_c}: R$ {_v(val_c)}/m2  ({fonte_c})", ln=True)
        pdf.set_text_color(*_PRETO)

        # tabela ano a ano (a conta inteira)
        pdf.ln(1)
        _tabela_lcca_anos(pdf, r)
        n_sec = 9

    # -- Notas metodologicas --
    pdf.titulo_secao(f"{n_sec}. Notas Metodológicas e Limitações")
    notas = [
        "Motor de cálculo verificado contra o exemplo resolvido do IPR-714 (Quadros 11 e 24): "
        "espessura adotada (26 cm) e critério governante (erosão) iguais aos do manual; "
        "número admissível de repetições por fadiga com diferença de até 3,5%.",
        "Erosão: leitura direta das Figuras 28 e 29 do IPR-714, digitalizadas. A Figura 28 "
        "(sem acostamento) tem erro médio de 8,0% nas 34 leituras publicadas no manual, que "
        "também serviram ao seu ajuste. A Figura 29 (com acostamento) não tem exemplo oficial "
        "e foi verificada apenas de forma indireta; a precisão nesse caso não foi quantificada.",
        "fctk fixado em 4,8 MPa. FSC por regra do autor a partir das repetições de eixos "
        "pesados (1,0 abaixo de 5×10^5; 1,1 até 5×10^6; 1,2 acima), associada às categorias "
        "qualitativas do Quadro 9 do IPR-714. Espessura verificada em centímetros inteiros, "
        "de 12 a 34 cm, intervalo coberto pelas tabelas do IPR-714 (sem extrapolação).",
        "Solo do subleito estimado pelo mapeamento pedológico da Embrapa (SiBCS, RJ). A "
        "conversão textura → AASHTO → CBR → k0 é regra do autor (hipótese de anteprojeto): "
        "confirmar com ensaio de CBR no local.",
        "VMDa: PNCT/DNIT, ano-base 2022 (modelado). Composição da frota por perfil-tipo e "
        "eixos conforme o IPR-723 (Figura 13).",
    ]
    if lcca_res is not None:
        notas.append(
            "Custo de ciclo de vida: pavimento flexível de REFERÊNCIA (não dimensionado; "
            "espessura de CBUQ pela tabela do IPR-719 + base granular de 20 cm). Custos "
            "unitários SICRO RJ jan/2026; cronogramas de manutenção típicos. VPL por m².")
    pdf._sf("", 8)
    pdf.set_text_color(70, 70, 70)
    for i, nota in enumerate(notas, 1):
        pdf.set_x(18)
        pdf.multi_cell(0, 4.5, f"{i}. {nota}")
    pdf.set_text_color(*_PRETO)

    return bytes(pdf.output())


# -----------------------------------------------------------------------
# Tabelas auxiliares
# -----------------------------------------------------------------------
_EIXO_LABEL = {
    c.TipoEixo.SIMPLES:       "Simples",
    c.TipoEixo.TANDEM_DUPLO:  "Tandem duplo",
    c.TipoEixo.TANDEM_TRIPLO: "Tandem triplo",
}


def _tabela_espectro(pdf: RelatorioPDF, espectro: list[c.FaixaCarga]):
    colunas = ["Tipo de eixo", "Carga (tf)", "Repetições"]
    larguras = [55, 35, 55]
    _cabecalho_tabela(pdf, colunas, larguras)
    pdf._sf("", 8)
    for i, f in enumerate(espectro):
        fill = (i % 2 == 0)
        pdf.set_fill_color(248, 248, 248)
        pdf.set_x(18)
        pdf.cell(larguras[0], 5.5, _EIXO_LABEL.get(f.eixo, f.eixo.value),
                 border="B", fill=fill)
        pdf.cell(larguras[1], 5.5, _v(f.carga_tf, 1),
                 border="B", fill=fill, align="R")
        pdf.cell(larguras[2], 5.5,
                 f"{f.repeticoes_previstas:,.0f}".replace(",", "."),
                 border="B", fill=fill, align="R", ln=True)
    pdf.ln(2)


def _tabela_faixas(pdf: RelatorioPDF, resultado: c.ResultadoEspessura):
    colunas = ["Eixo", "Carga (tf)", "N prev.", "SR", "CF (%)", "FE", "CE (%)"]
    larguras = [28, 22, 30, 18, 20, 18, 20]
    _cabecalho_tabela(pdf, colunas, larguras)
    pdf._sf("", 7)
    for i, d in enumerate(resultado.detalhes):
        fill = (i % 2 == 0)
        pdf.set_fill_color(248, 248, 248)
        pdf.set_x(18)
        vals = [
            _EIXO_LABEL.get(d.faixa.eixo, d.faixa.eixo.value),
            _v(d.faixa.carga_tf, 1),
            f"{d.faixa.repeticoes_previstas:,.0f}".replace(",", "."),
            _v(d.sr, 3),
            _v(d.consumo_fadiga_pct, 2),
            _v(d.fator_erosao, 3),
            _v(d.consumo_erosao_pct, 2),
        ]
        for j, (val, larg) in enumerate(zip(vals, larguras)):
            aln = "R" if j > 0 else "L"
            last = (j == len(larguras) - 1)
            pdf.cell(larg, 5.5, val, border="B", fill=fill, align=aln, ln=last)
    # soma
    pdf._sf("B", 8)
    pdf.set_x(18)
    pdf.set_fill_color(*_CINZA_CLARO)
    total_w = sum(larguras[:5])
    pdf.cell(total_w, 6, "Somatório:", border="T", fill=True, align="R")
    pdf.cell(larguras[5], 6, "", border="T", fill=True)
    pdf.cell(larguras[6], 6,
             f"Fad {_v(resultado.soma_fadiga_pct, 1)}% / Ero {_v(resultado.soma_erosao_pct, 1)}%",
             border="T", fill=True, align="R", ln=True)
    pdf.ln(2)


def _cabecalho_tabela(pdf: RelatorioPDF, colunas: list[str], larguras: list[int]):
    pdf.set_fill_color(*_CINZA_ESCURO)
    pdf.set_text_color(255, 255, 255)
    pdf._sf("B", 8)
    pdf.set_x(18)
    for j, (col, larg) in enumerate(zip(colunas, larguras)):
        last = (j == len(colunas) - 1)
        pdf.cell(larg, 6, col, fill=True, align="C", ln=last)
    pdf.set_text_color(*_PRETO)
