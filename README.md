# Dimensionamento de Pavimentos Rígidos — DNIT IPR-714 / PCA 1984

Ferramenta computacional (Python + NiceGUI) para dimensionamento de placas de
pavimento rígido de concreto simples pelo **método PCA 1984** (critério duplo de
fadiga e erosão), método preferencial do **Manual de Pavimentos Rígidos do DNIT
(IPR-714)**. Desenvolvida como TCC — Engenharia Civil, UFRJ/POLI.

O app guia o usuário por um assistente de 6 etapas (Viabilidade → Fundação →
Tráfego → Concreto → Memória de cálculo → Resultado), puxando dados reais de
fontes oficiais a partir do local da obra (cobertura automática: Estado do RJ)
e exportando relatório em PDF.

## Instalação

Requer Python 3.12+ (desenvolvido em 3.14).

```bash
pip install -r requirements.txt
```

## Execução

**Interface principal (NiceGUI):**

```bash
python app_nicegui.py
```

O app abre em `http://localhost:8503`.

**Plano B (interface Streamlit legada, mesmas funcionalidades):**

```bash
python -m streamlit run app.py    # http://localhost:8501
```

As duas interfaces usam exatamente o mesmo motor de cálculo e os mesmos dados —
apenas a camada visual difere.

> **Windows:** se `streamlit` não estiver no PATH, use sempre `python -m streamlit`.
> Se o Smart App Control bloquear DLLs do numpy/pandas, desative-o em
> *Segurança do Windows → Controle de aplicativos e navegador*.

## Validação do motor de cálculo

O motor é validado ponta-a-ponta contra o exemplo do IPR-714 (Quadro 11):

```bash
python validar_e2e.py      # fadiga 8,6% (manual: 8,9%) | erosão 89,8% (manual: 89,9%)
python validar_erosao.py   # equação de erosão vs. ábaco: erro médio 3,2%
```

## Mapa de módulos

| Camada | Arquivos | Função |
|---|---|---|
| **Motor de cálculo** | `calculos.py`, `tabelas_pca.py`, `_tabelas_geradas.py` | PCA 1984: fadiga + erosão; Quadros 12–23 do IPR-714 (interpolação bilinear h×k) |
| **Fundação** | `estagio3.py`, `solos_rj.py`, `local_subleito.py` | CBR/solo → k0 (Fig. 11 / Quadro 3); sub-base → k efetivo (Figs. 18–21); solo pelo local (pedologia EMBRAPA, point-in-polygon offline) |
| **Tráfego** | `veiculos_dnit.py`, `perfis_trafego.py`, `pnct_dados.py` | Classes de veículos e eixos (IPR-723, Fig. 13); perfis de composição; VMDa real dos postos PNCT/DNIT (RJ, 2022) |
| **Custo / recomendação** | `custos_sicro.py`, `recomenda_subbase.py` | Custos SICRO RJ jan/2026 (R$/m³); recomendação de sub-base por tráfego + subleito, com eficiência custo×ganho de k |
| **Clima** | `clima.py` | Precipitação média anual por município (normal NASA POWER, offline) |
| **Interface principal** | `app_nicegui.py`, `telas_ng.py`, `ui_ng.py`, `state_ng.py` | Wizard NiceGUI (fluxo vertical, mapas Leaflet, gráficos ECharts interativos, MathJax) |
| **Interface plano B** | `app.py`, `telas.py`, `ui.py`, `triagem.py` | Mesmo wizard em Streamlit (mapa folium, matplotlib); `triagem.py` é compartilhado pelas duas |
| **Saída** | `resultados.py` | Relatório PDF (fpdf2): parâmetros, espectro, resultado, gráfico h×consumo, recomendação |

**Scripts `_gen_*.py` e `_fit_*.py` são ferramentas de desenvolvimento** (digitalização
de tabelas do manual, empacotamento de dados externos, calibração) — não são usados
em runtime. Os dados que eles geram ficam versionados nas pastas `_pnct/`, `_solos/`,
`_mun/`, `_clima/`, `_sicro/` e em `_tabelas_geradas.py`. Nenhuma API é consultada
em runtime: todo dado externo é empacotado offline.

## Fontes de dados

- **DNIT IPR-714** — Manual de Pavimentos Rígidos (método PCA 1984, Quadros 9–23, Figuras 11, 18–21): <https://www.gov.br/dnit/pt-br/assuntos/planejamento-e-pesquisa/ipr/coletanea-de-manuais/vigentes/ipr-714-manual-de-pavimentos-rigidos.pdf>
- **DNIT IPR-723** — Manual de Estudos de Tráfego (Figura 13, configuração de eixos por classe de veículo): <https://www.gov.br/dnit/pt-br/assuntos/planejamento-e-pesquisa/ipr/coletanea-de-manuais/vigentes>
- **PNCT/DNIT** — Plano Nacional de Contagem de Tráfego, VMDa 2022 por trecho SNV: <https://servicos.dnit.gov.br/dadospnct> (dados abertos CKAN)
- **EMBRAPA GeoInfo** — Pedologia do Estado do RJ (camada WFS, classes SiBCS + textura): <https://geoinfo.dados.embrapa.br>
- **SICRO/DNIT** — Custos rodoviários RJ, referência jan/2026: <https://www.gov.br/dnit/pt-br/assuntos/planejamento-e-pesquisa/custos-e-pagamentos/custos-e-pagamentos-dnit/sistemas-de-custos>
- **NASA POWER** — Normal climatológica de precipitação (PRECTOTCORR): <https://power.larc.nasa.gov>
- **IBGE** — Malha municipal do RJ (divisas no mapa): <https://www.ibge.gov.br/geociencias/organizacao-do-territorio/malhas-territoriais>

## Limitações assumidas (transparência)

- A equação de erosão foi **reconstruída empiricamente** a partir do exemplo do
  manual (o IPR-714 só traz ábacos) — erro médio de 3,2% na validação.
- Solo → CBR/k0 pelo local é **estimativa de partida** (textura → AASHTO → CBR);
  o app sempre recomenda confirmar com ensaio CBR local.
- A composição de tráfego vem de **perfis-tipo editáveis** (o VMDa é real, do PNCT).
- Cobertura automática dos dados (solo/tráfego/custo): RJ. Fora do RJ, entrada manual.

Documentação completa (método, fórmulas, decisões de projeto): [`DOCUMENTACAO.md`](DOCUMENTACAO.md).
Plano de evolução: [`ROADMAP.md`](ROADMAP.md).
