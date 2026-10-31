from __future__ import annotations

import argparse

from src.relatorio import carregar_movimentacoes, gerar_relatorio


def criar_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Transforma movimentações em CSV em um relatório financeiro Excel."
    )
    parser.add_argument("arquivo", help="Caminho do arquivo CSV de entrada")
    parser.add_argument(
        "-o",
        "--saida",
        default="saida/relatorio_financeiro.xlsx",
        help="Caminho do relatório Excel",
    )
    return parser


def main() -> None:
    argumentos = criar_parser().parse_args()
    dados = carregar_movimentacoes(argumentos.arquivo)
    destino = gerar_relatorio(dados, argumentos.saida)
    print(f"Relatório gerado com sucesso: {destino.resolve()}")


if __name__ == "__main__":
    main()
