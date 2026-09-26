"""
Testes automatizados para a Fase E (Experiência IA) e Fase F (Refinamentos).
Cobre o Histórico de Operações da IA, buffer circular de eventos,
endpoints HTTP (/api/ai-history, /api/ai-history/clear) e os componentes visuais
(Mini-Map, AI Status Capsule, Drawer de Histórico e Clustering).
"""

import os
import sys
import json
import time
import shutil
import tempfile
import unittest
import urllib.request
import urllib.parse
from http.server import HTTPServer

# Garante importação a partir da raiz
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.change_manager import ChangeManager, AIState
from core.hub_server import HubServer, ProjectSession
from core.library import LibraryManager
from core.graph import ProjectGraph
from core.visualizer import ArchitectureVisualizer


class TestAIExperienceAndRefinements(unittest.TestCase):
    """Suíte de validação da Experiência IA e Refinamentos (Fases E e F)."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="graflean_test_phase_ef_")
        self.change_mgr = ChangeManager(self.test_dir)

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_ai_history_recording_and_retrieval(self):
        """Valida se operações da IA são registradas na timeline com mensagens e horários."""
        self.change_mgr.set_ai_state("auth/service.py", "creating", message="Criando serviço de autenticação JWT")
        self.change_mgr.set_ai_state("auth/token.py", "editing", message="Ajustando expiração do token")

        history = self.change_mgr.get_ai_history()
        self.assertEqual(len(history), 2)

        # O mais recente fica no topo (índice 0)
        self.assertEqual(history[0]["path"], "auth/token.py")
        self.assertEqual(history[0]["state"], "editing")
        self.assertEqual(history[0]["message"], "Ajustando expiração do token")
        self.assertEqual(history[0]["file_name"], "token.py")
        self.assertIn(":", history[0]["time_str"])

        self.assertEqual(history[1]["path"], "auth/service.py")
        self.assertEqual(history[1]["state"], "creating")
        self.assertEqual(history[1]["message"], "Criando serviço de autenticação JWT")

    def test_ai_history_max_buffer_rotation(self):
        """Valida rotação FIFO do buffer para não ultrapassar o limite máximo de 50 itens."""
        for i in range(70):
            self.change_mgr.set_ai_state(f"module_{i}.py", "editing", message=f"Editando módulo {i}")

        history = self.change_mgr.get_ai_history()
        self.assertEqual(len(history), 50)
        # O último adicionado (índice 69) deve estar no topo
        self.assertEqual(history[0]["path"], "module_69.py")

    def test_clear_ai_history(self):
        """Garante que clear_ai_history limpa todos os registros do buffer."""
        self.change_mgr.set_ai_state("app.py", "editing")
        self.assertEqual(len(self.change_mgr.get_ai_history()), 1)

        self.change_mgr.clear_ai_history()
        self.assertEqual(len(self.change_mgr.get_ai_history()), 0)

    def test_get_summary_includes_ai_history(self):
        """Valida inclusão do histórico recente no resumo retornado por get_summary()."""
        self.change_mgr.set_ai_state("src/main.py", "creating", message="Arquivo principal")
        summary = self.change_mgr.get_summary()

        self.assertIn("ai_history", summary)
        self.assertIsInstance(summary["ai_history"], list)
        self.assertEqual(len(summary["ai_history"]), 1)
        self.assertEqual(summary["ai_history"][0]["path"], "src/main.py")

    def test_rendered_html_contains_phase_e_and_f_components(self):
        """Verifica se o HTML gerado inclui os novos elementos da Fase E e F."""
        # Cria arquivo mínimo de código para o grafo não ficar vazio
        sample_file = os.path.join(self.test_dir, "calc.py")
        with open(sample_file, "w", encoding="utf-8") as f:
            f.write("def soma(a, b):\n    return a + b\n")

        graph = ProjectGraph(self.test_dir)
        graph.scan_project()
        vis = ArchitectureVisualizer(graph)
        html = vis.render_html()

        # Componentes da Fase E
        self.assertIn('id="ai-status-capsule"', html)
        self.assertIn('id="ai-history-drawer"', html)
        self.assertIn('id="ai-history-list"', html)
        self.assertIn('id="btn-ai-history"', html)

        # Componentes da Fase F
        self.assertIn('id="change-mini-map"', html)
        self.assertIn('id="btn-toggle-clustering"', html)
        self.assertIn('id="telemetry-fps"', html)


class TestAIEndpointsIntegration(unittest.TestCase):
    """Testa a integração das novas rotas HTTP com o HubServer."""

    @classmethod
    def setUpClass(cls):
        cls.test_dir = tempfile.mkdtemp(prefix="graflean_hub_ef_")
        cls.base_dir = os.path.join(cls.test_dir, ".graflean")
        cls.project_dir = os.path.join(cls.test_dir, "my_project")
        os.makedirs(cls.project_dir)
        with open(os.path.join(cls.project_dir, "index.py"), "w", encoding="utf-8") as f:
            f.write("print('Hello EF')\n")

        cls.hub = HubServer(base_dir=cls.base_dir, port=0)
        cls.hub.start(block=False, open_browser=False)
        cls.base_url = f"http://127.0.0.1:{cls.hub.port}"

        # Registra projeto de teste na biblioteca
        cls.hub.manager.library.register_project(cls.project_dir, name="Projeto EF")

    @classmethod
    def tearDownClass(cls):
        cls.hub.stop()
        shutil.rmtree(cls.test_dir, ignore_errors=True)

    def _post(self, path, payload):
        url = f"{self.base_url}{path}"
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def _get(self, path):
        url = f"{self.base_url}{path}"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def test_ai_state_endpoint_with_message_and_history(self):
        """Valida POST /api/ai-state com mensagem descritiva e consulta via /api/ai-history."""
        resp = self._post("/api/ai-state", {
            "path": "service/user.py",
            "state": "creating",
            "message": "Criando model de usuário"
        })
        self.assertTrue(resp["success"])
        self.assertEqual(resp["event"]["message"], "Criando model de usuário")

        # Consulta via GET /api/ai-history
        hist_resp = self._get("/api/ai-history")
        self.assertTrue(hist_resp["success"])
        self.assertGreaterEqual(len(hist_resp["history"]), 1)
        self.assertEqual(hist_resp["history"][0]["path"], "service/user.py")

        # Limpeza via POST /api/ai-history/clear
        clear_resp = self._post("/api/ai-history/clear", {})
        self.assertTrue(clear_resp["success"])

        # Confirma que ficou vazio
        hist_resp2 = self._get("/api/ai-history")
        self.assertEqual(len(hist_resp2["history"]), 0)


if __name__ == "__main__":
    unittest.main()
