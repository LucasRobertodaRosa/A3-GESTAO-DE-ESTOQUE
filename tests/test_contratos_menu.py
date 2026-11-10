"""Verifica as referências e assinaturas das funções usadas no menu."""

import inspect

from src import main


def _argumento_exemplo(tipo):
    tipo = tipo.rstrip("?")
    if tipo in ("int", "@usuario"):
        return 1
    if tipo == "decimal":
        return 5.0
    if tipo == "perfil":
        return "ESTOQUISTA"
    if tipo == "data":
        return "2026-11-09"
    if tipo == "senha":
        return "SenhaTeste123!"
    return "exemplo"


def test_todas_as_opcoes_do_menu_tem_funcoes_compatíveis():
    """Inspeciona as chamadas sem executar operações nem alterar o banco."""
    for titulo, itens in main.MENUS:
        for item in itens:
            modulo = main._carregar(item.modulo)
            assert modulo is not None, f"Módulo ausente: {item.modulo} ({titulo})"

            funcao = getattr(modulo, item.funcao, None)
            assert callable(funcao), f"Função ausente: {item.modulo}.{item.funcao}"

            parametros = inspect.signature(funcao)
            argumentos = [_argumento_exemplo(tipo) for _, _, tipo in item.campos]
            extras = {}
            if "conexao" in parametros.parameters:
                if next(iter(parametros.parameters)) == "conexao":
                    argumentos.insert(0, None)
                else:
                    extras["conexao"] = None

            try:
                parametros.bind(*argumentos, **extras)
            except TypeError as erro:
                raise AssertionError(
                    f"Contrato incompatível em '{titulo} / {item.rotulo}': {erro}"
                ) from erro


def test_busca_textual_usa_funcao_correta():
    itens_produtos = next(itens for titulo, itens in main.MENUS if titulo == "Produtos")
    busca = next(item for item in itens_produtos if item.rotulo.startswith("Buscar produto"))
    assert busca.funcao == "buscar_produtos"
    assert [nome for nome, _, _ in busca.campos] == ["termo"]


def test_usuario_consulta_nao_tem_opcoes_de_escrita():
    verbos_escrita = ("Cadastrar", "Editar", "Desativar", "Registrar entrada", "Registrar saída")
    for _, itens in main.MENUS:
        for item in itens:
            if item.rotulo.startswith(verbos_escrita):
                assert main.CONSULTA not in item.perfis, item.rotulo
