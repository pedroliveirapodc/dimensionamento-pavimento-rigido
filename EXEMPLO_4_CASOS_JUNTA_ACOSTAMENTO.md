# Exemplo de aplicação — os 4 casos de junta × acostamento

**Finalidade:** complemento ao [`EXEMPLO_RESOLVIDO_MANUAL_VS_SOFTWARE.md`](EXEMPLO_RESOLVIDO_MANUAL_VS_SOFTWARE.md)
(que resolve o exemplo oficial do manual, caso 1 abaixo). Aqui o mesmo roteiro passo a
passo do Manual de Pavimentos Rígidos do DNIT (IPR-714, §4.6.2.4, pág. 95–97) é aplicado
às **quatro combinações possíveis** de junta (com/sem barra de transferência) e
acostamento (com/sem acostamento de concreto) — a escolha de projeto que define, em cada
etapa do roteiro, **qual par de Quadros consultar**.

Mantém-se fixo o resto do projeto (mesma fundação, mesmo concreto, mesma espessura-tentativa)
para que os quatro casos sejam diretamente comparáveis entre si — só a condição de borda
da placa muda.

---

## 0. Por que a junta e o acostamento mudam a tabela a consultar

O manual trata separadamente **8 combinações de tabela** (Quadros 12–23) porque tanto a
junta quanto o acostamento mudam a distribuição de tensões e o suporte lateral da placa:

| | **Tensão equivalente** (passo c) | **Fator de erosão** (passo d) |
|---|---|---|
| depende de | h, k, acostamento | h, k, acostamento, **junta (barras)** |
| não depende de | junta (barras) | — |

Ou seja: a tensão equivalente só tem **2 variantes** (Quadros 12/13 sem acostamento;
14/15 com acostamento) — a presença de barras de transferência não altera a tensão de
flexão calculada. Já o fator de erosão tem as **4 variantes**, porque as barras mudam
diretamente a transferência de carga entre placas e, com isso, o bombeamento na junta:

| Caso | Junta | Acostamento | Quadro tensão (c) | Quadro erosão (d) |
|---|---|---|---|---|
| **1** | sem barras (JSP) | sem concreto (PSAC) | 12 / 13 (pág. 101–102) | 16 / 17 (pág. 105–106) |
| **2** | sem barras (JSP) | com concreto (PCAC) | 14 / 15 (pág. 103–104) | 18 / 19 (pág. 107–108) |
| **3** | com barras (JCP) | sem concreto (PSAC) | 12 / 13 (pág. 101–102) | **20 / 21** (pág. 109–110) |
| **4** | com barras (JCP) | com concreto (PCAC) | 14 / 15 (pág. 103–104) | 22 / 23 (pág. 111–112) |

> **Nota (achado da auditoria de 23/08/2026):** os títulos IMPRESSOS dos Quadros 20 e 21
> no manual estão errados — dizem "JSP e PCAC", o que contradiz o próprio parêntese
> explicativo do título ("pavimento SEM acostamento") e duplica o título dos Quadros
> 18/19. Pelo padrão da sequência (16/17→18/19→**20/21**→22/23) e pela conferência dos
> valores tabelados (diferentes dos de 18/19), o nome correto é **JCP-PSAC** — como usado
> nesta tabela e como o código já rotula. Vale citar como errata do manual no TCC.

---

## 1. Dados fixos do exemplo

| Parâmetro | Valor |
|---|---|
| fctk (28 dias) | 4,8 MPa |
| k do sistema | 100 MPa/m |
| FSC | 1,2 |
| Espessura-tentativa | h = 25 cm |
| Vida de projeto | 20 anos |

Três faixas de carga representativas (uma por tipo de eixo), do espectro de tráfego:

| Eixo | Carga (tf) | N previsto (repetições no período) |
|---|---|---|
| Simples (ES) | 13,0 | 250.000 |
| Tandem duplo (ETD) | 20,0 (total) | 150.000 |
| Tandem triplo (ETT) | 25,5 (total; ábaco de ES com carga ÷3) | 80.000 |

Carga corrigida pelo FSC (passo a/f, carga × 1,2): ES → 15,6 tf · ETD → 24,0 tf ·
ETT → 10,2 tf/eixo (25,5 ÷ 3 × 1,2).

---

> **✏️ Atualizado em 23/08/2026 (tarde):** os números de erosão abaixo foram recalculados
> depois de **digitalizar diretamente as Figuras 28 e 29** do manual (nomograma de 3
> escalas, lido pixel a pixel a partir da imagem do PDF — ver seção 6). Isso substitui a
> versão anterior deste documento, que usava uma regressão com um limite (clamp) de
> segurança fora de uma faixa estreita de fator de erosão — e que, por causa disso, dava
> os Casos 2 e 4 com resultado **idêntico** (artefato do clamp, não da física). Com a
> digitalização, os 4 casos agora dão resultados **distintos e consistentes** — mas leia a
> seção 6: só a Figura 28 (Casos 1 e 3, sem acostamento) tem um exemplo oficial do manual
> pra conferir; a Figura 29 (Casos 2 e 4, com acostamento) foi digitalizada pelo mesmo
> método mas **ainda sem essa conferência numérica independente**.

## 2. Caso 1 — sem barras, sem acostamento (JSP/PSAC)

*(idêntico ao exemplo oficial do manual — reproduzido aqui só para comparação lado a lado
com os outros 3 casos; resolução completa no documento complementar.)*

**(c) Tensão equivalente** (Quadros 12/13, h=25, k=100): ES = 1,140 MPa · ETD = 0,990 MPa ·
ETT = 0,727 MPa.

**(d) Fator de erosão** (Quadros 16/17, h=25, k=100): ES = 2,72 · ETD = 2,89 · ETT = 2,92.

**(e) Fator de fadiga** = σ_eq/4,8: ES 0,238 · ETD 0,206 · ETT 0,151 → **SR** (após escalar
pela razão de carga ao expoente 0,94, pág. 93) fica bem abaixo de 0,45 nos três casos ⇒
**fadiga ilimitada** nas três faixas.

**(f)/(g) Repetições admissíveis por erosão** (leitura da Figura 28, sem acostamento):
ES ≈ 8,26×10⁵ · ETD ≈ 1,24×10⁶ · ETT ≈ 2,71×10⁶.

**(h) Consumo de erosão:** ES = 100×250.000/826.000 ≈ **30,3 %** · ETD ≈ **12,1 %** ·
ETT ≈ **3,0 %**.

**Σ erosão (3 faixas) ≈ 45,3 %** · Σ fadiga = 0,0 % → **aprovado em h=25 para este
subconjunto de 3 faixas** (o exemplo oficial do manual usa o espectro completo de 28
faixas e reprova em h=25 — ver documento complementar). ✅ Este caso é o próprio exemplo
oficial do manual — os números de σ_eq e FE batem exatamente; o N admissível lido do
ábaco tem ~8% de erro médio validado contra os 34 pontos do Quadro 11/24 (ver seção 6).

---

## 3. Caso 2 — sem barras, com acostamento (JSP/PCAC)

O acostamento de concreto dá suporte lateral à placa: a carga na borda passa a se
comportar mais como carga interior, **reduzindo tanto a tensão quanto a erosão**.

**(c) Tensão equivalente** (Quadros 14/15, h=25, k=100): ES = **0,960** MPa · ETD =
**0,820** MPa · ETT = **0,637** MPa — cerca de 15–18 % menores que no Caso 1, só por
trocar de tabela (Quadro 12→14).

**(d) Fator de erosão** (Quadros 18/19, h=25, k=100): ES = **2,31** · ETD = **2,42** ·
ETT = **2,437** — bem menores que os 2,72/2,89/2,92 do Caso 1.

**(e) Fator de fadiga** = σ_eq/4,8: ES 0,200 · ETD 0,171 · ETT 0,133 → fadiga ilimitada
nas três faixas (ainda mais folgado que o Caso 1).

**(f)/(g) Repetições admissíveis por erosão** (leitura da **Figura 29**, com acostamento —
ábaco próprio, não Figura 28 escalada): ES ≈ 1,04×10⁶ · ETD ≈ 3,42×10⁶ · ETT ≈ 1,80×10⁷.

**(h) Consumo de erosão:** ES ≈ **24,0 %** · ETD ≈ **4,4 %** · ETT ≈ **0,4 %**.

**Σ erosão (3 faixas) ≈ 28,8 %** — cerca de 2/3 do Caso 1, pelo efeito do acostamento.

> **⚠️ Ressalva de confiabilidade:** a Figura 29 foi digitalizada pelo mesmo método
> rigoroso da Figura 28 (seção 6), mas o manual só publica um exemplo resolvido oficial
> **sem** acostamento — não há como conferir esses números ponto a ponto contra uma fonte
> independente. O comportamento qualitativo (reduz a erosão em relação ao Caso 1) está
> correto; o valor numérico exato ainda não tem a mesma confirmação do Caso 1.

---

## 4. Caso 3 — com barras, sem acostamento (JCP/PSAC)

A barra de transferência mecânica melhora a transferência de carga na junta sem depender
de um acostamento de concreto (a tensão de flexão, que não depende da junta, fica
**igual ao Caso 1**).

**(c) Tensão equivalente** (Quadros 12/13 — mesmos do Caso 1, pois barras não mudam a
tensão): ES = 1,140 MPa · ETD = 0,990 MPa · ETT = 0,727 MPa (idêntico ao Caso 1).

**(d) Fator de erosão** (Quadros **20/21**, h=25, k=100 — ver nota da errata na seção 0):
ES = **2,51** · ETD = **2,65** · ETT = **2,75** — menores que o Caso 1 (2,72/2,89/2,92).

**(e) Fator de fadiga:** idêntico ao Caso 1 (0,238/0,206/0,151) — fadiga ilimitada.

**(f)/(g) Repetições admissíveis por erosão** (Figura 28, sem acostamento — mesmo ábaco
validado do Caso 1, só muda o FE de entrada): ES ≈ 3,90×10⁶ · ETD ≈ 7,30×10⁶ ·
ETT ≈ 9,77×10⁶.

**(h) Consumo de erosão:** ES ≈ **6,4 %** · ETD ≈ **2,1 %** · ETT ≈ **0,8 %**.

**Σ erosão (3 faixas) ≈ 9,3 %** — bem abaixo do Caso 1 (45,3 %) e também abaixo do
Caso 2 (28,8 %). ✅ Este caso usa a Figura 28 (mesmo ábaco validado do Caso 1) — só a
combinação de tabelas (Quadros 20/21) muda; a confiabilidade numérica é a mesma do Caso 1.

> **Achado que muda a leitura anterior deste documento:** na versão anterior (regressão
> com clamp), a barra de transferência (Caso 3) parecia ajudar *menos* que o acostamento
> (Caso 2). Com a Figura 28 digitalizada e validada, o resultado se **inverte**: neste h/k,
> a **barra de transferência (Caso 3, 9,3%) reduz a erosão mais que o acostamento sozinho
> (Caso 2, 28,8%)**. Como o Caso 3 vem do ábaco validado (Figura 28) e o Caso 2 do ábaco
> ainda não conferido (Figura 29), essa comparação pesa a favor do resultado do Caso 3.

---

## 5. Caso 4 — com barras, com acostamento (JCP/PCAC)

A combinação mais favorável à erosão: suporte lateral do acostamento **e** transferência
mecânica nas juntas transversais.

**(c) Tensão equivalente** (Quadros 14/15 — mesmos do Caso 2, pois barras não mudam a
tensão): ES = 0,960 MPa · ETD = 0,820 MPa · ETT = 0,637 MPa (idêntico ao Caso 2).

**(d) Fator de erosão** (Quadros 22/23, h=25, k=100): ES = **2,08** · ETD = **2,17** ·
ETT = **2,237** — os menores dos quatro casos, como esperado (efeito do acostamento e da
barra somados).

**(f)/(g) Repetições admissíveis por erosão** (Figura 29, com acostamento): ES ≈ 2,06×10⁷ ·
ETD e ETT ficam **ilimitados** (a reta do nomograma sai acima do topo impresso da escala,
10⁸ — erosão desprezível nessas faixas).

**(h) Consumo de erosão:** ES ≈ **1,2 %** · ETD ≈ **0,0 %** · ETT ≈ **0,0 %**.

**Σ erosão (3 faixas) ≈ 1,2 %** — de longe o melhor cenário, e agora **distinto** do
Caso 2 (diferente da versão anterior deste documento, em que os dois saturavam no mesmo
valor por causa do clamp). Mesma ressalva do Caso 2: vem da Figura 29, ainda sem exemplo
oficial pra conferir numericamente.

---

## 6. Quadro-resumo comparativo (h=25 cm, k=100 MPa/m, mesmas 3 faixas)

| Caso | Junta | Acostamento | Σ tensão ES (MPa) | Σ FE ES | **Σ erosão (3 faixas)** | Confiabilidade |
|---|---|---|---|---|---|---|
| 1 | sem barras | sem concreto | 1,140 | 2,72 | **45,3 %** | ✅ Validada (exemplo oficial, Fig.28) |
| 2 | sem barras | com concreto | 0,960 | 2,31 | **28,8 %** | ⚠️ Fig.29 digitalizada, não conferida |
| 3 | com barras | sem concreto | 1,140 | 2,51 | **9,3 %** | ✅ Fig.28 (mesmo ábaco validado do Caso 1) |
| 4 | com barras | com concreto | 0,960 | 2,08 | **1,2 %** | ⚠️ Fig.29 digitalizada, não conferida |

**Leitura de engenharia:** sem barras/sem acostamento é o pior cenário e os dois reforços
juntos (Caso 4) são o melhor, como manda o manual (§4.6.2.3.2, pág. 91–92). A ordem
relativa de "qual reforço isolado ajuda mais" (barra vs. acostamento) agora tem um lado
validado numericamente (Caso 3, via Figura 28) apontando que a barra de transferência é o
reforço isolado mais eficaz nesta condição de h/k — mas a comparação direta com o Caso 2
carrega a ressalva de que a Figura 29 ainda não foi conferida contra um exemplo oficial.

---

## 7. Como as Figuras 28 e 29 foram digitalizadas (resumo técnico)

As Figuras 28 (sem acostamento, pág. 114) e 29 (com acostamento, pág. 115) são
**nomogramas de 3 escalas paralelas**: carga por eixo | fator de erosão | número
admissível de repetições. Usar o ábaco à mão é traçar uma reta entre o ponto da carga e o
ponto do fator de erosão e ler N onde essa reta cruza a terceira escala.

Processo (23/08/2026):
1. Extração da imagem raster embutida em cada página do PDF (mesma técnica já usada para
   as Figuras 11 e 18–21 da fundação, mas aqui processando os pixels diretamente em vez de
   leitura visual).
2. Detecção automática da posição (em pixels) de cada traço de escala e calibração
   contra os próprios números impressos: a escala de carga é logarítmica, a de fator de
   erosão é linear, a de N é aproximadamente log (com uma pequena correção quadrática na
   Figura 29, cuja escala de N não é perfeitamente log-linear).
3. Reconstrução da leitura geométrica (reta por 3 pontos em escalas paralelas) e um
   pequeno ajuste fino contra os **34 pontos oficiais do Quadro 11/24** do manual — a
   única fonte de verdade disponível, e que só cobre a Figura 28.

**Resultado:** Figura 28 — erro médio 8,0% / máximo 20,9% sobre os 34 pontos oficiais
(ordem de grandeza esperada para um método gráfico: um humano lendo o mesmo nomograma à
mão também erra nessa faixa). Válida em toda a extensão impressa do ábaco (fator de erosão
de 2,0 a 4,0), sem precisar de limite de segurança. Figura 29 — mesmo método, mas sem
exemplo oficial para conferir; tratar como estimativa razoável até surgir uma segunda
fonte de validação.

**Isso substitui o C₁ = 0,90 provisório** usado antes para "converter" a Figura 28 em uma
aproximação da com-acostamento — na verdade a Figura 29 é um ábaco próprio, não uma
versão escalada da Figura 28 (a prova: sua escala de fator de erosão vai de 1,6 a 3,6, não
de 2,0 a 4,0 como a Figura 28).

**Próximo passo, se quiser fechar 100% a precisão:** conseguir um SEGUNDO exemplo oficial
resolvido com acostamento de concreto (de outro manual/norma equivalente, ou de uma
apostila de curso) para validar a Figura 29 numericamente do mesmo jeito que o Quadro
11/24 validou a Figura 28.
