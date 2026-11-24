"""Testes das funções essenciais: reativação, troca de senha e ajuste de inventário."""

import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src import (
    auditoria, autenticacao, banco, categorias, fornecedores, funcionarios, movimentacoes, produtos,
)


class BaseComBanco(unittest.TestCase):
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
        conexao = banco.conectar()
        banco.criar_tabelas(conexao)
        banco.fechar_conexao(conexao)

    def _produto(self, codigo="P1"):
        categoria = categorias.cadastrar_categoria("Geral", None)
        categoria_id = categoria["id"] if isinstance(categoria, dict) else categoria
        criado = produtos.cadastrar_produto(codigo, "Caneta", 2.5, 5, categoria_id)
        return criado["id"] if isinstance(criado, dict) else criado


class TestReativacao(BaseComBanco):
    def test_reativar_produto(self):
        pid = self._produto()
        produtos.desativar_produto(pid)
        self.assertTrue(produtos.reativar_produto(pid)["ativo"])
        self.assertEqual(len(produtos.listar_produtos()), 1)

    def test_reativar_produto_ja_ativo_ou_inexistente(self):
        pid = self._produto()
        with self.assertRaises(ValueError):
            produtos.reativar_produto(pid)
        with self.assertRaises(ValueError):
            produtos.reativar_produto(999)

    def test_reativar_fornecedor(self):
        fid = fornecedores.cadastrar_fornecedor("Alfa", None, None, None)
        fid = fid["id"] if isinstance(fid, dict) else fid
        fornecedores.desativar_fornecedor(fid)
        self.assertTrue(fornecedores.reativar_fornecedor(fid))
        self.assertTrue(fornecedores.buscar_fornecedor(fid)["ativo"])
        with self.assertRaises(ValueError):
            fornecedores.reativar_fornecedor(fid)
        with self.assertRaises(ValueError):
            fornecedores.reativar_fornecedor(999)

    def test_reativar_funcionario(self):
        funcionarios.cadastrar_funcionario("Ana", "ana", "segredo1", "ADMIN")
        beto = funcionarios.cadastrar_funcionario("Beto", "beto", "segredo1", "CONSULTA")
        funcionarios.desativar_funcionario(beto)
        self.assertIsNone(autenticacao.login("beto", "segredo1"))
        self.assertTrue(funcionarios.reativar_funcionario(beto)["ativo"])
        self.assertIsNotNone(autenticacao.login("beto", "segredo1"))
        with self.assertRaises(ValueError):
            funcionarios.reativar_funcionario(beto)
        with self.assertRaises(ValueError):
            funcionarios.reativar_funcionario(999)


class TestSenhas(BaseComBanco):
    def setUp(self):
        super().setUp()
        self.ana = funcionarios.cadastrar_funcionario("Ana", "ana", "segredo1", "ADMIN")

    def test_alterar_senha(self):
        self.assertTrue(funcionarios.alterar_senha(self.ana, "segredo1", "novasenha", "novasenha"))
        self.assertIsNone(autenticacao.login("ana", "segredo1"))
        self.assertIsNotNone(autenticacao.login("ana", "novasenha"))

    def test_alterar_senha_exige_senha_atual_correta(self):
        with self.assertRaises(ValueError):
            funcionarios.alterar_senha(self.ana, "errada", "novasenha")
        self.assertIsNotNone(autenticacao.login("ana", "segredo1"))

    def test_alterar_senha_regras(self):
        with self.assertRaises(ValueError):       # confirmação diferente
            funcionarios.alterar_senha(self.ana, "segredo1", "novasenha", "outra")
        with self.assertRaises(ValueError):       # igual à atual
            funcionarios.alterar_senha(self.ana, "segredo1", "segredo1")
        with self.assertRaises(ValueError):       # curta demais
            funcionarios.alterar_senha(self.ana, "segredo1", "123")
        with self.assertRaises(ValueError):       # funcionário inexistente
            funcionarios.alterar_senha(999, "segredo1", "novasenha")

    def test_redefinir_senha(self):
        beto = funcionarios.cadastrar_funcionario("Beto", "beto", "segredo1", "CONSULTA")
        self.assertTrue(funcionarios.redefinir_senha(beto, "outrasenha", "outrasenha"))
        self.assertIsNone(autenticacao.login("beto", "segredo1"))
        self.assertIsNotNone(autenticacao.login("beto", "outrasenha"))

    def test_redefinir_senha_erros(self):
        with self.assertRaises(ValueError):
            funcionarios.redefinir_senha(self.ana, "novasenha", "diferente")
        with self.assertRaises(ValueError):
            funcionarios.redefinir_senha(self.ana, "123")
        with self.assertRaises(ValueError):
            funcionarios.redefinir_senha(999, "novasenha")


class TestAjusteDeInventario(BaseComBanco):
    def setUp(self):
        super().setUp()
        self.pid = self._produto()
        movimentacoes.registrar_entrada(self.pid, 10)

    def _saldo(self):
        return produtos.buscar_produto(self.pid)["estoque_atual"]

    def test_falta_vira_saida(self):
        r = movimentacoes.registrar_ajuste(self.pid, 7, "quebra")
        self.assertEqual((r["saldo_anterior"], r["saldo_novo"], r["diferenca"]), (10, 7, -3))
        self.assertEqual(self._saldo(), 7)
        ultima = movimentacoes.listar_movimentacoes(self.pid)[0]
        self.assertEqual((ultima["tipo"], ultima["quantidade"]), ("SAIDA", 3))
        self.assertTrue(ultima["observacao"].startswith("Ajuste de inventário"))
        self.assertIn("quebra", ultima["observacao"])

    def test_sobra_vira_entrada(self):
        r = movimentacoes.registrar_ajuste(self.pid, 15)
        self.assertEqual(r["diferenca"], 5)
        self.assertEqual(self._saldo(), 15)
        self.assertEqual(movimentacoes.listar_movimentacoes(self.pid)[0]["tipo"], "ENTRADA")

    def test_sem_diferenca_nao_registra(self):
        r = movimentacoes.registrar_ajuste(self.pid, 10)
        self.assertIsNone(r["movimentacao_id"])
        self.assertEqual(len(movimentacoes.listar_movimentacoes(self.pid)), 1)

    def test_contagem_zero_e_validacoes(self):
        movimentacoes.registrar_ajuste(self.pid, 0)
        self.assertEqual(self._saldo(), 0)
        for invalido in (-1, "5", 2.5, None):
            with self.assertRaises(ValueError):
                movimentacoes.registrar_ajuste(self.pid, invalido)
        with self.assertRaises(ValueError):
            movimentacoes.registrar_ajuste(999, 1)
        produtos.desativar_produto(self.pid)
        with self.assertRaises(ValueError):
            movimentacoes.registrar_ajuste(self.pid, 1)

    def test_auditoria_aceita_as_novas_acoes(self):
        func = funcionarios.cadastrar_funcionario("Ana", "ana", "segredo1", "ADMIN")
        for acao in (auditoria.REATIVACAO, auditoria.SENHA, auditoria.AJUSTE):
            auditoria.registrar_evento(func, acao, "teste", 1)
        acoes = {e["acao"] for e in auditoria.listar_eventos()}
        self.assertTrue({"REATIVACAO", "SENHA", "AJUSTE"} <= acoes)


if __name__ == "__main__":
    unittest.main()
