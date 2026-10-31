from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from src.relatorio import calcular_resumo, carregar_movimentacoes, gerar_relatorio_bytes


st.set_page_config(
    page_title="Relatório Financeiro",
    page_icon="📊",
    layout="wide",
)

st.title("📊 Relatório Financeiro Automatizado")
st.write(
    "Envie suas movimentações em CSV para visualizar os indicadores e gerar um relatório Excel."
)

modelo = Path("exemplos/movimentacoes.csv").read_bytes()
st.download_button(
    "Baixar arquivo CSV de exemplo",
    data=modelo,
    file_name="modelo_movimentacoes.csv",
    mime="text/csv",
)

arquivo = st.file_uploader("Selecione o arquivo CSV", type=["csv"])

if arquivo is None:
    st.info("Use o arquivo de exemplo para conhecer o formato esperado.")
    st.stop()

try:
    dados = carregar_movimentacoes(arquivo)
except (ValueError, pd.errors.ParserError, UnicodeDecodeError) as erro:
    st.error(f"Não foi possível processar o arquivo: {erro}")
    st.stop()

resumo = calcular_resumo(dados)
coluna_1, coluna_2, coluna_3, coluna_4 = st.columns(4)
coluna_1.metric("Receitas", f"R$ {resumo['Total de receitas']:,.2f}")
coluna_2.metric("Despesas", f"R$ {resumo['Total de despesas']:,.2f}")
coluna_3.metric("Saldo", f"R$ {resumo['Saldo']:,.2f}")
coluna_4.metric("Lançamentos", resumo["Quantidade de lançamentos"])

if resumo["Possíveis duplicados"]:
    st.warning(f"Foram encontrados {resumo['Possíveis duplicados']} possíveis registros duplicados.")

aba_visao, aba_dados = st.tabs(["Visão geral", "Movimentações"])

with aba_visao:
    por_mes = dados.pivot_table(
        index="mes", columns="tipo", values="valor", aggfunc="sum", fill_value=0
    )
    por_categoria = (
        dados.groupby("categoria", as_index=False)["valor_assinado"].sum().set_index("categoria")
    )

    esquerda, direita = st.columns(2)
    with esquerda:
        st.subheader("Movimentação por mês")
        st.bar_chart(por_mes)
    with direita:
        st.subheader("Resultado por categoria")
        st.bar_chart(por_categoria)

with aba_dados:
    exibicao = dados.drop(columns=["mes"]).copy()
    st.dataframe(
        exibicao,
        use_container_width=True,
        hide_index=True,
        column_config={
            "data": st.column_config.DateColumn("Data", format="DD/MM/YYYY"),
            "valor": st.column_config.NumberColumn("Valor", format="R$ %.2f"),
            "valor_assinado": st.column_config.NumberColumn("Valor líquido", format="R$ %.2f"),
            "duplicado": st.column_config.CheckboxColumn("Possível duplicado"),
        },
    )

st.download_button(
    "Gerar e baixar relatório Excel",
    data=gerar_relatorio_bytes(dados),
    file_name="relatorio_financeiro.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    type="primary",
)
