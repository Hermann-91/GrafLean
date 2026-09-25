"""
Parser estático para arquivos de folha de estilo CSS (.css).
Extrai nós de arquivo, regras @import e classes principais de estilo.
"""

import os
import re
from core.models import Node, Edge, SymbolType, EdgeType
from core.parsers.base import BaseParser, ParseResult


class CSSParser(BaseParser):
    """Extrai informações estruturadas de folhas de estilo CSS."""

    RE_IMPORT = re.compile(r"""@import\s+(?:url\(['"]?([^'")]+)['"]?\)|['"]([^'"]+)['"]);""")
    RE_CLASS = re.compile(r"""\.([a-zA-Z0-9_-]+)\s*\{""")

    def parse_source(self, code: str, file_path: str) -> ParseResult:
        result = ParseResult()
        file_name = os.path.basename(file_path)
        file_id = f"file://{file_path}"

        file_node = Node(
            id=file_id,
            name=file_name,
            symbol_type=SymbolType.FILE,
            file_path=file_path,
            line=1,
            docstring=f"Folha de Estilo CSS ({file_name})"
        )
        result.nodes.append(file_node)

        # 1. Extração de regras @import (dependências de estilo entre arquivos)
        for match in self.RE_IMPORT.finditer(code):
            imported_file = match.group(1) or match.group(2)
            if imported_file:
                clean_target = imported_file.split("?")[0].strip()
                if not clean_target.startswith("http://") and not clean_target.startswith("https://"):
                    file_dir = os.path.dirname(file_path)
                    target_abs = os.path.normpath(os.path.join(file_dir, clean_target))
                    line_no = code[:match.start()].count("\n") + 1
                    result.edges.append(Edge(
                        source_id=file_id,
                        target_id=f"file://{target_abs}",
                        edge_type=EdgeType.USES,
                        line=line_no,
                        description=f"@import {imported_file}"
                    ))

        # 2. Extração de classes CSS significativas
        seen_classes = set()
        for match in self.RE_CLASS.finditer(code):
            class_name = match.group(1).strip()
            if class_name in seen_classes or len(class_name) <= 1:
                continue
            seen_classes.add(class_name)

            if len(seen_classes) > 50:
                break

            line_no = code[:match.start()].count("\n") + 1
            class_node_id = f"{file_id}::.{class_name}"
            class_node = Node(
                id=class_node_id,
                name=f".{class_name}",
                symbol_type=SymbolType.FUNCTION,
                file_path=file_path,
                line=line_no,
                docstring=f"Classe CSS .{class_name}"
            )
            result.nodes.append(class_node)
            result.edges.append(Edge(source_id=file_id, target_id=class_node_id, edge_type=EdgeType.USES))

        return result
