"""Relatórios e indicadores do estoque.

Tabelas usadas (criadas por criar_tabelas() em src/banco.py):
    produtos(id, codigo, nome, preco, estoque_minimo, estoque_atual,
             categoria_id, ativo)
    categorias(id, nome, ...)

Todas as funções devolvem listas de dicionários (ou dicionários), sem
imprimir nada. A impressão no terminal é feita pelo src/main.py.

Cada função aceita o parâmetro opcional "conexao". O main.py o repassa
automaticamente e, nos testes, use conectar(":memory:").
"""

import unicodedata

from datetime import datetime

try:
    from .banco import conectar
except ImportError:  # quando executado de dentro da pasta src
    from banco import conectar


def _obter_conexao(conexao=None):
    """Reaproveita a conexão recebida ou abre uma nova.

    Devolve (conexao, deve_fechar).
    """
    if conexao is not None:
        return conexao, False
    return conectar(), True


def _chave_nome(nome):
    """Chave de ordenação sem acentos e sem diferenciar maiúsculas.

    O ORDER BY do SQLite compara byte a byte e põe "Água" depois de "Detergente".
    """
    sem_acento = unicodedata.normalize("NFKD", nome)
    sem_acento = "".join(c for c in sem_acento if not unicodedata.combining(c))
    return sem_acento.casefold()


def _situacao(estoque_atual, estoque_minimo):
    if estoque_atual == 0:
        return "SEM ESTOQUE"
    if estoque_atual < estoque_minimo:
        return "BAIXO"
    return "OK"


def relatorio_estoque(incluir_inativos=False, conexao=None):
    """Situação atual do estoque, um item por produto, ordenado por nome.

    Cada item traz: codigo, nome, categoria, estoque_atual, estoque_minimo,
    preco, valor_total (preco * estoque_atual) e situacao
    ("OK", "BAIXO" ou "SEM ESTOQUE").

    Por padrão considera apenas produtos ativos.
    """
    conn, deve_fechar = _obter_conexao(conexao)
    try:
        sql = """
            SELECT
                p.codigo,
                p.nome,
                c.nome AS categoria,
                p.estoque_atual,
                p.estoque_minimo,
                p.preco
            FROM produtos p
            JOIN categorias c ON c.id = p.categoria_id
        """
        if not incluir_inativos:
            sql += " WHERE p.ativo = 1"

        relatorio = []
        for linha in conn.execute(sql).fetchall():
            codigo, nome, categoria, atual, minimo, preco = tuple(linha)
            relatorio.append(
                {
                    "codigo": codigo,
                    "nome": nome,
                    "categoria": categoria,
                    "estoque_atual": atual,
                    "estoque_minimo": minimo,
                    "preco": preco,
                    "valor_total": round(preco * atual, 2),
                    "situacao": _situacao(atual, minimo),
                }
            )
        return sorted(relatorio, key=lambda item: _chave_nome(item["nome"]))
    finally:
        if deve_fechar:
            conn.close()


def produtos_estoque_baixo(conexao=None):
    """Produtos ativos com saldo acima de zero e abaixo do estoque mínimo."""
    return [
        item
        for item in relatorio_estoque(conexao=conexao)
        if item["situacao"] == "BAIXO"
    ]


def produtos_sem_estoque(conexao=None):
    """Produtos ativos com saldo zerado."""
    return [
        item
        for item in relatorio_estoque(conexao=conexao)
        if item["situacao"] == "SEM ESTOQUE"
    ]


def _validar_data(data, nome):
    """Aceita 'AAAA-MM-DD' e devolve a data normalizada."""
    try:
        return datetime.strptime(str(data).strip(), "%Y-%m-%d").strftime(
            "%Y-%m-%d"
        )
    except ValueError:
        raise ValueError(f"{nome} inválida. Use o formato AAAA-MM-DD.")


def _linhas_para_dicts(cursor):
    colunas = [descricao[0] for descricao in cursor.description]
    return [dict(zip(colunas, linha)) for linha in cursor.fetchall()]


_SQL_MOVIMENTACOES = """
    SELECT
        m.id,
        m.data_hora,
        m.tipo,
        p.codigo,
        p.nome AS produto,
        m.quantidade,
        f.nome AS funcionario,
        fo.nome AS fornecedor,
        m.observacao
    FROM movimentacoes m
    JOIN produtos p ON p.id = m.produto_id
    LEFT JOIN funcionarios f ON f.id = m.funcionario_id
    LEFT JOIN fornecedores fo ON fo.id = m.fornecedor_id
"""


def movimentacoes_por_periodo(data_inicio, data_fim, conexao=None):
    """Entradas e saídas entre duas datas (inclusive), da mais recente à mais antiga.

    As datas usam o formato AAAA-MM-DD. O dia final é incluído por inteiro.
    Cada item traz: id, data_hora, tipo, codigo, produto, quantidade,
    funcionario, fornecedor e observacao.
    """
    inicio = _validar_data(data_inicio, "Data inicial")
    fim = _validar_data(data_fim, "Data final")
    if inicio > fim:
        raise ValueError("A data inicial não pode ser maior que a data final.")

    conn, deve_fechar = _obter_conexao(conexao)
    try:
        cursor = conn.execute(
            _SQL_MOVIMENTACOES
            + " WHERE date(m.data_hora) BETWEEN ? AND ?"
            + " ORDER BY m.data_hora DESC, m.id DESC",
            (inicio, fim),
        )
        return _linhas_para_dicts(cursor)
    finally:
        if deve_fechar:
            conn.close()


def movimentacoes_por_produto(produto_id, conexao=None):
    """Histórico de entradas e saídas de um produto, da mais recente à mais antiga."""
    conn, deve_fechar = _obter_conexao(conexao)
    try:
        existe = conn.execute(
            "SELECT 1 FROM produtos WHERE id = ?", (produto_id,)
        ).fetchone()
        if existe is None:
            raise ValueError(f"Produto {produto_id} não encontrado.")

        cursor = conn.execute(
            _SQL_MOVIMENTACOES
            + " WHERE m.produto_id = ?"
            + " ORDER BY m.data_hora DESC, m.id DESC",
            (produto_id,),
        )
        return _linhas_para_dicts(cursor)
    finally:
        if deve_fechar:
            conn.close()
