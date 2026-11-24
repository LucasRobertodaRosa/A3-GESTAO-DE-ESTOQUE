"""Testes web das funções essenciais (reativação, senha, ajuste)."""

import unittest

from src import categorias, movimentacoes, produtos
from tests.test_web import BaseWeb, _url_da_opcao


class TestFuncoesWeb(BaseWeb):
    def setUp(self):
        super().setUp()
        self._entrar()
        categoria = categorias.cadastrar_categoria("Papelaria", None)
        cid = categoria["id"] if isinstance(categoria, dict) else categoria
        criado = produtos.cadastrar_produto("CAN-1", "Caneta azul", 2.5, 5, cid)
        self.pid = criado["id"] if isinstance(criado, dict) else criado
        movimentacoes.registrar_entrada(self.pid, 10)

    def _html(self, resposta):
        return resposta.get_data(as_text=True)

    # ---------- reativar ----------

    def test_reativar_produto_pelo_site(self):
        produtos.desativar_produto(self.pid)
        resposta = self._post(_url_da_opcao("Reativar produto"), id=str(self.pid))
        self.assertEqual(resposta.status_code, 302)
        self.assertTrue(produtos.buscar_produto(self.pid)["ativo"])
        self.assertIn("REATIVACAO", self._acoes_de_auditoria())


if __name__ == "__main__":
    unittest.main()
