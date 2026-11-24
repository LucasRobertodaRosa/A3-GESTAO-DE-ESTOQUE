# Front-end web (Flask)

O front-end fica em `src/web.py` (rotas), `src/templates/` (HTML) e `src/static/` (CSS e JS).
Ele **não duplica regras de negócio**: cada tela chama as mesmas funções dos módulos
(`produtos`, `movimentacoes`, ...) que o menu de terminal chama.

## Como as telas são geradas

A tabela `MENUS` de `src/main.py` descreve cada opção: módulo, função, campos e perfis
permitidos. O site percorre essa tabela:

| Elemento do `Item` | Vira, no site |
|---|---|
| `rotulo` | título da página e link no menu lateral |
| `campos` (`texto`, `int`, `decimal`, `data`, `perfil`, `senha`, com `?` = opcional) | campos do formulário (`text`, `number`, `date`, `select`, `password`) |
| `@usuario` | id do funcionário logado, preenchido pelo servidor |
| `perfis` | quem enxerga a opção no menu **e** quem pode abrir a página (403 para os demais) |
| `auditoria` | evento registrado após o sucesso, com o mesmo formato do terminal |

Opção nova em `MENUS` aparece no site sem mexer em `web.py`.

## Rotas

| Rota | Método | Função |
|---|---|---|
| `/primeiro-acesso` | GET, POST | cria o ADMIN inicial (só existe enquanto não há funcionários) |
| `/entrar` | GET, POST | login (bloqueio de 60 s após 3 falhas seguidas do mesmo login) |
| `/sair` | POST | encerra a sessão |
| `/` | GET | painel com os indicadores de `relatorios.indicadores_gerais` |
| `/m/<grupo>/<item>` | GET, POST | formulário e resultado de uma opção de `MENUS` |
| `/m/<grupo>/<item>/csv` | GET | baixa em CSV a tabela de uma consulta (mesmos filtros, na URL) |

Consultas sem filtros (listagens, estoque atual) abrem direto no GET. Operações que gravam
usam POST, depois redirecionam (padrão Post/Redirect/Get) e mostram a confirmação.
`?id=3` na URL preenche o campo `id`.

## Listas de escolha e CSV

- Campos de ID (`id`, `produto_id`, `categoria_id`, `fornecedor_id`, `funcionario_id`) viram uma
  lista de escolha preenchida pelo banco da requisição. "Desativar" e as saídas/entradas listam só
  ativos; "Reativar" lista só inativos. A função do módulo continua validando o valor recebido.
- O CSV usa `;` como separador, UTF-8 com BOM (acentos corretos no Excel), vírgula decimal e
  prefixa com `'` textos que começam com `=`, `+`, `-` ou `@` (evita fórmulas injetadas).
  Só consultas (itens sem `auditoria`) que devolvem lista podem ser exportadas.
- Nas listagens de produtos (e no CSV), a coluna `categoria_id` é trocada pelo **nome** da categoria.

## Segurança

- Sessão assinada: defina `SECRET_KEY` no ambiente (sem ela, uma chave aleatória é criada a cada início).
- Token CSRF em todo POST.
- Perfil conferido no servidor a cada requisição; funcionário desativado perde o acesso na hora.
- Senha nunca é devolvida à página nem gravada na auditoria.
- Cabeçalhos: CSP restritiva (sem script inline), `X-Frame-Options: DENY`, `nosniff`, `no-store`.

## Testes

`tests/test_web.py` usa o `test_client` do Flask (sem navegador), com banco temporário.
Cobre primeiro acesso, login e bloqueio, CSRF, permissões por perfil, o fluxo
cadastro → entrada → saída → relatório e os erros de validação.

## Limitações conhecidas

- O bloqueio de login fica na memória do processo (reinicia junto com o servidor).
- No terminal os IDs ainda são digitados; só o site tem listas de escolha.
- `python -m src.web` usa o servidor de desenvolvimento do Flask: serve para a demonstração,
  não para produção.
