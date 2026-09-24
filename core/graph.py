"""
Orquestrador do Grafo do Projeto (ProjectGraph).
Varre o projeto, extrai nós e arestas via ParserRegistry, executa o analisador e salva em cache.
"""

import os
import sys

# Garante importação do core tanto como pacote quanto script
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

import json
from typing import Dict, List, Optional
from core.models import Node, Edge, SymbolType
from core.parsers.registry import ParserRegistry
from core.analyzer import ArchitectureAnalyzer


class ProjectGraph:
    IGNORED_DIRS = {
        ".git", "vendor", "node_modules", ".venv", "venv",
        "__pycache__", "storage", ".idea", ".vscode", "dist", "build"
    }
    IGNORED_FILES = {"arch_map.html", ".arch_graph.json"}

    def __init__(self, root_dir: str):
        self.root_dir = os.path.abspath(root_dir)
        self.registry = ParserRegistry()
        self.nodes: Dict[str, Node] = {}
        self.edges: List[Edge] = []
        self.analyzer: Optional[ArchitectureAnalyzer] = None

    def scan_project(self):
        """Escaneia recursivamente todos os arquivos suportados no projeto."""
        all_nodes: List[Node] = []
        all_edges: List[Edge] = []

        for root, dirs, files in os.walk(self.root_dir):
            dirs[:] = [d for d in dirs if d not in self.IGNORED_DIRS]

            for file in files:
                if file in self.IGNORED_FILES:
                    continue
                full_path = os.path.join(root, file)
                parser = self.registry.get_parser_for_file(full_path)
                if parser:
                    result = parser.parse_file(full_path)
                    all_nodes.extend(result.nodes)
                    all_edges.extend(result.edges)

        # Rastreia status Git dos arquivos do projeto (< 5ms)
        from core.git_tracker import GitTracker
        git_tracker = GitTracker(self.root_dir)
        git_status_map = git_tracker.get_status_map()

        # Indexa nós por ID (evitando duplicatas)
        self.nodes = {}
        for node in all_nodes:
            if node.file_path in git_status_map:
                node.git_status = git_status_map[node.file_path]
            self.nodes[node.id] = node
        self.edges = self._link_and_resolve_edges(all_edges)

        # Executa a análise arquitetural
        self.analyzer = ArchitectureAnalyzer(list(self.nodes.values()), self.edges)
        self.analyzer.analyze_all()

    def _link_and_resolve_edges(self, raw_edges: List[Edge]) -> List[Edge]:
        """Resolve arestas que apontam para nomes curtos ou imports para os IDs canônicos."""
        # 1. Monta tabela de lookup de símbolos para os nós reais
        symbol_to_id: Dict[str, str] = {}
        for node_id, node in self.nodes.items():
            # Mapeia ID completo
            symbol_to_id[node_id] = node_id
            # Mapeia nome curto (ex: "BasePlatformExtractor", "Order")
            if node.name not in symbol_to_id or node.symbol_type in (SymbolType.CLASS, SymbolType.INTERFACE):
                symbol_to_id[node.name] = node_id

            # Mapeia caminho relativo e variações (ex: "app.models.order", "core/base_extractor.py::BasePlatformExtractor")
            rel_file = os.path.relpath(node.file_path, self.root_dir)
            rel_module = rel_file.replace("/", ".").replace("\\", ".")
            for ext in [".py", ".php", ".ts", ".js", ".blade.php"]:
                if rel_module.endswith(ext):
                    rel_module = rel_module[:-len(ext)]
                    break
            symbol_to_id[f"{rel_module}.{node.name}"] = node_id
            symbol_to_id[f"{rel_file}::{node.name}"] = node_id
            symbol_to_id[rel_file] = f"file://{node.file_path}"
            symbol_to_id[node.file_path] = f"file://{node.file_path}"

        resolved_edges: List[Edge] = []
        for edge in raw_edges:
            target = edge.target_id

            # Caso A: Alvo já é um ID canônico de nó existente
            if target in self.nodes:
                resolved_edges.append(edge)
                continue

            # Caso B: Alvo mapeado no lookup
            if target in symbol_to_id:
                edge.target_id = symbol_to_id[target]
                resolved_edges.append(edge)
                continue

            # Caso C: Tenta pelo último segmento (ex: "module.submodule.ClassName" -> "ClassName")
            short_target = target.split(".")[-1].split("::")[-1]
            if short_target in symbol_to_id:
                edge.target_id = symbol_to_id[short_target]
                resolved_edges.append(edge)
                continue

            # Caso D: Se for uma importação de arquivo (ex: "core.base_extractor"), tenta achar o arquivo
            matched = False
            for node_id, node in self.nodes.items():
                if node.symbol_type == SymbolType.FILE:
                    if target.replace(".", "/") in node.file_path or target in node.file_path:
                        edge.target_id = node_id
                        resolved_edges.append(edge)
                        matched = True
                        break
            if matched:
                continue

        return resolved_edges

    def save_to_file(self, output_path: Optional[str] = None) -> str:
        """Salva o grafo em formato JSON otimizado para leitura instantânea."""
        if not output_path:
            output_path = os.path.join(self.root_dir, ".arch_graph.json")

        data = {
            "root_dir": self.root_dir,
            "nodes": {n_id: n.to_dict() for n_id, n in self.nodes.items()},
            "edges": [e.to_dict() for e in self.edges]
        }

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        return output_path

    @classmethod
    def load_from_file(cls, graph_path: str) -> "ProjectGraph":
        """Carrega o grafo do disco para a memória em menos de 10ms."""
        with open(graph_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        graph = cls(data.get("root_dir", "."))
        nodes_dict = {}
        for n_id, n_data in data.get("nodes", {}).items():
            node = Node.from_dict(n_data)
            nodes_dict[n_id] = node
        graph.nodes = nodes_dict

        edges_list = [Edge.from_dict(e_data) for e_data in data.get("edges", [])]
        graph.edges = edges_list
        graph.analyzer = ArchitectureAnalyzer(list(graph.nodes.values()), graph.edges)

        return graph

    def find_symbol(self, symbol_name: str, file_path: Optional[str] = None) -> Optional[Node]:
        """Busca em O(1) pelo símbolo (para atender ao orçamento de latência do Sublime)."""
        # 1. Busca exata por FQCN ou ID
        if symbol_name in self.nodes:
            return self.nodes[symbol_name]

        # 2. Busca por nome simples contextualizado ao arquivo
        if file_path:
            qualified = f"{file_path}::{symbol_name}"
            if qualified in self.nodes:
                return self.nodes[qualified]

        # 3. Busca por nome simples global
        for node in self.nodes.values():
            if node.name == symbol_name:
                return node

        return None


if __name__ == "__main__":
    target_dir = sys.argv[1] if len(sys.argv) > 1 else "."
    print(f"🔍 Escaneando arquitetura em: {target_dir}")
    g = ProjectGraph(target_dir)
    g.scan_project()
    saved_path = g.save_to_file()
    print(f"✅ Grafo salvo em: {saved_path}")
    print(f"📊 Estatísticas: {len(g.nodes)} nós, {len(g.edges)} conexões mapeadas.")
