"""
perfis_trafego.py - Perfis-tipo de composicao de trafego (modo expedito/semi).

Permite estimar o espectro de eixos a partir de POUCOS dados:
  - um PERFIL de via (que define a % de cada classe de veiculo), e
  - o VOLUME de trafego (VMDa - volume medio diario anual) + periodo de projeto.

IMPORTANTE (para a banca):
  - A configuracao de EIXOS de cada classe vem do Manual IPR-723 (veiculos_dnit.py)
    -> dado RIGOROSO e citavel.
  - A COMPOSICAO (% de cada classe) dos perfis abaixo e uma REFERENCIA EDITAVEL,
    ancorada em ordens de grandeza do IPR-723 (ex.: PNTC: ~56% automoveis, ~8%
    onibus, ~36% caminhoes). Nao substitui contagem real; serve de ponto de
    partida que o usuario ajusta. Quando houver dado real (PNCT por posto), use-o
    para o VOLUME e, se possivel, para a composicao.
"""
from __future__ import annotations

from dataclasses import dataclass

from calculos import FaixaCarga
import veiculos_dnit as vd


@dataclass(frozen=True)
class PerfilTrafego:
    """Composicao percentual da frota (fracao de cada classe DNIT)."""
    nome: str
    descricao: str
    composicao: dict[str, float]  # {codigo_classe: fracao} (soma ~1.0)

    def normalizada(self) -> dict[str, float]:
        s = sum(self.composicao.values()) or 1.0
        return {k: v / s for k, v in self.composicao.items()}


# ---------------------------------------------------------------
# Perfis de referencia (EDITAVEIS). Percentuais ilustrativos por classe DNIT.
# A internal split dos caminhoes segue o porte tipico da via.
# ---------------------------------------------------------------
PERFIS: dict[str, PerfilTrafego] = {
    "local": PerfilTrafego(
        "Via local / urbana", "Predomina trafego leve; poucos caminhoes leves.",
        {"P": 0.78, "U": 0.10, "M": 0.06, "2CB": 0.01, "2C": 0.03, "3C": 0.02}),
    "coletora": PerfilTrafego(
        "Coletora / arterial", "Mistura urbana com caminhoes medios e onibus.",
        {"P": 0.68, "U": 0.10, "M": 0.05, "2CB": 0.02, "3CB": 0.01,
         "2C": 0.06, "3C": 0.04, "2S3": 0.03, "3S3": 0.01}),
    "rodovia": PerfilTrafego(
        "Rodovia arterial", "Trafego de longa distancia; caminhoes variados.",
        {"P": 0.55, "U": 0.08, "M": 0.04, "2CB": 0.02, "3CB": 0.01,
         "2C": 0.07, "3C": 0.07, "2S2": 0.03, "2S3": 0.08, "3S3": 0.05}),
    "rodovia_pesada": PerfilTrafego(
        "Rodovia troncal pesada", "Corredor de carga; alta fracao de combinacoes.",
        {"P": 0.42, "U": 0.06, "M": 0.03, "2CB": 0.01, "3CB": 0.01,
         "2C": 0.06, "3C": 0.09, "2S2": 0.04, "2S3": 0.14, "3S3": 0.11,
         "3T6": 0.03}),
}


def frota_diaria(perfil: PerfilTrafego, vmda: float) -> dict[str, float]:
    """Numero de veiculos/dia de cada classe = VMDa * fracao da classe."""
    return {c: vmda * frac for c, frac in perfil.normalizada().items()}


def espectro_de_projeto(perfil: PerfilTrafego, vmda: float,
                        periodo_anos: int = 20,
                        fator_sentido: float = 0.5,
                        fator_faixa: float = 1.0,
                        taxa_crescimento: float = 0.0,
                        fator_carga: float = vd.FATOR_CARGA_PADRAO) -> list[FaixaCarga]:
    """
    Espectro de eixos para TODO o periodo de projeto.

    N_total de cada classe = VMDa * fracao * 365 * periodo * Fs * Ff * Fc
      - fator_sentido (Fs): fracao do trafego no sentido/pista de projeto (0,5 = bidirecional)
      - fator_faixa (Ff): fracao na faixa de projeto (1,0 = pista de 1 faixa por sentido)
      - taxa_crescimento (g): se >0, aplica fator de periodo de juros compostos
            Fc = ((1+g)^periodo - 1) / g ; senao Fc = periodo (linear)
    A conversao classe -> eixos usa veiculos_dnit (Manual IPR-723) -- "fator
    de eixo" (numero de eixos por veiculo, rigoroso). "Fator de carga"
    (carregamento em relacao ao limite legal, ver veiculos_dnit) e repassado
    direto a espectro_de_frota; default 1,0 mantem o comportamento anterior.
    """
    if taxa_crescimento > 0:
        g = taxa_crescimento
        fator_periodo = ((1 + g) ** periodo_anos - 1) / g
    else:
        fator_periodo = float(periodo_anos)

    veic_dia = frota_diaria(perfil, vmda)
    fator = 365.0 * fator_periodo * fator_sentido * fator_faixa
    frota_total = {c: n * fator for c, n in veic_dia.items()}
    return vd.espectro_de_frota(frota_total, fator_carga=fator_carga)


if __name__ == "__main__":
    p = PERFIS["rodovia_pesada"]
    print(f"Perfil: {p.nome} (VMDa=8000, 20 anos, g=3%/ano)\n")
    esp = espectro_de_projeto(p, vmda=8000, periodo_anos=20, taxa_crescimento=0.03)
    tot = 0.0
    for f in esp:
        print(f"  {f.eixo.value:14} {f.carga_tf:5.1f} t  ->  {f.repeticoes_previstas:14,.0f} eixos")
        tot += f.repeticoes_previstas
    print(f"\n  Total de eixos solicitantes (pesados): {tot:,.0f}")
