"""
Módulo de Análise Arquitetural.
Calcula métricas de acoplamento (Ca, Ce, Instabilidade), detecta dependências circulares
e avalia profundidade de módulos segundo Robert C. Martin e John Ousterhout.
"""

from typing import Dict, List, Set
from collections import defaultdict
from core.models import Node, Edge, EdgeType, ArchitectureMetrics
from core.summarizer import SemanticSummarizer


class ArchitectureAnalyzer:
    def __init__(self, nodes: List[Node], edges: List[Edge]):
        self.nodes = {n.id: n for n in nodes}
        self.edges = edges
        self.adjacency: Dict[str, Set[str]] = defaultdict(set)
        self.reverse_adjacency: Dict[str, Set[str]] = defaultdict(set)
        self._build_adjacency()

    def _build_adjacency(self):
        for e in self.edges:
            # Considera apenas conexões de dependência estrutural
            if e.edge_type in (EdgeType.CALLS, EdgeType.INJECTS, EdgeType.INHERITS, EdgeType.IMPLEMENTS, EdgeType.USES):
                self.adjacency[e.source_id].add(e.target_id)
                self.reverse_adjacency[e.target_id].add(e.source_id)

    def analyze_all(self):
        """Calcula as métricas para todos os nós presentes no grafo."""
        cycles = self.detect_cycles()
        cycle_nodes = set().union(*cycles) if cycles else set()

        for node_id, node in self.nodes.items():
            ca = len(self.reverse_adjacency.get(node_id, set()))
            ce = len(self.adjacency.get(node_id, set()))
            has_cycle = node_id in cycle_nodes

            metrics = ArchitectureMetrics(
                afferent_coupling=ca,
                efferent_coupling=ce,
                has_cycles=has_cycle
            )
            metrics.calculate_instability()

            # Diagnóstico de Módulo Profundo (Ousterhout):
            # Se for uma classe e possuir poucos métodos públicos em relação às chamadas internas
            methods = [n for n in self.nodes.values() if n.id.startswith(f"{node_id}::")]
            if methods:
                metrics.is_deep_module = len(methods) <= 5 or ca >= ce

            node.metrics = metrics

            # Enriquecimento inteligente caso o nó não tenha docstring manual
            if not node.docstring:
                inbound = self.get_inbound_callers(node_id)
                outbound = self.get_outbound_dependencies(node_id)
                node.docstring = SemanticSummarizer.infer_summary(node, inbound, outbound, self.nodes)

    def detect_cycles(self) -> List[List[str]]:
        """Detecta ciclos de dependência utilizando busca em profundidade (DFS)."""
        visited = set()
        rec_stack = set()
        cycles = []
        path = []

        def dfs(u: str):
            visited.add(u)
            rec_stack.add(u)
            path.append(u)

            for v in self.adjacency.get(u, set()):
                if v not in visited:
                    dfs(v)
                elif v in rec_stack:
                    # Ciclo encontrado
                    cycle_start = path.index(v)
                    cycles.append(path[cycle_start:].copy())

            path.pop()
            rec_stack.remove(u)

        for node_id in list(self.adjacency.keys()):
            if node_id not in visited:
                dfs(node_id)

        return cycles

    def get_inbound_callers(self, node_id: str) -> List[str]:
        """Retorna a lista de IDs de quem depende/chama este nó."""
        return sorted(list(self.reverse_adjacency.get(node_id, set())))

    def get_outbound_dependencies(self, node_id: str) -> List[str]:
        """Retorna a lista de IDs do que este nó depende/chama."""
        return sorted(list(self.adjacency.get(node_id, set())))
