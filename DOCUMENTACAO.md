# Ferramenta de Dimensionamento de Pavimentos Rígidos — Documentação do Projeto

> **TCC — UFRJ/POLI** · Autor: Pedro · Plataforma: **Python + Streamlit**
> Método: **PCA 1984** (Manual de Pavimentos Rígidos do DNIT, **IPR‑714**)
> Este documento serve a dois fins: (a) **contexto de desenvolvimento** e (b) **base para a escrita do TCC** (fontes, métodos, justificativas e limitações).

---

## 1. Visão geral

A ferramenta automatiza o **dimensionamento da espessura de placas de pavimento rígido de concreto simples** pelo **método PCA 1984** (critério duplo de **fadiga** e **erosão**), adotado como preferencial pelo Manual DNIT IPR‑714 (seção 4.6.2). Além do cálculo, a ferramenta:

- **guia o usuário** por um assistente (wizard) de 6 etapas;
- **puxa dados reais** de fontes oficiais (solo, tráfego, custo, clima) a partir do **local da obra**;
- **mostra os cálculos** passo a passo (memória de cálculo), priorizando **transparência**.

Cobertura geográfica dos dados automáticos: **Estado do Rio de Janeiro** (solo, tráfego, clima, custo). Fora do RJ, o usuário insere os dados manualmente.

---

## 2. Como executar

```bash
# interpretador usado no projeto (Windows):
#   C:\Users\PEDRO\AppData\Local\Python\pythoncore-3.14-64\python.exe
python -m streamlit run app.py        # porta 8501
```

**Dependências** (`pip install`): `streamlit`, `pandas`, `numpy`, `matplotlib`, `openpyxl`, `folium`, `streamlit-folium`, `py7zr` (só para regenerar custos SICRO), `pypdf` (só dev).

**Gotchas de ambiente (Windows):**
- O **Smart App Control** já bloqueou as DLLs compiladas do `numpy`/PyMuPDF (erro *"política de Controle de Aplicativo bloqueou este arquivo"*). Se reaparecer, desativar em *Segurança do Windows → Controle de aplicativos e navegador → Smart App Control* (desativação é permanente) e reiniciar.
- `streamlit.exe` não está no PATH → sempre `python -m streamlit`.

---

## 3. Fluxo do usuário (wizard de 6 etapas)

Navegação **Voltar/Avançar**, uma decisão por tela, com **stepper** no topo e **resumo lateral** das escolhas. Tema visual *infra/âmbar* (cinza‑asfalto + âmbar).

| # | Etapa | O que faz |
|---|-------|-----------|
| 1 | **Viabilidade** | Triagem *go/no‑go*: 6 critérios ponderados (tráfego, vida útil, CBR, manutenção, precipitação, acesso a usina) → **score /36** e recomendação (rígido indicado / viável / favorável a flexível). Orientativo, não bloqueia. |
| 2 | **Fundação** | Define o **local** (clique no mapa ou CEP) → solo/CBR/**k0** automáticos (RJ); ou entrada manual. Depois a **sub‑base** (tipo + espessura) → **k efetivo**. |
| 3 | **Tráfego** | **Marcar no mapa** (posto real do PNCT) ou **digitar** o VMDa; + perfil de composição + período → **espectro de eixos** (editável). |
| 4 | **Concreto** | Acostamento, barras de transferência e (avançado) fctk, FSC. |
| 5 | **Memória de cálculo** | Mostra **passo a passo** como a espessura é obtida (fórmulas + valores), por classe de eixo. |
| 6 | **Resultado** | Espessura final, consumos, gráfico h × consumo e **recomendação de sub‑base com custo (SICRO)**. |

---

## 4. Método de cálculo — PCA 1984 (para a escrita do TCC)

**Critério duplo:** a espessura é adequada se, somando todas as classes de eixo, o **consumo de fadiga** (Σ) **e** o **consumo de erosão** (Σ) forem **≤ 100%**. Itera‑se *h* de 10 a 40 cm (passo 0,5) e adota‑se a **menor** *h* que atende ambos.

Para cada classe de eixo (carga *P*, *N* repetições previstas):

1. **Carga efetiva:** `P_ef = P · FSC` (tandem triplo: ÷3, pois o ábaco o trata como 3 eixos simples).
2. **Tensão equivalente** `σ_eq`: interpolada (h × k) dos **Quadros 12–15** do IPR‑714.
3. **Relação de tensões:** `SR = (σ_eq / f_ctk) · (P_ef / P_padrão)^0,94`.
4. **Repetições admissíveis — fadiga** (equações PCA, ábaco Fig. 27):
   - `SR < 0,45` → ilimitado;
   - `0,45 ≤ SR < 0,55` → `N = (4,2577/(SR−0,4325))^3,268`;
   - `SR ≥ 0,55` → `log10 N = 11,737 − 12,077·SR`.
5. **Fator de erosão** (Quadros 16–23) e **repetições admissíveis — erosão** (ábaco Fig. 28/29).
6. **Consumos:** `CF = N_prev/N_fadiga ×100` e `CE = N_prev/N_erosão ×100`.

**Entradas‑chave:** `f_ctk` (resistência à tração na flexão, usada diretamente — não derivada de fck), `k` (coeficiente de recalque no topo da sub‑base), `FSC` (Quadro 9: 1,0 / 1,1 / 1,2 / até 1,5), e o **espectro de tráfego** (carga × repetições por tipo de eixo: simples, tandem duplo, tandem triplo).

**Validação do motor (E2E, contra o Quadro 11 do manual):** fadiga **8,6%** (manual 8,9%) e erosão **89,8%** (manual 89,9%) para o exemplo. Equação de erosão calibrada com erro médio **3,2%** vs. o exemplo.

**Limitações assumidas (honestidade metodológica — citar na defesa):**
- A **equação de erosão** foi **reconstruída empiricamente** (o manual só traz o ábaco). Boa aderência ao exemplo, mas a dependência no fator de erosão foi ajustada com uma curva; o `C1` com acostamento é provisório.
- A **fadiga** usa as equações PCA consagradas (sem aproximação).

---

## 5. Funcionalidades e fontes de dados (para a escrita do TCC)

Princípio de projeto: **onde o dado é oficial e direto, é rigoroso; onde é aproximação, está marcado como estimativa e o usuário confirma**. Nenhum número "sai do nada".

### 5.1 Localização → subleito (solo, CBR, k0)
- **Fonte:** pedologia do **EMBRAPA GeoInfo** (camada estadual do RJ, *geonode:solos_rj_lat_long_wgs84_1*, 2807 polígonos, SiBCS + classe textural). Baixada via WFS e empacotada em GeoJSON; consulta **offline** por *point‑in‑polygon* (sem dependência de API em runtime).
- **Cadeia:** CEP → município/UF (ViaCEP) → coordenada (Nominatim/OSM) → solo+textura (EMBRAPA) → classe AASHTO → **k0** (Quadro 3 do IPR‑714). O clique no mapa entra direto com a coordenada.
- **Limitação:** a conversão **textura → AASHTO → CBR** é **estimativa** (o SiBCS não fornece CBR direto — faltam LL/IP). É **valor de partida** — a interface diz "confirmar com ensaio CBR local".

### 5.2 Tráfego (espectro de eixos)
- **Tipo de eixo por veículo:** **Manual de Estudos de Tráfego do DNIT, IPR‑723, Figura 13** (configurações de eixos por classe e cargas legais). Fonte oficial e citável.
- **Volume real:** **PNCT/DNIT** (Plano Nacional de Contagem de Tráfego), VMDa modelado **ano‑base 2022**. Reduzido aos **33 postos "Referencial"** (estações de contagem reais) do RJ; **27 geocodificados** e exibidos como **pinos clicáveis** no mapa.
- **Composição da frota:** **perfil‑tipo editável** (referência ancorada em ordens de grandeza do IPR‑723), não contagem real.
- **Separação defensável:** tipo de eixo = **rigoroso** (IPR‑723); volume = **dado real** (PNCT) ou manual; composição = **perfil editável**.
- **Limitação:** a legenda das categorias A–J do VMDa modelado está fora do ar → a composição vem do perfil‑tipo. Trechos urbanos "Não Simuláveis" são sinalizados.

### 5.3 Sub‑base — recomendação + custo
- **Recomendação técnica:** regra de decisão a partir do **nível de tráfego (N)** + **qualidade do subleito (k0)** → tipo de sub‑base (diretriz DNIT/PCA: tráfego pesado/subleito fraco → sub‑base **cimentada**, que eleva *k* e reduz a erosão). Mostra o **k efetivo** de cada opção (Figuras 18–21).
- **Custo:** **SICRO/DNIT** (Relatório Sintético de Composições de Custos), **RJ, janeiro/2026** — custo por m³ das sub‑bases (brita graduada R$ 121, solo‑cimento R$ 117, BGTC R$ 170, CCR R$ 184). A ferramenta calcula a **custo‑efetividade** (ganho de *k* por R$).
- **Limitação:** custo por **UF** (não por município); a recomendação é **estrutural** — disponibilidade local de material é ressalva.

### 5.4 Clima (precipitação) — *implementado, hoje dormente*
- **Fonte:** **normal climatológica** da **NASA POWER** (média histórica multi‑anual) por município do RJ, pré‑calculada em CSV. **Decisão metodológica:** usa **série histórica**, não API de tempo real — a precipitação de projeto é média de longo prazo.
- **Estado:** o auto‑preenchimento da precipitação na triagem foi **desligado** quando a triagem virou a 1ª etapa (sem local definido ainda). O módulo e o dado seguem prontos para religar.
- **Limitação:** resolução ~0,5° suaviza extremos (serra/região dos Lagos) → estimativa de **faixa**, não valor de estação.

### 5.5 Divisões municipais no mapa
- **Fonte:** **IBGE** (malha municipal do RJ, 92 municípios). Exibidas como contorno + nome no hover.

---

## 6. Transparência — memória de cálculo

A etapa **"Memória de cálculo"** apresenta, para a espessura adotada e **por classe de eixo**, as **fórmulas com os valores substituídos** (renderizadas em notação matemática): carga efetiva, σ_eq, SR, repetições admissíveis de fadiga (com o regime aplicado), consumo de fadiga, fator de erosão, repetições de erosão e consumo de erosão — mais os **somatórios** e a **verificação ≤ 100%**.

Tecnicamente, o motor (`calculos.py`) passou a **expor os intermediários** (antes calculados e descartados) via a dataclass `ResultadoConsumo`. **O cálculo não mudou — apenas ficou visível.**

---

## 7. Arquitetura e módulos (para desenvolvimento)

**Orquestração / UI**
- `app.py` — orquestrador do wizard (sequência de telas, navegação, stepper).
- `ui.py` — tema/CSS, cabeçalho, stepper, `pergunta()`, `resumo_sidebar()`.
- `telas.py` — renderizadores de cada tela (lê/grava `st.session_state`, reusa o backend).
- `.streamlit/config.toml` — tema (cores âmbar/asfalto).

**Motor de cálculo (núcleo PCA 1984)**
- `calculos.py` — `dimensionar()`, `verificar_espessura()`, equações de fadiga/erosão, dataclasses (`ParametrosProjeto`, `ResultadoConsumo` com intermediários, `ResultadoEspessura`).
- `tabelas_pca.py` (+ `_tabelas_geradas.py`) — Quadros 12–23 (tensão equivalente e fator de erosão), `consultar()` (interpolação h×k).

**Camadas de dados / lógica**
- `estagio3.py` — CBR→k0 (Fig. 11), solo→k0 (Quadro 3), sub‑base→k efetivo (Figs. 18–21, cap 150).
- `veiculos_dnit.py` — classes DNIT → eixos (IPR‑723, Fig. 13) → `FaixaCarga`.
- `perfis_trafego.py` — perfis de composição → `espectro_de_projeto()`.
- `pnct_dados.py` — leitura do VMDa do PNCT por trecho.
- `local_subleito.py` — CEP/coordenada → solo/CBR/k0 (ViaCEP, Nominatim, EMBRAPA).
- `solos_rj.py` — *point‑in‑polygon* offline (pedologia RJ) + textura→AASHTO.
- `recomenda_subbase.py` — recomendação de sub‑base (N + k0) + custo/eficiência.
- `custos_sicro.py` — tabela de custos SICRO (RJ jan/2026).
- `clima.py` — precipitação por município (NASA POWER) [dormente].
- `triagem.py` — perguntas, pesos, `score()`, categorizadores.

**Dados embarcados**
- `_pnct/vmda2022.xlsx`, `_pnct/postos_rj.csv` (27 postos geocodificados).
- `_solos/solos_rj.min.geojson` (consulta de solo).
- `_mun/rj_municipios.min.geojson` (divisas).
- `_sicro/RJ 01‑2026 … Composições de Custos.xlsx` (fonte do custo).
- `_clima/clima_rj.csv` (precipitação por município).

**Geradores / dev (não‑runtime)**
- `_gen_tabelas.py` (Quadros), `_gen_solos_display.py`, `_gen_postos.py`, `_gen_clima.py`, `_fit_erosao.py`, `validar_erosao.py`, `validar_e2e.py`.

**Manual de referência:** `C:\Users\PEDRO\Downloads\714_manual_de_pavimentos_rigidos (1).pdf` (IPR‑714 completo) e `IPR‑723` (no zip do curso de Rodovias).

---

## 8. Pendências / próximos passos

- ~~`resultados.py` — **exportação do relatório em PDF**~~ ✅ **FEITO (27/06/2026)** — `gerar_pdf(param, resultado, curva, ctx)` gera PDF de 2 páginas via `fpdf2` + Arial Unicode; botão ⬇️ na tela de Resultado. `fpdf2>=2.8` adicionado ao `requirements.txt`.
- `README.md` curto (instalação/uso).
- **Estender cobertura além do RJ:** solo (outras UFs EMBRAPA / shapefile IBGE 250k), custo (.7z SICRO por UF), clima (NASA POWER já é nacional).
- **Recuperar os 6 postos** do PNCT que falharam no geocode; refinar posições.
- (Opcional) Religar o auto‑preenchimento de clima/CBR após a definição do local; validar dependência‑EF da erosão.

### 🔴 Decisão pendente — Conversão VMDa → categoria de tráfego na Etapa 1 (Viabilidade)

**Contexto:** a triagem (Etapa 1) classifica o volume de tráfego na escala de **N total de eixos pesados** no período (`triagem.py`, critério `"traf"`: N < 10⁶ / 10⁶–10⁷ / 10⁷–10⁸ / > 10⁸). Os postos PNCT geocodificados (`_pnct/postos_rj.csv`) fornecem **VMDa em veíc/dia** (volume total de veículos, sem discriminação por tipo). Para auto‑preencher o slider de tráfego a partir de um posto PNCT selecionado no mapa, seria necessário converter VMDa → N, o que exige ao menos dois dados ainda não disponíveis na Etapa 1: **perfil de composição da frota** (% de veículos pesados) e **período de projeto** (anos). Esses dados só são definidos na Etapa 3 (Tráfego).

**Opções em aberto (decidir antes de implementar o auto‑fill de tráfego):**

- **Opção A — Conversão rápida com defaults:** aplicar um perfil-tipo fixo (ex.: 10 % de veículos pesados, 20 anos, sem crescimento) só para estimar a *faixa* da triagem. Resultado seria indicativo, não rigoroso. Registrar na UI como "estimativa orientativa".
- **Opção B — Reformular o critério `"traf"` para VMDa:** substituir a escala N pelas faixas de VMDa total (ex.: < 1.000 / 1.000–10.000 / 10.000–50.000 / > 50.000 veic/dia), que são mais intuitivas e diretamente obtidas do PNCT. Exige rever os limiares e pesos da triagem.
- **Opção C — Exibir VMDa só como informação:** mostrar "Posto BR‑XXX — VMDa X.XXX veic/dia" sem auto‑preencher nenhum slider; o usuário ajusta manualmente. Zero risco de erro de conversão.

**Impacto:** nenhum código de cálculo muda; só a lógica de auto‑fill do slider `"traf"` na `tela_viabilidade`. Baixo risco técnico, mas a escolha afeta a coerência metodológica da triagem.

---

## 9. Referências (fontes oficiais)

- **DNIT — Manual de Pavimentos Rígidos (IPR‑714).** Método PCA 1984.
- **DNIT — Manual de Estudos de Tráfego (IPR‑723).** Figura 13 (classificação de eixos).
- **DNIT — PNCT (Plano Nacional de Contagem de Tráfego), VMDa modelado, ano‑base 2022.** Dados abertos: `servicos.dnit.gov.br/dadosabertos` (dataset *contagem‑de‑trafego*).
- **DNIT — SICRO (Sistema de Custos Referenciais de Obras), RJ jan/2026.** `gov.br/dnit → Custos Referenciais → SICRO`.
- **EMBRAPA GeoInfo — Pedologia do RJ (SiBCS).** `geoinfo.dados.embrapa.br/geoserver` (camada *solos_rj_lat_long_wgs84_1*).
- **IBGE — Malhas municipais e localidades.** `servicodados.ibge.gov.br/api`.
- **ViaCEP** (`viacep.com.br`) e **Nominatim/OpenStreetMap** (geocodificação).
- **NASA POWER — Climatologia (precipitação).** `power.larc.nasa.gov`.

> *Observação para a redação:* as URLs e datas de acesso devem ser confirmadas no momento da escrita; os dados embarcados têm ano‑base explícito (PNCT 2022, SICRO jan/2026).

---

*Documento gerado em 25/06/2026, ao fim da reestruturação que colocou a Viabilidade como 1ª etapa e adicionou a Memória de cálculo.*
