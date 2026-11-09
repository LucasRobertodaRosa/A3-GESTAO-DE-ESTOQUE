"""Testes de src/produtos.py.

Usam o schema OFICIAL (banco.criar_tabelas) em um arquivo temporário novo a cada
teste, sem tocar no estoque.db real.
Rodar a partir da raiz do projeto:  python -m unittest tests.test_produtos
"""

import shutil
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src import banco, categorias, produtos


class TestProdutos(unittest.TestCase):
    def setUp(self):
        pasta = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, pasta, ignore_errors=True)
        patcher = patch.object(banco, "CAMINHO_PADRAO", Path(pasta) / "teste.db")
        patcher.start()
        self.addCleanup(patcher.stop)

        conexao = banco.conectar()
        banco.criar_tabelas(conexao)
        banco.fechar_conexao(conexao)

        self.perifericos = categorias.cadastrar_categoria("Periféricos")["id"]
        self.cabos = categorias.cadastrar_categoria("Cabos")["id"]

    def _definir_saldo(self, produto_id, saldo):
        """Simula uma movimentação: só o módulo de movimentações altera o saldo."""
        conexao = banco.conectar()
        try:
            with conexao:
                conexao.execute(
                    "UPDATE produtos SET estoque_atual = ? WHERE id = ?",
                    (saldo, produto_id),
                )
        finally:
            banco.fechar_conexao(conexao)

    def _linhas_no_banco(self):
        conexao = banco.conectar()
        try:
            return conexao.execute(
                "SELECT codigo, nome, preco, estoque_minimo, estoque_atual, "
                "categoria_id, ativo FROM produtos ORDER BY id"
            ).fetchall()
        finally:
            banco.fechar_conexao(conexao)

    def test_produto_cadastrado_fica_gravado_na_tabela_oficial(self):
        self._mouse()

        linhas = self._linhas_no_banco()

        self.assertEqual(
            [tuple(l) for l in linhas],
            [("MS-01", "Mouse Óptico", 49.9, 5, 0, self.perifericos, 1)],
        )

    def test_desativar_produto_grava_ativo_zero_na_tabela_oficial(self):
        self._mouse()

        produtos.desativar_produto(1)

        self.assertEqual(self._linhas_no_banco()[0]["ativo"], 0)

    def _mouse(self, **extra):
        dados = dict(
            codigo="MS-01", nome="Mouse Óptico", preco=49.9,
            estoque_minimo=5, categoria_id=self.perifericos,
        )
        dados.update(extra)
        return produtos.cadastrar_produto(**dados)

    # ---------- cadastro ----------

    def test_cadastrar_produto_nasce_ativo_e_com_estoque_zerado(self):
        produto = self._mouse()

        self.assertEqual(produto["id"], 1)
        self.assertEqual(produto["codigo"], "MS-01")
        self.assertEqual(produto["preco"], 49.9)
        self.assertEqual(produto["estoque_minimo"], 5)
        self.assertEqual(produto["estoque_atual"], 0)
        self.assertTrue(produto["ativo"])

    def test_cadastrar_produto_remove_espacos_e_aceita_preco_em_texto(self):
        produto = self._mouse(codigo=" MS-01 ", nome=" Mouse ", preco="49.90")

        self.assertEqual(produto["codigo"], "MS-01")
        self.assertEqual(produto["nome"], "Mouse")
        self.assertEqual(produto["preco"], 49.9)

    def test_cadastrar_produto_exige_codigo_e_nome(self):
        for campo in ("codigo", "nome"):
            for valor in ("", "   ", None):
                with self.subTest(campo=campo, valor=valor):
                    with self.assertRaises(ValueError):
                        self._mouse(**{campo: valor})

    def test_cadastrar_produto_nao_aceita_codigo_repetido_ignorando_caixa(self):
        self._mouse()

        for repetido in ("MS-01", "ms-01"):
            with self.subTest(codigo=repetido):
                with self.assertRaises(ValueError):
                    self._mouse(codigo=repetido, nome="Outro")

    def test_cadastrar_produto_valida_preco(self):
        for preco in (-1, "abc", None):
            with self.subTest(preco=preco):
                with self.assertRaises(ValueError):
                    self._mouse(preco=preco)

    def test_cadastrar_produto_aceita_preco_zero(self):
        self.assertEqual(self._mouse(preco=0)["preco"], 0)

    def test_cadastrar_produto_valida_estoque_minimo(self):
        for minimo in (-1, 1.5, "3", None, True):
            with self.subTest(estoque_minimo=minimo):
                with self.assertRaises(ValueError):
                    self._mouse(estoque_minimo=minimo)

    def test_cadastrar_produto_aceita_estoque_minimo_zero(self):
        self.assertEqual(self._mouse(estoque_minimo=0)["estoque_minimo"], 0)

    def test_cadastrar_produto_exige_categoria_existente(self):
        for categoria in (99, None):
            with self.subTest(categoria_id=categoria):
                with self.assertRaises(ValueError):
                    self._mouse(categoria_id=categoria)

    def test_produto_invalido_nao_e_gravado(self):
        with self.assertRaises(ValueError):
            self._mouse(preco=-5)

        self.assertEqual(produtos.listar_produtos(incluir_inativos=True), [])

    # ---------- consulta ----------

    def test_buscar_produto_existente_e_inexistente(self):
        self._mouse()

        self.assertEqual(produtos.buscar_produto(1)["nome"], "Mouse Óptico")
        self.assertIsNone(produtos.buscar_produto(99))

    def test_buscar_produto_por_codigo_ignora_caixa_e_espacos(self):
        self._mouse()

        self.assertEqual(produtos.buscar_produto_por_codigo(" ms-01 ")["id"], 1)
        self.assertIsNone(produtos.buscar_produto_por_codigo("MS"))
        self.assertIsNone(produtos.buscar_produto_por_codigo(""))
        self.assertIsNone(produtos.buscar_produto_por_codigo(None))

    def test_listar_produtos_ordena_por_nome(self):
        self._mouse()
        self._mouse(codigo="CB-01", nome="Cabo USB", categoria_id=self.cabos)

        nomes = [p["nome"] for p in produtos.listar_produtos()]

        self.assertEqual(nomes, ["Cabo USB", "Mouse Óptico"])

    # ---------- edição ----------

    def test_editar_produto_altera_so_o_que_foi_informado(self):
        self._mouse()

        editado = produtos.editar_produto(1, preco=59.9, estoque_minimo=8)

        self.assertEqual(editado["preco"], 59.9)
        self.assertEqual(editado["estoque_minimo"], 8)
        self.assertEqual(editado["nome"], "Mouse Óptico")
        self.assertEqual(editado["codigo"], "MS-01")

    def test_editar_produto_troca_de_categoria(self):
        self._mouse()

        editado = produtos.editar_produto(1, categoria_id=self.cabos)

        self.assertEqual(editado["categoria_id"], self.cabos)

    def test_editar_produto_pode_manter_o_proprio_codigo(self):
        self._mouse()

        self.assertEqual(produtos.editar_produto(1, codigo="ms-01")["codigo"], "ms-01")

    def test_editar_produto_nao_aceita_codigo_de_outro(self):
        self._mouse()
        self._mouse(codigo="CB-01", nome="Cabo USB", categoria_id=self.cabos)

        with self.assertRaises(ValueError):
            produtos.editar_produto(2, codigo="MS-01")

    def test_editar_produto_valida_os_campos(self):
        self._mouse()

        for campo, valor in (
            ("nome", "  "),
            ("preco", -1),
            ("estoque_minimo", -1),
            ("categoria_id", 99),
        ):
            with self.subTest(campo=campo, valor=valor):
                with self.assertRaises(ValueError):
                    produtos.editar_produto(1, **{campo: valor})

    def test_editar_produto_inexistente(self):
        with self.assertRaises(ValueError):
            produtos.editar_produto(99, nome="X")

    def test_editar_produto_nao_altera_o_saldo_em_estoque(self):
        self._mouse()
        self._definir_saldo(1, 12)

        editado = produtos.editar_produto(1, nome="Mouse Gamer")

        self.assertEqual(editado["estoque_atual"], 12)

    # ---------- desativação ----------

    def test_desativar_produto_some_da_listagem_padrao_mas_nao_e_apagado(self):
        self._mouse()
        self._mouse(codigo="CB-01", nome="Cabo USB", categoria_id=self.cabos)

        desativado = produtos.desativar_produto(2)

        self.assertFalse(desativado["ativo"])
        self.assertEqual([p["id"] for p in produtos.listar_produtos()], [1])
        self.assertEqual(len(produtos.listar_produtos(incluir_inativos=True)), 2)
        self.assertIsNotNone(produtos.buscar_produto(2))

    def test_desativar_produto_inexistente(self):
        with self.assertRaises(ValueError):
            produtos.desativar_produto(99)

    # ---------- filtros ----------

    def _catalogo(self):
        self._mouse()
        self._mouse(codigo="TC-01", nome="Teclado", categoria_id=self.perifericos)
        self._mouse(codigo="CB-01", nome="Cabo USB", categoria_id=self.cabos)
        self._mouse(codigo="CB-02", nome="Cabo HDMI", categoria_id=self.cabos)
        produtos.desativar_produto(4)

    def _nomes(self, **filtros):
        return [p["nome"] for p in produtos.listar_produtos(**filtros)]

    def test_filtro_por_nome_ignora_caixa_e_acento(self):
        self._catalogo()

        self.assertEqual(self._nomes(nome="óptico"), ["Mouse Óptico"])
        self.assertEqual(self._nomes(nome="ÓPTICO"), ["Mouse Óptico"])
        self.assertEqual(self._nomes(nome="optico"), ["Mouse Óptico"])
        self.assertEqual(self._nomes(nome="cabo"), ["Cabo USB"])

    def test_filtro_por_codigo_busca_trecho(self):
        self._catalogo()

        self.assertEqual(self._nomes(codigo="tc"), ["Teclado"])
        self.assertEqual(self._nomes(codigo="CB"), ["Cabo USB"])

    def test_filtro_por_categoria(self):
        self._catalogo()

        self.assertEqual(
            self._nomes(categoria_id=self.perifericos), ["Mouse Óptico", "Teclado"]
        )
        self.assertEqual(self._nomes(categoria_id=self.cabos), ["Cabo USB"])

    def test_filtros_combinados(self):
        self._catalogo()

        self.assertEqual(self._nomes(categoria_id=self.perifericos, nome="tec"), ["Teclado"])
        self.assertEqual(self._nomes(categoria_id=self.cabos, nome="tec"), [])

    def test_filtro_vazio_ou_em_branco_nao_filtra(self):
        self._catalogo()

        self.assertEqual(self._nomes(nome="   "), self._nomes())
        self.assertEqual(self._nomes(codigo=""), self._nomes())

    def test_filtro_sem_resultado_devolve_lista_vazia(self):
        self._catalogo()

        self.assertEqual(self._nomes(nome="inexistente"), [])

    def test_filtro_respeita_inativos(self):
        self._catalogo()

        self.assertEqual(self._nomes(nome="cabo"), ["Cabo USB"])
        self.assertEqual(
            self._nomes(nome="cabo", incluir_inativos=True), ["Cabo HDMI", "Cabo USB"]
        )


    # ---------- compatibilidade com o menu do main.py ----------

    def test_editar_produto_aceita_a_ordem_posicional_do_menu(self):
        # main.py chama: editar_produto(id, nome, preco, estoque_minimo, categoria_id)
        self._mouse()

        editado = produtos.editar_produto(1, "Mouse Gamer", 70.0, 8, self.cabos)

        self.assertEqual(editado["codigo"], "MS-01")
        self.assertEqual(editado["nome"], "Mouse Gamer")
        self.assertEqual(editado["preco"], 70.0)
        self.assertEqual(editado["estoque_minimo"], 8)
        self.assertEqual(editado["categoria_id"], self.cabos)

    # ---------- busca por termo (nome, código ou categoria) ----------

    def _ids(self, termo, **extra):
        return [p["id"] for p in produtos.buscar_produtos(termo, **extra)]

    def test_buscar_produtos_por_nome_codigo_e_categoria(self):
        self._catalogo()  # 1 Mouse Óptico, 2 Teclado (Periféricos); 3 Cabo USB (Cabos); 4 inativo

        self.assertEqual(self._ids("óptico"), [1])
        self.assertEqual(self._ids("tc-01"), [2])
        self.assertEqual(self._ids("periféricos"), [1, 2])

    def test_buscar_produtos_ignora_caixa_e_acento(self):
        self._catalogo()

        self.assertEqual(self._ids("ÓPTICO"), [1])
        self.assertEqual(self._ids("optico"), [1])
        self.assertEqual(self._ids("PERIFERICOS"), [1, 2])
        self.assertEqual(self._ids("periféricos"), self._ids("PERIFÉRICOS"))

    def test_buscar_produtos_so_ativos_por_padrao(self):
        self._catalogo()

        self.assertEqual(self._ids("hdmi"), [])
        self.assertEqual(self._ids("hdmi", incluir_inativos=True), [4])

    def test_buscar_produtos_termo_vazio_ou_sem_resultado(self):
        self._catalogo()

        for termo in ("", "   ", None, "inexistente"):
            with self.subTest(termo=termo):
                self.assertEqual(produtos.buscar_produtos(termo), [])

    def test_buscar_produtos_devolve_dados_completos(self):
        self._catalogo()

        produto = produtos.buscar_produtos("teclado")[0]

        self.assertEqual(produto["codigo"], "TC-01")
        self.assertEqual(produto["categoria_id"], self.perifericos)
        self.assertTrue(produto["ativo"])


    # ---------- conexões ----------

    def _rastrear_conexoes(self):
        """Registra cada conexão aberta pelos módulos para conferir se foi fechada."""
        abertas = []
        original = banco.conectar

        def conectar_rastreado(*args, **kwargs):
            conexao = original(*args, **kwargs)
            abertas.append(conexao)
            return conexao

        for modulo in (categorias, produtos):
            patcher = patch.object(modulo, "conectar", conectar_rastreado)
            patcher.start()
            self.addCleanup(patcher.stop)
        return abertas

    @staticmethod
    def _esta_fechada(conexao):
        try:
            conexao.execute("SELECT 1")
        except sqlite3.ProgrammingError:
            return True
        return False

    def test_toda_operacao_fecha_a_conexao_que_abriu(self):
        abertas = self._rastrear_conexoes()

        self._mouse()
        produtos.listar_produtos()
        produtos.listar_produtos(nome="mouse")
        produtos.buscar_produto(1)
        produtos.buscar_produto_por_codigo("MS-01")
        produtos.buscar_produtos("mouse")
        produtos.editar_produto(1, nome="Mouse Gamer")
        produtos.desativar_produto(1)

        self.assertGreaterEqual(len(abertas), 8)
        self.assertTrue(all(self._esta_fechada(c) for c in abertas))

    def test_conexao_e_fechada_mesmo_quando_a_operacao_falha(self):
        self._mouse()
        abertas = self._rastrear_conexoes()

        with self.assertRaises(ValueError):
            self._mouse(codigo="ms-01")  # código repetido, falha dentro da transação
        with self.assertRaises(ValueError):
            produtos.editar_produto(1, categoria_id=99)

        self.assertTrue(abertas)
        self.assertTrue(all(self._esta_fechada(c) for c in abertas))


if __name__ == "__main__":
    unittest.main()
