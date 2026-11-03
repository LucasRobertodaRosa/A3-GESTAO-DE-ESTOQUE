"""Camada de acesso ao banco de dados (SQLite) do sistema de estoque.

Todos os módulos devem obter a conexão por aqui:

    from src.banco import conectar, fechar_conexao

    conexao = conectar()
    ...
    fechar_conexao(conexao)

Nos testes, passe ":memory:" (ou um arquivo temporário) para não
mexer no banco real:

    conexao = conectar(":memory:")
    criar_tabelas(conexao)
"""

import sqlite3
from pathlib import Path

# Arquivo do banco na raiz do projeto (ignorado pelo Git via *.db).
CAMINHO_PADRAO = Path(__file__).resolve().parent.parent / "estoque.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS categorias (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    nome        TEXT    NOT NULL UNIQUE,
    descricao   TEXT,
    ativo       INTEGER NOT NULL DEFAULT 1 CHECK (ativo IN (0, 1))
);

CREATE TABLE IF NOT EXISTS fornecedores (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    nome        TEXT    NOT NULL,
    cnpj        TEXT    UNIQUE,
    telefone    TEXT,
    email       TEXT,
    ativo       INTEGER NOT NULL DEFAULT 1 CHECK (ativo IN (0, 1))
);

CREATE TABLE IF NOT EXISTS produtos (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    codigo          TEXT    NOT NULL UNIQUE,
    nome            TEXT    NOT NULL,
    preco           REAL    NOT NULL CHECK (preco >= 0),
    estoque_minimo  INTEGER NOT NULL DEFAULT 0 CHECK (estoque_minimo >= 0),
    estoque_atual   INTEGER NOT NULL DEFAULT 0 CHECK (estoque_atual >= 0),
    categoria_id    INTEGER NOT NULL,
    ativo           INTEGER NOT NULL DEFAULT 1 CHECK (ativo IN (0, 1)),
    FOREIGN KEY (categoria_id) REFERENCES categorias (id)
);

CREATE TABLE IF NOT EXISTS funcionarios (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    nome        TEXT    NOT NULL,
    login       TEXT    NOT NULL UNIQUE,
    senha_hash  TEXT    NOT NULL,
    perfil      TEXT    NOT NULL
                CHECK (perfil IN ('ADMIN', 'ESTOQUISTA', 'CONSULTA')),
    ativo       INTEGER NOT NULL DEFAULT 1 CHECK (ativo IN (0, 1))
);

CREATE TABLE IF NOT EXISTS movimentacoes (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    produto_id      INTEGER NOT NULL,
    tipo            TEXT    NOT NULL CHECK (tipo IN ('ENTRADA', 'SAIDA')),
    quantidade      INTEGER NOT NULL CHECK (quantidade > 0),
    data_hora       TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    funcionario_id  INTEGER,
    fornecedor_id   INTEGER,
    observacao      TEXT,
    FOREIGN KEY (produto_id)     REFERENCES produtos (id),
    FOREIGN KEY (funcionario_id) REFERENCES funcionarios (id),
    FOREIGN KEY (fornecedor_id)  REFERENCES fornecedores (id)
);

CREATE TABLE IF NOT EXISTS auditoria (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    data_hora       TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    funcionario_id  INTEGER,
    acao            TEXT    NOT NULL,
    entidade        TEXT,
    entidade_id     INTEGER,
    detalhes        TEXT,
    FOREIGN KEY (funcionario_id) REFERENCES funcionarios (id)
);

CREATE INDEX IF NOT EXISTS idx_produtos_nome
    ON produtos (nome);
CREATE INDEX IF NOT EXISTS idx_produtos_categoria
    ON produtos (categoria_id);
CREATE INDEX IF NOT EXISTS idx_movimentacoes_produto
    ON movimentacoes (produto_id);
CREATE INDEX IF NOT EXISTS idx_movimentacoes_data
    ON movimentacoes (data_hora);
"""


def conectar(caminho=None):
    """Abre uma conexão com o banco SQLite e a devolve.

    caminho: arquivo do banco. Se omitido, usa o estoque.db da raiz do
    projeto. Use ":memory:" nos testes.

    As linhas retornadas permitem acesso por nome de coluna
    (linha["nome"]) e as chaves estrangeiras ficam ativadas.
    """
    destino = str(caminho) if caminho is not None else str(CAMINHO_PADRAO)
    conexao = sqlite3.connect(destino)
    conexao.row_factory = sqlite3.Row
    conexao.execute("PRAGMA foreign_keys = ON")
    return conexao


def criar_tabelas(conexao):
    """Cria todas as tabelas e índices, caso ainda não existam."""
    conexao.executescript(SCHEMA)
    conexao.commit()


def fechar_conexao(conexao):
    """Fecha a conexão com segurança (aceita None)."""
    if conexao is not None:
        conexao.close()
