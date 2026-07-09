"""
lcca.py - Custo de Ciclo de Vida (LCCA): pavimento RIGIDO dimensionado vs.
pavimento FLEXIVEL de referencia, em VPL por m2.

Metodo: fluxo de caixa nominal (CAPEX no ano 0 + eventos de manutencao ao longo
do horizonte) descontado a valor presente (VPL = soma custo_t/(1+i)^t).
Todos os custos unitarios vem do SICRO RJ jan/2026 (custos_sicro.py) — "nenhum
numero sai do nada".

O flexivel de referencia NAO e dimensionado (fora do escopo do TCC): a espessura
de CBUQ vem da tabela de espessura minima de revestimento betuminoso por faixa
de N do Manual de Pavimentacao do DNIT (IPR-719), editavel na UI.

Cronogramas de manutencao default (constantes documentadas, editaveis):
- RIGIDO: resselagem de juntas nos anos 8/16/24 (pratica ABCP/DNIT: vida do
  selante 8-10 anos) + reparo localizado de ~2% da area das placas no ano 15.
- FLEXIVEL: recapeamento (pintura de ligacao + 5 cm de CBUQ) nos anos 8/16/24
  (vida funcional tipica do revestimento asfaltico, IPR-719/relatorio setorial)
  + conserva anual leve de 0,5% do CAPEX (remendos/selagem de trincas).
"""
from __future__ import annotations

from dataclasses import dataclass, field

import custos_sicro as cs

# ---------------------------------------------------------------------
# Constantes de projeto (documentadas; editaveis na UI avancada)
# ---------------------------------------------------------------------

# Juntas do pavimento rigido: placas tipicas ~5,0 m (transversal) x 3,75 m
# (longitudinal) => (1/5,0 + 1/3,75) ~= 0,47 m de junta por m2 de pista.
JUNTAS_M_POR_M2 = 0.47

# Tabela IPR-719 (Manual de Pavimentacao DNIT): espessura minima de
# revestimento betuminoso em funcao de N (operacoes do eixo padrao).
# (para N<=1e6 o manual admite tratamento superficial; adotamos 5 cm de CBUQ
#  como piso p/ comparabilidade estrutural)
def espessura_cbuq_cm(n: float) -> float:
    if n <= 1e6:
        return 5.0
    if n <= 5e6:
        return 5.0
    if n <= 1e7:
        return 7.5
    return 12.5


ESP_BASE_FLEX_CM = 20.0     # base granular tipica do flexivel de referencia
RECAP_ESP_CM = 5.0          # espessura do recapeamento em CBUQ
ANOS_RECAP = (8, 16, 24)    # recapeamentos do flexivel
ANOS_SELAGEM = (8, 16, 24)  # resselagem de juntas do rigido
ANO_REPARO_PLACAS = 15      # reparo localizado de placas
FRAC_AREA_REPARO = 0.02     # ~2% da area das placas
CONSERVA_FLEX_FRAC = 0.005  # conserva anual do flexivel (0,5% do CAPEX)

TAXA_DESCONTO_PADRAO = 0.08
HORIZONTE_PADRAO = 30

# custo do reparo localizado de placa (SICRO 4915753, R$/m2 reparado)
_CUSTO_REPARO_PLACA_M2 = 1535.67


# ---------------------------------------------------------------------
# Modelo
# ---------------------------------------------------------------------

@dataclass
class EventoManutencao:
    ano: int
    custo_m2: float          # R$/m2 de pista, nominal
    descricao: str


@dataclass
class Alternativa:
    nome: str
    capex_m2: float
    eventos: list[EventoManutencao] = field(default_factory=list)
    memoria: list[str] = field(default_factory=list)  # linhas "de onde veio"
    # decomposicao do CAPEX p/ graficos/PDF: (componente, R$/m2, fonte SICRO)
    componentes: list[tuple[str, float, str]] = field(default_factory=list)

    def fluxo_anual(self, horizonte: int) -> list[float]:
        """Custo nominal por ano (indice 0 = CAPEX)."""
        fluxo = [0.0] * (horizonte + 1)
        fluxo[0] = self.capex_m2
        for ev in self.eventos:
            if 0 < ev.ano <= horizonte:
                fluxo[ev.ano] += ev.custo_m2
        return fluxo

    def vpl(self, horizonte: int, taxa: float) -> float:
        return sum(c / (1 + taxa) ** t
                   for t, c in enumerate(self.fluxo_anual(horizonte)))

    def acumulado_vp(self, horizonte: int, taxa: float) -> list[float]:
        """Custo acumulado em valor presente, ano a ano (p/ o grafico)."""
        acc, out = 0.0, []
        for t, c in enumerate(self.fluxo_anual(horizonte)):
            acc += c / (1 + taxa) ** t
            out.append(acc)
        return out


@dataclass
class ResultadoLCCA:
    rigido: Alternativa
    flexivel: Alternativa
    horizonte: int
    taxa: float
    vpl_rigido: float
    vpl_flexivel: float
    ano_cruzamento: int | None   # 1o ano em que o acumulado do rigido fica <= flexivel

    @property
    def vantagem_rigido(self) -> bool:
        return self.vpl_rigido <= self.vpl_flexivel

    @property
    def caue_rigido(self) -> float:
        return caue(self.vpl_rigido, self.horizonte, self.taxa)

    @property
    def caue_flexivel(self) -> float:
        return caue(self.vpl_flexivel, self.horizonte, self.taxa)


def caue(vpl: float, horizonte: int, taxa: float) -> float:
    """Custo Anual Uniforme Equivalente (R$/m2 por ano).

    CAUE = VPL x FRC, com FRC = i(1+i)^n / ((1+i)^n - 1) (fator de recuperacao
    de capital, engenharia economica classica). Responde "quanto custa por ano"
    de forma comparavel entre alternativas de perfis de gasto diferentes.
    """
    if horizonte <= 0:
        return vpl
    if taxa <= 0:
        return vpl / horizonte
    frc = taxa * (1 + taxa) ** horizonte / ((1 + taxa) ** horizonte - 1)
    return vpl * frc


# ---------------------------------------------------------------------
# Montagem das alternativas
# ---------------------------------------------------------------------

def alternativa_rigido(h_cm: float, tipo_subbase: str,
                       esp_subbase_cm: float) -> Alternativa:
    """CAPEX e manutencao do pavimento rigido dimensionado."""
    c_placa = (h_cm / 100.0) * cs.custo_revestimento(
        "Placa de concreto (fôrmas deslizantes)")
    c_sb = ((esp_subbase_cm / 100.0) * (cs.custo_m3(tipo_subbase) or 0.0)
            if tipo_subbase != "Sem sub-base" else 0.0)
    c_juntas = JUNTAS_M_POR_M2 * cs.custo_revestimento("Serragem e selagem de juntas")
    c_cura = cs.custo_revestimento("Cura química")
    capex = c_placa + c_sb + c_juntas + c_cura

    selagem = JUNTAS_M_POR_M2 * cs.custo_revestimento("Serragem e selagem de juntas")
    reparo = FRAC_AREA_REPARO * _CUSTO_REPARO_PLACA_M2

    eventos = [EventoManutencao(a, selagem, "Resselagem de juntas")
               for a in ANOS_SELAGEM]
    eventos.append(EventoManutencao(
        ANO_REPARO_PLACAS, reparo,
        f"Reparo localizado (~{FRAC_AREA_REPARO:.0%} das placas)"))

    mem = [
        f"Placa {h_cm:.1f} cm × R$ {cs.custo_revestimento('Placa de concreto (fôrmas deslizantes)'):.2f}/m³ = R$ {c_placa:.2f}/m²",
        f"Sub-base {tipo_subbase} {esp_subbase_cm:.0f} cm = R$ {c_sb:.2f}/m²",
        f"Juntas ({JUNTAS_M_POR_M2} m/m²) + selagem = R$ {c_juntas:.2f}/m²",
        f"Cura química = R$ {c_cura:.2f}/m²",
    ]
    cod_sb = (cs.CUSTOS_RJ.get(tipo_subbase) or {}).get("codigo")
    comp = [
        (f"Placa de concreto ({h_cm:.1f} cm)", c_placa, "SICRO 4011532"),
        (f"Sub-base {tipo_subbase} ({esp_subbase_cm:.0f} cm)", c_sb,
         f"SICRO {cod_sb}" if cod_sb else "—"),
        ("Juntas (serragem + selagem)", c_juntas, "SICRO 4011537"),
        ("Cura química", c_cura, "SICRO 4011236"),
    ]
    return Alternativa("Rígido (PCA 1984)", capex, eventos, mem, comp)


def alternativa_flexivel(n_eixo_padrao: float,
                         esp_cbuq_cm: float | None = None,
                         esp_base_cm: float = ESP_BASE_FLEX_CM,
                         horizonte: int = HORIZONTE_PADRAO) -> Alternativa:
    """Flexivel de REFERENCIA (nao dimensionado): CBUQ (IPR-719) + base granular."""
    e_cbuq = esp_cbuq_cm if esp_cbuq_cm is not None else espessura_cbuq_cm(n_eixo_padrao)
    t_cbuq_m2 = (e_cbuq / 100.0) * cs.DENSIDADE_CBUQ_T_M3
    c_cbuq = t_cbuq_m2 * cs.custo_revestimento("CBUQ capa (faixa C-12,5)")
    c_base = (esp_base_cm / 100.0) * cs.custo_revestimento("Base granular (BGS)")
    c_pinturas = (cs.custo_revestimento("Imprimação")
                  + cs.custo_revestimento("Pintura de ligação"))
    capex = c_cbuq + c_base + c_pinturas

    recap = (cs.custo_revestimento("Pintura de ligação")
             + (RECAP_ESP_CM / 100.0) * cs.DENSIDADE_CBUQ_T_M3
             * cs.custo_revestimento("CBUQ capa (faixa C-12,5)"))
    eventos = [EventoManutencao(a, recap, f"Recapeamento {RECAP_ESP_CM:.0f} cm CBUQ")
               for a in ANOS_RECAP]
    conserva = CONSERVA_FLEX_FRAC * capex
    for ano in range(1, horizonte + 1):
        if ano not in ANOS_RECAP:
            eventos.append(EventoManutencao(ano, conserva, "Conserva anual"))

    mem = [
        f"CBUQ {e_cbuq:.1f} cm ({t_cbuq_m2:.3f} t/m² × R$ {cs.custo_revestimento('CBUQ capa (faixa C-12,5)'):.2f}/t) = R$ {c_cbuq:.2f}/m²",
        f"Base granular {esp_base_cm:.0f} cm = R$ {c_base:.2f}/m²",
        f"Imprimação + pintura de ligação = R$ {c_pinturas:.2f}/m²",
    ]
    comp = [
        (f"CBUQ ({e_cbuq:.1f} cm)", c_cbuq, "SICRO 4011462"),
        (f"Base granular ({esp_base_cm:.0f} cm)", c_base, "SICRO 4011275"),
        ("Imprimação + pintura de ligação", c_pinturas, "SICRO 4011352/4011353"),
    ]
    return Alternativa("Flexível (referência IPR-719)", capex, eventos, mem, comp)


# ---------------------------------------------------------------------
# Comparacao
# ---------------------------------------------------------------------

def comparar(h_cm: float, tipo_subbase: str, esp_subbase_cm: float,
             n_eixo_padrao: float,
             horizonte: int = HORIZONTE_PADRAO,
             taxa: float = TAXA_DESCONTO_PADRAO,
             esp_cbuq_cm: float | None = None) -> ResultadoLCCA:
    rig = alternativa_rigido(h_cm, tipo_subbase, esp_subbase_cm)
    flx = alternativa_flexivel(n_eixo_padrao, esp_cbuq_cm, horizonte=horizonte)

    vpl_r = rig.vpl(horizonte, taxa)
    vpl_f = flx.vpl(horizonte, taxa)

    acc_r = rig.acumulado_vp(horizonte, taxa)
    acc_f = flx.acumulado_vp(horizonte, taxa)
    ano_cruz = None
    for t in range(horizonte + 1):
        if acc_r[t] <= acc_f[t]:
            ano_cruz = t
            break

    return ResultadoLCCA(rig, flx, horizonte, taxa, vpl_r, vpl_f, ano_cruz)


def fluxo_detalhado(res: ResultadoLCCA) -> list[dict]:
    """A conta inteira, linha a linha (p/ tabela na UI e no PDF).

    Cada linha: pavimento, ano, evento, custo nominal, fator de desconto
    1/(1+i)^t, valor presente e acumulado (VP). O acumulado final de cada
    pavimento fecha com o respectivo VPL.
    """
    linhas = []
    for alt, rotulo in ((res.rigido, "Rígido"), (res.flexivel, "Asfalto")):
        desc_por_ano: dict[int, list[str]] = {}
        for ev in alt.eventos:
            desc_por_ano.setdefault(ev.ano, []).append(ev.descricao)
        acumulado = 0.0
        for t, custo in enumerate(alt.fluxo_anual(res.horizonte)):
            if custo <= 0:
                continue
            fator = 1 / (1 + res.taxa) ** t
            vp = custo * fator
            acumulado += vp
            evento = ("Construção (CAPEX)" if t == 0
                      else " + ".join(dict.fromkeys(desc_por_ano.get(t, ["Manutenção"]))))
            linhas.append({"pavimento": rotulo, "ano": t, "evento": evento,
                           "nominal": custo, "fator": fator, "vp": vp,
                           "acumulado": acumulado})
    return linhas


if __name__ == "__main__":
    # smoke test: h=25cm, solo-cimento 15cm, trafego pesado
    r = comparar(h_cm=25.0, tipo_subbase="Solo-cimento", esp_subbase_cm=15.0,
                 n_eixo_padrao=2e7)
    for alt, vpl in ((r.rigido, r.vpl_rigido), (r.flexivel, r.vpl_flexivel)):
        print(f"\n{alt.nome}: CAPEX R$ {alt.capex_m2:.2f}/m² | VPL({r.horizonte}a,"
              f" {r.taxa:.0%}) R$ {vpl:.2f}/m²")
        for linha in alt.memoria:
            print("   ", linha)
        for ev in sorted(alt.eventos, key=lambda e: e.ano)[:6]:
            print(f"    ano {ev.ano:>2}: R$ {ev.custo_m2:6.2f}/m²  {ev.descricao}")
    print(f"\nAno de cruzamento (acumulado VP): {r.ano_cruzamento}")
    print("Vantagem no horizonte:", "RÍGIDO" if r.vantagem_rigido else "FLEXÍVEL")
