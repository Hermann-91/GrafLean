"""
Módulo de Visualização Global Interativa (Mapa Arquitetural).
Orquestra a serialização dos dados estruturais do grafo e a montagem do HTML autocontido.
"""

import os
import sys
from typing import Optional

# Garante compatibilidade de importação
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(os.path.dirname(current_dir))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from core.graph import ProjectGraph
from core.visualizer.data_serializer import GraphDataSerializer
from core.visualizer.template_engine import TemplateEngine


class ArchitectureVisualizer:
    """Orquestrador do mapa visual arquitetural interativo."""

    def __init__(self, graph: ProjectGraph, template_engine: Optional[TemplateEngine] = None):
        self.graph = graph
        self.serializer = GraphDataSerializer(graph)
        self.template_engine = template_engine or TemplateEngine()

    def generate_html(self, output_path: Optional[str] = None) -> str:
        """Gera e grava em disco o arquivo HTML autocontido."""
        if not output_path:
            output_path = os.path.join(self.graph.root_dir, "arch_map.html")
        html_content = self.render_html()
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        return output_path

    def render_html(self) -> str:
        """Serializa o estado do grafo e renderiza a representação HTML."""
        data = self.serializer.serialize_all()
        return self.template_engine.render(data)


if __name__ == "__main__":
    target_dir = sys.argv[1] if len(sys.argv) > 1 else "."
    g = ProjectGraph(target_dir)
    g.scan_project()
    g.save_to_file()
    viz = ArchitectureVisualizer(g)
    path = viz.generate_html()
    print(f"Mapa visual gerado com sucesso em: {path}")
