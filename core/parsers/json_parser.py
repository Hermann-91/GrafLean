"""
Parser estático para arquivos JSON (.json).
Extrai nós de arquivo, scripts (npm/composer), dependências declaradas e chaves de configuração.
"""

import os
import json
from typing import Dict, Any
from core.models import Node, Edge, SymbolType, EdgeType
from core.parsers.base import BaseParser, ParseResult


class JSONParser(BaseParser):
    """Extrai informações estruturais de manifestos e configurações JSON."""

    def parse_source(self, code: str, file_path: str) -> ParseResult:
        result = ParseResult()
        file_name = os.path.basename(file_path)
        file_id = f"file://{file_path}"

        try:
            data = json.loads(code)
        except Exception:
            # Em caso de JSON com comentários ou malformado, cria apenas o nó do arquivo
            result.nodes.append(Node(
                id=file_id,
                name=file_name,
                symbol_type=SymbolType.FILE,
                file_path=file_path,
                line=1,
                docstring=f"Arquivo JSON ({file_name})"
            ))
            return result

        docstring = f"Configuração JSON ({file_name})"
        if isinstance(data, dict):
            pkg_name = data.get("name")
            pkg_version = data.get("version")
            if pkg_name:
                docstring = f"Pacote: {pkg_name} (v{pkg_version})" if pkg_version else f"Pacote: {pkg_name}"

        file_node = Node(
            id=file_id,
            name=file_name,
            symbol_type=SymbolType.FILE,
            file_path=file_path,
            line=1,
            docstring=docstring
        )
        result.nodes.append(file_node)

        if not isinstance(data, dict):
            return result

        # 1. Extrai scripts (ex: package.json ou composer.json)
        scripts = data.get("scripts", {})
        if isinstance(scripts, dict):
            for script_name, script_cmd in scripts.items():
                script_id = f"{file_id}::script::{script_name}"
                cmd_str = str(script_cmd)
                script_node = Node(
                    id=script_id,
                    name=f"npm run {script_name}",
                    symbol_type=SymbolType.FUNCTION,
                    file_path=file_path,
                    line=1,
                    docstring=f"Comando: {cmd_str}"
                )
                result.nodes.append(script_node)
                result.edges.append(Edge(source_id=file_id, target_id=script_id, edge_type=EdgeType.USES))

        # 2. Extrai dependências declaradas (package.json / composer.json)
        dep_sections = ["dependencies", "devDependencies", "require", "require-dev", "peerDependencies"]
        for section in dep_sections:
            deps = data.get(section, {})
            if isinstance(deps, dict):
                for dep_name, version in deps.items():
                    # Ignora dependências da linguagem (ex: 'php', 'ext-*')
                    if dep_name.lower() == "php" or dep_name.startswith("ext-"):
                        continue
                    result.edges.append(Edge(
                        source_id=file_id,
                        target_id=dep_name,
                        edge_type=EdgeType.USES,
                        description=f"{section}: {version}"
                    ))

        # 3. Para arquivos de configuração gerais (ex: tsconfig, settings)
        if not scripts and not any(k in data for k in dep_sections):
            for key in list(data.keys())[:15]:
                val = data[key]
                val_type = type(val).__name__
                key_id = f"{file_id}::{key}"
                key_node = Node(
                    id=key_id,
                    name=key,
                    symbol_type=SymbolType.FUNCTION,
                    file_path=file_path,
                    line=1,
                    docstring=f"Chave de Configuração [{val_type}]"
                )
                result.nodes.append(key_node)
                result.edges.append(Edge(source_id=file_id, target_id=key_id, edge_type=EdgeType.USES))

        return result
