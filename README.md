# A3 — Sistema de Gestão de Estoque

Trabalho acadêmico de Gestão da Qualidade de Software. Sistema em Python, com armazenamento em SQLite, controle de produtos, categorias, fornecedores e movimentações de estoque, além de relatórios e módulos de gestão de funcionários, autenticação e auditoria.

## Integrantes

- Lucas Roberto da Rosa — Entradas, saídas e controle de estoque (Pessoa 2)
- Heitor José Basso — Funcionários, login e permissões (Pessoa 4)
- Nizio Antônio Martins de Araujo Filho — Relatórios (Pessoa 3)
- Rafael da Silva Gutubir — Produtos e categorias (Pessoa 1)
- Diogo Augusto Cassimiro Rocha — Banco, fornecedores, auditoria e integração (Pessoa 5)

## Estrutura

```text
A3-GESTAO-DE-ESTOQUE/
├── src/
│   ├── __init__.py
│   ├── main.py
│   ├── banco.py
│   ├── produtos.py
│   ├── categorias.py
│   ├── movimentacoes.py
│   ├── fornecedores.py
│   ├── funcionarios.py
│   ├── autenticacao.py
│   ├── relatorios.py
│   ├── auditoria.py
├── tests/
│   └── test_*.py
├── data/
├── requirements.txt
├── .gitignore
└── README.md
```

A árvore lista os módulos previstos/encontrados no repositório; algumas implementações ainda podem estar pendentes de integração.

## Requisitos

- Python 3.11 ou superior (recomenda-se uma versão suportada pelas dependências instaladas).
- Git e terminal PowerShell, Bash ou equivalente.

## Instalação

Clone o repositório e entre na pasta:

```bash
git clone https://github.com/LucasRobertodaRosa/A3-GESTAO-DE-ESTOQUE.git
cd A3-GESTAO-DE-ESTOQUE
```

Crie um ambiente virtual:

```bash
python -m venv .venv
```

No Windows (PowerShell), ative-o com:

```powershell
.\.venv\Scripts\Activate.ps1
```

No macOS/Linux, utilize:

```bash
source .venv/bin/activate
```

Instale as dependências:

```bash
python -m pip install -r requirements.txt
```

## Executar

Execute na raiz do projeto:

```bash
python -m src.main
```

O arquivo `src/banco.py` utiliza SQLite e pode criar `estoque.db` automaticamente na raiz do projeto. Esse banco local não é versionado.


## Observações de execução

O sistema oferece interface de terminal e interface web Flask.

A aplicação utiliza o mesmo banco SQLite para persistir
os dados, respeitando as regras de negócio e as permissões
implementadas no backend.

Para executar os testes, recomenda-se utilizar um ambiente
isolado e um banco de teste, sem alterar os dados da aplicação.

Para acesso web em ambientes diferentes do uso local,
é necessário configurar uma SECRET_KEY segura e revisar
as condições de implantação e segurança do servidor.


## Testes

A pasta `tests/` contém testes-fonte Python (`test_*.py`) que fazem parte da comprovação de qualidade e devem permanecer no GitHub.

Execute todos os testes:

```bash
python -m pytest tests/ -v
```

Para executar só os testes de movimentações:

```bash
python -m pytest tests/test_movimentacoes.py -v
```

Para medir cobertura (meta acadêmica: pelo menos 75%):

```bash
python -m coverage run --source=src -m pytest tests/
python -m coverage report -m --fail-under=75
```

Para verificar o código com Ruff:

```bash
python -m ruff check .
```

Caches como `__pycache__/`, arquivos `.pyc`, `.pytest_cache/`, relatórios `.coverage` e bancos locais são descartáveis e ficam fora do versionamento.


## Qualidade e integração contínua

O projeto utiliza:

- Pytest para testes automatizados.
- Coverage.py para medição de cobertura.
- Ruff para análise estática.
- GitHub Actions para integração contínua.

A cobertura mínima exigida no projeto é de 75%.

### Executar os testes

```bash
python -m pytest tests/ -v
```

### Medir a cobertura

```bash
python -m coverage run --source=src -m pytest tests/
python -m coverage report -m --fail-under=75
```

### Executar o Ruff

```bash
python -m ruff check .
```

O workflow de integração contínua está em
`.github/workflows/backend-ci.yml`.

As informações de homologação estão em
`docs/EVIDENCIAS_A3.md`.

## Licença

O projeto está disponibilizado sob os termos descritos
no arquivo LICENSE.


## Testes e qualidade do backend

Instale as dependências:

```bash
python -m pip install -r requirements.txt
```

Execute os testes:

```bash
python -m pytest tests/ -v
```

Verifique a cobertura:

```bash
python -m coverage run --source=src -m pytest tests/
python -m coverage report -m --fail-under=75
```

Execute a análise estática:

```bash
python -m ruff check .
```

A validação automática é executada pelo workflow
`.github/workflows/backend-ci.yml` nos Pull Requests
e atualizações das branches `develop` e `main`.

As evidências da entrega estão em `docs/EVIDENCIAS_A3.md`.



## Funcionalidades implementadas

O Sistema de Gestão de Estoque foi desenvolvido em Python,
com banco de dados SQLite e interface web Flask.

### Produtos e categorias
- Cadastro e consulta de categorias.
- Cadastro, edição, busca e desativação de produtos.
- Validação de código, preço e estoque mínimo.

### Movimentações de estoque
- Registro de entradas de produtos.
- Registro de saídas de produtos.
- Atualização automática do estoque disponível.
- Bloqueio de saída com saldo insuficiente.
- Histórico de movimentações.

### Fornecedores
- Cadastro e consulta de fornecedores.
- Associação de fornecedores às entradas de estoque.

### Funcionários e autenticação
- Cadastro e gerenciamento de funcionários.
- Autenticação de usuários com bcrypt.
- Controle de acesso por perfil.
- Perfis ADMIN, ESTOQUISTA e CONSULTA.

### Relatórios
- Relatório de estoque atual.
- Identificação de produtos com estoque baixo ou zerado.
- Histórico de entradas e saídas.
- Indicadores gerais do estoque.

### Auditoria
- Registro de operações relevantes do sistema.
- Identificação de ações realizadas pelos funcionários.

### Interface
- Menu de terminal em Python.
- Interface web desenvolvida com Flask.
- Formulários e tabelas para gerenciamento do estoque.


## Publicação sem arquivos de teste

Para entregar uma distribuição do aplicativo sem a pasta `tests/`, mantendo os testes no GitHub, execute **após commitar a limpeza**:

```powershell
New-Item -ItemType Directory -Force dist | Out-Null
git archive --format=zip --output=dist/gestao-estoque-final.zip HEAD src data README.md requirements.txt
```

Esse ZIP é uma distribuição para execução. Para avaliação de qualidade e testes, use o repositório GitHub completo.
