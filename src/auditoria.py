"""Registro de auditoria do sistema.

Guarda quem fez o quê e quando (login, cadastros, entradas, saídas,
alterações). Exemplo de uso em qualquer módulo:

    from src import auditoria

    auditoria.registrar_evento(
        funcionario_id,
        auditoria.SAIDA,
        entidade="produto",
        entidade_id=produto_id,
        detalhes={"quantidade": 5},
    )

Convenções:
- acao: use as constantes deste módulo (LOGIN, CADASTRO, ENTRADA...).
  É gravada em MAIÚSCULAS.
- entidade: nome em minúsculas e no singular ("produto", "fornecedor",
  "funcionario", "movimentacao", "categoria").
- funcionario_id pode ser None (por exemplo, login com usuário inexistente).

As funções aceitam o parâmetro opcional `conexao`. Se ele não for
informado, abrem e fecham a própria conexão. Dados inválidos levantam
ValueError. Registros de auditoria nunca são alterados nem apagados.
"""

import json
import sqlite3
from contextlib import contextmanager
from datetime import date, datetime

try:
    from src.banco import conectar, fechar_conexao
except ImportError:  # quando o main.py é executado de dentro da pasta src
    from banco import conectar, fechar_conexao

# Ações padronizadas (use estas constantes para o filtro funcionar bem).
LOGIN = "LOGIN"
LOGIN_FALHA = "LOGIN_FALHA"
LOGOUT = "LOGOUT"
CADASTRO = "CADASTRO"
EDICAO = "EDICAO"
DESATIVACAO = "DESATIVACAO"
ENTRADA = "ENTRADA"
SAIDA = "SAIDA"


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


def _formatar_detalhes(detalhes):
    """Aceita texto, dicionário ou lista e devolve texto (ou None)."""
    if detalhes is None:
        return None
    if isinstance(detalhes, (dict, list, tuple)):
        return json.dumps(detalhes, ensure_ascii=False, default=str)
    texto = str(detalhes).strip()
    return texto or None


def _validar_data(valor):
    """Converte para 'AAAA-MM-DD', aceitando texto ou date/datetime."""
    if isinstance(valor, (date, datetime)):
        return valor.strftime("%Y-%m-%d")
    try:
        return datetime.strptime(str(valor).strip(), "%Y-%m-%d").strftime("%Y-%m-%d")
    except ValueError:
        raise ValueError("Data inválida. Use o formato AAAA-MM-DD.")


# --------------------------------------------------------------------------
# Operações
# --------------------------------------------------------------------------

def registrar_evento(funcionario_id, acao, entidade=None, entidade_id=None,
                     detalhes=None, conexao=None):
    """Registra um evento de auditoria e devolve o id do registro.

    O registro é gravado (commit) imediatamente. Chame esta função depois
    que a operação principal já tiver sido concluída com sucesso.
    """
    acao = (acao or "").strip().upper()
    if not acao:
        raise ValueError("A ação do evento é obrigatória.")

    entidade = (entidade or "").strip().lower() or None
    detalhes = _formatar_detalhes(detalhes)

    with _conexao_em_uso(conexao) as con:
        try:
            cursor = con.execute(
                "INSERT INTO auditoria "
                "(funcionario_id, acao, entidade, entidade_id, detalhes) "
                "VALUES (?, ?, ?, ?, ?)",
                (funcionario_id, acao, entidade, entidade_id, detalhes),
            )
            con.commit()
        except sqlite3.IntegrityError:
            con.rollback()
            raise ValueError("Funcionário não encontrado.")
        return cursor.lastrowid


def listar_eventos(funcionario_id=None, acao=None, entidade=None,
                   data_inicio=None, data_fim=None, limite=None, conexao=None):
    """Lista eventos, do mais recente para o mais antigo (lista de dicionários).

    Todos os filtros são opcionais e podem ser combinados:
    - funcionario_id: eventos de um funcionário;
    - acao / entidade: filtram pelo tipo de ação e pela entidade afetada;
    - data_inicio / data_fim: período inclusivo, no formato 'AAAA-MM-DD';
    - limite: quantidade máxima de registros.

    Cada item traz também funcionario_nome (None se não houver funcionário).
    """
    filtros = []
    parametros = []

    if funcionario_id is not None:
        filtros.append("a.funcionario_id = ?")
        parametros.append(funcionario_id)
    if acao and str(acao).strip():
        filtros.append("a.acao = ?")
        parametros.append(str(acao).strip().upper())
    if entidade and str(entidade).strip():
        filtros.append("a.entidade = ?")
        parametros.append(str(entidade).strip().lower())
    if data_inicio is not None:
        filtros.append("date(a.data_hora) >= ?")
        parametros.append(_validar_data(data_inicio))
    if data_fim is not None:
        filtros.append("date(a.data_hora) <= ?")
        parametros.append(_validar_data(data_fim))

    consulta = (
        "SELECT a.id, a.data_hora, a.funcionario_id, "
        "f.nome AS funcionario_nome, a.acao, a.entidade, a.entidade_id, "
        "a.detalhes "
        "FROM auditoria a "
        "LEFT JOIN funcionarios f ON f.id = a.funcionario_id"
    )
    if filtros:
        consulta += " WHERE " + " AND ".join(filtros)
    consulta += " ORDER BY a.data_hora DESC, a.id DESC"

    if limite is not None:
        try:
            limite = int(limite)
        except (TypeError, ValueError):
            raise ValueError("O limite deve ser um número inteiro positivo.")
        if limite <= 0:
            raise ValueError("O limite deve ser um número inteiro positivo.")
        consulta += " LIMIT ?"
        parametros.append(limite)

    with _conexao_em_uso(conexao) as con:
        return [dict(linha) for linha in con.execute(consulta, parametros).fetchall()]
