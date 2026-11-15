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
│   ├── web.py
│   ├── templates/
│   └── static/
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

### Interface web (Flask)

```bash
python -m src.web
```

Abra <http://127.0.0.1:5000>. O site usa os mesmos módulos, campos e permissões do menu de terminal (as telas são geradas a partir da tabela `MENUS` de `src/main.py`). Em ambiente real, defina a variável `SECRET_KEY` antes de iniciar; veja `docs/integracao-frontend.md`.

O arquivo `src/banco.py` utiliza SQLite e pode criar `estoque.db` automaticamente na raiz do projeto. Esse banco local não é versionado.

**Atenção:** a execução integral do menu depende da conclusão e compatibilidade dos módulos de autenticação e funcionários. Caso ainda estejam em desenvolvimento, a inicialização/login pode falhar até a integração final.

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

## Funcionalidades previstas

- Cadastro, edição, consulta e desativação de produtos e categorias.
- Registro de entrada e saída com atualização de `estoque_atual` e bloqueio de saldo negativo.
- Histórico de movimentações e relatórios de estoque.
- Gerenciamento de fornecedores.
- Gestão de funcionários, autenticação por perfil e auditoria, sujeitos à integração final.

## Publicação sem arquivos de teste

Para entregar uma distribuição do aplicativo sem a pasta `tests/`, mantendo os testes no GitHub, execute **após commitar a limpeza**:

```powershell
New-Item -ItemType Directory -Force dist | Out-Null
git archive --format=zip --output=dist/gestao-estoque-final.zip HEAD src data README.md requirements.txt
```

Esse ZIP é uma distribuição para execução. Para avaliação de qualidade e testes, use o repositório GitHub completo.
