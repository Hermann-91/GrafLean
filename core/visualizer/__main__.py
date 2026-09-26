"""
Ponto de entrada CLI para python -m core.visualizer
"""

import sys
from core.graph import ProjectGraph
from core.visualizer import ArchitectureVisualizer

if __name__ == "__main__":
    target_dir = sys.argv[1] if len(sys.argv) > 1 else "."
    g = ProjectGraph(target_dir)
    g.scan_project()
    g.save_to_file()
    viz = ArchitectureVisualizer(g)
    path = viz.generate_html()
    print(f"Mapa visual gerado com sucesso em: {path}")
