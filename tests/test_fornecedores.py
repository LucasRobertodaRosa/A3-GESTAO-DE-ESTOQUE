"""Testes do módulo de fornecedores (e da integração com banco e auditoria).

Como executar, na raiz do projeto (funciona com unittest e com pytest):

    python -m unittest discover -s tests -v
    python -m pytest tests/test_fornecedores.py -v

Os testes usam um banco SQLite em memória, então não mexem no estoque.db.
"""

import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

# Permite executar o arquivo de qualquer lugar: coloca a raiz do projeto no path.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import auditoria, banco  # noqa: E402
from src.banco import conectar, criar_tabelas, fechar_conexao  # noqa: E402
from src.fornecedores import (  # noqa: E402
    buscar_fornecedor,
    cadastrar_fornecedor,
    desativar_fornecedor,
    editar_fornecedor,
    listar_fornecedores,
    validar_cnpj,
)

CNPJ_A = "11.222.333/0001-81"   # válido
CNPJ_B = "11.444.777/0001-61"   # válido, diferente do A


class BaseComBanco(unittest.TestCase):
    """Cada teste ganha um banco novo, em memória e já com as tabelas."""

    def setUp(self):
        self.con = conectar(":memory:")
        criar_tabelas(self.con)
        self.addCleanup(fechar_conexao, self.con)

    def cadastrar(self, nome="Fornecedor Teste", **campos):
        return cadastrar_fornecedor(nome, conexao=self.con, **campos)

    def total_no_banco(self):
        return self.con.execute("SELECT COUNT(*) FROM fornecedores").fetchone()[0]


# --------------------------------------------------------------------------
# CNPJ
# --------------------------------------------------------------------------

class TestValidarCnpj(unittest.TestCase):
    def test_aceita_cnpj_com_e_sem_mascara(self):
        self.assertTrue(validar_cnpj("11.222.333/0001-81"))
        self.assertTrue(validar_cnpj("11222333000181"))

    def test_rejeita_digito_verificador_errado(self):
        self.assertFalse(validar_cnpj("11222333000182"))
        self.assertFalse(validar_cnpj("11.222.333/0001-80"))

    def test_rejeita_sequencia_de_digitos_repetidos(self):
        self.assertFalse(validar_cnpj("00000000000000"))
        self.assertFalse(validar_cnpj("11111111111111"))

    def test_rejeita_tamanho_errado(self):
        self.assertFalse(validar_cnpj("123"))
        self.assertFalse(validar_cnpj("112223330001811"))

    def test_rejeita_vazio_e_none(self):
        self.assertFalse(validar_cnpj(""))
        self.assertFalse(validar_cnpj(None))


# --------------------------------------------------------------------------
# Cadastro
# --------------------------------------------------------------------------

class TestCadastrarFornecedor(BaseComBanco):
    def test_cadastra_e_normaliza_os_dados(self):
        fid = self.cadastrar(
            "  Sul Distribuidora  ",
            cnpj=CNPJ_A,
            telefone="(48) 99999-1234",
            email="  Contato@Sul.com ",
        )
        self.assertIsInstance(fid, int)

        fornecedor = buscar_fornecedor(fid, conexao=self.con)
        self.assertEqual(fornecedor["nome"], "Sul Distribuidora")
        self.assertEqual(fornecedor["cnpj"], "11222333000181")
        self.assertEqual(fornecedor["telefone"], "48999991234")
        self.assertEqual(fornecedor["email"], "contato@sul.com")
        self.assertEqual(fornecedor["ativo"], 1)

    def test_cadastra_apenas_com_nome(self):
        fornecedor = buscar_fornecedor(self.cadastrar("Só Nome"), conexao=self.con)
        self.assertIsNone(fornecedor["cnpj"])
        self.assertIsNone(fornecedor["telefone"])
        self.assertIsNone(fornecedor["email"])

    def test_nome_e_obrigatorio(self):
        for nome in ("", "   ", None):
            with self.subTest(nome=nome):
                with self.assertRaises(ValueError):
                    cadastrar_fornecedor(nome, conexao=self.con)
        self.assertEqual(self.total_no_banco(), 0)

    def test_nome_tem_no_maximo_100_caracteres(self):
        self.cadastrar("A" * 100)
        with self.assertRaises(ValueError):
            self.cadastrar("A" * 101)

    def test_rejeita_cnpj_invalido(self):
        for cnpj in ("123", "11222333000182", "11111111111111"):
            with self.subTest(cnpj=cnpj):
                with self.assertRaisesRegex(ValueError, "CNPJ"):
                    self.cadastrar(cnpj=cnpj)
        self.assertEqual(self.total_no_banco(), 0)

    def test_rejeita_cnpj_duplicado_mesmo_com_mascara_diferente(self):
        self.cadastrar("Primeiro", cnpj="11.222.333/0001-81")
        with self.assertRaisesRegex(ValueError, "CNPJ"):
            self.cadastrar("Segundo", cnpj="11222333000181")
        self.assertEqual(self.total_no_banco(), 1)

    def test_permite_varios_fornecedores_sem_cnpj(self):
        self.cadastrar("Sem CNPJ 1")
        self.cadastrar("Sem CNPJ 2")
        self.assertEqual(self.total_no_banco(), 2)

    def test_rejeita_email_invalido(self):
        for email in ("abc", "a@b", "a b@c.com", "@c.com"):
            with self.subTest(email=email):
                with self.assertRaisesRegex(ValueError, "mail"):
                    self.cadastrar(email=email)

    def test_valida_tamanho_do_telefone(self):
        for telefone in ("123", "123456789012"):
            with self.subTest(telefone=telefone):
                with self.assertRaisesRegex(ValueError, "[Tt]elefone"):
                    self.cadastrar(telefone=telefone)
        self.cadastrar("Fixo", telefone="(48) 3333-4444")      # 10 dígitos
        self.cadastrar("Celular", telefone="(48) 99999-4444")  # 11 dígitos


# --------------------------------------------------------------------------
# Listagem e busca
# --------------------------------------------------------------------------

class TestListarEBuscar(BaseComBanco):
    def test_lista_vazia(self):
        self.assertEqual(listar_fornecedores(conexao=self.con), [])

    def test_lista_em_ordem_alfabetica_sem_diferenciar_maiusculas(self):
        for nome in ("beta", "Alfa", "Cristal"):
            self.cadastrar(nome)
        nomes = [f["nome"] for f in listar_fornecedores(conexao=self.con)]
        self.assertEqual(nomes, ["Alfa", "beta", "Cristal"])

    def test_lista_so_ativos_por_padrao(self):
        self.cadastrar("Ativo")
        inativo = self.cadastrar("Inativo")
        desativar_fornecedor(inativo, conexao=self.con)

        ativos = [f["nome"] for f in listar_fornecedores(conexao=self.con)]
        todos = [f["nome"] for f in
                 listar_fornecedores(apenas_ativos=False, conexao=self.con)]
        self.assertEqual(ativos, ["Ativo"])
        self.assertEqual(todos, ["Ativo", "Inativo"])

    def test_busca_fornecedor_existente(self):
        fid = self.cadastrar("Buscado", cnpj=CNPJ_A)
        fornecedor = buscar_fornecedor(fid, conexao=self.con)
        self.assertEqual(fornecedor["id"], fid)
        self.assertEqual(fornecedor["nome"], "Buscado")

    def test_busca_inexistente_devolve_none(self):
        self.assertIsNone(buscar_fornecedor(999, conexao=self.con))

    def test_busca_encontra_fornecedor_desativado(self):
        fid = self.cadastrar("Antigo")
        desativar_fornecedor(fid, conexao=self.con)
        self.assertEqual(buscar_fornecedor(fid, conexao=self.con)["ativo"], 0)


# --------------------------------------------------------------------------
# Edição
# --------------------------------------------------------------------------

class TestEditarFornecedor(BaseComBanco):
    def setUp(self):
        super().setUp()
        self.fid = self.cadastrar(
            "Original", cnpj=CNPJ_A, telefone="48999991234", email="a@a.com"
        )

    def test_altera_apenas_os_campos_informados(self):
        atualizado = editar_fornecedor(self.fid, nome="Novo Nome", conexao=self.con)
        self.assertEqual(atualizado["nome"], "Novo Nome")
        self.assertEqual(atualizado["cnpj"], "11222333000181")
        self.assertEqual(atualizado["telefone"], "48999991234")
        self.assertEqual(atualizado["email"], "a@a.com")

    def test_devolve_o_fornecedor_atualizado_e_grava_no_banco(self):
        atualizado = editar_fornecedor(
            self.fid, email="NOVO@Email.com", conexao=self.con
        )
        self.assertEqual(atualizado, buscar_fornecedor(self.fid, conexao=self.con))
        self.assertEqual(atualizado["email"], "novo@email.com")

    def test_string_vazia_limpa_campo_opcional(self):
        atualizado = editar_fornecedor(
            self.fid, email="", telefone="", cnpj="", conexao=self.con
        )
        self.assertIsNone(atualizado["email"])
        self.assertIsNone(atualizado["telefone"])
        self.assertIsNone(atualizado["cnpj"])

    def test_aceita_reenviar_o_proprio_cnpj(self):
        atualizado = editar_fornecedor(
            self.fid, nome="Outro", cnpj=CNPJ_A, conexao=self.con
        )
        self.assertEqual(atualizado["cnpj"], "11222333000181")

    def test_sem_nenhum_campo_levanta_erro(self):
        with self.assertRaises(ValueError):
            editar_fornecedor(self.fid, conexao=self.con)

    def test_fornecedor_inexistente_levanta_erro(self):
        with self.assertRaisesRegex(ValueError, "não encontrado"):
            editar_fornecedor(999, nome="X", conexao=self.con)

    def test_cnpj_de_outro_fornecedor_e_rejeitado_sem_alterar_nada(self):
        segundo = self.cadastrar("Segundo", cnpj=CNPJ_B)
        with self.assertRaisesRegex(ValueError, "CNPJ"):
            editar_fornecedor(segundo, nome="Mudou", cnpj=CNPJ_A, conexao=self.con)

        fornecedor = buscar_fornecedor(segundo, conexao=self.con)
        self.assertEqual(fornecedor["nome"], "Segundo")
        self.assertEqual(fornecedor["cnpj"], "11444777000161")

    def test_valida_os_novos_valores(self):
        casos = (
            {"nome": "   "},
            {"cnpj": "123"},
            {"email": "invalido"},
            {"telefone": "12"},
        )
        for campos in casos:
            with self.subTest(campos=campos):
                with self.assertRaises(ValueError):
                    editar_fornecedor(self.fid, conexao=self.con, **campos)
        self.assertEqual(buscar_fornecedor(self.fid, conexao=self.con)["nome"],
                         "Original")


# --------------------------------------------------------------------------
# Desativação
# --------------------------------------------------------------------------

class TestDesativarFornecedor(BaseComBanco):
    def test_marca_como_inativo_e_devolve_true(self):
        fid = self.cadastrar("Vai sair")
        self.assertTrue(desativar_fornecedor(fid, conexao=self.con))
        self.assertEqual(buscar_fornecedor(fid, conexao=self.con)["ativo"], 0)
        self.assertEqual(listar_fornecedores(conexao=self.con), [])

    def test_nao_apaga_o_registro(self):
        fid = self.cadastrar("Continua no banco")
        desativar_fornecedor(fid, conexao=self.con)
        self.assertEqual(self.total_no_banco(), 1)

    def test_desativar_duas_vezes_nao_da_erro(self):
        fid = self.cadastrar("Repetido")
        desativar_fornecedor(fid, conexao=self.con)
        self.assertTrue(desativar_fornecedor(fid, conexao=self.con))

    def test_fornecedor_inexistente_levanta_erro(self):
        with self.assertRaisesRegex(ValueError, "não encontrado"):
            desativar_fornecedor(999, conexao=self.con)


# --------------------------------------------------------------------------
# Persistência e integração entre módulos
# --------------------------------------------------------------------------

class TestPersistencia(unittest.TestCase):
    def test_dados_continuam_depois_de_fechar_e_reabrir_o_banco(self):
        with tempfile.TemporaryDirectory() as pasta:
            arquivo = Path(pasta) / "teste.db"
            # Sem passar `conexao`, as funções usam o banco padrão.
            with mock.patch.object(banco, "CAMINHO_PADRAO", arquivo):
                inicial = conectar()
                criar_tabelas(inicial)
                fechar_conexao(inicial)

                fid = cadastrar_fornecedor("Persistente", CNPJ_A)

                # Conexão nova e independente, como numa próxima execução.
                nova = conectar()
                try:
                    linha = nova.execute(
                        "SELECT nome, cnpj FROM fornecedores WHERE id = ?", (fid,)
                    ).fetchone()
                finally:
                    fechar_conexao(nova)

                self.assertEqual(linha["nome"], "Persistente")
                self.assertEqual(linha["cnpj"], "11222333000181")
                self.assertEqual(len(listar_fornecedores()), 1)


class TestIntegracao(BaseComBanco):
    """Fornecedores trabalhando junto com produtos, entradas e auditoria."""

    def setUp(self):
        super().setUp()
        self.con.execute("INSERT INTO categorias (nome) VALUES ('Geral')")
        self.con.execute(
            "INSERT INTO produtos (codigo, nome, preco, categoria_id) "
            "VALUES ('P1', 'Caneta', 2.5, 1)"
        )
        self.con.execute(
            "INSERT INTO funcionarios (nome, login, senha_hash, perfil) "
            "VALUES ('Ana', 'ana', 'hash', 'ADMIN')"
        )
        self.con.commit()

    def registrar_entrada(self, fornecedor_id, quantidade=10):
        self.con.execute(
            "INSERT INTO movimentacoes (produto_id, tipo, quantidade, fornecedor_id) "
            "VALUES (1, 'ENTRADA', ?, ?)",
            (quantidade, fornecedor_id),
        )
        self.con.commit()

    def entradas_com_fornecedor(self):
        return self.con.execute(
            "SELECT m.quantidade, f.nome AS fornecedor "
            "FROM movimentacoes m JOIN fornecedores f ON f.id = m.fornecedor_id"
        ).fetchall()

    def test_entrada_de_estoque_fica_ligada_ao_fornecedor(self):
        fid = self.cadastrar("Sul Distribuidora", cnpj=CNPJ_A)
        self.registrar_entrada(fid, quantidade=10)

        entradas = self.entradas_com_fornecedor()
        self.assertEqual(len(entradas), 1)
        self.assertEqual(entradas[0]["fornecedor"], "Sul Distribuidora")
        self.assertEqual(entradas[0]["quantidade"], 10)

    def test_desativar_fornecedor_preserva_o_historico_de_entradas(self):
        fid = self.cadastrar("Antigo Fornecedor")
        self.registrar_entrada(fid)
        desativar_fornecedor(fid, conexao=self.con)

        entradas = self.entradas_com_fornecedor()
        self.assertEqual(len(entradas), 1)
        self.assertEqual(entradas[0]["fornecedor"], "Antigo Fornecedor")

    def test_banco_bloqueia_entrada_com_fornecedor_inexistente(self):
        with self.assertRaises(sqlite3.IntegrityError):
            self.registrar_entrada(fornecedor_id=999)

    def test_cadastro_de_fornecedor_aparece_na_auditoria(self):
        fid = self.cadastrar("Auditado", cnpj=CNPJ_A)
        auditoria.registrar_evento(
            1, auditoria.CADASTRO, "fornecedor", fid,
            {"nome": "Auditado"}, conexao=self.con,
        )

        eventos = auditoria.listar_eventos(entidade="fornecedor", conexao=self.con)
        self.assertEqual(len(eventos), 1)
        self.assertEqual(eventos[0]["acao"], "CADASTRO")
        self.assertEqual(eventos[0]["entidade_id"], fid)
        self.assertEqual(eventos[0]["funcionario_nome"], "Ana")


if __name__ == "__main__":
    unittest.main()
