"""
Módulo de Árvore Estrutural do Projeto (Project Tree).
Aplica os Padrões de Projeto:
- Composite Pattern (GoF): Trata diretórios e arquivos de forma uniforme.
- Builder Pattern (GoF): Constrói a hierarquia a partir do grafo plano de nós.
"""

import os
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from core.models import Node, SymbolType


class FileSystemComponent(ABC):
    """Componente base abstrato do padrão Composite."""

    def __init__(self, name: str, relative_path: str):
        self.name = name
        self.relative_path = relative_path

    @abstractmethod
    def to_dict(self) -> Dict[str, Any]:
        """Serializa o componente para JSON consumível pelo front-end."""
        pass


class FileLeaf(FileSystemComponent):
    """Representa a folha (arquivo) no padrão Composite."""

    def __init__(self, name: str, relative_path: str, full_id: str, git_status: Optional[str] = None):
        super().__init__(name, relative_path)
        self.full_id = full_id
        self.git_status = git_status
        self.symbols: List[Dict[str, Any]] = []

    def add_symbol(self, node: Node):
        self.symbols.append({
            "id": node.id,
            "name": node.name,
            "type": node.symbol_type.value,
            "line": node.line,
            "ca": node.metrics.afferent_coupling,
            "ce": node.metrics.efferent_coupling,
            "instability": node.metrics.instability
        })

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "file",
            "name": self.name,
            "relative_path": self.relative_path,
            "full_id": self.full_id,
            "git_status": self.git_status,
            "symbols": sorted(self.symbols, key=lambda s: s["line"])
        }


class DirectoryNode(FileSystemComponent):
    """Representa o nó composto (diretório) no padrão Composite."""

    def __init__(self, name: str, relative_path: str):
        super().__init__(name, relative_path)
        self.children: Dict[str, FileSystemComponent] = {}

    def get_or_create_dir(self, name: str, rel_path: str) -> "DirectoryNode":
        if name not in self.children:
            self.children[name] = DirectoryNode(name, rel_path)
        return self.children[name]  # type: ignore

    def add_file(self, file_leaf: FileLeaf):
        self.children[file_leaf.name] = file_leaf

    def to_dict(self) -> Dict[str, Any]:
        # Ordena: primeiro diretórios, depois arquivos
        dirs = []
        files = []
        for child in self.children.values():
            if isinstance(child, DirectoryNode):
                dirs.append(child.to_dict())
            else:
                files.append(child.to_dict())

        dirs.sort(key=lambda d: d["name"].lower())
        files.sort(key=lambda f: f["name"].lower())

        return {
            "type": "directory",
            "name": self.name,
            "relative_path": self.relative_path,
            "children": dirs + files
        }


class ProjectTreeBuilder:
    """Builder responsável por converter os nós planos do ProjectGraph em uma árvore Composite."""

    def __init__(self, root_dir: str, nodes: Dict[str, Node]):
        self.root_dir = os.path.abspath(root_dir)
        self.nodes = nodes

    def build(self) -> DirectoryNode:
        root_name = os.path.basename(self.root_dir) or "root"
        root = DirectoryNode(root_name, "")

        # 1. Descobre todos os diretórios e arquivos reais no disco (inclusive .idea, .docs, .env, etc.)
        ignored_dirs = {".git", ".svn", ".hg", "__pycache__", "node_modules", "vendor", ".venv", "venv"}
        ignored_files = {"arch_map.html", ".arch_graph.json"}
        files_map: Dict[str, FileLeaf] = {}

        try:
            from core.git_tracker import GitTracker
            git_tracker = GitTracker(self.root_dir)
            git_status_map = git_tracker.get_status_map()
        except Exception:
            git_status_map = {}

        if os.path.exists(self.root_dir):
            for root_path, dirs, files in os.walk(self.root_dir):
                dirs[:] = [d for d in dirs if d not in ignored_dirs]
                rel_dir = os.path.relpath(root_path, self.root_dir)
                if rel_dir != ".":
                    parts = rel_dir.split(os.sep)
                    curr = root
                    curr_p = ""
                    for part in parts:
                        curr_p = os.path.join(curr_p, part) if curr_p else part
                        curr = curr.get_or_create_dir(part, curr_p)

                for f in files:
                    if f in ignored_files:
                        continue
                    full_f = os.path.join(root_path, f)
                    rel_f = os.path.relpath(full_f, self.root_dir)
                    f_git = git_status_map.get(full_f, "")
                    files_map[rel_f] = FileLeaf(f, rel_f, f"file://{full_f}", git_status=f_git)

        # 2. Agrupa nós de símbolos por arquivo e atualiza status git
        for node in self.nodes.values():
            if node.file_path in git_status_map:
                node.git_status = git_status_map[node.file_path]
            rel_file = os.path.relpath(node.file_path, self.root_dir)
            if rel_file not in files_map:
                file_id = f"file://{node.file_path}"
                file_name = os.path.basename(node.file_path)
                files_map[rel_file] = FileLeaf(file_name, rel_file, file_id, git_status=node.git_status)
            elif node.git_status and not files_map[rel_file].git_status:
                files_map[rel_file].git_status = node.git_status

            if node.symbol_type != SymbolType.FILE:
                files_map[rel_file].add_symbol(node)

        # 2. Constrói a hierarquia de pastas
        for rel_file, file_leaf in files_map.items():
            parts = rel_file.split(os.sep)
            current_dir = root
            current_path = ""

            # Navega/cria pastas intermediárias
            for part in parts[:-1]:
                current_path = os.path.join(current_path, part) if current_path else part
                current_dir = current_dir.get_or_create_dir(part, current_path)

            current_dir.add_file(file_leaf)

        self.files_map = files_map
        return root
