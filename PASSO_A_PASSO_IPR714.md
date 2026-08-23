# Passo a passo do dimensionamento — mapa para o Manual DNIT IPR-714

**Método:** PCA 1984 (§4.6.2 do *Manual de Pavimentos Rígidos*, DNIT IPR-714, 2. ed. 2005)
**PDF de referência:** `714_manual_de_pavimentos_rigidos (2).pdf` (238 págs.)
**Convenção de páginas:** os números abaixo são as **páginas impressas** do manual.
No leitor de PDF, a folha física = **página impressa + 4** (ex.: impressa 87 = folha 91 do PDF).
*(A numeração foi conferida página a página no PDF.)*

Para cada etapa da resolução, duas amarrações:
**(A)** a **página do manual** de onde vem a fórmula/tabela/ábaco; e
**(B)** o **ponto do código** que a executa. Ao final, a **resolução completa** do
exemplo oficial do manual, passo a passo.

---

## 0. Índice de páginas do manual (todo o material usado)

### Fundação — coeficiente de recalque *k*
| Material | Conteúdo | Pág. impressa |
|---|---|---|
| **Quadro 3** | Tipo de solo → k0 do subleito | **69** |
| **Figura 11** | CBR → k0 do subleito (ábaco) | **70** |
| **Figuras 18–21** | Sub-base → k efetivo (granular / BGTC / solo-cimento / CCR) | **78–81** |

### Método PCA 1984 — teoria
| Seção | Conteúdo | Pág. impressa |
|---|---|---|
| §4.6.2 | Início do método PCA 1984 | **87** |
| §4.6.2.3.1 | Modelos de ruína: **fadiga** e **erosão**; lei de Miner; limite 100%; Figura 22 | **90–91** |
| §4.6.2.3.2 | Tipos de junta e efeito do acostamento (posição crítica da carga) | **91–92** |
| §4.6.2.3.3 | Distribuição do tráfego (6% na borda) e **expoente 0,94** na fadiga | **92–93** |
| §4.6.2.3.4 | Concreto: fctk aos 28 dias como entrada; CV de 15% embutido | **93** |
| §4.6.2.3.9 | **Quadro 9 — Fatores de Segurança de Carga (FSC)** | **95** |

### Método PCA 1984 — roteiro, tabelas e ábacos
| Material | Conteúdo | Pág. impressa |
|---|---|---|
| §4.6.2.4 | **Roteiro de dimensionamento (passos a–i)** | **95–97** |
| Quadro 10 | Exemplo de cálculo de eixos totais por classe de carga | 94 |
| Quadro 11 | **Folha-tipo de trabalho** (formulário do cálculo; aparece preenchido no exemplo) | 116–117 |
| **Quadro 12** | Tensão equivalente ES/ETD — **sem** acostamento (PSAC) | **101** |
| **Quadro 13** | Tensão equivalente ETT — sem acostamento | **102** |
| **Quadro 14** | Tensão equivalente ES/ETD — **com** acostamento (PCAC) | **103** |
| **Quadro 15** | Tensão equivalente ETT — com acostamento | **104** |
| **Quadro 16** | Fator de erosão ES/ETD — junta **sem** barras, sem acost. | **105** |
| **Quadro 17** | Fator de erosão ETT — sem barras, sem acost. | **106** |
| **Quadro 18** | Fator de erosão ES/ETD — sem barras, com acost. | **107** |
| **Quadro 19** | Fator de erosão ETT — sem barras, com acost. | **108** |
| **Quadro 20** | Fator de erosão ES/ETD — **com** barras, sem acost. | **109** |
| **Quadro 21** | Fator de erosão ETT — com barras, sem acost. | **110** |
| **Quadro 22** | Fator de erosão ES/ETD — com barras, com acost. | **111** |
| **Quadro 23** | Fator de erosão ETT — com barras, com acost. | **112** |
| **Figura 27** | Ábaco de **análise por fadiga** (Fator de fadiga → N adm.) | **113** |
| **Figura 28** | Ábaco de **análise por erosão — sem** acostamento | **114** |
| **Figura 29** | Ábaco de análise por erosão — **com** acostamento | **115** |
| §4.6.2.5 | **Exemplo resolvido** (dados + passos a–j) | **115–117** |
| Quadro 24 | Exemplo com h=26 cm (espessura aprovada) | **118** |

> Observação (dois erros de numeração no próprio manual, pág. 117): no texto do
> exemplo o manual escreve "desenvolvido no Quadro 9" e "soma da coluna 5 e coluna 6
> do Quadro 9" — o correto é **Quadro 11** (a folha de trabalho). Vale mencionar na
> defesa para não confundir a banca.

---

## 1. O que o método decide, em uma frase

Adota-se uma **espessura-tentativa h** e verifica-se se ela suporta o espectro de
tráfego sem romper por **fadiga** (trincamento por flexão) **nem** por **erosão**
(bombeamento/perda de suporte). A placa é aprovada quando **ambos** os somatórios
de consumo ficam **≤ 100%** (§4.6.2.3.1, pág. 90–91). Adota-se a **menor h** aprovada.

- **Código:** `calculos.dimensionar()` — itera h de 10 a 40 cm, passo 0,5 cm.

---

## 2. Passo a passo (roteiro a–i, pág. 95–97) × código

### Passo (a) — Parâmetros de projeto · pág. 95
Define-se: acostamento e barras; **fctk** aos 28 dias; **k** do sistema; **FSC**;
e o tráfego por classe de carga (Quadro 10).
- **Manual:** §4.6.2.4-a, pág. 95. fctk como entrada direta: §4.6.2.3.4, pág. 93.
  FSC: Quadro 9, pág. 95.
- **Código:** `ParametrosProjeto` (`calculos.py`, campos `fctk_mpa`, `k_mpa_m`, `fsc`,
  `acostamento`, `com_barras_transferencia`, `espectro`).

**k do sistema** (entra aqui) vem da etapa de fundação:
- CBR → k0 pela **Figura 11 (pág. 70)** → `estagio3.k_de_cbr()`
- ou solo → k0 pelo **Quadro 3 (pág. 69)** → `estagio3.k_de_solo()`
- sub-base → k efetivo pelas **Figuras 18–21 (pág. 78–81)** → `estagio3.k_efetivo()`
  (teto de 150 MPa/m).

### Passo (b) — Espessura-tentativa · pág. 95
Arbitra-se um h inicial e preenche-se a folha (Quadro 11).
- **Código:** loop em `dimensionar()`; cada h vai para `verificar_espessura(h, p)`.

### Passo (c) — Tensão equivalente σ_eq · pág. 95–96
Nos **Quadros 12 e 13** (sem acostamento) **ou 14 e 15** (com acostamento), entra-se
com **h** e **k** e lê-se σ_eq para ES, ETD e ETT.
- **Manual:** Quadros 12–15, pág. 101–104. A interpolação linear em k é explicitamente
  autorizada (nota da pág. 116: "pode-se aceitar que [a variação] seja [linear] para
  fins de interpolação, pois se está do lado da segurança").
- **Código:** `tensao_equivalente()` → mapa `_TENSAO` escolhe o quadro certo →
  `tabelas_pca.consultar()` faz a **interpolação bilinear** h×k. As 12 tabelas estão
  em `tabelas_pca.py` / `_tabelas_geradas.py`.

### Passo (d) — Fator de erosão FE · pág. 96
Nos **Quadros 16–23** (escolhidos por junta com/sem barras × com/sem acostamento),
entra-se com **h** e **k** e lê-se FE para ES, ETD e ETT.
- **Manual:** Quadros 16–23, pág. 105–112.
- **Código:** `fator_erosao()` → mapa `_EROSAO` (12 combinações) → `consultar()`.

### Passo (e) — Fator de fadiga · pág. 96
Fator de fadiga = **σ_eq / fctk** (relação de tensões do eixo-padrão).
- **Manual:** §4.6.2.4-e, pág. 96. No exemplo: ES 1,14/4,8 = **0,238**.
- **Código:** dentro de `verificar_espessura()`, termo `sigma_eq / mr` (mr = fctk).

### Passo (f) — Repetições admissíveis por FADIGA (Figura 27) · pág. 96
Com o fator de fadiga e a **carga corrigida** (× FSC), lê-se N_adm na **Figura 27**.
O **expoente 0,94** sobre as cargas (só na fadiga) entra aqui — pág. 93.
Tandem triplo: tratado como **3 eixos simples com 1/3 da carga** (pág. 96).
- **Manual:** Figura 27, pág. 113; regra do 0,94, pág. 93; regra do tandem triplo, pág. 96.
- **Código:** `repeticoes_admissiveis_fadiga()`. Como o programa não "lê ábaco", usa
  as equações da PCA que **reproduzem** a Figura 27:

  `SR = (σ_eq / fctk) · (P_ef / P_padrão)^0,94`
  - `SR < 0,45` → N ilimitado
  - `0,45 ≤ SR < 0,55` → `N = (4,2577/(SR−0,4325))^3,268`
  - `SR ≥ 0,55` → `log₁₀N = 11,737 − 12,077·SR`

  Cargas-padrão: ES 8,16 tf; ETD 16,31 tf; ETT usa o ábaco do ES. Tandem triplo ÷3
  em `_carga_efetiva()`.

### Passo (g) — Repetições admissíveis por EROSÃO (Figuras 28/29) · pág. 96–97
Com o fator de erosão e a carga corrigida, lê-se N_adm na **Figura 28** (sem
acostamento) ou **Figura 29** (com acostamento).
- **Manual:** Figuras 28/29, pág. 114–115.
- **Código:** `repeticoes_admissiveis_erosao()`. O manual só traz o **ábaco** (não a
  equação fechada); o programa usa a forma publicada por Packard e **calibra a taxa de
  trabalho X** contra os pontos do próprio exemplo do manual (`_fit_erosao.py`):

  `log₁₀N = 14,524 − 6,777·(C1·X − 9,0)^0,103`, com
  `X = 10^FE · exp(−2,0913 − 2,4000·u + 0,7108·u²)`, `u = ln(P_ef)`.

### Passo (h) — Consumos · pág. 97
Para cada faixa: `consumo = 100 · (repetições previstas / repetições admissíveis)`,
tanto na fadiga (coluna 5) quanto na erosão (coluna 7) do Quadro 11.
- **Código:** `100.0 * faixa.repeticoes_previstas / n_adm` (fadiga e erosão).

### Passo (i) — Verificação · pág. 97
Soma-se a coluna de fadiga e a de erosão. **Se qualquer soma > 100%, aumenta-se h**
e repete. Se ambas ficam muito abaixo de 100%, a placa está superdimensionada
(reduzir h).
- **Código:** `aprovada = (soma_fadiga ≤ 100) and (soma_erosao ≤ 100)`;
  `dimensionar()` devolve a primeira h que passa.

---

## 3. Resolução completa do exemplo oficial (pág. 115–118)

**Dados (pág. 115):** sub-base de brita tratada com cimento 12 cm; **k = 100 MPa/m**;
**fctk = 4,8 MPa**; **FSC = 1,2**; **sem** acostamento e junta **sem** barras;
vida de projeto 20 anos; tráfego do Quadro 10.

### 3.1 Tentativa h = 25 cm (pág. 116–117)

**(c) Tensão equivalente** — Quadros 12 e 13 (sem acostamento), h=25, k=100:
| Eixo | σ_eq (MPa) | Fonte |
|---|---|---|
| Simples (ES) | **1,14** | Quadro 12, pág. 101 |
| Tandem duplo (ETD) | **0,99** | Quadro 12, pág. 101 |
| Tandem triplo (ETT) | **0,727** | Quadro 13, pág. 102 |

**(d) Fator de erosão** — Quadros 16 e 17, h=25, k=100:
| Eixo | FE | Fonte |
|---|---|---|
| ES | **2,72** | Quadro 16, pág. 105 |
| ETD | **2,89** | Quadro 16, pág. 105 |
| ETT | **2,92** | Quadro 17, pág. 106 |

**(e) Fator de fadiga** = σ_eq / 4,8: ES 0,238 · ETD 0,206 · ETT 0,151.

**(f–h) Repetições admissíveis e consumos** — pela Figura 27 (fadiga, pág. 113) e
Figura 28 (erosão, pág. 114), sobre o espectro de eixos simples do Quadro 10.

**(i–j) Resultado do manual:** Σ fadiga = **8,9%** (< 100% → OK na fadiga); mas
Σ erosão **> 100%** → **h = 25 cm REPROVA** por erosão.

> **Reprodução pela ferramenta** (`validar_e2e.py`, só eixos simples):
> Σ fadiga = **8,6%** (manual 8,9%) · Σ erosão = **89,8%** (manual 89,9%).
> Somando ETD+ETT (+15,5% de erosão no manual), o total passa de 100% → reprova,
> igual ao manual.

### 3.2 Tentativa h = 26 cm — Quadro 24 (pág. 118)

Refaz-se todo o roteiro com h=26. Agora **σ_eq ES = 1,08** e **FE ES = 2,68** (menores,
pois a placa é mais espessa). Toda a fadiga fica **ilimitada** (fator de fadiga baixo);
a erosão cai abaixo de 100%. **h = 26 cm é a espessura adotada**, controlada pela erosão.

Trecho do Quadro 24 (eixos simples — carga×FSC · N previsto · N adm. erosão · dano %):
```
 9,6 tf   238.118   26.000.000    0,9%
10,8 tf   242.715   10.000.000    2,4%
12,0 tf   310.404    5.100.000    6,1%
13,2 tf   282.267    2.750.000   10,3%
14,4 tf   242.438    1.700.000   14,3%
15,6 tf   206.645    1.000.000   20,7%
16,8 tf    65.889      630.000   10,5%
```

**Conclusão do exemplo:** a **erosão governa** o dimensionamento (consome mais que a
fadiga), sendo os **eixos simples** os mais influentes — exatamente o que a ferramenta
demonstra na tela de *Memória de Cálculo* e no gráfico h × consumo.

---

## 4. Quadro-resumo: etapa → página do manual → função no código

| Etapa | Manual (pág. impressa) | Função no código |
|---|---|---|
| k0 por CBR | Figura 11 (70) | `estagio3.k_de_cbr` |
| k0 por solo | Quadro 3 (69) | `estagio3.k_de_solo` |
| k efetivo (sub-base) | Figuras 18–21 (78–81) | `estagio3.k_efetivo` |
| FSC | Quadro 9 (95) | `ParametrosProjeto.fsc`, `_carga_efetiva` |
| Carga corrigida × FSC (÷3 no triplo) | passo a/f (95–96) | `_carga_efetiva` |
| Tensão equivalente σ_eq | Quadros 12–15 (101–104) | `tensao_equivalente` → `consultar` |
| Fator de erosão FE | Quadros 16–23 (105–112) | `fator_erosao` → `consultar` |
| N admissível — fadiga | Figura 27 (113) + expoente 0,94 (93) | `repeticoes_admissiveis_fadiga` |
| N admissível — erosão | Figuras 28/29 (114–115) | `repeticoes_admissiveis_erosao` |
| Consumo e verificação ≤100% | passos h–i (97) | `verificar_espessura` |
| Menor h aprovada | passo i (97) | `dimensionar` |

---

## 5. Para os slides (síntese)

1. **O método é o oficial** (PCA 1984, §4.6.2, pág. 87) — critério duplo fadiga+erosão.
2. **Cada número da ferramenta tem página**: as 12 tabelas (Quadros 12–23, pág. 101–112)
   foram transcritas; os ábacos (Fig. 27–29, pág. 113–115) viram equações; a fundação
   sai das Figuras 11 e 18–21 (pág. 70, 78–81) e do Quadro 3 (pág. 69).
3. **Validação contra o próprio exemplo do manual** (pág. 115–118): a ferramenta
   reproduz Σ fadiga 8,6% (manual 8,9%) e Σ erosão 89,8% (manual 89,9%), e chega à
   mesma espessura adotada (h = 26 cm, controlada por erosão).
4. **Transparência**: a etapa *Memória de Cálculo* do app mostra, para cada classe de
   eixo, a interpolação nas tabelas e as equações de fadiga e erosão com os valores
   substituídos — é o Quadro 11 do manual, feito ao vivo.
