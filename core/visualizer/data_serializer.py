"""
Módulo de Serialização e Sanitização de Dados do Grafo.
Responsável por converter o estado estrutural do ProjectGraph em representações
JSON estritamente sanitizadas para consumo pelo frontend.
"""

import os
import json
from dataclasses import dataclass
from typing import Dict, List, Any, Optional
from core.graph import ProjectGraph
from core.tree import ProjectTreeBuilder


@dataclass(frozen=True)
class SerializedGraphData:
    """Contrato imutável de dados do grafo preparados para renderização."""
    nodes_json: str
    edges_json: str
    tree_json: str
    sources_json: str
    project_name: str


class GraphDataSerializer:
    """Extrai e sanitiza os dados estruturais do grafo para renderização."""

    def __init__(self, graph: ProjectGraph):
        self.graph = graph

    @staticmethod
    def safe_json(data: Any) -> str:
        """
        Escapa '<' e '>' como unicode '\\u003c' e '\\u003e' em conformidade com RFC 8259
        impedindo que tags HTML (ex: </script>, <!--) interfiram no parser do navegador.
        """
        return json.dumps(data, ensure_ascii=False).replace("<", "\\u003c").replace(">", "\\u003e")

    def serialize_nodes(self) -> List[Dict[str, Any]]:
        """Processa nós, métricas arquiteturais, níveis e tooltips."""
        nodes_data = []
        for node in self.graph.nodes.values():
            m = node.metrics
            doc_text = f"💡 {node.docstring}" if node.docstring else "Sem descrição."
            tooltip = f"🏷️ {node.name} ({node.symbol_type.value.upper()})\n{doc_text}"

            # Níveis: 1 = arquivo, 2 = classe/interface/trait, 3 = métodos/funções
            level = 1 if node.symbol_type.value == "file" else (
                2 if node.symbol_type.value in ("class", "interface", "trait") else 3
            )
            parent_id = None
            if level == 2:
                parent_id = f"file://{node.file_path}"
            elif level == 3:
                parent_id = node.id.rsplit("::", 1)[0] if "::" in node.id else f"file://{node.file_path}"

            nodes_data.append({
                "id": node.id,
                "label": node.name,
                "title": tooltip,
                "type": node.symbol_type.value,
                "file": node.file_path,
                "line": node.line,
                "doc": node.docstring or "",
                "ca": m.afferent_coupling,
                "ce": m.efferent_coupling,
                "instability": m.instability,
                "deep": m.is_deep_module,
                "cycle": m.has_cycles,
                "git": node.git_status or "",
                "level": level,
                "parentId": parent_id
            })
        return nodes_data

    def serialize_edges(self) -> List[Dict[str, Any]]:
        """Processa arestas e seus tipos de relacionamento."""
        edges_data = []
        for edge in self.graph.edges:
            edges_data.append({
                "source": edge.source_id,
                "target": edge.target_id,
                "type": edge.edge_type.value,
                "desc": edge.description or ""
            })
        return edges_data

    def serialize_tree(self) -> Dict[str, Any]:
        """Gera a árvore composta de arquivos e diretórios do projeto."""
        tree_builder = ProjectTreeBuilder(self.graph.root_dir, self.graph.nodes)
        return tree_builder.build().to_dict()

    def load_initial_sources(self, max_bytes: int = 500 * 1024) -> Dict[str, str]:
        """Carrega sob demanda o código do primeiro arquivo focal (limite de 500 KB)."""
        file_sources = {}
        first_file = next(
            (node.file_path for node in self.graph.nodes.values() if node.file_path and os.path.isfile(node.file_path)),
            None
        )
        if first_file and os.path.getsize(first_file) <= max_bytes:
            try:
                with open(first_file, "r", encoding="utf-8", errors="replace") as f:
                    file_sources[first_file] = f.read()
            except Exception:
                pass
        return file_sources

    def serialize_all(self) -> SerializedGraphData:
        """Executa a serialização completa e retorna o container de dados sanitizados."""
        nodes_data = self.serialize_nodes()
        edges_data = self.serialize_edges()
        tree_data = self.serialize_tree()
        file_sources = self.load_initial_sources()

        project_name = os.path.basename(os.path.abspath(self.graph.root_dir)) or "GrafLean"

        return SerializedGraphData(
            nodes_json=self.safe_json(nodes_data),
            edges_json=self.safe_json(edges_data),
            tree_json=self.safe_json(tree_data),
            sources_json=self.safe_json(file_sources),
            project_name=project_name
        )
