"""Testes web das funções essenciais (reativação, senha, ajuste, listas de escolha, nome da categoria e CSV)."""

import unittest

from src import categorias, fornecedores, movimentacoes, produtos, web
from tests.test_web import BaseWeb, SENHA, _url_da_opcao


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

    # ---------- senha ----------

    def test_trocar_minha_senha(self):
        resposta = self._post(_url_da_opcao("Trocar minha senha"),
                              senha_atual=SENHA, nova_senha="novasenha",
                              confirmacao="novasenha")
        self.assertEqual(resposta.status_code, 302)
        self.assertIn("SENHA", self._acoes_de_auditoria())
        self.cliente.post("/sair", data={"csrf_token": "x"})
        outro = self.app.test_client()
        self.assertEqual(self._post("/entrar", cliente=outro, login="ana",
                                    senha=SENHA).status_code, 401)   # senha antiga recusada
        self.assertEqual(self._post("/entrar", cliente=outro, login="ana",
                                    senha="novasenha").status_code, 302)

    def test_trocar_senha_com_senha_atual_errada(self):
        resposta = self._post(_url_da_opcao("Trocar minha senha"),
                              senha_atual="errada1", nova_senha="novasenha",
                              confirmacao="novasenha")
        self.assertEqual(resposta.status_code, 400)
        self.assertIn("senha atual está incorreta", self._html(resposta))

    def test_trocar_senha_com_confirmacao_diferente(self):
        resposta = self._post(_url_da_opcao("Trocar minha senha"),
                              senha_atual=SENHA, nova_senha="novasenha",
                              confirmacao="diferente")
        self.assertEqual(resposta.status_code, 400)

    def test_consulta_nao_pode_redefinir_senha_de_outro(self):
        self._criar_funcionario("cris", "CONSULTA")
        outro = self.app.test_client()
        self._post("/entrar", cliente=outro, login="cris", senha=SENHA)
        resposta = self._post(_url_da_opcao("Redefinir senha de um funcionário"),
                              cliente=outro, id="1", nova_senha="hackeada1",
                              confirmacao="hackeada1")
        self.assertEqual(resposta.status_code, 403)

    # ---------- ajuste ----------

    def test_ajuste_de_inventario_pelo_site(self):
        resposta = self._post(_url_da_opcao("Ajustar estoque (contagem física)"),
                              produto_id=str(self.pid), quantidade_contada="8",
                              motivo="contagem anual")
        self.assertEqual(resposta.status_code, 302)
        self.assertEqual(produtos.buscar_produto(self.pid)["estoque_atual"], 8)
        self.assertIn("AJUSTE", self._acoes_de_auditoria())
        pagina = self._html(self.cliente.get(resposta.headers["Location"]))
        self.assertIn("Estoque ajustado de 10 para 8", pagina)

    # ---------- listas de escolha ----------

    def test_campo_de_produto_vira_lista(self):
        html = self._html(self.cliente.get(_url_da_opcao("Registrar saída")))
        self.assertIn('<select name="produto_id"', html)
        self.assertIn("CAN-1 — Caneta azul (estoque 10)", html)

    def test_desativar_lista_so_ativos_e_reativar_so_inativos(self):
        desativar = self._html(self.cliente.get(_url_da_opcao("Desativar produto")))
        reativar = self._html(self.cliente.get(_url_da_opcao("Reativar produto")))
        self.assertIn("Caneta azul", desativar)
        self.assertNotIn("Caneta azul", reativar)
        produtos.desativar_produto(self.pid)
        desativar = self._html(self.cliente.get(_url_da_opcao("Desativar produto")))
        reativar = self._html(self.cliente.get(_url_da_opcao("Reativar produto")))
        self.assertNotIn("Caneta azul", desativar)
        self.assertIn("Caneta azul", reativar)

    def test_lista_de_categoria_e_fornecedor(self):
        fornecedores.cadastrar_fornecedor("Alfa Ltda", None, None, None)
        html = self._html(self.cliente.get(_url_da_opcao("Registrar entrada")))
        self.assertIn("Alfa Ltda", html)
        html = self._html(self.cliente.get(_url_da_opcao("Cadastrar produto")))
        self.assertIn("Papelaria", html)

    def test_escolher_na_lista_funciona_de_ponta_a_ponta(self):
        resposta = self._post(_url_da_opcao("Registrar saída"),
                              produto_id=str(self.pid), quantidade="4")
        self.assertEqual(resposta.status_code, 302)
        self.assertEqual(produtos.buscar_produto(self.pid)["estoque_atual"], 6)

    # ---------- nome da categoria ----------

    def test_listagem_de_produtos_mostra_nome_da_categoria(self):
        html = self._html(self.cliente.get(_url_da_opcao("Listar produtos")))
        self.assertIn("Papelaria", html)
        self.assertNotIn("ID categoria", html)
        html = self._html(self._post(_url_da_opcao("Buscar produto (nome, código ou categoria)"),
                                     termo="caneta"))
        self.assertIn("Papelaria", html)

    def test_com_nome_da_categoria_mantem_outros_resultados(self):
        con = web.banco.conectar()
        self.addCleanup(web.banco.fechar_conexao, con)
        sem = [{"id": 1, "nome": "x"}]
        self.assertIs(web._com_nome_da_categoria(sem, con), sem)
        self.assertEqual(web._com_nome_da_categoria([], con), [])
        orfao = web._com_nome_da_categoria([{"id": 1, "categoria_id": 99}], con)
        self.assertEqual(orfao, [{"id": 1, "categoria": "ID 99"}])
        self.assertEqual(web._com_nome_da_categoria({"categoria_id": None}, con),
                         {"categoria": "-"})

    # ---------- CSV ----------

    def test_csv_de_produtos_tem_nome_da_categoria(self):
        texto = self.cliente.get(_url_da_opcao("Listar produtos") + "/csv").get_data(as_text=True)
        self.assertIn("Papelaria", texto)
        self.assertNotIn("ID categoria", texto)

    def test_csv_do_estoque_atual(self):
        resposta = self.cliente.get(_url_da_opcao("Estoque atual") + "/csv")
        self.assertEqual(resposta.status_code, 200)
        self.assertTrue(resposta.mimetype.startswith("text/csv"))
        self.assertIn("attachment", resposta.headers["Content-Disposition"])
        self.assertIn("estoque-atual-", resposta.headers["Content-Disposition"])
        texto = resposta.get_data(as_text=True)
        self.assertTrue(texto.startswith("﻿"))
        linhas = texto.lstrip("﻿").splitlines()
        self.assertIn(";", linhas[0])
        self.assertTrue(any("Caneta azul" in linha and "2,50" in linha for linha in linhas))

    def test_csv_com_filtros_e_erros(self):
        url = _url_da_opcao("Movimentações por produto") + "/csv"
        self.assertEqual(self.cliente.get(url, query_string={"produto_id": self.pid}).status_code, 200)
        self.assertEqual(self.cliente.get(url).status_code, 400)        # filtro obrigatório
        self.assertEqual(self.cliente.get(url, query_string={"produto_id": "x"}).status_code, 400)

    def test_csv_so_para_consultas_e_com_permissao(self):
        self.assertEqual(self.cliente.get(_url_da_opcao("Cadastrar produto") + "/csv").status_code, 403)
        self.assertEqual(self.cliente.get(_url_da_opcao("Consultar eventos (Enter ignora o filtro)") + "/csv").status_code, 200)
        self._criar_funcionario("cris", "CONSULTA")
        outro = self.app.test_client()
        self._post("/entrar", cliente=outro, login="cris", senha=SENHA)
        self.assertEqual(outro.get(_url_da_opcao("Consultar eventos (Enter ignora o filtro)") + "/csv").status_code, 403)
        self.assertEqual(self.app.test_client().get("/m/4/0/csv").status_code, 302)  # sem login

    def test_csv_de_indicadores_que_nao_e_lista(self):
        self.assertEqual(self.cliente.get(_url_da_opcao("Indicadores gerais") + "/csv").status_code, 404)

    def test_botao_baixar_csv_aparece_na_tabela(self):
        html = self._html(self.cliente.get(_url_da_opcao("Estoque atual")))
        self.assertIn("Baixar CSV", html)

    def test_celula_csv_protege_contra_formulas(self):
        self.assertEqual(web._celula_csv("=1+1"), "'=1+1")
        self.assertEqual(web._celula_csv("@soma"), "'@soma")
        self.assertEqual(web._celula_csv(3.5), "3,50")
        self.assertEqual(web._celula_csv(-3), "-3")
        self.assertEqual(web._celula_csv(None), "")
        self.assertEqual(web._celula_csv(True), "Sim")


if __name__ == "__main__":
    unittest.main()
