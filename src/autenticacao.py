"""Autenticação: hash de senha com bcrypt, login e permissões por perfil.

Uso típico (o main.py já faz isso):

    from src import autenticacao

    usuario = autenticacao.login("ana", "segredo1")   # dict ou None
    if usuario and autenticacao.tem_permissao(usuario, autenticacao.ADMIN):
        ...

Convenções (iguais às dos outros módulos):
- As funções aceitam o parâmetro opcional `conexao`. Sem ele, abrem e fecham a
  própria conexão com o banco.
- Dados inválidos levantam ValueError com mensagem clara.
- A senha em texto nunca é gravada nem devolvida: só o hash bcrypt fica em
  `funcionarios.senha_hash`.
"""

from contextlib import contextmanager

import bcrypt

try:
    from src.banco import conectar, fechar_conexao
except ImportError:  # quando o main.py é executado de dentro da pasta src
    from banco import conectar, fechar_conexao

ADMIN = "ADMIN"
ESTOQUISTA = "ESTOQUISTA"
CONSULTA = "CONSULTA"
PERFIS = (ADMIN, ESTOQUISTA, CONSULTA)

# Custo do bcrypt (2^12 iterações). Os testes baixam para 4, o mínimo permitido.
CUSTO_BCRYPT = 12
SENHA_MIN_CARACTERES = 6
# O bcrypt só considera os 72 primeiros bytes; recusamos senhas maiores em vez
# de truncá-las em silêncio.
SENHA_MAX_BYTES = 72

MENSAGEM_LOGIN_INVALIDO = "Login ou senha inválidos."


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


# --------------------------------------------------------------------------
# Senhas
# --------------------------------------------------------------------------

def validar_senha(senha):
    """Confere as regras de senha e devolve a própria senha (sem alterá-la)."""
    if not isinstance(senha, str) or not senha:
        raise ValueError("A senha é obrigatória.")
    if len(senha) < SENHA_MIN_CARACTERES:
        raise ValueError(
            f"A senha deve ter pelo menos {SENHA_MIN_CARACTERES} caracteres."
        )
    if len(senha.encode("utf-8")) > SENHA_MAX_BYTES:
        raise ValueError(f"A senha deve ter no máximo {SENHA_MAX_BYTES} bytes.")
    return senha


def gerar_hash(senha):
    """Valida a senha e devolve o hash bcrypt (texto) para gravar no banco."""
    senha = validar_senha(senha)
    sal = bcrypt.gensalt(rounds=CUSTO_BCRYPT)
    return bcrypt.hashpw(senha.encode("utf-8"), sal).decode("ascii")


def verificar_senha(senha, senha_hash):
    """True se a senha corresponde ao hash. Nunca levanta erro por dado ruim."""
    if not isinstance(senha, str) or not isinstance(senha_hash, str):
        return False
    try:
        return bcrypt.checkpw(senha.encode("utf-8"), senha_hash.encode("ascii"))
    except (ValueError, UnicodeEncodeError):
        # hash malformado ou senha grande demais para o bcrypt
        return False


# --------------------------------------------------------------------------
# Login
# --------------------------------------------------------------------------

def normalizar_login(login):
    """Login sem espaços nas pontas e em minúsculas ('' se não for texto)."""
    if not isinstance(login, str):
        return ""
    return login.strip().lower()


def validar_usuario(login, senha, conexao=None):
    """Confere login e senha e devolve os dados do funcionário.

    Levanta ValueError com a MESMA mensagem para login inexistente, senha errada
    e funcionário inativo, para não revelar qual dos casos aconteceu.
    """
    login = normalizar_login(login)
    if not login or not isinstance(senha, str) or not senha:
        raise ValueError(MENSAGEM_LOGIN_INVALIDO)

    with _conexao_em_uso(conexao) as con:
        linha = con.execute(
            "SELECT id, nome, login, perfil, senha_hash, ativo "
            "FROM funcionarios WHERE login = ?",
            (login,),
        ).fetchone()

    if linha is None or not linha[5]:
        raise ValueError(MENSAGEM_LOGIN_INVALIDO)
    if not verificar_senha(senha, linha[4]):
        raise ValueError(MENSAGEM_LOGIN_INVALIDO)

    return {"id": linha[0], "nome": linha[1], "login": linha[2], "perfil": linha[3]}


def login(login, senha, conexao=None):
    """Devolve {id, nome, login, perfil} se as credenciais estão certas, senão None."""
    try:
        return validar_usuario(login, senha, conexao=conexao)
    except ValueError:
        return None


# --------------------------------------------------------------------------
# Permissões
# --------------------------------------------------------------------------

def tem_permissao(usuario, *perfis_permitidos):
    """True se o perfil do usuário (dict devolvido pelo login) está na lista."""
    if not usuario:
        return False
    perfil = str(usuario.get("perfil") or "").upper()
    return perfil in {p.upper() for p in perfis_permitidos}


def exigir_permissao(usuario, *perfis_permitidos):
    """Levanta PermissionError se o usuário não tiver um dos perfis informados."""
    if not tem_permissao(usuario, *perfis_permitidos):
        permitidos = ", ".join(perfis_permitidos)
        raise PermissionError(f"Acesso negado: exige perfil {permitidos}.")
