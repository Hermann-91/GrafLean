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
    def test_generates_html_with_hierarchy_levels_and_toolbar(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            graph = ProjectGraph(tmp_dir)
            file_node = Node(id="file://mod.py", name="mod.py", symbol_type=SymbolType.FILE, file_path="mod.py", line=1)
            class_node = Node(id="ClassA", name="ClassA", symbol_type=SymbolType.CLASS, file_path="mod.py", line=5)
            method_node = Node(id="ClassA::foo", name="foo", symbol_type=SymbolType.METHOD, file_path="mod.py", line=10)

            graph.nodes = {"file://mod.py": file_node, "ClassA": class_node, "ClassA::foo": method_node}
            graph.edges = []
            graph.analyzer = ArchitectureAnalyzer([file_node, class_node, method_node], [])
            graph.analyzer.analyze_all()

            viz = ArchitectureVisualizer(graph)
            out_file = os.path.join(tmp_dir, "map.html")
            path = viz.generate_html(out_file)

            with open(path, "r", encoding="utf-8") as f:
                content = f.read()

            self.assertIn("graph-toolbar", content)
            self.assertIn("barnesHut", content)
            self.assertIn("code-collapsed", content)
            self.assertIn("btn-toggle-graph", content)
            self.assertIn("btn-collapse-stage", content)
            self.assertIn("sidebar-reopen-btn", content)
            self.assertIn("handleStageCollapse", content)
            self.assertIn("toggleGraphPanel", content)
            self.assertIn("toggleCodeSubpanel", content)
            self.assertIn("nav-top-header", content)
            self.assertIn("btn-hub-link", content)
            self.assertIn("btn-nav-reopen-code", content)
            self.assertIn("btn-nav-reopen-graph", content)
            self.assertIn("btn-toggle-live", content)
            self.assertIn("btn-shutdown-server", content)
            self.assertIn("toggleLiveWatch", content)
            self.assertIn("btn-collapse-tree", content)
            self.assertIn("btn-find-in-files-tree", content)
            self.assertIn("collapseAllFolders", content)
            self.assertIn("🏛️", content)
            self.assertIn('"level": 1', content)
            self.assertIn('"level": 2', content)
            self.assertIn('"level": 3', content)

    def test_generates_html_with_quick_palette_and_sublime_oled_theme(self):
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

            self.assertIn("quick-palette-backdrop", content)
            self.assertIn("quick-palette-input", content)
            self.assertIn("openQuickPalette", content)
            self.assertIn("btn-quick-open", content)
            self.assertIn("CodeMirror", content)
            self.assertIn("sublime-table", content)
            self.assertIn("#000000", content)

    def test_generates_html_with_multiple_editor_tabs_and_keybindings(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            graph = ProjectGraph(tmp_dir)
            node_file = Node(id="file://User.php", name="User.php", symbol_type=SymbolType.FILE, file_path="User.php", line=1)
            graph.nodes = {"file://User.php": node_file}
            graph.edges = []
            graph.analyzer = ArchitectureAnalyzer([node_file], [])
            graph.analyzer.analyze_all()

            viz = ArchitectureVisualizer(graph)
            out_file = os.path.join(tmp_dir, "map.html")
            path = viz.generate_html(out_file)

            with open(path, "r", encoding="utf-8") as f:
                content = f.read()

            self.assertIn("sublime-tabs-track", content)
            self.assertIn("sublime-tab-item", content)
            self.assertIn("openEditorTab", content)
            self.assertIn("closeEditorTab", content)
            self.assertIn("switchEditorTab", content)
            self.assertIn("cycleNextTab", content)
            self.assertIn("renderEditorTabs", content)
            self.assertIn("openEditorTabs", content)
            self.assertIn("previewTabPath", content)
            self.assertIn("pinEditorTab", content)
            self.assertIn("is-preview", content)


if __name__ == "__main__":
    unittest.main()

