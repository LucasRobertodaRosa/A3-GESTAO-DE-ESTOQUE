"""Testes de src/categorias.py.

Usam um banco SQLite em memória (um novo a cada teste), sem tocar no banco real.
Rodar a partir da raiz do projeto:  python -m pytest tests/test_categorias.py
"""

import sqlite3
import unittest
from unittest.mock import patch

from src import categorias


class TestCategorias(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.execute(
            "CREATE TABLE categorias (id INTEGER PRIMARY KEY AUTOINCREMENT, "
            "nome TEXT NOT NULL UNIQUE, descricao TEXT)"
        )
        patcher = patch.object(categorias, "conectar", lambda: self.conn)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(self.conn.close)

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
