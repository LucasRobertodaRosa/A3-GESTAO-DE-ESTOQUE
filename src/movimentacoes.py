from datetime import datetime

try:
    from .banco import conectar
except ImportError:
    from banco import conectar


def _obter_conexao(conexao=None):
    """
    Retorna uma conexão com o banco.

    Se uma conexão for passada, ela será reutilizada.
    Isso facilita os testes posteriormente.
    """
    if conexao is not None:
        return conexao, False

    return conectar(), True


def _validar_quantidade(quantidade):
    """
    Valida se a quantidade informada é numérica e maior que zero.
    """
    if isinstance(quantidade, bool) or not isinstance(
        quantidade, (int, float)
    ):
        raise ValueError("A quantidade deve ser numérica.")

    if quantidade <= 0:
        raise ValueError("A quantidade deve ser maior que zero.")


def _data_atual():
    """
    Retorna a data e hora atuais.
    """
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _produto_existe(conexao, id_produto):
    """
    Verifica se o produto existe no banco.
    """
    cursor = conexao.execute(
        "SELECT id FROM produtos WHERE id = ?",
        (id_produto,),
    )

    return cursor.fetchone() is not None


def registrar_entrada(
    id_produto,
    quantidade,
    fornecedor,
    data_entrada=None,
    conexao=None,
):
    """
    Registra uma entrada no estoque e atualiza
    a quantidade disponível do produto.

    Retorna o ID da entrada criada.
    """

    _validar_quantidade(quantidade)

    if not fornecedor or not str(fornecedor).strip():
        raise ValueError("O fornecedor deve ser informado.")

    conn, deve_fechar = _obter_conexao(conexao)

    try:
        if not _produto_existe(conn, id_produto):
            raise ValueError("Produto não encontrado.")

        data_entrada = data_entrada or _data_atual()

        with conn:

            cursor = conn.execute(
                """
                INSERT INTO entradas
                (
                    id_produto,
                    quantidade,
                    data_entrada,
                    fornecedor
                )
                VALUES (?, ?, ?, ?)
                """,
                (
                    id_produto,
                    quantidade,
                    data_entrada,
                    str(fornecedor).strip(),
                ),
            )

            conn.execute(
                """
                UPDATE produtos
                SET quantidade = quantidade + ?
                WHERE id = ?
                """,
                (
                    quantidade,
                    id_produto,
                ),
            )

        return cursor.lastrowid

    finally:
        if deve_fechar:
            conn.close()
def registrar_saida(
    id_produto,
    quantidade,
    destinatario,
    data_saida=None,
    conexao=None,
):
    """
    Registra uma saída do estoque e atualiza
    a quantidade disponível do produto.

    Impede a saída quando não houver estoque
    suficiente.

    Retorna o ID da saída criada.
    """

    _validar_quantidade(quantidade)

    if not destinatario or not str(destinatario).strip():
        raise ValueError("O destinatário deve ser informado.")

    conn, deve_fechar = _obter_conexao(conexao)

    try:
        cursor = conn.execute(
            """
            SELECT quantidade
            FROM produtos
            WHERE id = ?
            """,
            (id_produto,),
        )

        produto = cursor.fetchone()

        if produto is None:
            raise ValueError("Produto não encontrado.")

        saldo_disponivel = produto[0]

        if quantidade > saldo_disponivel:
            raise ValueError(
                f"Estoque insuficiente. "
                f"Disponível: {saldo_disponivel}."
            )

        data_saida = data_saida or _data_atual()

        with conn:

            cursor = conn.execute(
                """
                INSERT INTO saidas
                (
                    id_produto,
                    quantidade,
                    data_saida,
                    destinatario
                )
                VALUES (?, ?, ?, ?)
                """,
                (
                    id_produto,
                    quantidade,
                    data_saida,
                    str(destinatario).strip(),
                ),
            )

            conn.execute(
                """
                UPDATE produtos
                SET quantidade = quantidade - ?
                WHERE id = ?
                """,
                (
                    quantidade,
                    id_produto,
                ),
            )

        return cursor.lastrowid

    finally:
        if deve_fechar:
            conn.close()

def _linhas_para_dicts(cursor):
    """
    Converte o resultado de uma consulta SQL
    em uma lista de dicionários.
    """

    colunas = [
        descricao[0]
        for descricao in cursor.description
    ]

    return [
        dict(zip(colunas, linha))
        for linha in cursor.fetchall()
    ]


def listar_entradas(id_produto=None, conexao=None):
    """
    Retorna todas as entradas do estoque.

    É possível informar um produto específico
    utilizando id_produto.
    """

    conn, deve_fechar = _obter_conexao(conexao)

    try:

        sql = """
            SELECT
                e.id,
                e.id_produto,
                p.nome AS produto,
                e.quantidade,
                e.data_entrada,
                e.fornecedor
            FROM entradas e
            JOIN produtos p
                ON p.id = e.id_produto
        """

        parametros = []

        if id_produto is not None:
            sql += """
                WHERE e.id_produto = ?
            """

            parametros.append(id_produto)

        sql += """
            ORDER BY
                e.data_entrada DESC,
                e.id DESC
        """

        cursor = conn.execute(
            sql,
            parametros,
        )

        return _linhas_para_dicts(cursor)

    finally:
        if deve_fechar:
            conn.close()


def listar_saidas(id_produto=None, conexao=None):
    """
    Retorna todas as saídas do estoque.

    É possível informar um produto específico
    utilizando id_produto.
    """

    conn, deve_fechar = _obter_conexao(conexao)

    try:

        sql = """
            SELECT
                s.id,
                s.id_produto,
                p.nome AS produto,
                s.quantidade,
                s.data_saida,
                s.destinatario
            FROM saidas s
            JOIN produtos p
                ON p.id = s.id_produto
        """

        parametros = []

        if id_produto is not None:
            sql += """
                WHERE s.id_produto = ?
            """

            parametros.append(id_produto)

        sql += """
            ORDER BY
                s.data_saida DESC,
                s.id DESC
        """

        cursor = conn.execute(
            sql,
            parametros,
        )

        return _linhas_para_dicts(cursor)

    finally:
        if deve_fechar:
            conn.close()


def listar_movimentacoes(id_produto=None, conexao=None):
    """
    Retorna entradas e saídas em um único
    histórico de movimentações.
    """

    conn, deve_fechar = _obter_conexao(conexao)

    try:

        sql = """
            SELECT
                e.id AS id,
                'ENTRADA' AS tipo,
                e.id_produto AS id_produto,
                p.nome AS produto,
                e.quantidade AS quantidade,
                e.data_entrada AS data,
                e.fornecedor AS responsavel
            FROM entradas e

            JOIN produtos p
                ON p.id = e.id_produto

            UNION ALL

            SELECT
                s.id AS id,
                'SAIDA' AS tipo,
                s.id_produto AS id_produto,
                p.nome AS produto,
                s.quantidade AS quantidade,
                s.data_saida AS data,
                s.destinatario AS responsavel
            FROM saidas s

            JOIN produtos p
                ON p.id = s.id_produto
        """

        parametros = []

        if id_produto is not None:

            sql = f"""
                SELECT *
                FROM (
                    {sql}
                )
                WHERE id_produto = ?
                ORDER BY data DESC, id DESC
            """

            parametros.append(id_produto)

        else:

            sql += """
                ORDER BY
                    data DESC,
                    id DESC
            """

        cursor = conn.execute(
            sql,
            parametros,
        )

        return _linhas_para_dicts(cursor)

    finally:
        if deve_fechar:
            conn.close()