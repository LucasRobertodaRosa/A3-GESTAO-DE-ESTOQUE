"""Gerenciamento de categorias de produtos.

Tabela esperada (criada por criar_tabelas() em src/banco.py):

    categorias(id INTEGER PRIMARY KEY AUTOINCREMENT,
               nome TEXT NOT NULL UNIQUE,
               descricao TEXT)
"""

from contextlib import contextmanager

from src.banco import conectar, fechar_conexao


@contextmanager
def _conexao():
    """Abre uma conexão e garante o fechamento ao final, mesmo com erro."""
    conn = conectar()
    try:
        yield conn
    finally:
        fechar_conexao(conn)


def _linha_para_dict(linha):
    return {"id": linha[0], "nome": linha[1], "descricao": linha[2]}


def _validar_nome(nome):
    if nome is None or not str(nome).strip():
        raise ValueError("O nome da categoria é obrigatório.")
    return str(nome).strip()


def _nome_em_uso(conn, nome, ignorar_id=None):
    # Comparação feita em Python: o LOWER() do SQLite não trata acentos (É/é).
    linhas = conn.execute("SELECT id, nome FROM categorias").fetchall()
    return any(
        linha[1].casefold() == nome.casefold() and linha[0] != ignorar_id
        for linha in linhas
    )


def cadastrar_categoria(nome, descricao=""):
    """Cadastra uma categoria e devolve seus dados (com o id gerado)."""
    nome = _validar_nome(nome)
    descricao = (descricao or "").strip()

    with _conexao() as conn:
        with conn:
            if _nome_em_uso(conn, nome):
                raise ValueError(f"Já existe uma categoria chamada '{nome}'.")
            cursor = conn.execute(
                "INSERT INTO categorias (nome, descricao) VALUES (?, ?)",
                (nome, descricao),
            )
            categoria_id = cursor.lastrowid

    return {"id": categoria_id, "nome": nome, "descricao": descricao}


def listar_categorias():
    """Devolve todas as categorias, ordenadas por nome."""
    with _conexao() as conn:
        linhas = conn.execute(
            "SELECT id, nome, descricao FROM categorias ORDER BY nome"
        ).fetchall()
    return [_linha_para_dict(linha) for linha in linhas]


def buscar_categoria(categoria_id):
    """Devolve a categoria com o id informado, ou None se não existir."""
    with _conexao() as conn:
        linha = conn.execute(
            "SELECT id, nome, descricao FROM categorias WHERE id = ?",
            (categoria_id,),
        ).fetchone()
    return _linha_para_dict(linha) if linha else None


def editar_categoria(categoria_id, nome=None, descricao=None):
    """Altera nome e/ou descrição de uma categoria e devolve os dados atualizados.

    Campos não informados (None) permanecem como estão.
    """
    atual = buscar_categoria(categoria_id)
    if atual is None:
        raise ValueError(f"Categoria {categoria_id} não encontrada.")

    novo_nome = atual["nome"] if nome is None else _validar_nome(nome)
    nova_descricao = (
        atual["descricao"] if descricao is None else (descricao or "").strip()
    )

    with _conexao() as conn:
        with conn:
            if _nome_em_uso(conn, novo_nome, ignorar_id=categoria_id):
                raise ValueError(f"Já existe uma categoria chamada '{novo_nome}'.")
            conn.execute(
                "UPDATE categorias SET nome = ?, descricao = ? WHERE id = ?",
                (novo_nome, nova_descricao, categoria_id),
            )

    return {"id": categoria_id, "nome": novo_nome, "descricao": nova_descricao}
