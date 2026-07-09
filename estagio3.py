"""
estagio3.py - Selecao do subleito e sub-base -> coeficiente de recalque k efetivo
Metodo PCA 1984 / DNIT IPR-714 (secao 4.4.4).

O k efetivo no topo da sub-base alimenta diretamente as equacoes de Westergaard
(tensao equivalente e fator de erosao). Fluxo:
  1) determina k0 do SUBLEITO natural (via CBR, tipo de solo, ou valor direto)
  2) majora k0 conforme a SUB-BASE escolhida (tipo + espessura)
  3) limita o k efetivo a 150 MPa/m (recomendacao do IPR-714)

FONTE DOS DADOS: os valores foram LIDOS diretamente dos abacos do IPR-714
(Figuras 11 e 18-21), renderizados em imagem com PyMuPDF (ver _gen_figuras /
_fig*.png). Precisao de leitura ~±5 MPa/m. Curvas:
  - Figura 11: CBR -> k0 do subleito
  - Figura 18: sub-base granular        -> aumento de k
  - Figura 19: brita tratada com cimento (BGTC)
  - Figura 20: solo-cimento
  - Figura 21: concreto rolado (CCR)
Os abacos vao ate k_subleito = 70 MPa/m (CBR ~20). Para sub-bases cimentadas o
k chega a 220-240 MPa/m, mas o IPR-714 limita o k de projeto a 150 MPa/m.
"""
from __future__ import annotations

K_MAX_TOPO_SUBBASE = 150.0  # MPa/m (limite recomendado pelo IPR-714, secao 4.4.4)


# ---------------------------------------------------------------
# Quadro 3 - tipo de solo do subleito -> faixa de k (MPa/m). Exato (texto IPR-714).
# Usar o ponto medio da faixa como estimativa.
# ---------------------------------------------------------------
QUADRO_3_SOLO_K = {
    "A1-a":        (110, 165),   # >110 (limite sup. estimado)
    "A1-b":        (70, 165),
    "A2-4 / A2-5": (80, 110),    # >80
    "A2-6 / A2-7": (50, 90),
    "A3":          (55, 90),
    "A4":          (25, 80),
    "A5":          (20, 50),     # <50
    "A6":          (20, 60),     # <60
    "A7-5 / A7-6": (20, 60),     # <60
}


def k_de_solo(tipo: str) -> float:
    """k0 estimado (ponto medio da faixa do Quadro 3), em MPa/m."""
    lo, hi = QUADRO_3_SOLO_K[tipo]
    return (lo + hi) / 2.0


# ---------------------------------------------------------------
# CBR do subleito -> k0 (Figura 11). Pontos lidos da curva do abaco.
# Abaco vai ate CBR 21 / k 70; CBR>20 e extrapolacao (marcada).
# ---------------------------------------------------------------
_CBR_PTS = [2, 3, 4, 5, 6, 7, 8, 10, 12, 15, 20, 30, 50, 100]
_K_PTS = [20, 28, 34, 39, 43, 47, 50, 55, 58, 63, 69, 76, 86, 100]
#         <----------------- lido da Figura 11 ----------------><-- extrap. -->



def _interp(xs: list[float], ys: list[float], x: float) -> float:
    if x <= xs[0]:
        return ys[0]
    if x >= xs[-1]:
        return ys[-1]
    for i in range(len(xs) - 1):
        if xs[i] <= x <= xs[i + 1]:
            t = (x - xs[i]) / (xs[i + 1] - xs[i])
            return ys[i] + (ys[i + 1] - ys[i]) * t
    return ys[-1]


def k_de_cbr(cbr: float) -> float:
    """k0 do subleito (MPa/m) a partir do CBR (%) — aprox. da Figura 11."""
    return _interp(_CBR_PTS, _K_PTS, cbr)


# ---------------------------------------------------------------
# Sub-base -> aumento de k (Figuras 18-21). Tabelas de k efetivo (MPa/m) em
# funcao de k0 do subleito e da espessura da sub-base. Aproximacoes das curvas.
# Estrutura: {tipo: {"esp_cm": [...], "k0": [...], "kef": [[...]]}}  (kef[i_esp][j_k0])
# ---------------------------------------------------------------
# Eixo de k0 do subleito comum aos abacos (vao de 20 a 70 MPa/m).
_K0 = [20, 40, 60, 70]

# GRANULAR (Figura 18): kef lido do abaco p/ espessuras 10/15/20/30 cm.
_SB_GRANULAR = {
    "esp_cm": [10, 15, 20, 30],
    "k0": _K0,
    "kef": [
        [22, 48, 66, 73],    # 10 cm
        [28, 54, 71, 77],    # 15 cm
        [32, 58, 78, 85],    # 20 cm
        [43, 70, 92, 100],   # 30 cm
    ],
}
# BRITA TRATADA COM CIMENTO / BGTC (Figura 19): espessuras 10/12.5/15/20 cm.
_SB_BGTC = {
    "esp_cm": [10, 12.5, 15, 20],
    "k0": _K0,
    "kef": [
        [62, 100, 130, 140],
        [68, 118, 160, 175],
        [75, 130, 178, 195],
        [85, 160, 220, 220],
    ],
}
# SOLO-CIMENTO (Figura 20): espessuras 10/12.5/15/17.5/20 cm.
_SB_SOLO_CIMENTO = {
    "esp_cm": [10, 12.5, 15, 17.5, 20],
    "k0": _K0,
    "kef": [
        [80, 110, 135, 145],
        [90, 140, 190, 210],
        [100, 170, 225, 240],
        [115, 195, 240, 240],
        [130, 215, 240, 240],
    ],
}
# CONCRETO ROLADO / CCR (Figura 21): espessuras 10/12.5/15 cm.
_SB_CCR = {
    "esp_cm": [10, 12.5, 15],
    "k0": _K0,
    "kef": [
        [75, 120, 155, 165],
        [82, 150, 190, 190],
        [90, 175, 230, 240],
    ],
}

TIPOS_SUBBASE = {
    "Sem sub-base": None,
    "Granular (BGS/macadame)": _SB_GRANULAR,
    "Brita tratada com cimento (BGTC)": _SB_BGTC,
    "Solo-cimento": _SB_SOLO_CIMENTO,
    "Concreto rolado (CCR)": _SB_CCR,
}


def _interp_bilinear(tab: dict, k0: float, esp_cm: float) -> float:
    esps, k0s, kef = tab["esp_cm"], tab["k0"], tab["kef"]
    # interpola em k0 dentro de cada espessura, depois em espessura
    por_esp = [_interp(k0s, linha, k0) for linha in kef]
    return _interp(esps, por_esp, esp_cm)


def k_efetivo(k0: float, tipo_subbase: str, espessura_cm: float = 0.0) -> float:
    """
    Coeficiente de recalque efetivo no topo da sub-base (MPa/m).
    Limitado a 150 MPa/m (IPR-714). Se 'Sem sub-base', retorna k0 (limitado).
    """
    tab = TIPOS_SUBBASE[tipo_subbase]
    if tab is None:
        return min(k0, K_MAX_TOPO_SUBBASE)
    kef = _interp_bilinear(tab, k0, espessura_cm)
    return min(kef, K_MAX_TOPO_SUBBASE)


if __name__ == "__main__":
    print("CBR 5% -> k0 =", k_de_cbr(5), "MPa/m")
    print("Solo A4 -> k0 =", k_de_solo("A4"), "MPa/m")
    print("k0=40, granular 20cm -> kef =", k_efetivo(40, "Granular (BGS/macadame)", 20))
    print("k0=40, solo-cimento 15cm -> kef =", k_efetivo(40, "Solo-cimento", 15))
    print("k0=20, sem sub-base -> kef =", k_efetivo(20, "Sem sub-base"))
