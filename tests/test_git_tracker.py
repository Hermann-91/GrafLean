"""
Testes unitários para o módulo GitTracker.
"""

import os
import sys
import tempfile
import subprocess
import shutil
import unittest

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from core.git_tracker import GitTracker, GitStatusType


class TestGitTracker(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_non_git_directory_returns_empty_map(self):
        tracker = GitTracker(self.temp_dir)
        self.assertFalse(tracker.is_git_repository())
        self.assertEqual(tracker.get_status_map(), {})

    def test_detects_untracked_and_modified_files(self):
        # Inicializa git no temp_dir
        subprocess.run(["git", "init"], cwd=self.temp_dir, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=self.temp_dir, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=self.temp_dir, capture_output=True)

        tracker = GitTracker(self.temp_dir)
        self.assertTrue(tracker.is_git_repository())

        # Cria arquivo 1 e comita
        f1_path = os.path.join(self.temp_dir, "file1.py")
        with open(f1_path, "w", encoding="utf-8") as f:
            f.write("print('hello')")
        subprocess.run(["git", "add", "file1.py"], cwd=self.temp_dir, capture_output=True)
        subprocess.run(["git", "commit", "-m", "initial"], cwd=self.temp_dir, capture_output=True)

        # Agora cria arquivo novo (untracked)
        f2_path = os.path.join(self.temp_dir, "file2.py")
        with open(f2_path, "w", encoding="utf-8") as f:
            f.write("print('new file')")

        # Modifica arquivo 1
        with open(f1_path, "a", encoding="utf-8") as f:
            f.write("\nprint('modified')")

        status_map = tracker.get_status_map()
        self.assertEqual(status_map.get(f2_path), GitStatusType.NEW)
        self.assertEqual(status_map.get(f1_path), GitStatusType.MODIFIED)

    def test_tree_builder_reflects_git_status(self):
        from core.tree import ProjectTreeBuilder
        subprocess.run(["git", "init"], cwd=self.temp_dir, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=self.temp_dir, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=self.temp_dir, capture_output=True)

        f1_path = os.path.join(self.temp_dir, "tracked.py")
        with open(f1_path, "w") as f:
            f.write("print('1')")
        subprocess.run(["git", "add", "tracked.py"], cwd=self.temp_dir, capture_output=True)
        subprocess.run(["git", "commit", "-m", "init"], cwd=self.temp_dir, capture_output=True)

        # Modifica tracked.py e cria new_by_ai.py
        with open(f1_path, "a") as f:
            f.write("\nprint('2')")
        f2_path = os.path.join(self.temp_dir, "new_by_ai.py")
        with open(f2_path, "w") as f:
            f.write("print('ai')")

        builder = ProjectTreeBuilder(self.temp_dir, {})
        tree = builder.build()
        data = tree.to_dict()

        files_status = {c["name"]: c.get("git_status") for c in data["children"]}
        self.assertEqual(files_status.get("new_by_ai.py"), GitStatusType.NEW)
        self.assertEqual(files_status.get("tracked.py"), GitStatusType.MODIFIED)


if __name__ == "__main__":
    unittest.main()
