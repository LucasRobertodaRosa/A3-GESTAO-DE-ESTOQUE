"""Teste integrado do esquema SQLite oficial com bcrypt e movimentações.

Usa banco em memória, sem tocar no arquivo estoque.db.
"""

from contextlib import contextmanager

import pytest

from src import autenticacao, banco, main, movimentacoes, produtos, relatorios


@pytest.fixture
def conexao():
    con = banco.conectar(":memory:")
    banco.criar_tabelas(con)
    try:
        yield con
    finally:
        banco.fechar_conexao(con)


def test_fluxo_inicial_login_movimentacoes_e_relatorio(conexao, monkeypatch):
    # Diminui apenas o custo computacional do bcrypt DURANTE este teste.
    monkeypatch.setattr(autenticacao, "CUSTO_BCRYPT", 4)
    respostas = iter(["Admin Teste", "admina3", "SenhaA3!123", "SenhaA3!123"])
    monkeypatch.setattr(main, "_ler_campo", lambda *_args: next(respostas))

    assert main._primeiro_acesso(conexao) is True
    assert conexao.execute("SELECT COUNT(*) FROM funcionarios").fetchone()[0] == 1

    usuario = autenticacao.login("admina3", "SenhaA3!123", conexao=conexao)
    assert usuario is not None
    assert usuario["perfil"] == "ADMIN"
    assert autenticacao.login("admina3", "senha-errada", conexao=conexao) is None

    with conexao:
        categoria_id = conexao.execute(
            "INSERT INTO categorias (nome) VALUES (?)", ("Informática",)
        ).lastrowid
        produto_id = conexao.execute(
            """INSERT INTO produtos
               (codigo, nome, preco, estoque_minimo, estoque_atual, categoria_id)
               VALUES (?, ?, ?, ?, ?, ?)""",
            ("TEC-01", "Teclado USB", 99.90, 2, 0, categoria_id),
        ).lastrowid

    movimentacoes.registrar_entrada(
        produto_id, 15, funcionario_id=usuario["id"], conexao=conexao
    )
    movimentacoes.registrar_saida(
        produto_id, 3, "Sala de TI", funcionario_id=usuario["id"], conexao=conexao
    )

    with pytest.raises(ValueError, match="Estoque insuficiente"):
        movimentacoes.registrar_saida(
            produto_id, 20, "Sala de TI", funcionario_id=usuario["id"], conexao=conexao
        )

    saldo = conexao.execute(
        "SELECT estoque_atual FROM produtos WHERE id = ?", (produto_id,)
    ).fetchone()[0]
    assert saldo == 12
    registros = conexao.execute(
        "SELECT tipo, quantidade FROM movimentacoes ORDER BY id"
    ).fetchall()
    assert [(r[0], r[1]) for r in registros] == [("ENTRADA", 15), ("SAIDA", 3)]

    atual = relatorios.relatorio_estoque(conexao=conexao)
    assert any(p["codigo"] == "TEC-01" and p["estoque_atual"] == 12 for p in atual)

    # produtos.buscar_produtos() abre conexão própria; injetamos a conexão de teste.
    @contextmanager
    def conexao_teste():
        yield conexao

    monkeypatch.setattr(produtos, "_conexao", conexao_teste)
    encontrados = produtos.buscar_produtos("teclado")
    assert len(encontrados) == 1
    assert encontrados[0]["codigo"] == "TEC-01"


def test_permissoes_no_backend(conexao, monkeypatch):
    monkeypatch.setattr(autenticacao, "CUSTO_BCRYPT", 4)
    from src import funcionarios

    funcionario_id = funcionarios.cadastrar_funcionario(
        "Leitor", "leitor.a3", "SenhaTeste123!", "CONSULTA", conexao=conexao
    )
    usuario = autenticacao.login("leitor.a3", "SenhaTeste123!", conexao=conexao)
    assert usuario["id"] == funcionario_id
    assert autenticacao.tem_permissao(usuario, "CONSULTA")
    assert not autenticacao.tem_permissao(usuario, "ADMIN", "ESTOQUISTA")
    with pytest.raises(PermissionError):
        autenticacao.exigir_permissao(usuario, "ADMIN", "ESTOQUISTA")
