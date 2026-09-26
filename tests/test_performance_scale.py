"""
Testes de Stress, Performance e Escala (Fase C do Plano de Evolução).
Valida o comportamento do GrafLean com 1.000 e 3.000 nós, medição de latência
de serialização e simulação de rajadas de criação de arquivos pela IA.
"""

import time
import tempfile
import unittest
from core.models import Node, Edge, SymbolType, EdgeType
from core.graph import ProjectGraph
from core.visualizer.data_serializer import GraphDataSerializer
from core.visualizer.template_engine import TemplateEngine
from core.visualizer import ArchitectureVisualizer
from core.change_manager import ChangeManager, AIState


class TestPerformanceAndScale(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.root = self.tmp_dir.name
        self.graph = ProjectGraph(self.root)

    def tearDown(self):
        self.tmp_dir.cleanup()

    def test_serialization_performance_1000_nodes(self):
        """Mede o tempo de serialização e sanitização com 1.000 nós e 2.000 arestas."""
        nodes = {}
        edges = []

        for i in range(1000):
            node_id = f"node_{i}"
            st = SymbolType.FILE if i % 4 == 0 else (SymbolType.CLASS if i % 4 == 1 else SymbolType.METHOD)
            parent = f"node_{(i // 4) * 4}" if st != SymbolType.FILE else None
            node = Node(
                id=node_id,
                name=f"Symbol_{i}",
                symbol_type=st,
                file_path=f"src/module_{i % 50}/file_{i}.py",
                line=i + 1
            )
            nodes[node_id] = node

            if i > 0:
                edges.append(Edge(
                    source_id=f"node_{i-1}",
                    target_id=node_id,
                    edge_type=EdgeType.CALLS
                ))

        self.graph.nodes = nodes
        self.graph.edges = edges

        start = time.perf_counter()
        serializer = GraphDataSerializer(self.graph)
        data = serializer.serialize_all()
        elapsed_ms = (time.perf_counter() - start) * 1000

        # Valida que 1.000 nós são serializados em menos de 200ms
        self.assertLess(elapsed_ms, 200.0, f"Serialização muito lenta: {elapsed_ms:.2f}ms")
        self.assertEqual(len(serializer.serialize_nodes()), 1000)
        self.assertEqual(len(serializer.serialize_edges()), 999)

        # Valida renderização via TemplateEngine
        engine = TemplateEngine()
        render_start = time.perf_counter()
        html = engine.render(data)
        render_ms = (time.perf_counter() - render_start) * 1000

        self.assertLess(render_ms, 50.0, f"Renderização HTML muito lenta: {render_ms:.2f}ms")
        self.assertIn("Symbol_999", html)

    def test_serialization_performance_3000_nodes(self):
        """Mede a capacidade de suporte com 3.000 nós (projeto de grande porte)."""
        nodes = {}
        for i in range(3000):
            node_id = f"big_node_{i}"
            nodes[node_id] = Node(
                id=node_id,
                name=f"BigSymbol_{i}",
                symbol_type=SymbolType.FUNCTION,
                file_path=f"lib/file_{i % 100}.py",
                line=10
            )

        self.graph.nodes = nodes
        self.graph.edges = []

        start = time.perf_counter()
        serializer = GraphDataSerializer(self.graph)
        data = serializer.serialize_all()
        elapsed_ms = (time.perf_counter() - start) * 1000

        # 3.000 nós devem ser processados em menos de 500ms
        self.assertLess(elapsed_ms, 500.0, f"Serialização de 3.000 nós lenta: {elapsed_ms:.2f}ms")
        self.assertTrue(len(data.nodes_json) > 100000)

    def test_ai_simulation_rapid_burst_100_files(self):
        """Simula a IA criando e modificando 100 arquivos em sequência."""
        cm = ChangeManager(self.root)
        received_events = []
        cm.subscribe(lambda e: received_events.append(e))

        start = time.perf_counter()
        # 1. IA inicia 50 criações
        for i in range(50):
            path = f"ai_gen/service_{i}.py"
            cm.set_ai_state(path, AIState.CREATING)

        # 2. IA transiciona para edição
        for i in range(50):
            path = f"ai_gen/service_{i}.py"
            cm.set_ai_state(path, AIState.EDITING)

        # 3. IA conclui
        for i in range(50):
            path = f"ai_gen/service_{i}.py"
            cm.clear_ai_state(path)

        elapsed_ms = (time.perf_counter() - start) * 1000

        # 150 transições de estado despachadas
        self.assertEqual(len(received_events), 150)
        self.assertLess(elapsed_ms, 50.0, f"Disparo de eventos da IA lento: {elapsed_ms:.2f}ms")
        self.assertEqual(cm.get_summary()["ai_active_count"], 0)

    def test_generated_html_contains_performance_and_perspective_features(self):
        """Verifica se o HTML gerado inclui os seletores de perspectiva e avisos de limite."""
        node = Node(id="N1", name="App", symbol_type=SymbolType.FILE, file_path="app.py", line=1)
        self.graph.nodes = {"N1": node}
        self.graph.edges = []

        viz = ArchitectureVisualizer(self.graph)
        html = viz.render_html()

        self.assertIn("btn-perspective-code", html)
        self.assertIn("btn-perspective-change", html)
        self.assertIn("change-summary-banner", html)
        self.assertIn("graph-limit-banner", html)
        self.assertIn("switchPerspective", html)
        self.assertIn("applyIncrementalPatch", html)
        self.assertIn("focusNextChange", html)


if __name__ == "__main__":
    unittest.main()
