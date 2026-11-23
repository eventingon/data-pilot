"""Agente de conversa sobre as vendas, via OpenRouter — sem framework de agentes.

Fluxo (o mesmo que um framework esconderia):

1. Montamos ``messages`` (system + pergunta) e enviamos junto com ``tools``.
2. Se o modelo pedir ferramentas (``tool_calls``), executamos cada uma pelo nome
   em :mod:`data_pilot.ferramentas` e devolvemos o resultado como mensagem
   ``role=tool``.
3. Repetimos até o modelo responder em texto. A resposta final apenas explica os
   números que o Python calculou.

O cliente é injetável para permitir testes sem rede: qualquer objeto com
``chat.completions.create`` compatível com o SDK ``openai`` serve.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any

import pandas as pd

from .ferramentas import ESQUEMAS, executar_ferramenta

BASE_URL_PADRAO = "https://openrouter.ai/api/v1"
MODELO_PADRAO = "openrouter/free"

SYSTEM_PROMPT = (
    "Você é o Data Pilot, assistente de vendas de uma loja. Responda em "
    "português, de forma curta e objetiva. NUNCA invente ou calcule números por "
    "conta própria: use SEMPRE as ferramentas fornecidas para obter as métricas "
    "e apenas explique o resultado retornado. Formate valores em reais (R$). "
    "Se a pergunta envolver uma categoria, passe o parâmetro 'categoria'."
)


class ErroAgente(RuntimeError):
    """Falha de configuração ou de comunicação com o provedor do modelo."""


@dataclass
class ResultadoConversa:
    """Resposta final e rastro das ferramentas executadas."""

    resposta: str
    chamadas: list[dict[str, Any]] = field(default_factory=list)


def criar_cliente() -> Any:
    """Cria o cliente ``openai`` apontado para o OpenRouter.

    Requer ``OPENROUTER_API_KEY`` no ambiente (ou no ``.env`` carregado antes).
    """
    try:
        from openai import OpenAI
    except ModuleNotFoundError as erro:  # pragma: no cover - depende do ambiente
        raise ErroAgente("instale o SDK: pip install openai") from erro

    chave = os.getenv("OPENROUTER_API_KEY", "").strip()
    if not chave:
        raise ErroAgente(
            "OPENROUTER_API_KEY ausente. Copie .env.example para .env e preencha a chave."
        )
    return OpenAI(base_url=os.getenv("OPENROUTER_BASE_URL", BASE_URL_PADRAO), api_key=chave)


def _extrair_texto(mensagem: Any) -> str:
    conteudo = getattr(mensagem, "content", None)
    return conteudo.strip() if isinstance(conteudo, str) else ""


def responder(
    pergunta: str,
    df: pd.DataFrame,
    *,
    cliente: Any,
    modelo: str | None = None,
    max_iteracoes: int = 5,
) -> ResultadoConversa:
    """Responde uma pergunta em linguagem natural usando as ferramentas.

    ``cliente`` deve expor ``chat.completions.create(...)``. Em testes, use um
    cliente falso com respostas roteirizadas.
    """
    if not pergunta or not pergunta.strip():
        raise ValueError("pergunta vazia.")

    modelo = modelo or os.getenv("OPENROUTER_MODEL", MODELO_PADRAO)
    mensagens: list[dict[str, Any]] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": pergunta.strip()},
    ]
    chamadas: list[dict[str, Any]] = []

    for _ in range(max_iteracoes):
        resposta = cliente.chat.completions.create(
            model=modelo, messages=mensagens, tools=ESQUEMAS, tool_choice="auto"
        )
        mensagem = resposta.choices[0].message
        pedidos = getattr(mensagem, "tool_calls", None) or []

        if not pedidos:
            texto = _extrair_texto(mensagem)
            if not texto:
                raise ErroAgente("o modelo não retornou texto nem ferramentas.")
            return ResultadoConversa(resposta=texto, chamadas=chamadas)

        # Registra a mensagem do assistente com as chamadas para manter o histórico.
        mensagens.append(
            {
                "role": "assistant",
                "content": getattr(mensagem, "content", None),
                "tool_calls": [
                    {
                        "id": chamada.id,
                        "type": "function",
                        "function": {
                            "name": chamada.function.name,
                            "arguments": chamada.function.arguments,
                        },
                    }
                    for chamada in pedidos
                ],
            }
        )

        for chamada in pedidos:
            nome = chamada.function.name
            argumentos = _ler_argumentos(chamada.function.arguments)
            resultado = executar_ferramenta(nome, argumentos, df)
            chamadas.append(
                {"ferramenta": nome, "argumentos": argumentos, "resultado": resultado["resultado"]}
            )
            mensagens.append(
                {
                    "role": "tool",
                    "tool_call_id": chamada.id,
                    "name": nome,
                    "content": json.dumps(resultado, ensure_ascii=False),
                }
            )

    raise ErroAgente("o modelo excedeu o número máximo de rodadas de ferramentas.")


def _ler_argumentos(bruto: Any) -> dict[str, Any]:
    if isinstance(bruto, dict):
        return dict(bruto)
    if not bruto:
        return {}
    try:
        dados = json.loads(bruto)
    except (TypeError, json.JSONDecodeError):
        return {}
    return dados if isinstance(dados, dict) else {}
