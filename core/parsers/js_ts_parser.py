"""
Parser estático para JavaScript e TypeScript (React, Angular, Node.js).
Extrai módulos, imports/exports, componentes funcionais, classes, custom hooks e chamadas de API.
"""

import re
from typing import Dict, List
from core.models import Node, Edge, SymbolType, EdgeType
from core.parsers.base import BaseParser, ParseResult


class JSTypeScriptParser(BaseParser):
    RE_IMPORT = re.compile(
        r"^\s*import\s+(?:(?P<default>[a-zA-Z0-9_$]+)|(?:\{(?P<named>[^}]+)\})|(?:\*\s+as\s+(?P<all>[a-zA-Z0-9_$]+)))\s+from\s+['\"](?P<source>[^'\"]+)['\"];?",
        re.MULTILINE
    )
    RE_EXPORT_CLASS = re.compile(
        r"export\s+(?:default\s+)?class\s+(?P<name>[a-zA-Z0-9_$]+)(?:\s+extends\s+(?P<extends>[a-zA-Z0-9_$]+))?(?:\s+implements\s+(?P<implements>[^{]+))?",
        re.MULTILINE
    )
    RE_EXPORT_FUNCTION = re.compile(
        r"export\s+(?:default\s+)?(?:async\s+)?function\s+(?P<name>[a-zA-Z0-9_$]+)\s*\((?P<params>[^)]*)\)",
        re.MULTILINE
    )
    RE_CONST_ARROW = re.compile(
        r"export\s+const\s+(?P<name>[a-zA-Z0-9_$]+)\s*=\s*(?:async\s*)?\((?P<params>[^)]*)\)\s*=>",
        re.MULTILINE
    )
    RE_HOOK_CALL = re.compile(r"\b(?P<hook>use[A-Z][a-zA-Z0-9_$]*)\s*\(")
    RE_JSX_COMPONENT = re.compile(r"<(?P<comp>[A-Z][a-zA-Z0-9_$]*)\b")

    def parse_source(self, code: str, file_path: str) -> ParseResult:
        result = ParseResult()
        file_node_id = f"file://{file_path}"
        file_node = Node(
            id=file_node_id,
            name=file_path.split("/")[-1],
            symbol_type=SymbolType.FILE,
            file_path=file_path,
            line=1
        )
        result.nodes.append(file_node)

        # 1. Imports
        imports: Dict[str, str] = {}
        for m in self.RE_IMPORT.finditer(code):
            src = m.group("source")
            line_no = code[:m.start()].count("\n") + 1
            if m.group("default"):
                name = m.group("default")
                imports[name] = src
            if m.group("named"):
                for item in m.group("named").split(","):
                    item_clean = item.strip()
                    if " as " in item_clean:
                        orig, alias = item_clean.split(" as ")
                        imports[alias.strip()] = f"{src}#{orig.strip()}"
                    elif item_clean:
                        imports[item_clean] = f"{src}#{item_clean}"
            result.edges.append(Edge(source_id=file_node_id, target_id=src, edge_type=EdgeType.USES, line=line_no, description=f"Import {src}"))

        # 2. Classes (Angular Services, Components, Controllers)
        for m in self.RE_EXPORT_CLASS.finditer(code):
            name = m.group("name")
            extends = m.group("extends")
            line_no = code[:m.start()].count("\n") + 1
            class_id = f"{file_path}::{name}"
            node = Node(id=class_id, name=name, symbol_type=SymbolType.CLASS, file_path=file_path, line=line_no)
            result.nodes.append(node)
            result.edges.append(Edge(source_id=file_node_id, target_id=class_id, edge_type=EdgeType.USES, line=line_no))
            if extends:
                target = imports.get(extends, extends)
                result.edges.append(Edge(source_id=class_id, target_id=target, edge_type=EdgeType.INHERITS, line=line_no))

        # 3. Funções e Componentes React (export function, export const = () =>)
        symbols = []
        for m in self.RE_EXPORT_FUNCTION.finditer(code):
            symbols.append((m.group("name"), code[:m.start()].count("\n") + 1))
        for m in self.RE_CONST_ARROW.finditer(code):
            symbols.append((m.group("name"), code[:m.start()].count("\n") + 1))

        for sym_name, line_no in symbols:
            sym_id = f"{file_path}::{sym_name}"
            if sym_name[0].isupper():
                doc = "Componente React"
            elif sym_name.startswith("use"):
                doc = "Custom Hook React"
            else:
                doc = "Função exportada"

            node = Node(id=sym_id, name=sym_name, symbol_type=SymbolType.FUNCTION, file_path=file_path, line=line_no, docstring=doc)
            result.nodes.append(node)
            result.edges.append(Edge(source_id=file_node_id, target_id=sym_id, edge_type=EdgeType.USES, line=line_no))

        # 4. Uso de Hooks e Componentes Filhos
        for m in self.RE_HOOK_CALL.finditer(code):
            hook_name = m.group("hook")
            line_no = code[:m.start()].count("\n") + 1
            target = imports.get(hook_name, hook_name)
            result.edges.append(Edge(source_id=file_node_id, target_id=target, edge_type=EdgeType.CALLS, line=line_no, description=f"Uso do Hook {hook_name}()"))

        for m in self.RE_JSX_COMPONENT.finditer(code):
            comp_name = m.group("comp")
            line_no = code[:m.start()].count("\n") + 1
            if comp_name in imports:
                result.edges.append(Edge(source_id=file_node_id, target_id=imports[comp_name], edge_type=EdgeType.CALLS, line=line_no, description=f"Renderiza <{comp_name} />"))

        return result
