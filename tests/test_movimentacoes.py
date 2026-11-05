"""Testes de integração das movimentações com o esquema oficial de banco.py.

Executar da raiz do projeto: python -m pytest tests/test_movimentacoes.py -v
O banco dos testes é SQLite em memória; o estoque.db real não é alterado.
"""

import sqlite3

import pytest

from src.banco import conectar, criar_tabelas, fechar_conexao
from src.movimentacoes import (
    registrar_entrada,
    registrar_saida,
    listar_movimentacoes,
    listar_entradas,
    listar_saidas,
)


@pytest.fixture
def conexao():
    conn = conectar(":memory:")
    criar_tabelas(conn)
    conn.execute("INSERT INTO categorias (nome) VALUES (?)", ("Informática",))
    conn.execute(
        """INSERT INTO produtos
           (codigo, nome, preco, estoque_minimo, estoque_atual, categoria_id)
           VALUES (?, ?, ?, ?, ?, ?)""",
        ("TEC-001", "Teclado", 100.0, 2, 10, 1),
    )
    conn.execute(
        """INSERT INTO produtos
           (codigo, nome, preco, estoque_minimo, estoque_atual, categoria_id)
           VALUES (?, ?, ?, ?, ?, ?)""",
        ("MOU-002", "Mouse", 50.0, 1, 0, 1),
    )
    conn.execute(
        "INSERT INTO fornecedores (nome) VALUES (?)", ("Fornecedor A",)
    )
    conn.execute(
        """INSERT INTO funcionarios (nome, login, senha_hash, perfil)
           VALUES (?, ?, ?, ?)""",
        ("Funcionário Teste", "teste", "hash_de_teste", "ESTOQUISTA"),
    )
    conn.commit()
    yield conn
    fechar_conexao(conn)


def saldo(conexao, produto_id=1):
    return conexao.execute(
        "SELECT estoque_atual FROM produtos WHERE id = ?", (produto_id,)
    ).fetchone()["estoque_atual"]


def movimentos_gravados(conexao):
    return conexao.execute("SELECT COUNT(*) FROM movimentacoes").fetchone()[0]


def test_entrada_aumenta_saldo_e_salva_historico(conexao):
    movimento_id = registrar_entrada(1, 5, fornecedor_id=1, funcionario_id=1, conexao=conexao)
    assert movimento_id > 0
    assert saldo(conexao) == 15
    registro = conexao.execute(
        "SELECT tipo, quantidade, fornecedor_id, funcionario_id FROM movimentacoes WHERE id = ?",
        (movimento_id,),
    ).fetchone()
    assert tuple(registro) == ("ENTRADA", 5, 1, 1)


def test_saida_reduz_saldo_e_grava_destinatario(conexao):
    movimento_id = registrar_saida(1, 4, "Setor TI", funcionario_id=1, conexao=conexao)
    assert saldo(conexao) == 6
    registro = conexao.execute(
        "SELECT tipo, quantidade, observacao FROM movimentacoes WHERE id = ?",
        (movimento_id,),
    ).fetchone()
    assert tuple(registro) == ("SAIDA", 4, "Destinatário: Setor TI")


def test_saida_acima_do_estoque_nao_altera_saldo_nem_historico(conexao):
    with pytest.raises(ValueError, match="Estoque insuficiente"):
        registrar_saida(1, 11, "Setor TI", conexao=conexao)
    assert saldo(conexao) == 10
    assert movimentos_gravados(conexao) == 0


def test_saida_igual_ao_saldo_zera_estoque(conexao):
    registrar_saida(1, 10, "Setor TI", conexao=conexao)
    assert saldo(conexao) == 0
    assert movimentos_gravados(conexao) == 1


@pytest.mark.parametrize("quantidade", [0, -1, 1.5, True, "3", None])
def test_quantidade_invalida_e_bloqueada(conexao, quantidade):
    with pytest.raises(ValueError, match="quantidade"):
        registrar_entrada(1, quantidade, conexao=conexao)
    with pytest.raises(ValueError, match="quantidade"):
        registrar_saida(1, quantidade, conexao=conexao)
    assert saldo(conexao) == 10
    assert movimentos_gravados(conexao) == 0


def test_produto_inexistente_e_bloqueado(conexao):
    with pytest.raises(ValueError, match="Produto não encontrado"):
        registrar_entrada(999, 1, conexao=conexao)
    with pytest.raises(ValueError, match="Produto não encontrado"):
        registrar_saida(999, 1, conexao=conexao)
    assert movimentos_gravados(conexao) == 0


def test_produto_inativo_e_bloqueado(conexao):
    conexao.execute("UPDATE produtos SET ativo = 0 WHERE id = 1")
    conexao.commit()
    with pytest.raises(ValueError, match="Produto inativo"):
        registrar_entrada(1, 1, conexao=conexao)
    with pytest.raises(ValueError, match="Produto inativo"):
        registrar_saida(1, 1, conexao=conexao)
    assert movimentos_gravados(conexao) == 0


def test_historico_entradas_e_saidas(conexao):
    registrar_entrada(1, 5, fornecedor_id=1, conexao=conexao)
    registrar_saida(1, 3, "Compras", conexao=conexao)
    historico = listar_movimentacoes(conexao=conexao)
    assert [item["tipo"] for item in historico] == ["SAIDA", "ENTRADA"]
    assert len(listar_entradas(conexao=conexao)) == 1
    assert len(listar_saidas(conexao=conexao)) == 1
    assert historico[0]["produto"] == "Teclado"


def test_historico_filtra_por_produto(conexao):
    registrar_entrada(1, 2, conexao=conexao)
    registrar_entrada(2, 3, conexao=conexao)
    assert len(listar_movimentacoes(produto_id=1, conexao=conexao)) == 1
    assert len(listar_movimentacoes(produto_id=2, conexao=conexao)) == 1
    assert len(listar_entradas(produto_id=1, conexao=conexao)) == 1
    assert listar_saidas(produto_id=1, conexao=conexao) == []


def test_saldo_final_apos_entrada_e_saida(conexao):
    registrar_entrada(1, 8, conexao=conexao)
    registrar_saida(1, 5, conexao=conexao)
    assert saldo(conexao) == 13
    assert movimentos_gravados(conexao) == 2


def test_fornecedor_inexistente_desfaz_entrada(conexao):
    with pytest.raises(sqlite3.IntegrityError):
        registrar_entrada(1, 5, fornecedor_id=999, conexao=conexao)
    assert saldo(conexao) == 10
    assert movimentos_gravados(conexao) == 0


def test_funcionario_inexistente_desfaz_saida(conexao):
    with pytest.raises(sqlite3.IntegrityError):
        registrar_saida(1, 3, funcionario_id=999, conexao=conexao)
    assert saldo(conexao) == 10
    assert movimentos_gravados(conexao) == 0
