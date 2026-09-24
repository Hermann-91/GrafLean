"""
Módulo de Modelos de Domínio do Grafo Arquitetural.
Define as entidades fundamentais, tipos de nós, conexões e métricas de acoplamento.
"""

from __future__ import annotations
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Dict, List, Optional, Any


class SymbolType(str, Enum):
    FILE = "file"
    CLASS = "class"
    INTERFACE = "interface"
    TRAIT = "trait"
    METHOD = "method"
    FUNCTION = "function"


class EdgeType(str, Enum):
    CALLS = "calls"
    INHERITS = "inherits"
    IMPLEMENTS = "implements"
    INJECTS = "injects"
    USES = "uses"


@dataclass
class ArchitectureMetrics:
    afferent_coupling: int = 0   # Ca: Quantos módulos dependem deste (Inbound)
    efferent_coupling: int = 0   # Ce: De quantos módulos este depende (Outbound)
    instability: float = 0.0     # I = Ce / (Ca + Ce) [0 = Máxima Estabilidade, 1 = Máxima Instabilidade]
    is_deep_module: bool = True  # Ousterhout: interface simples que oculta complexidade
    has_cycles: bool = False     # Alerta de dependência circular

    def calculate_instability(self) -> float:
        total = self.afferent_coupling + self.efferent_coupling
        if total == 0:
            self.instability = 0.0
        else:
            self.instability = round(self.efferent_coupling / total, 2)
        return self.instability


@dataclass
class Node:
    id: str                                # Identificador único (ex: "App\\Services\\CheckoutService::processar")
    name: str                              # Nome curto (ex: "processar")
    symbol_type: SymbolType                # Tipo do símbolo
    file_path: str                         # Caminho do arquivo no disco
    line: int                              # Linha onde o símbolo é definido
    docstring: Optional[str] = None        # Resumo ou docstring extraída
    metadata: Dict[str, Any] = field(default_factory=dict)
    metrics: ArchitectureMetrics = field(default_factory=ArchitectureMetrics)
    git_status: Optional[str] = None       # Status Git: 'new', 'modified', 'deleted' ou None

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["symbol_type"] = self.symbol_type.value
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Node:
        metrics_data = data.pop("metrics", {})
        metrics = ArchitectureMetrics(**metrics_data) if metrics_data else ArchitectureMetrics()
        symbol_type = SymbolType(data.pop("symbol_type"))
        return cls(symbol_type=symbol_type, metrics=metrics, **data)


@dataclass
class Edge:
    source_id: str                         # ID do nó de origem (quem chama/depende)
    target_id: str                         # ID do nó de destino (quem é chamado/dependência)
    edge_type: EdgeType                    # Tipo de conexão
    line: Optional[int] = None             # Linha onde a chamada ocorre
    description: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["edge_type"] = self.edge_type.value
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Edge:
        edge_type = EdgeType(data.pop("edge_type"))
        return cls(edge_type=edge_type, **data)
