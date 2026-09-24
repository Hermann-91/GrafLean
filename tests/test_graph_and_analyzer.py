"""
Testes automatizados para o ArchitectureAnalyzer e o ProjectGraph.
Valida métricas Ca/Ce, instabilidade, ciclos de dependência e salvamento em arquivo.
"""

import unittest
import os
import tempfile
from core.models import Node, Edge, SymbolType, EdgeType
from core.analyzer import ArchitectureAnalyzer
from core.graph import ProjectGraph


class TestGraphAndAnalyzer(unittest.TestCase):
    def test_analyzer_calculates_coupling_and_instability(self):
        # Nó A chama Nó B
        node_a = Node(id="A", name="A", symbol_type=SymbolType.CLASS, file_path="A.php", line=1)
        node_b = Node(id="B", name="B", symbol_type=SymbolType.CLASS, file_path="B.php", line=1)
        edge = Edge(source_id="A", target_id="B", edge_type=EdgeType.CALLS)

        analyzer = ArchitectureAnalyzer([node_a, node_b], [edge])
        analyzer.analyze_all()

        # Para Nó A: não é chamado por ninguém (Ca=0), depende de B (Ce=1) -> I = 1.0 (Instável)
        self.assertEqual(node_a.metrics.afferent_coupling, 0)
        self.assertEqual(node_a.metrics.efferent_coupling, 1)
        self.assertEqual(node_a.metrics.instability, 1.0)

        # Para Nó B: é chamado por A (Ca=1), não depende de ninguém (Ce=0) -> I = 0.0 (Estável)
        self.assertEqual(node_b.metrics.afferent_coupling, 1)
        self.assertEqual(node_b.metrics.efferent_coupling, 0)
        self.assertEqual(node_b.metrics.instability, 0.0)

    def test_analyzer_detects_circular_dependencies(self):
        # Ciclo: A chama B e B chama A
        node_a = Node(id="A", name="A", symbol_type=SymbolType.CLASS, file_path="A.php", line=1)
        node_b = Node(id="B", name="B", symbol_type=SymbolType.CLASS, file_path="B.php", line=1)
        edge_ab = Edge(source_id="A", target_id="B", edge_type=EdgeType.CALLS)
        edge_ba = Edge(source_id="B", target_id="A", edge_type=EdgeType.CALLS)

        analyzer = ArchitectureAnalyzer([node_a, node_b], [edge_ab, edge_ba])
        analyzer.analyze_all()

        self.assertTrue(node_a.metrics.has_cycles)
        self.assertTrue(node_b.metrics.has_cycles)

    def test_project_graph_save_and_load(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            file_php = os.path.join(tmp_dir, "Service.php")
            with open(file_php, "w", encoding="utf-8") as f:
                f.write("<?php class Service { public function run() {} }")

            graph = ProjectGraph(tmp_dir)
            graph.scan_project()

            json_path = graph.save_to_file()
            self.assertTrue(os.path.exists(json_path))

            # Carrega de volta e busca símbolo em O(1)
            loaded_graph = ProjectGraph.load_from_file(json_path)
            symbol = loaded_graph.find_symbol("Service")
            self.assertIsNotNone(symbol)
            self.assertEqual(symbol.name, "Service")

    def test_symbol_linker_resolves_cross_file_inheritance_and_imports(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            base_py = os.path.join(tmp_dir, "base_extractor.py")
            with open(base_py, "w", encoding="utf-8") as f:
                f.write("class BaseExtractor:\n    def extract(self):\n        pass\n")

            adapter_py = os.path.join(tmp_dir, "adapter.py")
            with open(adapter_py, "w", encoding="utf-8") as f:
                f.write("from base_extractor import BaseExtractor\n\nclass CustomAdapter(BaseExtractor):\n    def extract(self):\n        pass\n")

            graph = ProjectGraph(tmp_dir)
            graph.scan_project()

            # Procura a aresta de herança entre CustomAdapter e BaseExtractor
            inherits_edges = [
                e for e in graph.edges
                if e.edge_type == EdgeType.INHERITS
            ]
            self.assertTrue(len(inherits_edges) > 0)
            target_node_id = inherits_edges[0].target_id
            self.assertIn("base_extractor.py::BaseExtractor", target_node_id)
            self.assertIn(target_node_id, graph.nodes)


if __name__ == "__main__":
    unittest.main()
