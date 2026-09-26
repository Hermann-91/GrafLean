"""
Pacote Modular de Visualização Arquitetural do GrafLean.
Exporta o ArchitectureVisualizer mantendo 100% de retrocompatibilidade com o sistema.
"""

from core.visualizer.visualizer import ArchitectureVisualizer
from core.visualizer.data_serializer import GraphDataSerializer, SerializedGraphData
from core.visualizer.template_engine import TemplateEngine

__all__ = [
    "ArchitectureVisualizer",
    "GraphDataSerializer",
    "SerializedGraphData",
    "TemplateEngine",
]
