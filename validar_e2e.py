"""
validar_e2e.py - Validacao end-to-end contra o exemplo do IPR-714 (Quadro 11)

Caso: h=25 cm, k=100 MPa/m, fctk=4,8 MPa, FSC=1,2, PSAC, junta sem barras.
Espectro de EIXOS SIMPLES do exemplo (carga pre-FSC em tf; o codigo aplica o FSC).

Alvos do manual (subtotais dos eixos simples no Quadro 11):
  - Consumo de FADIGA total  = 8,9%   (ETD e ETT dao fadiga ilimitada -> 0%)
  - Consumo de EROSAO  total = 89,9%  (eixos simples; ETD+ETT somam +15,5%)
O manual conclui: somando tudo, erosao = 105,4% > 100% -> h=25 REPROVA.
"""
from __future__ import annotations
import calculos as c

# (carga_tf pre-FSC, repeticoes previstas) - eixos simples do Quadro 10/11
ESPECTRO_ES = [
    (5.0, 3_270_843), (6.0, 203_804), (7.0, 290_488), (8.0, 238_118),
    (9.0, 242_715), (10.0, 310_404), (11.0, 282_267), (12.0, 242_438),
    (13.0, 206_645), (14.0, 65_889), (15.0, 39_296), (16.0, 5_565),
]

espectro = [c.FaixaCarga(c.TipoEixo.SIMPLES, carga, n) for carga, n in ESPECTRO_ES]

p = c.ParametrosProjeto(
    fctk_mpa=4.8, k_mpa_m=100.0, fsc=1.2,
    acostamento=c.TipoAcostamento.SEM_CONCRETO,
    com_barras_transferencia=False,
    espectro=espectro,
)


def detalhar(h_cm: float) -> None:
    r = c.verificar_espessura(h_cm, p)
    print(f"\n h = {h_cm:.0f} cm  (eixos simples do exemplo)")
    print(f"   {'carga(tf)':>9} {'cargaxFSC':>9} {'N prev':>11}"
          f" {'%fadiga':>8} {'%erosao':>8}")
    for d in r.detalhes:
        cf = d.consumo_fadiga_pct
        ce = d.consumo_erosao_pct
        print(f"   {d.faixa.carga_tf:>9.0f} {d.faixa.carga_tf*p.fsc:>9.1f}"
              f" {d.faixa.repeticoes_previstas:>11,.0f}"
              f" {cf:>7.1f}% {ce:>7.1f}%")
    print(f"   {'SOMA':>43} {r.soma_fadiga_pct:>6.1f}% {r.soma_erosao_pct:>6.1f}%")
    print(f"   Alvo manual (so eixos simples): fadiga 8,9% | erosao 89,9%")


if __name__ == "__main__":
    print("=" * 60)
    print("VALIDACAO END-TO-END - exemplo IPR-714 (Quadro 11)")
    print("=" * 60)
    detalhar(25)
