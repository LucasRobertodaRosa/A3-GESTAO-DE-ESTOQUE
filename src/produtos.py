"""Gerenciamento de produtos.

Tabela esperada (criada por criar_tabelas() em src/banco.py):

    produtos(id INTEGER PRIMARY KEY AUTOINCREMENT,
             codigo TEXT NOT NULL UNIQUE,
             nome TEXT NOT NULL,
             preco REAL NOT NULL,
             estoque_minimo INTEGER NOT NULL DEFAULT 0,
             estoque_atual INTEGER NOT NULL DEFAULT 0,
             categoria_id INTEGER NOT NULL REFERENCES categorias(id),
             ativo INTEGER NOT NULL DEFAULT 1)

O campo estoque_atual é alterado apenas pelas movimentações (src/movimentacoes.py).
"""

from src.banco import conectar
from src.categorias import buscar_categoria

_COLUNAS = "id, codigo, nome, preco, estoque_minimo, estoque_atual, categoria_id, ativo"


def _linha_para_dict(linha):
    return {
        "id": linha[0],
        "codigo": linha[1],
        "nome": linha[2],
        "preco": linha[3],
        "estoque_minimo": linha[4],
        "estoque_atual": linha[5],
        "categoria_id": linha[6],
        "ativo": bool(linha[7]),
    }


def _validar_codigo(codigo):
    if codigo is None or not str(codigo).strip():
        raise ValueError("O código do produto é obrigatório.")
    return str(codigo).strip()


def _validar_nome(nome):
    if nome is None or not str(nome).strip():
        raise ValueError("O nome do produto é obrigatório.")
    return str(nome).strip()


def _validar_preco(preco):
    try:
        preco = float(preco)
    except (TypeError, ValueError):
        raise ValueError("O preço deve ser um número.")
    if preco < 0:
        raise ValueError("O preço não pode ser negativo.")
    return round(preco, 2)


def _validar_estoque_minimo(estoque_minimo):
    # bool é subclasse de int; rejeitar evita aceitar True/False sem querer.
    if isinstance(estoque_minimo, bool) or not isinstance(estoque_minimo, int):
        raise ValueError("O estoque mínimo deve ser um número inteiro.")
    if estoque_minimo < 0:
        raise ValueError("O estoque mínimo não pode ser negativo.")
    return estoque_minimo


def _validar_categoria(categoria_id):
    if categoria_id is None or buscar_categoria(categoria_id) is None:
        raise ValueError(f"Categoria {categoria_id} não encontrada.")
    return categoria_id


def _codigo_em_uso(conn, codigo, ignorar_id=None):
    linhas = conn.execute("SELECT id, codigo FROM produtos").fetchall()
    return any(
        linha[1].casefold() == codigo.casefold() and linha[0] != ignorar_id
        for linha in linhas
    )


def cadastrar_produto(codigo, nome, preco, estoque_minimo, categoria_id):
    """Cadastra um produto (ativo e com estoque zerado) e devolve seus dados."""
    codigo = _validar_codigo(codigo)
    nome = _validar_nome(nome)
    preco = _validar_preco(preco)
    estoque_minimo = _validar_estoque_minimo(estoque_minimo)
    categoria_id = _validar_categoria(categoria_id)

    conn = conectar()
    with conn:
        if _codigo_em_uso(conn, codigo):
            raise ValueError(f"Já existe um produto com o código '{codigo}'.")
        cursor = conn.execute(
            "INSERT INTO produtos (codigo, nome, preco, estoque_minimo, "
            "estoque_atual, categoria_id, ativo) VALUES (?, ?, ?, ?, 0, ?, 1)",
            (codigo, nome, preco, estoque_minimo, categoria_id),
        )
        produto_id = cursor.lastrowid

    return buscar_produto(produto_id)


def listar_produtos(incluir_inativos=False):
    """Devolve os produtos ordenados por nome. Por padrão, só os ativos."""
    sql = f"SELECT {_COLUNAS} FROM produtos"
    if not incluir_inativos:
        sql += " WHERE ativo = 1"
    sql += " ORDER BY nome"

    conn = conectar()
    return [_linha_para_dict(linha) for linha in conn.execute(sql).fetchall()]


def buscar_produto(produto_id):
    """Devolve o produto com o id informado, ou None se não existir."""
    conn = conectar()
    linha = conn.execute(
        f"SELECT {_COLUNAS} FROM produtos WHERE id = ?", (produto_id,)
    ).fetchone()
    return _linha_para_dict(linha) if linha else None


def editar_produto(
    produto_id,
    codigo=None,
    nome=None,
    preco=None,
    estoque_minimo=None,
    categoria_id=None,
):
    """Altera os dados de um produto e devolve o produto atualizado.

    Campos não informados (None) permanecem como estão. O saldo em estoque
    não é editado aqui: ele só muda por entradas e saídas.
    """
    atual = buscar_produto(produto_id)
    if atual is None:
        raise ValueError(f"Produto {produto_id} não encontrado.")

    novo_codigo = atual["codigo"] if codigo is None else _validar_codigo(codigo)
    novo_nome = atual["nome"] if nome is None else _validar_nome(nome)
    novo_preco = atual["preco"] if preco is None else _validar_preco(preco)
    novo_minimo = (
        atual["estoque_minimo"]
        if estoque_minimo is None
        else _validar_estoque_minimo(estoque_minimo)
    )
    nova_categoria = (
        atual["categoria_id"]
        if categoria_id is None
        else _validar_categoria(categoria_id)
    )

    conn = conectar()
    with conn:
        if _codigo_em_uso(conn, novo_codigo, ignorar_id=produto_id):
            raise ValueError(f"Já existe um produto com o código '{novo_codigo}'.")
        conn.execute(
            "UPDATE produtos SET codigo = ?, nome = ?, preco = ?, "
            "estoque_minimo = ?, categoria_id = ? WHERE id = ?",
            (novo_codigo, novo_nome, novo_preco, novo_minimo, nova_categoria, produto_id),
        )

    return buscar_produto(produto_id)


def desativar_produto(produto_id):
    """Desativa o produto (exclusão lógica, preserva o histórico) e o devolve."""
    if buscar_produto(produto_id) is None:
        raise ValueError(f"Produto {produto_id} não encontrado.")

    conn = conectar()
    with conn:
        conn.execute("UPDATE produtos SET ativo = 0 WHERE id = ?", (produto_id,))

    return buscar_produto(produto_id)
