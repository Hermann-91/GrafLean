"""
Parser estático para HTML e templates Blade do Laravel.
Detecta herança de templates (@extends), inclusão de parciais (@include),
componentes Blade (<x-component />) e links de CSS/JavaScript.
"""

import re
from core.models import Node, Edge, SymbolType, EdgeType
from core.parsers.base import BaseParser, ParseResult


class HTMLBladeParser(BaseParser):
    RE_EXTENDS = re.compile(r"@extends\s*\(\s*['\"]([^'\"]+)['\"]\s*\)")
    RE_INCLUDE = re.compile(r"@include\s*\(\s*['\"]([^'\"]+)['\"]\s*\)")
    RE_BLADE_COMPONENT = re.compile(r"<x-([a-zA-Z0-9_\-\.]+)")
    RE_LINK_CSS = re.compile(r"<link\s+[^>]*href=['\"]([^'\"]+\.css)['\"]")
    RE_SCRIPT_JS = re.compile(r"<script\s+[^>]*src=['\"]([^'\"]+\.(?:js|ts))['\"]")

    def parse_source(self, code: str, file_path: str) -> ParseResult:
        result = ParseResult()
        file_node_id = f"file://{file_path}"
        file_node = Node(
            id=file_node_id,
            name=file_path.split("/")[-1],
            symbol_type=SymbolType.FILE,
            file_path=file_path,
            line=1,
            docstring="Template Blade / HTML"
        )
        result.nodes.append(file_node)

        for m in self.RE_EXTENDS.finditer(code):
            layout = m.group(1)
            line_no = code[:m.start()].count("\n") + 1
            result.edges.append(Edge(source_id=file_node_id, target_id=f"blade://{layout}", edge_type=EdgeType.INHERITS, line=line_no, description=f"Estende layout @extends('{layout}')"))

        for m in self.RE_INCLUDE.finditer(code):
            partial = m.group(1)
            line_no = code[:m.start()].count("\n") + 1
            result.edges.append(Edge(source_id=file_node_id, target_id=f"blade://{partial}", edge_type=EdgeType.CALLS, line=line_no, description=f"Inclui parcial @include('{partial}')"))

        for m in self.RE_BLADE_COMPONENT.finditer(code):
            comp = m.group(1)
            line_no = code[:m.start()].count("\n") + 1
            result.edges.append(Edge(source_id=file_node_id, target_id=f"blade-component://{comp}", edge_type=EdgeType.CALLS, line=line_no, description=f"Usa componente <x-{comp} />"))

        for m in self.RE_LINK_CSS.finditer(code):
            css = m.group(1)
            line_no = code[:m.start()].count("\n") + 1
            result.edges.append(Edge(source_id=file_node_id, target_id=f"asset://{css}", edge_type=EdgeType.USES, line=line_no, description=f"Carrega CSS {css}"))

        for m in self.RE_SCRIPT_JS.finditer(code):
            js = m.group(1)
            line_no = code[:m.start()].count("\n") + 1
            result.edges.append(Edge(source_id=file_node_id, target_id=f"asset://{js}", edge_type=EdgeType.USES, line=line_no, description=f"Carrega Script {js}"))

        return result
