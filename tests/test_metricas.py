"""Testes das métricas de negócio (números conhecidos da fixture ``vendas``)."""

from __future__ import annotations

import pandas as pd

from data_pilot.metricas import (
    clientes_unicos,
    receita_media_por_cliente,
    receita_por_mes,
    receita_total,
    taxa_cancelamento,
    ticket_medio,
    top_cidades,
    total_pedidos,
)


def test_receita_total_so_conta_concluidos(vendas: pd.DataFrame) -> None:
    assert receita_total(vendas) == 550.0


def test_total_pedidos_concluidos(vendas: pd.DataFrame) -> None:
    assert total_pedidos(vendas) == 3


def test_ticket_medio(vendas: pd.DataFrame) -> None:
    assert ticket_medio(vendas) == 183.33


def test_clientes_unicos(vendas: pd.DataFrame) -> None:
    assert clientes_unicos(vendas) == 2


def test_taxa_cancelamento_usa_total_de_pedidos(vendas: pd.DataFrame) -> None:
    # 1 cancelado em 5 pedidos = 20%
    assert taxa_cancelamento(vendas) == 20.0


def test_receita_media_por_cliente(vendas: pd.DataFrame) -> None:
    # 550 / 2 clientes distintos
    assert receita_media_por_cliente(vendas) == 275.0


def test_filtro_por_categoria(vendas: pd.DataFrame) -> None:
    assert receita_total(vendas, "A") == 250.0
    assert total_pedidos(vendas, "A") == 2
    assert ticket_medio(vendas, "A") == 125.0
    assert taxa_cancelamento(vendas, "A") == 0.0


def test_receita_por_mes_ordenada(vendas: pd.DataFrame) -> None:
    mensal = receita_por_mes(vendas)

    assert list(mensal["mes"]) == ["2025-01", "2025-02"]
    assert list(mensal["receita"]) == [250.0, 300.0]


def test_top_cidades_por_receita_concluida(vendas: pd.DataFrame) -> None:
    cidades = top_cidades(vendas, n=5)

    assert list(cidades["cidade"]) == ["Gurupi", "Palmas"]
    assert list(cidades["receita"]) == [300.0, 250.0]


def test_top_cidades_limita_n(vendas: pd.DataFrame) -> None:
    cidades = top_cidades(vendas, n=1)

    assert len(cidades) == 1
    assert cidades.iloc[0]["cidade"] == "Gurupi"


def test_metricas_com_base_vazia_nao_quebram(vendas: pd.DataFrame) -> None:
    vazio = vendas.iloc[0:0]

    assert receita_total(vazio) == 0.0
    assert total_pedidos(vazio) == 0
    assert ticket_medio(vazio) == 0.0
    assert taxa_cancelamento(vazio) == 0.0
    assert receita_por_mes(vazio).empty
    assert top_cidades(vazio).empty
