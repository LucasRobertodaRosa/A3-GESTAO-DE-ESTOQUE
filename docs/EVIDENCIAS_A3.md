# Evidências da entrega — A3 Gestão de Estoque

> Atualizado em 16/11/2026 a partir do plano da A3, do relatório *Análise do projeto A3 e plano até 29/11* (15/11/2026) e dos registros públicos do repositório. Links de commits/PRs comprovam que o material foi versionado, mas não substituem a confirmação de autoria individual pelo Git nem os resultados de execução.

## Versão do projeto

- Projeto: [A3-GESTAO-DE-ESTOQUE](https://github.com/LucasRobertodaRosa/A3-GESTAO-DE-ESTOQUE)
- Versão publicada: [`v1.0.0`](https://github.com/LucasRobertodaRosa/A3-GESTAO-DE-ESTOQUE/releases/tag/v1.0.0)
- Commit da versão publicada: [`a006ab4`](https://github.com/LucasRobertodaRosa/A3-GESTAO-DE-ESTOQUE/commit/a006ab4)
- PR de integração `develop` → `main`: [#40 — Release v1.0.0](https://github.com/LucasRobertodaRosa/A3-GESTAO-DE-ESTOQUE/pull/40), integrado em 15/11/2026
- Commit/branch usados na *homologação final do grupo*: `main` em [`5ed896d`](https://github.com/LucasRobertodaRosa/A3-GESTAO-DE-ESTOQUE/commit/5ed896db71075e1868447e698edd90bddd5c1bed) (`5ed896db71075e1868447e698edd90bddd5c1bed`), conferido em 27/11/2026

## Resultado da homologação local (27/11/2026)

Execução local na revisão `5ed896d`, Windows 11, Python 3.15.2:

| Comando | Resultado |
| --- | --- |
| `python -m pytest tests/` | **307 testes aprovados** (mais 125 subtestes), 0 falhas |
| `python -m coverage report` | **87% de cobertura total** (1556 instruções, 204 não cobertas) |
| `python -m ruff check .` | `All checks passed!` |

Cobertura por módulo:

| Módulo | Cobertura |
| --- | --- |
| `banco.py`, `categorias.py`, `produtos.py` | 100% |
| `fornecedores.py`, `funcionarios.py` | 98% |
| `autenticacao.py`, `web.py` | 97% |
| `movimentacoes.py` | 96% |
| `relatorios.py` | 91% |
| `auditoria.py` | 71% |
| `main.py` (menu de terminal) | 52% |

Todas as issues do repositório (incluindo as abertas pelo professor: #1, #14 e #41) estão fechadas.

## Qualidade e integração contínua

| Verificação | Evidência verificável | Situação |
| --- | --- | --- |
| GitHub Actions | [Backend CI #6, versão v1.0.0](https://github.com/LucasRobertodaRosa/A3-GESTAO-DE-ESTOQUE/actions/runs/43677846616) e [Backend CI #7, main](https://github.com/LucasRobertodaRosa/A3-GESTAO-DE-ESTOQUE/actions/runs/43678536545) | Ambas as execuções aparecem como concluídas com sucesso no GitHub |
| Testes automatizados | `python -m pytest tests/ -v`; [configuração da CI](https://github.com/LucasRobertodaRosa/A3-GESTAO-DE-ESTOQUE/blob/main/.github/workflows/backend-ci.yml) | **307 testes aprovados** na revisão `5ed896d` (ver homologação local acima) |
| Cobertura mínima de 75% | A CI executa `python -m coverage report -m --fail-under=75` | **87%** pelo `coverage.py` na revisão `5ed896d` |
| Ruff | A CI executa `python -m ruff check .` | Sem apontamentos (`All checks passed!`) |
| SonarCloud / Quality Gate | Etapa `Analise SonarCloud e Quality Gate` da CI, configurada em `sonar-project.properties`; envia `coverage.xml` e espera o resultado do Quality Gate (`sonar.qualitygate.wait=true`) | **Pendente:** inserir o link do painel e o status do Quality Gate após a primeira análise. Registrar os apontamentos iniciais (segurança, confiabilidade, manutenibilidade, duplicações e complexidade) e as correções na seção abaixo |

## Análise estática no SonarCloud — antes e depois do Quality Gate

Painel do projeto: **inserir link** (ex.: `https://sonarcloud.io/project/overview?id=LucasRobertodaRosa_A3-GESTAO-DE-ESTOQUE`)

| Medida | Primeira análise (antes) | Após correções (depois) | Correções aplicadas (commits) |
| --- | --- | --- | --- |
| Segurança (Security) | preencher | preencher | preencher |
| Confiabilidade (Reliability) | preencher | preencher | preencher |
| Manutenibilidade (Maintainability) | preencher | preencher | preencher |
| Duplicações | preencher | preencher | preencher |
| Complexidade (ciclomática/cognitiva) | preencher | preencher | preencher |
| Cobertura | preencher | preencher | — |
| **Quality Gate** | preencher | **Passed** (meta) | — |

Guarde um print da primeira análise antes de corrigir os apontamentos: ele é a evidência do "antes" exigida no item 2.12 e no slide de evolução do software.

**Observação:** o documento de análise datado de 15/11 estima 236 testes e aproximadamente 85% de cobertura com ferramentas substitutas em sandbox; esses valores **não são o resultado oficial do `pytest`/`coverage.py`** e por isso não foram registrados como medições finais.

## Rastreabilidade por integrante

| Pessoa / aluno | Módulo e funcionalidade atribuída | PRs / commits publicamente identificados | Testes relacionados no repositório | O que a evidência comprova / validação restante |
| --- | --- | --- | --- | --- |
| **Pessoa 1 — Rafael da Silva Gutubir** | Produtos e categorias: cadastrar, editar, buscar, filtrar e desativar; apoio à interface Flask e visual | [PR #3 — categorias](https://github.com/LucasRobertodaRosa/A3-GESTAO-DE-ESTOQUE/pull/3), [PR #6 — produtos](https://github.com/LucasRobertodaRosa/A3-GESTAO-DE-ESTOQUE/pull/6), [PR #17 — testes](https://github.com/LucasRobertodaRosa/A3-GESTAO-DE-ESTOQUE/pull/17), [PR #28 — integração com menu](https://github.com/LucasRobertodaRosa/A3-GESTAO-DE-ESTOQUE/pull/28), [PR #38 — interface Flask](https://github.com/LucasRobertodaRosa/A3-GESTAO-DE-ESTOQUE/pull/38), [PR #39 — visual](https://github.com/LucasRobertodaRosa/A3-GESTAO-DE-ESTOQUE/pull/39) | [`test_produtos.py`](https://github.com/LucasRobertodaRosa/A3-GESTAO-DE-ESTOQUE/blob/main/tests/test_produtos.py), [`test_categorias.py`](https://github.com/LucasRobertodaRosa/A3-GESTAO-DE-ESTOQUE/blob/main/tests/test_categorias.py), [`test_web.py`](https://github.com/LucasRobertodaRosa/A3-GESTAO-DE-ESTOQUE/blob/main/tests/test_web.py) | PRs mostram a entrega e a integração dos módulos. Executar testes para comprovar funcionamento; verificar autoria de cada commit no próprio Git. |
| **Pessoa 2 — Lucas Roberto da Rosa** | Entradas e saídas; atualização transacional do saldo, bloqueio de saldo insuficiente, histórico e testes | [PR #8 — movimentações](https://github.com/LucasRobertodaRosa/A3-GESTAO-DE-ESTOQUE/pull/8), commits [`901054d`](https://github.com/LucasRobertodaRosa/A3-GESTAO-DE-ESTOQUE/commit/901054d), [`388d03f`](https://github.com/LucasRobertodaRosa/A3-GESTAO-DE-ESTOQUE/commit/388d03f), [`31a169b`](https://github.com/LucasRobertodaRosa/A3-GESTAO-DE-ESTOQUE/commit/31a169b), [`446a5a1`](https://github.com/LucasRobertodaRosa/A3-GESTAO-DE-ESTOQUE/commit/446a5a1), [`66ace92`](https://github.com/LucasRobertodaRosa/A3-GESTAO-DE-ESTOQUE/commit/66ace92), [`5b68d26`](https://github.com/LucasRobertodaRosa/A3-GESTAO-DE-ESTOQUE/commit/5b68d26); integração adicional [PR #35](https://github.com/LucasRobertodaRosa/A3-GESTAO-DE-ESTOQUE/pull/35) | [`test_movimentacoes.py`](https://github.com/LucasRobertodaRosa/A3-GESTAO-DE-ESTOQUE/blob/main/tests/test_movimentacoes.py), [`test_fluxo_backend.py`](https://github.com/LucasRobertodaRosa/A3-GESTAO-DE-ESTOQUE/blob/main/tests/test_fluxo_backend.py), [`test_web.py`](https://github.com/LucasRobertodaRosa/A3-GESTAO-DE-ESTOQUE/blob/main/tests/test_web.py) | Commits demonstram entrada, saída, validação, histórico e testes. Parte deles guarda **Author = `unknown`** no Git; isso não apaga a evidência do PR. Confirmar vínculo dos e-mails à conta GitHub sem reescrever o histórico. |
| **Pessoa 3 — Nizio Antônio Martins de Araujo Filho** | Relatórios de estoque atual, estoque baixo/zerado, movimentações, indicadores | [PR #18 — relatórios](https://github.com/LucasRobertodaRosa/A3-GESTAO-DE-ESTOQUE/pull/18), commits [`ec9b8e2`](https://github.com/LucasRobertodaRosa/A3-GESTAO-DE-ESTOQUE/commit/ec9b8e2), [`f25f0ab`](https://github.com/LucasRobertodaRosa/A3-GESTAO-DE-ESTOQUE/commit/f25f0ab), [`50de782`](https://github.com/LucasRobertodaRosa/A3-GESTAO-DE-ESTOQUE/commit/50de782), [`ebd8a2f`](https://github.com/LucasRobertodaRosa/A3-GESTAO-DE-ESTOQUE/commit/ebd8a2f), [`6a581aa`](https://github.com/LucasRobertodaRosa/A3-GESTAO-DE-ESTOQUE/commit/6a581aa) | [`test_relatorios.py`](https://github.com/LucasRobertodaRosa/A3-GESTAO-DE-ESTOQUE/blob/main/tests/test_relatorios.py) | O PR inclui quatro implementações de relatórios e o commit específico de testes. Confirmar resultados dos testes da versão final. |
| **Pessoa 4 — Heitor José Basso** | Funcionários, primeiro acesso, autenticação bcrypt, login e controle de perfis | [PR #33 — autenticação e funcionários](https://github.com/LucasRobertodaRosa/A3-GESTAO-DE-ESTOQUE/pull/33), commits [`b78dd29`](https://github.com/LucasRobertodaRosa/A3-GESTAO-DE-ESTOQUE/commit/b78dd29), [`fc505f4`](https://github.com/LucasRobertodaRosa/A3-GESTAO-DE-ESTOQUE/commit/fc505f4), [`04867c3`](https://github.com/LucasRobertodaRosa/A3-GESTAO-DE-ESTOQUE/commit/04867c3) | [`test_funcionarios.py`](https://github.com/LucasRobertodaRosa/A3-GESTAO-DE-ESTOQUE/blob/main/tests/test_funcionarios.py), [`test_autenticacao.py`](https://github.com/LucasRobertodaRosa/A3-GESTAO-DE-ESTOQUE/blob/main/tests/test_autenticacao.py), [`test_fluxo_login.py`](https://github.com/LucasRobertodaRosa/A3-GESTAO-DE-ESTOQUE/blob/main/tests/test_fluxo_login.py) | PR #33 comprova que o **módulo** entrou na `develop`; ele foi aberto/integrado por outra conta. A atribuição individual de autoria a Heitor deve ser comprovada com os commits pessoais `HeitorJB` (o relatório de 15/11 relata aproximadamente cinco), ou por evidência complementar validada pela equipe. |
| **Pessoa 5 — Diogo Augusto Cassimiro Rocha** | Banco SQLite, fornecedores, auditoria e integração dos módulos | [PR #12 — banco e fornecedores](https://github.com/LucasRobertodaRosa/A3-GESTAO-DE-ESTOQUE/pull/12) por `DigoGiant`; integração de equipe em [PR #40 — release final](https://github.com/LucasRobertodaRosa/A3-GESTAO-DE-ESTOQUE/pull/40) **não constitui prova de autoria individual de Diogo** | [`test_fornecedores.py`](https://github.com/LucasRobertodaRosa/A3-GESTAO-DE-ESTOQUE/blob/main/tests/test_fornecedores.py), [`test_fluxo_backend.py`](https://github.com/LucasRobertodaRosa/A3-GESTAO-DE-ESTOQUE/blob/main/tests/test_fluxo_backend.py), testes relacionados à auditoria e banco | PR #12 comprova sua contribuição ao banco/fornecedores. Os commits pessoais de auditoria/integração precisam ser conferidos no Git antes de atribuir sua autoria. |

### Interpretação correta da autoria

- **Responsável pelo módulo**: atribuição do plano da A3.
- **Autor do commit**: campos `Author`/`Committer` gravados pelo Git, consultáveis por hash.
- **Criador ou responsável pelo merge de PR**: pode ser diferente do autor de parte ou de todos os commits. **Não usar o merge como prova de autoria individual sem conferir.**
- A conta `unknown` identificada em commits da Pessoa 2 refere-se ao **nome gravado no histórico**; o e-mail pode ser associado ao GitHub. Preservar os hashes; não fazer `push --force` apenas para trocar nomes.

## Fluxo manual em banco de teste — anexar prints reais

| Teste | Resultado esperado | Situação documental |
| --- | --- | --- |
| Primeiro acesso / criação do ADMIN | Usuário criado, senha armazenada com hash bcrypt | **[Vídeo](https://drive.google.com/file/d/1LSKsu6uuUdFI5U8uuAcgmVXlCDD7OjcC/view?usp=sharing)** |
| Login correto / senha incorreta | Acesso autorizado / recusado | **[Vídeo](https://drive.google.com/file/d/1LSKsu6uuUdFI5U8uuAcgmVXlCDD7OjcC/view?usp=sharing)** |
| Criar categoria e produto | Produto válido cadastrado com categoria existente | **[Vídeo](https://drive.google.com/file/d/1LSKsu6uuUdFI5U8uuAcgmVXlCDD7OjcC/view?usp=sharing)** |
| Entrada 15, saída 3, tentativa de saída 20 | Saldo final 12; operação acima do saldo recusada | **[Vídeo](https://drive.google.com/file/d/1LSKsu6uuUdFI5U8uuAcgmVXlCDD7OjcC/view?usp=sharing)** |
| Histórico | Apenas as duas movimentações válidas | **[Vídeo](https://drive.google.com/file/d/1LSKsu6uuUdFI5U8uuAcgmVXlCDD7OjcC/view?usp=sharing)** |
| Relatórios / auditoria | Saldo coerente; ações vinculadas ao funcionário | **[Vídeo](https://drive.google.com/file/d/1LSKsu6uuUdFI5U8uuAcgmVXlCDD7OjcC/view?usp=sharing)** |
| Perfil CONSULTA | Sem permissão de escrita | **[Vídeo](https://drive.google.com/file/d/1LSKsu6uuUdFI5U8uuAcgmVXlCDD7OjcC/view?usp=sharing)** |

> Não incluir credenciais reais, senhas, tokens ou dados pessoais em capturas.

## Decisões técnicas

- **SQLite**: simplicidade da execução acadêmica local; chaves estrangeiras e transações preservam integridade.
- **bcrypt**: armazenamento de senhas com hash, não em texto puro.
- **Movimentações**: saldo e histórico alterados em transação; saídas acima do saldo bloqueadas.
- **Interfaces**: terminal Python e frontend web Flask; testes em `tests/`.
- **Qualidade**: CI com pytest, `coverage.py` e Ruff. A exigência mínima de cobertura é 75%.
- **Rastreabilidade**: links acima devem permanecer associados à versão homologada; novos resultados devem indicar o commit testado.

## Verificações para concluir esta evidência

1. Em `main` (ou na referência final aprovada), registrar `git rev-parse HEAD` e data da homologação.
2. Copiar o número de testes, percentual oficial de cobertura e saída do Ruff dos logs locais/CI **da mesma revisão**.
3. Inserir links de prints e/ou arquivos de evidências do fluxo manual.
4. Conferir com Heitor e Diogo os hashes dos commits de autoria individual para completar a rastreabilidade, sem assumir autoria pelo título do PR.
5. Se o SonarCloud for realmente obrigatório segundo a orientação do professor, inserir o link para o Quality Gate da versão final, após aprovação.


## Procedimento de conferência final para preenchimento (antes de publicar)

> Esta seção complementa o conteúdo já preenchido acima; não substitui a tabela de rastreabilidade.

### 1. Fixar uma versão única do projeto

No terminal do VS Code, na branch da revisão a ser documentada:

```powershell
git fetch origin
git branch --show-current
git rev-parse HEAD
git status
```

Registre o SHA completo e a data na seção **Versão do projeto**. Não misture resultados de versões diferentes do código. Para a release já registrada acima, use os links existentes da `v1.0.0`; se a turma homologou uma revisão posterior, informe também o novo commit.

### 2. Obter contagem verdadeira de testes e cobertura

```powershell
python -m pytest tests/ -v
python -m coverage erase
python -m coverage run --source=src -m pytest tests/
python -m coverage report -m --fail-under=75
python -m ruff check .
```

Copie o **resumo efetivo** do pytest, o **TOTAL** da cobertura e o resultado do Ruff. Mantenha um link da execução equivalente do GitHub Actions. Se for usada uma execução local, informe sistema operacional e versão do Python (com `python --version`).

### 3. Confirmar os commits pessoais sem confundir autor com quem integrou o PR

```powershell
git shortlog -sne origin/develop
git log origin/develop --format="%h | %an <%ae> | %s" -- src/movimentacoes.py tests/test_movimentacoes.py
git show -s --format="%H%nAutor: %an <%ae>%nCommitter: %cn <%ce>%nMensagem: %s" HASH_REAL
```

Substitua `HASH_REAL` por um hash real. O nome `unknown` gravado nos commits da Pessoa 2 é um dado histórico: não declarar o autor como outra pessoa sem checar o e-mail e o vínculo com o GitHub. Para Heitor e Diogo, validar individualmente os commits de seu módulo antes de afirmar autoria pessoal; a autoria do PR/merge não é prova suficiente.

### 4. Inserir evidências manuais verificáveis

Organize capturas ou vídeos sem dados sensíveis em `docs/evidencias/`, ou vincule um local acessível à equipe. Sempre relacione cada imagem ao teste que comprova, por exemplo:

| Evidência | Caso | Comprovação esperada | Arquivo ou URL |
| --- | --- | --- | --- |
| EV-01 | Primeiro acesso e autenticação | ADMIN criado e login válido; senha nunca visível | **[EV-01](https://drive.google.com/file/d/1xiQd3VKMMh0PbDrJIIUQDe22XBcqLIor/view?usp=sharing)** |
| EV-02 | Cadastro de categoria e produto | Produto vinculado à categoria existente | **[EV-02](https://drive.google.com/file/d/1hTHxIJ0M1u-WAuOB-h_6SNAzuqruQJgO/view?usp=sharing)** |
| EV-03 | Movimentação de estoque | Entrada 15, saída 3, tentativa de saída 20 bloqueada | **[EV-03](https://drive.google.com/file/d/1k9lpdpQlkXO7g6D8cN2MFjDLtGBB2ln5/view?usp=sharing)** |
| EV-04 | Saldo e histórico | Saldo final 12 e somente 2 movimentações válidas | **[EV-04](https://drive.google.com/file/d/1AZneZewZKJ7USvfpKIZu7t430NA02_Sf/view?usp=sharing)** |
| EV-05 | Relatórios | Totais consistentes com o saldo e as movimentações | **[EV-05](https://drive.google.com/file/d/1s6zKZPrc-aa2A8YFbK-6jP68YRToD42E/view?usp=sharing)** |
| EV-06 | Permissões e auditoria | Perfil CONSULTA bloqueado e ação atribuída ao responsável | **[EV-06](https://drive.google.com/file/d/1C6miBpxEGixRt70U9EJnHd5GrL7Xaent/view?usp=sharing)** |

### 5. Rastreabilidade da avaliação

Para cada linha da tabela de integrantes acima, conferir: (a) função do plano de A3; (b) arquivo implementado; (c) PR ou commit real; (d) teste relacionado; (e) resultado do teste na versão homologada. A existência de um teste ou de um PR comprova material versionado, mas **não**, por si só, que a pessoa indicada seja a autora de todas as linhas nem que o teste tenha sido aprovado em qualquer revisão.

### 6. Revisão de publicação

- [ ] Nenhum dado de teste está inventado ou copiado de estimativa sem indicação.
- [ ] O percentual oficial é do `coverage.py` e está ligado à revisão homologada.
- [ ] Links de PRs e commits abrem corretamente.
- [ ] Autoria dos commits atribuída por registros do Git, não apenas pelo responsável pelo merge.
- [ ] Capturas comprovam o fluxo de ponta a ponta e não expõem senhas.
- [ ] Quality Gate do SonarCloud tem link e status real, caso seja obrigatório na A3.
- [ ] Documento foi commitado em branch própria e passou por revisão do grupo.
