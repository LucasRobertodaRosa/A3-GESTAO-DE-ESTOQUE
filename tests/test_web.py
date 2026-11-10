"""Testes do front-end web (src/web.py) com o test_client do Flask.

Não abrem navegador nem servidor: rodam no CI como qualquer outro teste.
Usam um banco temporário (CAMINHO_PADRAO apontado para um arquivo novo a cada
teste) e baixam o custo do bcrypt para os testes ficarem rápidos.
Rodar a partir da raiz do projeto:  python -m pytest tests/test_web.py
"""

import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src import auditoria, autenticacao, banco, funcionarios, main, web

TOKEN = "token-de-teste"
SENHA = "segredo1"


def _url_da_opcao(rotulo):
    """Endereço da página gerada para a opção de menu com este rótulo."""
    for gi, (_, itens) in enumerate(main.MENUS):
        for ii, item in enumerate(itens):
            if item.rotulo == rotulo:
                return f"/m/{gi}/{ii}"
    raise AssertionError(f"Opção de menu inexistente: {rotulo}")


class BaseWeb(unittest.TestCase):
    def setUp(self):
        pasta = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, pasta, ignore_errors=True)
        for alvo, atributo, valor in (
            (banco, "CAMINHO_PADRAO", Path(pasta) / "teste.db"),
            (autenticacao, "CUSTO_BCRYPT", 4),
        ):
            patcher = patch.object(alvo, atributo, valor)
            patcher.start()
            self.addCleanup(patcher.stop)

        self.app = web.criar_app(config={"TESTING": True, "SECRET_KEY": "chave-de-teste"})
        self.cliente = self.app.test_client()

    # ---------- utilitários ----------

    def _post(self, url, cliente=None, **dados):
        """POST com token CSRF válido (o token é gravado na sessão do cliente)."""
        cliente = cliente or self.cliente
        with cliente.session_transaction() as sessao:
            sessao.setdefault("csrf", TOKEN)
            token = sessao["csrf"]
        dados["csrf_token"] = token
        return cliente.post(url, data=dados)

    def _banco(self):
        conexao = banco.conectar()
        self.addCleanup(banco.fechar_conexao, conexao)
        return conexao

    def _criar_funcionario(self, login="ana", perfil="ADMIN", nome=None):
        conexao = self._banco()
        return funcionarios.cadastrar_funcionario(
            nome or login.capitalize(), login, SENHA, perfil, conexao=conexao
        )

    def _entrar(self, login="ana", perfil="ADMIN"):
        """Cria o funcionário (se preciso) e faz o login pelo site."""
        if not self._existe(login):
            self._criar_funcionario(login, perfil)
        resposta = self._post("/entrar", login=login, senha=SENHA)
        self.assertEqual(resposta.status_code, 302)

    def _existe(self, login):
        linha = self._banco().execute(
            "SELECT 1 FROM funcionarios WHERE login = ?", (login,)
        ).fetchone()
        return linha is not None

    def _acoes_de_auditoria(self):
        return [e["acao"] for e in auditoria.listar_eventos(conexao=self._banco())]

    def _html(self, resposta):
        return resposta.get_data(as_text=True)


class TestPrimeiroAcesso(BaseWeb):
    def test_sem_funcionarios_tudo_leva_ao_primeiro_acesso(self):
        for caminho in ("/", "/entrar", "/m/0/0"):
            with self.subTest(caminho=caminho):
                resposta = self.cliente.get(caminho)
                self.assertEqual(resposta.status_code, 302)
                self.assertTrue(resposta.headers["Location"].endswith("/primeiro-acesso"))

    def test_cria_o_administrador_inicial_e_audita(self):
        resposta = self._post(
            "/primeiro-acesso", nome="Ana Admin", login="ana",
            senha=SENHA, confirmacao=SENHA,
        )

        self.assertEqual(resposta.status_code, 302)
        self.assertTrue(resposta.headers["Location"].endswith("/entrar"))
        usuario = autenticacao.login("ana", SENHA)
        self.assertEqual(usuario["perfil"], "ADMIN")
        self.assertEqual(self._acoes_de_auditoria(), ["CADASTRO"])

    def test_senhas_diferentes_nao_criam_ninguem(self):
        resposta = self._post(
            "/primeiro-acesso", nome="Ana", login="ana", senha=SENHA, confirmacao="outra123"
        )

        self.assertEqual(resposta.status_code, 200)
        self.assertIn("As senhas não conferem.", self._html(resposta))
        self.assertEqual(funcionarios.listar_funcionarios(), [])

    def test_senha_fraca_mostra_o_erro_e_mantem_o_que_foi_digitado(self):
        resposta = self._post(
            "/primeiro-acesso", nome="Ana", login="ana", senha="123", confirmacao="123"
        )

        html = self._html(resposta)
        self.assertIn("pelo menos", html)
        self.assertIn('value="ana"', html)
        self.assertEqual(funcionarios.listar_funcionarios(), [])

    def test_com_funcionario_cadastrado_a_tela_de_primeiro_acesso_some(self):
        self._criar_funcionario()

        resposta = self.cliente.get("/primeiro-acesso")

        self.assertEqual(resposta.status_code, 302)
        self.assertTrue(resposta.headers["Location"].endswith("/entrar"))


class TestLogin(BaseWeb):
    def setUp(self):
        super().setUp()
        self._criar_funcionario("ana", "ADMIN")

    def test_pagina_de_login_abre_sem_estar_logado(self):
        resposta = self.cliente.get("/entrar")

        self.assertEqual(resposta.status_code, 200)
        self.assertIn('name="senha"', self._html(resposta))

    def test_paginas_internas_exigem_login(self):
        for caminho in ("/", "/m/0/0"):
            with self.subTest(caminho=caminho):
                resposta = self.cliente.get(caminho)
                self.assertEqual(resposta.status_code, 302)
                self.assertTrue(resposta.headers["Location"].endswith("/entrar"))

    def test_login_correto_leva_ao_painel_e_audita(self):
        resposta = self._post("/entrar", login="ANA", senha=SENHA)

        self.assertEqual(resposta.status_code, 302)
        painel = self.cliente.get("/")
        self.assertEqual(painel.status_code, 200)
        self.assertIn("Painel", self._html(painel))
        self.assertEqual(self._acoes_de_auditoria(), ["LOGIN"])

    def test_quem_ja_esta_logado_nao_ve_a_tela_de_login(self):
        self._entrar()

        resposta = self.cliente.get("/entrar")

        self.assertEqual(resposta.status_code, 302)

    def test_senha_errada_mostra_mensagem_generica_e_audita(self):
        resposta = self._post("/entrar", login="ana", senha="errada123")

        self.assertEqual(resposta.status_code, 401)
        self.assertIn("Login ou senha inválidos.", self._html(resposta))
        self.assertEqual(self._acoes_de_auditoria(), ["LOGIN_FALHA"])

    def test_login_inexistente_tem_a_mesma_mensagem(self):
        resposta = self._post("/entrar", login="ninguem", senha=SENHA)

        self.assertEqual(resposta.status_code, 401)
        self.assertIn("Login ou senha inválidos.", self._html(resposta))

    def test_bloqueia_apos_o_maximo_de_falhas_e_libera_depois(self):
        relogio = [1000.0]
        with patch.object(web, "_agora", lambda: relogio[0]):
            for _ in range(main.MAX_TENTATIVAS_LOGIN):
                self._post("/entrar", login="ana", senha="errada123")

            bloqueado = self._post("/entrar", login="ana", senha=SENHA)
            self.assertEqual(bloqueado.status_code, 429)
            self.assertIn("Aguarde", self._html(bloqueado))

            relogio[0] += web.BLOQUEIO_SEGUNDOS + 1
            liberado = self._post("/entrar", login="ana", senha=SENHA)
            self.assertEqual(liberado.status_code, 302)

    def test_login_certo_zera_a_contagem_de_falhas(self):
        for _ in range(main.MAX_TENTATIVAS_LOGIN - 1):
            self._post("/entrar", login="ana", senha="errada123")
        self._post("/entrar", login="ana", senha=SENHA)
        self._post("/sair")

        for _ in range(main.MAX_TENTATIVAS_LOGIN - 1):
            resposta = self._post("/entrar", login="ana", senha="errada123")
            self.assertEqual(resposta.status_code, 401)

    def test_sair_encerra_a_sessao_e_audita(self):
        self._entrar()

        resposta = self._post("/sair")

        self.assertEqual(resposta.status_code, 302)
        self.assertTrue(self.cliente.get("/").headers["Location"].endswith("/entrar"))
        self.assertCountEqual(self._acoes_de_auditoria(), ["LOGIN", "LOGOUT"])

    def test_funcionario_desativado_perde_o_acesso_na_hora(self):
        self._entrar()
        beto = self._criar_funcionario("beto", "ESTOQUISTA")
        cliente_beto = self.app.test_client()
        self._post("/entrar", cliente=cliente_beto, login="beto", senha=SENHA)
        self.assertEqual(cliente_beto.get("/").status_code, 200)

        funcionarios.desativar_funcionario(beto)

        resposta = cliente_beto.get("/")
        self.assertEqual(resposta.status_code, 302)
        self.assertTrue(resposta.headers["Location"].endswith("/entrar"))

    def test_falha_na_auditoria_nao_derruba_o_login(self):
        with patch.object(auditoria, "registrar_evento", side_effect=RuntimeError("boom")), \
                self.assertLogs(self.app.logger, "WARNING"):
            resposta = self._post("/entrar", login="ana", senha=SENHA)

        self.assertEqual(resposta.status_code, 302)


class TestSeguranca(BaseWeb):
    def test_post_sem_token_csrf_e_recusado(self):
        self._criar_funcionario()

        resposta = self.cliente.post("/entrar", data={"login": "ana", "senha": SENHA})

        self.assertEqual(resposta.status_code, 400)

    def test_post_com_token_errado_e_recusado(self):
        self._criar_funcionario()
        self.cliente.get("/entrar")
        with self.cliente.session_transaction() as sessao:
            sessao["csrf"] = TOKEN

        resposta = self.cliente.post(
            "/entrar", data={"login": "ana", "senha": SENHA, "csrf_token": "outro"}
        )

        self.assertEqual(resposta.status_code, 400)

    def test_cabecalhos_de_seguranca(self):
        self._criar_funcionario()

        resposta = self.cliente.get("/entrar")

        self.assertEqual(resposta.headers["X-Frame-Options"], "DENY")
        self.assertEqual(resposta.headers["X-Content-Type-Options"], "nosniff")
        self.assertIn("default-src 'self'", resposta.headers["Content-Security-Policy"])
        self.assertEqual(resposta.headers["Cache-Control"], "no-store")

    def test_paginas_nao_tem_script_inline(self):
        self._criar_funcionario()

        html = self._html(self.cliente.get("/entrar"))

        self.assertNotIn("onsubmit=", html)
        self.assertNotIn("<script>", html)

    def test_arquivos_estaticos_nao_exigem_login(self):
        resposta = self.cliente.get("/static/estilo.css")
        self.addCleanup(resposta.close)

        self.assertEqual(resposta.status_code, 200)

    def test_pagina_inexistente_da_404(self):
        self._criar_funcionario()
        self._entrar()

        resposta = self.cliente.get("/nao-existe")

        self.assertEqual(resposta.status_code, 404)
        self.assertIn("Página não encontrada", self._html(resposta))

    def test_opcao_de_menu_inexistente_da_404(self):
        self._criar_funcionario()
        self._entrar()

        for caminho in ("/m/99/0", "/m/0/99"):
            with self.subTest(caminho=caminho):
                self.assertEqual(self.cliente.get(caminho).status_code, 404)

    def test_chave_secreta_vem_do_ambiente(self):
        with patch.dict("os.environ", {"SECRET_KEY": "do-ambiente"}):
            app = web.criar_app()

        self.assertEqual(app.config["SECRET_KEY"], "do-ambiente")


class TestPermissoes(BaseWeb):
    def setUp(self):
        super().setUp()
        self._criar_funcionario("ana", "ADMIN")
        self._criar_funcionario("lia", "CONSULTA")
        self._criar_funcionario("edu", "ESTOQUISTA")

    def _logar_como(self, login):
        cliente = self.app.test_client()
        resposta = self._post("/entrar", cliente=cliente, login=login, senha=SENHA)
        self.assertEqual(resposta.status_code, 302)
        return cliente

    def test_consulta_nao_ve_nem_acessa_opcoes_de_escrita(self):
        cliente = self._logar_como("lia")
        escrita = _url_da_opcao("Cadastrar categoria")

        painel = self._html(cliente.get("/"))
        self.assertNotIn(escrita, painel)
        self.assertNotIn("Cadastrar produto", painel)
        self.assertEqual(cliente.get(escrita).status_code, 403)
        self.assertEqual(
            self._post(escrita, cliente=cliente, nome="X", descricao="").status_code, 403
        )

    def test_consulta_consegue_consultar(self):
        cliente = self._logar_como("lia")

        resposta = cliente.get(_url_da_opcao("Listar produtos"))

        self.assertEqual(resposta.status_code, 200)

    def test_somente_admin_acessa_funcionarios_e_auditoria(self):
        restritas = [_url_da_opcao("Listar funcionários"),
                     _url_da_opcao("Consultar eventos (Enter ignora o filtro)")]
        for login, esperado in (("ana", 200), ("edu", 403), ("lia", 403)):
            cliente = self._logar_como(login)
            for url in restritas:
                with self.subTest(login=login, url=url):
                    self.assertEqual(cliente.get(url).status_code, esperado)

    def test_estoquista_escreve_mas_nao_gerencia_funcionarios(self):
        cliente = self._logar_como("edu")

        self.assertEqual(cliente.get(_url_da_opcao("Cadastrar categoria")).status_code, 200)
        self.assertEqual(cliente.get(_url_da_opcao("Cadastrar funcionário")).status_code, 403)

    def test_cada_perfil_ve_so_as_opcoes_permitidas_no_menu(self):
        for perfil in main.PERFIS:
            visiveis = web._menus_visiveis(perfil)
            for _, _, itens in visiveis:
                for _, item in itens:
                    self.assertIn(perfil, item.perfis)


class TestFluxoDeEstoque(BaseWeb):
    """O caminho principal do sistema, pelas telas: do cadastro ao relatório."""

    def setUp(self):
        super().setUp()
        self._entrar()

    def _cadastrar_categoria_e_produto(self):
        self._post(_url_da_opcao("Cadastrar categoria"), nome="Informática", descricao="")
        self._post(
            _url_da_opcao("Cadastrar produto"), codigo="TEC-01", nome="Teclado USB",
            preco="99,90", estoque_minimo="2", categoria_id="1",
        )

    def test_cadastro_mostra_confirmacao_depois_do_redirecionamento(self):
        resposta = self._post(_url_da_opcao("Cadastrar categoria"), nome="Informática", descricao="")

        self.assertEqual(resposta.status_code, 302)  # evita reenvio ao recarregar
        pagina = self.cliente.get(resposta.headers["Location"])
        self.assertIn("Operação concluída", self._html(pagina))

    def test_fluxo_completo_entrada_saida_saldo_e_relatorio(self):
        self._cadastrar_categoria_e_produto()

        entrada = self._post(
            _url_da_opcao("Registrar entrada"), produto_id="1", quantidade="15", fornecedor_id=""
        )
        saida = self._post(
            _url_da_opcao("Registrar saída"), produto_id="1", quantidade="3", destinatario="Sala de TI"
        )
        excesso = self._post(
            _url_da_opcao("Registrar saída"), produto_id="1", quantidade="20", destinatario=""
        )

        self.assertEqual((entrada.status_code, saida.status_code), (302, 302))
        self.assertEqual(excesso.status_code, 400)
        self.assertIn("Estoque insuficiente", self._html(excesso))
        relatorio = self._html(self.cliente.get(_url_da_opcao("Estoque atual")))
        self.assertIn("TEC-01", relatorio)
        self.assertIn("<td>12</td>", relatorio)
        historico = self._html(self.cliente.get(_url_da_opcao("Histórico de movimentações")))
        self.assertIn("ENTRADA", historico)
        self.assertIn("SAIDA", historico)

    def test_movimentacao_e_registrada_na_auditoria_com_o_usuario_logado(self):
        self._cadastrar_categoria_e_produto()

        self._post(_url_da_opcao("Registrar entrada"), produto_id="1", quantidade="5", fornecedor_id="")

        eventos = auditoria.listar_eventos(acao="ENTRADA", conexao=self._banco())
        self.assertEqual(len(eventos), 1)
        self.assertEqual(eventos[0]["funcionario_id"], 1)

    def test_painel_mostra_os_indicadores(self):
        self._cadastrar_categoria_e_produto()
        self._post(_url_da_opcao("Registrar entrada"), produto_id="1", quantidade="15", fornecedor_id="")

        painel = self._html(self.cliente.get("/"))

        self.assertIn("Produtos ativos", painel)
        self.assertIn("R$ 1498,50", painel)

    def test_busca_de_produto_por_texto_sem_acento(self):
        self._cadastrar_categoria_e_produto()

        resposta = self._post(_url_da_opcao("Buscar produto (nome, código ou categoria)"), termo="informatica")

        self.assertIn("TEC-01", self._html(resposta))

    def test_listagem_abre_direto_e_vazia_avisa(self):
        resposta = self.cliente.get(_url_da_opcao("Listar produtos"))

        self.assertEqual(resposta.status_code, 200)
        self.assertIn("Nenhum registro encontrado.", self._html(resposta))

    def test_campo_obrigatorio_em_branco_volta_com_erro_no_campo(self):
        resposta = self._post(_url_da_opcao("Cadastrar categoria"), nome="", descricao="")

        self.assertEqual(resposta.status_code, 400)
        self.assertIn("Campo obrigatório.", self._html(resposta))

    def test_numero_invalido_volta_com_erro_e_nao_chama_o_modulo(self):
        self._cadastrar_categoria_e_produto()

        resposta = self._post(
            _url_da_opcao("Registrar entrada"), produto_id="abc", quantidade="1", fornecedor_id=""
        )

        self.assertEqual(resposta.status_code, 400)
        self.assertIn("Informe um número inteiro.", self._html(resposta))
        self.assertEqual(self._acoes_de_auditoria().count("ENTRADA"), 0)

    def test_erro_de_regra_de_negocio_aparece_para_o_usuario(self):
        self._post(_url_da_opcao("Cadastrar categoria"), nome="Informática", descricao="")

        resposta = self._post(_url_da_opcao("Cadastrar categoria"), nome="informática", descricao="")

        self.assertEqual(resposta.status_code, 400)
        self.assertIn("Já existe uma categoria", self._html(resposta))

    def test_o_que_foi_digitado_volta_preenchido_apos_erro(self):
        resposta = self._post(
            _url_da_opcao("Registrar entrada"), produto_id="999", quantidade="1", fornecedor_id=""
        )

        self.assertEqual(resposta.status_code, 400)
        self.assertIn('value="999"', self._html(resposta))

    def test_consulta_com_filtros_opcionais_em_branco(self):
        resposta = self._post(
            _url_da_opcao("Consultar eventos (Enter ignora o filtro)"),
            funcionario_id="", acao="", entidade="", data_inicio="", data_fim="", limite="",
        )

        self.assertEqual(resposta.status_code, 200)
        self.assertIn("LOGIN", self._html(resposta))

    def test_relatorio_por_periodo_aceita_datas_do_formulario(self):
        resposta = self._post(
            _url_da_opcao("Movimentações por período"),
            data_inicio="2026-01-01", data_fim="2026-12-31",
        )

        self.assertEqual(resposta.status_code, 200)

    def test_id_na_url_preenche_o_formulario(self):
        resposta = self.cliente.get(_url_da_opcao("Buscar categoria") + "?id=7")

        self.assertIn('value="7"', self._html(resposta))

    def test_desativar_pede_confirmacao_no_navegador(self):
        resposta = self.cliente.get(_url_da_opcao("Desativar produto"))

        self.assertIn('data-confirmar="Confirma a desativação?"', self._html(resposta))

    def test_edicao_devolve_confirmacao_com_o_id(self):
        self._cadastrar_categoria_e_produto()

        resposta = self._post(
            _url_da_opcao("Editar categoria"), id="1", nome="Periféricos", descricao="",
        )

        self.assertEqual(resposta.status_code, 302)
        pagina = self._html(self.cliente.get(resposta.headers["Location"]))
        self.assertIn("ID: 1", pagina)


class TestFuncionariosPeloSite(BaseWeb):
    def setUp(self):
        super().setUp()
        self._entrar()

    def test_admin_cadastra_funcionario_e_ele_consegue_entrar(self):
        resposta = self._post(
            _url_da_opcao("Cadastrar funcionário"),
            nome="Beto", login="beto", senha=SENHA, perfil="ESTOQUISTA",
        )

        self.assertEqual(resposta.status_code, 302)
        cliente = self.app.test_client()
        self.assertEqual(
            self._post("/entrar", cliente=cliente, login="beto", senha=SENHA).status_code, 302
        )

    def test_senha_nunca_aparece_na_pagina_nem_na_auditoria(self):
        self._post(
            _url_da_opcao("Cadastrar funcionário"),
            nome="Beto", login="beto", senha=SENHA, perfil="CONSULTA",
        )

        pagina = self._html(self.cliente.get(_url_da_opcao("Listar funcionários")))
        eventos = auditoria.listar_eventos(acao="CADASTRO", conexao=self._banco())

        self.assertNotIn(SENHA, pagina)
        self.assertNotIn("senha_hash", pagina)
        self.assertNotIn(SENHA, str(eventos))

    def test_login_repetido_mostra_o_erro(self):
        resposta = self._post(
            _url_da_opcao("Cadastrar funcionário"),
            nome="Outra Ana", login="ana", senha=SENHA, perfil="CONSULTA",
        )

        self.assertEqual(resposta.status_code, 400)
        self.assertIn("Já existe um funcionário", self._html(resposta))

    def test_senha_nao_volta_preenchida_apos_erro(self):
        resposta = self._post(
            _url_da_opcao("Cadastrar funcionário"),
            nome="Outra Ana", login="ana", senha=SENHA, perfil="CONSULTA",
        )

        self.assertNotIn(f'value="{SENHA}"', self._html(resposta))

    def test_ultimo_administrador_nao_pode_ser_desativado(self):
        resposta = self._post(_url_da_opcao("Desativar funcionário"), id="1")

        self.assertEqual(resposta.status_code, 400)
        self.assertIn("último administrador", self._html(resposta))


class TestErrosInesperados(BaseWeb):
    def setUp(self):
        super().setUp()
        self._entrar()

    def test_excecao_inesperada_vira_pagina_de_erro_sem_derrubar_o_site(self):
        with patch.object(main, "_chamar", side_effect=RuntimeError("falha")):
            resposta = self._post(_url_da_opcao("Cadastrar categoria"), nome="X", descricao="")

        self.assertEqual(resposta.status_code, 500)
        self.assertIn("Erro inesperado", self._html(resposta))
        self.assertEqual(self.cliente.get("/").status_code, 200)

    def test_modulo_nao_integrado_avisa_que_esta_indisponivel(self):
        with patch.object(main, "_chamar", side_effect=main.NaoIntegrado("falta")):
            resposta = self.cliente.get(_url_da_opcao("Listar produtos"))

        self.assertIn("Indisponível", self._html(resposta))


class TestPrepararResultado(unittest.TestCase):
    def test_tipos_de_retorno_das_funcoes(self):
        casos = {
            "bool verdadeiro": (True, "texto", "Operação concluída com sucesso."),
            "bool falso": (False, "texto", "Operação não realizada."),
            "none": (None, "texto", "Operação concluída com sucesso."),
            "id": (7, "texto", "Concluído. ID: 7"),
            "texto": ("ok", "texto", "ok"),
            "lista vazia": ([], "texto", "Nenhum registro encontrado."),
        }
        for nome, (entrada, tipo, texto) in casos.items():
            with self.subTest(nome):
                saida = web._preparar_resultado(entrada)
                self.assertEqual((saida["tipo"], saida["texto"]), (tipo, texto))

    def test_lista_de_dicionarios_vira_tabela_com_colunas_unidas(self):
        saida = web._preparar_resultado([{"id": 1, "preco": 9.5}, {"id": 2, "nome": None}])

        self.assertEqual(saida["tipo"], "tabela")
        self.assertEqual(saida["colunas"], ["Id", "Preco", "Nome"])
        self.assertEqual(saida["linhas"], [["1", "9,50", "-"], ["2", "-", "-"]])
        self.assertEqual(saida["total"], 2)

    def test_tupla_de_valores_e_uma_unica_linha(self):
        saida = web._preparar_resultado((1, "a"))

        self.assertEqual(saida["total"], 1)

    def test_dicionario_vira_pares_chave_valor(self):
        saida = web._preparar_resultado({"total_produtos": 3})

        self.assertEqual(saida, {"tipo": "detalhes", "pares": [("Total produtos", "3")]})

    def test_rotulo_do_campo_opcional_nao_repete_opcional(self):
        item = main.Item("X", "m", "f", (("complemento", "Complemento (opcional): ", "texto?"),
                                          ("perfil", "Perfil (ADMIN ou CONSULTA): ", "perfil")))

        rotulos = [campo["rotulo"] for campo in web._campos_visiveis(item)]

        self.assertEqual(rotulos, ["Complemento", "Perfil"])

    def test_mensagem_de_sucesso(self):
        self.assertEqual(web._mensagem_sucesso(4), "Operação concluída. ID: 4")
        self.assertEqual(web._mensagem_sucesso({"id": 9}), "Operação concluída. ID: 9")
        self.assertEqual(web._mensagem_sucesso(None), "Operação concluída com sucesso.")


class TestExecucao(unittest.TestCase):
    def test_main_web_sobe_o_servidor_local(self):
        with patch.object(web, "criar_app") as criar, patch.dict("os.environ", {"PORT": "5055"}):
            web.main_web()

        criar.return_value.run.assert_called_once_with(host="127.0.0.1", port=5055)


if __name__ == "__main__":
    unittest.main()
