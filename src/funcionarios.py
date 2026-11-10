"""Gerenciamento de funcionários (tabela `funcionarios` de src/banco.py).

    funcionarios(id, nome, login UNIQUE, senha_hash, perfil, ativo)

Regras:
- perfil: ADMIN, ESTOQUISTA ou CONSULTA (tabela de permissões em autenticacao.py).
- login: 3 a 30 caracteres entre letras, números, ponto, hífen e sublinhado;
  é gravado em minúsculas e não pode se repetir.
- senha: validada e guardada só como hash bcrypt (veja autenticacao.gerar_hash).
- Funcionário não é apagado, só desativado, para preservar o histórico.
- O sistema nunca fica sem administrador ativo: o último ADMIN não pode ser
  desativado nem rebaixado.

As funções aceitam o parâmetro opcional `conexao` (o main.py repassa a dele).
Sem ele, abrem e fecham a própria conexão. Dados inválidos levantam ValueError.
Nenhuma função devolve a senha nem o hash.
"""

import re
import sqlite3
from contextlib import contextmanager

try:
    from src.autenticacao import ADMIN, PERFIS, gerar_hash, normalizar_login
    from src.banco import conectar, fechar_conexao
except ImportError:  # quando o main.py é executado de dentro da pasta src
    from autenticacao import ADMIN, PERFIS, gerar_hash, normalizar_login
    from banco import conectar, fechar_conexao

_PADRAO_LOGIN = re.compile(r"^[a-z0-9._-]{3,30}$")
_COLUNAS = "id, nome, login, perfil, ativo"


@contextmanager
def _conexao_em_uso(conexao):
    """Usa a conexão recebida ou abre (e fecha) uma própria."""
    if conexao is not None:
        yield conexao
        return
    propria = conectar()
    try:
        yield propria
    finally:
        fechar_conexao(propria)


def _linha_para_dict(linha):
    return {
        "id": linha[0],
        "nome": linha[1],
        "login": linha[2],
        "perfil": linha[3],
        "ativo": bool(linha[4]),
    }


# --------------------------------------------------------------------------
# Validações
# --------------------------------------------------------------------------

def _validar_nome(nome):
    if nome is None or not str(nome).strip():
        raise ValueError("O nome do funcionário é obrigatório.")
    return str(nome).strip()


def _validar_login(login):
    login = normalizar_login(login)
    if not login:
        raise ValueError("O login é obrigatório.")
    if not _PADRAO_LOGIN.match(login):
        raise ValueError(
            "O login deve ter de 3 a 30 caracteres: letras, números, ponto, "
            "hífen ou sublinhado (sem espaços)."
        )
    return login


def _validar_perfil(perfil):
    perfil = str(perfil or "").strip().upper()
    if perfil not in PERFIS:
        raise ValueError(f"Perfil inválido. Use {', '.join(PERFIS)}.")
    return perfil


def _buscar(con, funcionario_id):
    linha = con.execute(
        f"SELECT {_COLUNAS} FROM funcionarios WHERE id = ?", (funcionario_id,)
    ).fetchone()
    return _linha_para_dict(linha) if linha else None


def _exigir_existente(con, funcionario_id):
    atual = _buscar(con, funcionario_id)
    if atual is None:
        raise ValueError(f"Funcionário {funcionario_id} não encontrado.")
    return atual


def _e_o_ultimo_admin_ativo(con, atual):
    """True se `atual` é um ADMIN ativo e não há outro ADMIN ativo."""
    if atual["perfil"] != ADMIN or not atual["ativo"]:
        return False
    outros = con.execute(
        "SELECT COUNT(*) FROM funcionarios "
        "WHERE perfil = ? AND ativo = 1 AND id <> ?",
        (ADMIN, atual["id"]),
    ).fetchone()[0]
    return outros == 0


# --------------------------------------------------------------------------
# Operações
# --------------------------------------------------------------------------

def cadastrar_funcionario(nome, login, senha, perfil, conexao=None):
    """Cadastra um funcionário ativo e devolve o id gerado."""
    nome = _validar_nome(nome)
    login = _validar_login(login)
    perfil = _validar_perfil(perfil)
    senha_hash = gerar_hash(senha)  # valida a senha; o bcrypt é lento, fica fora da transação

    with _conexao_em_uso(conexao) as con:
        try:
            with con:
                cursor = con.execute(
                    "INSERT INTO funcionarios (nome, login, senha_hash, perfil, ativo) "
                    "VALUES (?, ?, ?, ?, 1)",
                    (nome, login, senha_hash, perfil),
                )
                return cursor.lastrowid
        except sqlite3.IntegrityError:
            raise ValueError(f"Já existe um funcionário com o login '{login}'.")


def listar_funcionarios(apenas_ativos=False, conexao=None):
    """Devolve os funcionários (sem senha) ordenados por nome."""
    sql = f"SELECT {_COLUNAS} FROM funcionarios"
    if apenas_ativos:
        sql += " WHERE ativo = 1"
    sql += " ORDER BY nome"
    with _conexao_em_uso(conexao) as con:
        return [_linha_para_dict(linha) for linha in con.execute(sql).fetchall()]


def buscar_funcionario(funcionario_id, conexao=None):
    """Devolve o funcionário (sem senha) ou None se o id não existir."""
    with _conexao_em_uso(conexao) as con:
        return _buscar(con, funcionario_id)


def editar_funcionario(funcionario_id, nome=None, perfil=None, conexao=None):
    """Altera nome e/ou perfil e devolve o funcionário atualizado.

    Campos não informados (None) permanecem como estão. O login e a senha não
    são alterados aqui.
    """
    with _conexao_em_uso(conexao) as con:
        atual = _exigir_existente(con, funcionario_id)
        novo_nome = atual["nome"] if nome is None else _validar_nome(nome)
        novo_perfil = atual["perfil"] if perfil is None else _validar_perfil(perfil)

        if novo_perfil != ADMIN and _e_o_ultimo_admin_ativo(con, atual):
            raise ValueError(
                "Não é possível alterar o perfil do último administrador ativo."
            )

        with con:
            con.execute(
                "UPDATE funcionarios SET nome = ?, perfil = ? WHERE id = ?",
                (novo_nome, novo_perfil, funcionario_id),
            )
        return _buscar(con, funcionario_id)


def desativar_funcionario(funcionario_id, conexao=None):
    """Desativa o funcionário (ele não consegue mais entrar) e o devolve."""
    with _conexao_em_uso(conexao) as con:
        atual = _exigir_existente(con, funcionario_id)
        if not atual["ativo"]:
            raise ValueError(f"O funcionário {funcionario_id} já está desativado.")
        if _e_o_ultimo_admin_ativo(con, atual):
            raise ValueError("Não é possível desativar o último administrador ativo.")

        with con:
            con.execute(
                "UPDATE funcionarios SET ativo = 0 WHERE id = ?", (funcionario_id,)
            )
        return _buscar(con, funcionario_id)
