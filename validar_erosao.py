"""
validar_erosao.py - Validacao do modelo de erosao contra o exemplo do IPR-714

O Manual (secao 4.6.2.5, Quadro 11) traz um exemplo resolvido:
  h = 25 cm, k = 100 MPa/m, PSAC, junta sem barras, FSC = 1,2
  Fator de erosao para eixo simples (Q16): EF_ES = 2,72
A coluna 6 do Quadro 11 lista o N admissivel por erosao para cada carga
(ja majorada pelo FSC). Estes 9 pontos foram LIDOS A MAO do abaco (Fig.28),
portanto sao aproximados - servem para aferir a ordem de grandeza do modelo.

Rode (quando houver Python):  python validar_erosao.py
"""

from __future__ import annotations
import calculos as c

# Pontos do exemplo: (carga_tf_majorada, N_admissivel_lido_do_abaco)
# EF_ES = 2,72 ; pavimento SEM acostamento (Figura 28)
EF_ES = 2.72
PONTOS = [
    (8.4, float("inf")),   # ilimitado no exemplo
    (9.6, 21_200_000),
    (10.8, 8_500_000),
    (12.0, 4_000_000),
    (13.2, 2_500_000),
    (14.4, 1_430_000),
    (15.6, 825_000),
    (16.8, 555_000),
    (18.0, 365_000),
    (19.2, 265_000),
]


def main() -> None:
    print(f"Validacao da erosao - EF={EF_ES}, PSAC (Figura 28)")
    print(f"{'carga(tf)':>10} {'N manual':>14} {'N modelo':>14} {'erro %':>9}")
    print("-" * 50)
    erros = []
    for carga, n_manual in PONTOS:
        n_mod = c.repeticoes_admissiveis_erosao(
            EF_ES, carga, c.TipoAcostamento.SEM_CONCRETO)
        if n_manual == float("inf"):
            # "ilimitado" no manual = fora de escala do abaco (N muito alto)
            ok = "OK" if n_mod >= 5e7 else "DIVERGE"
            print(f"{carga:>10.1f} {'ilimitado':>14} {n_mod:>14.2e}  {ok}")
            continue
        erro = 100.0 * (n_mod - n_manual) / n_manual
        erros.append(abs(erro))
        print(f"{carga:>10.1f} {n_manual:>14,.0f} {n_mod:>14.2e} {erro:>8.1f}%")

    if erros:
        print("-" * 50)
        print(f"Erro absoluto medio: {sum(erros)/len(erros):.1f}%")
        print(f"Erro absoluto max  : {max(erros):.1f}%")
        print("\nNota: os N do manual sao leituras manuais do abaco; um erro")
        print("da ordem de 10-20% e esperado e aceitavel para esta calibracao.")


if __name__ == "__main__":
    main()
