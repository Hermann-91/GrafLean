"""
Testes automatizados para a árvore de projeto (Composite Pattern).
"""

import unittest
from core.models import Node, SymbolType
from core.tree import DirectoryNode, FileLeaf, ProjectTreeBuilder


class TestProjectTree(unittest.TestCase):
    def test_composite_structure(self):
        root = DirectoryNode("my_project", "")
        src_dir = root.get_or_create_dir("src", "src")
        file_leaf = FileLeaf("index.py", "src/index.py", "file:///tmp/src/index.py")

        fn_node = Node(
            id="file:///tmp/src/index.py::main",
            name="main",
            symbol_type=SymbolType.FUNCTION,
            file_path="/tmp/src/index.py",
            line=10
        )
        file_leaf.add_symbol(fn_node)
        src_dir.add_file(file_leaf)

        data = root.to_dict()
        self.assertEqual(data["type"], "directory")
        self.assertEqual(len(data["children"]), 1)
        self.assertEqual(data["children"][0]["name"], "src")
        self.assertEqual(data["children"][0]["children"][0]["name"], "index.py")
        self.assertEqual(len(data["children"][0]["children"][0]["symbols"]), 1)

    def test_builder_constructs_from_nodes(self):
        nodes = {
            "f1": Node(id="f1", name="app.py", symbol_type=SymbolType.FILE, file_path="/root/src/app.py", line=1),
            "c1": Node(id="c1", name="App", symbol_type=SymbolType.CLASS, file_path="/root/src/app.py", line=5)
        }
        builder = ProjectTreeBuilder("/root", nodes)
        tree = builder.build()
        data = tree.to_dict()

        self.assertEqual(data["type"], "directory")
        self.assertEqual(data["children"][0]["name"], "src")
        self.assertEqual(data["children"][0]["name"], "app.py") if len(data["children"][0]["children"]) == 0 else self.assertEqual(data["children"][0]["children"][0]["name"], "app.py")

    def test_builder_includes_config_dirs_and_dotfiles(self):
        import tempfile, os
        with tempfile.TemporaryDirectory() as tmp_dir:
            # Cria .idea, .env, .git
            os.makedirs(os.path.join(tmp_dir, ".idea"), exist_ok=True)
            with open(os.path.join(tmp_dir, ".idea", "workspace.xml"), "w") as f:
                f.write("<xml></xml>")
            with open(os.path.join(tmp_dir, ".env"), "w") as f:
                f.write("KEY=VAL")
            os.makedirs(os.path.join(tmp_dir, ".git"), exist_ok=True)
            with open(os.path.join(tmp_dir, ".git", "config"), "w") as f:
                f.write("git-config")

            builder = ProjectTreeBuilder(tmp_dir, {})
            tree = builder.build()
            data = tree.to_dict()

            child_names = [c["name"] for c in data["children"]]
            self.assertIn(".idea", child_names)
            self.assertIn(".env", child_names)
            self.assertNotIn(".git", child_names)


if __name__ == "__main__":
    unittest.main()
