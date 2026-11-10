"""Testes do primeiro acesso e do login passando pelo menu (src/main.py).

Exercitam o caminho real do sistema: main -> funcionarios/autenticacao -> banco
oficial, com a digitação simulada. Usam um arquivo de banco temporário.
Rodar a partir da raiz do projeto:  python -m unittest tests.test_fluxo_login
"""

import contextlib
import io
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src import autenticacao, banco, funcionarios, main


class TestPrimeiroAcessoELogin(unittest.TestCase):
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

        self.conexao = banco.conectar()
        self.addCleanup(banco.fechar_conexao, self.conexao)
        banco.criar_tabelas(self.conexao)

    def _digitando(self, texto=(), senhas=()):
        """Simula o que a pessoa digita: `texto` em input() e `senhas` em getpass()."""
        pilha = contextlib.ExitStack()
        pilha.enter_context(patch("builtins.input", side_effect=list(texto)))
        pilha.enter_context(patch.object(main.getpass, "getpass", side_effect=list(senhas)))
        pilha.enter_context(contextlib.redirect_stdout(io.StringIO()))
        self.addCleanup(pilha.close)
        return pilha

    def _saida(self, funcao, *args):
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            resultado = funcao(*args)
        return resultado, buffer.getvalue()

    def _total_funcionarios(self):
        return self.conexao.execute("SELECT COUNT(*) FROM funcionarios").fetchone()[0]

    # ---------- primeiro acesso ----------

    def test_primeiro_acesso_cria_o_administrador_inicial(self):
        with patch("builtins.input", side_effect=["Ana Admin", "ana"]), \
                patch.object(main.getpass, "getpass", side_effect=["segredo1", "segredo1"]):
            ok, _ = self._saida(main._primeiro_acesso, self.conexao)

        self.assertTrue(ok)
        lista = funcionarios.listar_funcionarios(conexao=self.conexao)
        self.assertEqual(len(lista), 1)
        self.assertEqual((lista[0]["login"], lista[0]["perfil"]), ("ana", "ADMIN"))
        self.assertIsNotNone(autenticacao.login("ana", "segredo1"))

    def test_primeiro_acesso_registra_o_evento_na_auditoria(self):
        with patch("builtins.input", side_effect=["Ana Admin", "ana"]), \
                patch.object(main.getpass, "getpass", side_effect=["segredo1", "segredo1"]):
            self._saida(main._primeiro_acesso, self.conexao)

        eventos = main.auditoria.listar_eventos(conexao=self.conexao)

        self.assertEqual([e["acao"] for e in eventos], ["CADASTRO"])

    def test_primeiro_acesso_pede_de_novo_quando_as_senhas_nao_conferem(self):
        with patch("builtins.input", side_effect=["Ana Admin", "ana"]), \
                patch.object(
                    main.getpass, "getpass",
                    side_effect=["segredo1", "outra123", "segredo1", "segredo1"],
                ):
            ok, saida = self._saida(main._primeiro_acesso, self.conexao)

        self.assertTrue(ok)
        self.assertIn("As senhas não conferem.", saida)
        self.assertIsNotNone(autenticacao.login("ana", "segredo1"))

    def test_primeiro_acesso_com_senha_fraca_nao_cria_ninguem(self):
        with patch("builtins.input", side_effect=["Ana Admin", "ana"]), \
                patch.object(main.getpass, "getpass", side_effect=["123", "123"]):
            ok, saida = self._saida(main._primeiro_acesso, self.conexao)

        self.assertFalse(ok)
        self.assertIn("pelo menos", saida)
        self.assertEqual(self._total_funcionarios(), 0)

    def test_primeiro_acesso_cancelado_com_exclamacao(self):
        with patch("builtins.input", side_effect=["!"]):
            ok, _ = self._saida(main._primeiro_acesso, self.conexao)

        self.assertFalse(ok)
        self.assertEqual(self._total_funcionarios(), 0)

    def test_primeiro_acesso_nao_pergunta_nada_se_ja_existe_funcionario(self):
        funcionarios.cadastrar_funcionario("Ana", "ana", "segredo1", "ADMIN", conexao=self.conexao)

        with patch("builtins.input", side_effect=AssertionError("não deveria perguntar")):
            ok, _ = self._saida(main._primeiro_acesso, self.conexao)

        self.assertTrue(ok)
        self.assertEqual(self._total_funcionarios(), 1)

    # ---------- login ----------

    def test_login_pelo_menu_devolve_o_usuario_e_audita(self):
        ana = funcionarios.cadastrar_funcionario("Ana", "ana", "segredo1", "ADMIN", conexao=self.conexao)

        with patch("builtins.input", side_effect=["ana"]), \
                patch.object(main.getpass, "getpass", side_effect=["segredo1"]):
            usuario, _ = self._saida(main._fazer_login, self.conexao)

        self.assertEqual(usuario, {"id": ana, "nome": "Ana", "perfil": "ADMIN"})
        eventos = main.auditoria.listar_eventos(conexao=self.conexao)
        self.assertEqual([e["acao"] for e in eventos], ["LOGIN"])

    def test_login_pelo_menu_aceita_login_em_maiusculas(self):
        funcionarios.cadastrar_funcionario("Ana", "ana", "segredo1", "CONSULTA", conexao=self.conexao)

        with patch("builtins.input", side_effect=["ANA"]), \
                patch.object(main.getpass, "getpass", side_effect=["segredo1"]):
            usuario, _ = self._saida(main._fazer_login, self.conexao)

        self.assertEqual(usuario["perfil"], "CONSULTA")

    def test_login_com_senha_errada_tenta_de_novo_e_depois_entra(self):
        funcionarios.cadastrar_funcionario("Ana", "ana", "segredo1", "ADMIN", conexao=self.conexao)

        with patch("builtins.input", side_effect=["ana", "ana"]), \
                patch.object(main.getpass, "getpass", side_effect=["errada123", "segredo1"]):
            usuario, saida = self._saida(main._fazer_login, self.conexao)

        self.assertIsNotNone(usuario)
        self.assertIn("Login ou senha inválidos.", saida)
        eventos = main.auditoria.listar_eventos(conexao=self.conexao)
        self.assertCountEqual([e["acao"] for e in eventos], ["LOGIN_FALHA", "LOGIN"])

    def test_login_bloqueia_apos_o_maximo_de_tentativas(self):
        funcionarios.cadastrar_funcionario("Ana", "ana", "segredo1", "ADMIN", conexao=self.conexao)
        tentativas = main.MAX_TENTATIVAS_LOGIN

        with patch("builtins.input", side_effect=["ana"] * tentativas), \
                patch.object(main.getpass, "getpass", side_effect=["errada123"] * tentativas):
            usuario, saida = self._saida(main._fazer_login, self.conexao)

        self.assertIsNone(usuario)
        self.assertIn("Número máximo de tentativas", saida)
        eventos = main.auditoria.listar_eventos(conexao=self.conexao)
        self.assertEqual([e["acao"] for e in eventos], ["LOGIN_FALHA"] * tentativas)

    def test_funcionario_desativado_nao_consegue_entrar_pelo_menu(self):
        funcionarios.cadastrar_funcionario("Ana", "ana", "segredo1", "ADMIN", conexao=self.conexao)
        beto = funcionarios.cadastrar_funcionario(
            "Beto", "beto", "segredo1", "ESTOQUISTA", conexao=self.conexao
        )
        funcionarios.desativar_funcionario(beto, conexao=self.conexao)
        tentativas = main.MAX_TENTATIVAS_LOGIN

        with patch("builtins.input", side_effect=["beto"] * tentativas), \
                patch.object(main.getpass, "getpass", side_effect=["segredo1"] * tentativas):
            usuario, _ = self._saida(main._fazer_login, self.conexao)

        self.assertIsNone(usuario)


class TestMenuDeFuncionarios(unittest.TestCase):
    """As opções do menu de funcionários batem com as funções do módulo."""

    def test_cada_opcao_do_menu_aceita_os_argumentos_que_o_menu_envia(self):
        import inspect

        menu = dict(main.MENUS)["Funcionários"]

        for item in menu:
            with self.subTest(opcao=item.rotulo):
                funcao = getattr(funcionarios, item.funcao)
                inspect.signature(funcao).bind(*[object()] * len(item.campos))

    def test_listar_e_cadastrar_aceitam_a_conexao_do_menu(self):
        import inspect

        for nome in ("cadastrar_funcionario", "listar_funcionarios",
                     "editar_funcionario", "desativar_funcionario"):
            with self.subTest(funcao=nome):
                self.assertIn("conexao", inspect.signature(getattr(funcionarios, nome)).parameters)

    def test_apenas_admin_acessa_o_menu_de_funcionarios(self):
        for item in dict(main.MENUS)["Funcionários"]:
            with self.subTest(opcao=item.rotulo):
                self.assertEqual(tuple(item.perfis), (autenticacao.ADMIN,))


if __name__ == "__main__":
    unittest.main()
