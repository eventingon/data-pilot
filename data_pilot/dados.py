"""Camada de dados: carregar, limpar e salvar a base de vendas.

Decisões explícitas desta camada:

- Datas chegam em formatos mistos (ISO e ``dd/mm/aaaa``); são convertidas com
  ``dayfirst=True`` e datas inválidas são descartadas (e contadas), nunca
  silenciadas.
- ``status`` é reduzido a três valores canônicos: ``concluido``, ``cancelado`` e
  ``pendente`` (qualquer outro vira ``desconhecido``).
- Duplicatas são removidas por linha idêntica e por ``id_pedido`` (mantém a
  primeira ocorrência) — o mesmo pedido não entra duas vezes.
- ``receita = quantidade * preco_unitario`` é calculada aqui, uma única vez.

O arquivo limpo é gravado com ``;`` como separador e ``,`` como decimal, e
relido do mesmo jeito, conforme pede o desafio.
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

COLUNAS = [
    "id_pedido",
    "data",
    "cliente",
    "cidade",
    "categoria",
    "produto",
    "quantidade",
    "preco_unitario",
    "status",
    "receita",
]

STATUS_CONCLUIDO = "concluido"
STATUS_CANCELADO = "cancelado"
STATUS_PENDENTE = "pendente"
STATUS_DESCONHECIDO = "desconhecido"

_MAPA_STATUS = {
    "concluido": STATUS_CONCLUIDO,
    "finalizado": STATUS_CONCLUIDO,
    "entregue": STATUS_CONCLUIDO,
    "pago": STATUS_CONCLUIDO,
    "cancelado": STATUS_CANCELADO,
    "cancelada": STATUS_CANCELADO,
    "estornado": STATUS_CANCELADO,
    "pendente": STATUS_PENDENTE,
    "aberto": STATUS_PENDENTE,
    "em andamento": STATUS_PENDENTE,
}


@dataclass(frozen=True, slots=True)
class RelatorioLimpeza:
    """Contagens de reconciliação entre o dado bruto e o limpo."""

    linhas_brutas: int
    removidas_data_invalida: int
    removidas_valor_invalido: int
    removidas_duplicadas: int
    linhas_limpas: int


def _sem_acento(texto: str) -> str:
    decomposto = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in decomposto if not unicodedata.combining(c))


def normalizar_status(valor: object) -> str:
    """Reduz um status arbitrário a um dos valores canônicos."""
    chave = _sem_acento(str(valor)).strip().lower()
    return _MAPA_STATUS.get(chave, STATUS_DESCONHECIDO)


def _converter_datas(serie: pd.Series) -> pd.Series:
    """Converte ISO e ``dd/mm/aaaa`` sem ambiguidade.

    ``format="mixed"`` com ``dayfirst=True`` troca mês/dia em datas ISO, então
    tentamos o formato ISO primeiro e só depois o brasileiro. Datas que não
    casam com nenhum formato viram ``NaT`` (e são contadas na limpeza).
    """
    texto = serie.astype("string")
    resultado = pd.to_datetime(texto, errors="coerce", format="%Y-%m-%d")

    restantes = resultado.isna() & texto.notna()
    if bool(restantes.any()):
        brasileiro = pd.to_datetime(texto[restantes], errors="coerce", format="%d/%m/%Y")
        resultado.loc[restantes] = brasileiro

    restantes = resultado.isna() & texto.notna()
    if bool(restantes.any()):
        generico = pd.to_datetime(texto[restantes], errors="coerce", dayfirst=True)
        resultado.loc[restantes] = generico

    return resultado


def carregar_bruto(caminho: Path | str) -> pd.DataFrame:
    """Lê o ``sales.csv`` bruto (vírgula como separador)."""
    caminho = Path(caminho)
    if not caminho.is_file():
        raise FileNotFoundError(f"base não encontrada: {caminho}")
    return pd.read_csv(caminho)


def limpar_vendas(df: pd.DataFrame) -> tuple[pd.DataFrame, RelatorioLimpeza]:
    """Limpa a base bruta e devolve ``(base_limpa, relatório)``."""
    bruto = df.copy()
    bruto.columns = [str(coluna).strip() for coluna in bruto.columns]
    linhas_brutas = len(bruto)

    bruto["data"] = _converter_datas(bruto["data"])
    invalidas_data = int(bruto["data"].isna().sum())
    bruto = bruto.loc[bruto["data"].notna()].copy()

    for coluna in ("quantidade", "preco_unitario"):
        bruto[coluna] = pd.to_numeric(bruto[coluna], errors="coerce")
    invalido = (
        bruto[["quantidade", "preco_unitario"]].isna().any(axis=1)
        | bruto["quantidade"].le(0)
        | bruto["preco_unitario"].le(0)
    )
    invalidas_valor = int(invalido.sum())
    bruto = bruto.loc[~invalido].copy()

    bruto["status"] = bruto["status"].map(normalizar_status)
    bruto["receita"] = (bruto["quantidade"] * bruto["preco_unitario"]).round(2)

    antes = len(bruto)
    bruto = bruto.drop_duplicates()
    bruto = bruto.drop_duplicates(subset=["id_pedido"], keep="first")
    removidas_duplicadas = antes - len(bruto)

    limpo = (
        bruto.loc[:, COLUNAS]
        .sort_values(["data", "id_pedido"], kind="mergesort")
        .reset_index(drop=True)
    )
    limpo["quantidade"] = limpo["quantidade"].astype("int64")

    relatorio = RelatorioLimpeza(
        linhas_brutas=linhas_brutas,
        removidas_data_invalida=invalidas_data,
        removidas_valor_invalido=invalidas_valor,
        removidas_duplicadas=removidas_duplicadas,
        linhas_limpas=len(limpo),
    )
    return limpo, relatorio


def salvar_limpo(df: pd.DataFrame, caminho: Path | str) -> Path:
    """Grava o CSV limpo com ``;`` e decimal ``,`` e devolve o caminho."""
    caminho = Path(caminho)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    saida = df.copy()
    saida["data"] = saida["data"].dt.strftime("%Y-%m-%d")
    saida.to_csv(caminho, sep=";", decimal=",", index=False, encoding="utf-8")
    return caminho


def carregar_limpo(caminho: Path | str) -> pd.DataFrame:
    """Lê o CSV limpo reaproveitando ``;`` e ``,`` como decimal."""
    caminho = Path(caminho)
    if not caminho.is_file():
        raise FileNotFoundError(f"base limpa não encontrada: {caminho}")
    df = pd.read_csv(caminho, sep=";", decimal=",")
    df["data"] = pd.to_datetime(df["data"], errors="raise", format="%Y-%m-%d")
    df["quantidade"] = df["quantidade"].astype("int64")
    return df
