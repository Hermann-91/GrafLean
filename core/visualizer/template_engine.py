"""
Módulo do Motor de Templates e Cache de Assets do Mapa Arquitetural.
Carrega os assets web uma única vez em memória e monta o HTML final com
altíssima performance (zero overhead de I/O em tempo de execução).
"""

import os
from typing import Optional
from core.visualizer.data_serializer import SerializedGraphData


class TemplateEngine:
    """Carrega assets com cache em memória e renderiza o HTML autocontido."""

    def __init__(self, assets_dir: Optional[str] = None):
        if assets_dir is None:
            assets_dir = os.path.join(os.path.dirname(__file__), "assets")
        self.assets_dir = assets_dir
        self._template: Optional[str] = None
        self._styles: Optional[str] = None
        self._scripts: Optional[str] = None

    def _load_assets(self) -> None:
        """Carrega os arquivos de template, estilo e scripts se ainda não estiverem em memória."""
        if self._template is None:
            template_path = os.path.join(self.assets_dir, "templates", "workspace.html")
            with open(template_path, "r", encoding="utf-8") as f:
                self._template = f.read()

        if self._styles is None:
            styles_path = os.path.join(self.assets_dir, "styles", "style.css")
            with open(styles_path, "r", encoding="utf-8") as f:
                self._styles = f.read()

        if self._scripts is None:
            scripts_path = os.path.join(self.assets_dir, "scripts", "app.js")
            with open(scripts_path, "r", encoding="utf-8") as f:
                self._scripts = f.read()

    def clear_cache(self) -> None:
        """Limpa o cache em memória caso os assets precisem ser recarregados."""
        self._template = None
        self._styles = None
        self._scripts = None

    def render(self, data: SerializedGraphData) -> str:
        """Interpola os dados serializados no esqueleto HTML e retorna a página completa."""
        self._load_assets()

        data_scripts = (
            f'<script type="application/json" id="data-nodes">{data.nodes_json}</script>\n'
            f'    <script type="application/json" id="data-edges">{data.edges_json}</script>\n'
            f'    <script type="application/json" id="data-tree">{data.tree_json}</script>\n'
            f'    <script type="application/json" id="data-sources">{data.sources_json}</script>'
        )

        return (
            self._template
            .replace("{{PROJECT_NAME}}", data.project_name)
            .replace("/*{{STYLES}}*/", self._styles or "")
            .replace("<!--{{DATA_SCRIPTS}}-->", data_scripts)
            .replace("/*{{SCRIPTS}}*/", self._scripts or "")
        )
