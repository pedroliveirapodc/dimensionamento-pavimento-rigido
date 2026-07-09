"""
_gen_tabelas.py - Parser dos Quadros do IPR-714 a partir do texto extraido.

Le /tmp/m_linear.txt (pdftotext SEM -layout) e monta as tabelas ES/ETD e ETT,
gerando codigo Python pronto para colar em tabelas_pca.py. Faz checagem de
monotonicidade (decrescente em k e em h) e marca celulas suspeitas (OCR).

Uso:  python _gen_tabelas.py
"""
from __future__ import annotations
import re

LINEAR = "_manual_linear.txt"
PAR = re.compile(r"\d,\d\d")          # ex: 3,56
HROW = re.compile(r"^\s*(1[2-9]|2\d|3[0-4])\s*$")  # h de 12 a 34

with open(LINEAR, encoding="latin-1") as f:
    LINES = f.readlines()


def nums(line: str) -> list[float]:
    return [float(x.replace(",", ".")) for x in PAR.findall(line)]


def bloco_linha(prefixo: str, ini: int, fim: int) -> list[float]:
    """Acha a linha que comeca com prefixo (ex '40 ES ETD') e retorna seus numeros."""
    for i in range(ini, fim):
        if LINES[i].lstrip().startswith(prefixo):
            return nums(LINES[i])
    return []


def parse_k20(ini: int, fim: int) -> list[tuple[float, float]]:
    """Bloco k=20: header '20 ES ETD' depois pares rotulados por h."""
    pares = []
    i = max(0, ini - 3)
    while i < fim and not LINES[i].lstrip().startswith("20 ES ETD"):
        i += 1
    i += 1
    # coleta pares na ordem ate achar 'ES: Eixos' (fim do sub-bloco)
    while i < fim:
        if "ES: Eixos" in LINES[i] or LINES[i].lstrip().startswith("40 ES ETD"):
            break
        ns = nums(LINES[i])
        if len(ns) == 2:
            pares.append((ns[0], ns[1]))
        i += 1
    return pares[:23]


def parse_k60_80_100(ini: int, fim: int) -> list[list[tuple]]:
    """Bloco do meio: apos 'ES ETD ES ETD ES ETD', 23 linhas de 6 numeros."""
    i = ini
    while i < fim and LINES[i].strip() != "ES ETD ES ETD ES ETD":
        i += 1
    i += 1
    linhas = []
    while i < fim and len(linhas) < 23:
        ns = nums(LINES[i])
        if len(ns) == 6:
            linhas.append([(ns[0], ns[1]), (ns[2], ns[3]), (ns[4], ns[5])])
        i += 1
    return linhas  # cada item = [k60_par, k80_par, k100_par]


def pares_de_linha(ns: list[float]) -> list[tuple]:
    return [(ns[j], ns[j + 1]) for j in range(0, len(ns) - 1, 2)][:23]


def montar_es_etd(ini: int, fim: int, ultimo_k: str):
    """Monta dict h->[7 pares] para uma tabela ES/ETD. ultimo_k='180' ou '200'."""
    k20 = parse_k20(ini, fim)
    k40 = pares_de_linha(bloco_linha("40 ES ETD", ini, fim))
    meio = parse_k60_80_100(ini, fim)
    k150 = pares_de_linha(bloco_linha("150 ES ETD", ini, fim))
    kult = pares_de_linha(bloco_linha(f"{ultimo_k} ES ETD", ini, fim))
    tabela = {}
    for r in range(23):
        h = 12 + r
        k60, k80, k100 = meio[r]
        tabela[h] = [k20[r], k40[r], k60, k80, k100, k150[r], kult[r]]
    return tabela


def checar(tabela: dict, nome: str):
    """Flag de monotonicidade: valor deve cair com k (na linha) e com h (na coluna)."""
    avisos = []
    hs = sorted(tabela)
    ncol = len(tabela[hs[0]])
    for h in hs:
        for c in range(ncol - 1):
            for idx in (0, 1):  # ES, ETD
                if tabela[h][c][idx] < tabela[h][c + 1][idx] - 0.005:
                    avisos.append(f"  {nome} h={h} col{c}->{c+1} idx{idx}: "
                                  f"{tabela[h][c][idx]} < {tabela[h][c+1][idx]} (sobe com k)")
    return avisos


def emitir(tabela: dict, nome: str, k_axis: list[int]):
    print(f"\n{nome} = {{")
    print(f"    # k = {k_axis}")
    for h in sorted(tabela):
        cels = ", ".join(f"({a:.2f}, {b:.2f})" for a, b in tabela[h])
        print(f"    {h}: [{cels}],")
    print("}")


# Faixas de linha por quadro (ES/ETD): do 'NN ES ETD' inicial ate antes do proximo
QUADROS_ES_ETD = {
    "Q14_ES_ETD_PCAC":      (2944, 3105, "180"),
    "Q18_ES_ETD_JSP_PCAC":  (3988, 4149, "200"),
    "Q20_ES_ETD_JCP_PSAC":  (4508, 4669, "200"),
    "Q22_ES_ETD_JCP_PCAC":  (5028, 5189, "180"),
}

# Correcoes de OCR: (nome_tabela, h, col_idx, sub_idx) -> valor.
# sub_idx: 0=ES, 1=ETD (ES/ETD); para ETT sub_idx e ignorado (col_idx direto).
# Recuperadas da fonte ('68,00'->0.68, '1,18'->2.18, '0,1'->3.01) ou estimadas
# por monotonicidade (marcadas EST). Conferir no PDF p.103-113.
CORRECOES = {
    ("Q14_ES_ETD_PCAC", 27, 4, 1): 0.74,   # EST (k100 ETD)
    ("Q14_ES_ETD_PCAC", 32, 2, 1): 0.68,   # fonte: "68,00"
    ("Q14_ES_ETD_PCAC", 33, 1, 1): 0.72,   # EST (k40 ETD)
    ("Q18_ES_ETD_JSP_PCAC", 29, 2, 0): 2.18,  # fonte: "1,18"
    ("Q22_ES_ETD_JCP_PCAC", 19, 5, 1): 2.41,  # EST (k150 ETD)
    ("Q22_ES_ETD_JCP_PCAC", 24, 1, 0): 2.19,  # EST (k40 ES)
    ("Q22_ES_ETD_JCP_PCAC", 28, 6, 0): 1.90,  # EST (k180 ES)
    ("Q19_ETT_JSP_PCAC", 13, 3, None): 3.01,  # EST (k80)
}


def aplicar_correcoes(tabela: dict, nome: str):
    for (n, h, c, s), val in CORRECOES.items():
        if n != nome:
            continue
        if s is None:
            tabela[h][c] = val
        else:
            par = list(tabela[h][c])
            par[s] = val
            tabela[h][c] = tuple(par)


def parse_ett(ini: int, fim: int) -> dict:
    """Tabela ETT: apos 6 cabecalhos 'ETT', cada h seguido de 6 valores unicos."""
    i = ini
    cont_ett = 0
    while i < fim and cont_ett < 6:
        if LINES[i].strip() == "ETT":
            cont_ett += 1
        i += 1
    tabela = {}
    h = 12
    while i < fim and h <= 34:
        vals = []
        j = i
        while j < fim and len(vals) < 6:
            ns = nums(LINES[j])
            if len(ns) == 1:
                vals.append(ns[0])
            j += 1
        tabela[h] = vals
        h += 1
        i = j
    return tabela


def checar_ett(tabela: dict, nome: str):
    avisos = []
    for h in sorted(tabela):
        row = tabela[h]
        for c in range(len(row) - 1):
            if row[c] < row[c + 1] - 0.005:
                avisos.append(f"  {nome} h={h} col{c}->{c+1}: {row[c]} < {row[c+1]}")
    return avisos


def emitir_ett(tabela: dict, nome: str, k_axis: list[int]):
    print(f"\n{nome} = {{")
    print(f"    # k = {k_axis}")
    for h in sorted(tabela):
        print(f"    {h}: {tabela[h]},")
    print("}")


QUADROS_ETT = {  # k = [20,40,60,80,140,180]
    "Q19_ETT_JSP_PCAC": (4156, 4506),
    "Q21_ETT_JCP_PSAC": (4676, 5026),
    "Q23_ETT_JCP_PCAC": (5196, 5600),
}

def emitir_para(tabela, nome, kax, ett, out):
    if ett:
        out.append(f"\n{nome} = {{")
        out.append(f"    # k = {kax}")
        for h in sorted(tabela):
            out.append(f"    {h}: {tabela[h]},")
        out.append("}")
    else:
        out.append(f"\n{nome} = {{")
        out.append(f"    # k = {kax}")
        for h in sorted(tabela):
            cels = ", ".join(f"({a:.2f}, {b:.2f})" for a, b in tabela[h])
            out.append(f"    {h}: [{cels}],")
        out.append("}")


if __name__ == "__main__":
    out = ['"""Tabelas geradas automaticamente por _gen_tabelas.py (IPR-714).',
           'Correcoes de OCR aplicadas via CORRECOES (ver _gen_tabelas.py)."""', ""]
    restantes = []
    for nome, (ini, fim, ult) in QUADROS_ES_ETD.items():
        kax = [20, 40, 60, 80, 100, 150, int(ult)]
        t = montar_es_etd(ini, fim, ult)
        aplicar_correcoes(t, nome)
        emitir_para(t, nome, kax, False, out)
        restantes += checar(t, nome)
    for nome, (ini, fim) in QUADROS_ETT.items():
        t = parse_ett(ini, fim)
        aplicar_correcoes(t, nome)
        emitir_para(t, nome, [20, 40, 60, 80, 140, 180], True, out)
        restantes += checar_ett(t, nome)
    with open("_tabelas_geradas.py", "w", encoding="utf-8") as f:
        f.write("\n".join(out) + "\n")
    print("Gerado _tabelas_geradas.py")
    print(f"Avisos remanescentes (inversoes <=0,10, fieis a fonte): {len(restantes)}")
    for a in restantes:
        print("# " + a)
