"""Testes do laço de ferramentas do agente com um cliente falso (sem rede)."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pandas as pd
import pytest

from data_pilot.agente import ErroAgente, responder


def _tool_call(id_: str, nome: str, argumentos: str) -> SimpleNamespace:
    return SimpleNamespace(id=id_, function=SimpleNamespace(name=nome, arguments=argumentos))


def _resposta(
    content: str | None = None, tool_calls: list[SimpleNamespace] | None = None
) -> SimpleNamespace:
    mensagem = SimpleNamespace(content=content, tool_calls=tool_calls)
    return SimpleNamespace(choices=[SimpleNamespace(message=mensagem)])


class FakeCompletions:
    def __init__(self, respostas: list[SimpleNamespace]) -> None:
        self._respostas = list(respostas)
        self.chamadas: list[dict[str, Any]] = []

    def create(self, **kwargs: Any) -> SimpleNamespace:
        self.chamadas.append(kwargs)
        return self._respostas.pop(0)


class FakeCliente:
    def __init__(self, respostas: list[SimpleNamespace]) -> None:
        self.chat = SimpleNamespace(completions=FakeCompletions(respostas))


def test_executa_ferramenta_e_devolve_explicacao(vendas: pd.DataFrame) -> None:
    cliente = FakeCliente(
        [
            _resposta(tool_calls=[_tool_call("call-1", "receita_total", "{}")]),
            _resposta(content="A receita total foi R$ 550,00."),
        ]
    )

    resultado = responder("qual a receita?", vendas, cliente=cliente)

    assert resultado.resposta == "A receita total foi R$ 550,00."
    assert len(resultado.chamadas) == 1
    assert resultado.chamadas[0]["ferramenta"] == "receita_total"
    assert resultado.chamadas[0]["resultado"] == 550.0


def test_resultado_da_ferramenta_volta_como_mensagem_role_tool(vendas: pd.DataFrame) -> None:
    cliente = FakeCliente(
        [
            _resposta(tool_calls=[_tool_call("call-1", "receita_total", "{}")]),
            _resposta(content="ok"),
        ]
    )

    responder("receita?", vendas, cliente=cliente)

    segunda_chamada = cliente.chat.completions.chamadas[1]["messages"]
    mensagens_tool = [m for m in segunda_chamada if m["role"] == "tool"]
    assert len(mensagens_tool) == 1
    assert mensagens_tool[0]["tool_call_id"] == "call-1"
    assert "550" in mensagens_tool[0]["content"]


def test_resposta_direta_sem_ferramenta(vendas: pd.DataFrame) -> None:
    cliente = FakeCliente([_resposta(content="Olá! Como posso ajudar?")])

    resultado = responder("oi", vendas, cliente=cliente)

    assert resultado.resposta == "Olá! Como posso ajudar?"
    assert resultado.chamadas == []


def test_esquemas_e_modelo_sao_enviados(vendas: pd.DataFrame) -> None:
    cliente = FakeCliente([_resposta(content="ok")])

    responder("oi", vendas, cliente=cliente, modelo="openrouter/free")

    enviado = cliente.chat.completions.chamadas[0]
    assert enviado["model"] == "openrouter/free"
    assert enviado["tool_choice"] == "auto"
    assert enviado["tools"][0]["type"] == "function"


def test_limite_de_rodadas_e_respeitado(vendas: pd.DataFrame) -> None:
    cliente = FakeCliente(
        [
            _resposta(tool_calls=[_tool_call("c1", "receita_total", "{}")]),
            _resposta(tool_calls=[_tool_call("c2", "receita_total", "{}")]),
        ]
    )

    with pytest.raises(ErroAgente, match="máximo de rodadas"):
        responder("receita?", vendas, cliente=cliente, max_iteracoes=2)


def test_argumentos_json_invalido_viram_vazio(vendas: pd.DataFrame) -> None:
    cliente = FakeCliente(
        [
            _resposta(tool_calls=[_tool_call("c1", "receita_total", "isto não é json")]),
            _resposta(content="ok"),
        ]
    )

    resultado = responder("receita?", vendas, cliente=cliente)

    assert resultado.chamadas[0]["argumentos"] == {}
    assert resultado.chamadas[0]["resultado"] == 550.0


def test_pergunta_vazia_falha(vendas: pd.DataFrame) -> None:
    cliente = FakeCliente([])

    with pytest.raises(ValueError, match="pergunta vazia"):
        responder("   ", vendas, cliente=cliente)
