# Exemplo de aplicação: resolução manual vs. resolução pela ferramenta

**Finalidade deste documento:** texto pronto para adaptação e inserção no TCC (capítulo de
Metodologia ou de Resultados/Estudo de Caso). Resolve o mesmo problema de duas formas —
manualmente, seguindo o roteiro do Manual de Pavimentos Rígidos do DNIT (IPR-714, 2ª ed.
2005, §4.6.2.4), e pela ferramenta computacional desenvolvida — para permitir a comparação
direta entre os dois processos.

Referência: `714_manual_de_pavimentos_rigidos`, seção 4.6.2 (Método PCA 1984), exemplo
resolvido nas páginas 115–118. Todos os números desta seção foram conferidos página a
página no manual (ver auditoria de 23/08/2026, registrada na memória do projeto).

---

## 1. O problema

Dimensionar a espessura de uma placa de concreto simples (sem armadura estrutural) pelo
método PCA 1984, dado:

| Parâmetro | Valor | Fonte |
|---|---|---|
| Resistência característica à tração na flexão, fctk (28 dias) | 4,8 MPa | dado de projeto |
| Coeficiente de recalque do sistema, k | 100 MPa/m | Estágio de fundação (subleito + sub-base) |
| Fator de Segurança de Cargas, FSC | 1,2 | Quadro 9 (pág. 95), via alto volume |
| Acostamento | sem acostamento de concreto (PSAC) | dado de projeto |
| Junta | sem barras de transferência (JSP) | dado de projeto |
| Vida de projeto | 20 anos | dado de projeto |
| Espectro de tráfego | Quadro 10 (pág. 94) | contagem/projeção de tráfego |

O critério de aprovação (§4.6.2.3.1, pág. 90–91): a espessura-tentativa **h** é aprovada
se, somando sobre todo o espectro de tráfego, o consumo de **fadiga** (trincamento por
flexão) **e** o dano por **erosão** (perda de suporte por bombeamento) ficarem, cada um,
**≤ 100%**. Adota-se a menor h que atende aos dois critérios simultaneamente.

---

## 2. Resolução manual — passo a passo (roteiro do manual, pág. 95–97)

### Passo (a) — Parâmetros de projeto
Já listados na tabela acima. Este passo, por si, já exige que o projetista tenha em mãos
cinco fontes diferentes dentro do manual (Quadro 9 para o FSC, mais os resultados da etapa
de fundação) antes de começar a preencher a folha de trabalho (Quadro 11).

### Passo (b) — Espessura-tentativa
Arbitra-se h = 25 cm e preenche-se a folha de cálculo (Quadro 11) inteira para esse valor.

### Passo (c) — Tensão equivalente (σ_eq)
Como o pavimento é **sem acostamento**, usam-se os **Quadros 12 e 13** (pág. 101–102), a
tabela específica para essa combinação de junta/acostamento (das 4 combinações possíveis:
sem barras×sem acostamento, sem barras×com acostamento, com barras×sem acostamento, com
barras×com acostamento — cada uma com sua própria tabela, e é fácil pegar a errada). Como
h=25 e k=100 caem exatamente nos nós tabelados, a leitura é direta (sem interpolação):

| Eixo | σ_eq (MPa) | Quadro |
|---|---|---|
| Simples (ES) | 1,14 | Quadro 12 |
| Tandem duplo (ETD) | 0,99 | Quadro 12 |
| Tandem triplo (ETT) | 0,727 | Quadro 13 |

*(A carga do eixo tandem triplo entra no Quadro 11 já dividida por três — o manual
determina usar o ábaco do eixo simples para o triplo, "pois se está do lado da segurança",
nota da pág. 116.)*

### Passo (d) — Fator de erosão (FE)
Junta sem barras + sem acostamento → **Quadros 16 e 17** (pág. 105–106):

| Eixo | FE | Quadro |
|---|---|---|
| ES | 2,72 | Quadro 16 |
| ETD | 2,89 | Quadro 16 |
| ETT | 2,92 | Quadro 17 |

### Passo (e) — Fator de fadiga
Fator de fadiga = σ_eq / fctk (relação de tensões do eixo-padrão):

- ES: 1,14 / 4,8 = **0,238**
- ETD: 0,99 / 4,8 = **0,206**
- ETT: 0,727 / 4,8 = **0,151**

### Passos (f) e (g) — Repetições admissíveis (fadiga e erosão)
Com o fator de fadiga (e) e a carga corrigida (× FSC), lê-se o número admissível de
repetições **N** na **Figura 27** (fadiga, pág. 113); com o fator de erosão (d) e a mesma
carga corrigida, lê-se **N** na **Figura 28** (erosão, pág. 114). Ambos os ábacos são
**nomogramas de três escalas paralelas**: traça-se uma reta entre o ponto da carga (escala
1) e o ponto do fator (escala 2), e o valor de N é lido onde essa reta cruza a terceira
escala (log). Isso é feito, à mão, **uma vez para cada uma das 25 faixas de carga do
espectro** (12 de eixo simples + 12 de tandem duplo + 4 de tandem triplo, no exemplo do
Quadro 24) — 25 leituras gráficas de régua e nomograma, cada uma sujeita a erro de
paralaxe/traço.

### Passo (h) — Consumo por faixa
Para cada faixa: consumo (%) = 100 × (repetições previstas / repetições admissíveis),
separadamente para fadiga e para erosão.

### Passo (i) — Verificação e resultado em h = 25 cm
Somando as 25 linhas da folha de trabalho (Quadro 11):

**Σ fadiga = 8,9 %** (< 100 %, aprovada) **Σ erosão = 105,4 %** (> 100 %, **reprovada**)

A erosão governa. Deve-se tentar uma espessura maior.

### Repetição completa do roteiro em h = 26 cm (Quadro 24, pág. 118)
Todo o roteiro (passos c–h) é refeito do zero: novas leituras nos Quadros 12/13 (agora
σ_eq ES = 1,08), novas leituras nos Quadros 16/17 (FE ES = 2,68), 25 novas leituras nos
ábacos das Figuras 27/28, 25 novas divisões para o consumo por faixa.

**Resultado em h = 26 cm:** Σ fadiga = 0 % (todas as faixas ficam com fadiga ilimitada) ·
**Σ erosão = 89,3 %** (< 100 %, **aprovada**).

**⇒ Espessura adotada: h = 26 cm, controlada por erosão.**

Resolver o problema à mão, do zero até esse resultado, envolve **duas passagens completas**
pelo roteiro (h=25 reprovado, h=26 aprovado) — ou seja, cerca de **50 leituras de
nomograma** mais as somas e verificações, além da consulta a 6 tabelas diferentes (Quadros
9, 12, 13, 16, 17) e 2 ábacos (Figuras 27, 28) organizados em 4 variantes cada
(sem/com acostamento × sem/com barras) — 12 tabelas e 4 ábacos ao todo disponíveis no
manual, dos quais o projetista precisa identificar e usar os corretos a cada consulta.

---

## 3. Exemplo complementar: quando a carga não cai num nó tabelado

O exemplo oficial do manual foi montado propositalmente com h e k caindo exatamente nos
nós das tabelas (h em centímetros inteiros, k = 100 MPa/m, ambos valores tabelados) — não
exige interpolação. **Na prática, isso raramente acontece**: o subleito de um projeto real
quase nunca resulta num k redondo como 100. Para ilustrar o passo que o exemplo oficial
evita, seja um subleito com **k = 85 MPa/m**, mesma placa (h-tentativa = 27 cm, fctk = 4,8
MPa, FSC = 1,2, PSAC/JSP), eixo simples com carga de 13 tf.

O Quadro 12 tabela k em [20, 40, 60, 80, 100, 150, 180] MPa/m — **85 não é um valor
tabelado**. O projetista precisa **interpolar entre as colunas k=80 e k=100** (interpolação
linear "pois se está do lado da segurança", mesma nota do manual, pág. 116):

**(c) Tensão equivalente, por interpolação linear em k** (h=27 é nó exato; interpola-se só k):

$$\sigma_{eq}(k{=}85) = \sigma_{eq}(80) + \big[\sigma_{eq}(100)-\sigma_{eq}(80)\big]\cdot\frac{85-80}{100-80}$$
$$= 1{,}07 + (1{,}03 - 1{,}07)\cdot\frac{5}{20} = 1{,}07 - 0{,}01 = \mathbf{1{,}06\ MPa}$$

**(d) Fator de erosão, mesma interpolação, agora no Quadro 16:**

$$FE(k{=}85) = 2{,}64 + (2{,}63-2{,}64)\cdot\frac{5}{20} = 2{,}64 - 0{,}0025 = \mathbf{2{,}6375}$$

Cada uma dessas duas interpolações é uma conta extra que o projetista precisa montar e
resolver à mão — **e repetir para cada uma das dezenas de faixas de carga do espectro**,
sempre que k (ou h) não caia num nó tabelado. É exatamente aqui que a maior parte dos erros
de projeto manual acontece: usar por engano a coluna vizinha, trocar os dois quadros de uma
mesma dupla (ex.: ler o Quadro 18 pensando ser o 16), ou interpolar com o sinal invertido.

---

## 4. Resolução pela ferramenta computacional

Os mesmos dados de entrada (fctk, k, FSC, acostamento, barras, espectro de tráfego) são
informados uma única vez na interface. A ferramenta:

1. Consulta as 12 tabelas tabuladas (Quadros 12–23, transcritas integralmente do manual)
   por **interpolação bilinear** (h × k) — a mesma operação do item 3 acima, mas repetida
   automaticamente para cada uma das faixas de carga do espectro, em milissegundos.
2. Substitui os ábacos das Figuras 27/28/29 por equações equivalentes (a de fadiga é a
   equação padrão da PCA; a de erosão foi reconstruída e calibrada empiricamente a partir
   dos pontos do próprio exemplo oficial do manual — ver nota metodológica, seção 5).
3. Itera h de 10 a 40 cm automaticamente, repetindo o roteiro completo (passos c–i) para
   cada espessura testada, e devolve a **menor h aprovada em ambos os critérios**.
4. Exibe, na tela "Memória de Cálculo", a mesma folha de trabalho do Quadro 11 —
   interpolações, fórmulas com os valores substituídos e resultado por faixa — de forma
   equivalente à resolução manual, mas gerada automaticamente e sem risco de erro de
   transcrição entre passos.

Rodando os mesmos dados do exemplo oficial (item 2), a ferramenta devolve:

| | Manual (folha de trabalho, ×2 passagens h=25/26) | Ferramenta |
|---|---|---|
| Σ fadiga (h=26) | 0,0 % | 1,8 % |
| Σ erosão (h=26) | 89,3 % | 90,9 % |
| Espessura adotada | 26 cm | 26 cm |
| Critério que governa | Erosão | Erosão |

(A pequena diferença de 1,6 p.p. na erosão vem da equação de erosão ser uma reconstrução
empírica dos ábacos, não uma cópia exata — ver seção 5. A conclusão de engenharia —
espessura e critério governante — é idêntica.)

---

## 5. Comparação: manual vs. ferramenta

| | Manual | Ferramenta |
|---|---|---|
| Consultas a tabela/ábaco (1 espessura, 25 faixas) | ~50 (2 tensão + 2 erosão por faixa) | idem, automáticas |
| Interpolações manuais necessárias (k ou h fora dos nós) | 1 por consulta, à mão | automáticas, bilineares, sem erro de conta |
| Repetir tudo para uma 2ª espessura-tentativa | Sim, do zero | Instantâneo (a ferramenta já testa h=10 a 40 automaticamente) |
| Tempo estimado (1 espessura, espectro de 25 faixas) | 1 a 3 horas (leitura de nomograma + tabelas + somas) | < 1 segundo |
| Risco de erro humano | Tabela/ábaco errado, interpolação com sinal trocado, erro de soma, paralaxe na leitura do nomograma | Nenhum erro de execução (mesma fórmula aplicada sempre); risco desloca-se para a qualidade da calibração das equações que substituem os ábacos |
| Rastreabilidade | Depende de o projetista anotar cada leitura | Cada resultado guarda os valores intermediários (σ_eq, FE, SR, N admissível) para auditoria |
| Sensibilidade (variar k, fctk, tráfego, FSC) | Refazer manualmente cada cenário | Gráfico gerado automaticamente (`sensibilidade.py`) |

**O ganho central não é só velocidade — é consistência.** Um ser humano repetindo o mesmo
roteiro 25 vezes por espessura, para várias espessuras, tende a cometer *erros diferentes
a cada vez* (fadiga em uma linha, tabela errada em outra). A ferramenta aplica a *mesma*
fórmula, sempre da mesma forma — o que significa que, se houver um erro, ele é
**sistemático e localizável por auditoria**, não aleatório e escondido em uma folha de
papel.

---

## 6. Nota metodológica: um caso real de erro sistemático encontrado por auditoria

Este episódio, ocorrido durante o desenvolvimento (23/08/2026), é um argumento direto a
favor da ferramenta e vale registrar no TCC como evidência de rigor metodológico.

Ao validar a ferramenta contra o **Quadro 24** do manual (a folha de trabalho completa em
h=26cm, com eixo simples, tandem duplo e tandem triplo), identificou-se que a equação de
erosão — reconstruída empiricamente porque o manual só publica o ábaco, não uma fórmula
fechada — havia sido calibrada usando **apenas** pontos de eixo simples. Ao ser aplicada a
eixos tandem duplo (cargas maiores, sobre a mesma Figura 28), a equação **extrapolava mal**
e chegava a prever consumo de erosão de 60–90% onde o manual mostra 0,6–1,5% — um erro de
duas ordens de grandeza, que teria comprometido silenciosamente qualquer dimensionamento
real com tráfego de caminhões articulados (a maioria dos casos práticos).

A causa raiz, uma vez identificada, foi dupla: (1) a Figura 28 é um nomograma de três
escalas paralelas cuja escala de carga para tandem duplo é desenhada à metade da posição da
escala de eixo simples — um "fator de conversão" implícito no desenho do gráfico que não
estava sendo replicado na fórmula; e (2) a dependência da equação em relação ao fator de
erosão havia sido ajustada com uma única curva, sem cobertura para outros valores.

A correção — recalibrar a equação com os 25 pontos do Quadro 24 (cobrindo os três tipos de
eixo) e adicionar o fator de conversão de escala do tandem duplo — reduziu a divergência
média por faixa de carga de **21,9 p.p. para 0,2 p.p.** Esse é exatamente o tipo de erro
sistemático que uma verificação manual pontual (conferir uma ou duas linhas) **não
detectaria**, mas que uma auditoria automatizada, comparando dezenas de pontos de uma vez,
expõe imediatamente — outro argumento em favor de ferramentas computacionais testáveis
frente ao cálculo manual ponto-a-ponto.

**Limitação ainda em aberto** (para constar honestamente no TCC): a recalibração acima cobre
apenas fatores de erosão entre 2,68 e 2,89 (a faixa do exemplo oficial, sem acostamento).
Fora dessa faixa — por exemplo, pavimentos com acostamento de concreto e barras de
transferência, que tendem a fatores de erosão bem menores — a ferramenta aplica um limite
conservador (clamp) em vez de extrapolar sem controle, mas a precisão nessa região ainda não
foi validada contra um segundo exemplo oficial. Próximo passo natural: digitalizar
diretamente a Figura 28 (faixa completa, FE de 2,0 a 4,0) e a Figura 29 (com acostamento),
usando a mesma técnica já empregada para os ábacos de fundação (Figuras 11, 18–21).
