"""Front-end web (Flask) do Sistema de Gestão de Estoque.

Executar na raiz do projeto:

    python -m src.web            (abre em http://127.0.0.1:5000)

As telas são geradas a partir da tabela MENUS de src/main.py: cada opção do
menu de terminal vira uma página com formulário. Assim o terminal e o site
usam as MESMAS funções dos módulos (produtos, movimentacoes, ...), os mesmos
campos e as mesmas permissões por perfil. Uma opção nova em MENUS aparece no
site sem alterar este arquivo.

Segurança:
- Sessão assinada (defina SECRET_KEY no ambiente; sem ela, uma chave aleatória
  é gerada a cada início e as sessões antigas deixam de valer).
- Token CSRF em todo POST.
- Perfil conferido no servidor em cada requisição (funcionário desativado perde
  o acesso na hora); o menu escondido não substitui a verificação.
- Bloqueio temporário do login após várias falhas seguidas.
- Cabeçalhos de segurança (CSP restritiva, sem scripts inline).
"""

import hmac
import os
import re
import secrets
import time
from datetime import datetime

from flask import (
    Flask,
    abort,
    current_app,
    flash,
    g,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

try:
    from src import auditoria, autenticacao, banco, funcionarios, main, relatorios
except ImportError:  # quando executado de dentro da pasta src
    import auditoria
    import autenticacao
    import banco
    import funcionarios
    import main
    import relatorios

BLOQUEIO_SEGUNDOS = 60
ENDPOINTS_PUBLICOS = ("entrar", "primeiro_acesso")


def _agora():
    """Relógio do bloqueio de login (os testes substituem esta função)."""
    return time.time()


# --------------------------------------------------------------------------
# Banco, auditoria e menus
# --------------------------------------------------------------------------

def _conexao():
    """Conexão da requisição atual (aberta na 1ª vez, fechada ao final)."""
    if "conexao" not in g:
        g.conexao = banco.conectar(current_app.config["CAMINHO_BANCO"])
    return g.conexao


def _auditar(usuario, acao, entidade=None, entidade_id=None, detalhes=None):
    """Registra na auditoria sem derrubar a requisição se algo falhar."""
    try:
        auditoria.registrar_evento(
            usuario["id"] if usuario else None,
            acao, entidade, entidade_id, detalhes,
            conexao=_conexao(),
        )
    except Exception:  # a ação principal já foi concluída
        current_app.logger.warning("Falha ao registrar auditoria", exc_info=True)


def _auditar_item(usuario, item, valores, resultado):
    """Mesma regra de src/main.py: detalhes sem senha e id da entidade."""
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
    _auditar(usuario, acao, entidade, entidade_id, detalhes)


def _menus_visiveis(perfil):
    """[(indice_do_grupo, titulo, [(indice_do_item, item), ...]), ...]."""
    grupos = []
    for gi, (titulo, itens) in enumerate(main.MENUS):
        permitidos = [(ii, item) for ii, item in enumerate(itens) if perfil in item.perfis]
        if permitidos:
            grupos.append((gi, titulo, permitidos))
    return grupos


ATALHOS = ("Registrar entrada", "Registrar saída", "Cadastrar produto")


def _atalhos(perfil):
    """Ações mais usadas que o perfil pode executar: [(rotulo, gi, ii)]."""
    encontrados = []
    for rotulo in ATALHOS:
        for gi, _, itens in _menus_visiveis(perfil):
            for ii, item in itens:
                if item.rotulo == rotulo:
                    encontrados.append((rotulo, gi, ii))
    return encontrados


def _localizar(gi, ii):
    try:
        titulo, itens = main.MENUS[gi]
        return titulo, itens[ii]
    except IndexError:
        abort(404)


# --------------------------------------------------------------------------
# Campos do formulário e resultado
# --------------------------------------------------------------------------

def _campos_visiveis(item):
    """Campos que o usuário preenche, com tudo que o template precisa."""
    campos = []
    for param, pergunta, tipo in item.campos:
        if tipo == "@usuario":
            continue
        base = tipo.rstrip("?")
        rotulo = pergunta.strip().rstrip(":").strip()
        rotulo = re.sub(r"\s*\(opcional\)$", "", rotulo)   # o template já avisa
        if base == "perfil":
            rotulo = rotulo.split(" (")[0]
        campos.append({
            "nome": param,
            "rotulo": rotulo,
            "tipo": base,
            "opcional": tipo.endswith("?"),
        })
    return campos


def _ler_formulario(item, campos, formulario):
    """Converte o que foi digitado. Devolve (valores, erros_por_campo)."""
    erros = {}
    digitado = {}
    for campo in campos:
        bruto = formulario.get(campo["nome"], "")
        if campo["tipo"] != "senha":
            bruto = bruto.strip()
        if not bruto:
            if campo["opcional"]:
                digitado[campo["nome"]] = None
            else:
                erros[campo["nome"]] = "Campo obrigatório."
            continue
        try:
            digitado[campo["nome"]] = main._converter(bruto, campo["tipo"])
        except ValueError as erro:
            erros[campo["nome"]] = str(erro)

    valores = []
    for param, _, tipo in item.campos:
        valores.append(g.usuario["id"] if tipo == "@usuario" else digitado.get(param))
    return valores, erros


ROTULOS_DE_COLUNA = {
    "codigo": "Código", "descricao": "Descrição", "preco": "Preço",
    "situacao": "Situação", "funcionario": "Funcionário", "data_hora": "Data e hora",
    "estoque_atual": "Estoque", "estoque_minimo": "Mínimo", "valor_total": "Valor total",
    "quantidade": "Qtd.", "observacao": "Observação", "acao": "Ação",
    "id": "ID", "categoria_id": "ID categoria", "produto_id": "ID produto",
    "fornecedor_id": "ID fornecedor", "funcionario_id": "ID funcionário",
    "entidade_id": "ID registro",
}
COLUNAS_DE_DINHEIRO = ("preco", "valor")
SELOS_DE_SITUACAO = {"OK": "ok", "BAIXO": "baixo", "SEM ESTOQUE": "zero"}
SELOS_DE_TIPO = {"ENTRADA": "entrada", "SAIDA": "saida"}


def _moeda(valor):
    """1498.5 -> 'R$ 1.498,50' (formato brasileiro)."""
    try:
        texto = f"{float(valor):,.2f}"
    except (TypeError, ValueError):
        return "-"
    return "R$ " + texto.replace(",", "X").replace(".", ",").replace("X", ".")


def _data_hora(valor):
    """'2026-11-10 19:58:19' -> '10/11/2026 19:58' (devolve o original se não der)."""
    try:
        return datetime.fromisoformat(str(valor)).strftime("%d/%m/%Y %H:%M")
    except ValueError:
        return str(valor)


def _nivel(atual, minimo):
    """Dados do medidor de estoque: classe, % preenchido e % da marca do mínimo.

    A escala vai até o dobro do mínimo (ou o saldo, se maior), então o
    produto exatamente no mínimo fica com o preenchimento na marca.
    """
    escala = max(minimo * 2, atual, 1)
    if atual == 0:
        classe = "zero"
    elif atual < minimo:
        classe = "baixo"
    else:
        classe = "ok"
    return {
        "classe": classe,
        "preenchido": round(atual / escala * 100, 1),
        "marca": round(minimo / escala * 100, 1),
    }


def _e_numerica(coluna, valor):
    """Números de verdade (quantidades, valores) alinham à direita; ids e códigos não."""
    return (isinstance(valor, (int, float)) and not isinstance(valor, bool)
            and coluna not in ("id", "codigo") and not coluna.endswith("_id"))


def _formatar(valor):
    if valor is None:
        return "-"
    if isinstance(valor, float):
        return f"{valor:.2f}".replace(".", ",")
    return str(valor)


def _celula(coluna, valor, linha):
    """Uma célula da tabela: texto, classes e, se couber, selo ou medidor."""
    celula = {"texto": _formatar(valor), "classes": [], "selo": None, "nivel": None}
    if coluna.startswith(COLUNAS_DE_DINHEIRO) and isinstance(valor, (int, float)):
        celula["texto"] = _moeda(valor)
    elif coluna == "data_hora" and valor is not None:
        celula["texto"] = _data_hora(valor)
        celula["classes"].append("data")
    elif coluna == "situacao" and valor in SELOS_DE_SITUACAO:
        celula["selo"] = SELOS_DE_SITUACAO[valor]
        celula["texto"] = {"OK": "Em dia", "BAIXO": "Baixo", "SEM ESTOQUE": "Sem estoque"}[valor]
    elif coluna == "tipo" and valor in SELOS_DE_TIPO:
        celula["selo"] = SELOS_DE_TIPO[valor]
        celula["texto"] = "Entrada" if valor == "ENTRADA" else "Saída"
    elif coluna == "ativo" and isinstance(valor, (bool, int)):
        celula["selo"] = "ok" if valor else "inativo"
        celula["texto"] = "Ativo" if valor else "Inativo"
    elif (coluna == "estoque_atual" and isinstance(valor, int)
          and isinstance(linha.get("estoque_minimo"), int)):
        celula["nivel"] = _nivel(valor, linha["estoque_minimo"])

    if _e_numerica(coluna, valor):
        celula["classes"].append("num")
    if coluna == "codigo":
        celula["classes"].append("codigo")
    celula["classe"] = " ".join(celula["classes"])
    return celula


def _preparar_resultado(resultado):
    """Transforma o retorno de uma função em algo que o template desenha."""
    if isinstance(resultado, bool):
        return {"tipo": "texto", "texto": "Operação concluída com sucesso."
                if resultado else "Operação não realizada."}
    if resultado is None:
        return {"tipo": "texto", "texto": "Operação concluída com sucesso."}
    if isinstance(resultado, int):
        return {"tipo": "texto", "texto": f"Concluído. ID: {resultado}"}
    if isinstance(resultado, str):
        return {"tipo": "texto", "texto": resultado}
    if isinstance(resultado, (list, tuple)):
        if not resultado:
            return {"tipo": "vazio", "texto": "Nenhum registro encontrado."}
        if isinstance(resultado[0], (str, int, float, type(None))):
            resultado = [resultado]                     # uma única linha (tupla)
        linhas = [main._como_dict(linha) for linha in resultado]
        colunas = []
        for linha in linhas:
            for coluna in linha:
                if coluna not in colunas:
                    colunas.append(coluna)
        return {
            "tipo": "tabela",
            "colunas": [
                {"rotulo": ROTULOS_DE_COLUNA.get(c, c.replace("_", " ").capitalize()),
                 "numerica": any(_e_numerica(c, linha.get(c)) for linha in linhas)}
                for c in colunas
            ],
            "linhas": [[_celula(c, linha.get(c), linha) for c in colunas] for linha in linhas],
            "total": len(linhas),
        }
    pares = [(ROTULOS_DE_COLUNA.get(str(k), str(k).replace("_", " ").capitalize()),
              _formatar(v))
             for k, v in main._como_dict(resultado).items()]
    return {"tipo": "detalhes", "pares": pares}


def _produtos_para_repor(conexao, limite=8):
    """Produtos sem estoque ou abaixo do mínimo, os zerados primeiro."""
    itens = [
        {**item, "nivel": _nivel(item["estoque_atual"], item["estoque_minimo"])}
        for item in relatorios.relatorio_estoque(conexao=conexao)
        if item["situacao"] != "OK"
    ]
    itens.sort(key=lambda i: (i["estoque_atual"] > 0, i["estoque_atual"] - i["estoque_minimo"]))
    return itens[:limite], len(itens)


def _mensagem_sucesso(resultado):
    if isinstance(resultado, int) and not isinstance(resultado, bool):
        return f"Operação concluída. ID: {resultado}"
    if isinstance(resultado, dict) and "id" in resultado:
        return f"Operação concluída. ID: {resultado['id']}"
    return "Operação concluída com sucesso."


# --------------------------------------------------------------------------
# Aplicação
# --------------------------------------------------------------------------

def criar_app(caminho_banco=None, config=None):
    """Cria a aplicação. `caminho_banco=None` usa o banco padrão do projeto."""
    app = Flask(__name__)
    app.config.update(
        SECRET_KEY=os.environ.get("SECRET_KEY") or secrets.token_hex(32),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        CAMINHO_BANCO=caminho_banco,
        MAX_TENTATIVAS_LOGIN=main.MAX_TENTATIVAS_LOGIN,
    )
    if config:
        app.config.update(config)

    app.extensions["falhas_login"] = {}   # login -> {"conta": int, "ate": float}

    inicial = banco.conectar(app.config["CAMINHO_BANCO"])
    try:
        banco.criar_tabelas(inicial)
    finally:
        banco.fechar_conexao(inicial)

    # ---------- infraestrutura ----------

    def token_csrf():
        if "csrf" not in session:
            session["csrf"] = secrets.token_hex(16)
        return session["csrf"]

    app.jinja_env.globals["csrf_token"] = token_csrf
    app.jinja_env.filters["moeda"] = _moeda

    @app.context_processor
    def contexto():
        usuario = g.get("usuario")
        return {
            "usuario": usuario,
            "menu": _menus_visiveis(usuario["perfil"]) if usuario else [],
        }

    @app.teardown_appcontext
    def fechar_conexao(_erro):
        conexao = g.pop("conexao", None)
        if conexao is not None:
            banco.fechar_conexao(conexao)

    @app.after_request
    def cabecalhos_de_seguranca(resposta):
        resposta.headers.setdefault("X-Content-Type-Options", "nosniff")
        resposta.headers.setdefault("X-Frame-Options", "DENY")
        resposta.headers.setdefault("Referrer-Policy", "same-origin")
        resposta.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; style-src 'self'; script-src 'self'; "
            "frame-ancestors 'none'; form-action 'self'",
        )
        resposta.headers.setdefault("Cache-Control", "no-store")
        return resposta

    @app.before_request
    def proteger_e_autenticar():
        g.usuario = None
        if request.endpoint in (None, "static"):
            return None

        if request.method == "POST":
            enviado = request.form.get("csrf_token", "").encode("utf-8")
            esperado = session.get("csrf", "").encode("utf-8")
            if not esperado or not hmac.compare_digest(enviado, esperado):
                abort(400, "Sessão expirada ou formulário inválido. Recarregue a página.")

        conexao = _conexao()
        total = conexao.execute("SELECT COUNT(*) FROM funcionarios").fetchone()[0]
        if total == 0:
            if request.endpoint != "primeiro_acesso":
                return redirect(url_for("primeiro_acesso"))
            return None

        usuario_id = session.get("usuario_id")
        if usuario_id is not None:
            atual = funcionarios.buscar_funcionario(usuario_id, conexao=conexao)
            if atual and atual["ativo"]:
                g.usuario = atual
            else:
                session.clear()
        if g.usuario is None and request.endpoint not in ENDPOINTS_PUBLICOS:
            return redirect(url_for("entrar"))
        return None

    @app.errorhandler(400)
    @app.errorhandler(403)
    @app.errorhandler(404)
    def pagina_de_erro(erro):
        mensagens = {
            400: erro.description if erro.description else "Requisição inválida.",
            403: "Você não tem permissão para acessar esta página.",
            404: "Página não encontrada.",
        }
        return render_template(
            "erro.html", codigo=erro.code, mensagem=mensagens[erro.code]
        ), erro.code

    # ---------- primeiro acesso e login ----------

    @app.route("/primeiro-acesso", methods=["GET", "POST"])
    def primeiro_acesso():
        conexao = _conexao()
        if conexao.execute("SELECT COUNT(*) FROM funcionarios").fetchone()[0]:
            return redirect(url_for("entrar"))

        valores = {"nome": "", "login": ""}
        if request.method == "POST":
            valores = {c: request.form.get(c, "").strip() for c in ("nome", "login")}
            senha = request.form.get("senha", "")
            if senha != request.form.get("confirmacao", ""):
                flash("As senhas não conferem.", "erro")
            else:
                try:
                    funcionarios.cadastrar_funcionario(
                        valores["nome"], valores["login"], senha,
                        autenticacao.ADMIN, conexao=conexao,
                    )
                except ValueError as erro:
                    flash(str(erro), "erro")
                else:
                    _auditar(None, auditoria.CADASTRO, "funcionario", None, {
                        "login": valores["login"], "perfil": autenticacao.ADMIN,
                        "origem": "primeiro acesso",
                    })
                    flash("Administrador criado. Entre com o login e a senha cadastrados.", "ok")
                    return redirect(url_for("entrar"))
        return render_template("primeiro_acesso.html", valores=valores)

    @app.route("/entrar", methods=["GET", "POST"])
    def entrar():
        if g.usuario:
            return redirect(url_for("inicio"))

        login = ""
        if request.method == "POST":
            login = request.form.get("login", "").strip()
            chave = autenticacao.normalizar_login(login)
            falhas = app.extensions["falhas_login"].get(chave, {"conta": 0, "ate": 0})

            if falhas["ate"] > _agora():
                restante = int(falhas["ate"] - _agora()) + 1
                flash(f"Muitas tentativas. Aguarde {restante} s para tentar de novo.", "erro")
                return render_template("entrar.html", login=login), 429

            usuario = autenticacao.login(
                login, request.form.get("senha", ""), conexao=_conexao()
            )
            if usuario:
                app.extensions["falhas_login"].pop(chave, None)
                session.clear()
                session["usuario_id"] = usuario["id"]
                _auditar(usuario, auditoria.LOGIN)
                return redirect(url_for("inicio"))

            falhas["conta"] += 1
            if falhas["conta"] >= app.config["MAX_TENTATIVAS_LOGIN"]:
                falhas = {"conta": 0, "ate": _agora() + BLOQUEIO_SEGUNDOS}
            app.extensions["falhas_login"][chave] = falhas
            _auditar(None, auditoria.LOGIN_FALHA, detalhes=f"login={login}")
            flash(autenticacao.MENSAGEM_LOGIN_INVALIDO, "erro")
            return render_template("entrar.html", login=login), 401
        return render_template("entrar.html", login=login)

    @app.post("/sair")
    def sair():
        _auditar(g.usuario, auditoria.LOGOUT)
        session.clear()
        flash("Você saiu do sistema.", "ok")
        return redirect(url_for("entrar"))

    # ---------- páginas do sistema ----------

    @app.get("/")
    def inicio():
        conexao = _conexao()
        repor, total_repor = _produtos_para_repor(conexao)
        return render_template(
            "inicio.html",
            indicadores=relatorios.indicadores_gerais(conexao=conexao),
            repor=repor,
            total_repor=total_repor,
            atalhos=_atalhos(g.usuario["perfil"]),
        )

    @app.route("/m/<int:gi>/<int:ii>", methods=["GET", "POST"])
    def operacao(gi, ii):
        titulo, item = _localizar(gi, ii)
        if g.usuario["perfil"] not in item.perfis:
            abort(403)

        campos = _campos_visiveis(item)
        contexto_base = {"item": item, "grupo": titulo, "campos": campos,
                         "valores": {}, "erros": {}, "resultado": None}

        if request.method == "GET":
            # Consultas sem filtros (listagens, relatórios) abrem direto.
            if not campos and item.auditoria is None:
                return _executar(item, campos, contexto_base, {})
            contexto_base["valores"] = request.args.to_dict()   # ex.: ?id=3
            return render_template("operacao.html", **contexto_base)

        return _executar(item, campos, contexto_base, request.form)

    def _executar(item, campos, contexto_base, formulario):
        valores, erros = _ler_formulario(item, campos, formulario)
        digitado = {k: v for k, v in formulario.items()
                    if k not in ("csrf_token",) and
                    not any(c["nome"] == k and c["tipo"] == "senha" for c in campos)}
        contexto_base.update(valores=digitado, erros=erros)
        if erros:
            return render_template("operacao.html", **contexto_base), 400

        try:
            resultado = main._chamar(item.modulo, item.funcao, valores, _conexao())
        except Exception as erro:
            contexto_base["erro"] = main._mensagem_de_erro(erro)
            status = 400 if isinstance(erro, ValueError) else 500
            return render_template("operacao.html", **contexto_base), status

        if item.auditoria:
            _auditar_item(g.usuario, item, valores, resultado)
            # Redireciona para evitar reenvio do formulário ao recarregar.
            flash(_mensagem_sucesso(resultado), "ok")
            return redirect(request.path)

        contexto_base["resultado"] = _preparar_resultado(resultado)
        return render_template("operacao.html", **contexto_base)

    return app


def main_web():
    """Ponto de entrada: python -m src.web"""
    criar_app().run(host="127.0.0.1", port=int(os.environ.get("PORT", "5000")))


if __name__ == "__main__":
    main_web()
