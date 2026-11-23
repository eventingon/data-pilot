"""Gera uma base sintética de vendas (``data/raw/sales.csv``) para o Data Pilot.

Dados 100% fictícios: nenhuma pessoa, CNPJ ou valor real. A base é *suja* de
propósito (datas em formatos diferentes, status com caixa/acento variados,
duplicatas) para que a camada de limpeza tenha trabalho real a fazer.
"""

from __future__ import annotations

import random
from pathlib import Path

import pandas as pd

CATEGORIAS = ["Eletronicos", "Moveis", "Vestuario", "Alimentos", "Livros"]
CIDADES = [
    "Palmas",
    "Araguaina",
    "Gurupi",
    "Porto Nacional",
    "Paraiso do Tocantins",
    "Colinas do Tocantins",
]
PRODUTOS = {
    "Eletronicos": ["Fone Bluetooth", "Monitor 24", "Teclado Mecanico", "Mouse Sem Fio"],
    "Moveis": ["Cadeira Escritorio", "Mesa Simples", "Estante", "Sofa 2 Lugares"],
    "Vestuario": ["Camiseta", "Jaqueta", "Tenis", "Bone"],
    "Alimentos": ["Cafe 500g", "Cesta Basica", "Chocolate", "Suco Natural"],
    "Livros": ["Python para Dados", "Estatistica Basica", "SQL Pratico", "IA Aplicada"],
}
# Variantes "sujas" de status; a limpeza deve canonicalizar.
STATUS_SUJOS = [
    "Concluído",
    "concluido",
    "CONCLUIDO",
    "finalizado",
    "Cancelado",
    "cancelado",
    "Pendente",
    "pendente",
]


def _data_suja(ano: int, mes: int, dia: int) -> str:
    """Devolve a data em um entre dois formatos, simulando planilha inconsistente."""
    if random.random() < 0.75:
        return f"{ano:04d}-{mes:02d}-{dia:02d}"
    return f"{dia:02d}/{mes:02d}/{ano:04d}"


def gerar(linhas: int = 240, semente: int = 42) -> pd.DataFrame:
    """Constrói a base bruta de vendas com ruído controlado."""
    random.seed(semente)
    registros: list[dict[str, object]] = []

    for indice in range(linhas):
        categoria = random.choice(CATEGORIAS)
        produto = random.choice(PRODUTOS[categoria])
        mes = random.randint(1, 12)
        dia = random.randint(1, 28)
        quantidade = random.randint(1, 5)
        preco = round(random.uniform(20, 900), 2)
        registros.append(
            {
                "id_pedido": f"PED-{indice + 1:04d}",
                "data": _data_suja(2025, mes, dia),
                "cliente": f"Cliente {random.randint(1, 90):03d}",
                "cidade": random.choice(CIDADES),
                "categoria": categoria,
                "produto": produto,
                "quantidade": quantidade,
                "preco_unitario": preco,
                "status": random.choice(STATUS_SUJOS),
            }
        )

    base = pd.DataFrame(registros)

    # Duplicatas idênticas (a limpeza deve remover) e um pedido repetido com os
    # mesmos dados — o ``drop_duplicates`` por ``id_pedido`` cobre os dois casos.
    duplicatas = base.sample(5, random_state=semente)
    return pd.concat([base, duplicatas], ignore_index=True)


def main() -> None:
    destino = Path(__file__).resolve().parents[1] / "data" / "raw" / "sales.csv"
    destino.parent.mkdir(parents=True, exist_ok=True)
    base = gerar()
    base.to_csv(destino, index=False)
    print(f"gravado: {destino} ({len(base)} linhas brutas)")


if __name__ == "__main__":
    main()
