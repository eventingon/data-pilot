"""Mede se o modelo escolhe a ferramenta certa para perguntas fixas.

Por que isso existe: o modelo não vê o Python, só ``name``, ``description`` e
``parameters`` de cada ferramenta. Então a "qualidade da descrição" é uma
hipótese testável — este script roda uma lista fixa de perguntas e mostra, para
cada uma, qual ferramenta o modelo escolheu de fato.

Uso::

    python scripts/avaliar_ferramentas.py
    python scripts/avaliar_ferramentas.py --modelo openrouter/free --json saida.json
    python scripts/avaliar_ferramentas.py --estrito   # falha se errar qualquer caso

O script faz chamadas reais ao provedor (precisa de ``OPENROUTER_API_KEY``); as
funções ``avaliar`` e ``resumir`` são puras o bastante para serem testadas com um
cliente falso, sem rede.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from data_pilot.agente import ErroAgente, criar_cliente, responder
from data_pilot.dados import carregar_limpo
from data_pilot.ferramentas import nomes_ferramentas

LIMPO_PADRAO = RAIZ / "data" / "processed" / "vendas_limpo.csv"


@dataclass(frozen=True)
class Caso:
    """Uma pergunta com a ferramenta (e argumentos) que deveriam ser escolhidos."""

    pergunta: str
    ferramenta: str
    argumentos: Mapping[str, Any] = field(default_factory=dict)


@dataclass
class Resultado:
    """O que o modelo escolheu para um caso."""

    caso: Caso
    escolhida: str | None
    argumentos: Mapping[str, Any]
    resposta: str
    erro: str | None = None

    @property
    def acertou_ferramenta(self) -> bool:
        return self.escolhida == self.caso.ferramenta

    @property
    def acertou_argumentos(self) -> bool:
        return self.acertou_ferramenta and dict(self.argumentos) == dict(self.caso.argumentos)


CASOS: list[Caso] = [
    Caso("Qual foi a receita total?", "receita_total"),
    Caso("Quantos pedidos concluídos nós tivemos?", "total_pedidos"),
    Caso("Qual é o ticket médio da loja?", "ticket_medio"),
    Caso("Quantos clientes únicos compraram?", "clientes_unicos"),
    Caso("Qual a taxa de cancelamento?", "taxa_cancelamento"),
    Caso("Qual a receita média por cliente?", "receita_media_por_cliente"),
    Caso("Quanto cada cliente gasta em média?", "receita_media_por_cliente"),
    Caso("Quais as 3 cidades que mais vendem?", "top_cidades", {"n": 3}),
    Caso("Qual a receita de Eletronicos?", "receita_total", {"categoria": "Eletronicos"}),
    Caso(
        "Qual a receita média por cliente em Livros?",
        "receita_media_por_cliente",
        {"categoria": "Livros"},
    ),
]


def avaliar(
    df: pd.DataFrame,
    cliente: Any,
    casos: Sequence[Caso] = tuple(CASOS),
    *,
    modelo: str | None = None,
) -> list[Resultado]:
    """Roda cada caso e registra a ferramenta escolhida pelo modelo."""
    resultados: list[Resultado] = []
    for caso in casos:
        try:
            conversa = responder(caso.pergunta, df, cliente=cliente, modelo=modelo)
        except (ErroAgente, ValueError) as erro:
            # Falha do provedor (limite do modelo gratuito, por exemplo) não é
            # erro de escolha: registra-se à parte, sem inflar o acerto.
            resultados.append(
                Resultado(
                    caso=caso,
                    escolhida=None,
                    argumentos={},
                    resposta="",
                    erro=str(erro),
                )
            )
            continue

        primeira = conversa.chamadas[0] if conversa.chamadas else None
        resultados.append(
            Resultado(
                caso=caso,
                escolhida=primeira["ferramenta"] if primeira else None,
                argumentos=(primeira or {}).get("argumentos", {}),
                resposta=conversa.resposta,
            )
        )
    return resultados


def resumir(resultados: Sequence[Resultado]) -> dict[str, Any]:
    """Contagens de acerto, separando falha de escolha de falha do provedor."""
    executados = [r for r in resultados if r.erro is None]
    acertos = [r for r in executados if r.acertou_ferramenta]
    acertos_argumentos = [r for r in executados if r.acertou_argumentos]
    total = len(executados)
    return {
        "casos": len(resultados),
        "executados": total,
        "acertos_ferramenta": len(acertos),
        "taxa_ferramenta": round(100 * len(acertos) / total, 1) if total else 0.0,
        "acertos_argumentos": len(acertos_argumentos),
        "taxa_argumentos": round(100 * len(acertos_argumentos) / total, 1) if total else 0.0,
        "falhas_provedor": len(resultados) - total,
        "erros": [
            {"pergunta": r.caso.pergunta, "escolhida": r.escolhida, "erro": r.erro}
            for r in resultados
            if not r.acertou_ferramenta
        ],
    }


def _formatar(resultado: Resultado) -> str:
    if resultado.erro is not None:
        return f"ERRO   {resultado.caso.pergunta} -> provedor: {resultado.erro}"
    marca = (
        "OK    "
        if resultado.acertou_argumentos
        else ("PARCIAL" if resultado.acertou_ferramenta else "FALHOU")
    )
    obtida = resultado.escolhida or "(nenhuma)"
    esperada = resultado.caso.ferramenta
    return f"{marca:<7} {resultado.caso.pergunta} -> esperada={esperada} obtida={obtida}"


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dados", type=Path, default=LIMPO_PADRAO, help="CSV limpo a usar")
    parser.add_argument("--modelo", default=None, help="modelo do OpenRouter (padrão do .env)")
    parser.add_argument(
        "--json", type=Path, default=None, help="grava também um JSON com o relatório"
    )
    parser.add_argument(
        "--estrito", action="store_true", help="sai com código 1 se algum caso não acertar"
    )
    args = parser.parse_args(argv)

    if not args.dados.is_file():
        print(f"base nao encontrada: {args.dados}", file=sys.stderr)
        return 2

    df = carregar_limpo(args.dados)
    try:
        cliente = criar_cliente()
    except ErroAgente as erro:
        print(f"nao foi possivel criar o cliente do modelo: {erro}", file=sys.stderr)
        return 2
    resultados = avaliar(df, cliente, modelo=args.modelo)

    for resultado in resultados:
        print(_formatar(resultado))

    resumo = resumir(resultados)
    print()
    print(f"ferramentas disponiveis: {', '.join(nomes_ferramentas())}")
    print(
        f"ferramenta correta: {resumo['acertos_ferramenta']}/{resumo['executados']} "
        f"({resumo['taxa_ferramenta']}%)"
    )
    print(
        f"argumentos corretos: {resumo['acertos_argumentos']}/{resumo['executados']} "
        f"({resumo['taxa_argumentos']}%)"
    )
    if resumo["falhas_provedor"]:
        print(
            f"falhas do provedor (nao contadas como erro de escolha): {resumo['falhas_provedor']}"
        )

    if args.json is not None:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(resumo, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"relatorio gravado em {args.json}")

    if args.estrito and resumo["acertos_argumentos"] < resumo["executados"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
