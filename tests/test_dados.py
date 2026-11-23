"""Testes da camada de dados: limpeza, status e ida-e-volta do CSV."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from data_pilot.dados import (
    carregar_limpo,
    limpar_vendas,
    normalizar_status,
    salvar_limpo,
)


def _bruto() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "id_pedido": ["P1", "P1", "P2", "P3", "P4"],
            "data": [
                "2025-01-05",
                "2025-01-05",  # duplicata idêntica de P1
                "10/02/2025",  # formato dd/mm/aaaa
                "data-invalida",  # data inválida -> removida
                "2025-03-01",
            ],
            "cliente": ["C1", "C1", "C2", "C3", "C4"],
            "cidade": ["Palmas"] * 5,
            "categoria": ["A"] * 5,
            "produto": ["x"] * 5,
            "quantidade": [2, 2, 1, 3, 1],
            "preco_unitario": [100.0, 100.0, 50.0, 10.0, 0.0],  # P4 tem preço 0
            "status": ["Concluído", "Concluído", "FINALIZADO", "Cancelado", "Pendente"],
        }
    )


def test_limpeza_remove_duplicatas_data_e_valor_invalido() -> None:
    limpo, relatorio = limpar_vendas(_bruto())

    # P1 (duplicata), P3 (data inválida) e P4 (preço 0) saem.
    assert list(limpo["id_pedido"]) == ["P1", "P2"]
    assert relatorio.linhas_brutas == 5
    assert relatorio.removidas_duplicadas == 1
    assert relatorio.removidas_data_invalida == 1
    assert relatorio.removidas_valor_invalido == 1
    assert relatorio.linhas_limpas == 2


def test_receita_e_calculada_como_quantidade_vezes_preco() -> None:
    limpo, _ = limpar_vendas(_bruto())

    assert list(limpo["receita"]) == [200.0, 50.0]


def test_data_dd_mm_aaaa_e_convertida_com_dia_primeiro() -> None:
    limpo, _ = limpar_vendas(_bruto())

    assert limpo.loc[limpo["id_pedido"] == "P2", "data"].iloc[0] == pd.Timestamp("2025-02-10")


@pytest.mark.parametrize(
    ("entrada", "esperado"),
    [
        ("Concluído", "concluido"),
        ("CONCLUIDO", "concluido"),
        ("finalizado", "concluido"),
        ("Cancelado", "cancelado"),
        ("cancelada", "cancelado"),
        ("Pendente", "pendente"),
        ("algo estranho", "desconhecido"),
    ],
)
def test_normalizar_status(entrada: str, esperado: str) -> None:
    assert normalizar_status(entrada) == esperado


def test_colunas_finais_na_ordem_esperada() -> None:
    limpo, _ = limpar_vendas(_bruto())

    assert list(limpo.columns) == [
        "id_pedido",
        "data",
        "cliente",
        "cidade",
        "categoria",
        "produto",
        "quantidade",
        "preco_unitario",
        "status",
        "receita",
    ]


def test_salvar_e_carregar_preserva_valores(tmp_path: Path) -> None:
    limpo, _ = limpar_vendas(_bruto())
    destino = tmp_path / "limpo.csv"

    salvar_limpo(limpo, destino)
    texto = destino.read_text(encoding="utf-8")
    assert ";" in texto.splitlines()[0]  # separador ponto e vírgula
    assert "200,0" in texto  # decimal com vírgula

    recarregado = carregar_limpo(destino)
    assert recarregado["receita"].tolist() == limpo["receita"].tolist()
    assert recarregado["data"].tolist() == limpo["data"].tolist()


def test_carregar_limpo_arquivo_ausente_falha(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        carregar_limpo(tmp_path / "nao_existe.csv")
