"""Prepara o dado: lê ``sales.csv`` bruto, limpa e grava ``vendas_limpo.csv``."""

from __future__ import annotations

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from data_pilot.dados import carregar_bruto, limpar_vendas, salvar_limpo


def main() -> None:
    bruto = RAIZ / "data" / "raw" / "sales.csv"
    limpo = RAIZ / "data" / "processed" / "vendas_limpo.csv"

    base, relatorio = limpar_vendas(carregar_bruto(bruto))
    salvar_limpo(base, limpo)

    print(f"bruto:   {relatorio.linhas_brutas} linhas")
    print(f"datas invalidas removidas:  {relatorio.removidas_data_invalida}")
    print(f"valores invalidos removidos: {relatorio.removidas_valor_invalido}")
    print(f"duplicadas removidas:       {relatorio.removidas_duplicadas}")
    print(f"limpo:   {relatorio.linhas_limpas} linhas -> {limpo}")


if __name__ == "__main__":
    main()
