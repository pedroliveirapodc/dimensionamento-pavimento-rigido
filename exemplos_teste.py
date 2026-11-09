"""
exemplos_teste.py - Dois exemplos de dimensionamento para a apresentacao.

Rode:  python exemplos_teste.py

Exemplo A - reproduz o exemplo oficial do IPR-714 (pag. 115-118): valida o motor.
Exemplo B - via com acostamento de concreto + barras e trafego misto (ES/ETD/ETT):
            exercita outras tabelas (Quadros 14/15 e 22/23) e mostra a fadiga
            participando junto com a erosao.

Cada exemplo imprime: premissas, h adotada, somatorios e a conta por classe de eixo.
"""
from __future__ import annotations
import calculos as c

_EIXO = {c.TipoEixo.SIMPLES: "Eixo simples (ES)",
         c.TipoEixo.TANDEM_DUPLO: "Tandem duplo (ETD)",
         c.TipoEixo.TANDEM_TRIPLO: "Tandem triplo (ETT)"}


def _fmt(n: float) -> str:
    if n >= 1e19:
        return "ilimitado"
    return f"{n:,.0f}".replace(",", ".")


def rodar(titulo: str, p: c.ParametrosProjeto, esperado: str = "") -> None:
    print("=" * 72)
    print(titulo)
    print("=" * 72)
    ac = "com" if p.acostamento == c.TipoAcostamento.COM_CONCRETO else "sem"
    ba = "com" if p.com_barras_transferencia else "sem"
    print(f"Premissas: fctk = {p.fctk_mpa:.1f} MPa | k = {p.k_mpa_m:.0f} MPa/m | "
          f"FSC = {p.fsc:.1f} | {ac} acostamento | {ba} barras")
    print(f"Espectro: {len(p.espectro)} faixas de carga")

    res = c.dimensionar(p)
    if res is None:
        print(f">>> Nenhuma espessura de {c.H_MIN_CM:.0f} a {c.H_MAX_CM:.0f} cm atendeu (ver diagnostico no app).")
        return

    print(f"\n>>> ESPESSURA ADOTADA: h = {res.h_cm:.1f} cm")
    print(f"    Sigma fadiga = {res.soma_fadiga_pct:5.1f}%   |   "
          f"Sigma erosao = {res.soma_erosao_pct:5.1f}%")
    governa = "EROSAO" if res.soma_erosao_pct >= res.soma_fadiga_pct else "FADIGA"
    print(f"    Criterio que governa: {governa}")
    if esperado:
        print(f"    Esperado: {esperado}")

    print(f"\n    Conta por classe de eixo (em h = {res.h_cm:.1f} cm):")
    print(f"    {'classe':<20}{'carga':>7}{'P_ef':>7}{'sigma':>7}{'SR':>7}"
          f"{'N_fad':>13}{'%fad':>7}{'FE':>6}{'N_ero':>13}{'%ero':>7}")
    for d in res.detalhes:
        print(f"    {_EIXO[d.faixa.eixo]:<20}"
              f"{d.faixa.carga_tf:>6.1f} {d.carga_efetiva:>6.2f} "
              f"{d.sigma_eq:>6.3f} {d.sr:>6.3f} "
              f"{_fmt(d.n_adm_fadiga):>12} {d.consumo_fadiga_pct:>6.1f} "
              f"{d.fator_erosao:>5.2f} {_fmt(d.n_adm_erosao):>12} "
              f"{d.consumo_erosao_pct:>6.1f}")
    print()


# ---------------------------------------------------------------------------
# EXEMPLO A - reproduz o exemplo oficial do manual (IPR-714, pag. 115-118)
#   fctk=4,8 | k=100 | FSC=1,2 | sem acostamento | sem barras
#   Espectro de eixos simples do Quadro 10 (carga pre-FSC em tf).
#   Resultado esperado: h=26 cm, controlado por erosao (h=25 reprova).
# ---------------------------------------------------------------------------
ESPECTRO_MANUAL_ES = [
    (5.0, 3_270_843), (6.0, 203_804), (7.0, 290_488), (8.0, 238_118),
    (9.0, 242_715), (10.0, 310_404), (11.0, 282_267), (12.0, 242_438),
    (13.0, 206_645), (14.0, 65_889), (15.0, 39_296), (16.0, 5_565),
]
exemplo_a = c.ParametrosProjeto(
    fctk_mpa=4.8, k_mpa_m=100.0, fsc=1.2,
    acostamento=c.TipoAcostamento.SEM_CONCRETO,
    com_barras_transferencia=False,
    espectro=[c.FaixaCarga(c.TipoEixo.SIMPLES, carga, n)
              for carga, n in ESPECTRO_MANUAL_ES],
)

# ---------------------------------------------------------------------------
# EXEMPLO B - rodovia com acostamento de concreto + barras, trafego misto.
#   Subleito bom (k=60), concreto fctk=4,5, FSC=1,2.
#   Espectro com eixos simples, tandem duplos e tandem triplos (cargas legais).
#   Exercita os Quadros 14/15 (tensao, com acostamento) e 22/23 (erosao, com
#   barras + acostamento). Mostra fadiga e erosao atuando juntas.
# ---------------------------------------------------------------------------
exemplo_b = c.ParametrosProjeto(
    fctk_mpa=4.5, k_mpa_m=60.0, fsc=1.2,
    acostamento=c.TipoAcostamento.COM_CONCRETO,
    com_barras_transferencia=True,
    espectro=[
        c.FaixaCarga(c.TipoEixo.SIMPLES,        10.0, 1_500_000),
        c.FaixaCarga(c.TipoEixo.SIMPLES,        13.0,   400_000),
        c.FaixaCarga(c.TipoEixo.TANDEM_DUPLO,   17.0, 2_000_000),
        c.FaixaCarga(c.TipoEixo.TANDEM_DUPLO,   20.0,   600_000),
        c.FaixaCarga(c.TipoEixo.TANDEM_TRIPLO,  25.5,   900_000),
    ],
)


if __name__ == "__main__":
    rodar("EXEMPLO A - Exemplo oficial do manual IPR-714 (pag. 115-118)",
          exemplo_a,
          esperado=("subtotal so-ES: fadiga 8,6% (manual 8,9%) / erosao 89,8% "
                    "(manual 89,9%). No manual completo, ETD+ETT somam +15,5% de "
                    "erosao -> h=25 REPROVA e adota-se h=26 cm."))
    rodar("EXEMPLO B - Rodovia com acostamento + barras, trafego misto ES/ETD/ETT",
          exemplo_b)
