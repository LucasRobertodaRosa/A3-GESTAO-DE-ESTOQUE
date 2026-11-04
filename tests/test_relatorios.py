"""Testes dos relatórios (src/relatorios.py).

Usa um banco SQLite em memória, então não mexe no estoque.db real.
Rodar na raiz do projeto:  python -m pytest tests/test_relatorios.py
"""

import pytest

from src.banco import conectar, criar_tabelas, fechar_conexao
from src.relatorios import (
    indicadores_gerais,
    movimentacoes_por_periodo,
    movimentacoes_por_produto,
    produtos_estoque_baixo,
    produtos_sem_estoque,
    relatorio_estoque,
)


def _movimentar(conn, produto_id, tipo, quantidade, data_hora):
    """Registra a movimentação e ajusta o saldo, como o módulo de movimentações."""
    conn.execute(
        "INSERT INTO movimentacoes (produto_id, tipo, quantidade, data_hora) "
        "VALUES (?, ?, ?, ?)",
        (produto_id, tipo, quantidade, data_hora),
    )
    sinal = 1 if tipo == "ENTRADA" else -1
    conn.execute(
        "UPDATE produtos SET estoque_atual = estoque_atual + ? WHERE id = ?",
        (sinal * quantidade, produto_id),
    )


@pytest.fixture
def conexao():
    """Cenário fixo.

    Produto 1 Água       (mín 10): entra 20, sai 15 -> saldo 5   (BAIXO)
    Produto 2 Detergente (mín  5): entra 10, sai 10 -> saldo 0   (SEM ESTOQUE)
    Produto 3 Suco       (mín  3): entra  8         -> saldo 8   (OK)
    Produto 4 Antigo     (inativo, saldo 0, sem movimentações)
    """
    conn = conectar(":memory:")
    criar_tabelas(conn)
    conn.execute("INSERT INTO categorias (nome) VALUES ('Bebidas'), ('Limpeza')")
    conn.execute(
        "INSERT INTO produtos (codigo, nome, preco, estoque_minimo, categoria_id, ativo) "
        "VALUES ('A1', 'Água', 2.5, 10, 1, 1), "
        "       ('D1', 'Detergente', 4.0, 5, 2, 1), "
        "       ('S1', 'Suco', 6.0, 3, 1, 1), "
        "       ('X1', 'Antigo', 1.0, 5, 2, 0)"
    )
    _movimentar(conn, 1, "ENTRADA", 20, "2026-10-01 10:00:00")
    _movimentar(conn, 1, "SAIDA", 15, "2026-10-05 09:00:00")
    _movimentar(conn, 2, "ENTRADA", 10, "2026-10-02 11:00:00")
    _movimentar(conn, 2, "SAIDA", 10, "2026-10-10 15:30:00")
    _movimentar(conn, 3, "ENTRADA", 8, "2026-10-03 08:00:00")
    conn.commit()
    yield conn
    fechar_conexao(conn)


# --- relatorio_estoque ------------------------------------------------------

def test_relatorio_estoque_lista_apenas_ativos_ordenados_por_nome(conexao):
    nomes = [p["nome"] for p in relatorio_estoque(conexao=conexao)]
    assert nomes == ["Água", "Detergente", "Suco"]


def test_relatorio_estoque_pode_incluir_inativos(conexao):
    nomes = [p["nome"] for p in relatorio_estoque(True, conexao=conexao)]
    assert "Antigo" in nomes
    assert len(nomes) == 4


def test_relatorio_estoque_campos_e_valor_total(conexao):
    agua = relatorio_estoque(conexao=conexao)[0]
    assert agua["codigo"] == "A1"
    assert agua["categoria"] == "Bebidas"
    assert agua["estoque_atual"] == 5
    assert agua["estoque_minimo"] == 10
    assert agua["valor_total"] == 12.5


def test_relatorio_estoque_situacao(conexao):
    situacoes = {p["nome"]: p["situacao"] for p in relatorio_estoque(conexao=conexao)}
    assert situacoes == {"Água": "BAIXO", "Detergente": "SEM ESTOQUE", "Suco": "OK"}


# --- estoque baixo e zerado -------------------------------------------------

def test_produtos_estoque_baixo(conexao):
    assert [p["nome"] for p in produtos_estoque_baixo(conexao=conexao)] == ["Água"]


def test_produtos_sem_estoque_ignora_inativos(conexao):
    assert [p["nome"] for p in produtos_sem_estoque(conexao=conexao)] == ["Detergente"]


def test_produto_com_minimo_zero_e_saldo_zero_nao_e_baixo(conexao):
    conexao.execute(
        "INSERT INTO produtos (codigo, nome, preco, estoque_minimo, categoria_id) "
        "VALUES ('Z1', 'Zero', 1.0, 0, 1)"
    )
    assert "Zero" not in [p["nome"] for p in produtos_estoque_baixo(conexao=conexao)]


# --- movimentações ----------------------------------------------------------

def test_movimentacoes_por_periodo_inclui_o_dia_final_inteiro(conexao):
    movs = movimentacoes_por_periodo("2026-10-05", "2026-10-10", conexao=conexao)
    assert [(m["produto"], m["tipo"], m["quantidade"]) for m in movs] == [
        ("Detergente", "SAIDA", 10),   # 10/10 às 15:30
        ("Água", "SAIDA", 15),         # 05/10
    ]


def test_movimentacoes_por_periodo_vazio(conexao):
    assert movimentacoes_por_periodo("2025-01-01", "2025-01-31", conexao=conexao) == []


def test_movimentacoes_por_periodo_valida_datas(conexao):
    with pytest.raises(ValueError):
        movimentacoes_por_periodo("10/10/2026", "2026-10-31", conexao=conexao)
    with pytest.raises(ValueError):
        movimentacoes_por_periodo("2026-10-31", "2026-10-01", conexao=conexao)


def test_movimentacoes_por_produto(conexao):
    movs = movimentacoes_por_produto(1, conexao=conexao)
    assert [(m["tipo"], m["quantidade"]) for m in movs] == [
        ("SAIDA", 15),
        ("ENTRADA", 20),
    ]


def test_movimentacoes_por_produto_inexistente(conexao):
    with pytest.raises(ValueError):
        movimentacoes_por_produto(999, conexao=conexao)


def test_saldo_do_relatorio_bate_com_as_movimentacoes(conexao):
    """Saldo = entradas - saídas, para cada produto do relatório."""
    ids = {"A1": 1, "D1": 2, "S1": 3}
    for produto in relatorio_estoque(conexao=conexao):
        movs = movimentacoes_por_produto(ids[produto["codigo"]], conexao=conexao)
        saldo = sum(
            m["quantidade"] if m["tipo"] == "ENTRADA" else -m["quantidade"]
            for m in movs
        )
        assert produto["estoque_atual"] == saldo


# --- indicadores gerais -----------------------------------------------------

def test_indicadores_gerais(conexao):
    assert indicadores_gerais(conexao=conexao) == {
        "total_produtos": 3,
        "produtos_abaixo_minimo": 1,
        "produtos_sem_estoque": 1,
        "unidades_em_estoque": 13,
        "valor_total_estoque": 60.5,
        "total_entradas": 38,
        "total_saidas": 25,
        "qtd_entradas": 3,
        "qtd_saidas": 2,
    }


def test_indicadores_batem_com_os_outros_relatorios(conexao):
    ind = indicadores_gerais(conexao=conexao)
    assert ind["total_produtos"] == len(relatorio_estoque(conexao=conexao))
    assert ind["produtos_abaixo_minimo"] == len(produtos_estoque_baixo(conexao=conexao))
    assert ind["produtos_sem_estoque"] == len(produtos_sem_estoque(conexao=conexao))
    periodo = movimentacoes_por_periodo("2026-01-01", "2026-12-31", conexao=conexao)
    assert ind["qtd_entradas"] + ind["qtd_saidas"] == len(periodo)
    assert ind["total_entradas"] - ind["total_saidas"] == ind["unidades_em_estoque"]


def test_indicadores_com_banco_vazio():
    conn = conectar(":memory:")
    criar_tabelas(conn)
    ind = indicadores_gerais(conexao=conn)
    assert ind["total_produtos"] == 0
    assert ind["total_entradas"] == 0
    assert ind["valor_total_estoque"] == 0
    fechar_conexao(conn)
