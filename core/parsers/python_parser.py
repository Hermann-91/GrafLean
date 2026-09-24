"""
Parser estático para Python utilizando a biblioteca padrão 'ast'.
Extrai classes, funções, métodos, herança, imports e chamadas com precisão 100% determinística.
"""

import ast
from typing import Dict, List, Optional
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
                    if isinstance(item, ast.FunctionDef):
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

            elif isinstance(stmt, ast.FunctionDef):
                func_id = f"{file_path}::{stmt.name}"
                doc = ast.get_docstring(stmt)
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

    def _resolve_call_name(self, node: ast.AST) -> Optional[str]:
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            val = self._resolve_call_name(node.value)
            return f"{val}.{node.attr}" if val else node.attr
        return None
