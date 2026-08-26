"""
veiculos_dnit.py - Classificacao de veiculos do DNIT e conversao para eixos.

Traduz uma FROTA (quantidade de veiculos por classe) no ESPECTRO de eixos
(ES / ETD / ETT) que o motor de calculo (calculos.py) consome.

FONTE: Manual de Estudos de Trafego do DNIT (IPR-723), secao 3.4 e Figura 13
("Veiculos adotados na classificacao do DNIT"). Cada classe tem uma configuracao
de eixos com carga maxima legal (CM):
  - eixo simples de rodagem simples (direcional) ......  6 t
  - eixo simples de rodagem dupla (ESRD) .............. 10 t
  - conjunto tandem duplo (TD) ........................ 17 t
  - conjunto tandem triplo (TT) ....................... 25,5 t
  - conjunto de eixos direcionais (CED, 4CD) .......... 12 t

As cargas adotadas aqui sao os LIMITES LEGAIS (veiculo carregado no limite), o
que da um espectro conservador e citavel. O usuario pode editar caso a caso no
modo detalhado do app, ou aplicar um fator de carga medio.

No metodo PCA o tandem triplo entra com a carga TOTAL do conjunto (25,5 t); o
proprio motor (calculos._carga_efetiva) divide por 3 ao usar o abaco de eixo
simples. Por isso aqui o ETT carrega a carga total, nao a fracao.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from calculos import TipoEixo, FaixaCarga


# Cargas maximas legais por tipo de eixo (t), Figura 13 do IPR-723.
CM_ES_DIRECIONAL = 6.0    # eixo simples de rodagem simples (dianteiro)
CM_ESRD = 10.0            # eixo simples de rodagem dupla
CM_TANDEM_DUPLO = 17.0    # conjunto tandem duplo
CM_TANDEM_TRIPLO = 25.5   # conjunto tandem triplo
CM_DIRECIONAL_DUPLO = 12.0  # conjunto de eixos direcionais (4CD/CED)


class Categoria(Enum):
    """Agrupa para o calculo: leves dao consumo ~0 e podem ser ignorados."""
    LEVE = "leve"          # passeio, moto, utilitario
    ONIBUS = "onibus"
    CAMINHAO = "caminhao"


@dataclass(frozen=True)
class Eixo:
    """Um eixo (ou conjunto tandem) de um veiculo, com sua carga legal."""
    tipo: TipoEixo
    carga_tf: float
    descr: str = ""


@dataclass(frozen=True)
class VeiculoDNIT:
    """Uma classe de veiculo do DNIT e sua composicao de eixos."""
    codigo: str            # codigo de classe DNIT (ex.: "3C", "2S3")
    nome: str
    categoria: Categoria
    eixos: tuple[Eixo, ...]


# Atalhos para montar os eixos.
def _esd() -> Eixo:  # eixo simples direcional (dianteiro), rodagem simples
    return Eixo(TipoEixo.SIMPLES, CM_ES_DIRECIONAL, "ES direcional (RS) 6 t")


def _esrd() -> Eixo:  # eixo simples traseiro de rodagem dupla
    return Eixo(TipoEixo.SIMPLES, CM_ESRD, "ES rodagem dupla 10 t")


def _td() -> Eixo:
    return Eixo(TipoEixo.TANDEM_DUPLO, CM_TANDEM_DUPLO, "tandem duplo 17 t")


def _tt() -> Eixo:
    return Eixo(TipoEixo.TANDEM_TRIPLO, CM_TANDEM_TRIPLO, "tandem triplo 25,5 t")


# ---------------------------------------------------------------
# Catalogo das classes mais frequentes na malha brasileira (IPR-723).
# (Leves entram so para completude; sao desprezados no consumo.)
# ---------------------------------------------------------------
VEICULOS: dict[str, VeiculoDNIT] = {
    # --- leves (carga por eixo baixa -> consumo ~0) ---
    "P":  VeiculoDNIT("P", "Automovel de passeio", Categoria.LEVE,
                      (Eixo(TipoEixo.SIMPLES, 1.0, "ES RS"),
                       Eixo(TipoEixo.SIMPLES, 1.0, "ES RS"))),
    "U":  VeiculoDNIT("U", "Utilitario / comercial leve", Categoria.LEVE,
                      (Eixo(TipoEixo.SIMPLES, 1.5, "ES RS"),
                       Eixo(TipoEixo.SIMPLES, 2.5, "ES RS"))),
    "M":  VeiculoDNIT("M", "Motocicleta", Categoria.LEVE,
                      (Eixo(TipoEixo.SIMPLES, 0.1, "ES RS"),
                       Eixo(TipoEixo.SIMPLES, 0.1, "ES RS"))),
    # --- onibus ---
    "2CB": VeiculoDNIT("2CB", "Onibus 2 eixos", Categoria.ONIBUS,
                       (_esd(), _esrd())),
    "3CB": VeiculoDNIT("3CB", "Onibus 3 eixos (traseiro tandem)", Categoria.ONIBUS,
                       (_esd(), _td())),
    # --- caminhoes rigidos ---
    "2C": VeiculoDNIT("2C", "Caminhao 2 eixos (toco)", Categoria.CAMINHAO,
                      (_esd(), _esrd())),
    "3C": VeiculoDNIT("3C", "Caminhao 3 eixos (trucado)", Categoria.CAMINHAO,
                      (_esd(), _td())),
    "4C": VeiculoDNIT("4C", "Caminhao 4 eixos (simples, tandem triplo)", Categoria.CAMINHAO,
                      (_esd(), _tt())),
    # --- combinacoes (cavalo + semi-reboque / reboque) ---
    "2S1": VeiculoDNIT("2S1", "Cavalo 2 eixos + semi 1 eixo", Categoria.CAMINHAO,
                       (_esd(), _esrd(), _esrd())),
    "2S2": VeiculoDNIT("2S2", "Cavalo 2 eixos + semi 2 eixos", Categoria.CAMINHAO,
                       (_esd(), _esrd(), _td())),
    "2S3": VeiculoDNIT("2S3", "Cavalo 2 eixos + semi 3 eixos", Categoria.CAMINHAO,
                       (_esd(), _esrd(), _tt())),
    "3S3": VeiculoDNIT("3S3", "Cavalo 3 eixos + semi 3 eixos (bitruck)", Categoria.CAMINHAO,
                       (_esd(), _td(), _tt())),
    "3T6": VeiculoDNIT("3T6", "Rodotrem (cavalo 3 + 2 semi 6 eixos)", Categoria.CAMINHAO,
                       (_esd(), _td(), _tt(), _tt())),
}


# ---------------------------------------------------------------
# FATOR DE CARGA (carregamento da frota) — Bloco A, pedido da orientadora
# (23/08/2026): "Deveria entrar com fator de carga e fator de eixo."
#
# "Fator de eixo" = numero de eixos de cada tipo por veiculo — ja e dado
# RIGOROSO aqui (a tupla `eixos` de cada VeiculoDNIT, Figura 13 do IPR-723).
#
# "Fator de carga" = o quanto os eixos realmente carregam em relacao ao
# LIMITE LEGAL (CM_*). Ate esta sessao, o app assumia SEMPRE 100% do limite
# legal (todo caminhao "no talo") — conservador, mas nao reflete a pratica
# (parte da frota roda vazia ou parcialmente carregada; ver DNIT, "A
# Importancia das Contagens de Trafego...", que separa "classificacao da
# frota" de "carregamento da frota" como duas etapas distintas do estudo).
# A fonte RIGOROSA para o carregamento real e pesquisa de carga em posto de
# pesagem — que este projeto nao tem. Por isso o fator abaixo e um parametro
# EXPLICITO e AJUSTAVEL (nao mais implicito em "sempre 100%"), com o default
# mantendo o comportamento conservador anterior (citavel, lado da seguranca).
FATOR_CARGA_PADRAO = 1.0  # 1,0 = 100% do limite legal (default conservador)


def espectro_de_frota(frota: dict[str, float],
                      ignorar_leves: bool = True,
                      fator_carga: float = FATOR_CARGA_PADRAO) -> list[FaixaCarga]:
    """
    Converte uma frota {codigo_classe: n_veiculos} no espectro de eixos.

    Cada veiculo contribui com seus eixos; agregamos por (tipo de eixo, carga)
    somando as repeticoes. Leves sao ignorados por padrao (consumo ~0).

    fator_carga: fracao do limite legal (CM_*) que os eixos realmente
    carregam, em media (1,0 = 100%, default). Aplicado a TODOS os eixos
    igualmente -- e uma aproximacao de UM parametro (desloca o nivel de
    carga, nao reproduz uma distribuicao real vazio/parcial/cheio, que
    exigiria dado de pesagem). Ajuste se houver contagem classificatoria ou
    pesquisa de carga real do trecho -- nesse caso, prefira informar o
    espectro diretamente (editar a tabela na tela de Trafego), que entra
    100% no dimensionamento sem passar por este fator.
    """
    acumulado: dict[tuple[TipoEixo, float], float] = {}
    for codigo, n in frota.items():
        if codigo not in VEICULOS:
            raise KeyError(f"Classe de veiculo desconhecida: {codigo!r}")
        v = VEICULOS[codigo]
        if ignorar_leves and v.categoria == Categoria.LEVE:
            continue
        for e in v.eixos:
            chave = (e.tipo, e.carga_tf * fator_carga)
            acumulado[chave] = acumulado.get(chave, 0.0) + n

    faixas = [FaixaCarga(tipo, carga, rep)
              for (tipo, carga), rep in sorted(
                  acumulado.items(), key=lambda kv: (kv[0][0].value, kv[0][1]))]
    return faixas


def classes_por_categoria(categoria: Categoria) -> list[str]:
    """Lista os codigos de classe de uma categoria (para montar a UI)."""
    return [c for c, v in VEICULOS.items() if v.categoria == categoria]


if __name__ == "__main__":
    # Smoke test: frota mista de um dia hipotetico.
    frota = {"P": 5000, "M": 800, "U": 600,      # leves (ignorados)
             "2CB": 120, "3CB": 40,              # onibus
             "2C": 300, "3C": 180, "2S3": 90, "3S3": 50}  # caminhoes
    esp = espectro_de_frota(frota)
    print("Espectro de eixos (leves ignorados):")
    for f in esp:
        print(f"  {f.eixo.value:14} carga={f.carga_tf:5.1f} t  ->  {f.repeticoes_previstas:8.0f} eixos")
    print(f"\nClasses de caminhao no catalogo: {classes_por_categoria(Categoria.CAMINHAO)}")
