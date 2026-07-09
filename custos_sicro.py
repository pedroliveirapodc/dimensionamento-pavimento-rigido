"""
custos_sicro.py - Custo de referencia das sub-bases (SICRO/DNIT), por m3.

Fonte: SICRO (Sistema de Custos Referenciais de Obras do DNIT), Relatorio Sintetico
de Composicoes de Custos. Valores REAIS extraidos do relatorio oficial:
  UF = Rio de Janeiro | referencia = JANEIRO/2026 | arquivo rj-01-2026.7z (gov.br/dnit).

Premissa adotada para comparacao: composicao com "brita PRODUZIDA" (britagem no
proprio servico) e 100% Proctor - base usual de projeto rodoviario. A variante com
"brita COMERCIAL" (comprada) custa ~1,7-2,3x mais; depende da proximidade de
pedreira (logistica regional). Os custos sao por m3 de camada compactada.

Para outras UFs / datas: baixar o relatorio correspondente no SICRO e atualizar a
tabela (mesmos codigos de composicao). Aqui esta o RJ, foco do app.
"""
from __future__ import annotations

REFERENCIA = "SICRO RJ — janeiro/2026 (brita produzida, 100% Proctor)"

# tipo de sub-base (chave igual a estagio3.TIPOS_SUBBASE) -> custo de referencia
CUSTOS_RJ: dict[str, dict] = {
    "Sem sub-base": {
        "codigo": None, "rs_m3": 0.0,
        "descricao": "sem camada de sub-base"},
    "Granular (BGS/macadame)": {
        "codigo": "4011275", "rs_m3": 121.46,
        "descricao": "Base/sub-base de brita graduada - brita produzida - 100% Proctor mod."},
    "Solo-cimento": {
        "codigo": "4011314", "rs_m3": 117.38,
        "descricao": "Base/sub-base de solo-cimento 7% cimento, usina - 100% Proctor normal"},
    "Brita tratada com cimento (BGTC)": {
        "codigo": "4011277", "rs_m3": 169.97,
        "descricao": "Base/sub-base de brita graduada tratada com cimento - brita produzida"},
    "Concreto rolado (CCR)": {
        "codigo": "4011213", "rs_m3": 184.50,
        "descricao": "Sub-base de concreto compactado com rolo - brita produzida"},
}


# ---------------------------------------------------------------------
# Revestimentos e servicos p/ o LCCA (mesma fonte/premissas: RJ jan/2026,
# brita produzida). Unidade indicada em cada item.
# ---------------------------------------------------------------------
CUSTOS_REVESTIMENTO: dict[str, dict] = {
    "Placa de concreto (fôrmas deslizantes)": {
        "codigo": "4011532", "valor": 329.51, "unidade": "m3",
        "descricao": "Pavimento de concreto com fôrmas deslizantes - areia extraída e brita produzida"},
    "CBUQ capa (faixa C-12,5)": {
        "codigo": "4011462", "valor": 145.09, "unidade": "t",
        "descricao": "Concreto asfáltico - faixa C-12,5 - areia extraída e brita produzida"},
    "CBUQ binder (faixa B-19)": {
        "codigo": "4011458", "valor": 145.48, "unidade": "t",
        "descricao": "Concreto asfáltico - faixa B-19 - areia extraída e brita produzida"},
    "Base granular (BGS)": {
        "codigo": "4011275", "valor": 121.46, "unidade": "m3",
        "descricao": "Base/sub-base de brita graduada - brita produzida - 100% Proctor mod."},
    "Serragem e selagem de juntas": {
        "codigo": "4011537", "valor": 23.67, "unidade": "m",
        "descricao": "Serragem de juntas em pavimento de concreto, limpeza e enchimento com selante a frio"},
    "Cura química": {
        "codigo": "4011236", "valor": 2.34, "unidade": "m2",
        "descricao": "Cura química para pavimento de concreto (equip. pequeno porte)"},
    "Imprimação": {
        "codigo": "4011352", "valor": 0.63, "unidade": "m2",
        "descricao": "Imprimação com emulsão asfáltica"},
    "Pintura de ligação": {
        "codigo": "4011353", "valor": 0.43, "unidade": "m2",
        "descricao": "Pintura de ligação"},
}

# massa especifica de projeto do CBUQ compactado (t/m3) — valor usual DNIT (2,4-2,5)
DENSIDADE_CBUQ_T_M3 = 2.4


def custo_revestimento(item: str) -> float:
    """Valor unitario do item de revestimento (unidade em CUSTOS_REVESTIMENTO)."""
    return CUSTOS_REVESTIMENTO[item]["valor"]


def custo_m3(tipo_subbase: str) -> float | None:
    """Custo de referencia (R$/m3) do tipo de sub-base, ou None se desconhecido."""
    item = CUSTOS_RJ.get(tipo_subbase)
    return item["rs_m3"] if item else None


def info(tipo_subbase: str) -> dict | None:
    return CUSTOS_RJ.get(tipo_subbase)


if __name__ == "__main__":
    print(REFERENCIA, "\n")
    for tipo, d in CUSTOS_RJ.items():
        cod = d["codigo"] or "—"
        print(f"  {tipo:34} R$ {d['rs_m3']:7.2f}/m3  (SICRO {cod})")
