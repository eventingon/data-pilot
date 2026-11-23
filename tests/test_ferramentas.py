"""Testes do contrato das ferramentas e do roteador (sem modelo, sem rede)."""

from __future__ import annotations

import pandas as pd
import pytest

from data_pilot.ferramentas import (
    ESQUEMAS,
    ErroFerramenta,
    executar_ferramenta,
    nomes_ferramentas,
)


def test_todos_os_esquemas_tem_nome_descricao_e_parametros() -> None:
    for esquema in ESQUEMAS:
        funcao = esquema["function"]
        assert esquema["type"] == "function"
        assert funcao["name"]
        assert funcao["description"]
        assert funcao["parameters"]["type"] == "object"


def test_registro_cobre_exatamente_os_esquemas() -> None:
    assert nomes_ferramentas() == [
        "receita_total",
        "total_pedidos",
        "ticket_medio",
        "clientes_unicos",
        "taxa_cancelamento",
        "receita_media_por_cliente",
        "top_cidades",
    ]


def test_executar_receita_total(vendas: pd.DataFrame) -> None:
    resultado = executar_ferramenta("receita_total", {}, vendas)

    assert resultado == {
        "ferramenta": "receita_total",
        "argumentos": {},
        "resultado": 550.0,
    }


def test_executar_com_filtro_de_categoria(vendas: pd.DataFrame) -> None:
    resultado = executar_ferramenta("receita_total", {"categoria": "A"}, vendas)

    assert resultado["resultado"] == 250.0


def test_top_cidades_devolve_lista_de_registros(vendas: pd.DataFrame) -> None:
    resultado = executar_ferramenta("top_cidades", {"n": 1}, vendas)

    assert resultado["resultado"] == [{"cidade": "Gurupi", "receita": 300.0}]


def test_ferramenta_desconhecida_falha(vendas: pd.DataFrame) -> None:
    with pytest.raises(ErroFerramenta, match="ferramenta desconhecida"):
        executar_ferramenta("lucro_total", {}, vendas)


def test_argumento_nao_permitido_falha(vendas: pd.DataFrame) -> None:
    with pytest.raises(ErroFerramenta, match="não permitidos"):
        executar_ferramenta("receita_total", {"periodo": "2025"}, vendas)


def test_top_cidades_com_n_invalido_falha(vendas: pd.DataFrame) -> None:
    with pytest.raises(ErroFerramenta, match="entre 1 e 20"):
        executar_ferramenta("top_cidades", {"n": 0}, vendas)
