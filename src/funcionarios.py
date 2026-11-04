
# src/funcionarios.py

funcionarios = []
proximo_id = 1


def cadastrar_funcionario(nome, cargo, salario):
    """Cadastra um novo funcionário."""
    global proximo_id

    if not nome or not cargo:
        print("Erro: nome e cargo são obrigatórios.")
        return None

    try:
        salario = float(salario)
        if salario < 0:
            print("Erro: o salário não pode ser negativo.")
            return None
    except (ValueError, TypeError):
        print("Erro: informe um salário válido.")
        return None

    funcionario = {
        "id": proximo_id,
        "nome": nome,
        "cargo": cargo,
        "salario": salario,
        "ativo": True
    }

    funcionarios.append(funcionario)
    proximo_id += 1

    print("Funcionário cadastrado com sucesso!")
    return funcionario


def listar_funcionarios():
    """Lista todos os funcionários cadastrados."""
    if not funcionarios:
        print("Nenhum funcionário cadastrado.")
        return []

    for funcionario in funcionarios:
        status = "Ativo" if funcionario["ativo"] else "Inativo"

        print(
            f'ID: {funcionario["id"]} | '
            f'Nome: {funcionario["nome"]} | '
            f'Cargo: {funcionario["cargo"]} | '
            f'Salário: R$ {funcionario["salario"]:.2f} | '
            f'Status: {status}'
        )

    return funcionarios.copy()


def editar_funcionario(id_funcionario, nome=None,
                       cargo=None, salario=None):
    """Edita os dados de um funcionário."""
    for funcionario in funcionarios:
        if funcionario["id"] == id_funcionario:
            if nome is not None and nome.strip():
                funcionario["nome"] = nome

            if cargo is not None and cargo.strip():
                funcionario["cargo"] = cargo

            if salario is not None:
                try:
                    novo_salario = float(salario)
                    if novo_salario < 0:
                        print("Erro: salário negativo.")
                        return False
                    funcionario["salario"] = novo_salario
                except (ValueError, TypeError):
                    print("Erro: informe um salário válido.")
                    return False

            print("Funcionário editado com sucesso!")
            return True

    print("Funcionário não encontrado.")
    return False


def desativar_funcionario(id_funcionario):
    """Desativa um funcionário sem excluí-lo do cadastro."""
    for funcionario in funcionarios:
        if funcionario["id"] == id_funcionario:
            if not funcionario["ativo"]:
                print("Este funcionário já está desativado.")
                return False

            funcionario["ativo"] = False
            print("Funcionário desativado com sucesso!")
            return True

    print("Funcionário não encontrado.")
    return False


if __name__ == "__main__":
    # Exemplo de utilização
    cadastrar_funcionario("Ana Silva", "Analista", 3500)
    cadastrar_funcionario("João Souza", "Desenvolvedor", 5000)

    print("\n--- Lista de funcionários ---")
    listar_funcionarios()

    print("\n--- Editando funcionário ---")
    editar_funcionario(1, cargo="Analista Sênior", salario=4000)

    print("\n--- Desativando funcionário ---")
    desativar_funcionario(2)

    print("\n--- Lista atualizada ---")
    listar_funcionarios()
