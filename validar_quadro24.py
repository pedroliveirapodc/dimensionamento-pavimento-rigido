"""
validar_quadro24.py - Validacao end-to-end contra o Quadro 24 do IPR-714 (pag. 118)

Caso 2 de validacao (complementa validar_e2e.py, que testa so o Quadro 11/h=25/ES).
Quadro 24 e a folha-tipo PREENCHIDA e OFICIAL do exemplo do manual para h=26 cm,
com TODOS os tipos de eixo (ES + ETD + ETT) e o TOTAL de erosao (89,3%) batendo
com a soma das 3 parcelas -- e por isso um dataset de validacao muito mais rico
que o do Quadro 11 (que so aparece em prosa, para ES).

Mesmos parametros de projeto do Quadro 11: k=100 MPa/m, fctk=4,8 MPa, FSC=1,2,
PSAC (sem acostamento de concreto), junta sem barras de transferencia (JSP).

Objetivo: comparar, FAIXA A FAIXA (nao so o total), o %erosao calculado pela
ferramenta contra o valor impresso no Quadro 24, para isolar onde a equacao
de erosao reconstruida (_fit_erosao.py) diverge do abaco original do manual
(Figura 28) -- ver [[project-tcc]] sessao 23/08/2026 na memoria.

NOTA (achado da auditoria 23/08/2026): a propria linha de ETT do Quadro 24 no
manual tem um erro de copia-e-cola em (14) Tensao equivalente e (16) Fator de
fadiga -- os valores impressos (0,99 / 0,206) sao na verdade os do ETD em h=25,
nao os do ETT em h=26. Isso NAO afeta a comparacao abaixo pois so mexe na coluna
de FADIGA (que fica "ilimitado" nos dois casos) -- a coluna de EROSAO da ETT no
Quadro 24 usa o Fator de Erosao 2,89 (proximo do nosso 2,883), que esta correto.
"""
from __future__ import annotations
import calculos as c

# (carga_tf pre-FSC = limite SUPERIOR da faixa do manual, N previsto) por tipo de
# eixo -- extraido do Quadro 24, pag. 118. ETT usa a carga TOTAL do tandem (o
# codigo divide por 3 internamente em _carga_efetiva()).
ESPECTRO_ES = [
    (5.0, 3_270_843), (6.0, 203_804), (7.0, 290_488), (8.0, 238_118),
    (9.0, 242_715), (10.0, 310_404), (11.0, 282_267), (12.0, 242_438),
    (13.0, 206_645), (14.0, 65_889), (15.0, 39_296), (16.0, 5_565),
]
ESPECTRO_ETD = [
    (13.0, 182_532), (14.0, 5_565), (15.0, 12_243), (16.0, 12_243),
    (17.0, 17_808), (18.0, 30_051), (19.0, 23_373), (20.0, 17_808),
    (21.0, 17_808), (22.0, 12_243), (23.0, 5_565), (24.0, 5_565),
]
ESPECTRO_ETT = [
    (24.0, 30_051), (26.0, 17_808), (28.0, 12_243), (30.0, 18_921),
]

# %erosao impresso no Quadro 24 (coluna 7), na mesma ordem das listas acima.
# "-" no manual = 0,0 (repeticao prevista pequena demais p/ arredondar >0,0%).
ALVO_EROSAO_ES = [0.0, 0.0, 0.0, 0.9, 2.4, 6.1, 10.3, 14.3, 20.7, 10.5, 9.4, 1.9]
ALVO_EROSAO_ETD = [0.6, 0.0, 0.1, 0.2, 0.4, 1.1, 1.2, 1.1, 1.5, 1.4, 0.8, 1.1]
ALVO_EROSAO_ETT = [0.7, 0.6, 0.6, 1.4]

ALVO_TOTAL_EROSAO = 89.3  # Quadro 24, TOTAL da coluna 7
ALVO_TOTAL_FADIGA = 0.0   # todas as faixas dao "ilimitado" -> 0,0% em fadiga


def _monta_espectro() -> list[c.FaixaCarga]:
    esp = [c.FaixaCarga(c.TipoEixo.SIMPLES, carga, n) for carga, n in ESPECTRO_ES]
    esp += [c.FaixaCarga(c.TipoEixo.TANDEM_DUPLO, carga, n) for carga, n in ESPECTRO_ETD]
    esp += [c.FaixaCarga(c.TipoEixo.TANDEM_TRIPLO, carga, n) for carga, n in ESPECTRO_ETT]
    return esp


def _param(h_cm: float) -> c.ParametrosProjeto:
    return c.ParametrosProjeto(
        fctk_mpa=4.8, k_mpa_m=100.0, fsc=1.2,
        acostamento=c.TipoAcostamento.SEM_CONCRETO,
        com_barras_transferencia=False,
        espectro=_monta_espectro(),
    )


def _linha(carga_tf: float, d, alvo: float) -> tuple[str, float]:
    ce = d.consumo_erosao_pct
    diff = ce - alvo
    marca = "  <-- diverge" if abs(diff) > 1.0 else ""
    linha = (f"   {carga_tf:>9.1f} {d.faixa.repeticoes_previstas:>12,.0f}"
              f" {ce:>9.1f}% {alvo:>9.1f}% {diff:>+8.1f}pp{marca}")
    return linha, ce


def rodar() -> None:
    p = _param(26)
    r = c.verificar_espessura(26, p)

    grupos = [
        ("EIXOS SIMPLES (ES)", ESPECTRO_ES, ALVO_EROSAO_ES, c.TipoEixo.SIMPLES),
        ("TANDEM DUPLO (ETD)", ESPECTRO_ETD, ALVO_EROSAO_ETD, c.TipoEixo.TANDEM_DUPLO),
        ("TANDEM TRIPLO (ETT)", ESPECTRO_ETT, ALVO_EROSAO_ETT, c.TipoEixo.TANDEM_TRIPLO),
    ]

    print("=" * 72)
    print("VALIDACAO vs QUADRO 24 (pag. 118) - h=26cm, k=100 MPa/m, FSC=1,2, PSAC/JSP")
    print("=" * 72)

    soma_calc = 0.0
    soma_alvo = 0.0
    soma_abs_diff = 0.0
    n_faixas = 0
    for nome, espectro, alvos, tipo in grupos:
        print(f"\n {nome}")
        print(f"   {'carga(tf)':>9} {'N previsto':>12} {'%eros calc':>10}"
              f" {'%eros manual':>11} {'diff':>10}")
        detalhes = [d for d in r.detalhes if d.faixa.eixo == tipo]
        for (carga, _n), d, alvo in zip(espectro, detalhes, alvos):
            linha, ce = _linha(carga, d, alvo)
            print(linha)
            soma_calc += ce
            soma_alvo += alvo
            soma_abs_diff += abs(ce - alvo)
            n_faixas += 1

    print("\n" + "-" * 72)
    print(f" TOTAL erosao calculado = {soma_calc:5.1f}%   |   "
          f"TOTAL erosao manual (Quadro 24) = {ALVO_TOTAL_EROSAO:5.1f}%   |   "
          f"diff = {soma_calc - ALVO_TOTAL_EROSAO:+.1f}pp")
    print(f" TOTAL fadiga calculado = {r.soma_fadiga_pct:5.1f}%   |   "
          f"TOTAL fadiga manual = {ALVO_TOTAL_FADIGA:5.1f}%")
    print(f" Divergencia media absoluta por faixa: {soma_abs_diff / n_faixas:.2f} p.p."
          f"  (sobre {n_faixas} faixas)")
    print(f" Espessura aprovada pelo software: h={r.aprovada and 26 or 'REPROVA em 26'}"
          f"  (fadiga {r.soma_fadiga_pct:.1f}% / erosao {r.soma_erosao_pct:.1f}%)")


if __name__ == "__main__":
    rodar()
