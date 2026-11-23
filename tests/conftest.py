"""Fixtures compartilhadas dos testes do Data Pilot."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))
# Os scripts são módulos de topo (não um pacote); testes importam deles.
SCRIPTS = RAIZ / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))


@pytest.fixture
def vendas() -> pd.DataFrame:
    """Base limpa pequena com números conhecidos.

    Concluídos: P1 (200), P2 (50), P3 (300) -> receita 550, 3 pedidos.
    Cancelado: P4. Pendente: P5. Total de pedidos: 5 -> cancelamento 20%.
    """
    return pd.DataFrame(
        {
            "id_pedido": ["P1", "P2", "P3", "P4", "P5"],
            "data": pd.to_datetime(
                [
                    "2025-01-05",
                    "2025-01-10",
                    "2025-02-01",
                    "2025-02-05",
                    "2025-02-06",
                ]
            ),
            "cliente": ["C1", "C2", "C1", "C3", "C4"],
            "cidade": ["Palmas", "Palmas", "Gurupi", "Gurupi", "Palmas"],
            "categoria": ["A", "A", "B", "B", "A"],
            "produto": ["x", "x", "y", "y", "x"],
            "quantidade": [2, 1, 1, 1, 1],
            "preco_unitario": [100.0, 50.0, 300.0, 100.0, 100.0],
            "status": ["concluido", "concluido", "concluido", "cancelado", "pendente"],
            "receita": [200.0, 50.0, 300.0, 100.0, 100.0],
        }
    )
