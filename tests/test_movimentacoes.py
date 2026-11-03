import sqlite3

import pytest

from src.movimentacoes import (
    listar_entradas,
    listar_movimentacoes,
    listar_saidas,
    registrar_entrada,
    registrar_saida,
)


@pytest.fixture
def conexao():
    """
    Cria um banco SQLite em memória
    exclusivamente para os testes.
    """

    conn = sqlite3.connect(":memory:")

    conn.executescript(
        """
        CREATE TABLE produtos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            categoria_id INTEGER,
            preco REAL NOT NULL DEFAULT 0,
            quantidade INTEGER NOT NULL DEFAULT 0
        );

        CREATE TABLE entradas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            id_produto INTEGER NOT NULL,
            quantidade INTEGER NOT NULL,
            data_entrada TEXT NOT NULL,
            fornecedor TEXT NOT NULL,
            FOREIGN KEY (id_produto)
                REFERENCES produtos(id)
        );

        CREATE TABLE saidas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            id_produto INTEGER NOT NULL,
            quantidade INTEGER NOT NULL,
            data_saida TEXT NOT NULL,
            destinatario TEXT NOT NULL,
            FOREIGN KEY (id_produto)
                REFERENCES produtos(id)
        );

        INSERT INTO produtos
        (
            nome,
            preco,
            quantidade
        )
        VALUES
        (
            'Teclado',
            100.00,
            10
        );
        """
    )

    yield conn

    conn.close()


def saldo_produto(conexao, id_produto=1):
    """
    Consulta o saldo atual de um produto.
    """

    cursor = conexao.execute(
        """
        SELECT quantidade
        FROM produtos
        WHERE id = ?
        """,
        (id_produto,),
    )

    return cursor.fetchone()[0]


def test_registrar_entrada_aumenta_saldo(conexao):

    entrada_id = registrar_entrada(
        id_produto=1,
        quantidade=5,
        fornecedor="Fornecedor A",
        data_entrada="2026-10-27 10:00:00",
        conexao=conexao,
    )

    assert entrada_id == 1

    assert saldo_produto(conexao) == 15


def test_registrar_saida_reduz_saldo(conexao):

    saida_id = registrar_saida(
        id_produto=1,
        quantidade=4,
        destinatario="Setor de TI",
        data_saida="2026-10-27 11:00:00",
        conexao=conexao,
    )

    assert saida_id == 1

    assert saldo_produto(conexao) == 6


def test_saida_acima_do_saldo_e_bloqueada(conexao):

    with pytest.raises(
        ValueError,
        match="Estoque insuficiente",
    ):

        registrar_saida(
            id_produto=1,
            quantidade=11,
            destinatario="Setor de TI",
            conexao=conexao,
        )

    assert saldo_produto(conexao) == 10

    total_saidas = conexao.execute(
        """
        SELECT COUNT(*)
        FROM saidas
        """
    ).fetchone()[0]

    assert total_saidas == 0


def test_quantidade_zero_e_bloqueada(conexao):

    with pytest.raises(ValueError):

        registrar_entrada(
            id_produto=1,
            quantidade=0,
            fornecedor="Fornecedor A",
            conexao=conexao,
        )


def test_quantidade_negativa_e_bloqueada(conexao):

    with pytest.raises(ValueError):

        registrar_saida(
            id_produto=1,
            quantidade=-1,
            destinatario="Setor de TI",
            conexao=conexao,
        )


def test_produto_inexistente_e_bloqueado(conexao):

    with pytest.raises(
        ValueError,
        match="Produto não encontrado",
    ):

        registrar_entrada(
            id_produto=999,
            quantidade=1,
            fornecedor="Fornecedor A",
            conexao=conexao,
        )


def test_listar_entradas_e_saidas(conexao):

    registrar_entrada(
        id_produto=1,
        quantidade=2,
        fornecedor="Fornecedor A",
        data_entrada="2026-10-27 10:00:00",
        conexao=conexao,
    )

    registrar_saida(
        id_produto=1,
        quantidade=3,
        destinatario="Setor Comercial",
        data_saida="2026-10-27 11:00:00",
        conexao=conexao,
    )

    entradas = listar_entradas(
        conexao=conexao
    )

    saidas = listar_saidas(
        conexao=conexao
    )

    assert len(entradas) == 1

    assert entradas[0]["produto"] == "Teclado"

    assert entradas[0]["quantidade"] == 2

    assert len(saidas) == 1

    assert saidas[0]["produto"] == "Teclado"

    assert saidas[0]["quantidade"] == 3


def test_listar_historico_completo(conexao):

    registrar_entrada(
        id_produto=1,
        quantidade=2,
        fornecedor="Fornecedor A",
        data_entrada="2026-10-27 10:00:00",
        conexao=conexao,
    )

    registrar_saida(
        id_produto=1,
        quantidade=3,
        destinatario="Setor Comercial",
        data_saida="2026-10-27 11:00:00",
        conexao=conexao,
    )

    movimentacoes = listar_movimentacoes(
        conexao=conexao
    )

    assert len(movimentacoes) == 2

    assert movimentacoes[0]["tipo"] == "SAIDA"

    assert movimentacoes[1]["tipo"] == "ENTRADA"


def test_saldo_final_apos_entrada_e_saida(conexao):

    registrar_entrada(
        id_produto=1,
        quantidade=8,
        fornecedor="Fornecedor A",
        conexao=conexao,
    )

    registrar_saida(
        id_produto=1,
        quantidade=5,
        destinatario="Setor de TI",
        conexao=conexao,
    )

    assert saldo_produto(conexao) == 13