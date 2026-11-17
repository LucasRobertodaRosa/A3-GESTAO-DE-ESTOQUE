# Contrato de integração do frontend — Gestão de Estoque

## Situação atual

O backend é Python + SQLite e atualmente executa um menu de terminal.
**Não existe API REST autenticada implementada neste pacote.** Para um frontend
Streamlit local, chamar os módulos Python. Para React ou frontend remoto, projetar
uma API autenticada separadamente, antes de expor a aplicação na internet.

## Banco oficial

Criado por `src.banco.criar_tabelas(conexao)`. Principais tabelas:
`categorias`, `produtos`, `fornecedores`, `funcionarios`, `movimentacoes`, `auditoria`.
Saldo: `produtos.estoque_atual`; histórico: `movimentacoes.tipo` em `ENTRADA`/`SAIDA`.
Não editar o saldo diretamente pela interface.

## Contratos de funções existentes

- `src.banco.conectar(caminho=None)` e `criar_tabelas(conexao)`.
- `src.autenticacao.login(login, senha, conexao=None)` → dict ou `None`.
- `src.autenticacao.tem_permissao(usuario, *perfis_permitidos)` → bool.
- `src.produtos.buscar_produtos(termo, incluir_inativos=False)` → lista de dicts.
- `src.produtos.buscar_produto(produto_id)` → dict ou `None`.
- `src.produtos.cadastrar_produto(codigo, nome, preco, estoque_minimo, categoria_id)` → produto.
- `src.movimentacoes.registrar_entrada(produto_id, quantidade, fornecedor_id=None, funcionario_id=None, conexao=None)` → ID.
- `src.movimentacoes.registrar_saida(produto_id, quantidade, destinatario=None, funcionario_id=None, conexao=None)` → ID.
- `src.movimentacoes.listar_movimentacoes(...)` → lista; verificar opções no módulo.
- `src.relatorios.relatorio_estoque(incluir_inativos=False, conexao=None)` → lista de dicts.
- `src.funcionarios.cadastrar_funcionario(nome, login, senha, perfil, conexao=None)` → ID.
- `src.funcionarios.editar_funcionario(funcionario_id, nome=None, perfil=None, conexao=None)` → funcionário.

As funções de `produtos`/`categorias` usam conexões próprias. Antes de suportar
múltiplos usuários ou deploy remoto, recomenda-se introduzir camada de serviço
com injeção de conexão e transações explícitas.

## Permissões

Perfis: `ADMIN`, `ESTOQUISTA`, `CONSULTA`. O menu filtra operações conforme o
perfil, mas **não basta esconder botões no frontend**. Um serviço web deverá
verificar a autorização a cada operação de escrita.

## Comportamentos obrigatórios

- Quantidade deve ser inteiro maior que zero.
- Saída acima do saldo deve levantar `ValueError`, sem registrar movimento.
- Produto inexistente/inativo deve ser rejeitado.
- Login inválido retorna `None`.
- Nunca exibir, guardar em logs nem enviar de volta senhas ou hashes.
- Conexão de banco deve ser fechada após uso.

## Testes mínimos da tela de movimentações

1. Criar categoria e produto com 0 unidades.
2. Entrada de 15 unidades => saldo 15.
3. Saída de 3 unidades => saldo 12.
4. Tentar saída de 20 unidades => rejeitada e saldo permanece 12.
5. Histórico com apenas 2 movimentos válidos.
6. Perfil `CONSULTA` não pode registrar entradas ou saídas.

## Decisão de frontend

- Streamlit local: menor esforço para demonstração. Usar autenticação e
  verificação de permissão em cada ação da UI, mantendo execução local.
- React: requer API HTTP com autenticação, sessões/tokens, autorização,
  tratamento de erros e proteção de operações concorrentes. Não tratar como
  funcionalidade pronta.
