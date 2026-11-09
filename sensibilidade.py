"""
Analise de sensibilidade do dimensionamento (grafico tornado).

Para cada parametro de projeto, re-roda calculos.dimensionar() com o parametro
variado em -X% e +X% (default 20%) mantendo os demais fixos, e registra a
variacao da espessura dimensionada (delta_h em cm) em relacao ao caso-base.

Parametros analisados:
- k efetivo (MPa/m)  — cap de 150 MPa/m do IPR-714 continua valendo;
- fctk (MPa);
- volume de trafego  — escala as REPETICOES de todas as faixas (as cargas por
  eixo nao mudam: os eixos sao rigorosos, IPR-723);
- FSC (fator de seguranca de cargas).
"""

from __future__ import annotations

import copy
from dataclasses import dataclass

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import calculos as c
from estagio3 import K_MAX_TOPO_SUBBASE


@dataclass
class LinhaTornado:
    """Efeito de um parametro sobre a espessura dimensionada."""
    parametro: str          # rotulo p/ o grafico
    valor_base: float
    h_menos: float          # h (cm) com parametro em -variacao
    h_mais: float           # h (cm) com parametro em +variacao
    estourou: bool = False  # algum caso nao convergiu ate H_MAX (h = sentinela)

    def amplitude(self, h_base: float) -> float:
        return max(abs(self.h_menos - h_base), abs(self.h_mais - h_base))


# sentinela quando nenhuma espessura <= H_MAX atende (caso "estourou")
_H_ESTOURO = c.H_MAX_CM + c.H_PASSO_CM


def _h_de(p: c.ParametrosProjeto) -> tuple[float, bool]:
    r = c.dimensionar(p)
    if r is None:
        return _H_ESTOURO, True
    return r.h_cm, False


def _com_k(p: c.ParametrosProjeto, fator: float) -> c.ParametrosProjeto:
    q = copy.deepcopy(p)
    q.k_mpa_m = max(min(p.k_mpa_m * fator, K_MAX_TOPO_SUBBASE), c.K_MIN_QUADROS)
    return q


def _com_fctk(p: c.ParametrosProjeto, fator: float) -> c.ParametrosProjeto:
    q = copy.deepcopy(p)
    q.fctk_mpa = p.fctk_mpa * fator
    return q


def _com_volume(p: c.ParametrosProjeto, fator: float) -> c.ParametrosProjeto:
    q = copy.deepcopy(p)
    for faixa in q.espectro:
        faixa.repeticoes_previstas = faixa.repeticoes_previstas * fator
    return q


def _com_fsc(p: c.ParametrosProjeto, fator: float) -> c.ParametrosProjeto:
    q = copy.deepcopy(p)
    q.fsc = p.fsc * fator
    return q


def tornado(p: c.ParametrosProjeto,
            variacao: float = 0.20) -> tuple[float, list[LinhaTornado]]:
    """
    Roda a analise de sensibilidade.

    Retorna (h_base_cm, linhas) com as linhas ORDENADAS por amplitude de efeito
    (maior primeiro — formato tornado). ~9 dimensionamentos no total.
    """
    h_base, base_estourou = _h_de(p)
    if base_estourou:
        raise ValueError("O caso-base nao converge (nenhum h <= "
                         f"{c.H_MAX_CM:.0f} cm atende) — sem base p/ sensibilidade.")

    casos = [
        (f"k efetivo ({p.k_mpa_m:.0f} MPa/m)", p.k_mpa_m, _com_k),
        (f"fctk ({p.fctk_mpa:.1f} MPa)", p.fctk_mpa, _com_fctk),
        ("Volume de tráfego", 1.0, _com_volume),
        (f"FSC ({p.fsc:.2f})", p.fsc, _com_fsc),
    ]

    linhas: list[LinhaTornado] = []
    for rotulo, valor_base, construir in casos:
        h_menos, e1 = _h_de(construir(p, 1.0 - variacao))
        h_mais, e2 = _h_de(construir(p, 1.0 + variacao))
        linhas.append(LinhaTornado(rotulo, valor_base, h_menos, h_mais,
                                   estourou=e1 or e2))

    linhas.sort(key=lambda ln: ln.amplitude(h_base), reverse=True)
    return h_base, linhas


def grafico_tornado(h_base: float, linhas: list[LinhaTornado],
                    variacao: float = 0.20):
    """Grafico de barras horizontais (tornado). Retorna a Figure matplotlib."""
    pct = int(round(variacao * 100))
    rotulos = [ln.parametro for ln in linhas][::-1]
    d_menos = [ln.h_menos - h_base for ln in linhas][::-1]
    d_mais = [ln.h_mais - h_base for ln in linhas][::-1]

    fig, ax = plt.subplots(figsize=(7, 0.7 * len(linhas) + 1.6))
    y = range(len(rotulos))
    ax.barh(y, d_menos, color="#1565C0", label=f"Parâmetro −{pct}%", height=0.55)
    ax.barh(y, d_mais, color="#E8A33D", label=f"Parâmetro +{pct}%", height=0.55)
    for yi, (dm, dp) in enumerate(zip(d_menos, d_mais)):
        for d in (dm, dp):
            if abs(d) > 1e-9:
                ax.annotate(f"{d:+.1f}".replace(".", ","),
                            (d, yi), ha="left" if d > 0 else "right",
                            va="center", fontsize=8,
                            xytext=(4 if d > 0 else -4, 0),
                            textcoords="offset points")
    ax.axvline(0, color="#2E3A40", lw=1.2)
    ax.set_yticks(list(y), rotulos)
    ax.set_xlabel(f"Variação da espessura dimensionada Δh (cm) — base: h = "
                  f"{h_base:.1f} cm".replace(".", ","))
    ax.grid(axis="x", alpha=0.3)
    ax.legend(fontsize=8)
    fig.tight_layout()
    return fig


if __name__ == "__main__":
    # smoke test: espectro de eixos simples do exemplo do manual (validar_e2e)
    from validar_e2e import ESPECTRO_ES
    p = c.ParametrosProjeto(
        fctk_mpa=4.8, k_mpa_m=100.0, fsc=1.2,
        acostamento=c.TipoAcostamento.SEM_CONCRETO,
        com_barras_transferencia=False,
        espectro=[c.FaixaCarga(c.TipoEixo.SIMPLES, carga, n)
                  for carga, n in ESPECTRO_ES])
    h_base, linhas = tornado(p)
    print(f"h base = {h_base:.1f} cm")
    for ln in linhas:
        print(f"  {ln.parametro:28s} -20%: {ln.h_menos:5.1f}  +20%: {ln.h_mais:5.1f}"
              f"  (amplitude {ln.amplitude(h_base):.1f} cm)"
              + ("  [ESTOUROU]" if ln.estourou else ""))
    # monotonia fisica esperada: k(+)→h<=base; fctk(+)→h<=base; volume(+)→h>=base; fsc(+)→h>=base
    def _get(nome):
        return next(l for l in linhas if l.parametro.startswith(nome))
    assert _get("k efetivo").h_mais <= h_base <= _get("k efetivo").h_menos
    assert _get("fctk").h_mais <= h_base <= _get("fctk").h_menos
    assert _get("Volume").h_menos <= h_base <= _get("Volume").h_mais
    assert _get("FSC").h_menos <= h_base <= _get("FSC").h_mais
    print("monotonia fisica OK")
