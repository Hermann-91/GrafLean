"""
Interface base para extratores de código estático (Parsers).
Permite plugar novas linguagens mantendo o core desacoplado.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List
from core.models import Node, Edge


@dataclass
class ParseResult:
    nodes: List[Node] = field(default_factory=list)
    edges: List[Edge] = field(default_factory=list)


class BaseParser(ABC):
    @abstractmethod
    def parse_source(self, code: str, file_path: str) -> ParseResult:
        """Analisa o código-fonte em memória e retorna nós e arestas extraídos."""
        pass

    def parse_file(self, file_path: str) -> ParseResult:
        """Lê o arquivo do disco com tratamento seguro de encoding UTF-8."""
        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                code = f.read()
            return self.parse_source(code, file_path)
        except Exception as e:
            return ParseResult()
