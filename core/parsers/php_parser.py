"""
Parser estático para PHP 8+.
Extrai classes, interfaces, traits, métodos, injeções de dependência,
chamadas e cláusulas 'use' sem depender do binário PHP externo.
"""

import re
from typing import List, Dict, Optional, Tuple
from core.models import Node, Edge, SymbolType, EdgeType
from core.parsers.base import BaseParser, ParseResult


class PHPParser(BaseParser):
    # Expressões regulares otimizadas para PHP moderno
    RE_NAMESPACE = re.compile(r"^\s*namespace\s+([^;]+);", re.MULTILINE)
    RE_USE = re.compile(r"^\s*use\s+([^;]+);", re.MULTILINE)
    RE_CLASS = re.compile(
        r"(?P<doc>/\*\*[\s\S]*?\*/\s*)?"
        r"(?P<abstract>abstract\s+)?(?P<final>final\s+)?"
        r"(?P<type>class|interface|trait)\s+(?P<name>[a-zA-Z0-9_]+)"
        r"(?:\s+extends\s+(?P<extends>[a-zA-Z0-9_\\]+))?"
        r"(?:\s+implements\s+(?P<implements>[a-zA-Z0-9_\\,\s]+))?",
        re.MULTILINE
    )
    RE_METHOD = re.compile(
        r"(?P<doc>/\*\*[\s\S]*?\*/\s*)?"
        r"(?P<visibility>public|protected|private)?\s+"
        r"(?P<static>static\s+)?"
        r"function\s+(?P<name>[a-zA-Z0-9_]+)\s*\((?P<params>[^)]*)\)",
        re.MULTILINE
    )
    RE_CALL_THIS = re.compile(r"\$this->(?P<prop>[a-zA-Z0-9_]+)->(?P<method>[a-zA-Z0-9_]+)\(")
    RE_CALL_STATIC = re.compile(r"(?P<class>[a-zA-Z0-9_]+)::(?P<method>[a-zA-Z0-9_]+)\(")
    RE_CALL_NEW = re.compile(r"new\s+(?P<class>[a-zA-Z0-9_]+)\(")
    RE_ROUTE = re.compile(
        r"Route::(?P<method>get|post|put|delete|patch|options|any)\s*\(\s*['\"](?P<path>[^'\"]+)['\"]\s*,\s*(?:\[(?P<controller>[a-zA-Z0-9_\\]+)::class,\s*['\"](?P<action>[a-zA-Z0-9_]+)['\"]\]|['\"](?P<controller_str>[a-zA-Z0-9_\\]+)@(?P<action_str>[a-zA-Z0-9_]+)['\"]|function)",
        re.MULTILINE | re.IGNORECASE
    )

    def parse_source(self, code: str, file_path: str) -> ParseResult:
        result = ParseResult()
        lines = code.splitlines()

        # 1. Extração do Namespace
        ns_match = self.RE_NAMESPACE.search(code)
        namespace = ns_match.group(1).strip() if ns_match else ""

        # 2. Extração de Cláusulas 'use' (Imports)
        uses: Dict[str, str] = {}  # alias/short_name -> FQCN
        for m in self.RE_USE.finditer(code):
            raw_use = m.group(1).strip()
            if " as " in raw_use:
                fqcn, alias = raw_use.split(" as ")
                uses[alias.strip()] = fqcn.strip()
            else:
                short_name = raw_use.split("\\")[-1]
                uses[short_name] = raw_use

        # Nó representativo do Arquivo
        file_node_id = f"file://{file_path}"
        file_node = Node(
            id=file_node_id,
            name=file_path.split("/")[-1],
            symbol_type=SymbolType.FILE,
            file_path=file_path,
            line=1,
            metadata={"namespace": namespace, "imports": list(uses.values())}
        )
        result.nodes.append(file_node)

        # 3. Extração de Classes / Interfaces
        fqcn = None
        for m in self.RE_CLASS.finditer(code):
            start_pos = m.start()
            line_no = code[:start_pos].count("\n") + 1
            type_str = m.group("type")
            name = m.group("name")
            extends = m.group("extends")
            implements_str = m.group("implements")
            raw_doc = m.group("doc")
            docstring = self._clean_docstring(raw_doc) if raw_doc else None

            symbol_type = SymbolType.INTERFACE if type_str == "interface" else (
                SymbolType.TRAIT if type_str == "trait" else SymbolType.CLASS
            )

            fqcn = f"{namespace}\\{name}" if namespace else name
            class_node = Node(
                id=fqcn,
                name=name,
                symbol_type=symbol_type,
                file_path=file_path,
                line=line_no,
                docstring=docstring,
                metadata={
                    "namespace": namespace,
                    "extends": extends,
                    "implements": [i.strip() for i in implements_str.split(",")] if implements_str else []
                }
            )
            result.nodes.append(class_node)
            # Aresta: Arquivo contém a Classe
            result.edges.append(Edge(source_id=file_node_id, target_id=fqcn, edge_type=EdgeType.USES, line=line_no))

            # Arestas de Herança
            if extends:
                target_fqcn = self._resolve_fqcn(extends, namespace, uses)
                result.edges.append(Edge(source_id=fqcn, target_id=target_fqcn, edge_type=EdgeType.INHERITS, line=line_no))

            # Arestas de Implementação
            if implements_str:
                for iface in implements_str.split(","):
                    iface_clean = iface.strip()
                    if iface_clean:
                        target_fqcn = self._resolve_fqcn(iface_clean, namespace, uses)
                        result.edges.append(Edge(source_id=fqcn, target_id=target_fqcn, edge_type=EdgeType.IMPLEMENTS, line=line_no))

        # 4. Extração de Métodos e Injeções
        current_class_fqcn = fqcn
        injected_properties: Dict[str, str] = {}  # prop_name -> type_name

        for m in self.RE_METHOD.finditer(code):
            start_pos = m.start()
            line_no = code[:start_pos].count("\n") + 1
            method_name = m.group("name")
            params = m.group("params")
            raw_doc = m.group("doc")
            visibility = m.group("visibility") or "public"
            docstring = self._clean_docstring(raw_doc) if raw_doc else None

            method_id = f"{current_class_fqcn}::{method_name}" if current_class_fqcn else method_name
            method_node = Node(
                id=method_id,
                name=method_name,
                symbol_type=SymbolType.METHOD,
                file_path=file_path,
                line=line_no,
                docstring=docstring,
                metadata={"visibility": visibility, "params": params.strip()}
            )
            result.nodes.append(method_node)

            if current_class_fqcn:
                result.edges.append(Edge(source_id=current_class_fqcn, target_id=method_id, edge_type=EdgeType.USES, line=line_no))

            # Detecta injeção de dependência no __construct
            if method_name == "__construct" and params and current_class_fqcn:
                for param in params.split(","):
                    param_clean = param.strip()
                    # Exemplo PHP 8: private GatewayInterface $gateway
                    parts = param_clean.split()
                    if len(parts) >= 2:
                        var_name = [p for p in parts if p.startswith("$")]
                        type_candidates = [p for p in parts if not p.startswith("$") and p not in ("public", "protected", "private", "readonly")]
                        if var_name and type_candidates:
                            p_name = var_name[0].lstrip("$")
                            p_type = type_candidates[-1]
                            injected_properties[p_name] = p_type
                            dep_fqcn = self._resolve_fqcn(p_type, namespace, uses)
                            result.edges.append(Edge(
                                source_id=current_class_fqcn,
                                target_id=dep_fqcn,
                                edge_type=EdgeType.INJECTS,
                                line=line_no,
                                description=f"Injetado via construtor: ${p_name}"
                            ))

        # 5. Extração de Chamadas de Métodos ($this->prop->metodo, Class::metodo, new Class)
        for m in self.RE_CALL_THIS.finditer(code):
            line_no = code[:m.start()].count("\n") + 1
            prop = m.group("prop")
            called_method = m.group("method")
            if prop in injected_properties and current_class_fqcn:
                dep_type = injected_properties[prop]
                dep_fqcn = self._resolve_fqcn(dep_type, namespace, uses)
                target_method_id = f"{dep_fqcn}::{called_method}"
                result.edges.append(Edge(
                    source_id=current_class_fqcn,
                    target_id=target_method_id,
                    edge_type=EdgeType.CALLS,
                    line=line_no,
                    description=f"Chamada via ${prop}->{called_method}()"
                ))

        for m in self.RE_CALL_STATIC.finditer(code):
            line_no = code[:m.start()].count("\n") + 1
            cls_name = m.group("class")
            called_method = m.group("method")
            if cls_name not in ("self", "parent", "static") and current_class_fqcn:
                dep_fqcn = self._resolve_fqcn(cls_name, namespace, uses)
                result.edges.append(Edge(
                    source_id=current_class_fqcn,
                    target_id=f"{dep_fqcn}::{called_method}",
                    edge_type=EdgeType.CALLS,
                    line=line_no,
                    description=f"Chamada estática {cls_name}::{called_method}()"
                ))

        for m in self.RE_CALL_NEW.finditer(code):
            line_no = code[:m.start()].count("\n") + 1
            cls_name = m.group("class")
            if current_class_fqcn:
                dep_fqcn = self._resolve_fqcn(cls_name, namespace, uses)
                result.edges.append(Edge(
                    source_id=current_class_fqcn,
                    target_id=dep_fqcn,
                    edge_type=EdgeType.CALLS,
                    line=line_no,
                    description=f"Instanciação new {cls_name}()"
                ))
        # 6. Rotas HTTP (Laravel / Lumen)
        for m in self.RE_ROUTE.finditer(code):
            line_no = code[:m.start()].count("\n") + 1
            http_m = m.group("method").upper()
            route_path = m.group("path")
            route_id = f"http://{http_m.lower()}:{route_path}"
            route_node = Node(
                id=route_id,
                name=f"🌐 {http_m} {route_path}",
                symbol_type=SymbolType.INTERFACE,
                file_path=file_path,
                line=line_no,
                docstring=f"Rota HTTP Laravel: {http_m} {route_path}"
            )
            result.nodes.append(route_node)
            result.edges.append(Edge(source_id=file_node_id, target_id=route_id, edge_type=EdgeType.USES, line=line_no))

            ctrl = m.group("controller") or m.group("controller_str")
            action = m.group("action") or m.group("action_str")
            if ctrl and action:
                ctrl_fqcn = self._resolve_fqcn(ctrl, namespace, uses)
                result.edges.append(Edge(
                    source_id=route_id,
                    target_id=f"{ctrl_fqcn}::{action}",
                    edge_type=EdgeType.CALLS,
                    line=line_no,
                    description=f"HTTP Action {ctrl}@{action}"
                ))

        return result

    def _resolve_fqcn(self, type_name: str, current_namespace: str, uses: Dict[str, str]) -> str:
        """Resolve o nome qualificado completo da classe (FQCN)."""
        type_name = type_name.lstrip("\\")
        if type_name in uses:
            return uses[type_name]
        if current_namespace:
            return f"{current_namespace}\\{type_name}"
        return type_name

    def _clean_docstring(self, raw: str) -> str:
        """Limpa blocos de comentário /** ... */ retornando texto conciso."""
        lines = []
        for line in raw.splitlines():
            cleaned = re.sub(r"^\s*(/\*\*|\*/|\*)\s?", "", line).strip()
            if cleaned and not cleaned.startswith("@"):
                lines.append(cleaned)
        return " ".join(lines)
