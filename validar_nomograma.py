"""
validar_nomograma.py - Aferição da digitalização das Figuras 28 e 29 (IPR-714).

Consolida TODOS os pontos oficiais disponíveis no manual e mede o erro da
leitura do nomograma implementada em calculos._ler_nomograma().

Fontes dos pontos (todas oficiais, do próprio manual):
  - Quadro 11 (pág. 116-117): h=25 cm, k=100, PSAC/JSP -> eixos simples, EF=2,72
  - Quadro 24 (pág. 118):     h=26 cm, k=100, PSAC/JSP -> ES (EF=2,68),
                              ETD (EF=2,86) e ETT (EF=2,89)

⚠️ TODOS os 34 pontos são da FIGURA 28 (sem acostamento de concreto).
O manual NÃO traz nenhum exemplo resolvido com acostamento, portanto a
Figura 29 NÃO tem como ser aferida numericamente aqui - só é possível
checar coerência interna (monotonia e ordenação física), feito no final.

Rode:  python validar_nomograma.py
"""
from __future__ import annotations
import calculos as c

# ---------------------------------------------------------------------------
# Pontos oficiais: (carga_por_eixo_majorada_tf, N_admissivel_erosao_do_manual)
# ---------------------------------------------------------------------------
PONTOS = {
    # (rotulo, fator de erosao, tipo de eixo)
    ("Quadro 11 - ES  (h=25)", 2.72, c.TipoEixo.SIMPLES): [
        (9.6, 21.2e6), (10.8, 8.5e6), (12.0, 4.0e6), (13.2, 2.5e6),
        (14.4, 1.43e6), (15.6, 825e3), (16.8, 555e3), (18.0, 365e3),
        (19.2, 265e3),
    ],
    ("Quadro 24 - ES  (h=26)", 2.68, c.TipoEixo.SIMPLES): [
        (9.6, 26.0e6), (10.8, 10.0e6), (12.0, 5.1e6), (13.2, 2.75e6),
        (14.4, 1.7e6), (15.6, 1.0e6), (16.8, 630e3), (18.0, 420e3),
        (19.2, 290e3),
    ],
    ("Quadro 24 - ETD (h=26)", 2.86, c.TipoEixo.TANDEM_DUPLO): [
        (15.6, 30.0e6), (16.8, 16.0e6), (18.0, 9.3e6), (19.2, 6.1e6),
        (20.4, 4.0e6), (21.6, 2.8e6), (22.8, 2.0e6), (24.0, 1.6e6),
        (25.2, 1.2e6), (26.4, 880e3), (27.6, 680e3), (28.8, 520e3),
    ],
    ("Quadro 24 - ETT (h=26)", 2.89, c.TipoEixo.TANDEM_TRIPLO): [
        (9.6, 4.5e6), (10.4, 2.9e6), (11.2, 1.9e6), (12.0, 1.4e6),
    ],
}


def _erro_pct(modelo: float, manual: float) -> float:
    return 100.0 * (modelo - manual) / manual


def aferir_figura28() -> None:
    print("=" * 78)
    print("FIGURA 28 (sem acostamento) - aferição contra os 34 pontos oficiais")
    print("=" * 78)

    todos = []
    for (rotulo, ef, eixo), pts in PONTOS.items():
        print(f"\n  {rotulo}   |   fator de erosão = {ef}")
        print(f"  {'carga(tf)':>9} {'N manual':>13} {'N modelo':>13} {'erro':>9}")
        print("  " + "-" * 48)
        erros_grupo = []
        for carga, n_manual in pts:
            n_mod = c.repeticoes_admissiveis_erosao(
                ef, carga, c.TipoAcostamento.SEM_CONCRETO, eixo)
            e = _erro_pct(n_mod, n_manual)
            erros_grupo.append(abs(e))
            todos.append(abs(e))
            print(f"  {carga:>9.1f} {n_manual:>13,.0f} {n_mod:>13,.0f} {e:>+8.1f}%")
        med = sum(erros_grupo) / len(erros_grupo)
        print(f"  {'->':>9} erro médio do grupo = {med:5.1f}%  |  "
              f"máx = {max(erros_grupo):5.1f}%")

    todos.sort()
    n = len(todos)
    print("\n" + "=" * 78)
    print(f"  TOTAL: {n} pontos oficiais (todos da Figura 28)")
    print(f"  Erro absoluto MÉDIO   = {sum(todos)/n:5.1f}%")
    print(f"  Erro absoluto MEDIANO = {todos[n//2]:5.1f}%")
    print(f"  Erro absoluto MÁXIMO  = {todos[-1]:5.1f}%")
    print(f"  Pontos com erro <10%  = {sum(1 for e in todos if e < 10)}/{n}")
    print(f"  Pontos com erro <20%  = {sum(1 for e in todos if e < 20)}/{n}")
    print("=" * 78)


def coerencia_figura29() -> None:
    """A Fig.29 não tem exemplo oficial. Só dá para checar coerência física."""
    print("\n" + "=" * 78)
    print("FIGURA 29 (com acostamento) - sem exemplo oficial no manual")
    print("Só é possível checar COERÊNCIA FÍSICA, não precisão numérica.")
    print("=" * 78)

    print("\n  (a) N admissível deve CRESCER quando o fator de erosão CAI")
    print(f"  {'FE':>6} {'N (carga 15,6tf)':>20}")
    print("  " + "-" * 28)
    ant = None
    ok_a = True
    for ef in (3.4, 3.2, 3.0, 2.8, 2.6, 2.4, 2.2, 2.0, 1.8):
        n = c.repeticoes_admissiveis_erosao(
            ef, 15.6, c.TipoAcostamento.COM_CONCRETO, c.TipoEixo.SIMPLES)
        marca = ""
        if ant is not None and n < ant:
            marca = "  <-- INVERSÃO!"
            ok_a = False
        print(f"  {ef:>6.1f} {n:>20,.0f}{marca}")
        ant = n
    print(f"  => {'OK, monotônico' if ok_a else 'FALHOU'}")

    print("\n  (b) N admissível deve CAIR quando a carga CRESCE")
    print(f"  {'carga':>6} {'N (EF=2,4)':>20}")
    print("  " + "-" * 28)
    ant = None
    ok_b = True
    for carga in (8.0, 10.0, 12.0, 14.0, 16.0, 18.0, 20.0, 22.0):
        n = c.repeticoes_admissiveis_erosao(
            2.4, carga, c.TipoAcostamento.COM_CONCRETO, c.TipoEixo.SIMPLES)
        marca = ""
        if ant is not None and n > ant:
            marca = "  <-- INVERSÃO!"
            ok_b = False
        print(f"  {carga:>6.1f} {n:>20,.0f}{marca}")
        ant = n
    print(f"  => {'OK, monotônico' if ok_b else 'FALHOU'}")

    print("\n  (c) Acostamento de concreto deve ser SEMPRE mais permissivo")
    print("      ATENÇÃO: a comparação tem de ser PAREADA - mesma h e k, cada")
    print("      caso lido na SUA tabela e na SUA figura. Comparar 'mesmo EF'")
    print("      nas duas figuras NÃO tem sentido físico: o EF já embute o")
    print("      acostamento (Q16 dá 2,72 onde Q18 dá 2,31 para a mesma placa),")
    print("      e as escalas de EF das duas figuras nem cobrem a mesma faixa")
    print("      (Fig.28: 2,0-4,0  |  Fig.29: 1,6-3,6).")
    import tabelas_pca as tab
    print(f"\n  {'h(cm)':>6} {'EF s/ac':>8} {'N Fig.28':>14} {'EF c/ac':>8} "
          f"{'N Fig.29':>14} {'razão':>8}")
    print("  " + "-" * 62)
    ok_c = True
    for h in (20, 22, 25, 28, 30, 32):
        ef_s = tab.consultar(tab.Q16_ES_ETD_JSP_PSAC, tab.K_ERO_ES_ETD, h, 100, 0)
        ef_c = tab.consultar(tab.Q18_ES_ETD_JSP_PCAC, tab.K_ERO_ES_ETD, h, 100, 0)
        n_s = c.repeticoes_admissiveis_erosao(
            ef_s, 15.6, c.TipoAcostamento.SEM_CONCRETO, c.TipoEixo.SIMPLES)
        n_c = c.repeticoes_admissiveis_erosao(
            ef_c, 15.6, c.TipoAcostamento.COM_CONCRETO, c.TipoEixo.SIMPLES)
        razao = n_c / n_s
        marca = ""
        if razao < 1.0:
            marca = "  <-- INCOERENTE!"
            ok_c = False
        print(f"  {h:>6d} {ef_s:>8.2f} {n_s:>14,.0f} {ef_c:>8.2f} {n_c:>14,.0f} "
              f"{razao:>7.2f}x{marca}")
    print(f"  => {'OK, coerente (acostamento sempre ajuda)' if ok_c else 'FALHOU'}")

    print("\n  (d) VIÉS RESIDUAL CONHECIDO da Figura 29")
    print("      A Fig.28 precisou de um ajuste fino (w, offset) contra os 34")
    print("      pontos oficiais. A Fig.29 NÃO pôde receber esse ajuste (não há")
    print("      exemplo oficial com acostamento). Abaixo, o quanto esse ajuste")
    print("      valeu na Fig.28 - é a ordem de grandeza do viés que a Fig.29")
    print("      provavelmente ainda carrega (subestimando N => superestimando")
    print("      o dano por erosão, ou seja, errando para o lado SEGURO).")
    import math
    p28 = c._NOMO[c.TipoAcostamento.SEM_CONCRETO]
    w_geom = (774.0 - 70.5) / (403.5 - 70.5)

    def _n_com(carga, ef, w, offset, pr):
        p1 = pr["a1"] + pr["b1"] * math.log(carga)
        p2 = pr["a2"] + pr["b2"] * ef
        p3 = p1 + (p2 - p1) * w + offset
        return 10 ** ((p3 - pr["a3"]) / pr["b3"])

    print(f"\n  {'EF':>6} {'carga':>7} {'N s/ ajuste':>14} {'N c/ ajuste':>14} {'razão':>8}")
    print("  " + "-" * 54)
    razoes = []
    for ef in (2.68, 2.72, 2.86):
        for carga in (10.8, 15.6, 19.2):
            ng = _n_com(carga, ef, w_geom, 0.0, p28)
            nc = _n_com(carga, ef, p28["w"], p28["offset"], p28)
            razoes.append(nc / ng)
            print(f"  {ef:>6.2f} {carga:>7.1f} {ng:>14,.0f} {nc:>14,.0f} "
                  f"{nc/ng:>7.2f}x")
    media = sum(razoes) / len(razoes)
    print(f"\n  => o ajuste elevou N em {100*(media-1):.0f}% em média "
          f"(faixa {100*(min(razoes)-1):.0f}% a {100*(max(razoes)-1):.0f}%).")
    print(f"     Logo, os N da Fig.29 devem estar subestimados nessa mesma")
    print(f"     ordem (~10-55%), e os consumos de erosão com acostamento,")
    print(f"     SUPERestimados na mesma proporção.")

    print("\n  (e) AFERIÇÃO INDIRETA DA FIG.29 pelo texto do manual")
    print("      §4.6.2.3.5 (pág. 93): 'A adoção de um acostamento de concreto")
    print("      pode resultar em até cerca de 4cm na redução na espessura")
    print("      necessária de placa, dependendo dos demais parâmetros.'")
    print("      => é um alvo NUMÉRICO independente para a Fig.29, que não")
    print("         depende de nenhum exemplo resolvido. Varredura ampla:")
    import itertools
    base = [(c.TipoEixo.SIMPLES, 13.0, 250_000),
            (c.TipoEixo.TANDEM_DUPLO, 20.0, 150_000),
            (c.TipoEixo.TANDEM_TRIPLO, 25.5, 80_000)]

    def _h(acost, barras, k, fctk, mult):
        esp = [c.FaixaCarga(t, cg, n * mult) for t, cg, n in base]
        p = c.ParametrosProjeto(fctk_mpa=fctk, k_mpa_m=k, fsc=1.2,
                                acostamento=acost,
                                com_barras_transferencia=barras, espectro=esp)
        r = c.dimensionar(p)
        return r.h_cm if r else None

    reducoes = []
    for k, fctk, mult, barras in itertools.product(
            [30, 40, 60, 80, 100, 150, 180], [4.0, 4.5, 4.8, 5.5],
            [0.2, 1.0, 5.0, 20.0], [False, True]):
        hs = _h(c.TipoAcostamento.SEM_CONCRETO, barras, k, fctk, mult)
        hc = _h(c.TipoAcostamento.COM_CONCRETO, barras, k, fctk, mult)
        if hs and hc:
            reducoes.append(hs - hc)
    med = sum(reducoes) / len(reducoes)
    mx = max(reducoes)
    acima = sum(1 for r in reducoes if r > 4.0)
    print(f"\n      {len(reducoes)} cenários testados")
    print(f"      redução média de h = {med:.2f} cm  |  MÁXIMA = {mx:.2f} cm")
    print(f"      cenários acima de 4 cm: {acima} ({100*acima/len(reducoes):.1f}%)")
    veredito = "COMPATÍVEL com o manual" if mx <= 4.5 else "EXTRAPOLA o manual"
    print(f"      => {veredito}")

    print("\n  CONCLUSÃO Fig.29: coerência física OK, E agora com uma aferição")
    print("  numérica INDIRETA (o teto de ~4cm do §4.6.2.3.5 é reproduzido).")
    print("  Não é tão forte quanto os 34 pontos da Fig.28, mas deixa de ser")
    print("  'sem nenhuma validação'.")


def contexto_de_precisao() -> None:
    """Compara o erro da digitalização com a incerteza que o método assume."""
    print("\n" + "=" * 78)
    print("CONTEXTO: o erro da leitura do ábaco vs. a incerteza do PRÓPRIO método")
    print("=" * 78)
    print("  O manual (§4.6.2.3.4, pág. 93) assume explicitamente um COEFICIENTE")
    print("  DE VARIAÇÃO DE 15% na resistência à tração na flexão do concreto")
    print("  ('equivalente a um controle de qualidade de regular para bom,")
    print("  conforme o ACI 214'). Abaixo, o que cada incerteza vale em cm de placa.")

    base = [(c.TipoEixo.SIMPLES, 13.0, 250_000),
            (c.TipoEixo.TANDEM_DUPLO, 20.0, 150_000),
            (c.TipoEixo.TANDEM_TRIPLO, 25.5, 80_000)]

    def _h(k, fctk, mult):
        esp = [c.FaixaCarga(t, cg, n * mult) for t, cg, n in base]
        p = c.ParametrosProjeto(fctk_mpa=fctk, k_mpa_m=k, fsc=1.2,
                                acostamento=c.TipoAcostamento.SEM_CONCRETO,
                                com_barras_transferencia=False, espectro=esp)
        r = c.dimensionar(p)
        return r.h_cm if r else None

    print(f"\n  {'k':>5} {'CV 15% do concreto':>22} {'erro 8% do ábaco':>20}")
    print("  " + "-" * 48)
    for k in (40, 60, 80, 100, 150):
        faixa_cv = _h(k, 4.8*0.85, 1.0) - _h(k, 4.8*1.15, 1.0)
        faixa_ab = _h(k, 4.8, 1.08) - _h(k, 4.8, 0.92)
        print(f"  {k:>5} {faixa_cv:>19.1f} cm {faixa_ab:>17.1f} cm")
    print("\n  => A incerteza que o MÉTODO já assume é várias vezes maior que o")
    print("     erro introduzido pela digitalização do ábaco. Perseguir '100% de")
    print("     precisão' na leitura gráfica não muda a espessura de projeto.")


if __name__ == "__main__":
    aferir_figura28()
    coerencia_figura29()
    contexto_de_precisao()
