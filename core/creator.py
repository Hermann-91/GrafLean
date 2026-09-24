"""
Módulo de Criação de Pastas e Especificações Markdown para Orquestração de Agentes.
Fornece templates arquiteturais prontos para uso (TASK.md, SPEC.md, CONTEXT.md)
e utilitários seguros para manipulação do sistema de arquivos com proteção contra path traversal.
"""

import os
from typing import Dict, Optional


# Templates padrão orientados a orquestração de agentes autônomos
TEMPLATES: Dict[str, str] = {
    "task": """# 📋 Tarefa do Agente

## 🎯 Objetivo
Descreva o que o agente deve realizar nesta tarefa de forma clara e delimitada.

## 📐 Contexto Arquitetural
- **Módulo / Componente Alvo:** `{target}`
- **Chamadores (Inbound):** {inbound}
- **Dependências (Outbound):** {outbound}

## 🔒 Diretrizes e Restrições Técnicas
- Princípios: Clean Code, SOLID, Arquitetura Limpa.
- Manter 100% dos testes unitários passando.
- Não introduzir acoplamentos circulares.

## ✅ Critérios de Aceite
- [ ] Implementação da funcionalidade / correção.
- [ ] Testes unitários cobrindo cenários de sucesso e borda.
- [ ] Validação do mapa arquitetural no GrafLens.

## 🚀 Passos de Execução Sugeridos
1. Analisar os arquivos afetados e dependências no GrafLens.
2. Escrever testes unitários para a funcionalidade.
3. Implementar as modificações necessárias.
4. Executar os testes e validar no navegador.
""",
    "spec": """# 🏛️ Especificação Arquitetural

## 📌 Visão Geral do Módulo
Resumo das responsabilidades, fronteiras arquiteturais e objetivos deste componente.

## 🧱 Componentes & Interfaces
- Classes e Interfaces Principais:
- Injeção de Dependências e Contratos:

## ⚖️ Métricas Arquiteturais Alvo
- **Acoplamento Aferente (Ca):** Controlado
- **Acoplamento Eferente (Ce):** Mínimo necessário
- **Instabilidade (I = Ce / (Ca + Ce)):** Adequada à camada

## 🛡️ Regras e Invariantes
1. Regra 1: ...
2. Regra 2: ...
""",
    "context": """# 🧠 Contexto Operacional para Agentes

## 📦 Stack do Projeto
- Linguagens: Python, PHP, JavaScript / TypeScript
- Ferramentas: GrafLens, Git

## 🛠️ Comandos Essenciais
- **Testes:** `python3 -m unittest discover -s tests -p "test_*.py" -v`
- **Gerar Mapa:** `graf-lens-map .`
- **Watch Mode:** `graf-lens-watch .`

## 🧭 Diretrizes de Desenvolvimento
- Toda comunicação e comentários em Português (BR).
- Zero dependências externas pesadas (priorizar stdlib).
- Commits atômicos seguindo Conventional Commits.
""",
    "empty": """# 📝 Nova Especificação

Escreva aqui o conteúdo da sua especificação ou notas para os agentes.
"""
}


def is_safe_path(base_dir: str, target_path: str) -> bool:
    """
    Verifica se o caminho de destino está estritamente contido no diretório base,
    prevenindo ataques de Path Traversal (ex: '../../etc/passwd').
    """
    base = os.path.abspath(base_dir)
    target = os.path.abspath(os.path.join(base, target_path))
    return target == base or target.startswith(base + os.sep)


def create_folder(base_dir: str, relative_path: str) -> str:
    """
    Cria uma pasta com segurança dentro do diretório base do projeto.
    Retorna o caminho absoluto da pasta criada.
    """
    if not is_safe_path(base_dir, relative_path):
        raise ValueError(f"Caminho inseguro detectado (Path Traversal): {relative_path}")

    full_path = os.path.abspath(os.path.join(base_dir, relative_path))
    os.makedirs(full_path, exist_ok=True)
    return full_path


def create_file(base_dir: str, relative_path: str, content: str = "") -> str:
    """
    Cria um arquivo vazio (ou com conteúdo customizado) de forma segura.
    Suporta qualquer extensão e não força inserção de texto ou templates.
    """
    if not is_safe_path(base_dir, relative_path):
        raise ValueError(f"Caminho inseguro detectado (Path Traversal): {relative_path}")

    full_path = os.path.abspath(os.path.join(base_dir, relative_path))
    parent_dir = os.path.dirname(full_path)
    os.makedirs(parent_dir, exist_ok=True)

    with open(full_path, "w", encoding="utf-8") as f:
        f.write(content)

    return full_path


def create_markdown_spec(
    base_dir: str,
    relative_path: str,
    template_key: str = "task",
    context_data: Optional[Dict[str, str]] = None,
    custom_content: Optional[str] = None
) -> str:
    """
    Cria um arquivo Markdown (.md) com template para agentes autônomos.
    Retorna o caminho absoluto do arquivo criado.
    """
    if not relative_path.endswith(".md"):
        relative_path = f"{relative_path}.md"

    if not is_safe_path(base_dir, relative_path):
        raise ValueError(f"Caminho inseguro detectado (Path Traversal): {relative_path}")

    full_path = os.path.abspath(os.path.join(base_dir, relative_path))
    parent_dir = os.path.dirname(full_path)
    os.makedirs(parent_dir, exist_ok=True)

    if custom_content is not None:
        content = custom_content
    else:
        template = TEMPLATES.get(template_key.lower(), TEMPLATES["task"])
        data = {
            "target": "Nenhum alvo especificado",
            "inbound": "Nenhum",
            "outbound": "Nenhuma"
        }
        if context_data:
            data.update(context_data)
        try:
            content = template.format(**data)
        except KeyError:
            content = template

    with open(full_path, "w", encoding="utf-8") as f:
        f.write(content)

    return full_path


def rename_resource(base_dir: str, old_relative_path: str, new_name_or_rel_path: str) -> str:
    """
    Renomeia um arquivo ou pasta dentro do diretório base do projeto com segurança.
    Retorna o novo caminho absoluto.
    """
    if not is_safe_path(base_dir, old_relative_path):
        raise ValueError(f"Caminho inseguro detectado (Path Traversal): {old_relative_path}")

    old_full = os.path.abspath(os.path.join(base_dir, old_relative_path))
    if not os.path.exists(old_full):
        raise FileNotFoundError(f"Arquivo ou pasta não encontrado: {old_relative_path}")

    if os.sep not in new_name_or_rel_path and "/" not in new_name_or_rel_path:
        new_full = os.path.join(os.path.dirname(old_full), new_name_or_rel_path)
    else:
        new_full = os.path.abspath(os.path.join(base_dir, new_name_or_rel_path))

    if not is_safe_path(base_dir, os.path.relpath(new_full, base_dir)):
        raise ValueError(f"Novo caminho inseguro detectado: {new_name_or_rel_path}")

    if os.path.exists(new_full):
        raise FileExistsError(f"Já existe um arquivo ou pasta com este nome: {new_name_or_rel_path}")

    os.rename(old_full, new_full)
    return new_full


def delete_resource(base_dir: str, relative_path: str) -> str:
    """
    Exclui um arquivo ou diretório com segurança dentro do projeto.
    Impede a exclusão do diretório raiz.
    Retorna o caminho absoluto do recurso excluído.
    """
    if not relative_path or relative_path.strip() in (".", "/", "\\", ""):
        raise ValueError("Operação bloqueada: não é permitido excluir o diretório raiz do projeto.")

    if not is_safe_path(base_dir, relative_path):
        raise ValueError(f"Caminho inseguro detectado (Path Traversal): {relative_path}")

    full_path = os.path.abspath(os.path.join(base_dir, relative_path))
    if not os.path.exists(full_path):
        raise FileNotFoundError(f"Arquivo ou pasta não encontrado: {relative_path}")

    if os.path.isdir(full_path):
        import shutil
        shutil.rmtree(full_path)
    else:
        os.remove(full_path)

    return full_path


def save_file_content(base_dir: str, file_path: str, content: str) -> str:
    """
    Salva o conteúdo de um arquivo de forma segura, prevenindo Path Traversal.
    Retorna o caminho absoluto do arquivo salvo.
    """
    if os.path.isabs(file_path):
        rel_path = os.path.relpath(file_path, base_dir)
    else:
        rel_path = file_path

    if not is_safe_path(base_dir, rel_path):
        raise ValueError(f"Caminho inseguro detectado (Path Traversal): {file_path}")

    full_path = os.path.abspath(os.path.join(base_dir, rel_path))
    parent = os.path.dirname(full_path)
    os.makedirs(parent, exist_ok=True)

    with open(full_path, "w", encoding="utf-8") as f:
        f.write(content)

    return full_path
