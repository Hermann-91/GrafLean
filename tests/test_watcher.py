"""
Testes unitários para o módulo ArchitectureWatcher (Watch Mode).
"""

import os
import sys
import time
import tempfile
import unittest

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from core.watcher import ArchitectureWatcher


class TestArchitectureWatcher(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.file1 = os.path.join(self.temp_dir, "test.php")
        with open(self.file1, "w", encoding="utf-8") as f:
            f.write("<?php class TestWatcher {}")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_get_tracked_files(self):
        watcher = ArchitectureWatcher(self.temp_dir, port=9999)
        tracked = watcher.get_tracked_files()
        self.assertIn(self.file1, tracked)

    def test_has_changes_detection(self):
        watcher = ArchitectureWatcher(self.temp_dir, port=9999)
        watcher.file_snapshots = watcher.get_tracked_files()
        self.assertFalse(watcher.has_changes(watcher.file_snapshots))

        time.sleep(0.05)
        with open(self.file1, "a", encoding="utf-8") as f:
            f.write("\n// novo comentario")
        
        current = watcher.get_tracked_files()
        self.assertTrue(watcher.has_changes(current))

    def test_build_initial_generates_html_and_json(self):
        watcher = ArchitectureWatcher(self.temp_dir, port=9999)
        duration = watcher.build_initial()
        self.assertGreater(duration, 0)
        self.assertTrue(os.path.exists(os.path.join(self.temp_dir, "arch_map.html")))
        self.assertTrue(os.path.exists(os.path.join(self.temp_dir, ".arch_graph.json")))


if __name__ == "__main__":
    unittest.main()
