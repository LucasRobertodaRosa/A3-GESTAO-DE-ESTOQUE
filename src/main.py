"""Sistema de Gestão de Estoque - ponto de entrada (menu de terminal).

Executar na raiz do projeto:

    python -m src.main          (ou)          python src/main.py

Fluxo:
    abre o banco -> cria as tabelas -> (primeiro acesso: cria o ADMIN)
    -> login -> menu principal conforme o perfil -> cada ação relevante
    é registrada na auditoria.

COMO ESTE ARQUIVO SE LIGA AOS OUTROS MÓDULOS
--------------------------------------------
Todas as chamadas aos módulos dos colegas estão na tabela MENUS, no fim
deste arquivo: uma linha por opção de menu, com o módulo, a função e os
campos que serão perguntados ao usuário (na ORDEM dos parâmetros da função).
Se a função de um colega tiver outra ordem ou outros parâmetros, basta
ajustar a linha correspondente; nada mais precisa mudar.

- Se uma função recebe um parâmetro chamado "conexao" (ou "con", "conn",
  "connection"), a conexão aberta aqui é repassada automaticamente.
- Módulo ou função ainda inexistente: o menu avisa "Indisponível" em vez de
  quebrar, então a integração pode ser feita aos poucos.
- Campo do tipo "@usuario" é preenchido com o id do funcionário logado.

Contratos assumidos (confira com cada responsável):
    autenticacao.login(login, senha)  -> funcionário (dict) ou None/False
    funcionarios.cadastrar_funcionario(nome, login, senha, perfil)
"""

import getpass
import importlib
import inspect
import math
import sqlite3
import sys
from dataclasses import dataclass
from datetime import datetime

try:
    from src import auditoria, banco
except ImportError:  # quando executado de dentro da pasta src
    import auditoria
    import banco

ADMIN = "ADMIN"
ESTOQUISTA = "ESTOQUISTA"
CONSULTA = "CONSULTA"
PERFIS = (ADMIN, ESTOQUISTA, CONSULTA)

TODOS = PERFIS
ESCRITA = (ADMIN, ESTOQUISTA)
SOMENTE_ADMIN = (ADMIN,)

MAX_TENTATIVAS_LOGIN = 3
_NOMES_CONEXAO = ("conexao", "con", "conn", "connection")


class NaoIntegrado(Exception):
    """Módulo ou função ainda não disponível no projeto."""


class Cancelado(Exception):
    """O usuário digitou '!' para cancelar a operação."""


@dataclass(frozen=True)
class Item:
    """Uma opção de menu.

    campos: tuplas (parametro, pergunta, tipo). Tipos: texto, int, decimal,
    data, perfil, senha e "@usuario". Com "?" no fim (ex.: "texto?") o campo
    é opcional e, se deixado em branco, a função recebe None.
    auditoria: (acao, entidade) a registrar após o sucesso, ou None.
    """

    rotulo: str
    modulo: str
    funcao: str
    campos: tuple = ()
    perfis: tuple = TODOS
    auditoria: tuple = None


@dataclass
class Contexto:
    conexao: object
    usuario: dict

    @property
    def perfil(self):
        return self.usuario["perfil"]


# --------------------------------------------------------------------------
# Chamada aos módulos
# --------------------------------------------------------------------------

def _carregar(nome):
    """Importa src.<nome> (ou <nome>). Devolve None se o módulo não existir."""
    for prefixo in ("src.", ""):
        completo = prefixo + nome
        try:
            return importlib.import_module(completo)
        except ModuleNotFoundError as erro:
            # Se faltar OUTRA coisa (ex.: bcrypt), o erro precisa aparecer.
            if erro.name not in (completo, "src"):
                raise
    return None


def _chamar(modulo, funcao, argumentos=(), conexao=None):
    """Chama modulo.funcao(*argumentos), repassando a conexão se ela aceitar."""
    mod = _carregar(modulo)
    if mod is None:
        raise NaoIntegrado(f"o módulo '{modulo}' ainda não foi integrado.")
    func = getattr(mod, funcao, None)
    if not callable(func):
        raise NaoIntegrado(f"'{modulo}.{funcao}' ainda não existe.")

    argumentos = tuple(argumentos)
    extras = {}
    if conexao is not None:
        try:
            parametros = list(inspect.signature(func).parameters)
        except (TypeError, ValueError):
            parametros = []
        for nome in _NOMES_CONEXAO:
            if nome in parametros:
                if parametros[0] == nome:      # conexão é o 1º parâmetro
                    argumentos = (conexao,) + argumentos
                else:
                    extras[nome] = conexao
                break
    return func(*argumentos, **extras)


def _mensagem_de_erro(erro):
    if isinstance(erro, NaoIntegrado):
        return f"Indisponível: {erro}"
    if isinstance(erro, ValueError):
        return str(erro)
    if isinstance(erro, TypeError):
        return ("Chamada incompatível com a função do módulo "
                f"(ajuste a tabela MENUS em main.py): {erro}")
    return f"Erro inesperado ({type(erro).__name__}): {erro}"


def _auditar(conexao, usuario, acao, entidade=None, entidade_id=None,
             detalhes=None):
    """Registra na auditoria sem derrubar o programa se algo falhar."""
    funcionario_id = usuario["id"] if usuario else None
    try:
        auditoria.registrar_evento(funcionario_id, acao, entidade, entidade_id,
                                   detalhes, conexao=conexao)
    except Exception as erro:  # a ação principal já foi concluída
        print(f"Aviso: não foi possível registrar na auditoria ({erro}).")


# --------------------------------------------------------------------------
# Entrada e saída no terminal
# --------------------------------------------------------------------------

def _converter(texto, tipo):
    if tipo == "int":
        try:
            return int(texto)
        except ValueError:
            raise ValueError("Informe um número inteiro.")
    if tipo == "decimal":
        try:
            numero = float(texto.replace(",", "."))
        except ValueError:
            numero = float("nan")
        if not math.isfinite(numero):
            raise ValueError("Informe um número válido (ex.: 12,50).")
        return numero
    if tipo == "data":
        for formato in ("%Y-%m-%d", "%d/%m/%Y"):
            try:
                return datetime.strptime(texto, formato).strftime("%Y-%m-%d")
            except ValueError:
                pass
        raise ValueError("Data inválida. Use AAAA-MM-DD ou DD/MM/AAAA.")
    if tipo == "perfil":
        perfil = texto.upper()
        if perfil not in PERFIS:
            raise ValueError("Perfil inválido. Use ADMIN, ESTOQUISTA ou CONSULTA.")
        return perfil
    return texto


def _ler_campo(pergunta, tipo):
    opcional = tipo.endswith("?")
    base = tipo.rstrip("?")
    while True:
        if base == "senha":
            texto = getpass.getpass(pergunta)
        else:
            texto = input(pergunta).strip()
        if texto == "!":
            raise Cancelado()
        if not texto:
            if opcional:
                return None
            print("Campo obrigatório.")
            continue
        try:
            return _converter(texto, base)
        except ValueError as erro:
            print(erro)


def _como_dict(obj):
    if isinstance(obj, dict):
        return obj
    if isinstance(obj, sqlite3.Row):
        return dict(obj)
    if hasattr(obj, "_asdict"):
        return obj._asdict()
    if hasattr(obj, "__dict__"):
        return {k: v for k, v in vars(obj).items() if not k.startswith("_")}
    if isinstance(obj, (list, tuple)):
        return {f"col{i}": v for i, v in enumerate(obj, 1)}
    return {"valor": obj}


def _texto(valor):
    return "-" if valor is None else str(valor)


def _imprimir_tabela(linhas):
    dados = [_como_dict(linha) for linha in linhas]
    colunas = []
    for linha in dados:
        for coluna in linha:
            if coluna not in colunas:
                colunas.append(coluna)
    celulas = [[_texto(linha.get(c)) for c in colunas] for linha in dados]
    larguras = [
        min(40, max([len(str(c))] + [len(l[i]) for l in celulas]))
        for i, c in enumerate(colunas)
    ]
    cabecalho = " | ".join(str(c).upper().ljust(w) for c, w in zip(colunas, larguras))
    print(cabecalho)
    print("-" * len(cabecalho))
    for linha in celulas:
        print(" | ".join(v[:w].ljust(w) for v, w in zip(linha, larguras)))
    print(f"\n{len(celulas)} registro(s).")


def _mostrar(resultado):
    if isinstance(resultado, bool):
        print("Operação concluída com sucesso." if resultado
              else "Operação não realizada.")
    elif resultado is None:
        print("Operação concluída com sucesso.")
    elif isinstance(resultado, int):
        print(f"Concluído. ID: {resultado}")
    elif isinstance(resultado, str):
        print(resultado)
    elif isinstance(resultado, (list, tuple)):
        if not resultado:
            print("Nenhum registro encontrado.")
        elif isinstance(resultado[0], (str, int, float, type(None))):
            _imprimir_tabela([resultado])         # uma única linha (tupla)
        else:
            _imprimir_tabela(resultado)
    else:
        for chave, valor in _como_dict(resultado).items():
            print(f"{chave}: {_texto(valor)}")


# --------------------------------------------------------------------------
# Execução das opções de menu
# --------------------------------------------------------------------------

def _executar_item(item, ctx):
    print(f"\n--- {item.rotulo} ---")
    if any(tipo != "@usuario" for _, _, tipo in item.campos):
        print('(digite "!" a qualquer momento para cancelar)')
    try:
        valores = []
        for _, pergunta, tipo in item.campos:
            if tipo == "@usuario":
                valores.append(ctx.usuario["id"])
            else:
                valores.append(_ler_campo(pergunta, tipo))

        resultado = _chamar(item.modulo, item.funcao, valores, ctx.conexao)
        print()
        _mostrar(resultado)
    except Cancelado:
        print("Operação cancelada.")
        return
    except Exception as erro:
        print(f"\n{_mensagem_de_erro(erro)}")
        return

    if item.auditoria:
        acao, entidade = item.auditoria
        detalhes = {
            param: valor
            for (param, _, tipo), valor in zip(item.campos, valores)
            if tipo not in ("senha", "@usuario") and valor is not None
        }
        entidade_id = None
        if isinstance(resultado, int) and not isinstance(resultado, bool):
            entidade_id = resultado
        elif (item.campos and isinstance(valores[0], int)
              and (item.campos[0][0] == "id" or item.campos[0][0].endswith("_id"))):
            entidade_id = valores[0]
        _auditar(ctx.conexao, ctx.usuario, acao, entidade, entidade_id, detalhes)


def _submenu(titulo, itens, ctx):
    permitidos = [item for item in itens if ctx.perfil in item.perfis]
    while True:
        print(f"\n=== {titulo} ===")
        for numero, item in enumerate(permitidos, 1):
            print(f"{numero}. {item.rotulo}")
        print("0. Voltar")
        escolha = input("Opção: ").strip()
        if escolha == "0":
            return
        if escolha.isdigit() and 1 <= int(escolha) <= len(permitidos):
            _executar_item(permitidos[int(escolha) - 1], ctx)
            input("\nPressione Enter para continuar...")
        else:
            print("Opção inválida.")


def _menu_principal(ctx):
    visiveis = [(titulo, itens) for titulo, itens in MENUS
                if any(ctx.perfil in item.perfis for item in itens)]
    while True:
        print("\n===== GESTÃO DE ESTOQUE =====")
        print(f"Usuário: {ctx.usuario['nome']} ({ctx.perfil})")
        for numero, (titulo, _) in enumerate(visiveis, 1):
            print(f"{numero}. {titulo}")
        print("0. Sair")
        escolha = input("Opção: ").strip()
        if escolha == "0":
            _auditar(ctx.conexao, ctx.usuario, auditoria.LOGOUT)
            print("Até logo!")
            return
        if escolha.isdigit() and 1 <= int(escolha) <= len(visiveis):
            titulo, itens = visiveis[int(escolha) - 1]
            _submenu(titulo, itens, ctx)
        else:
            print("Opção inválida.")


# --------------------------------------------------------------------------
# Primeiro acesso e login
# --------------------------------------------------------------------------

def _primeiro_acesso(conexao):
    """Se não há funcionários, cria o administrador inicial."""
    total = conexao.execute("SELECT COUNT(*) FROM funcionarios").fetchone()[0]
    if total:
        return True

    print("Nenhum funcionário cadastrado. Vamos criar o administrador inicial.")
    try:
        nome = _ler_campo("Nome: ", "texto")
        login = _ler_campo("Login: ", "texto")
        while True:
            senha = _ler_campo("Senha: ", "senha")
            if senha == _ler_campo("Confirme a senha: ", "senha"):
                break
            print("As senhas não conferem.")
        _chamar("funcionarios", "cadastrar_funcionario",
                [nome, login, senha, ADMIN], conexao)
    except Cancelado:
        print("Cadastro cancelado.")
        return False
    except Exception as erro:
        print(_mensagem_de_erro(erro))
        return False

    _auditar(conexao, None, auditoria.CADASTRO, "funcionario", None,
             {"login": login, "perfil": ADMIN, "origem": "primeiro acesso"})
    print("Administrador criado com sucesso.\n")
    return True


def _montar_usuario(conexao, login, resultado):
    """Obtém id, nome e perfil do funcionário que acabou de logar."""
    dados = {}
    if not isinstance(resultado, bool):
        try:
            dados = {str(k).lower(): v for k, v in _como_dict(resultado).items()}
        except Exception:
            dados = {}
    if not all(k in dados for k in ("id", "nome")):
        linha = conexao.execute(
            "SELECT id, nome, perfil FROM funcionarios WHERE login = ?", (login,)
        ).fetchone()
        if linha is None:
            return None
        dados = dict(linha)
    perfil = str(dados.get("perfil") or dados.get("cargo") or "").upper()
    if perfil not in PERFIS:
        perfil = CONSULTA   # na dúvida, o menor privilégio
    return {"id": dados["id"], "nome": dados["nome"], "perfil": perfil}


def _fazer_login(conexao):
    for _ in range(MAX_TENTATIVAS_LOGIN):
        print("\n--- Login ---")
        login = input("Login: ").strip()
        senha = getpass.getpass("Senha: ")
        try:
            resultado = _chamar("autenticacao", "login", [login, senha], conexao)
        except NaoIntegrado as erro:
            print(_mensagem_de_erro(erro))
            return None
        except ValueError:
            resultado = None
        except Exception as erro:
            print(_mensagem_de_erro(erro))
            return None

        usuario = _montar_usuario(conexao, login, resultado) if resultado else None
        if usuario:
            _auditar(conexao, usuario, auditoria.LOGIN)
            return usuario

        _auditar(conexao, None, auditoria.LOGIN_FALHA, detalhes=f"login={login}")
        print("Login ou senha inválidos.")
    print("Número máximo de tentativas atingido.")
    return None


# --------------------------------------------------------------------------
# Tabela de menus: ajuste aqui se a função de um módulo tiver outra assinatura
# --------------------------------------------------------------------------

_ID = ("id", "ID: ", "int")

MENUS = [
    ("Categorias", [
        Item("Cadastrar categoria", "categorias", "cadastrar_categoria",
             (("nome", "Nome: ", "texto"),
              ("descricao", "Descrição (opcional): ", "texto?")),
             ESCRITA, (auditoria.CADASTRO, "categoria")),
        Item("Listar categorias", "categorias", "listar_categorias"),
        Item("Buscar categoria", "categorias", "buscar_categoria", (_ID,)),
        Item("Editar categoria", "categorias", "editar_categoria",
             (_ID,
              ("nome", "Novo nome: ", "texto"),
              ("descricao", "Nova descrição (opcional): ", "texto?")),
             ESCRITA, (auditoria.EDICAO, "categoria")),
    ]),
    ("Produtos", [
        Item("Cadastrar produto", "produtos", "cadastrar_produto",
             (("codigo", "Código: ", "texto"),
              ("nome", "Nome: ", "texto"),
              ("preco", "Preço: ", "decimal"),
              ("estoque_minimo", "Estoque mínimo: ", "int"),
              ("categoria_id", "ID da categoria: ", "int")),
             ESCRITA, (auditoria.CADASTRO, "produto")),
        Item("Listar produtos", "produtos", "listar_produtos"),
        Item("Buscar produto (nome, código ou categoria)", "produtos",
             "buscar_produto", (("termo", "Busca: ", "texto"),)),
        Item("Editar produto", "produtos", "editar_produto",
             (_ID,
              ("nome", "Novo nome: ", "texto"),
              ("preco", "Novo preço: ", "decimal"),
              ("estoque_minimo", "Novo estoque mínimo: ", "int"),
              ("categoria_id", "Nova categoria (ID): ", "int")),
             ESCRITA, (auditoria.EDICAO, "produto")),
        Item("Desativar produto", "produtos", "desativar_produto", (_ID,),
             ESCRITA, (auditoria.DESATIVACAO, "produto")),
    ]),
    ("Entradas e saídas", [
        Item("Registrar entrada", "movimentacoes", "registrar_entrada",
             (("produto_id", "ID do produto: ", "int"),
              ("quantidade", "Quantidade: ", "int"),
              ("fornecedor_id", "ID do fornecedor (opcional): ", "int?"),
              ("funcionario_id", "", "@usuario")),
             ESCRITA, (auditoria.ENTRADA, "movimentacao")),
        Item("Registrar saída", "movimentacoes", "registrar_saida",
             (("produto_id", "ID do produto: ", "int"),
              ("quantidade", "Quantidade: ", "int"),
              ("destinatario", "Destinatário (opcional): ", "texto?"),
              ("funcionario_id", "", "@usuario")),
             ESCRITA, (auditoria.SAIDA, "movimentacao")),
        Item("Histórico de movimentações", "movimentacoes", "listar_movimentacoes"),
        Item("Histórico de entradas", "movimentacoes", "listar_entradas"),
        Item("Histórico de saídas", "movimentacoes", "listar_saidas"),
    ]),
    ("Fornecedores", [
        Item("Cadastrar fornecedor", "fornecedores", "cadastrar_fornecedor",
             (("nome", "Nome: ", "texto"),
              ("cnpj", "CNPJ (opcional): ", "texto?"),
              ("telefone", "Telefone com DDD (opcional): ", "texto?"),
              ("email", "E-mail (opcional): ", "texto?")),
             ESCRITA, (auditoria.CADASTRO, "fornecedor")),
        Item("Listar fornecedores", "fornecedores", "listar_fornecedores"),
        Item("Buscar fornecedor", "fornecedores", "buscar_fornecedor", (_ID,)),
        Item("Editar fornecedor (Enter mantém o valor atual)", "fornecedores",
             "editar_fornecedor",
             (_ID,
              ("nome", "Novo nome: ", "texto?"),
              ("cnpj", "Novo CNPJ: ", "texto?"),
              ("telefone", "Novo telefone: ", "texto?"),
              ("email", "Novo e-mail: ", "texto?")),
             ESCRITA, (auditoria.EDICAO, "fornecedor")),
        Item("Desativar fornecedor", "fornecedores", "desativar_fornecedor",
             (_ID,), ESCRITA, (auditoria.DESATIVACAO, "fornecedor")),
    ]),
    ("Relatórios e consultas", [
        Item("Estoque atual", "relatorios", "relatorio_estoque"),
        Item("Produtos com estoque baixo", "relatorios", "produtos_estoque_baixo"),
        Item("Produtos sem estoque", "relatorios", "produtos_sem_estoque"),
        Item("Movimentações por período", "relatorios", "movimentacoes_por_periodo",
             (("data_inicio", "Data inicial (AAAA-MM-DD): ", "data"),
              ("data_fim", "Data final (AAAA-MM-DD): ", "data"))),
        Item("Movimentações por produto", "relatorios", "movimentacoes_por_produto",
             (("produto_id", "ID do produto: ", "int"),)),
        Item("Indicadores gerais", "relatorios", "indicadores_gerais"),
    ]),
    ("Funcionários", [
        Item("Cadastrar funcionário", "funcionarios", "cadastrar_funcionario",
             (("nome", "Nome: ", "texto"),
              ("login", "Login: ", "texto"),
              ("senha", "Senha: ", "senha"),
              ("perfil", "Perfil (ADMIN, ESTOQUISTA ou CONSULTA): ", "perfil")),
             SOMENTE_ADMIN, (auditoria.CADASTRO, "funcionario")),
        Item("Listar funcionários", "funcionarios", "listar_funcionarios",
             perfis=SOMENTE_ADMIN),
        Item("Editar funcionário", "funcionarios", "editar_funcionario",
             (_ID,
              ("nome", "Novo nome: ", "texto"),
              ("perfil", "Novo perfil (ADMIN, ESTOQUISTA ou CONSULTA): ", "perfil")),
             SOMENTE_ADMIN, (auditoria.EDICAO, "funcionario")),
        Item("Desativar funcionário", "funcionarios", "desativar_funcionario",
             (_ID,), SOMENTE_ADMIN, (auditoria.DESATIVACAO, "funcionario")),
    ]),
    ("Auditoria", [
        Item("Consultar eventos (Enter ignora o filtro)", "auditoria",
             "listar_eventos",
             (("funcionario_id", "ID do funcionário: ", "int?"),
              ("acao", "Ação (ex.: LOGIN, SAIDA): ", "texto?"),
              ("entidade", "Entidade (ex.: produto): ", "texto?"),
              ("data_inicio", "Data inicial: ", "data?"),
              ("data_fim", "Data final: ", "data?"),
              ("limite", "Quantidade máxima de registros: ", "int?")),
             SOMENTE_ADMIN),
    ]),
]


# --------------------------------------------------------------------------
# Programa principal
# --------------------------------------------------------------------------

def main():
    conexao = banco.conectar()
    try:
        banco.criar_tabelas(conexao)
        if not _primeiro_acesso(conexao):
            return 1
        usuario = _fazer_login(conexao)
        if usuario is None:
            return 1
        _menu_principal(Contexto(conexao, usuario))
    except (KeyboardInterrupt, EOFError):
        print("\nEncerrado.")
    finally:
        banco.fechar_conexao(conexao)
    return 0


if __name__ == "__main__":
    sys.exit(main())
