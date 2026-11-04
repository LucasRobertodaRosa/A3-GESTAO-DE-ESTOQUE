"""Gerenciamento de fornecedores.

Regras:
- o nome é obrigatório;
- CNPJ, telefone e e-mail são opcionais, mas, se informados, são validados;
- o CNPJ é guardado só com números e não pode se repetir;
- fornecedores nunca são apagados: desativar_fornecedor() marca ativo = 0,
  preservando o histórico das entradas de estoque.

Todas as funções aceitam o parâmetro opcional `conexao`. Se ele não for
informado, a função abre e fecha a própria conexão com o banco.

Dados inválidos ou inexistentes levantam ValueError, com uma mensagem
pronta para ser exibida ao usuário.
"""

import re
import sqlite3
from contextlib import contextmanager

try:
    from src.banco import conectar, fechar_conexao
except ImportError:  # quando o main.py é executado de dentro da pasta src
    from banco import conectar, fechar_conexao

_COLUNAS = "id, nome, cnpj, telefone, email, ativo"
_PESOS_CNPJ = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
_PADRAO_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


# --------------------------------------------------------------------------
# Auxiliares
# --------------------------------------------------------------------------

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


def _somente_digitos(texto):
    return re.sub(r"\D", "", str(texto))


def _digito_verificador(base):
    pesos = _PESOS_CNPJ[len(_PESOS_CNPJ) - len(base):]
    soma = sum(int(d) * p for d, p in zip(base, pesos))
    resto = soma % 11
    return "0" if resto < 2 else str(11 - resto)


def validar_cnpj(cnpj):
    """Retorna True se o CNPJ (com ou sem máscara) for válido."""
    numeros = _somente_digitos(cnpj or "")
    if len(numeros) != 14 or numeros == numeros[0] * 14:
        return False
    return (
        numeros[12] == _digito_verificador(numeros[:12])
        and numeros[13] == _digito_verificador(numeros[:13])
    )


def _validar_nome(nome):
    nome = (nome or "").strip()
    if not nome:
        raise ValueError("O nome do fornecedor é obrigatório.")
    if len(nome) > 100:
        raise ValueError("O nome do fornecedor deve ter no máximo 100 caracteres.")
    return nome


def _validar_cnpj_opcional(cnpj):
    if cnpj is None or not str(cnpj).strip():
        return None
    if not validar_cnpj(cnpj):
        raise ValueError("CNPJ inválido.")
    return _somente_digitos(cnpj)


def _validar_telefone(telefone):
    if telefone is None or not str(telefone).strip():
        return None
    numeros = _somente_digitos(telefone)
    if len(numeros) not in (10, 11):
        raise ValueError("Telefone inválido. Informe o DDD e o número.")
    return numeros


def _validar_email(email):
    if email is None or not str(email).strip():
        return None
    email = str(email).strip().lower()
    if not _PADRAO_EMAIL.match(email):
        raise ValueError("E-mail inválido.")
    return email


def _para_dict(linha):
    return dict(linha) if linha is not None else None


# --------------------------------------------------------------------------
# Operações
# --------------------------------------------------------------------------

def cadastrar_fornecedor(nome, cnpj=None, telefone=None, email=None, conexao=None):
    """Cadastra um fornecedor e devolve o id gerado."""
    nome = _validar_nome(nome)
    cnpj = _validar_cnpj_opcional(cnpj)
    telefone = _validar_telefone(telefone)
    email = _validar_email(email)

    with _conexao_em_uso(conexao) as con:
        try:
            cursor = con.execute(
                "INSERT INTO fornecedores (nome, cnpj, telefone, email) "
                "VALUES (?, ?, ?, ?)",
                (nome, cnpj, telefone, email),
            )
            con.commit()
        except sqlite3.IntegrityError:
            con.rollback()
            raise ValueError("Já existe um fornecedor cadastrado com este CNPJ.")
        return cursor.lastrowid


def listar_fornecedores(apenas_ativos=True, conexao=None):
    """Lista os fornecedores em ordem alfabética (lista de dicionários)."""
    consulta = f"SELECT {_COLUNAS} FROM fornecedores"
    if apenas_ativos:
        consulta += " WHERE ativo = 1"
    consulta += " ORDER BY nome COLLATE NOCASE"

    with _conexao_em_uso(conexao) as con:
        return [dict(linha) for linha in con.execute(consulta).fetchall()]


def buscar_fornecedor(fornecedor_id, conexao=None):
    """Devolve o fornecedor (dicionário) ou None se não existir.

    Também encontra fornecedores desativados, pois entradas antigas
    ainda podem fazer referência a eles.
    """
    with _conexao_em_uso(conexao) as con:
        linha = con.execute(
            f"SELECT {_COLUNAS} FROM fornecedores WHERE id = ?",
            (fornecedor_id,),
        ).fetchone()
        return _para_dict(linha)


def editar_fornecedor(fornecedor_id, nome=None, cnpj=None, telefone=None,
                      email=None, conexao=None):
    """Altera apenas os campos informados e devolve o fornecedor atualizado.

    Campos não informados (None) permanecem como estão. Para apagar um
    campo opcional (cnpj, telefone ou email), passe uma string vazia.
    """
    campos = {}
    if nome is not None:
        campos["nome"] = _validar_nome(nome)
    if cnpj is not None:
        campos["cnpj"] = _validar_cnpj_opcional(cnpj)
    if telefone is not None:
        campos["telefone"] = _validar_telefone(telefone)
    if email is not None:
        campos["email"] = _validar_email(email)

    if not campos:
        raise ValueError("Informe ao menos um campo para editar.")

    with _conexao_em_uso(conexao) as con:
        if buscar_fornecedor(fornecedor_id, conexao=con) is None:
            raise ValueError("Fornecedor não encontrado.")

        # Os nomes das colunas vêm do dicionário acima (nunca do usuário).
        atribuicoes = ", ".join(f"{coluna} = ?" for coluna in campos)
        valores = list(campos.values()) + [fornecedor_id]
        try:
            con.execute(
                f"UPDATE fornecedores SET {atribuicoes} WHERE id = ?", valores
            )
            con.commit()
        except sqlite3.IntegrityError:
            con.rollback()
            raise ValueError("Já existe um fornecedor cadastrado com este CNPJ.")
        return buscar_fornecedor(fornecedor_id, conexao=con)


def desativar_fornecedor(fornecedor_id, conexao=None):
    """Desativa o fornecedor (exclusão lógica). Devolve True em caso de sucesso."""
    with _conexao_em_uso(conexao) as con:
        if buscar_fornecedor(fornecedor_id, conexao=con) is None:
            raise ValueError("Fornecedor não encontrado.")
        con.execute("UPDATE fornecedores SET ativo = 0 WHERE id = ?", (fornecedor_id,))
        con.commit()
        return True
