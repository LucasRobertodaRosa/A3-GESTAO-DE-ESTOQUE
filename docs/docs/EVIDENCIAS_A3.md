# Evidências da entrega — A3 Gestão de Estoque

> Preencher com os resultados reais. Não afirmar aprovação antes da execução.

## Versão do projeto
- Data:
- Commit de `develop` homologado:
- PR de `develop` para `main`:
- Commit final em `main`:

## Qualidade
- Comando: `python -m pytest tests/ -v`
- Testes coletados / passaram / falharam:
- Link do GitHub Actions:
- Comando: `python -m coverage report -m --fail-under=75`
- Percentual real de cobertura:
- Comando: `python -m ruff check .`
- Resultado:

## Fluxo manual em banco de teste (sem tocar estoque.db real)
- Primeiro acesso / ADMIN: (print ou vídeo)
- Login correto e login incorreto: (print)
- Categoria e produto: (print)
- Entrada 15 / saída 3 / tentativa de saída 20: (print)
- Saldo final 12 e histórico com 2 movimentos: (print)
- Relatórios e auditoria: (print)
- Usuário CONSULTA sem permissão para escrita: (print)

## Rastreabilidade por integrante
| Pessoa | Módulo | PR / commits | Testes | Evidência |
|---|---|---|---|---|
| Pessoa 1 | Produtos e categorias | PREENCHER | PREENCHER | PREENCHER |
| Pessoa 2 | Movimentações | PREENCHER | PREENCHER | PREENCHER |
| Pessoa 3 | Relatórios | PREENCHER | PREENCHER | PREENCHER |
| Pessoa 4 | Login e funcionários | PREENCHER | PREENCHER | PREENCHER |
| Pessoa 5 | Banco, fornecedores, auditoria e integração | PREENCHER | PREENCHER | PREENCHER |

## Decisões técnicas
- SQLite: simplicidade para uso local, chaves estrangeiras ativadas.
- Senhas: bcrypt, sem persistência em texto puro.
- Movimentações: atualização de saldo e lançamento do histórico em uma transação.
- Frontend: contrato disponível em `docs/integracao-frontend.md`.
- Limitações atuais: informar claramente itens ainda não disponíveis.
