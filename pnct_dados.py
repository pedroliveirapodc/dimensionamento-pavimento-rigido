"""
pnct_dados.py - Leitura dos dados de trafego do PNCT (DNIT) por trecho de rodovia.

Fonte: planilha do VMDa MODELADO do Plano Nacional de Contagem de Trafego (PNCT),
ano-base 2022 (_pnct/vmda2022.xlsx, aba SNV202301B). Dados abertos do DNIT.

O que este modulo entrega: o VOLUME (VMDa) e o ANO de um trecho real de rodovia
federal. A COMPOSICAO por classe de veiculo NAO sai daqui - a legenda das
categorias A-J do PNCT esta indisponivel (doc oficial fora do ar). Por isso o
modo Expedito do app usa o VMDa real desta fonte e a composicao de um perfil-tipo
(perfis_trafego.py), com os eixos pela classificacao do Manual DNIT IPR-723.

OBS p/ a banca: o VMDa do PNCT e MODELADO (nao contagem bruta). Trechos urbanos/
metropolitanos podem vir marcados "Nao Simulavel" no campo 'classificacao' - nesses
casos o proprio DNIT recomenda complementar com analise local.
"""
from __future__ import annotations

import os
from dataclasses import dataclass

ANO_BASE = 2022
_ARQUIVO = os.path.join(os.path.dirname(__file__), "_pnct", "vmda2022.xlsx")
_ABA = "SNV202301B"


@dataclass(frozen=True)
class Trecho:
    """Um trecho de rodovia federal com seu VMDa total (ambos os sentidos)."""
    br: str
    local_i: str
    local_f: str
    km_i: float | None
    km_f: float | None
    vmda_total: float
    classificacao: str = ""

    @property
    def rotulo(self) -> str:
        loc = f"{self.local_i} -> {self.local_f}".strip(" ->")
        return f"BR-{self.br} | {loc}  (VMDa {self.vmda_total:,.0f})"

    @property
    def nao_simulavel(self) -> bool:
        c = self.classificacao.lower()
        return "simul" in c and ("nao" in c or "não" in c)


def _resolver(idx: dict, *cands: str) -> int | None:
    """Acha o indice de uma coluna por nome exato ou por substring (robusto a acentos)."""
    for c in cands:
        if c in idx:
            return idx[c]
    for k in idx:
        ks = str(k).lower()
        if any(c.lower() in ks for c in cands):
            return idx[k]
    return None


def _fmt_br(v) -> str:
    try:
        return f"{int(round(float(v))):03d}"
    except (TypeError, ValueError):
        return str(v)


def carregar_trechos(caminho: str = _ARQUIVO, uf: str = "RJ",
                     apenas_com_volume: bool = True) -> list[Trecho]:
    """
    Le o XLSX do PNCT e retorna os trechos da UF dada, ordenados por VMDa (desc).
    Remove duplicatas exatas (mesmo BR + mesmos locais inicial/final).
    Lanca FileNotFoundError se o arquivo nao existir.
    """
    if not os.path.exists(caminho):
        raise FileNotFoundError(f"Arquivo do PNCT nao encontrado: {caminho}")

    import openpyxl
    wb = openpyxl.load_workbook(caminho, read_only=True, data_only=True)
    ws = wb[_ABA]
    rows = ws.iter_rows(values_only=True)
    header = list(next(rows))
    idx = {h: i for i, h in enumerate(header)}

    i_uf = _resolver(idx, "sg_uf")
    i_br = _resolver(idx, "vl_br")
    i_li = _resolver(idx, "ds_local_i")
    i_lf = _resolver(idx, "ds_local_f")
    i_ki = _resolver(idx, "vl_km_inic")
    i_kf = _resolver(idx, "vl_km_fina")
    i_vc = _resolver(idx, "VMDa_C")
    i_vd = _resolver(idx, "VMDa_D")
    i_cl = _resolver(idx, "classificacao", "classificação", "classif")

    def cel(r, i):
        return r[i] if (i is not None and i < len(r)) else None

    vistos: set[tuple] = set()
    trechos: list[Trecho] = []
    for r in rows:
        if cel(r, i_uf) != uf:
            continue
        total = (cel(r, i_vc) or 0) + (cel(r, i_vd) or 0)
        if apenas_com_volume and total <= 0:
            continue
        br = _fmt_br(cel(r, i_br))
        li = str(cel(r, i_li) or "").strip()
        lf = str(cel(r, i_lf) or "").strip()
        chave = (br, li, lf)
        if chave in vistos:
            continue
        vistos.add(chave)
        trechos.append(Trecho(
            br=br, local_i=li, local_f=lf,
            km_i=cel(r, i_ki), km_f=cel(r, i_kf),
            vmda_total=float(total),
            classificacao=str(cel(r, i_cl) or "").strip(),
        ))
    wb.close()
    trechos.sort(key=lambda t: -t.vmda_total)
    return trechos


if __name__ == "__main__":
    ts = carregar_trechos()
    print(f"Trechos RJ com VMDa>0 (ano-base {ANO_BASE}): {len(ts)}\n")
    print("Top 8 por VMDa:")
    for t in ts[:8]:
        flag = "  [NAO SIMULAVEL]" if t.nao_simulavel else ""
        print(f"  {t.rotulo}{flag}")
    print(f"\nBRs presentes: {sorted({t.br for t in ts})}")
