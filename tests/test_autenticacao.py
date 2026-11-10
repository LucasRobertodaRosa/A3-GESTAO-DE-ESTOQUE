"""Testes de src/autenticacao.py (hash bcrypt, login e permissões).

Usam o schema OFICIAL (banco.criar_tabelas) em um arquivo temporário novo a cada
teste, sem tocar no estoque.db real. Os funcionários de teste são inseridos
direto no banco, para estes testes não dependerem de funcionarios.py.
Rodar a partir da raiz do projeto:  python -m unittest tests.test_autenticacao
"""

import shutil
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src import autenticacao, banco


class BaseComBanco(unittest.TestCase):
    def setUp(self):
        pasta = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, pasta, ignore_errors=True)
        for alvo, atributo, valor in (
            (banco, "CAMINHO_PADRAO", Path(pasta) / "teste.db"),
            (autenticacao, "CUSTO_BCRYPT", 4),  # mínimo do bcrypt: testes rápidos
        ):
            patcher = patch.object(alvo, atributo, valor)
            patcher.start()
            self.addCleanup(patcher.stop)

        conexao = banco.conectar()
        banco.criar_tabelas(conexao)
        banco.fechar_conexao(conexao)

    def _inserir(self, nome, login, senha, perfil="ESTOQUISTA", ativo=1):
        conexao = banco.conectar()
        try:
            with conexao:
                cursor = conexao.execute(
                    "INSERT INTO funcionarios (nome, login, senha_hash, perfil, ativo) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (nome, login, autenticacao.gerar_hash(senha), perfil, ativo),
                )
                return cursor.lastrowid
        finally:
            banco.fechar_conexao(conexao)


class TestSenhas(BaseComBanco):
    def test_gerar_hash_nao_guarda_a_senha_em_texto(self):
        senha_hash = autenticacao.gerar_hash("segredo1")

        self.assertNotIn("segredo1", senha_hash)
        self.assertTrue(senha_hash.startswith("$2"))  # formato do bcrypt

    def test_mesma_senha_gera_hashes_diferentes(self):
        self.assertNotEqual(
            autenticacao.gerar_hash("segredo1"), autenticacao.gerar_hash("segredo1")
        )

    def test_verificar_senha_certa_e_errada(self):
        senha_hash = autenticacao.gerar_hash("segredo1")

        self.assertTrue(autenticacao.verificar_senha("segredo1", senha_hash))
        self.assertFalse(autenticacao.verificar_senha("segredo2", senha_hash))
        self.assertFalse(autenticacao.verificar_senha("SEGREDO1", senha_hash))

    def test_verificar_senha_nao_estoura_com_dados_invalidos(self):
        senha_hash = autenticacao.gerar_hash("segredo1")

        self.assertFalse(autenticacao.verificar_senha("segredo1", "isso-nao-e-hash"))
        self.assertFalse(autenticacao.verificar_senha("segredo1", ""))
        self.assertFalse(autenticacao.verificar_senha("segredo1", None))
        self.assertFalse(autenticacao.verificar_senha(None, senha_hash))

    def test_senha_aceita_acentos(self):
        senha_hash = autenticacao.gerar_hash("açaí-123")

        self.assertTrue(autenticacao.verificar_senha("açaí-123", senha_hash))

    def test_senha_invalida_e_recusada(self):
        for senha in (None, "", "12345", 123456, "a" * 73):
            with self.subTest(senha=senha):
                with self.assertRaises(ValueError):
                    autenticacao.gerar_hash(senha)

    def test_limites_da_senha_sao_aceitos(self):
        autenticacao.gerar_hash("123456")        # mínimo: 6 caracteres
        autenticacao.gerar_hash("a" * 72)        # máximo: 72 bytes

    def test_limite_de_bytes_vale_para_caracteres_acentuados(self):
        # 40 letras "é" têm 40 caracteres mas 80 bytes
        with self.assertRaises(ValueError):
            autenticacao.gerar_hash("é" * 40)


class TestLogin(BaseComBanco):
    def test_login_certo_devolve_os_dados_sem_senha(self):
        ana = self._inserir("Ana Souza", "ana", "segredo1", "ADMIN")

        usuario = autenticacao.login("ana", "segredo1")

        self.assertEqual(
            usuario,
            {"id": ana, "nome": "Ana Souza", "login": "ana", "perfil": "ADMIN"},
        )
        self.assertNotIn("senha_hash", usuario)

    def test_login_ignora_maiusculas_e_espacos_no_login(self):
        self._inserir("Ana", "ana", "segredo1")

        self.assertIsNotNone(autenticacao.login("  ANA ", "segredo1"))

    def test_login_diferencia_maiusculas_na_senha(self):
        self._inserir("Ana", "ana", "Segredo1")

        self.assertIsNone(autenticacao.login("ana", "segredo1"))

    def test_senha_errada_devolve_none(self):
        self._inserir("Ana", "ana", "segredo1")

        self.assertIsNone(autenticacao.login("ana", "errada123"))

    def test_login_inexistente_devolve_none(self):
        self.assertIsNone(autenticacao.login("ninguem", "segredo1"))

    def test_funcionario_inativo_nao_entra(self):
        self._inserir("Beto", "beto", "segredo1", ativo=0)

        self.assertIsNone(autenticacao.login("beto", "segredo1"))

    def test_credenciais_vazias_ou_invalidas_devolvem_none(self):
        self._inserir("Ana", "ana", "segredo1")

        for login, senha in (("", ""), ("ana", ""), ("", "segredo1"),
                             (None, None), ("ana", None), (None, "segredo1")):
            with self.subTest(login=login, senha=senha):
                self.assertIsNone(autenticacao.login(login, senha))

    def test_validar_usuario_devolve_os_dados_quando_certo(self):
        self._inserir("Ana", "ana", "segredo1", "CONSULTA")

        self.assertEqual(autenticacao.validar_usuario("ana", "segredo1")["perfil"], "CONSULTA")

    def test_validar_usuario_usa_a_mesma_mensagem_para_qualquer_falha(self):
        self._inserir("Ana", "ana", "segredo1")
        self._inserir("Beto", "beto", "segredo1", ativo=0)
        mensagens = set()

        for login, senha in (("ana", "errada123"), ("ninguem", "segredo1"),
                             ("beto", "segredo1"), ("", "")):
            with self.assertRaises(ValueError) as erro:
                autenticacao.validar_usuario(login, senha)
            mensagens.add(str(erro.exception))

        self.assertEqual(mensagens, {autenticacao.MENSAGEM_LOGIN_INVALIDO})

    def test_login_usa_a_conexao_recebida_sem_fecha_la(self):
        self._inserir("Ana", "ana", "segredo1")
        conexao = banco.conectar()
        self.addCleanup(banco.fechar_conexao, conexao)

        usuario = autenticacao.login("ana", "segredo1", conexao=conexao)

        self.assertIsNotNone(usuario)
        conexao.execute("SELECT 1")  # se estivesse fechada, levantaria ProgrammingError

    def test_login_fecha_a_conexao_que_abriu(self):
        self._inserir("Ana", "ana", "segredo1")
        abertas = []
        original = banco.conectar

        def rastreada(*args, **kwargs):
            conexao = original(*args, **kwargs)
            abertas.append(conexao)
            return conexao

        with patch.object(autenticacao, "conectar", rastreada):
            autenticacao.login("ana", "segredo1")
            autenticacao.login("ana", "errada123")

        self.assertEqual(len(abertas), 2)
        for conexao in abertas:
            with self.assertRaises(sqlite3.ProgrammingError):
                conexao.execute("SELECT 1")


class TestPermissoes(unittest.TestCase):
    def test_tem_permissao_para_o_perfil_do_usuario(self):
        admin = {"id": 1, "perfil": "ADMIN"}

        self.assertTrue(autenticacao.tem_permissao(admin, autenticacao.ADMIN))
        self.assertTrue(
            autenticacao.tem_permissao(admin, autenticacao.ADMIN, autenticacao.ESTOQUISTA)
        )

    def test_nao_tem_permissao_para_outro_perfil(self):
        consulta = {"id": 2, "perfil": "CONSULTA"}

        self.assertFalse(autenticacao.tem_permissao(consulta, autenticacao.ADMIN))
        self.assertFalse(
            autenticacao.tem_permissao(consulta, autenticacao.ADMIN, autenticacao.ESTOQUISTA)
        )

    def test_sem_usuario_ou_sem_perfil_nao_tem_permissao(self):
        for usuario in (None, {}, {"id": 1}, {"perfil": None}):
            with self.subTest(usuario=usuario):
                self.assertFalse(autenticacao.tem_permissao(usuario, autenticacao.CONSULTA))

    def test_perfil_do_usuario_nao_diferencia_caixa(self):
        self.assertTrue(autenticacao.tem_permissao({"perfil": "admin"}, autenticacao.ADMIN))

    def test_exigir_permissao_deixa_passar_quem_pode(self):
        autenticacao.exigir_permissao({"perfil": "ADMIN"}, autenticacao.ADMIN)

    def test_exigir_permissao_barra_quem_nao_pode(self):
        with self.assertRaises(PermissionError) as erro:
            autenticacao.exigir_permissao({"perfil": "CONSULTA"}, autenticacao.ADMIN)

        self.assertIn("ADMIN", str(erro.exception))

    def test_perfis_do_sistema(self):
        self.assertEqual(autenticacao.PERFIS, ("ADMIN", "ESTOQUISTA", "CONSULTA"))


if __name__ == "__main__":
    unittest.main()
