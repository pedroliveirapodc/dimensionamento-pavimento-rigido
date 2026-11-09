"""
triagem.py - Triagem de viabilidade (score) + categorizadores p/ auto-preenchimento.

A triagem pontua 6 criterios (0..3 cada, com peso). Quando o usuario informa o
LOCAL/dados, 4 deles podem ser DERIVADOS (sem perguntar): trafego, CBR, vida util
e precipitacao. Restam sempre 'manut' e 'usina'. Score maximo = 36.
"""
from __future__ import annotations

# criterio -> (rotulo, {valor: texto}, peso). valor alto = mais favoravel a rigido.
PERGUNTAS: dict[str, tuple] = {
    "traf":  ("Volume de tráfego previsto",
              {0: "Baixo (N < 10⁶)", 1: "Médio (10⁶–10⁷)", 2: "Alto (10⁷–10⁸)", 3: "Muito alto (> 10⁸)"}, 3),
    "vida":  ("Vida útil de projeto",
              {0: "10 anos", 1: "20 anos", 2: "30 anos", 3: "40+ anos"}, 2),
    "cbr":   ("Qualidade do subleito (CBR)",
              {0: "Bom (CBR > 10%)", 1: "Razoável (6–10%)", 2: "Baixo (3–6%)", 3: "Muito baixo (< 3%)"}, 2),
    "manut": ("Capacidade de manutenção futura",
              {0: "Alta", 1: "Moderada", 2: "Limitada", 3: "Muito limitada"}, 2),
    "clima": ("Precipitação na região",
              {3: "Baixa (< 1000 mm)", 2: "Média (1000–1500)", 1: "Alta (1500–2000)", 0: "Muito alta (> 2000 mm)"}, 2),
    "usina": ("Acesso a usina de concreto",
              {0: "Sem acesso", 1: "Usina a instalar", 2: "Distante", 3: "Próxima"}, 1),
}

# criterios que podem vir prontos quando ha dados (local/trafego)
DERIVAVEIS = {"traf", "cbr", "vida", "clima"}
PESOS = {k: p for k, (_, _, p) in PERGUNTAS.items()}
SCORE_MAX = sum(PESOS.values()) * 3  # 36


# --- categorizadores (dado real -> valor 0..3 da triagem) ---
def cat_cbr(cbr: float) -> int:
    return 0 if cbr > 10 else 1 if cbr > 6 else 2 if cbr > 3 else 3


def cat_trafego(n_eixos: float) -> int:
    return 0 if n_eixos < 1e6 else 1 if n_eixos < 1e7 else 2 if n_eixos < 1e8 else 3


def cat_periodo(anos: float) -> int:
    return 0 if anos <= 10 else 1 if anos <= 20 else 2 if anos <= 30 else 3


def cat_precip(mm: float) -> int:
    return 3 if mm < 1000 else 2 if mm < 1500 else 1 if mm < 2000 else 0


def score(valores: dict[str, int]) -> int:
    """Soma ponderada dos criterios presentes em 'valores'."""
    return sum(valores.get(k, 0) * PESOS[k] for k in PERGUNTAS)


def recomendacao(sc: int) -> tuple[str, str, str]:
    """(emoji, nivel, texto) a partir do score."""
    pct = 100 * sc / SCORE_MAX
    if pct >= 70:
        return "🟢", "indicado", "Pavimento rígido fortemente indicado."
    if pct >= 40:
        return "🟡", "viavel", "Viável; compare com a solução em pavimento flexível antes de decidir."
    return "🔴", "alerta", "Cenário mais favorável a pavimento flexível (você pode prosseguir)."
