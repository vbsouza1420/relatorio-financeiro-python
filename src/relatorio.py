from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import BinaryIO

import pandas as pd
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter


COLUNAS_OBRIGATORIAS = {"data", "descricao", "categoria", "tipo", "valor"}
TIPOS_VALIDOS = {"receita", "despesa"}


def carregar_movimentacoes(caminho: str | Path | BinaryIO) -> pd.DataFrame:
    """Carrega e valida as movimentações de um arquivo CSV."""
    dados = pd.read_csv(caminho)
    dados.columns = dados.columns.str.strip().str.lower()

    faltantes = COLUNAS_OBRIGATORIAS - set(dados.columns)
    if faltantes:
        raise ValueError(f"Colunas obrigatórias ausentes: {', '.join(sorted(faltantes))}")

    dados = dados[list(COLUNAS_OBRIGATORIAS)].copy()
    dados["data"] = pd.to_datetime(dados["data"], errors="coerce")
    dados["valor"] = pd.to_numeric(dados["valor"], errors="coerce")
    dados["tipo"] = dados["tipo"].astype(str).str.strip().str.lower()
    dados["descricao"] = dados["descricao"].astype(str).str.strip()
    dados["categoria"] = dados["categoria"].astype(str).str.strip()

    if dados["data"].isna().any():
        raise ValueError("Existem datas inválidas no arquivo.")
    if dados["valor"].isna().any() or (dados["valor"] <= 0).any():
        raise ValueError("Todos os valores devem ser números positivos.")

    tipos_invalidos = set(dados["tipo"]) - TIPOS_VALIDOS
    if tipos_invalidos:
        raise ValueError(f"Tipos inválidos: {', '.join(sorted(tipos_invalidos))}")

    dados["duplicado"] = dados.duplicated(
        subset=["data", "descricao", "categoria", "tipo", "valor"], keep=False
    )
    dados["valor_assinado"] = dados["valor"].where(
        dados["tipo"].eq("receita"), -dados["valor"]
    )
    dados["mes"] = dados["data"].dt.to_period("M").astype(str)
    return dados.sort_values("data").reset_index(drop=True)


def calcular_resumo(dados: pd.DataFrame) -> dict[str, float | int]:
    receitas = dados.loc[dados["tipo"].eq("receita"), "valor"].sum()
    despesas = dados.loc[dados["tipo"].eq("despesa"), "valor"].sum()
    return {
        "Total de receitas": float(receitas),
        "Total de despesas": float(despesas),
        "Saldo": float(receitas - despesas),
        "Quantidade de lançamentos": int(len(dados)),
        "Possíveis duplicados": int(dados["duplicado"].sum()),
    }


def gerar_relatorio(dados: pd.DataFrame, destino: str | Path) -> Path:
    """Gera um relatório Excel com resumo e agrupamentos."""
    destino = Path(destino)
    destino.parent.mkdir(parents=True, exist_ok=True)

    with pd.ExcelWriter(destino, engine="openpyxl") as writer:
        _escrever_relatorio(dados, writer)

    return destino


def gerar_relatorio_bytes(dados: pd.DataFrame) -> bytes:
    """Gera o relatório em memória para download em aplicações web."""
    memoria = BytesIO()
    with pd.ExcelWriter(memoria, engine="openpyxl") as writer:
        _escrever_relatorio(dados, writer)
    return memoria.getvalue()


def _escrever_relatorio(dados: pd.DataFrame, writer: pd.ExcelWriter) -> None:
    resumo = pd.DataFrame(calcular_resumo(dados).items(), columns=["Indicador", "Valor"])
    por_categoria = (
        dados.groupby(["categoria", "tipo"], as_index=False)["valor"]
        .sum()
        .sort_values(["tipo", "valor"], ascending=[True, False])
    )
    por_mes = (
        dados.pivot_table(index="mes", columns="tipo", values="valor", aggfunc="sum", fill_value=0)
        .reset_index()
    )
    for coluna in TIPOS_VALIDOS:
        if coluna not in por_mes:
            por_mes[coluna] = 0.0
    por_mes["saldo"] = por_mes["receita"] - por_mes["despesa"]

    exportacao = dados.copy()
    exportacao["data"] = exportacao["data"].dt.date

    resumo.to_excel(writer, sheet_name="Resumo", index=False)
    exportacao.to_excel(writer, sheet_name="Movimentações", index=False)
    por_categoria.to_excel(writer, sheet_name="Por categoria", index=False)
    por_mes.to_excel(writer, sheet_name="Por mês", index=False)

    for planilha in writer.book.worksheets:
        _formatar_planilha(planilha)


def _formatar_planilha(planilha) -> None:
    cabecalho = PatternFill("solid", fgColor="1F4E78")
    for celula in planilha[1]:
        celula.fill = cabecalho
        celula.font = Font(color="FFFFFF", bold=True)
        celula.alignment = Alignment(horizontal="center")

    planilha.freeze_panes = "A2"
    planilha.auto_filter.ref = planilha.dimensions
    for coluna in planilha.columns:
        tamanho = min(max(len(str(celula.value or "")) for celula in coluna) + 2, 40)
        planilha.column_dimensions[get_column_letter(coluna[0].column)].width = tamanho

    for linha in planilha.iter_rows():
        for celula in linha:
            if isinstance(celula.value, float):
                celula.number_format = 'R$ #,##0.00'
