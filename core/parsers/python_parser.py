"""
Parser estático para Python utilizando a biblioteca padrão 'ast'.
Extrai classes, funções, métodos, herança, imports e chamadas com precisão 100% determinística.
"""

import ast
from typing import Dict, List, Optional, Tuple
from core.models import Node, Edge, SymbolType, EdgeType
from core.parsers.base import BaseParser, ParseResult


class PythonParser(BaseParser):
    def parse_source(self, code: str, file_path: str) -> ParseResult:
        result = ParseResult()
        try:
            tree = ast.parse(code, filename=file_path)
        except SyntaxError:
            return result

        file_node_id = f"file://{file_path}"
        file_node = Node(
            id=file_node_id,
            name=file_path.split("/")[-1],
            symbol_type=SymbolType.FILE,
            file_path=file_path,
            line=1
        )
        result.nodes.append(file_node)

        # Mapeamento de imports: alias -> full module/name
        imports: Dict[str, str] = {}
        for stmt in ast.walk(tree):
            if isinstance(stmt, ast.Import):
                for alias in stmt.names:
                    name = alias.asname or alias.name
                    imports[name] = alias.name
                    result.edges.append(Edge(source_id=file_node_id, target_id=alias.name, edge_type=EdgeType.USES, line=stmt.lineno, description=f"Import {alias.name}"))
            elif isinstance(stmt, ast.ImportFrom):
                mod = stmt.module or ""
                for alias in stmt.names:
                    name = alias.asname or alias.name
                    full = f"{mod}.{alias.name}" if mod else alias.name
                    imports[name] = full
                    result.edges.append(Edge(source_id=file_node_id, target_id=full, edge_type=EdgeType.USES, line=stmt.lineno, description=f"Import {full}"))

        # Mapeamento de Classes e Funções
        for stmt in tree.body:
            if isinstance(stmt, ast.ClassDef):
                class_id = f"{file_path}::{stmt.name}"
                doc = ast.get_docstring(stmt)
                class_node = Node(
                    id=class_id,
                    name=stmt.name,
                    symbol_type=SymbolType.CLASS,
                    file_path=file_path,
                    line=stmt.lineno,
                    docstring=doc
                )
                result.nodes.append(class_node)
                result.edges.append(Edge(source_id=file_node_id, target_id=class_id, edge_type=EdgeType.USES, line=stmt.lineno))

                # Herança
                for base in stmt.bases:
                    base_id = getattr(base, "id", None) or getattr(base, "attr", None)
                    if base_id:
                        base_name = imports.get(base_id, base_id)
                        result.edges.append(Edge(source_id=class_id, target_id=base_name, edge_type=EdgeType.INHERITS, line=stmt.lineno))

                # Métodos da Classe
                for item in stmt.body:
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        method_id = f"{class_id}::{item.name}"
                        method_doc = ast.get_docstring(item)
                        method_node = Node(
                            id=method_id,
                            name=item.name,
                            symbol_type=SymbolType.METHOD,
                            file_path=file_path,
                            line=item.lineno,
                            docstring=method_doc
                        )
                        result.nodes.append(method_node)
                        result.edges.append(Edge(source_id=class_id, target_id=method_id, edge_type=EdgeType.USES, line=item.lineno))

                        # Chamadas dentro do método
                        for call in ast.walk(item):
                            if isinstance(call, ast.Call):
                                called_name = self._resolve_call_name(call.func)
                                if called_name:
                                    if called_name.startswith("self.") and called_name.count(".") == 1:
                                        internal_id = f"{class_id}::{called_name[5:]}"
                                        result.edges.append(Edge(
                                            source_id=method_id,
                                            target_id=internal_id,
                                            edge_type=EdgeType.CALLS,
                                            line=getattr(call, "lineno", item.lineno)
                                        ))
                                    else:
                                        target_id = imports.get(called_name, called_name)
                                        result.edges.append(Edge(
                                            source_id=method_id,
                                            target_id=target_id,
                                            edge_type=EdgeType.CALLS,
                                            line=getattr(call, "lineno", item.lineno)
                                        ))

            elif isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
                func_id = f"{file_path}::{stmt.name}"
                doc = ast.get_docstring(stmt)
                route_info = self._extract_http_route(stmt.decorator_list)
                if route_info:
                    http_m, route_path = route_info
                    doc = f"🌐 HTTP: [{http_m}] {route_path}\n" + (doc or "")
                    route_id = f"http://{http_m.lower()}:{route_path}"
                    route_node = Node(
                        id=route_id,
                        name=f"🌐 {http_m} {route_path}",
                        symbol_type=SymbolType.INTERFACE,
                        file_path=file_path,
                        line=stmt.lineno,
                        docstring=f"Endpoint HTTP: {http_m} {route_path}"
                    )
                    result.nodes.append(route_node)
                    result.edges.append(Edge(source_id=file_node_id, target_id=route_id, edge_type=EdgeType.USES, line=stmt.lineno))
                    result.edges.append(Edge(source_id=route_id, target_id=func_id, edge_type=EdgeType.CALLS, line=stmt.lineno, description="HTTP Handler"))

                func_node = Node(
                    id=func_id,
                    name=stmt.name,
                    symbol_type=SymbolType.FUNCTION,
                    file_path=file_path,
                    line=stmt.lineno,
                    docstring=doc
                )
                result.nodes.append(func_node)
                result.edges.append(Edge(source_id=file_node_id, target_id=func_id, edge_type=EdgeType.USES, line=stmt.lineno))

        return result

    def _extract_http_route(self, decorator_list: List[ast.expr]) -> Optional[Tuple[str, str]]:
        """Extrai método HTTP e rota de decoradores (FastAPI, Flask, etc.)."""
        for dec in decorator_list:
            if isinstance(dec, ast.Call):
                func_name = self._resolve_call_name(dec.func) or ""
                parts = func_name.split(".")
                method = parts[-1].upper() if len(parts) > 1 else ""
                if method in {"GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"}:
                    if dec.args and isinstance(dec.args[0], ast.Constant) and isinstance(dec.args[0].value, str):
                        return (method, dec.args[0].value)
                elif method == "ROUTE":
                    route_path = dec.args[0].value if dec.args and isinstance(dec.args[0], ast.Constant) and isinstance(dec.args[0].value, str) else "/"
                    http_m = "GET"
                    for kw in dec.keywords:
                        if kw.arg == "methods" and isinstance(kw.value, (ast.List, ast.Tuple)):
                            for elt in kw.value.elts:
                                if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                                    http_m = elt.value.upper()
                                    break
                    return (http_m, route_path)
        return None

    def _resolve_call_name(self, node: ast.AST) -> Optional[str]:
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            val = self._resolve_call_name(node.value)
            return f"{val}.{node.attr}" if val else node.attr
        return None
