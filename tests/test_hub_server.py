"""
Testes de Integração Automatizados para o GrafLean Hub Server (Fase 2 do Hub PWA).
Valida rotas HTTP, APIs REST e renderização de Workspaces e Dashboard.
"""

import os
import json
import shutil
import tempfile
import unittest
import urllib.request
import urllib.error

from core.hub_server import HubServer


class TestHubServer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.test_dir = tempfile.mkdtemp(prefix="graflean_hub_test_")
        cls.base_dir = os.path.join(cls.test_dir, ".graflean")
        cls.project_dir = os.path.join(cls.test_dir, "projeto_teste")
        os.makedirs(cls.project_dir, exist_ok=True)

        with open(os.path.join(cls.project_dir, "Index.php"), "w") as f:
            f.write("<?php class Index { public function main() {} }")

        # Inicia servidor em porta efêmera (port=0)
        cls.hub = HubServer(base_dir=cls.base_dir, port=0)
        cls.hub.start(block=False, open_browser=False)
        cls.base_url = f"http://127.0.0.1:{cls.hub.port}"

    @classmethod
    def tearDownClass(cls):
        cls.hub.stop()
        shutil.rmtree(cls.test_dir, ignore_errors=True)

    def _http_get(self, path: str):
        req = urllib.request.Request(f"{self.base_url}{path}")
        with urllib.request.urlopen(req) as res:
            return res.status, res.read().decode("utf-8")

    def _http_post_json(self, path: str, payload: dict):
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            f"{self.base_url}{path}",
            data=data,
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req) as res:
            return res.status, json.loads(res.read().decode("utf-8"))

    def test_01_hub_dashboard_returns_200(self):
        """Verifica se a rota raiz '/' serve o Dashboard HTML do Hub."""
        status, html = self._http_get("/")
        self.assertEqual(status, 200)
        self.assertIn("GrafLean Hub", html)
        self.assertIn("Biblioteca de Projetos", html)

    def test_02_pwa_manifest_returns_200(self):
        """Verifica se o manifesto PWA '/manifest.json' é servido com sucesso."""
        status, content = self._http_get("/manifest.json")
        self.assertEqual(status, 200)
        data = json.loads(content)
        self.assertEqual(data.get("name"), "GrafLean IDE Hub")

    def test_03_api_projects_initially_empty(self):
        """Verifica se /api/projects retorna lista vazia no startup."""
        status, res = self._http_get("/api/projects")
        self.assertEqual(status, 200)
        self.assertTrue(res.startswith("{"))
        data = json.loads(res)
        self.assertTrue(data.get("success"))
        self.assertEqual(len(data.get("projects")), 0)

    def test_04_api_add_project(self):
        """Cadastra e indexa novo projeto via POST /api/projects/add."""
        status, res = self._http_post_json("/api/projects/add", {
            "path": self.project_dir,
            "name": "Projeto Teste",
            "ai_accelerator": True
        })
        self.assertEqual(status, 200)
        self.assertTrue(res.get("success"))
        proj = res.get("project")
        self.assertEqual(proj["name"], "Projeto Teste")
        self.assertTrue(proj["node_count"] > 0)
        TestHubServer.registered_id = proj["id"]

    def test_05_workspace_route_renders_ide(self):
        """Verifica se /p/<project_id> renderiza o Workspace IDE com o botão de voltar."""
        pid = getattr(self, "registered_id", None)
        self.assertIsNotNone(pid)
        status, html = self._http_get(f"/p/{pid}")
        self.assertEqual(status, 200)
        self.assertIn("🏛️ GrafLean", html)
        self.assertIn("◀ Biblioteca", html)

    def test_05b_api_file_content(self):
        """Testa lazy loading de arquivo via GET e POST /api/file-content com proteção de path traversal."""
        # 1. GET sob demanda
        status, res = self._http_get("/api/file-content?path=Index.php")
        self.assertEqual(status, 200)
        data = json.loads(res)
        self.assertTrue(data.get("success"))
        self.assertIn("class Index", data.get("content"))

        # 2. POST sob demanda
        status, data = self._http_post_json("/api/file-content", {"path": "Index.php"})
        self.assertEqual(status, 200)
        self.assertTrue(data.get("success"))
        self.assertIn("class Index", data.get("content"))

        # 3. Proteção contra Path Traversal
        try:
            self._http_get("/api/file-content?path=../../etc/passwd")
        except urllib.error.HTTPError as e:
            self.assertEqual(e.code, 403)

    def test_06_api_toggle_ai(self):
        """Alterna o modo IA de um projeto via POST /api/projects/toggle-ai."""
        pid = getattr(self, "registered_id", None)
        status, res = self._http_post_json("/api/projects/toggle-ai", {
            "project_id": pid,
            "enable": False
        })
        self.assertEqual(status, 200)
        self.assertTrue(res.get("success"))

    def test_07_api_rescan(self):
        """Força re-varredura via POST /api/projects/rescan."""
        pid = getattr(self, "registered_id", None)
        status, res = self._http_post_json("/api/projects/rescan", {
            "project_id": pid
        })
        self.assertEqual(status, 200)
        self.assertTrue(res.get("success"))

    def test_07b_api_ai_state_and_changes(self):
        """Valida controle do estado da IA e consulta de alterações via /api/ai-state e /api/changes."""
        status, res = self._http_post_json("/api/ai-state", {
            "path": "Index.php",
            "state": "editing"
        })
        self.assertEqual(status, 200)
        self.assertTrue(res.get("success"))
        self.assertEqual(res["event"]["state"], "editing")
        self.assertEqual(res["summary"]["ai_active_count"], 1)

        # Consulta resumo de alterações
        status, res_changes = self._http_post_json("/api/changes", {})
        self.assertEqual(status, 200)
        self.assertTrue(res_changes.get("success"))
        self.assertIn("ai_tasks", res_changes.get("summary", {}))
        self.assertEqual(res_changes["summary"]["ai_tasks"].get("Index.php"), "editing")

    def test_08_api_remove_project(self):
        """Remove o projeto da biblioteca via POST /api/projects/remove."""
        pid = getattr(self, "registered_id", None)
        status, res = self._http_post_json("/api/projects/remove", {
            "project_id": pid,
            "purge_local": True
        })
        self.assertEqual(status, 200)
        self.assertTrue(res.get("success"))

        # Confirma que a lista voltou a ficar vazia
        _, res_list = self._http_get("/api/projects")
        data = json.loads(res_list)
        self.assertEqual(len(data.get("projects")), 0)

    def test_09_service_worker_returns_200(self):
        """Verifica se o Service Worker PWA '/service-worker.js' é servido com sucesso."""
        status, content = self._http_get("/service-worker.js")
        self.assertEqual(status, 200)
        self.assertIn("graflean-hub-v1", content)

    def test_10_api_shutdown(self):
        """Valida que a rota /api/shutdown responde 200 com mensagem de sucesso."""
        called = []
        self.hub._on_shutdown_test_hook = lambda: called.append(True)
        status, res = self._http_post_json("/api/shutdown", {})
        self.assertEqual(status, 200)
        self.assertTrue(res.get("success"))
        import time
        time.sleep(0.3)
        self.assertTrue(len(called) > 0)


if __name__ == "__main__":
    unittest.main()
