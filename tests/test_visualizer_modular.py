"""
Testes unitários isolados para os submódulos do visualizer:
GraphDataSerializer, TemplateEngine e ArchitectureVisualizer.
"""

import os
import json
import tempfile
import unittest
from core.models import Node, Edge, SymbolType, EdgeType
from core.graph import ProjectGraph
from core.analyzer import ArchitectureAnalyzer
from core.visualizer.data_serializer import GraphDataSerializer, SerializedGraphData
from core.visualizer.template_engine import TemplateEngine
from core.visualizer import ArchitectureVisualizer


class TestVisualizerModular(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.root = self.tmp_dir.name
        self.graph = ProjectGraph(self.root)

        # Cria nós para teste
        self.file_node = Node(
            id="file://service.py",
            name="service.py",
            symbol_type=SymbolType.FILE,
            file_path="service.py",
            line=1,
            git_status="modified"
        )
        self.class_node = Node(
            id="AuthService",
            name="AuthService",
            symbol_type=SymbolType.CLASS,
            file_path="service.py",
            line=10,
            docstring="Serviço de autenticação seguro"
        )
        self.method_node = Node(
            id="AuthService::login",
            name="login",
            symbol_type=SymbolType.METHOD,
            file_path="service.py",
            line=20
        )
        self.edge = Edge(
            source_id="AuthService",
            target_id="AuthService::login",
            edge_type=EdgeType.CALLS
        )

        self.graph.nodes = {
            self.file_node.id: self.file_node,
            self.class_node.id: self.class_node,
            self.method_node.id: self.method_node
        }
        self.graph.edges = [self.edge]
        self.graph.analyzer = ArchitectureAnalyzer(
            [self.file_node, self.class_node, self.method_node],
            [self.edge]
        )
        self.graph.analyzer.analyze_all()

    def tearDown(self):
        self.tmp_dir.cleanup()

    def test_safe_json_escapes_html_tags(self):
        serializer = GraphDataSerializer(self.graph)
        payload = {"xss": "<script>alert('pwned')</script>", "comment": "<!-- safe -->"}
        escaped = serializer.safe_json(payload)

        self.assertNotIn("<script>", escaped)
        self.assertNotIn("</script>", escaped)
        self.assertNotIn("<!--", escaped)
        self.assertIn(r"\u003cscript\u003e", escaped)
        self.assertIn(r"\u003c!--", escaped)

    def test_serializer_extracts_hierarchy_levels_and_metrics(self):
        serializer = GraphDataSerializer(self.graph)
        nodes = serializer.serialize_nodes()
        nodes_by_id = {n["id"]: n for n in nodes}

        # Nível 1: Arquivo
        self.assertEqual(nodes_by_id["file://service.py"]["level"], 1)
        self.assertIsNone(nodes_by_id["file://service.py"]["parentId"])
        self.assertEqual(nodes_by_id["file://service.py"]["git"], "modified")

        # Nível 2: Classe
        self.assertEqual(nodes_by_id["AuthService"]["level"], 2)
        self.assertEqual(nodes_by_id["AuthService"]["parentId"], "file://service.py")
        self.assertIn("Serviço de autenticação", nodes_by_id["AuthService"]["doc"])

        # Nível 3: Método
        self.assertEqual(nodes_by_id["AuthService::login"]["level"], 3)
        self.assertEqual(nodes_by_id["AuthService::login"]["parentId"], "AuthService")

    def test_serializer_lazy_loads_first_file_under_limit(self):
        test_file = os.path.join(self.root, "sample.py")
        with open(test_file, "w", encoding="utf-8") as f:
            f.write("print('hello world')")

        self.file_node.file_path = test_file
        serializer = GraphDataSerializer(self.graph)
        sources = serializer.load_initial_sources(max_bytes=1024)

        self.assertIn(test_file, sources)
        self.assertEqual(sources[test_file], "print('hello world')")

    def test_template_engine_caches_and_interpolates(self):
        engine = TemplateEngine()
        data = SerializedGraphData(
            nodes_json='[{"id": "test"}]',
            edges_json='[]',
            tree_json='{}',
            sources_json='{}',
            project_name='UnitProject'
        )

        # Primeira renderização carrega do disco
        html = engine.render(data)
        self.assertIn("UnitProject — GrafLean", html)
        self.assertIn('[{"id": "test"}]', html)
        self.assertIn("vis-network", html)

        # Verifica cache em memória
        self.assertIsNotNone(engine._template)
        self.assertIsNotNone(engine._styles)
        self.assertIsNotNone(engine._scripts)

        # Segunda renderização reutiliza o cache
        html2 = engine.render(data)
        self.assertEqual(html, html2)

    def test_architecture_visualizer_end_to_end(self):
        viz = ArchitectureVisualizer(self.graph)
        out_path = os.path.join(self.root, "arch_map.html")
        result_path = viz.generate_html(out_path)

        self.assertEqual(out_path, result_path)
        self.assertTrue(os.path.exists(out_path))

        with open(out_path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("AuthService", content)
        self.assertIn("vis-network", content)
        self.assertIn("quick-palette-modal", content)
        self.assertIn("find-files-modal", content)


if __name__ == "__main__":
    unittest.main()
