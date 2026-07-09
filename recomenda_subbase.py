"""
recomenda_subbase.py - Recomendacao do TIPO de sub-base (Ponto 2).

NAO e um lookup de material existente (sub-base e decisao de projeto). E um motor
de DECISAO transparente que sugere o tipo de sub-base a partir de:
  - nivel de TRAFEGO (N = total de eixos pesados solicitantes no periodo), e
  - qualidade do SUBLEITO (k0 / CBR, vindo do Ponto 1 ou do Estagio 3).

Logica (diretriz DNIT/PCA, IPR-714): trafego pesado e/ou subleito fraco -> sub-base
CIMENTADA, que eleva o coeficiente de recalque k e reduz o dano por EROSAO (criterio
que costuma governar). Trafego leve + subleito bom -> granular ou sem sub-base.

Quantifica cada opcao pelo k efetivo resultante (estagio3.k_efetivo). O CUSTO por
regiao (SICRO/DNIT) fica como camada futura; aqui a recomendacao e tecnica.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import estagio3 as e3
import custos_sicro as cs

# Espessura de referencia p/ comparar o k efetivo das opcoes (valida em todas as
# tabelas do estagio3: granular 10-30, cimentadas 10-15/20).
ESP_REF_CM = 15.0

# Limiares de nivel de trafego por N (eixos pesados solicitantes no periodo).
# Faixas usuais de projeto rodoviario (ordens de grandeza).
def nivel_trafego(n_eixos: float) -> tuple[int, str]:
    if n_eixos < 5e5:      return 0, "leve"
    if n_eixos < 5e6:      return 1, "medio"
    if n_eixos < 5e7:      return 2, "pesado"
    return 3, "muito pesado"


# Qualidade do subleito por k0 (MPa/m). Indice = "fraqueza" (maior = pior).
def nivel_subleito(k0: float) -> tuple[int, str]:
    if k0 >= 80:  return 0, "bom"
    if k0 >= 50:  return 1, "medio"
    if k0 >= 30:  return 2, "fraco"
    return 3, "muito fraco"


# Mapa exigencia (0..6 = idx_trafego + idx_fraqueza) -> tipo de sub-base recomendado.
_CHAVE = {
    "Sem sub-base":                     "Sem sub-base",
    "Granular (BGS/macadame)":          "Granular (BGS/macadame)",
    "Brita tratada com cimento (BGTC)": "Brita tratada com cimento (BGTC)",
    "Solo-cimento":                     "Solo-cimento",
    "Concreto rolado (CCR)":            "Concreto rolado (CCR)",
}
_POR_EXIGENCIA = {
    0: "Sem sub-base",
    1: "Granular (BGS/macadame)",
    2: "Granular (BGS/macadame)",
    3: "Solo-cimento",
    4: "Solo-cimento",
    5: "Brita tratada com cimento (BGTC)",
    6: "Concreto rolado (CCR)",
}


@dataclass
class Recomendacao:
    tipo_recomendado: str
    nivel_trafego: str
    nivel_subleito: str
    exigencia: int
    justificativa: str
    opcoes: list[dict] = field(default_factory=list)  # [{tipo,k_efetivo,custo_m3,ganho_k,eficiencia,nota}]
    ressalva: str = ""
    custo_recomendado: float | None = None
    mais_custo_efetiva: str | None = None


def recomendar(n_eixos_pesados: float, k0: float,
               espessura_ref: float = ESP_REF_CM) -> Recomendacao:
    it, lt = nivel_trafego(n_eixos_pesados)
    isb, lsb = nivel_subleito(k0)
    exig = it + isb
    tipo = _POR_EXIGENCIA[exig]

    # Justificativa textual conforme o caso.
    if exig <= 1:
        jus = (f"Trafego {lt} e subleito {lsb}: exigencia baixa. "
               f"Sub-base simples ja atende; foco em drenagem/regularizacao.")
    elif exig <= 3:
        jus = (f"Trafego {lt} / subleito {lsb}: exigencia moderada. "
               f"Sub-base que eleve o k e de suporte uniforme.")
    else:
        jus = (f"Trafego {lt} e/ou subleito {lsb}: exigencia alta. "
               f"Sub-base CIMENTADA p/ elevar o k e reduzir a EROSAO (criterio "
               f"que tende a governar em trafego pesado).")

    # k efetivo + custo (SICRO) de cada opcao, na espessura de referencia.
    # Eficiencia = ganho de k por R$/m3 investido (MPa/m por R$/m3) -> custo-beneficio.
    opcoes = []
    for nome in _CHAVE:
        try:
            esp = 0.0 if nome == "Sem sub-base" else espessura_ref
            kef = e3.k_efetivo(k0, nome, esp)
        except Exception:
            kef = None
        custo = cs.custo_m3(nome)
        ganho = (kef - k0) if kef is not None else None
        if ganho and custo and custo > 0:
            eficiencia = ganho / custo  # MPa/m por R$/m3
        else:
            eficiencia = None
        opcoes.append({"tipo": nome, "k_efetivo": kef, "custo_m3": custo,
                       "ganho_k": ganho, "eficiencia": eficiencia,
                       "nota": "recomendado" if nome == tipo else ""})

    # Opcao mais CUSTO-EFETIVA (maior ganho de k por R$), entre as que dao ganho.
    candidatas = [o for o in opcoes if o["eficiencia"] is not None]
    mais_eficiente = max(candidatas, key=lambda o: o["eficiencia"])["tipo"] if candidatas else None

    custo_rec = cs.custo_m3(tipo)
    ress = (f"Recomendacao TECNICA (estrutural) + custo de referencia {cs.REFERENCIA}. "
            f"A escolha final considera disponibilidade local de material.")
    return Recomendacao(tipo, lt, lsb, exig, jus, opcoes, ress,
                        custo_recomendado=custo_rec, mais_custo_efetiva=mais_eficiente)


if __name__ == "__main__":
    casos = [
        ("Leve + subleito bom",      3e5, 90),
        ("Medio + subleito fraco",   2e6, 40),
        ("Pesado + subleito medio",  2e7, 60),
        ("Muito pesado + fraco",     8e7, 35),
    ]
    for nome, n, k0 in casos:
        r = recomendar(n, k0)
        print(f"\n{nome}  (N={n:.0e}, k0={k0})")
        print(f"  -> {r.tipo_recomendado}  [{r.nivel_trafego} / subleito {r.nivel_subleito}, exig {r.exigencia}]")
        print(f"     {r.justificativa}")
        for o in r.opcoes:
            kf = f"{o['k_efetivo']:.0f}" if o['k_efetivo'] is not None else "-"
            print(f"       {o['tipo']:34} k_ef={kf:>4} MPa/m {'<--' if o['nota'] else ''}")
