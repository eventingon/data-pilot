"""Ferramentas expostas ao modelo e o roteador que as executa.

A ideia do agente sem framework:

1. Descrevemos cada métrica como uma ferramenta (``name``, ``description``,
   ``parameters``) no formato aceito pela API de chat completions.
2. O modelo, ao receber a pergunta, escolhe **qual** ferramenta chamar e com
   quais argumentos.
3. ``executar_ferramenta`` roda a função Python correspondente pelo nome e
   devolve o resultado. O modelo apenas *explica* o número — nunca o calcula.

A descrição de cada ferramenta é o que orienta a escolha do modelo; por isso ela
diz, em português, exatamente qual pergunta de negócio a função responde.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pandas as pd

from . import metricas

ERRO_FERRAMENTA = "ferramenta desconhecida"
MAX_CIDADES = 20


class ErroFerramenta(ValueError):
    """Chamada de ferramenta inválida (nome ou argumentos)."""


_CATEGORIA = {
    "type": "string",
    "description": (
        "Categoria de produto para filtrar. Use 'Todas' (padrão) para considerar a loja inteira."
    ),
}


def _ferramenta(nome: str, descricao: str, propriedades: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": nome,
            "description": descricao,
            "parameters": {
                "type": "object",
                "properties": propriedades,
                "additionalProperties": False,
            },
        },
    }


ESQUEMAS: list[dict[str, Any]] = [
    _ferramenta(
        "receita_total",
        "Soma da receita (em reais) de todos os pedidos CONCLUIDOS. Use quando a "
        "pergunta for sobre quanto a loja faturou, receita, faturamento ou vendas "
        "em dinheiro.",
        {"categoria": _CATEGORIA},
    ),
    _ferramenta(
        "total_pedidos",
        "Quantidade de pedidos CONCLUIDOS (pedidos distintos). Use para perguntas "
        "como 'quantos pedidos', 'quantas vendas'.",
        {"categoria": _CATEGORIA},
    ),
    _ferramenta(
        "ticket_medio",
        "Receita media por pedido concluido (receita total dividida pelo numero de "
        "pedidos concluidos). Use para 'ticket medio', 'valor medio por pedido'.",
        {"categoria": _CATEGORIA},
    ),
    _ferramenta(
        "clientes_unicos",
        "Numero de clientes distintos que fizeram pedidos CONCLUIDOS. Use para "
        "'quantos clientes', 'clientes unicos'.",
        {"categoria": _CATEGORIA},
    ),
    _ferramenta(
        "taxa_cancelamento",
        "Percentual (0 a 100) de pedidos cancelados sobre TODOS os pedidos. Use "
        "para 'taxa de cancelamento', 'quantos por cento cancelaram'.",
        {"categoria": _CATEGORIA},
    ),
    _ferramenta(
        "receita_media_por_cliente",
        "Receita concluida dividida pelo numero de clientes distintos. Use para "
        "'receita media por cliente', 'gasto medio por cliente'.",
        {"categoria": _CATEGORIA},
    ),
    _ferramenta(
        "top_cidades",
        "As N cidades com maior receita CONCLUIDA, em ordem decrescente. Use para "
        "'quais cidades vendem mais', 'top cidades', 'melhores cidades'.",
        {
            "n": {
                "type": "integer",
                "description": "Quantas cidades retornar (padrao 5).",
                "minimum": 1,
                "maximum": 20,
            },
            "categoria": _CATEGORIA,
        },
    ),
]

ARGUMENTOS_PERMITIDOS: dict[str, frozenset[str]] = {
    "receita_total": frozenset({"categoria"}),
    "total_pedidos": frozenset({"categoria"}),
    "ticket_medio": frozenset({"categoria"}),
    "clientes_unicos": frozenset({"categoria"}),
    "taxa_cancelamento": frozenset({"categoria"}),
    "receita_media_por_cliente": frozenset({"categoria"}),
    "top_cidades": frozenset({"n", "categoria"}),
}


def _categoria(argumentos: dict[str, Any]) -> str | None:
    return argumentos.get("categoria")


def _executar_receita_total(df: pd.DataFrame, args: dict[str, Any]) -> Any:
    return metricas.receita_total(df, _categoria(args))


def _executar_total_pedidos(df: pd.DataFrame, args: dict[str, Any]) -> Any:
    return metricas.total_pedidos(df, _categoria(args))


def _executar_ticket_medio(df: pd.DataFrame, args: dict[str, Any]) -> Any:
    return metricas.ticket_medio(df, _categoria(args))


def _executar_clientes_unicos(df: pd.DataFrame, args: dict[str, Any]) -> Any:
    return metricas.clientes_unicos(df, _categoria(args))


def _executar_taxa_cancelamento(df: pd.DataFrame, args: dict[str, Any]) -> Any:
    return metricas.taxa_cancelamento(df, _categoria(args))


def _executar_receita_media_por_cliente(df: pd.DataFrame, args: dict[str, Any]) -> Any:
    return metricas.receita_media_por_cliente(df, _categoria(args))


def _executar_top_cidades(df: pd.DataFrame, args: dict[str, Any]) -> Any:
    try:
        n = int(args.get("n", 5))
    except (TypeError, ValueError) as erro:
        raise ErroFerramenta("'n' deve ser inteiro.") from erro
    if not 1 <= n <= MAX_CIDADES:
        raise ErroFerramenta(f"'n' deve estar entre 1 e {MAX_CIDADES}.")
    tabela = metricas.top_cidades(df, n=n, categoria=_categoria(args))
    return tabela.to_dict(orient="records")


REGISTRO: dict[str, Callable[[pd.DataFrame, dict[str, Any]], Any]] = {
    "receita_total": _executar_receita_total,
    "total_pedidos": _executar_total_pedidos,
    "ticket_medio": _executar_ticket_medio,
    "clientes_unicos": _executar_clientes_unicos,
    "taxa_cancelamento": _executar_taxa_cancelamento,
    "receita_media_por_cliente": _executar_receita_media_por_cliente,
    "top_cidades": _executar_top_cidades,
}


def nomes_ferramentas() -> list[str]:
    """Nomes das ferramentas disponíveis (na ordem dos esquemas)."""
    return [esquema["function"]["name"] for esquema in ESQUEMAS]


def executar_ferramenta(
    nome: str, argumentos: dict[str, Any] | None, df: pd.DataFrame
) -> dict[str, Any]:
    """Executa a ferramenta ``nome`` sobre ``df`` e devolve um resultado serializável.

    Falha com :class:`ErroFerramenta` para nome desconhecido ou argumento fora do
    contrato — nunca "chuta" uma métrica diferente.
    """
    if nome not in REGISTRO:
        raise ErroFerramenta(f"{ERRO_FERRAMENTA}: {nome!r}. Disponíveis: {nomes_ferramentas()}.")
    argumentos = argumentos or {}
    permitidos = ARGUMENTOS_PERMITIDOS[nome]
    invalidos = sorted(set(argumentos) - permitidos)
    if invalidos:
        raise ErroFerramenta(
            f"argumentos não permitidos para {nome!r}: {invalidos}. Aceitos: {sorted(permitidos)}."
        )
    resultado = REGISTRO[nome](df, argumentos)
    return {"ferramenta": nome, "argumentos": argumentos, "resultado": resultado}
