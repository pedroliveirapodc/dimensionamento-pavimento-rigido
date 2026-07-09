"""Calibracao do modelo de erosao contra os 9 pontos do exemplo (EF=2,72)."""
import math

A, B, C, EXP = 14.524, 6.777, 9.0, 0.103
EF = 2.72
pts = [(9.6, 21.2e6), (10.8, 8.5e6), (12.0, 4.0e6), (13.2, 2.5e6),
       (14.4, 1.43e6), (15.6, 825e3), (16.8, 555e3), (18.0, 365e3), (19.2, 265e3)]

# X requerido por ponto (inverte a eq. externa)
us, lxs = [], []
for carga, n in pts:
    X = C + ((A - math.log10(n)) / B) ** (1.0 / EXP)
    us.append(math.log(carga))
    lxs.append(math.log(X))

def lin_reg(xs, ys):
    n = len(xs); mx = sum(xs)/n; my = sum(ys)/n
    sxy = sum((x-mx)*(y-my) for x, y in zip(xs, ys))
    sxx = sum((x-mx)**2 for x in xs)
    b = sxy/sxx; a = my - b*mx
    return a, b

def quad_reg(xs, ys):
    # ajuste y = a + b x + c x^2 via normal equations 3x3
    n = len(xs)
    S = [sum(x**k for x in xs) for k in range(5)]
    T = [sum(y*x**k for x, y in zip(xs, ys)) for k in range(3)]
    # matriz [[n,S1,S2],[S1,S2,S3],[S2,S3,S4]] * [a,b,c] = [T0,T1,T2]
    M = [[n, S[1], S[2]], [S[1], S[2], S[3]], [S[2], S[3], S[4]]]
    v = [T[0], T[1], T[2]]
    # Gauss
    for i in range(3):
        p = M[i][i]
        for j in range(3): M[i][j] /= p
        v[i] /= p
        for r in range(3):
            if r != i:
                f = M[r][i]
                for j in range(3): M[r][j] -= f*M[i][j]
                v[r] -= f*v[i]
    return v  # a,b,c

def erro(modelo_X):
    erros = []
    for carga, n in pts:
        X = modelo_X(carga)
        base = X - C
        nm = 10**(A - B*base**EXP) if base > 0 else 1e20
        erros.append(abs(100*(nm-n)/n))
    return sum(erros)/len(erros), max(erros)

a, b = lin_reg(us, lxs)
K_pot = math.exp(a)/10**EF
print(f"POTENCIA (LS): M={b:.4f}  K={K_pot:.4e}")
print("  erro medio/max = %.1f%% / %.1f%%" % erro(
    lambda c: K_pot*10**EF*c**b))

qa, qb, qc = quad_reg(us, lxs)
print(f"QUADRATICA log: a={qa:.4f} b={qb:.4f} c={qc:.4f}")
print("  erro medio/max = %.1f%% / %.1f%%" % erro(
    lambda c: 10**EF*math.exp(qa + qb*math.log(c) + qc*math.log(c)**2)/10**EF
    if False else math.exp(qa + qb*math.log(c) + qc*math.log(c)**2)))
