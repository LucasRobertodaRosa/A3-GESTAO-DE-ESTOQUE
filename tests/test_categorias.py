"""Testes de src/categorias.py.

Usam o schema OFICIAL (banco.criar_tabelas) em um arquivo temporário novo a cada
teste, sem tocar no estoque.db real.
Rodar a partir da raiz do projeto:  python -m unittest tests.test_categorias
"""

import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src import banco, categorias


class TestCategorias(unittest.TestCase):
    def setUp(self):
        pasta = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, pasta, ignore_errors=True)
        patcher = patch.object(banco, "CAMINHO_PADRAO", Path(pasta) / "teste.db")
        patcher.start()
        self.addCleanup(patcher.stop)

        conexao = banco.conectar()
        banco.criar_tabelas(conexao)
        banco.fechar_conexao(conexao)

    def _linhas_no_banco(self):
        conexao = banco.conectar()
        try:
            return conexao.execute(
                "SELECT id, nome, descricao, ativo FROM categorias ORDER BY id"
            ).fetchall()
        finally:
            banco.fechar_conexao(conexao)

    def test_categoria_cadastrada_fica_gravada_na_tabela_oficial(self):
        categorias.cadastrar_categoria("Cabos", "Cabos em geral")

        linhas = self._linhas_no_banco()

        self.assertEqual(len(linhas), 1)
        self.assertEqual(tuple(linhas[0]), (1, "Cabos", "Cabos em geral", 1))

    def test_cadastrar_categoria_devolve_dados_com_id(self):
        cat = categorias.cadastrar_categoria("Periféricos", "Teclados e mouses")

        self.assertEqual(cat["id"], 1)
        self.assertEqual(cat["nome"], "Periféricos")
        self.assertEqual(cat["descricao"], "Teclados e mouses")

    def test_cadastrar_categoria_remove_espacos_e_descricao_padrao_vazia(self):
        cat = categorias.cadastrar_categoria("  Cabos  ")

        self.assertEqual(cat["nome"], "Cabos")
        self.assertEqual(cat["descricao"], "")

    def test_cadastrar_categoria_exige_nome(self):
        for nome in ("", "   ", None):
            with self.subTest(nome=nome):
                with self.assertRaises(ValueError):
                    categorias.cadastrar_categoria(nome)

    def test_cadastrar_categoria_nao_aceita_nome_repetido_ignorando_caixa_e_acento(self):
        categorias.cadastrar_categoria("Periféricos")

        for repetido in ("Periféricos", "periféricos", "PERIFÉRICOS"):
            with self.subTest(nome=repetido):
                with self.assertRaises(ValueError):
                    categorias.cadastrar_categoria(repetido)

    def test_listar_categorias_ordena_por_nome(self):
        categorias.cadastrar_categoria("Periféricos")
        categorias.cadastrar_categoria("Cabos")

        nomes = [c["nome"] for c in categorias.listar_categorias()]

        self.assertEqual(nomes, ["Cabos", "Periféricos"])

    def test_listar_categorias_vazio(self):
        self.assertEqual(categorias.listar_categorias(), [])

    def test_buscar_categoria_existente(self):
        categorias.cadastrar_categoria("Cabos")

        self.assertEqual(categorias.buscar_categoria(1)["nome"], "Cabos")

    def test_buscar_categoria_inexistente_devolve_none(self):
        self.assertIsNone(categorias.buscar_categoria(99))

    def test_editar_categoria_altera_so_o_que_foi_informado(self):
        categorias.cadastrar_categoria("Periféricos", "Teclados")

        editada = categorias.editar_categoria(1, descricao="Teclados e mouses")

        self.assertEqual(editada["nome"], "Periféricos")
        self.assertEqual(editada["descricao"], "Teclados e mouses")
        self.assertEqual(categorias.buscar_categoria(1), editada)

    def test_editar_categoria_pode_manter_o_proprio_nome(self):
        categorias.cadastrar_categoria("Cabos")

        editada = categorias.editar_categoria(1, nome="CABOS")

        self.assertEqual(editada["nome"], "CABOS")

    def test_editar_categoria_nao_aceita_nome_de_outra(self):
        categorias.cadastrar_categoria("Periféricos")
        categorias.cadastrar_categoria("Cabos")

        with self.assertRaises(ValueError):
            categorias.editar_categoria(2, nome="periféricos")

    def test_editar_categoria_nao_aceita_nome_vazio(self):
        categorias.cadastrar_categoria("Cabos")

        with self.assertRaises(ValueError):
            categorias.editar_categoria(1, nome="  ")

    def test_editar_categoria_inexistente(self):
        with self.assertRaises(ValueError):
            categorias.editar_categoria(99, nome="X")


if __name__ == "__main__":
    unittest.main()
