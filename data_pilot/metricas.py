"""Métricas de negócio do Data Pilot.

Cada função responde a **uma** pergunta, é pura (não lê arquivo nem rede) e
opera sobre a base já limpa. Regra central: as métricas de receita usam apenas
pedidos **concluídos**. A taxa de cancelamento é a exceção natural — ela precisa
do total de pedidos para ter denominador.
"""

from __future__ import annotations

import pandas as pd

from .dados import STATUS_CANCELADO, STATUS_CONCLUIDO

TODAS_AS_CATEGORIAS = "Todas"


def filtrar_categoria(df: pd.DataFrame, categoria: str | None = None) -> pd.DataFrame:
    """Filtra por categoria; ``None`` ou ``'Todas'`` mantém a base inteira."""
    if categoria is None or categoria == TODAS_AS_CATEGORIAS:
        return df
    return df.loc[df["categoria"] == categoria]


def _concluidos(df: pd.DataFrame) -> pd.DataFrame:
    return df.loc[df["status"] == STATUS_CONCLUIDO]


def receita_total(df: pd.DataFrame, categoria: str | None = None) -> float:
    """Soma da receita dos pedidos concluídos."""
    base = _concluidos(filtrar_categoria(df, categoria))
    return round(float(base["receita"].sum()), 2)


def total_pedidos(df: pd.DataFrame, categoria: str | None = None) -> int:
    """Quantidade de pedidos concluídos (por ``id_pedido``)."""
    base = _concluidos(filtrar_categoria(df, categoria))
    return int(base["id_pedido"].nunique())


def ticket_medio(df: pd.DataFrame, categoria: str | None = None) -> float:
    """Receita média por pedido concluído."""
    pedidos = total_pedidos(df, categoria)
    if pedidos == 0:
        return 0.0
    return round(receita_total(df, categoria) / pedidos, 2)


def clientes_unicos(df: pd.DataFrame, categoria: str | None = None) -> int:
    """Quantidade de clientes distintos que compraram (concluído)."""
    base = _concluidos(filtrar_categoria(df, categoria))
    return int(base["cliente"].nunique())


def taxa_cancelamento(df: pd.DataFrame, categoria: str | None = None) -> float:
    """Percentual de pedidos cancelados sobre o total de pedidos (0 a 100)."""
    base = filtrar_categoria(df, categoria)
    total = int(base["id_pedido"].nunique())
    if total == 0:
        return 0.0
    cancelados = int(base.loc[base["status"] == STATUS_CANCELADO, "id_pedido"].nunique())
    return round(100 * cancelados / total, 2)


def receita_media_por_cliente(df: pd.DataFrame, categoria: str | None = None) -> float:
    """Receita concluída dividida pelo número de clientes distintos."""
    clientes = clientes_unicos(df, categoria)
    if clientes == 0:
        return 0.0
    return round(receita_total(df, categoria) / clientes, 2)


def receita_por_mes(df: pd.DataFrame, categoria: str | None = None) -> pd.DataFrame:
    """Receita concluída por mês, ordenada, no formato ``AAAA-MM``."""
    base = _concluidos(filtrar_categoria(df, categoria)).copy()
    if base.empty:
        return pd.DataFrame(
            {"mes": pd.Series(dtype="string"), "receita": pd.Series(dtype="float64")}
        )
    base["mes"] = base["data"].dt.strftime("%Y-%m")
    agrupado = (
        base.groupby("mes", as_index=False)["receita"]
        .sum()
        .sort_values("mes", kind="mergesort")
        .reset_index(drop=True)
    )
    agrupado["receita"] = agrupado["receita"].round(2)
    return agrupado


def top_cidades(df: pd.DataFrame, n: int = 5, categoria: str | None = None) -> pd.DataFrame:
    """As ``n`` cidades com maior receita concluída, em ordem decrescente."""
    base = _concluidos(filtrar_categoria(df, categoria))
    if base.empty:
        return pd.DataFrame(
            {"cidade": pd.Series(dtype="string"), "receita": pd.Series(dtype="float64")}
        )
    agrupado = (
        base.groupby("cidade", as_index=False)["receita"]
        .sum()
        .sort_values(["receita", "cidade"], ascending=[False, True], kind="mergesort")
        .head(n)
        .reset_index(drop=True)
    )
    agrupado["receita"] = agrupado["receita"].round(2)
    return agrupado
