"""
Testes Automatizados para o LibraryManager e Acelerador de IA (Fase 1 do Hub PWA).
"""

import os
import shutil
import tempfile
import unittest

from core.models import ProjectMetadata
from core.graph import ProjectGraph
from core.library import LibraryManager


class TestLibraryManager(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="graflean_lib_test_")
        self.base_dir = os.path.join(self.test_dir, ".graflean")
        self.project_path = os.path.join(self.test_dir, "meu_projeto")
        os.makedirs(self.project_path, exist_ok=True)
        self.manager = LibraryManager(base_dir=self.base_dir)

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_initialization(self):
        """Verifica criação automática do diretório base e do config.json."""
        self.assertTrue(os.path.isdir(self.base_dir))
        self.assertTrue(os.path.isdir(os.path.join(self.base_dir, "library")))
        self.assertTrue(os.path.isfile(os.path.join(self.base_dir, "config.json")))
        self.assertEqual(len(self.manager.list_projects()), 0)

    def test_register_project_with_ai_accelerator(self):
        """Registra projeto no modo Acelerador de IA e valida .gitignore e .graflean/."""
        meta = self.manager.register_project(self.project_path, ai_accelerator=True)
        self.assertIsInstance(meta, ProjectMetadata)
        self.assertEqual(meta.path, os.path.abspath(self.project_path))
        self.assertTrue(meta.ai_accelerator)

        # Verifica cache na biblioteca
        cache_dir = self.manager.get_project_cache_dir(meta.id)
        self.assertTrue(os.path.isdir(cache_dir))

        # Verifica pasta local .graflean/
        local_graflean = os.path.join(self.project_path, ".graflean")
        self.assertTrue(os.path.isdir(local_graflean))

        # Verifica .gitignore gerado
        gitignore_path = os.path.join(self.project_path, ".gitignore")
        self.assertTrue(os.path.isfile(gitignore_path))
        with open(gitignore_path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn(".graflean/", content)

    def test_register_project_zero_footprint(self):
        """Registra projeto no modo Zero-Footprint (ai_accelerator=False) sem tocar no repo."""
        meta = self.manager.register_project(self.project_path, ai_accelerator=False)
        self.assertFalse(meta.ai_accelerator)

        local_graflean = os.path.join(self.project_path, ".graflean")
        self.assertFalse(os.path.exists(local_graflean))

        gitignore_path = os.path.join(self.project_path, ".gitignore")
        self.assertFalse(os.path.exists(gitignore_path))

    def test_register_nonexistent_directory_raises(self):
        """Garante que cadastrar pasta inexistente lança FileNotFoundError."""
        with self.assertRaises(FileNotFoundError):
            self.manager.register_project(os.path.join(self.test_dir, "pasta_fantasma"))

    def test_sync_project_gitignore_idempotent(self):
        """Garante que a entrada .graflean/ não é duplicada no .gitignore existente."""
        gitignore_path = os.path.join(self.project_path, ".gitignore")
        with open(gitignore_path, "w", encoding="utf-8") as f:
            f.write("node_modules/\nvendor/\n")

        self.manager.sync_project_gitignore(self.project_path)
        self.manager.sync_project_gitignore(self.project_path)

        with open(gitignore_path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertEqual(content.count(".graflean/"), 1)
        self.assertIn("node_modules/", content)

    def test_toggle_ai_accelerator(self):
        """Alterna o acelerador de IA entre desabilitado e habilitado."""
        meta = self.manager.register_project(self.project_path, ai_accelerator=False)
        self.assertFalse(meta.ai_accelerator)

        self.manager.toggle_ai_accelerator(meta.id, enable=True)
        updated = self.manager.get_project(meta.id)
        self.assertTrue(updated.ai_accelerator)
        self.assertTrue(os.path.isdir(os.path.join(self.project_path, ".graflean")))

    def test_remove_project(self):
        """Remove projeto, expurgando cache e pasta .graflean local."""
        meta = self.manager.register_project(self.project_path, ai_accelerator=True)
        cache_dir = self.manager.get_project_cache_dir(meta.id)
        local_graflean = os.path.join(self.project_path, ".graflean")

        self.assertTrue(os.path.isdir(cache_dir))
        self.assertTrue(os.path.isdir(local_graflean))

        removed = self.manager.remove_project(meta.id, purge_local_folder=True)
        self.assertTrue(removed)
        self.assertIsNone(self.manager.get_project(meta.id))
        self.assertFalse(os.path.exists(cache_dir))
        self.assertFalse(os.path.exists(local_graflean))

    def test_persistence_across_instances(self):
        """Garante que novas instâncias do LibraryManager preservam projetos registrados."""
        meta = self.manager.register_project(self.project_path, name="Projeto Teste")

        new_manager = LibraryManager(base_dir=self.base_dir)
        loaded = new_manager.get_project(meta.id)
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.name, "Projeto Teste")
        self.assertEqual(loaded.path, os.path.abspath(self.project_path))

    def test_update_project_metrics(self):
        """Verifica atualização de métricas e timestamp da última análise."""
        meta = self.manager.register_project(self.project_path)
        self.assertIsNone(meta.last_scanned)

        self.manager.update_project_metrics(
            project_id=meta.id,
            node_count=150,
            edge_count=320,
            avg_instability=0.428,
            has_cycles=True
        )

        updated = self.manager.get_project(meta.id)
        self.assertEqual(updated.node_count, 150)
        self.assertEqual(updated.edge_count, 320)
        self.assertEqual(updated.avg_instability, 0.43)
        self.assertTrue(updated.has_cycles)
        self.assertIsNotNone(updated.last_scanned)

    def test_save_project_graph_with_ai_accelerator(self):
        """Testa salvamento do grafo na biblioteca central e geração de .graflean/ com architecture.md."""
        meta = self.manager.register_project(self.project_path, ai_accelerator=True)
        # Cria um arquivo mock para simular scan
        with open(os.path.join(self.project_path, "App.py"), "w") as f:
            f.write("class App:\n    pass\n")

        graph = ProjectGraph(self.project_path)
        graph.scan_project()

        central_path = self.manager.save_project_graph(meta.id, graph)
        self.assertTrue(os.path.isfile(central_path))

        # Verifica cópia local e architecture.md
        local_graph = os.path.join(self.project_path, ".graflean", "graph.json")
        local_summary = os.path.join(self.project_path, ".graflean", "architecture.md")
        self.assertTrue(os.path.isfile(local_graph))
        self.assertTrue(os.path.isfile(local_summary))

    def test_save_project_graph_zero_footprint(self):
        """No modo Zero-Footprint, save_project_graph não grava nada no diretório do projeto."""
        meta = self.manager.register_project(self.project_path, ai_accelerator=False)
        graph = ProjectGraph(self.project_path)
        graph.scan_project()

        central_path = self.manager.save_project_graph(meta.id, graph)
        self.assertTrue(os.path.isfile(central_path))
        self.assertFalse(os.path.exists(os.path.join(self.project_path, ".graflean")))


if __name__ == "__main__":
    unittest.main()
