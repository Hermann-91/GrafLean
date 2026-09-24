"""
Parser de Markdown (.md) para Especificações e Tarefas de Orquestração de Agentes.
Extrai nós de documentação, títulos, objetivos e links cruzados para arquivos do projeto.
"""

import os
import re
from core.models import Node, Edge, SymbolType, EdgeType
from core.parsers.base import BaseParser, ParseResult


class MarkdownParser(BaseParser):
    """Extrai informações estruturadas de arquivos Markdown (.md)."""

    def parse_source(self, code: str, file_path: str) -> ParseResult:
        result = ParseResult()
        file_name = os.path.basename(file_path)
        file_id = f"file://{file_path}"

        # 1. Extrai o título principal do documento (# Título)
        title_match = re.search(r"^#\s+(.+)$", code, re.MULTILINE)
        doc_summary = title_match.group(1).strip() if title_match else f"Documento Markdown ({file_name})"

        file_node = Node(
            id=file_id,
            name=file_name,
            symbol_type=SymbolType.FILE,
            file_path=file_path,
            line=1,
            docstring=doc_summary
        )
        result.nodes.append(file_node)

        # 2. Extrai seções de nível 2 (## Seção) como marcos de tarefa/especificação
        for match in re.finditer(r"^##\s+(.+)$", code, re.MULTILINE):
            section_name = match.group(1).strip()
            line_no = code[:match.start()].count("\n") + 1
            sec_id = f"{file_id}::{section_name}"

            sec_node = Node(
                id=sec_id,
                name=section_name,
                symbol_type=SymbolType.FUNCTION,
                file_path=file_path,
                line=line_no,
                docstring=f"Seção: {section_name}"
            )
            result.nodes.append(sec_node)
            result.edges.append(Edge(source_id=sec_id, target_id=file_id, edge_type=EdgeType.USES))

        # 3. Extrai referências e links para outros arquivos do projeto (ex: `[arquivo](caminho)`)
        link_pattern = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
        for match in link_pattern.finditer(code):
            target = match.group(2).strip()
            if not target.startswith("http://") and not target.startswith("https://"):
                clean_target = target.split("#")[0]
                if clean_target:
                    result.edges.append(Edge(
                        source_id=file_id,
                        target_id=clean_target,
                        edge_type=EdgeType.CALLS
                    ))

        return result
