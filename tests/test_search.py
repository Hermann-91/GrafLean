"""
Testes automatizados para a funcionalidade de Busca Global de Conteúdo (Find in Files).
Valida o método search_project_content e os elementos do frontend no visualizador.
"""

import unittest
import os
import tempfile
from core.models import Node, SymbolType
from core.graph import ProjectGraph
from core.analyzer import ArchitectureAnalyzer
from core.library import ProjectMetadata, LibraryManager
from core.hub_server import ProjectSession
from core.visualizer import ArchitectureVisualizer


class TestSearchContent(unittest.TestCase):
    def test_search_project_content_finds_occurrences(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            src_dir = os.path.join(tmp_dir, "app", "Services")
            os.makedirs(src_dir, exist_ok=True)
            auth_file = os.path.join(src_dir, "AuthService.php")
            with open(auth_file, "w", encoding="utf-8") as f:
                f.write("<?php\nnamespace App\\Services;\nclass AuthService {\n    public function verifyToken($token) {\n        return true;\n    }\n}\n")

            meta = ProjectMetadata(id="test_proj", name="TestProj", path=tmp_dir)
            lib_manager = LibraryManager(base_dir=os.path.join(tmp_dir, ".graflean_test"))
            session = ProjectSession(meta, lib_manager)

            # Busca insensível a maiúsculas
            results = session.search_project_content("verifytoken", case_sensitive=False)
            self.assertEqual(len(results), 1)
            self.assertEqual(results[0]["file"], "app/Services/AuthService.php")
            self.assertEqual(results[0]["line"], 4)
            self.assertIn("verifyToken", results[0]["snippet"])

            # Busca sensível a maiúsculas que deve falhar se digitado em minúsculas
            results_case = session.search_project_content("verifytoken", case_sensitive=True)
            self.assertEqual(len(results_case), 0)

            # Busca sensível com grafia correta
            results_case_ok = session.search_project_content("verifyToken", case_sensitive=True)
            self.assertEqual(len(results_case_ok), 1)

    def test_search_ignores_vendor_and_git_directories(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            vendor_dir = os.path.join(tmp_dir, "vendor", "package")
            os.makedirs(vendor_dir, exist_ok=True)
            with open(os.path.join(vendor_dir, "VendorClass.php"), "w", encoding="utf-8") as f:
                f.write("<?php class VendorClass { function secretTarget() {} }")

            app_dir = os.path.join(tmp_dir, "app")
            os.makedirs(app_dir, exist_ok=True)
            with open(os.path.join(app_dir, "AppClass.php"), "w", encoding="utf-8") as f:
                f.write("<?php class AppClass { function secretTarget() {} }")

            meta = ProjectMetadata(id="test_proj", name="TestProj", path=tmp_dir)
            lib_manager = LibraryManager(base_dir=os.path.join(tmp_dir, ".graflean_test"))
            session = ProjectSession(meta, lib_manager)

            results = session.search_project_content("secretTarget")
            self.assertEqual(len(results), 1)
            self.assertEqual(results[0]["file"], "app/AppClass.php")

    def test_visualizer_contains_find_in_files_modal_and_shortcuts(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            graph = ProjectGraph(tmp_dir)
            node_file = Node(id="file://index.php", name="index.php", symbol_type=SymbolType.FILE, file_path="index.php", line=1)
            graph.nodes = {"file://index.php": node_file}
            graph.edges = []
            graph.analyzer = ArchitectureAnalyzer([node_file], [])
            graph.analyzer.analyze_all()

            viz = ArchitectureVisualizer(graph)
            out_file = os.path.join(tmp_dir, "map.html")
            path = viz.generate_html(out_file)

            with open(path, "r", encoding="utf-8") as f:
                content = f.read()

            self.assertIn("find-files-backdrop", content)
            self.assertIn("find-files-input", content)
            self.assertIn("openFindInFiles", content)
            self.assertIn("closeFindInFiles", content)
            self.assertIn("btn-find-in-files", content)
            self.assertIn("executeFindInFiles", content)


if __name__ == "__main__":
    unittest.main()
