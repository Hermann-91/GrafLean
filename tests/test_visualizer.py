"""
Testes automatizados para o ArchitectureVisualizer.
Valida a geração do mapa HTML interativo.
"""

import unittest
import os
import tempfile
from core.models import Node, Edge, SymbolType, EdgeType
from core.analyzer import ArchitectureAnalyzer
from core.graph import ProjectGraph
from core.visualizer import ArchitectureVisualizer


class TestArchitectureVisualizer(unittest.TestCase):
    def test_generates_html_with_nodes_and_edges(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            graph = ProjectGraph(tmp_dir)
            node_a = Node(id="A", name="ClassA", symbol_type=SymbolType.CLASS, file_path="A.php", line=1)
            node_b = Node(id="B", name="ClassB", symbol_type=SymbolType.CLASS, file_path="B.php", line=1)
            edge = Edge(source_id="A", target_id="B", edge_type=EdgeType.CALLS)

            graph.nodes = {"A": node_a, "B": node_b}
            graph.edges = [edge]
            graph.analyzer = ArchitectureAnalyzer([node_a, node_b], [edge])
            graph.analyzer.analyze_all()

            viz = ArchitectureVisualizer(graph)
            out_file = os.path.join(tmp_dir, "map.html")
            path = viz.generate_html(out_file)

            self.assertTrue(os.path.exists(path))
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()

            self.assertIn("ClassA", content)
            self.assertIn("ClassB", content)
            self.assertIn("vis-network", content)
            self.assertIn("GrafLean", content)
            self.assertIn("tree-context-menu", content)
            self.assertIn("openTreeContextMenu", content)
            self.assertIn("copyAgentPrompt", content)

    def test_generates_html_with_git_status_tags(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            graph = ProjectGraph(tmp_dir)
            node_new = Node(id="N", name="NewModule", symbol_type=SymbolType.FILE, file_path="New.py", line=1, git_status="new")
            node_mod = Node(id="M", name="ModModule", symbol_type=SymbolType.FILE, file_path="Mod.py", line=1, git_status="modified")

            graph.nodes = {"N": node_new, "M": node_mod}
            graph.edges = []
            graph.analyzer = ArchitectureAnalyzer([node_new, node_mod], [])
            graph.analyzer.analyze_all()

            viz = ArchitectureVisualizer(graph)
            out_file = os.path.join(tmp_dir, "map.html")
            path = viz.generate_html(out_file)

            with open(path, "r", encoding="utf-8") as f:
                content = f.read()

            self.assertIn('"git": "new"', content)
            self.assertIn('"git": "modified"', content)
            self.assertIn("git-badge-new", content)
            self.assertIn("git-badge-mod", content)


if __name__ == "__main__":
    unittest.main()
