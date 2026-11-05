"""Registro e histórico de entradas/saídas usando o esquema oficial de src.banco.

O menu principal passa os argumentos na seguinte ordem:
entrada: produto_id, quantidade, fornecedor_id, funcionario_id
saída: produto_id, quantidade, destinatario, funcionario_id
"""

try:
    from .banco import conectar
except ImportError:  # execução direta de dentro de src/
    from banco import conectar


def _obter_conexao(conexao=None):
    """Retorna (conexão, deve_fechar)."""
    if conexao is not None:
        return conexao, False
    return conectar(), True


def _validar_quantidade(quantidade):
    """A tabela movimentacoes aceita apenas quantidades inteiras positivas."""
    if type(quantidade) is not int or quantidade <= 0:
        raise ValueError("A quantidade deve ser um inteiro maior que zero.")


def _verificar_produto(conn, produto_id):
    """Confirma a existência do produto e se ele está ativo."""
    produto = conn.execute(
        "SELECT estoque_atual, ativo FROM produtos WHERE id = ?", (produto_id,)
    ).fetchone()
    if produto is None:
        raise ValueError("Produto não encontrado.")
    if not produto["ativo"]:
        raise ValueError("Produto inativo.")
    return produto["estoque_atual"]


def registrar_entrada(
    produto_id,
    quantidade,
    fornecedor_id=None,
    funcionario_id=None,
    conexao=None,
):
    """Aumenta estoque e registra a entrada em uma única transação.

    fornecedor_id e funcionario_id são opcionais e precisam existir no banco
    quando informados. Retorna o ID da movimentação.
    """
    _validar_quantidade(quantidade)
    conn, deve_fechar = _obter_conexao(conexao)
    try:
        with conn:
            _verificar_produto(conn, produto_id)
            conn.execute(
                "UPDATE produtos SET estoque_atual = estoque_atual + ? WHERE id = ?",
                (quantidade, produto_id),
            )
            cursor = conn.execute(
                """
                INSERT INTO movimentacoes
                    (produto_id, tipo, quantidade, funcionario_id, fornecedor_id)
                VALUES (?, 'ENTRADA', ?, ?, ?)
                """,
                (produto_id, quantidade, funcionario_id, fornecedor_id),
            )
        return cursor.lastrowid
    finally:
        if deve_fechar:
            conn.close()


def registrar_saida(
    produto_id,
    quantidade,
    destinatario=None,
    funcionario_id=None,
    conexao=None,
):
    """Diminui o saldo, bloqueando saídas superiores ao estoque atual.

    O esquema oficial não possui coluna 'destinatario'; essa informação fica
    registrada em 'observacao'. Retorna o ID da movimentação.
    """
    _validar_quantidade(quantidade)
    conn, deve_fechar = _obter_conexao(conexao)
    try:
        with conn:
            _verificar_produto(conn, produto_id)
            # Condição no próprio UPDATE impede saldo negativo mesmo se o saldo
            # tiver mudado entre a consulta inicial e a atualização.
            alteracao = conn.execute(
                """
                UPDATE produtos
                   SET estoque_atual = estoque_atual - ?
                 WHERE id = ? AND ativo = 1 AND estoque_atual >= ?
                """,
                (quantidade, produto_id, quantidade),
            )
            if alteracao.rowcount != 1:
                saldo = conn.execute(
                    "SELECT estoque_atual FROM produtos WHERE id = ?",
                    (produto_id,),
                ).fetchone()["estoque_atual"]
                raise ValueError(
                    f"Estoque insuficiente. Disponível: {saldo}."
                )

            observacao = None
            if destinatario is not None and str(destinatario).strip():
                observacao = f"Destinatário: {str(destinatario).strip()}"

            cursor = conn.execute(
                """
                INSERT INTO movimentacoes
                    (produto_id, tipo, quantidade, funcionario_id, observacao)
                VALUES (?, 'SAIDA', ?, ?, ?)
                """,
                (produto_id, quantidade, funcionario_id, observacao),
            )
        return cursor.lastrowid
    finally:
        if deve_fechar:
            conn.close()


def _listar(tipo=None, produto_id=None, conexao=None):
    """Consulta o histórico com filtros opcionais e nomes associados."""
    conn, deve_fechar = _obter_conexao(conexao)
    try:
        sql = """
            SELECT m.id, m.produto_id, p.codigo, p.nome AS produto,
                   m.tipo, m.quantidade, m.data_hora,
                   m.funcionario_id, f.nome AS funcionario,
                   m.fornecedor_id, fo.nome AS fornecedor, m.observacao
              FROM movimentacoes AS m
              JOIN produtos AS p ON p.id = m.produto_id
              LEFT JOIN funcionarios AS f ON f.id = m.funcionario_id
              LEFT JOIN fornecedores AS fo ON fo.id = m.fornecedor_id
        """
        condicoes = []
        parametros = []
        if tipo is not None:
            condicoes.append("m.tipo = ?")
            parametros.append(tipo)
        if produto_id is not None:
            condicoes.append("m.produto_id = ?")
            parametros.append(produto_id)
        if condicoes:
            sql += " WHERE " + " AND ".join(condicoes)
        sql += " ORDER BY m.data_hora DESC, m.id DESC"
        cursor = conn.execute(sql, parametros)
        return [dict(linha) for linha in cursor.fetchall()]
    finally:
        if deve_fechar:
            conn.close()


def listar_movimentacoes(produto_id=None, conexao=None):
    """Retorna entradas e saídas, mais recentes primeiro."""
    return _listar(produto_id=produto_id, conexao=conexao)


def listar_entradas(produto_id=None, conexao=None):
    """Retorna somente entradas, mais recentes primeiro."""
    return _listar(tipo="ENTRADA", produto_id=produto_id, conexao=conexao)


def listar_saidas(produto_id=None, conexao=None):
    """Retorna somente saídas, mais recentes primeiro."""
    return _listar(tipo="SAIDA", produto_id=produto_id, conexao=conexao)
