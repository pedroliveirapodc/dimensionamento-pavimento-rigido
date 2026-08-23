"""
_fit_erosao_v3.py - Recalibracao NAO-LINEAR (minimiza erro em log10(N) direto,
nao em ln(X)) do modelo de erosao Packard/PCA 1984.

_fit_erosao_v2.py tentou regressao linear em ln(X) e falhou (124% erro medio)
porque erros pequenos em X perto do "joelho" da curva (X-C perto de 0) sao
amplificados de forma extremamente nao-linear em N (expoente 0.103 tem
derivada que diverge quando X->C). Aqui minimizamos diretamente o residuo em
log10(N), que e a metrica que realmente importa (erro percentual em N), via
minimos quadrados nao-lineares (scipy.optimize.least_squares).

Mesmos 34 pontos de _fit_erosao_v2.py (9 ES-h25 + 9 ES-h26 + 12 ETD-h26 +
4 ETT-h26, todos do exemplo oficial do manual, Quadros 11/24, pag. 116-118).
"""
import math
import numpy as np
from scipy.optimize import least_squares

A, B, C, EXP = 14.524, 6.777, 9.0, 0.103

pts_es_h25 = [(9.6, 21.2e6), (10.8, 8.5e6), (12.0, 4.0e6), (13.2, 2.5e6),
              (14.4, 1.43e6), (15.6, 825e3), (16.8, 555e3), (18.0, 365e3),
              (19.2, 265e3)]
EF_ES_H25 = 2.72

pts_es_h26 = [(9.6, 26.0e6), (10.8, 10.0e6), (12.0, 5.1e6), (13.2, 2.75e6),
              (14.4, 1.7e6), (15.6, 1.0e6), (16.8, 630e3), (18.0, 420e3),
              (19.2, 290e3)]
EF_ES_H26 = 2.68

pts_etd_h26 = [(15.6, 30.0e6), (16.8, 16.0e6), (18.0, 9.3e6), (19.2, 6.1e6),
               (20.4, 4.0e6), (21.6, 2.8e6), (22.8, 2.0e6), (24.0, 1.6e6),
               (25.2, 1.2e6), (26.4, 880e3), (27.6, 680e3), (28.8, 520e3)]
EF_ETD_H26 = 2.86

pts_ett_h26 = [(9.6, 4.5e6), (10.4, 2.9e6), (11.2, 1.9e6), (12.0, 1.4e6)]
EF_ETT_H26 = 2.89

TODOS = ([(carga, n, EF_ES_H25, "ES-h25") for carga, n in pts_es_h25] +
         [(carga, n, EF_ES_H26, "ES-h26") for carga, n in pts_es_h26] +
         [(carga, n, EF_ETD_H26, "ETD-h26") for carga, n in pts_etd_h26] +
         [(carga, n, EF_ETT_H26, "ETT-h26") for carga, n in pts_ett_h26])

cargas = np.array([p[0] for p in TODOS])
ns = np.array([p[1] for p in TODOS])
efs = np.array([p[2] for p in TODOS])
us = np.log(cargas)
log10n_alvo = np.log10(ns)


def log10n_modelo(params, u, ef):
    k0, k1, k2, k3 = params
    lnx = k0 + k1 * ef + k2 * u + k3 * u * u
    x = np.exp(lnx)
    base = np.maximum(x - C, 1e-6)   # evita log de negativo durante a otimizacao
    return A - B * base ** EXP


def residuos(params):
    return log10n_modelo(params, us, efs) - log10n_alvo


# chute inicial = modelo antigo (k1 fixo em ln(10))
p0 = [-2.0913, math.log(10), -2.4000, 0.7108]
sol = least_squares(residuos, p0, method="lm", max_nfev=20000)
k0, k1, k2, k3 = sol.x

pred = 10 ** log10n_modelo(sol.x, us, efs)
erro_pct = 100 * np.abs(pred - ns) / ns

print("Convergiu:", sol.success, "| custo:", sol.cost)
print(f"ln(X) = {k0:.4f} + {k1:.4f}*EF + {k2:.4f}*u + {k3:.4f}*u^2")
print(f"(modelo antigo tinha: -2.0913 + {math.log(10):.4f}*EF + -2.4000*u + 0.7108*u^2)\n")
print(f"erro medio = {erro_pct.mean():.1f}%   erro max = {erro_pct.max():.1f}%   "
      f"mediana = {np.median(erro_pct):.1f}%\n")

print(f"{'grupo':<10} {'carga':>6} {'EF':>5} {'N_manual':>12} {'N_modelo':>12} {'erro%':>8}")
for (carga, n, ef, grupo), p, e in zip(TODOS, pred, erro_pct):
    print(f"{grupo:<10} {carga:>6.1f} {ef:>5.2f} {n:>12,.0f} {p:>12,.0f} {e:>+7.1f}%")

# erro por grupo
print("\nErro medio por grupo:")
for g in ("ES-h25", "ES-h26", "ETD-h26", "ETT-h26"):
    idx = [i for i, t in enumerate(TODOS) if t[3] == g]
    print(f"  {g:<10} erro medio = {erro_pct[idx].mean():.1f}%   max = {erro_pct[idx].max():.1f}%")

print(f"\nPARAMETROS FINAIS p/ colar em calculos.py:")
print(f"_ERO_A0 = {k0:.4f}")
print(f"_ERO_EF_COEF = {k1:.4f}")
print(f"_ERO_B1 = {k2:.4f}")
print(f"_ERO_C2 = {k3:.4f}")
