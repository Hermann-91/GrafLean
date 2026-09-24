"""
Sublime Architecture Lens — Plugin Principal para Sublime Text 3 e 4.
Exibe informações arquiteturais de classes, métodos, funções e arquivos via on_hover.
"""

import os
import sys

# Garante que o pacote core seja importável dentro do ambiente do Sublime Text
plugin_dir = os.path.dirname(os.path.abspath(__file__))
if plugin_dir not in sys.path:
    sys.path.insert(0, plugin_dir)

try:
    import sublime
    import sublime_plugin
except ImportError:
    sublime = None
    sublime_plugin = object

from core.graph import ProjectGraph
from core.models import SymbolType


# Cache global de grafos de projetos em memória (indexado por root_dir)
GLOBAL_GRAPHS = {}


def get_project_root(file_path):
    """Encontra a raiz do projeto baseando-se em marcadores comuns (.git, composer.json, package.json)."""
    current = os.path.dirname(os.path.abspath(file_path))
    markers = [".git", "composer.json", "package.json", "pyproject.toml", ".arch_graph.json"]
    while current and current != os.path.dirname(current):
        for marker in markers:
            if os.path.exists(os.path.join(current, marker)):
                return current
        current = os.path.dirname(current)
    return os.path.dirname(os.path.abspath(file_path))


class ArchitectureLensListener(sublime_plugin.ViewEventListener if sublime else object):
    def on_hover(self, point, hover_zone):
        if not sublime or hover_zone != sublime.HOVER_TEXT:
            return

        view = self.view
        file_path = view.file_name()
        if not file_path:
            return

        # Obtém a palavra sob o cursor do mouse
        word_region = view.word(point)
        symbol_name = view.substr(word_region).strip()
        if not symbol_name or len(symbol_name) < 2:
            return

        root_dir = get_project_root(file_path)
        graph = GLOBAL_GRAPHS.get(root_dir)

        # Se não houver grafo em cache, tenta carregar o .arch_graph.json existente
        if not graph:
            cached_json = os.path.join(root_dir, ".arch_graph.json")
            if os.path.exists(cached_json):
                try:
                    graph = ProjectGraph.load_from_file(cached_json)
                    GLOBAL_GRAPHS[root_dir] = graph
                except Exception:
                    graph = None

        if not graph:
            return

        # Busca em O(1) pelo símbolo
        node = graph.find_symbol(symbol_name, file_path)
        if not node:
            return

        # Coleta conexões e métricas
        inbound = graph.analyzer.get_inbound_callers(node.id) if graph.analyzer else []
        outbound = graph.analyzer.get_outbound_dependencies(node.id) if graph.analyzer else []

        html_content = self.render_popup_html(node, inbound, outbound, graph)
        view.show_popup(
            html_content,
            flags=sublime.HIDE_ON_MOUSE_MOVE_AWAY,
            location=point,
            max_width=650,
            on_navigate=self.on_navigate
        )

    def on_navigate(self, href):
        """Gerencia os cliques em links dentro do pop-up para navegação rápida."""
        if not sublime or not href.startswith("open:"):
            return

        target = href[len("open:"):]
        parts = target.split(":")
        file_target = parts[0]
        line_target = parts[1] if len(parts) > 1 else "1"

        if os.path.exists(file_target):
            sublime.active_window().open_file(f"{file_target}:{line_target}", sublime.ENCODED_POSITION)

    def render_popup_html(self, node, inbound, outbound, graph):
        """Monta o mini-HTML estilizado com CSS dark mode elegante."""
        badge_color = {
            SymbolType.CLASS: "#89b4fa",       # Azul
            SymbolType.INTERFACE: "#b4befe",   # Lavanda
            SymbolType.METHOD: "#a6e3a1",      # Verde
            SymbolType.FUNCTION: "#94e2d5",    # Ciano
            SymbolType.FILE: "#f9e2af",        # Amarelo
        }.get(node.symbol_type, "#cdd6f4")

        doc_html = f"<div class='doc'>{node.docstring}</div>" if node.docstring else ""

        # Métricas
        m = node.metrics
        instability_label = "Estável" if m.instability <= 0.3 else ("Equilibrado" if m.instability <= 0.7 else "Instável")
        metrics_html = f"""
        <div class='metrics'>
            <span class='badge metric'>Ca: {m.afferent_coupling}</span>
            <span class='badge metric'>Ce: {m.efferent_coupling}</span>
            <span class='badge metric'>Instabilidade: {m.instability} ({instability_label})</span>
            {"<span class='badge deep'>Módulo Profundo</span>" if m.is_deep_module else ""}
            {"<span class='badge cycle'>⚠️ Ciclo Detectado</span>" if m.has_cycles else ""}
        </div>
        """

        # Inbound (Quem chama)
        inbound_items = []
        for caller_id in inbound[:5]:
            caller_node = graph.nodes.get(caller_id)
            if caller_node:
                link = f"open:{caller_node.file_path}:{caller_node.line}"
                inbound_items.append(f"<li><a href='{link}'>{caller_node.name}</a> <span class='dim'>({caller_node.symbol_type.value})</span></li>")
            else:
                inbound_items.append(f"<li><span class='dim'>{caller_id}</span></li>")
        inbound_html = f"<div class='section'><b>📥 Chamado por:</b><ul>{''.join(inbound_items)}</ul></div>" if inbound_items else ""

        # Outbound (Do que depende)
        outbound_items = []
        for dep_id in outbound[:5]:
            dep_node = graph.nodes.get(dep_id)
            if dep_node:
                link = f"open:{dep_node.file_path}:{dep_node.line}"
                outbound_items.append(f"<li><a href='{link}'>{dep_node.name}</a> <span class='dim'>({dep_node.symbol_type.value})</span></li>")
            else:
                outbound_items.append(f"<li><span class='dim'>{dep_id}</span></li>")
        outbound_html = f"<div class='section'><b>📤 Depende de:</b><ul>{''.join(outbound_items)}</ul></div>" if outbound_items else ""

        return f"""
        <style>
            body {{ font-family: sans-serif; background-color: #1e1e2e; color: #cdd6f4; padding: 10px; font-size: 12px; }}
            .header {{ font-size: 13px; font-weight: bold; margin-bottom: 6px; }}
            .badge {{ padding: 2px 6px; border-radius: 4px; font-size: 10px; font-weight: bold; margin-right: 4px; color: #11111b; }}
            .metric {{ background-color: #45475a; color: #cdd6f4; }}
            .deep {{ background-color: #a6e3a1; color: #11111b; }}
            .cycle {{ background-color: #f38ba8; color: #11111b; }}
            .doc {{ color: #bac2de; font-style: italic; margin-bottom: 8px; border-left: 2px solid #89b4fa; padding-left: 6px; }}
            .metrics {{ margin-bottom: 8px; }}
            .section {{ margin-top: 6px; }}
            ul {{ margin: 3px 0 6px 15px; padding: 0; }}
            li {{ margin-bottom: 2px; }}
            a {{ color: #89b4fa; text-decoration: none; }}
            .dim {{ color: #6c7086; }}
        </style>
        <div>
            <div class='header'>
                <span class='badge' style='background-color: {badge_color};'>{node.symbol_type.value.upper()}</span>
                {node.name}
            </div>
            {doc_html}
            {metrics_html}
            {inbound_html}
            {outbound_html}
        </div>
        """


class ArchitectureLensIndexCommand(sublime_plugin.WindowCommand if sublime else object):
    """Comando para varrer e indexar a arquitetura do projeto aberto."""
    def run(self):
        if not sublime:
            return

        folders = self.window.folders()
        if not folders:
            sublime.status_message("⚠️ Nenhum projeto aberto para indexar.")
            return

        root_dir = folders[0]
        sublime.status_message("🔍 Indexando arquitetura do projeto...")
        sublime.set_timeout_async(lambda: self._index_async(root_dir), 10)

    def _index_async(self, root_dir):
        try:
            graph = ProjectGraph(root_dir)
            graph.scan_project()
            graph.save_to_file()
            GLOBAL_GRAPHS[root_dir] = graph
            sublime.status_message(f"✅ Arquitetura indexada: {len(graph.nodes)} nós, {len(graph.edges)} conexões!")
        except Exception as e:
            sublime.status_message(f"❌ Erro ao indexar arquitetura: {str(e)}")
