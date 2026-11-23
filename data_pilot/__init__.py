"""Data Pilot — painel de vendas em Python com chat sobre os dados.

O Python calcula (limpeza e métricas); a IA apenas explica, escolhendo qual
ferramenta chamar.
"""

from .agente import ResultadoConversa, criar_cliente, responder
from .dados import (
    RelatorioLimpeza,
    carregar_bruto,
    carregar_limpo,
    limpar_vendas,
    normalizar_status,
    salvar_limpo,
)
from .ferramentas import ESQUEMAS, ErroFerramenta, executar_ferramenta, nomes_ferramentas
from .metricas import (
    clientes_unicos,
    receita_media_por_cliente,
    receita_por_mes,
    receita_total,
    taxa_cancelamento,
    ticket_medio,
    top_cidades,
    total_pedidos,
)

__all__ = [
    "ESQUEMAS",
    "ErroFerramenta",
    "RelatorioLimpeza",
    "ResultadoConversa",
    "carregar_bruto",
    "carregar_limpo",
    "clientes_unicos",
    "criar_cliente",
    "executar_ferramenta",
    "limpar_vendas",
    "nomes_ferramentas",
    "normalizar_status",
    "receita_media_por_cliente",
    "receita_por_mes",
    "receita_total",
    "responder",
    "salvar_limpo",
    "taxa_cancelamento",
    "ticket_medio",
    "top_cidades",
    "total_pedidos",
]
