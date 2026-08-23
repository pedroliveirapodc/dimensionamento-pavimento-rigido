"""
calculos.py - Motor de dimensionamento de pavimentos rigidos de concreto simples
Metodo: PCA 1984 (criterio duplo de fadiga e erosao)
Referencia: Manual de Pavimentos Rigidos do DNIT (IPR-714, 2005), secao 4.6.2

Funcoes puras, sem dependencia de Streamlit. Permite testar o modulo isoladamente.

Filosofia do metodo PCA 1984
----------------------------
Adota-se uma espessura-tentativa h e verifica-se se ela suporta o espectro de
trafego SEM atingir a ruina por:
  (a) FADIGA   -> trincamento por flexao repetida da placa
  (b) EROSAO   -> bombeamento / perda de suporte da fundacao
Para cada tipo de eixo e cada faixa de carga, calcula-se o consumo (%) em cada
criterio. A espessura e aprovada se AMBAS as somas (Sigma fadiga e Sigma erosao)
ficarem <= 100%.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import math


# =====================================================================
# 1. CONSTANTES E CONFIGURACAO (centralizadas para facilitar ajustes)
# =====================================================================

# Faixa de espessuras testadas na iteracao (cm)
H_MIN_CM = 10.0
H_MAX_CM = 40.0
H_PASSO_CM = 0.5

# Limite de consumo para aprovacao (%)
CONSUMO_MAXIMO = 100.0

# "Infinito" pratico para repeticoes admissiveis ilimitadas (fadiga, SR baixo)
N_ILIMITADO = 1e20

# Fatores de Seguranca de Carga (FSC) sugeridos pela PCA conforme a via.
# O usuario pode sobrescrever; estes sao apenas defaults editaveis.
FSC_PADRAO = {
    "via_alto_volume_interestadual": 1.20,
    "via_arterial_alto_volume": 1.10,
    "via_secundaria_baixo_volume": 1.00,
}


class TipoEixo(Enum):
    """Tipos de eixo considerados no espectro de trafego."""
    SIMPLES = "simples"
    TANDEM_DUPLO = "tandem_duplo"
    TANDEM_TRIPLO = "tandem_triplo"


class TipoAcostamento(Enum):
    SEM_CONCRETO = "sem_concreto"
    COM_CONCRETO = "com_concreto"


# Cargas do eixo-PADRAO da PCA (tf), usadas para escalar a tensao na fadiga.
# A tensao equivalente tabelada (Quadros 12-15) corresponde a estes eixos;
# para outras cargas, a tensao escala com (carga/padrao)^0.94 (so na fadiga).
# Tandem triplo usa o abaco de eixo simples com 1/3 da carga -> padrao = ES.
CARGA_PADRAO_TF = {
    TipoEixo.SIMPLES: 8.16,        # 80 kN
    TipoEixo.TANDEM_DUPLO: 16.31,  # 160 kN
    TipoEixo.TANDEM_TRIPLO: 8.16,  # usa abaco de eixo simples (carga ja /3)
}
# Expoente das cargas no modelo de fadiga (IPR-714, secao 4.6.2.3.3).
EXP_CARGA_FADIGA = 0.94


# =====================================================================
# 2. PROPRIEDADES DO CONCRETO
# =====================================================================

def mr_de_fck(fck_mpa: float) -> float:
    """
    Correlacao OPCIONAL fck -> resistencia a tracao na flexao (fctk), em MPa.

    IMPORTANTE: O metodo PCA 1984 (IPR-714) trabalha DIRETAMENTE com a
    resistencia caracteristica a tracao na flexao aos 28 dias (fctk). O
    exemplo do manual usa fctk = 4,8 MPa como dado de entrada. Esta funcao
    so deve ser usada como fallback quando o projeto fornecer apenas fck.
    """
    # Correlacao aproximada (NBR 6118, tracao na flexao). Confirmar no projeto.
    return 0.7 * math.sqrt(fck_mpa)


# =====================================================================
# 3. TENSAO EQUIVALENTE E FATOR DE EROSAO (dados do manual, paginas 87-119)
# =====================================================================
#
# No metodo PCA 1984 estes dois valores sao lidos de QUADROS em funcao de:
#   - espessura da placa h (cm)
#   - coeficiente de recalque k (MPa/m)
#   - tipo de eixo
#   - presenca de acostamento de concreto (tensao equiv. e erosao)
#   - presenca de barras de transferencia (apenas erosao)
#
# Os dados ficam em tabelas_pca.py (Quadros 12-23 do IPR-714). Aqui apenas
# mapeamos a combinacao (eixo, acostamento, barras) para a tabela certa.
import tabelas_pca as tab


# Mapa: (acostamento, eixo) -> (tabela, eixo_k, indice_coluna)
#   indice_coluna: 0=ES, 1=ETD (tabelas de pares); None=ETT (valor unico)
_TENSAO = {
    # PSAC (sem acostamento): Quadros 12 (ES/ETD) e 13 (ETT)
    (TipoAcostamento.SEM_CONCRETO, TipoEixo.SIMPLES):      (tab.Q12_ES_ETD_PSAC, tab.K_ES_ETD, 0),
    (TipoAcostamento.SEM_CONCRETO, TipoEixo.TANDEM_DUPLO): (tab.Q12_ES_ETD_PSAC, tab.K_ES_ETD, 1),
    (TipoAcostamento.SEM_CONCRETO, TipoEixo.TANDEM_TRIPLO):(tab.Q13_ETT_PSAC,    tab.K_ETT,    None),
    # PCAC (com acostamento): Quadros 14 (ES/ETD) e 15 (ETT)
    (TipoAcostamento.COM_CONCRETO, TipoEixo.SIMPLES):      (tab.Q14_ES_ETD_PCAC, tab.K_ES_ETD, 0),
    (TipoAcostamento.COM_CONCRETO, TipoEixo.TANDEM_DUPLO): (tab.Q14_ES_ETD_PCAC, tab.K_ES_ETD, 1),
    (TipoAcostamento.COM_CONCRETO, TipoEixo.TANDEM_TRIPLO):(tab.Q15_ETT_PCAC,    tab.K_ETT,    None),
}

# Mapa de erosao: (acostamento, com_barras, eixo) -> (tabela, eixo_k, indice_coluna)
# Quadros 16-23 (todos transcritos). com_barras: False=JSP, True=JCP.
_EROSAO = {
    # JSP (sem barras) + PSAC (sem acostamento): Q16 (ES/ETD), Q17 (ETT)
    (TipoAcostamento.SEM_CONCRETO, False, TipoEixo.SIMPLES):       (tab.Q16_ES_ETD_JSP_PSAC, tab.K_ERO_ES_ETD,     0),
    (TipoAcostamento.SEM_CONCRETO, False, TipoEixo.TANDEM_DUPLO):  (tab.Q16_ES_ETD_JSP_PSAC, tab.K_ERO_ES_ETD,     1),
    (TipoAcostamento.SEM_CONCRETO, False, TipoEixo.TANDEM_TRIPLO): (tab.Q17_ETT_JSP_PSAC,    tab.K_ETT,            None),
    # JSP (sem barras) + PCAC (com acostamento): Q18 (ES/ETD), Q19 (ETT)
    (TipoAcostamento.COM_CONCRETO, False, TipoEixo.SIMPLES):       (tab.Q18_ES_ETD_JSP_PCAC, tab.K_ERO_ES_ETD,     0),
    (TipoAcostamento.COM_CONCRETO, False, TipoEixo.TANDEM_DUPLO):  (tab.Q18_ES_ETD_JSP_PCAC, tab.K_ERO_ES_ETD,     1),
    (TipoAcostamento.COM_CONCRETO, False, TipoEixo.TANDEM_TRIPLO): (tab.Q19_ETT_JSP_PCAC,    tab.K_ETT,            None),
    # JCP (com barras) + PSAC (sem acostamento): Q20 (ES/ETD), Q21 (ETT)
    (TipoAcostamento.SEM_CONCRETO, True, TipoEixo.SIMPLES):        (tab.Q20_ES_ETD_JCP_PSAC, tab.K_ERO_ES_ETD,     0),
    (TipoAcostamento.SEM_CONCRETO, True, TipoEixo.TANDEM_DUPLO):   (tab.Q20_ES_ETD_JCP_PSAC, tab.K_ERO_ES_ETD,     1),
    (TipoAcostamento.SEM_CONCRETO, True, TipoEixo.TANDEM_TRIPLO):  (tab.Q21_ETT_JCP_PSAC,    tab.K_ETT,            None),
    # JCP (com barras) + PCAC (com acostamento): Q22 (ES/ETD, k ate 180!), Q23 (ETT)
    (TipoAcostamento.COM_CONCRETO, True, TipoEixo.SIMPLES):        (tab.Q22_ES_ETD_JCP_PCAC, tab.K_ERO_ES_ETD_180, 0),
    (TipoAcostamento.COM_CONCRETO, True, TipoEixo.TANDEM_DUPLO):   (tab.Q22_ES_ETD_JCP_PCAC, tab.K_ERO_ES_ETD_180, 1),
    (TipoAcostamento.COM_CONCRETO, True, TipoEixo.TANDEM_TRIPLO):  (tab.Q23_ETT_JCP_PCAC,    tab.K_ETT,            None),
}


def tensao_equivalente(h_cm: float, k_mpa_m: float, eixo: TipoEixo,
                       acostamento: TipoAcostamento) -> float:
    """Tensao equivalente (MPa), interpolada dos Quadros 12-15 da PCA."""
    chave = (acostamento, eixo)
    if chave not in _TENSAO:
        raise NotImplementedError(
            f"Tabela de tensao equivalente nao disponivel para {chave} "
            f"(Quadro 14 PCAC ES/ETD ainda nao transcrito)."
        )
    tabela, eixo_k, col = _TENSAO[chave]
    return tab.consultar(tabela, eixo_k, h_cm, k_mpa_m, indice_coluna=col)


def fator_erosao(h_cm: float, k_mpa_m: float, eixo: TipoEixo,
                 acostamento: TipoAcostamento, com_barras: bool) -> float:
    """Fator de erosao, interpolado dos Quadros 16-23 da PCA."""
    chave = (acostamento, com_barras, eixo)
    if chave not in _EROSAO:
        raise NotImplementedError(
            f"Tabela de fator de erosao nao disponivel para {chave} "
            f"(Quadros 16,18-23 ainda nao transcritos)."
        )
    tabela, eixo_k, col = _EROSAO[chave]
    return tab.consultar(tabela, eixo_k, h_cm, k_mpa_m, indice_coluna=col)


# =====================================================================
# 4. REPETICOES ADMISSIVEIS (abacos PCA -> equacoes)
# =====================================================================

def repeticoes_admissiveis_fadiga(tensao_eq: float, mr: float,
                                  carga_tf: float, carga_padrao_tf: float) -> float:
    """
    Numero admissivel de repeticoes pelo criterio de FADIGA.

    A tensao equivalente tabelada vale para o eixo-padrao; a tensao real
    escala com a carga elevada ao expoente 0,94 (IPR-714):
        SR = (tensao_eq / MR) * (carga / carga_padrao)^0.94

    Equacoes da PCA 1984 (reproduzem o abaco de fadiga, Figura 27):
      SR < 0.45            -> repeticoes ilimitadas
      0.45 <= SR < 0.55    -> N = (4.2577 / (SR - 0.4325))^3.268
      SR >= 0.55           -> log10(N) = 11.737 - 12.077 * SR
    """
    sr = (tensao_eq / mr) * (carga_tf / carga_padrao_tf) ** EXP_CARGA_FADIGA
    if sr < 0.45:
        return N_ILIMITADO
    if sr < 0.55:
        return (4.2577 / (sr - 0.4325)) ** 3.268
    return 10.0 ** (11.737 - 12.077 * sr)


# --- Leitura da Figura 28 (sem acostamento) / Figura 29 (com acostamento) ---
# DIGITALIZACAO DIRETA DO ABACO (23/08/2026 — substitui a regressao empirica
# anterior). As Figuras 28/29 do IPR-714 sao NOMOGRAMAS de 3 escalas paralelas
# (carga por eixo | fator de erosao | numero admissivel de repeticoes): a
# leitura correta e tracar uma reta do ponto da carga ao ponto do fator de
# erosao e ler N onde essa reta cruza a 3a escala.
#
# As duas figuras foram extraidas da imagem raster embutida no PDF (mesma
# tecnica de PyMuPDF ja usada p/ Figs.11/18-21, mas aqui com deteccao
# pixel-a-pixel das posicoes dos tracos de escala em vez de leitura visual —
# ver _fit_erosao_v3.py e a sessao de 23/08/2026 na memoria do projeto p/ o
# processo completo). Cada escala foi calibrada contra os proprios numeros
# impressos: carga (log), fator de erosao (linear), N admissivel (log, com um
# termo quadratico extra p/ a Fig.29 cuja escala de N nao e perfeitamente
# log-linear). A extrapolacao geometrica (formula de retas por 3 pontos
# colineares em linhas paralelas, p3 = p1 + (p2-p1)*w) foi ainda corrigida por
# um pequeno ajuste (w, offset) contra os 34 pontos OFICIAIS do Quadro 11/24
# do manual — os UNICOS dados reais disponiveis, e todos da Figura 28.
#
# RESULTADO: Figura 28 (sem acostamento) — erro medio 8,0% / max 20,9% sobre
# os 34 pontos oficiais. VALIDADA e generaliza suavemente por TODO o fator de
# erosao impresso (2,0 a 4,0), sem precisar de clamp/saturacao — corrige o
# problema dos Casos 2/4 do EXEMPLO_4_CASOS (que davam resultado identico por
# saturarem no mesmo piso calibrado).
# Figura 29 (com acostamento) — MESMO metodo de digitalizacao pixel-a-pixel,
# mas SEM ajuste empirico (w geometrico puro), pois o UNICO exemplo oficial do
# manual e sem acostamento — nao ha dado real p/ validar a Fig.29 numericamente.
# ⚠️ LIMITACAO EM ABERTO: a Fig.29 fica sem validacao ponto-a-ponto; usar os
# resultados de casos COM acostamento com essa ressalva ate aparecer um 2o
# exemplo oficial (ou conferencia manual direta) p/ confirmar a precisao.
# Substitui o antigo C1_COM_ACOSTAMENTO=0,90 (que era so um multiplicador
# provisorio sobre a Fig.28 — a Fig.29 e um abaco proprio, nao uma Fig.28
# escalada; ver a diferenca de faixa do eixo de EF: 2,0-4,0 na Fig.28 x
# 1,6-3,6 na Fig.29).
_NOMO = {
    TipoAcostamento.SEM_CONCRETO: dict(
        a1=1543.19, b1=-467.13,              # p1(carga) = a1 + b1*ln(carga_equiv)
        a2=-497.76, b2=297.56,               # p2(EF)    = a2 + b2*EF
        a3=1556.11, b3=-204.39, c3=0.0,      # p3(N) = a3 + b3*L + c3*L^2, L=log10 N
        w=2.2040, offset=-27.158,            # extrapolacao geometrica (calibrada c/ Quadro 11/24)
        carga_min=4.0, carga_max=26.0, ef_min=2.0, ef_max=4.0,
    ),
    TipoAcostamento.COM_CONCRETO: dict(
        a1=1513.2467576, b1=-460.72224491,
        a2=-503.07786561, b2=320.16106719,
        a3=2134.12928571, b3=-470.36035714, c3=25.35535714,
        w=2.3289256198347106, offset=0.0,    # geometrico puro -- NAO validado (ver nota acima)
        carga_min=4.0, carga_max=26.0, ef_min=1.6, ef_max=3.6,
    ),
}

_CARGA_DIVISOR_EROSAO = {
    TipoEixo.SIMPLES: 1.0,
    TipoEixo.TANDEM_DUPLO: 2.0,   # Fig.28/29 tem escala dedicada p/ ETD a 2x a posicao do ES
    TipoEixo.TANDEM_TRIPLO: 1.0,  # ja chega dividido por 3 via _carga_efetiva
}


def _ler_nomograma(carga_equiv_tf: float, fator_eros: float,
                    acostamento: TipoAcostamento) -> float:
    """Le N admissivel na Figura 28/29 digitalizada (ver nota acima)."""
    p = _NOMO[acostamento]
    carga_equiv_tf = min(max(carga_equiv_tf, p["carga_min"]), p["carga_max"])
    ef = min(max(fator_eros, p["ef_min"]), p["ef_max"])
    p1 = p["a1"] + p["b1"] * math.log(carga_equiv_tf)
    p2 = p["a2"] + p["b2"] * ef
    p3 = p1 + (p2 - p1) * p["w"] + p["offset"]
    a3, b3, c3 = p["a3"], p["b3"], p["c3"]
    if c3 == 0.0:
        log_n = (p3 - a3) / b3
    else:
        disc = b3 * b3 - 4 * c3 * (a3 - p3)
        if disc < 0:
            return N_ILIMITADO   # reta sai por cima do topo impresso (10^8) -> N gigante
        raiz = math.sqrt(disc)
        candidatos = [l for l in ((-b3 + raiz) / (2 * c3), (-b3 - raiz) / (2 * c3))
                      if 2.0 <= l <= 9.0]
        log_n = candidatos[0] if candidatos else max((-b3 + raiz) / (2 * c3),
                                                       (-b3 - raiz) / (2 * c3))
    if log_n > 8.3:   # acima do topo impresso da escala (10^8)
        return N_ILIMITADO
    return 10.0 ** log_n


def repeticoes_admissiveis_erosao(fator_eros: float, carga_tf: float,
                                  acostamento: TipoAcostamento,
                                  eixo: TipoEixo = TipoEixo.SIMPLES) -> float:
    """
    Numero admissivel de repeticoes pelo criterio de EROSAO -- leitura da
    Figura 28 (sem acostamento) ou 29 (com acostamento) digitalizada.

    Entrada:
      fator_eros : fator de erosao lido dos Quadros 16-23 (f de h, k, eixo)
      carga_tf   : carga por eixo JA majorada pelo FSC, em tf
                   (tandem triplo: usar 1/3 da carga, ver _carga_efetiva)
      acostamento: escolhe a Figura 28 (sem) ou 29 (com)
      eixo       : define o divisor de carga p/ a escala equivalente a eixo
                   simples da Figura (ver _CARGA_DIVISOR_EROSAO)
    """
    carga_equiv = carga_tf / _CARGA_DIVISOR_EROSAO[eixo]
    return _ler_nomograma(carga_equiv, fator_eros, acostamento)


# =====================================================================
# 5. ESTRUTURAS DE TRAFEGO
# =====================================================================

@dataclass
class FaixaCarga:
    """Uma faixa do espectro de trafego: um tipo de eixo, uma carga, N repeticoes."""
    eixo: TipoEixo
    carga_tf: float            # carga do eixo em tf (sera majorada pelo FSC)
    repeticoes_previstas: float  # do levantamento de trafego


@dataclass
class ParametrosProjeto:
    """Premissas de projeto (passo 1 do roteiro PCA)."""
    fctk_mpa: float            # resistencia caracteristica a tracao na flexao (28 dias)
    k_mpa_m: float             # coeficiente de recalque do sistema
    fsc: float = 1.20          # fator de seguranca de cargas (Quadro 9: 1.0/1.1/1.2/ate 1.5)
    acostamento: TipoAcostamento = TipoAcostamento.SEM_CONCRETO
    com_barras_transferencia: bool = True
    espectro: list[FaixaCarga] = field(default_factory=list)


@dataclass
class ResultadoConsumo:
    """Consumo (fadiga e erosao) de uma faixa de carga para uma espessura.

    Guarda tambem os INTERMEDIARIOS do calculo (p/ a memoria de calculo / transparencia).
    """
    faixa: FaixaCarga
    consumo_fadiga_pct: float
    consumo_erosao_pct: float
    # intermediarios (memoria de calculo)
    carga_efetiva: float = 0.0      # carga x FSC (tandem triplo /3), tf
    carga_padrao: float = 0.0       # carga do eixo-padrao, tf
    sigma_eq: float = 0.0           # tensao equivalente, MPa
    mr: float = 0.0                 # resistencia (fctk), MPa
    sr: float = 0.0                 # relacao de tensoes
    n_adm_fadiga: float = 0.0       # repeticoes admissiveis - fadiga
    fator_erosao: float = 0.0       # fator de erosao
    n_adm_erosao: float = 0.0       # repeticoes admissiveis - erosao


@dataclass
class ResultadoEspessura:
    """Resultado da verificacao de uma espessura-tentativa."""
    h_cm: float
    soma_fadiga_pct: float
    soma_erosao_pct: float
    aprovada: bool
    detalhes: list[ResultadoConsumo]


# =====================================================================
# 6. CONSUMO POR FAIXA E VERIFICACAO DE UMA ESPESSURA
# =====================================================================

def _carga_efetiva(faixa: FaixaCarga, fsc: float) -> float:
    """
    Carga majorada pelo FSC. Para tandem triplo, o abaco trata como 3 eixos
    simples => divide-se a carga total por 3.
    """
    carga = faixa.carga_tf * fsc
    if faixa.eixo == TipoEixo.TANDEM_TRIPLO:
        carga = carga / 3.0
    return carga


def verificar_espessura(h_cm: float, p: ParametrosProjeto) -> ResultadoEspessura:
    """Aplica o roteiro PCA 1984 a uma espessura-tentativa h."""
    mr = p.fctk_mpa   # PCA usa a resistencia a tracao na flexao diretamente
    detalhes: list[ResultadoConsumo] = []
    soma_fadiga = 0.0
    soma_erosao = 0.0

    for faixa in p.espectro:
        carga_ef = _carga_efetiva(faixa, p.fsc)

        # --- Fadiga ---
        sigma_eq = tensao_equivalente(h_cm, p.k_mpa_m, faixa.eixo, p.acostamento)
        carga_padrao = CARGA_PADRAO_TF[faixa.eixo]
        sr = (sigma_eq / mr) * (carga_ef / carga_padrao) ** EXP_CARGA_FADIGA
        n_adm_fadiga = repeticoes_admissiveis_fadiga(
            sigma_eq, mr, carga_ef, carga_padrao)
        consumo_f = 100.0 * faixa.repeticoes_previstas / n_adm_fadiga

        # --- Erosao ---
        fe = fator_erosao(h_cm, p.k_mpa_m, faixa.eixo,
                          p.acostamento, p.com_barras_transferencia)
        n_adm_erosao = repeticoes_admissiveis_erosao(
            fe, carga_ef, p.acostamento, faixa.eixo)
        consumo_e = 100.0 * faixa.repeticoes_previstas / n_adm_erosao

        soma_fadiga += consumo_f
        soma_erosao += consumo_e
        detalhes.append(ResultadoConsumo(
            faixa, consumo_f, consumo_e,
            carga_efetiva=carga_ef, carga_padrao=carga_padrao, sigma_eq=sigma_eq,
            mr=mr, sr=sr, n_adm_fadiga=n_adm_fadiga, fator_erosao=fe,
            n_adm_erosao=n_adm_erosao))

    aprovada = (soma_fadiga <= CONSUMO_MAXIMO) and (soma_erosao <= CONSUMO_MAXIMO)
    return ResultadoEspessura(h_cm, soma_fadiga, soma_erosao, aprovada, detalhes)


# =====================================================================
# 7. DIMENSIONAMENTO (loop iterativo)
# =====================================================================

def dimensionar(p: ParametrosProjeto) -> ResultadoEspessura | None:
    """
    Itera a espessura de H_MIN ate H_MAX e retorna a MENOR espessura aprovada
    (Sigma fadiga <= 100% E Sigma erosao <= 100%). Retorna None se nenhuma passar.
    """
    h = H_MIN_CM
    while h <= H_MAX_CM + 1e-9:
        resultado = verificar_espessura(h, p)
        if resultado.aprovada:
            return resultado
        h += H_PASSO_CM
    return None


def curva_sensibilidade(p: ParametrosProjeto) -> list[ResultadoEspessura]:
    """Retorna o consumo para toda a faixa de h (alimenta o grafico de saida)."""
    resultados = []
    h = H_MIN_CM
    while h <= H_MAX_CM + 1e-9:
        resultados.append(verificar_espessura(h, p))
        h += H_PASSO_CM
    return resultados
