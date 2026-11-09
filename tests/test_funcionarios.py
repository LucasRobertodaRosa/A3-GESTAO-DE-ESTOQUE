"""Testes de src/funcionarios.py.

Usam o schema OFICIAL (banco.criar_tabelas) em um arquivo temporário novo a cada
teste, sem tocar no estoque.db real.
Rodar a partir da raiz do projeto:  python -m unittest tests.test_funcionarios
"""

import shutil
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src import autenticacao, banco, funcionarios


class TestFuncionarios(unittest.TestCase):
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

    def _admin(self, **extra):
        dados = dict(nome="Ana Admin", login="ana", senha="segredo1", perfil="ADMIN")
        dados.update(extra)
        return funcionarios.cadastrar_funcionario(**dados)

    def _estoquista(self, **extra):
        dados = dict(nome="Beto Estoque", login="beto", senha="segredo1", perfil="ESTOQUISTA")
        dados.update(extra)
        return funcionarios.cadastrar_funcionario(**dados)

    def _linhas_no_banco(self):
        conexao = banco.conectar()
        try:
            return conexao.execute(
                "SELECT id, nome, login, senha_hash, perfil, ativo "
                "FROM funcionarios ORDER BY id"
            ).fetchall()
        finally:
            banco.fechar_conexao(conexao)

    # ---------- cadastro ----------

    def test_cadastrar_devolve_o_id_e_grava_na_tabela_oficial(self):
        novo_id = self._admin()

        linhas = self._linhas_no_banco()

        self.assertEqual(novo_id, 1)
        self.assertEqual(len(linhas), 1)
        self.assertEqual(
            (linhas[0]["nome"], linhas[0]["login"], linhas[0]["perfil"], linhas[0]["ativo"]),
            ("Ana Admin", "ana", "ADMIN", 1),
        )

    def test_senha_nunca_fica_em_texto_no_banco(self):
        self._admin(senha="segredo1")

        linha = self._linhas_no_banco()[0]

        self.assertNotIn("segredo1", [str(valor) for valor in tuple(linha)])
        self.assertTrue(linha["senha_hash"].startswith("$2"))
        self.assertTrue(autenticacao.verificar_senha("segredo1", linha["senha_hash"]))

    def test_cadastrar_normaliza_nome_login_e_perfil(self):
        self._admin(nome="  Ana Admin  ", login="  ANA.Souza ", perfil="admin")

        linha = self._linhas_no_banco()[0]

        self.assertEqual(
            (linha["nome"], linha["login"], linha["perfil"]),
            ("Ana Admin", "ana.souza", "ADMIN"),
        )

    def test_cadastrar_aceita_os_tres_perfis(self):
        for numero, perfil in enumerate(autenticacao.PERFIS):
            with self.subTest(perfil=perfil):
                novo_id = funcionarios.cadastrar_funcionario(
                    "Pessoa", f"pessoa{numero}", "segredo1", perfil
                )
                self.assertEqual(funcionarios.buscar_funcionario(novo_id)["perfil"], perfil)

    def test_cadastrar_exige_nome(self):
        for nome in ("", "   ", None):
            with self.subTest(nome=nome):
                with self.assertRaises(ValueError):
                    self._admin(nome=nome)

    def test_cadastrar_valida_o_login(self):
        for login in ("", "   ", None, "ab", "a" * 31, "com espaco", "acentuação", "a@b"):
            with self.subTest(login=login):
                with self.assertRaises(ValueError):
                    self._admin(login=login)

    def test_cadastrar_aceita_login_nos_limites(self):
        funcionarios.cadastrar_funcionario("Tres", "abc", "segredo1", "CONSULTA")
        funcionarios.cadastrar_funcionario("Trinta", "a" * 30, "segredo1", "CONSULTA")

    def test_cadastrar_recusa_perfil_invalido(self):
        for perfil in ("GERENTE", "", None, "admins"):
            with self.subTest(perfil=perfil):
                with self.assertRaises(ValueError):
                    self._admin(perfil=perfil)

    def test_cadastrar_recusa_senha_invalida(self):
        for senha in ("", "12345", None, "a" * 73):
            with self.subTest(senha=senha):
                with self.assertRaises(ValueError):
                    self._admin(senha=senha)

    def test_cadastrar_nao_aceita_login_repetido_ignorando_caixa(self):
        self._admin(login="ana")

        for repetido in ("ana", "ANA", " Ana "):
            with self.subTest(login=repetido):
                with self.assertRaises(ValueError) as erro:
                    self._estoquista(login=repetido)
                self.assertIn("login", str(erro.exception))

    def test_cadastro_recusado_nao_grava_nada(self):
        self._admin()

        for chamada in (
            lambda: self._estoquista(login="ana"),
            lambda: self._estoquista(senha="123"),
            lambda: self._estoquista(perfil="GERENTE"),
        ):
            with self.assertRaises(ValueError):
                chamada()

        self.assertEqual(len(self._linhas_no_banco()), 1)

    # ---------- consulta ----------

    def test_listar_ordena_por_nome_e_nunca_expoe_a_senha(self):
        self._estoquista(nome="Zeca", login="zeca")
        self._admin(nome="Ana Admin")

        lista = funcionarios.listar_funcionarios()

        self.assertEqual([f["nome"] for f in lista], ["Ana Admin", "Zeca"])
        for funcionario in lista:
            self.assertEqual(
                set(funcionario), {"id", "nome", "login", "perfil", "ativo"}
            )

    def test_listar_vazio(self):
        self.assertEqual(funcionarios.listar_funcionarios(), [])

    def test_listar_apenas_ativos(self):
        self._admin()
        beto = self._estoquista()
        funcionarios.desativar_funcionario(beto)

        self.assertEqual(len(funcionarios.listar_funcionarios()), 2)
        ativos = funcionarios.listar_funcionarios(apenas_ativos=True)
        self.assertEqual([f["login"] for f in ativos], ["ana"])

    def test_buscar_existente_e_inexistente(self):
        ana = self._admin()

        encontrado = funcionarios.buscar_funcionario(ana)

        self.assertEqual(encontrado["login"], "ana")
        self.assertTrue(encontrado["ativo"])
        self.assertNotIn("senha_hash", encontrado)
        self.assertIsNone(funcionarios.buscar_funcionario(99))

    # ---------- edição ----------

    def test_editar_altera_nome_e_perfil(self):
        self._admin()
        beto = self._estoquista()

        editado = funcionarios.editar_funcionario(beto, "Beto Silva", "consulta")

        self.assertEqual(editado["nome"], "Beto Silva")
        self.assertEqual(editado["perfil"], "CONSULTA")
        self.assertEqual(editado["login"], "beto")
        self.assertEqual(funcionarios.buscar_funcionario(beto), editado)

    def test_editar_so_o_que_foi_informado(self):
        self._admin()
        beto = self._estoquista()

        self.assertEqual(
            funcionarios.editar_funcionario(beto, nome="Novo Nome")["perfil"], "ESTOQUISTA"
        )
        self.assertEqual(
            funcionarios.editar_funcionario(beto, perfil="CONSULTA")["nome"], "Novo Nome"
        )

    def test_editar_nao_altera_a_senha(self):
        self._admin()
        beto = self._estoquista(senha="segredo1")
        hash_antes = self._linhas_no_banco()[1]["senha_hash"]

        funcionarios.editar_funcionario(beto, "Beto Silva", "CONSULTA")

        self.assertEqual(self._linhas_no_banco()[1]["senha_hash"], hash_antes)
        self.assertIsNotNone(autenticacao.login("beto", "segredo1"))

    def test_editar_valida_os_campos(self):
        self._admin()
        beto = self._estoquista()

        for kwargs in ({"nome": "   "}, {"perfil": "GERENTE"}):
            with self.subTest(**kwargs):
                with self.assertRaises(ValueError):
                    funcionarios.editar_funcionario(beto, **kwargs)

        self.assertEqual(funcionarios.buscar_funcionario(beto)["nome"], "Beto Estoque")

    def test_editar_inexistente(self):
        with self.assertRaises(ValueError):
            funcionarios.editar_funcionario(99, nome="X")

    def test_ultimo_admin_nao_pode_ser_rebaixado(self):
        ana = self._admin()

        with self.assertRaises(ValueError):
            funcionarios.editar_funcionario(ana, perfil="CONSULTA")

        self.assertEqual(funcionarios.buscar_funcionario(ana)["perfil"], "ADMIN")

    def test_admin_pode_ser_rebaixado_havendo_outro_admin_ativo(self):
        ana = self._admin()
        self._admin(nome="Caio Admin", login="caio")

        editado = funcionarios.editar_funcionario(ana, perfil="CONSULTA")

        self.assertEqual(editado["perfil"], "CONSULTA")

    def test_admin_pode_mudar_de_nome_mantendo_o_perfil(self):
        ana = self._admin()

        editado = funcionarios.editar_funcionario(ana, nome="Ana Maria", perfil="ADMIN")

        self.assertEqual(editado["nome"], "Ana Maria")

    def test_outro_admin_inativo_nao_conta_como_admin_ativo(self):
        ana = self._admin()
        caio = self._admin(nome="Caio", login="caio")
        funcionarios.desativar_funcionario(caio)

        with self.assertRaises(ValueError):
            funcionarios.editar_funcionario(ana, perfil="CONSULTA")

    # ---------- desativação ----------

    def test_desativar_marca_inativo_e_impede_o_login(self):
        self._admin()
        beto = self._estoquista()
        self.assertIsNotNone(autenticacao.login("beto", "segredo1"))

        desativado = funcionarios.desativar_funcionario(beto)

        self.assertFalse(desativado["ativo"])
        self.assertEqual(self._linhas_no_banco()[1]["ativo"], 0)
        self.assertIsNone(autenticacao.login("beto", "segredo1"))

    def test_desativar_nao_apaga_o_registro(self):
        self._admin()
        beto = self._estoquista()

        funcionarios.desativar_funcionario(beto)

        self.assertEqual(len(self._linhas_no_banco()), 2)
        self.assertIsNotNone(funcionarios.buscar_funcionario(beto))

    def test_desativar_inexistente(self):
        with self.assertRaises(ValueError):
            funcionarios.desativar_funcionario(99)

    def test_desativar_duas_vezes_e_recusado(self):
        self._admin()
        beto = self._estoquista()
        funcionarios.desativar_funcionario(beto)

        with self.assertRaises(ValueError):
            funcionarios.desativar_funcionario(beto)

    def test_ultimo_admin_nao_pode_ser_desativado(self):
        ana = self._admin()

        with self.assertRaises(ValueError):
            funcionarios.desativar_funcionario(ana)

        self.assertTrue(funcionarios.buscar_funcionario(ana)["ativo"])
        self.assertIsNotNone(autenticacao.login("ana", "segredo1"))

    def test_admin_pode_ser_desativado_havendo_outro_admin_ativo(self):
        ana = self._admin()
        self._admin(nome="Caio Admin", login="caio")

        self.assertFalse(funcionarios.desativar_funcionario(ana)["ativo"])

    def test_login_de_funcionario_desativado_nao_pode_ser_reutilizado(self):
        self._admin()
        beto = self._estoquista()
        funcionarios.desativar_funcionario(beto)

        with self.assertRaises(ValueError):
            self._estoquista(nome="Outro Beto")  # mesmo login 'beto'

    # ---------- conexões ----------

    def test_usa_a_conexao_recebida_sem_fecha_la_e_com_commit(self):
        conexao = banco.conectar()
        self.addCleanup(banco.fechar_conexao, conexao)

        novo_id = funcionarios.cadastrar_funcionario(
            "Ana", "ana", "segredo1", "ADMIN", conexao=conexao
        )

        conexao.execute("SELECT 1")  # continua aberta
        self.assertEqual(novo_id, 1)
        self.assertEqual(len(self._linhas_no_banco()), 1)  # outra conexão já enxerga: houve commit

    def test_erro_com_conexao_recebida_desfaz_e_mantem_a_conexao_utilizavel(self):
        conexao = banco.conectar()
        self.addCleanup(banco.fechar_conexao, conexao)
        funcionarios.cadastrar_funcionario("Ana", "ana", "segredo1", "ADMIN", conexao=conexao)

        with self.assertRaises(ValueError):
            funcionarios.cadastrar_funcionario("Outra", "ana", "segredo1", "ADMIN", conexao=conexao)

        funcionarios.cadastrar_funcionario("Beto", "beto", "segredo1", "CONSULTA", conexao=conexao)
        self.assertEqual(len(self._linhas_no_banco()), 2)

    def test_toda_operacao_fecha_a_conexao_que_abriu(self):
        abertas = []
        original = banco.conectar

        def rastreada(*args, **kwargs):
            conexao = original(*args, **kwargs)
            abertas.append(conexao)
            return conexao

        with patch.object(funcionarios, "conectar", rastreada):
            ana = self._admin()
            beto = self._estoquista()
            funcionarios.listar_funcionarios()
            funcionarios.buscar_funcionario(ana)
            funcionarios.editar_funcionario(beto, nome="Beto S")
            funcionarios.desativar_funcionario(beto)
            with self.assertRaises(ValueError):
                funcionarios.desativar_funcionario(ana)  # falha dentro da operação

        self.assertGreaterEqual(len(abertas), 7)
        for conexao in abertas:
            with self.assertRaises(sqlite3.ProgrammingError):
                conexao.execute("SELECT 1")


if __name__ == "__main__":
    unittest.main()
