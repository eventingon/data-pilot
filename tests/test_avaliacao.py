"""Testes do avaliador de escolha de ferramentas, com clientes falsos (sem rede)."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pandas as pd
import pytest
from avaliar_ferramentas import CASOS, Caso, avaliar, main, resumir

from data_pilot.agente import ErroAgente
from data_pilot.ferramentas import nomes_ferramentas


def _tool_call(id_: str, nome: str, argumentos: str) -> SimpleNamespace:
    return SimpleNamespace(id=id_, function=SimpleNamespace(name=nome, arguments=argumentos))


def _resposta(
    content: str | None = None, tool_calls: list[SimpleNamespace] | None = None
) -> SimpleNamespace:
    mensagem = SimpleNamespace(content=content, tool_calls=tool_calls)
    return SimpleNamespace(choices=[SimpleNamespace(message=mensagem)])


class ClienteRoteirizado:
    """Escolhe a ferramenta a partir de um mapa pergunta -> (nome, argumentos)."""

    def __init__(
        self, escolhas: dict[str, tuple[str, str]], falhar_em: set[str] | None = None
    ) -> None:
        self._escolhas = escolhas
        self._falhar_em = falhar_em or set()
        self._ja_executou: set[str] = set()
        self.chat = SimpleNamespace(completions=self)

    def create(self, **kwargs: Any) -> SimpleNamespace:
        pergunta = next(
            (m["content"] for m in reversed(kwargs["messages"]) if m["role"] == "user"), ""
        )
        if pergunta in self._falhar_em:
            raise ErroAgente("limite de uso do modelo gratuito")

        if pergunta in self._ja_executou:
            return _resposta(content=f"resposta para: {pergunta}")

        self._ja_executou.add(pergunta)
        nome, argumentos = self._escolhas.get(pergunta, ("receita_total", "{}"))
        return _resposta(tool_calls=[_tool_call("call-1", nome, argumentos)])


def _mapa_perfeito() -> dict[str, tuple[str, str]]:
    return {
        caso.pergunta: (caso.ferramenta, json.dumps(dict(caso.argumentos), ensure_ascii=False))
        for caso in CASOS
    }


def test_casos_so_usam_ferramentas_existentes() -> None:
    disponiveis = set(nomes_ferramentas())
    assert {caso.ferramenta for caso in CASOS} <= disponiveis


def test_casos_tem_perguntas_unicas() -> None:
    perguntas = [caso.pergunta for caso in CASOS]
    assert len(perguntas) == len(set(perguntas))


def test_modelo_perfeito_acerta_tudo(vendas: pd.DataFrame) -> None:
    resultados = avaliar(vendas, ClienteRoteirizado(_mapa_perfeito()))

    resumo = resumir(resultados)
    assert resumo["executados"] == len(CASOS)
    assert resumo["acertos_ferramenta"] == len(CASOS)
    assert resumo["acertos_argumentos"] == len(CASOS)
    assert resumo["taxa_argumentos"] == 100.0
    assert resumo["erros"] == []


def test_modelo_que_sempre_usa_receita_total_e_medido_como_falha(vendas: pd.DataFrame) -> None:
    escolhas = {"Qual a receita média por cliente?": ("receita_total", "{}")}
    resultados = avaliar(vendas, ClienteRoteirizado(escolhas), casos=[CASOS[5]])

    resumo = resumir(resultados)
    assert resumo["acertos_ferramenta"] == 0
    assert resumo["erros"][0]["escolhida"] == "receita_total"
    assert resumo["erros"][0]["pergunta"] == escolhas.popitem()[0]


def test_argumentos_diferentes_contam_como_parcial(vendas: pd.DataFrame) -> None:
    caso = Caso("Quais as 3 cidades que mais vendem?", "top_cidades", {"n": 3})
    resultados = avaliar(
        vendas, ClienteRoteirizado({caso.pergunta: ("top_cidades", '{"n": 5}')}), casos=[caso]
    )

    assert resultados[0].acertou_ferramenta is True
    assert resultados[0].acertou_argumentos is False
    assert resumir(resultados)["acertos_argumentos"] == 0


def test_falha_do_provedor_nao_infla_o_denominador(vendas: pd.DataFrame) -> None:
    caso = CASOS[0]
    cliente = ClienteRoteirizado({}, falhar_em={caso.pergunta})

    resumo = resumir(avaliar(vendas, cliente, casos=[caso]))

    assert resumo["casos"] == 1
    assert resumo["executados"] == 0
    assert resumo["falhas_provedor"] == 1
    assert resumo["taxa_ferramenta"] == 0.0


def test_main_grava_json_e_respeita_estrito(
    tmp_path: Path, vendas: pd.DataFrame, monkeypatch: pytest.MonkeyPatch
) -> None:
    destino = tmp_path / "limpo.csv"
    vendas.to_csv(destino, sep=";", decimal=",", index=False)

    monkeypatch.setattr(
        "avaliar_ferramentas.criar_cliente", lambda: ClienteRoteirizado(_mapa_perfeito())
    )
    saida = tmp_path / "relatorio.json"

    codigo = main(["--dados", str(destino), "--json", str(saida), "--estrito"])

    assert codigo == 0
    dados = json.loads(saida.read_text(encoding="utf-8"))
    assert dados["taxa_ferramenta"] == 100.0


def test_main_falha_sem_base(tmp_path: Path) -> None:
    assert main(["--dados", str(tmp_path / "nao_existe.csv")]) == 2


def test_main_avisa_quando_falta_a_chave(
    tmp_path: Path, vendas: pd.DataFrame, monkeypatch: pytest.MonkeyPatch
) -> None:
    destino = tmp_path / "limpo.csv"
    vendas.to_csv(destino, sep=";", decimal=",", index=False)

    def sem_chave() -> Any:
        raise ErroAgente("OPENROUTER_API_KEY ausente.")

    monkeypatch.setattr("avaliar_ferramentas.criar_cliente", sem_chave)

    assert main(["--dados", str(destino)]) == 2
