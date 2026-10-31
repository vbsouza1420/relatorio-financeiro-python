from pathlib import Path

import pandas as pd
import pytest

from src.relatorio import (
    calcular_resumo,
    carregar_movimentacoes,
    gerar_relatorio,
    gerar_relatorio_bytes,
)


EXEMPLO = Path("exemplos/movimentacoes.csv")


def test_calcula_totais_do_exemplo() -> None:
    dados = carregar_movimentacoes(EXEMPLO)
    resumo = calcular_resumo(dados)

    assert resumo["Total de receitas"] == pytest.approx(4530.0)
    assert resumo["Total de despesas"] == pytest.approx(570.30)
    assert resumo["Saldo"] == pytest.approx(3959.70)
    assert resumo["Quantidade de lançamentos"] == 8


def test_rejeita_colunas_ausentes(tmp_path: Path) -> None:
    arquivo = tmp_path / "invalido.csv"
    pd.DataFrame({"data": ["2026-01-01"], "valor": [100]}).to_csv(arquivo, index=False)

    with pytest.raises(ValueError, match="Colunas obrigatórias ausentes"):
        carregar_movimentacoes(arquivo)


def test_gera_todas_as_abas(tmp_path: Path) -> None:
    dados = carregar_movimentacoes(EXEMPLO)
    destino = gerar_relatorio(dados, tmp_path / "relatorio.xlsx")

    assert destino.exists()
    assert set(pd.ExcelFile(destino).sheet_names) == {
        "Resumo",
        "Movimentações",
        "Por categoria",
        "Por mês",
    }


def test_gera_relatorio_em_memoria() -> None:
    dados = carregar_movimentacoes(EXEMPLO)
    conteudo = gerar_relatorio_bytes(dados)

    assert conteudo[:2] == b"PK"
    assert len(conteudo) > 1_000
