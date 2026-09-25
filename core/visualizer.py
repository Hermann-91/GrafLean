"""
Módulo de Visualização Global Interativa (Mapa Arquitetural).
Gera um arquivo HTML autocontido com Workspace Integrado:
- Coluna de Navegação (Sub-abas: 📁 Árvore / ℹ️ Inspetor) com botão de ocultar/mostrar.
- Coluna Central: Editor de Código Monokai Sublime nativo com Gutter e Linha Ativa.
- Divisores Arrastáveis com o Mouse (Resizer Interno e Resizer Externo).
- Painel Direito: Grafo Top-Down Interativo em Vis.js com Sincronização Bidirecional.
"""

import os
import sys

# Garante importação do core tanto como pacote quanto script
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

import json
from typing import Optional
from core.graph import ProjectGraph
from core.models import SymbolType
from core.tree import ProjectTreeBuilder


class ArchitectureVisualizer:
    def __init__(self, graph: ProjectGraph):
        self.graph = graph

    def generate_html(self, output_path: Optional[str] = None) -> str:
        if not output_path:
            output_path = os.path.join(self.graph.root_dir, "arch_map.html")

        # 1. Prepara dados dos nós
        nodes_data = []
        for node in self.graph.nodes.values():
            m = node.metrics
            doc_text = f"💡 {node.docstring}" if node.docstring else "Sem descrição."
            tooltip = f"🏷️ {node.name} ({node.symbol_type.value.upper()})\n{doc_text}"

            level = 1 if node.symbol_type.value == "file" else (2 if node.symbol_type.value in ("class", "interface", "trait") else 3)
            parent_id = None
            if level == 2:
                parent_id = f"file://{node.file_path}"
            elif level == 3:
                parent_id = node.id.rsplit("::", 1)[0] if "::" in node.id else f"file://{node.file_path}"

            nodes_data.append({
                "id": node.id,
                "label": node.name,
                "title": tooltip,
                "type": node.symbol_type.value,
                "file": node.file_path,
                "line": node.line,
                "doc": node.docstring or "",
                "ca": m.afferent_coupling,
                "ce": m.efferent_coupling,
                "instability": m.instability,
                "deep": m.is_deep_module,
                "cycle": m.has_cycles,
                "git": node.git_status or "",
                "level": level,
                "parentId": parent_id
            })

        # 2. Prepara dados das arestas
        edges_data = []
        for edge in self.graph.edges:
            edges_data.append({
                "source": edge.source_id,
                "target": edge.target_id,
                "type": edge.edge_type.value,
                "desc": edge.description or ""
            })

        # 3. Prepara a árvore Composite do projeto
        tree_builder = ProjectTreeBuilder(self.graph.root_dir, self.graph.nodes)
        tree_data = tree_builder.build().to_dict()

        # 4. Coleta o conteúdo dos arquivos para visualização de código sob demanda
        file_sources = {}
        all_paths = set(node.file_path for node in self.graph.nodes.values() if node.file_path)
        if hasattr(tree_builder, "files_map"):
            for rel_f in tree_builder.files_map.keys():
                all_paths.add(os.path.join(self.graph.root_dir, rel_f))

        for f_path in all_paths:
            if os.path.isfile(f_path):
                try:
                    if os.path.getsize(f_path) <= 500 * 1024:
                        with open(f_path, "r", encoding="utf-8", errors="replace") as f:
                            file_sources[f_path] = f.read()
                    else:
                        file_sources[f_path] = "<!-- Arquivo excede 500KB para exibição inline -->"
                except Exception:
                    file_sources[f_path] = ""

        def safe_json(data) -> str:
            # Escapa < e > como unicode \u003c e \u003e para garantir conformidade estrita com RFC 8259 (JSON)
            # e impedir que qualquer tag HTML/JS (ex: </script>, <!--) interfira no parser do navegador.
            return json.dumps(data, ensure_ascii=False).replace("<", "\\u003c").replace(">", "\\u003e")

        nodes_json = safe_json(nodes_data)
        edges_json = safe_json(edges_data)
        tree_json = safe_json(tree_data)
        sources_json = safe_json(file_sources)
        project_name = os.path.basename(os.path.abspath(self.graph.root_dir)) or "GrafLean"

        html_template = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{project_name} — GrafLean</title>
    <!-- Vis.js para Renderização de Grafo -->
    <script src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
    
    <!-- Highlight.js: Motor de Sintaxe Universal (Suporte Nativo a PHP, Python, JS, TS) -->
    <script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/highlight.min.js"></script>

    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        /* Scrollbar Escuro e Elegante (Estilo Sublime) */
        * {{
            scrollbar-width: thin;
            scrollbar-color: #3e3d32 #1e1f1c;
        }}
        ::-webkit-scrollbar {{
            width: 8px;
            height: 8px;
        }}
        ::-webkit-scrollbar-track {{
            background: #1e1f1c;
        }}
        ::-webkit-scrollbar-thumb {{
            background: #3e3d32;
            border-radius: 4px;
        }}
        ::-webkit-scrollbar-thumb:hover {{
            background: #57564b;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", sans-serif;
            background-color: #11111b;
            color: #cdd6f4;
            display: flex;
            height: 100vh;
            overflow: hidden;
        }}
        
        /* Sidebar Principal / Workspace */
        #sidebar {{
            width: 580px;
            min-width: 380px;
            max-width: 90vw;
            background: #11111b;
            border-right: 1px solid rgba(69, 71, 90, 0.4);
            display: flex;
            flex-direction: column;
            z-index: 100;
            box-shadow: 4px 0 24px rgba(0, 0, 0, 0.35);
            transition: margin-left 0.25s ease;
            position: relative;
        }}
        #sidebar.collapsed {{
            margin-left: -100%;
        }}
        
        /* Divisor Arrastável Externo com o Mouse (Sidebar vs Grafo) */
        #resizer {{
            width: 7px;
            min-width: 7px;
            cursor: col-resize;
            background: rgba(69, 71, 90, 0.35);
            transition: background 0.15s ease, box-shadow 0.15s ease;
            z-index: 120;
            user-select: none;
        }}
        #resizer:hover, #resizer.dragging {{
            background: #89b4fa !important;
            box-shadow: 0 0 12px rgba(137, 180, 250, 0.8) !important;
        }}



        /* Header Superior do Workspace */
        .workspace-header {{
            padding: 12px 16px;
            border-bottom: 1px solid rgba(69, 71, 90, 0.25);
            display: flex;
            align-items: center;
            justify-content: space-between;
            background: #11111b;
        }}
        .brand-title {{
            font-size: 15px;
            font-weight: 700;
            color: #89b4fa;
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        .brand-sub {{
            font-size: 11px;
            color: #a6adc8;
        }}

        /* Layout Dividido: Coluna de Navegação + Coluna de Código */
        .workspace-body {{
            display: flex;
            flex: 1;
            height: 100%;
            overflow: hidden;
            position: relative;
        }}

        /* 1. Sub-Painel de Navegação (Árvore / Inspetor) */
        #nav-subpanel {{
            width: 270px;
            min-width: 180px;
            max-width: 480px;
            display: flex;
            flex-direction: column;
            background: #11111b;
            border-right: 1px solid rgba(69, 71, 90, 0.25);
            overflow: hidden;
            transition: width 0.2s ease;
        }}
        #nav-subpanel.hidden {{
            display: none !important;
        }}

        .nav-header-tabs {{
            display: flex;
            align-items: center;
            background: #11111b;
            border-bottom: 1px solid rgba(69, 71, 90, 0.25);
            padding: 4px 6px 0;
            gap: 4px;
        }}
        .nav-tab-btn {{
            flex: 1;
            padding: 7px 6px;
            background: transparent;
            border: none;
            border-bottom: 2px solid transparent;
            color: #a6adc8;
            font-size: 12.5px;
            font-weight: 600;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 4px;
            transition: all 0.15s ease;
            white-space: nowrap;
        }}
        .nav-tab-btn:hover {{
            color: #cdd6f4;
        }}
        .nav-tab-btn.active {{
            color: #89b4fa;
            border-bottom-color: #89b4fa;
            background: rgba(49, 50, 68, 0.35);
            border-radius: 4px 4px 0 0;
        }}
        .nav-toggle-btn {{
            padding: 4px 8px;
            background: transparent;
            border: none;
            color: #6c7086;
            cursor: pointer;
            font-size: 11px;
            border-radius: 4px;
        }}
        .nav-toggle-btn:hover {{
            background: #313244;
            color: #cdd6f4;
        }}

        .nav-content-pane {{
            flex: 1;
            overflow-y: auto;
            padding: 10px;
            display: flex;
            flex-direction: column;
            gap: 10px;
        }}

        /* Divisor Arrastável Interno (Árvore vs Código) */
        #internal-resizer {{
            width: 6px;
            min-width: 6px;
            cursor: col-resize;
            background: transparent;
            transition: background 0.15s ease;
            z-index: 110;
            user-select: none;
        }}
        #internal-resizer:hover, #internal-resizer.dragging {{
            background: #89b4fa !important;
            box-shadow: 0 0 8px rgba(137, 180, 250, 0.6) !important;
        }}

        /* 2. Sub-Painel de Código */
        #editor-subpanel {{
            flex: 1;
            display: flex;
            flex-direction: column;
            overflow: hidden;
            background-color: #000000;
        }}

        /* Search input */
        .search-box {{
            position: relative;
        }}
        .search-input {{
            width: 100%;
            padding: 8px 10px 8px 28px;
            background: #181825;
            border: 1px solid #45475a;
            border-radius: 6px;
            color: #cdd6f4;
            font-size: 11px;
            outline: none;
        }}
        .search-input:focus {{
            border-color: #89b4fa;
        }}
        .search-icon {{
            position: absolute;
            left: 8px;
            top: 50%;
            transform: translateY(-50%);
            font-size: 11px;
            opacity: 0.6;
        }}

        /* Project File Tree Styles (Composite Pattern) */
        .tree-container {{
            flex: 1;
            overflow-y: auto;
            padding-right: 2px;
        }}
        .tree-node {{
            user-select: none;
            font-size: 11px;
        }}
        .tree-row {{
            display: flex;
            align-items: center;
            gap: 5px;
            padding: 4px 6px;
            font-size: 13px;
            border-radius: 4px;
            cursor: pointer;
            transition: background 0.15s ease;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }}
        .tree-row:hover {{
            background: rgba(49, 50, 68, 0.5);
        }}
        .tree-row.active {{
            background: rgba(137, 180, 250, 0.2);
            border-left: 3px solid #89b4fa;
            color: #89b4fa;
        }}
        .tree-arrow {{
            font-size: 10px;
            width: 10px;
            display: inline-block;
            transition: transform 0.2s ease;
            color: #6c7086;
        }}
        .tree-arrow.open {{
            transform: rotate(90deg);
        }}
        .tree-children {{
            margin-left: 12px;
            border-left: 1px dashed rgba(69, 71, 90, 0.5);
            padding-left: 3px;
            display: none;
        }}
        .tree-children.open {{
            display: block;
        }}
        .tree-file-name {{
            font-weight: 700;
            color: #cdd6f4;
        }}
        .tree-symbol-row {{
            margin-left: 14px;
            font-size: 12.5px;
            padding: 3px 5px;
            display: flex;
            align-items: center;
            gap: 5px;
            color: #a6adc8;
            cursor: pointer;
            border-radius: 3px;
        }}
        .tree-symbol-row:hover {{
            background: rgba(49, 50, 68, 0.4);
            color: #cdd6f4;
        }}
        .tree-symbol-row.active {{
            background: rgba(166, 227, 161, 0.2);
            color: #a6e3a1;
            font-weight: 600;
        }}
        .badge-count {{
            font-size: 9px;
            padding: 1px 5px;
            background: #313244;
            border-radius: 8px;
            margin-left: auto;
            color: #a6adc8;
        }}

        /* Badges de Status Git */
        .git-badge {{
            font-size: 10px;
            font-weight: 700;
            padding: 1px 6px;
            border-radius: 4px;
            margin-left: 6px;
            display: inline-block;
            vertical-align: middle;
            letter-spacing: 0.3px;
        }}
        .git-badge-new {{
            background: rgba(166, 226, 46, 0.18);
            color: #a6e22e;
            border: 1px solid rgba(166, 226, 46, 0.45);
        }}
        .git-badge-mod {{
            background: rgba(253, 151, 31, 0.18);
            color: #fd971f;
            border: 1px solid rgba(253, 151, 31, 0.45);
        }}
        .git-badge-del {{
            background: rgba(249, 38, 114, 0.18);
            color: #f92672;
            border: 1px solid rgba(249, 38, 114, 0.45);
        }}

        /* Botões de Ações na Árvore */
        .tree-add-btn {{
            margin-left: auto;
            background: transparent;
            border: 1px solid rgba(166, 226, 46, 0.4);
            color: #a6e22e;
            border-radius: 50%;
            width: 17px;
            height: 17px;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            font-size: 13px;
            font-weight: bold;
            cursor: pointer;
            opacity: 0.6;
            transition: all 0.15s ease;
            line-height: 1;
            padding: 0;
            flex-shrink: 0;
        }}
        .tree-row:hover .tree-add-btn {{
            opacity: 1;
        }}
        .tree-add-btn:hover {{
            background: #a6e22e;
            color: #1e1e1e;
            box-shadow: 0 0 6px rgba(166, 226, 46, 0.8);
            transform: scale(1.15);
        }}
        .tree-more-btn {{
            margin-left: auto;
            background: transparent;
            border: none;
            color: #6c7086;
            font-size: 14px;
            cursor: pointer;
            padding: 0 4px;
            opacity: 0;
            transition: all 0.15s ease;
            flex-shrink: 0;
        }}
        .tree-row:hover .tree-more-btn {{
            opacity: 1;
        }}
        .tree-more-btn:hover {{
            color: #89b4fa;
            transform: scale(1.2);
        }}

        /* Menu de Contexto Flutuante */
        .tree-context-menu {{
            position: fixed;
            z-index: 99999;
            background: #181825;
            border: 1px solid #45475a;
            border-radius: 8px;
            box-shadow: 0 8px 24px rgba(0,0,0,0.6);
            padding: 6px;
            min-width: 170px;
            display: flex;
            flex-direction: column;
            gap: 3px;
        }}
        .tree-context-header {{
            font-size: 10.5px;
            font-weight: 600;
            color: #89b4fa;
            padding: 4px 8px 6px;
            border-bottom: 1px solid #313244;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            max-width: 220px;
        }}
        .tree-context-item {{
            display: flex;
            align-items: center;
            gap: 8px;
            background: transparent;
            border: none;
            color: #cdd6f4;
            font-size: 12px;
            padding: 6px 10px;
            border-radius: 4px;
            cursor: pointer;
            text-align: left;
            transition: background 0.15s ease, color 0.15s ease;
        }}
        .tree-context-item:hover {{
            background: rgba(137, 180, 250, 0.2);
            color: #89b4fa;
        }}
        .tree-context-item.danger:hover {{
            background: rgba(249, 38, 114, 0.2);
            color: #f92672;
        }}



        /* Inspector Details */
        #inspector-content {{
            display: flex;
            flex-direction: column;
            gap: 10px;
        }}
        .card {{
            background: #181825;
            padding: 12px;
            border-radius: 6px;
            border: 1px solid #313244;
        }}
        .card h3 {{
            font-size: 15px;
            color: #89b4fa;
            margin-bottom: 4px;
            word-break: break-all;
        }}
        .card-doc {{
            font-size: 13px;
            color: #a6adc8;
            font-style: italic;
            margin-bottom: 8px;
            line-height: 1.4;
        }}
        .metric-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 6px;
            margin-top: 4px;
        }}
        .metric-box {{
            background: #1e1e2e;
            padding: 6px 8px;
            border-radius: 4px;
            border: 1px solid #313244;
            font-size: 12px;
        }}
        .metric-val {{
            font-size: 17px;
            font-weight: bold;
            color: #89b4fa;
            margin-top: 2px;
        }}
        .connection-list {{
            max-height: 140px;
            overflow-y: auto;
            font-size: 12.5px;
            display: flex;
            flex-direction: column;
            gap: 4px;
            margin-top: 4px;
        }}
        .conn-item {{
            padding: 5px 8px;
            font-size: 13px;
            font-weight: 500;
            background: #1e1e2e;
            border-radius: 3px;
            border-left: 2px solid #89b4fa;
            cursor: pointer;
            word-break: break-all;
        }}
        .conn-item:hover {{
            background: #313244;
        }}

        /* ========================================================
           SUBSTÂNCIA E ESTILO SUBLIME TEXT MONOKAI (1:1 COM O SUBLIME)
           ======================================================== */
        .sublime-editor-window {{
            flex: 1;
            display: flex;
            flex-direction: column;
            background-color: #000000; /* Fundo Preto Absoluto */
            overflow: hidden;
            height: 100%;
        }}
        .sublime-tab-header {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            background: #0a0a0a;
            padding: 6px 12px;
            border-bottom: 1px solid #1a1a1a;
            font-size: 12px;
        }}
        .sublime-file-tab {{
            display: flex;
            align-items: center;
            gap: 8px;
            background: #000000;
            padding: 5px 12px;
            border-radius: 4px 4px 0 0;
            color: #f8f8f2;
            font-weight: 600;
            border: 1px solid #1a1a1a;
            border-bottom: none;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
            max-width: 320px;
        }}
        .sublime-toolbar-actions {{
            display: flex;
            gap: 6px;
        }}
        .sublime-btn {{
            padding: 4px 8px;
            background: #141414;
            border: 1px solid #282828;
            border-radius: 4px;
            color: #f8f8f2;
            font-size: 11px;
            cursor: pointer;
            transition: all 0.15s ease;
            text-decoration: none;
            display: flex;
            align-items: center;
            gap: 4px;
        }}
        .sublime-btn:hover {{
            background: #f92672;
            color: #fff;
            border-color: #f92672;
        }}
        .sublime-code-viewport {{
            flex: 1;
            overflow: auto;
            position: relative;
            background-color: #000000;
        }}
        #sublime-editor-textarea {{
            width: 100%;
            height: 100%;
            background-color: #000000;
            color: #f8f8f2;
            font-family: "Fira Code", "Cascadia Code", Consolas, "Courier New", monospace;
            font-size: 14px;
            line-height: 1.6;
            padding: 14px 18px;
            border: none;
            outline: none;
            resize: none;
            tab-size: 4;
            white-space: pre;
            overflow-wrap: normal;
            overflow-x: auto;
            box-sizing: border-box;
            display: none;
        }}

        /* Toast Notificação Moderna e Não Bloqueante */
        .graf-toast {{
            position: fixed;
            bottom: 24px;
            right: 24px;
            background: #1e1e2e;
            color: #cdd6f4;
            padding: 10px 18px;
            border-radius: 6px;
            border: 1px solid #a6e3a1;
            font-size: 13px;
            font-weight: 600;
            box-shadow: 0 8px 24px rgba(0,0,0,0.5);
            z-index: 999999;
            opacity: 0;
            transform: translateY(12px);
            transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
            pointer-events: none;
        }}
        .graf-toast.show {{
            opacity: 1;
            transform: translateY(0);
        }}
        .graf-toast.error {{
            border-color: #f38ba8;
            color: #f38ba8;
        }}

        /* Tabela com Gutter e Código 100% Monokai */
        .sublime-table {{
            width: 100%;
            border-collapse: collapse;
            font-family: "Fira Code", "Cascadia Code", Consolas, "Courier New", monospace;
            font-size: 14.5px;
            line-height: 1.6;
            color: #f8f8f2;
            background-color: #000000;
        }}
        .sublime-table td {{
            padding: 0;
            vertical-align: top;
        }}
        .sublime-gutter {{
            width: 48px;
            min-width: 48px;
            text-align: right;
            padding-right: 14px;
            color: #75715e; /* Cinza oficial do gutter do Sublime */
            user-select: none;
            border-right: 1px solid #1a1a1a;
            background-color: #000000;
        }}
        .sublime-code-cell {{
            padding-left: 14px;
            padding-right: 14px;
            white-space: pre;
            background-color: #000000;
        }}

        /* Linha Ativa no Sublime */
        tr.active-sublime-line {{
            background-color: rgba(255, 255, 255, 0.08) !important;
            outline: 1px solid rgba(255, 255, 255, 0.22) !important;
        }}
        tr.active-sublime-line .sublime-gutter {{
            color: #f8f8f2 !important;
            font-weight: bold;
            background-color: rgba(255, 255, 255, 0.08) !important;
        }}
        tr.active-sublime-line .sublime-code-cell {{
            background-color: rgba(255, 255, 255, 0.08) !important;
        }}

        /* Cores Oficiais Monokai Sublime dos Tokens */
        .hljs-keyword, .hljs-selector-tag, .hljs-tag {{ color: #f92672 !important; font-weight: 500; }} /* Rosa/Pink */
        .hljs-title.class_, .hljs-type, .hljs-built_in {{ color: #66d9ef !important; font-style: italic; }} /* Ciano */
        .hljs-title.function_, .hljs-function .hljs-title {{ color: #a6e22e !important; }} /* Verde Limão */
        .hljs-variable, .hljs-template-variable, .hljs-params {{ color: #fd971f !important; }} /* Laranja */
        .hljs-string {{ color: #e6db74 !important; }} /* Amarelo */
        .hljs-number, .hljs-literal {{ color: #ae81ff !important; }} /* Roxo */
        .hljs-comment, .hljs-quote {{ color: #75715e !important; font-style: italic; }} /* Cinza Comentário */
        .hljs-meta {{ color: #f8f8f2 !important; }}

        /* Barra de Status Inferior do Sublime Text */
        .sublime-statusbar {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            background: #0a0a0a;
            border-top: 1px solid #1a1a1a;
            padding: 4px 12px;
            font-size: 11px;
            color: #75715e;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        }}

        /* Main Network Canvas */
        #network {{
            flex: 1;
            height: 100%;
            background-color: #11111b;
        }}
        
        /* Footer status */
        .sidebar-footer {{
            padding: 6px 16px;
            border-top: 1px solid rgba(69, 71, 90, 0.25);
            font-size: 11px;
            color: #6c7086;
            display: flex;
            justify-content: space-between;
            background: #11111b;
        }}
    </style>
</head>
<body>
    <div id="sidebar">
        <!-- Header do Workspace -->
        <div class="workspace-header">
            <div style="display:flex; align-items:center; gap:8px;">
                <a href="/" class="sublime-btn" style="text-decoration:none; font-weight:700; color:#89b4fa; border-color:#45475a;" title="Ir para a Biblioteca de Projetos">
                    🏛️ GrafLean | ◀ Biblioteca
                </a>
                <span class="brand-sub" style="font-size:11px; color:#6c7086;">📁 {project_name}</span>
            </div>
            <div style="display:flex; gap:6px; align-items:center;">
                <button class="sublime-btn" id="btn-reopen-nav" onclick="toggleNavSubpanel()" style="display:none;" title="Mostrar Árvore/Inspetor">
                    📁 Navegador
                </button>
                <button class="sublime-btn" id="btn-reopen-code" onclick="toggleCodeSubpanel()" style="display:none;" title="Mostrar Editor de Código">
                    📄 Código
                </button>
                <button class="sublime-btn" id="btn-toggle-graph" onclick="toggleGraphPanel()" title="Alternar Visibilidade do Grafo">
                    🌐 Grafo
                </button>
                <button class="sublime-btn" id="btn-collapse-stage" onclick="handleStageCollapse()" style="background:#2a283e; border-color:#89b4fa; color:#b4befe; font-weight:bold; padding:4px 10px;" title="Recolher (1º Estágio: Código • 2º Estágio: Barra Lateral)">
                    ◀
                </button>
            </div>
        </div>

        <!-- Corpo Dividido: Árvore/Inspetor à esquerda + Código no centro -->
        <div class="workspace-body">
            <!-- 1. Sub-Painel de Navegação -->
            <div id="nav-subpanel">
                <div class="nav-header-tabs">
                    <button class="nav-tab-btn active" id="subtab-btn-tree" onclick="switchNavTab('tree')">📁 Árvore</button>
                    <button class="nav-tab-btn" id="subtab-btn-inspector" onclick="switchNavTab('inspector')">ℹ️ Inspetor</button>
                    <button class="nav-toggle-btn" onclick="toggleNavSubpanel()" title="Ocultar Painel Lateral">◀</button>
                </div>

                <!-- Sub-aba 1: Árvore de Arquivos -->
                <div class="nav-content-pane" id="nav-pane-tree">
                    <div class="search-box">
                        <span class="search-icon">🔍</span>
                        <input type="text" class="search-input" id="search" placeholder="Filtrar arquivos ou classes..." oninput="onSearchInput(this.value)">
                    </div>



                    <div class="tree-container" id="tree-root"></div>
                </div>

                <!-- Sub-aba 2: Inspetor de Métricas -->
                <div class="nav-content-pane" id="nav-pane-inspector" style="display: none;">
                    <div id="inspector-placeholder" style="color: #6c7086; font-size: 11px; text-align: center; margin-top: 30px;">
                        👈 Clique em qualquer arquivo ou símbolo na árvore ou no grafo para inspecionar métricas e conexões.
                    </div>
                    <div id="inspector-content" style="display: none;">
                        <div class="card">
                            <h3 id="det-title">-</h3>
                            <div id="det-git" style="margin-bottom:6px;"></div>
                            <p class="card-doc" id="det-doc"></p>
                            <div style="font-size: 11px; color: #89b4fa;" id="det-file">-</div>
                            <button class="sublime-btn" style="width: 100%; justify-content: center; margin-top: 10px; background: #1e1e2e; border-color: #89b4fa; color: #89b4fa; font-weight: 600;" onclick="copyAgentPrompt()">📋 Copiar Prompt para Agente</button>
                        </div>

                        <div class="card">
                            <b style="font-size: 11px; color: #cdd6f4;">⚖️ Métricas de Arquitetura Limpa:</b>
                            <div class="metric-grid">
                                <div class="metric-box">
                                    <div>Acoplamento Aferente (Ca)</div>
                                    <div class="metric-val" id="det-ca">0</div>
                                </div>
                                <div class="metric-box">
                                    <div>Acoplamento Eferente (Ce)</div>
                                    <div class="metric-val" id="det-ce">0</div>
                                </div>
                            </div>
                            <div style="margin-top: 6px; font-size: 11px;">
                                Instabilidade (I): <b id="det-inst" style="color: #fab387;">0.0</b>
                            </div>
                        </div>

                        <div class="card">
                            <b style="font-size: 11px; color: #a6e3a1;">📥 Chamado por (Inbound):</b>
                            <div class="connection-list" id="det-inbound"></div>
                        </div>

                        <div class="card">
                            <b style="font-size: 11px; color: #fab387;">📤 Depende de (Outbound):</b>
                            <div class="connection-list" id="det-outbound"></div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Divisor Arrastável Interno (Árvore vs Código) -->
            <div id="internal-resizer" title="Arraste para ajustar a largura da Árvore"></div>

            <!-- 2. Sub-Painel do Editor de Código Monokai Sublime -->
            <div id="editor-subpanel">
                <div class="sublime-editor-window">
                    <div class="sublime-tab-header">
                        <div class="sublime-file-tab">
                            <span>📄</span>
                            <span id="sublime-tab-filename">Nenhum arquivo</span>
                            <span onclick="toggleCodeSubpanel()" title="Recolher Editor de Código" style="cursor:pointer; opacity:0.6; margin-left:6px; font-size:11px;" onmouseover="this.style.opacity='1'" onmouseout="this.style.opacity='0.6'">✕</span>
                        </div>
                        <div class="sublime-toolbar-actions">
                            <button class="sublime-btn" id="btn-toggle-edit" onclick="toggleEditMode()" title="Alternar entre Leitura e Edição">✏️ Editar</button>
                            <button class="sublime-btn" id="btn-save-code" onclick="saveCurrentCode()" style="display:none; background:#a6e22e; color:#11111b; font-weight:700; border-color:#a6e22e;" title="Salvar Alterações no Disco (Ctrl+S)">💾 Salvar</button>
                            <button class="sublime-btn" onclick="copyCurrentCode()" title="Copiar Código">📋 Copiar</button>
                            <button class="sublime-btn" id="btn-collapse-code" onclick="toggleCodeSubpanel()" title="Recolher Editor de Código (Focar na Árvore e Grafo)">◀ Recolher</button>
                        </div>
                    </div>

                    <div class="sublime-code-viewport" id="code-viewport">
                        <div id="sublime-table-container">
                            <div style="padding: 20px; color: #75715e; font-family: monospace;">
                                // Clique em qualquer arquivo ou símbolo da árvore à esquerda para carregar o código...
                            </div>
                        </div>
                        <textarea id="sublime-editor-textarea" spellcheck="false" placeholder="Digite ou edite o conteúdo do arquivo aqui..."></textarea>
                    </div>

                    <div class="sublime-statusbar">
                        <span id="sublime-status-pos">Line 1, Column 1</span>
                        <span id="sublime-status-lang">UTF-8 | Plain Text</span>
                    </div>
                </div>
            </div>
        </div>

        <!-- Rodapé da Barra Lateral -->
        <div class="sidebar-footer">
            <span>{len(nodes_data)} nós</span>
            <span>{len(edges_data)} conexões</span>
        </div>
    </div>

    <!-- Divisor Arrastável Externo com o Mouse (Sidebar vs Grafo) -->
    <div id="resizer" title="Arraste com o mouse para redimensionar a barra lateral"></div>

    <button id="sidebar-reopen-btn" class="sublime-btn" onclick="toggleSidebar()" style="display:none; position:absolute; top:12px; left:12px; z-index:150; height:31px; padding:6px 11px; font-weight:bold; background:#1e1e2e; border:1px solid #45475a; color:#89b4fa;" title="Reabrir Barra Lateral">▶</button>

    <div id="network-container" style="flex:1; position:relative; height:100%; width:100%;">
        <!-- Barra de Ferramentas Flutuante do Grafo -->
        <div id="graph-toolbar" style="position:absolute; top:12px; left:16px; z-index:90; display:flex; gap:6px; background:rgba(22,23,27,0.85); backdrop-filter:blur(8px); padding:4px 8px; border-radius:8px; border:1px solid rgba(255,255,255,0.08); align-items:center;">
            <button class="sublime-btn" id="btn-reorganize" onclick="reorganizeGraph()" title="Reorganizar Layout do Grafo Suavemente">🔄 Reorganizar</button>
            <button class="sublime-btn" id="btn-physics" onclick="togglePhysics()" title="Alternar Física de Colisão">⚡ Física: Off</button>
            <button class="sublime-btn" id="btn-fit" onclick="resetGraphView()" title="Centralizar e Enquadrar Todos os Nós">🔍 Enquadrar</button>
            <button class="sublime-btn" id="btn-collapse-graph" onclick="toggleGraphPanel()" title="Recolher Grafo (Modo Código Tela Cheia)">▶ Ocultar Grafo</button>
            <span id="graph-nodes-count" style="font-size:11px; color:#a6adc8; align-self:center; margin-left:6px; font-weight:600;">-- nós</span>
        </div>
        <div id="network" style="width:100%; height:100%;"></div>
    </div>

    <!-- Dados Protegidos e Imunes a Conflito de Tags Internas -->
    <script type="application/json" id="data-nodes">{nodes_json}</script>
    <script type="application/json" id="data-edges">{edges_json}</script>
    <script type="application/json" id="data-tree">{tree_json}</script>
    <script type="application/json" id="data-sources">{sources_json}</script>

    <script>
        let rawNodes = JSON.parse(document.getElementById('data-nodes').textContent);
        let rawEdges = JSON.parse(document.getElementById('data-edges').textContent);
        let rawTree = JSON.parse(document.getElementById('data-tree').textContent);
        let rawFileSources = JSON.parse(document.getElementById('data-sources').textContent);
        let currentNavTab = 'tree';
        let isEditMode = false;
        let currentLoadedFilePath = null;
        let openFolders = new Set(JSON.parse(localStorage.getItem('graf_lens_open_folders') || '[""]'));

        function showToast(message, type = 'info') {{
            let toast = document.getElementById('graf-toast');
            if (!toast) {{
                toast = document.createElement('div');
                toast.id = 'graf-toast';
                toast.className = 'graf-toast';
                document.body.appendChild(toast);
            }}
            toast.className = 'graf-toast' + (type === 'error' ? ' error' : '');
            toast.innerText = message;
            toast.classList.add('show');
            clearTimeout(window.__graf_toast_timeout);
            window.__graf_toast_timeout = setTimeout(() => {{
                toast.classList.remove('show');
            }}, 2600);
        }}

        function applyLiveUpdate(data) {{
            if (!data) return;
            try {{
                if (data.tree) {{
                    rawTree = data.tree;
                    const treeRoot = document.getElementById('tree-root');
                    if (treeRoot) {{
                        treeRoot.innerHTML = '';
                        renderTree(rawTree, treeRoot);
                    }}
                }}
                if (data.sources) {{
                    rawFileSources = data.sources;
                }}
                if (data.nodes && (typeof nodes !== 'undefined' || window.nodes)) {{
                    const targetNodes = typeof nodes !== 'undefined' ? nodes : window.nodes;
                    rawNodes = data.nodes;
                    const currentIds = new Set(data.nodes.map(n => n.id));
                    rawNodes = data.nodes;
                    if (typeof allNodesMap !== 'undefined') {{
                        allNodesMap.clear();
                        rawNodes.forEach(n => allNodesMap.set(n.id, n));
                    }}
                    if (data.edges) rawEdges = data.edges;
                    if (typeof refreshGraphData === 'function') {{
                        refreshGraphData();
                    }} else {{
                        const existingIds = targetNodes.getIds();
                        const toRemove = existingIds.filter(id => !currentIds.has(id));
                        if (toRemove.length > 0) targetNodes.remove(toRemove);
                        targetNodes.update(data.nodes.map(n => formatVisNode(n)));
                    }}
                    if (typeof network !== 'undefined') network.redraw();
                }}
                if (data.edges && (typeof edges !== 'undefined' || window.edges)) {{
                    rawEdges = data.edges;
                    if (typeof refreshGraphData === 'function') {{
                        refreshGraphData();
                    }}
                    if (typeof network !== 'undefined') network.redraw();
                }}
                if (currentLoadedFilePath && !rawFileSources[currentLoadedFilePath]) {{
                    currentLoadedFilePath = null;
                    const textarea = document.getElementById('sublime-editor-textarea');
                    if (textarea) textarea.value = '';
                    const tableContainer = document.getElementById('sublime-table-container');
                    if (tableContainer) {{
                        tableContainer.innerHTML = '<div style="padding: 20px; color: #75715e; font-family: monospace;">// Nenhum arquivo selecionado</div>';
                    }}
                    const pathEl = document.getElementById('sublime-tab-path');
                    if (pathEl) pathEl.innerText = 'Nenhum arquivo selecionado';
                    const badgeEl = document.getElementById('sublime-git-badge');
                    if (badgeEl) badgeEl.innerHTML = '';
                }}
            }} catch (err) {{
                console.error("Erro ao aplicar live update:", err);
            }}
        }}

        async function fetchLiveUpdate() {{
            try {{
                const res = await fetch('/api/data');
                if (!res.ok) return;
                const json = await res.json();
                if (json.success && json.data) {{
                    applyLiveUpdate(json.data);
                }}
            }} catch (e) {{}}
        }}

        const colorMap = {{
            "class": "#89b4fa",
            "interface": "#b4befe",
            "method": "#a6e3a1",
            "function": "#94e2d5",
            "file": "#f9e2af"
        }};

        // 1. Vis.js Network Setup com Células Modulares e Física Pacificada
        const allNodesMap = new Map();
        rawNodes.forEach(n => allNodesMap.set(n.id, n));
        let physicsRunning = false;

        // Mapeia classes contidas em cada arquivo para rotulagem limpa unificada
        const fileClassesMap = new Map();
        rawNodes.filter(n => (n.type === "class" || n.type === "interface" || n.type === "trait") && n.parentId).forEach(c => {{
            if (!fileClassesMap.has(c.parentId)) fileClassesMap.set(c.parentId, []);
            fileClassesMap.get(c.parentId).push(c.label);
        }});

        function formatVisNode(n) {{
            const classes = fileClassesMap.get(n.id) || [];
            let label = "📁 " + n.label;
            if (classes.length === 1) {{
                label = "🏛️ " + classes[0] + "\\n📁 " + n.label;
            }} else if (classes.length > 1) {{
                label = "📁 " + n.label + "\\n(" + classes.length + " classes)";
            }}
            const hasClasses = classes.length > 0;
            return {{
                id: n.id,
                label: label,
                title: n.title + (classes.length ? "\\n🏛️ Classes: " + classes.join(", ") : ""),
                color: {{
                    background: hasClasses ? "#1e1e2e" : "#261c14",
                    border: n.git === "new" ? "#a6e22e" : (n.git === "modified" ? "#fd971f" : (hasClasses ? "#89b4fa" : "#fab387"))
                }},
                borderWidth: (n.git === "new" || n.git === "modified") ? 2.5 : 2,
                shape: "dot",
                size: hasClasses ? 15 : 11,
                shapeProperties: {{
                    borderDashes: false
                }},
                font: {{
                    color: hasClasses ? "#cdd6f4" : "#fab387",
                    size: 10,
                    bold: true,
                    vadjust: 0
                }}
            }};
        }}

        function getFilteredNodes() {{
            // No Grafo cada arquivo/módulo é um Nó Componente Único e Limpo
            return rawNodes
                .filter(n => n.type === "file")
                .map(n => formatVisNode(n));
        }}

        function resolveToGraphNodeId(id) {{
            if (!id) return null;
            let current = allNodesMap.get(id);
            if (!current) {{
                if (allNodesMap.has(`file://${{id}}`)) return `file://${{id}}`;
                return null;
            }}
            if (current.type === "file") return current.id;
            if (current.parentId && allNodesMap.has(current.parentId)) {{
                return resolveToGraphNodeId(current.parentId);
            }}
            if (current.file && allNodesMap.has(`file://${{current.file}}`)) {{
                return `file://${{current.file}}`;
            }}
            return null;
        }}

        const nodes = new vis.DataSet(getFilteredNodes());

        function getFilteredEdges() {{
            const graphNodeIds = new Set(nodes.getIds());
            const edgeAggregator = new Map();

            // Arestas de Dependência e Chamada entre Módulos
            rawEdges.forEach(e => {{
                const src = resolveToGraphNodeId(e.source);
                const tgt = resolveToGraphNodeId(e.target);
                if (src && tgt && src !== tgt && graphNodeIds.has(src) && graphNodeIds.has(tgt)) {{
                    const key = `${{src}}->${{tgt}}`;
                    if (!edgeAggregator.has(key)) {{
                        edgeAggregator.set(key, {{
                            id: key,
                            from: src,
                            to: tgt,
                            arrows: {{ to: {{ enabled: true, scaleFactor: 0.5 }} }},
                            color: {{
                                color: "rgba(108, 112, 134, 0.28)",
                                highlight: "#89b4fa",
                                hover: "#89b4fa",
                                inherit: false
                            }},
                            smooth: {{ enabled: true, type: "continuous", roundness: 0.35 }},
                            width: 1.0,
                            count: 1
                        }});
                    }} else {{
                        const existing = edgeAggregator.get(key);
                        if (existing.count) {{
                            existing.count++;
                            existing.width = Math.min(2.5, 1.0 + existing.count * 0.2);
                            existing.title = `${{existing.count}} conexões/chamadas`;
                        }}
                    }}
                }}
            }});

            return Array.from(edgeAggregator.values());
        }}

        const edges = new vis.DataSet(getFilteredEdges());

        const container = document.getElementById('network');
        const network = new vis.Network(container, {{ nodes, edges }}, {{
            interaction: {{ hover: true, tooltipDelay: 50, selectConnectedEdges: true, hideEdgesOnDrag: true }},
            edges: {{ selectionWidth: 2.2, hoverWidth: 1.5 }},
            physics: {{
                enabled: true,
                solver: "barnesHut",
                barnesHut: {{
                    gravitationalConstant: -6000,
                    centralGravity: 0.08,
                    springLength: 260,
                    springConstant: 0.015,
                    damping: 0.90,
                    avoidOverlap: 1.0
                }},
                stabilization: {{ iterations: 90, updateInterval: 10 }}
            }}
        }});
        window.nodes = nodes;
        window.edges = edges;
        window.network = network;

        network.once('stabilizationIterationsDone', () => {{
            network.setOptions({{ physics: {{ enabled: false }} }});
            physicsRunning = false;
            updatePhysicsUI();
            network.fit({{ animation: {{ duration: 400, easingFunction: 'easeInOutQuad' }} }});
        }});

        network.on('click', (params) => {{
            if (params.nodes && params.nodes.length > 0) {{
                Mediator.select(params.nodes[0], 'network');
            }}
        }});

        function refreshGraphData() {{
            const newNodes = getFilteredNodes();
            nodes.clear();
            nodes.add(newNodes);
            edges.clear();
            edges.add(getFilteredEdges());
            updateNodesCount();
        }}

        function reorganizeGraph() {{
            network.setOptions({{ physics: {{ enabled: true }} }});
            network.stabilize(90);
            setTimeout(() => {{
                network.setOptions({{ physics: {{ enabled: false }} }});
                physicsRunning = false;
                updatePhysicsUI();
                network.fit({{ animation: {{ duration: 400, easingFunction: 'easeInOutQuad' }} }});
            }}, 500);
        }}

        function resetGraphView() {{
            network.fit({{ animation: {{ duration: 400, easingFunction: 'easeInOutQuad' }} }});
        }}

        function togglePhysics() {{
            physicsRunning = !physicsRunning;
            network.setOptions({{ physics: {{ enabled: physicsRunning }} }});
            updatePhysicsUI();
        }}

        function updatePhysicsUI() {{
            const btn = document.getElementById('btn-physics');
            if (btn) {{
                btn.innerText = physicsRunning ? '⚡ Física: On' : '⚡ Física: Off';
                btn.style.color = physicsRunning ? '#a6e22e' : '';
                btn.style.borderColor = physicsRunning ? '#a6e22e' : '';
            }}
        }}

        function updateNodesCount() {{
            const badge = document.getElementById('graph-nodes-count');
            if (badge) badge.innerText = `${{nodes.length}} nós ativos`;
        }}
        updateNodesCount();

        // 2. Construtor da Tabela de Código Monokai Sublime
        function buildSublimeTable(highlightedHtml, targetLine) {{
            const lines = highlightedHtml.split('\\n');
            let openTags = [];
            let tableHtml = '<table class="sublime-table">';
            
            for (let i = 0; i < lines.length; i++) {{
                const lineNum = i + 1;
                const isTarget = (lineNum === targetLine);
                const lineContent = lines[i];
                
                const prefix = openTags.map(t => t.full).join('');
                
                const tagRegex = /<\\/?([a-z0-9_-]+)([^>]*)>/gi;
                let match;
                while ((match = tagRegex.exec(lineContent)) !== null) {{
                    const isClosing = match[0].startsWith('</');
                    const tagName = match[1];
                    if (isClosing) {{
                        openTags.pop();
                    }} else {{
                        openTags.push({{ name: tagName, full: match[0] }});
                    }}
                }}
                
                const suffix = openTags.slice().reverse().map(t => `</${{t.name}}>`).join('');
                const fullLine = prefix + lineContent + suffix;
                const renderContent = (fullLine && fullLine.trim().length > 0) ? fullLine : '&nbsp;';
                
                const rowClass = isTarget ? 'active-sublime-line' : '';
                tableHtml += `
                    <tr class="${{rowClass}}" id="L${{lineNum}}">
                        <td class="sublime-gutter">${{lineNum}}</td>
                        <td class="sublime-code-cell">${{renderContent}}</td>
                    </tr>
                `;
            }}
            tableHtml += '</table>';
            return tableHtml;
        }}

        function escapeHtml(text) {{
            return text
                .replace(/&/g, "&amp;")
                .replace(/</g, "&lt;")
                .replace(/>/g, "&gt;")
                .replace(/"/g, "&quot;")
                .replace(/'/g, "&#039;");
        }}

        // Formata identificadores de conexão para exibição limpa (apenas nome do arquivo/símbolo)
        function formatConnLabel(id) {{
            if (!id) return '';
            if (id.includes('::')) {{
                const parts = id.split('::');
                const file = parts[0].split('/').pop();
                const symbol = parts.slice(1).join('::');
                return `${{file}} ➔ ${{symbol}}`;
            }}
            return '📄 ' + id.split('/').pop();
        }}

        // 3. Mediator Pattern (Sincronização Bidirecional)
        const Mediator = {{
            selectedId: null,
            currentNode: null,

            select(nodeId, origin) {{
                if (!nodeId) return;
                this.selectedId = nodeId;
                this.currentNode = rawNodes.find(n => n.id === nodeId);

                // A. Sincroniza o Grafo Vis.js
                if (origin !== 'network') {{
                    const targetGraphId = resolveToGraphNodeId(nodeId);
                    if (targetGraphId && nodes.get(targetGraphId)) {{
                        network.selectNodes([targetGraphId]);
                        network.focus(targetGraphId, {{
                            scale: 1.1,
                            animation: {{ duration: 400, easingFunction: 'easeInOutQuad' }}
                        }});
                    }}
                }}

                // B. Sincroniza a Árvore de Arquivos
                if (origin !== 'tree') {{
                    this.highlightInTree(nodeId);
                }}

                // C. Atualiza o Inspetor de Métricas
                this.updateInspector(nodeId);

                // D. Carrega o Código no Editor Monokai
                if (this.currentNode) {{
                    this.loadCode(this.currentNode.file, this.currentNode.line);
                }}
            }},

            highlightInTree(nodeId) {{
                document.querySelectorAll('.tree-row, .tree-symbol-row').forEach(el => el.classList.remove('active'));
                
                document.querySelectorAll(`[data-id="${{CSS.escape(nodeId)}}"]`).forEach(targetEl => {{
                    targetEl.classList.add('active');
                    let parent = targetEl.closest('.tree-children');
                    while (parent) {{
                        parent.classList.add('open');
                        const arrow = parent.previousElementSibling?.querySelector('.tree-arrow');
                        if (arrow) arrow.classList.add('open');
                        parent = parent.parentElement.closest('.tree-children');
                    }}
                    targetEl.scrollIntoView({{ behavior: 'smooth', block: 'nearest' }});
                }});
            }},

            updateInspector(nodeId) {{
                const node = this.currentNode;
                const placeholder = document.getElementById('inspector-placeholder');
                const content = document.getElementById('inspector-content');

                if (!node) {{
                    placeholder.style.display = 'block';
                    content.style.display = 'none';
                    return;
                }}

                placeholder.style.display = 'none';
                content.style.display = 'flex';

                document.getElementById('det-title').innerText = `${{node.label}} (${{node.type.toUpperCase()}})`;
                
                const gitBadgeEl = document.getElementById('det-git');
                if (node.git === 'new') {{
                    gitBadgeEl.innerHTML = '<span class="git-badge git-badge-new">+ Arquivo Não Rastreado (Novo)</span>';
                }} else if (node.git === 'modified') {{
                    gitBadgeEl.innerHTML = '<span class="git-badge git-badge-mod">~ Arquivo Modificado no Git</span>';
                }} else {{
                    gitBadgeEl.innerHTML = '';
                }}

                document.getElementById('det-doc').innerText = node.doc ? `💡 ${{node.doc}}` : "Sem docstring registrada.";
                document.getElementById('det-file').innerText = `${{node.file}}:${{node.line}}`;
                document.getElementById('det-ca').innerText = node.ca;
                document.getElementById('det-ce').innerText = node.ce;
                document.getElementById('det-inst').innerText = node.instability;

                // Inbound (quem chama)
                const inboundList = document.getElementById('det-inbound');
                inboundList.innerHTML = '';
                const callers = rawEdges.filter(e => e.target === nodeId);
                if (callers.length === 0) {{
                    inboundList.innerHTML = '<span style="color:#6c7086;font-size:12px;">Nenhum chamador direto.</span>';
                }} else {{
                    callers.forEach(c => {{
                        const item = document.createElement('div');
                        item.className = 'conn-item';
                        item.innerText = formatConnLabel(c.source);
                        item.title = c.source;
                        item.onclick = () => Mediator.select(c.source, 'inspector');
                        inboundList.appendChild(item);
                    }});
                }}

                // Outbound (de quem depende)
                const outboundList = document.getElementById('det-outbound');
                outboundList.innerHTML = '';
                const callees = rawEdges.filter(e => e.source === nodeId);
                if (callees.length === 0) {{
                    outboundList.innerHTML = '<span style="color:#6c7086;font-size:12px;">Nenhuma dependência externa direta.</span>';
                }} else {{
                    callees.forEach(c => {{
                        const item = document.createElement('div');
                        item.className = 'conn-item';
                        item.innerText = formatConnLabel(c.target);
                        item.title = c.target;
                        item.onclick = () => Mediator.select(c.target, 'inspector');
                        outboundList.appendChild(item);
                    }});
                }}
            }},

            loadCode(filePath, targetLine) {{
                currentLoadedFilePath = filePath;
                const container = document.getElementById('sublime-table-container');
                const textarea = document.getElementById('sublime-editor-textarea');
                const tabFilename = document.getElementById('sublime-tab-filename');
                const statusPos = document.getElementById('sublime-status-pos');
                const statusLang = document.getElementById('sublime-status-lang');

                if (!filePath || !rawFileSources[filePath]) {{
                    container.innerHTML = '<div style="padding: 20px; color: #75715e;">// Arquivo não disponível no cache.</div>';
                    tabFilename.innerText = 'Sem arquivo';
                    if (textarea) textarea.value = '';
                    return;
                }}

                const source = rawFileSources[filePath];
                const fileName = filePath.split('/').pop();
                tabFilename.innerText = fileName;
                if (textarea) textarea.value = source;

                let lang = 'python';
                let langLabel = 'Python';
                if (filePath.endsWith('.php')) {{ lang = 'php'; langLabel = 'PHP'; }}
                else if (filePath.endsWith('.js') || filePath.endsWith('.jsx')) {{ lang = 'javascript'; langLabel = 'JavaScript'; }}
                else if (filePath.endsWith('.ts') || filePath.endsWith('.tsx')) {{ lang = 'typescript'; langLabel = 'TypeScript'; }}
                else if (filePath.endsWith('.html') || filePath.endsWith('.blade.php')) {{ lang = 'html'; langLabel = 'HTML / Blade'; }}
                else if (filePath.endsWith('.md')) {{ lang = 'markdown'; langLabel = 'Markdown'; }}
                else if (filePath.endsWith('.json')) {{ lang = 'json'; langLabel = 'JSON'; }}
                else if (filePath.endsWith('.css')) {{ lang = 'css'; langLabel = 'CSS'; }}

                statusPos.innerText = `Line ${{targetLine || 1}}, Column 1`;
                statusLang.innerText = isEditMode ? `UTF-8 | ${{langLabel}} (Modo Edição • Ctrl+S para Salvar)` : `UTF-8 | ${{langLabel}}`;

                let highlightedHtml = '';
                try {{
                    if (window.hljs) {{
                        highlightedHtml = hljs.highlight(source, {{ language: lang, ignoreIllegals: true }}).value;
                    }} else {{
                        highlightedHtml = escapeHtml(source);
                    }}
                }} catch (e) {{
                    highlightedHtml = escapeHtml(source);
                }}

                container.innerHTML = buildSublimeTable(highlightedHtml, targetLine);

                if (targetLine && targetLine > 0) {{
                    setTimeout(() => {{
                        const row = document.getElementById(`L${{targetLine}}`);
                        if (row) {{
                            row.scrollIntoView({{ behavior: 'smooth', block: 'center' }});
                        }}
                    }}, 60);
                }}
            }}
        }};

        function copyAgentPrompt() {{
            const node = Mediator.currentNode;
            if (!node) {{
                showToast('⚠️ Selecione um arquivo ou classe para copiar o contexto.', 'error');
                return;
            }}
            const callers = rawEdges.filter(e => e.target === node.id).map(e => formatConnLabel(e.source)).join(', ') || 'Nenhum chamador direto';
            const callees = rawEdges.filter(e => e.source === node.id).map(e => formatConnLabel(e.target)).join(', ') || 'Nenhuma dependência externa';
            
            const promptText = `# 🤖 Contexto Arquitetural para o Agente\\n\\n` +
                `- **Componente Alvo:** ${{node.label}} (${{node.type.toUpperCase()}})\\n` +
                `- **Arquivo:** ${{node.file}}:${{node.line}}\\n` +
                `- **Git Status:** ${{node.git === 'new' ? 'Novo (não rastreado)' : (node.git === 'modified' ? 'Modificado' : 'Rastreado / Inalterado')}}\\n` +
                `- **Descrição / Doc:** ${{node.doc || 'Sem docstring registrada'}}\\n` +
                `- **Acoplamento Aferente (Ca - Chamado por):** ${{node.ca}} [${{callers}}]\\n` +
                `- **Acoplamento Eferente (Ce - Depende de):** ${{node.ce}} [${{callees}}]\\n` +
                `- **Instabilidade (I = Ce / (Ca + Ce)):** ${{node.instability}}\\n\\n` +
                `## 🎯 Diretrizes para Execução:\\n` +
                `1. Mantenha as regras de Arquitetura Limpa, Clean Code e SOLID.\\n` +
                `2. Não quebre os chamadores listados acima.\\n` +
                `3. Escreva testes unitários para validar qualquer alteração.\\n`;

            if (navigator.clipboard && navigator.clipboard.writeText) {{
                navigator.clipboard.writeText(promptText).then(() => {{
                    showToast('📋 Prompt arquitetural copiado com sucesso! Pronto para colar no seu agente.');
                }}).catch(() => {{
                    window.prompt('Copie o prompt abaixo:', promptText);
                }});
            }} else {{
                window.prompt('Copie o prompt abaixo:', promptText);
            }}
        }}

        // 4. Renderização da Árvore (Composite Pattern)
        function renderTree(comp, parentEl) {{
            if (comp.type === 'directory') {{
                const dirDiv = document.createElement('div');
                dirDiv.className = 'tree-node';

                const isOpen = openFolders.has(comp.relative_path) || comp.relative_path === '' || openFolders.size === 0;

                const row = document.createElement('div');
                row.className = 'tree-row';
                row.onclick = (e) => {{
                    e.stopPropagation();
                    const childrenEl = dirDiv.querySelector('.tree-children');
                    const arrow = row.querySelector('.tree-arrow');
                    if (childrenEl) {{
                        const opened = childrenEl.classList.toggle('open');
                        arrow.classList.toggle('open');
                        if (opened) {{
                            openFolders.add(comp.relative_path);
                        }} else {{
                            openFolders.delete(comp.relative_path);
                        }}
                        try {{
                            localStorage.setItem('graf_lens_open_folders', JSON.stringify(Array.from(openFolders)));
                        }} catch (err) {{}}
                    }}
                }};

                const arrow = document.createElement('span');
                arrow.className = 'tree-arrow' + (isOpen ? ' open' : '');
                arrow.innerText = '▶';

                const icon = document.createElement('span');
                icon.innerText = '📁';

                const name = document.createElement('span');
                name.innerText = comp.name;

                row.appendChild(arrow);
                row.appendChild(icon);
                row.appendChild(name);

                const dirActionsBtn = document.createElement('button');
                dirActionsBtn.className = 'tree-add-btn';
                dirActionsBtn.title = `Criar ou gerenciar em "${{comp.name}}"`;
                dirActionsBtn.innerText = '+';
                dirActionsBtn.onclick = (e) => {{
                    e.stopPropagation();
                    openTreeContextMenu(e, 'directory', comp.relative_path, comp.name);
                }};
                row.appendChild(dirActionsBtn);

                dirDiv.appendChild(row);

                const childrenDiv = document.createElement('div');
                childrenDiv.className = 'tree-children' + (isOpen ? ' open' : '');
                comp.children.forEach(child => renderTree(child, childrenDiv));
                dirDiv.appendChild(childrenDiv);

                parentEl.appendChild(dirDiv);
            }} else if (comp.type === 'file') {{
                const fileDiv = document.createElement('div');
                fileDiv.className = 'tree-node';

                const row = document.createElement('div');
                row.className = 'tree-row';
                row.setAttribute('data-id', comp.full_id);
                row.onclick = (e) => {{
                    e.stopPropagation();
                    Mediator.select(comp.full_id, 'tree');
                }};

                const spacer = document.createElement('span');
                spacer.style.width = '10px';

                const icon = document.createElement('span');
                icon.innerText = '📄';

                const name = document.createElement('span');
                name.className = 'tree-file-name';
                name.innerText = comp.name;

                row.appendChild(spacer);
                row.appendChild(icon);
                row.appendChild(name);

                if (comp.git_status) {{
                    const gitBadge = document.createElement('span');
                    if (comp.git_status === 'new') {{
                        gitBadge.className = 'git-badge git-badge-new';
                        gitBadge.innerText = '+ Novo';
                    }} else if (comp.git_status === 'modified') {{
                        gitBadge.className = 'git-badge git-badge-mod';
                        gitBadge.innerText = '~ Mod';
                    }} else if (comp.git_status === 'deleted') {{
                        gitBadge.className = 'git-badge git-badge-del';
                        gitBadge.innerText = '- Rem';
                    }}
                    row.appendChild(gitBadge);
                }}

                if (comp.symbols && comp.symbols.length > 0) {{
                    const badge = document.createElement('span');
                    badge.className = 'badge-count';
                    badge.innerText = comp.symbols.length;
                    row.appendChild(badge);
                }}

                const fileActionsBtn = document.createElement('button');
                fileActionsBtn.className = 'tree-more-btn';
                fileActionsBtn.title = `Ações em "${{comp.name}}" (Renomear, Excluir)`;
                fileActionsBtn.innerText = '⋮';
                fileActionsBtn.onclick = (e) => {{
                    e.stopPropagation();
                    openTreeContextMenu(e, 'file', comp.relative_path, comp.name);
                }};
                row.appendChild(fileActionsBtn);

                fileDiv.appendChild(row);

                if (comp.symbols && comp.symbols.length > 0) {{
                    const symContainer = document.createElement('div');
                    symContainer.className = 'tree-children';
                    comp.symbols.forEach(sym => {{
                        const symRow = document.createElement('div');
                        symRow.className = 'tree-symbol-row';
                        symRow.setAttribute('data-id', sym.id);
                        symRow.onclick = (e) => {{
                            e.stopPropagation();
                            Mediator.select(sym.id, 'tree');
                        }};
                        const symIcon = sym.type === 'class' ? '🏛️' : (sym.type === 'interface' ? '📜' : '⚡');
                        symRow.innerHTML = `<span>${{symIcon}}</span> <span>${{sym.name}}</span>`;
                        symContainer.appendChild(symRow);
                    }});
                    fileDiv.appendChild(symContainer);

                    row.ondblclick = (e) => {{
                        e.stopPropagation();
                        symContainer.classList.toggle('open');
                    }};
                }}

                parentEl.appendChild(fileDiv);
            }}
        }}

        // Inicializa a árvore
        const treeRoot = document.getElementById('tree-root');
        renderTree(rawTree, treeRoot);


        // 6. Sub-abas de Navegação (Árvore vs Inspetor)
        function switchNavTab(tab) {{
            currentNavTab = tab;
            document.querySelectorAll('.nav-tab-btn').forEach(b => b.classList.remove('active'));
            document.getElementById('nav-pane-tree').style.display = 'none';
            document.getElementById('nav-pane-inspector').style.display = 'none';

            if (tab === 'tree') {{
                document.getElementById('subtab-btn-tree').classList.add('active');
                document.getElementById('nav-pane-tree').style.display = 'flex';
            }} else {{
                document.getElementById('subtab-btn-inspector').classList.add('active');
                document.getElementById('nav-pane-inspector').style.display = 'flex';
            }}
        }}

        // Alterna visibilidade do Sub-Painel de Navegação
        function toggleNavSubpanel() {{
            const nav = document.getElementById('nav-subpanel');
            const resizer = document.getElementById('internal-resizer');
            const btnReopen = document.getElementById('btn-reopen-nav');
            
            nav.classList.toggle('hidden');
            const isHidden = nav.classList.contains('hidden');
            resizer.style.display = isHidden ? 'none' : 'block';
            btnReopen.style.display = isHidden ? 'inline-flex' : 'none';
        }}

        // 7. Alterna visibilidade do Sub-Painel de Código (Recolher / Expandir)
        let isCodeCollapsed = false;
        let savedSidebarWidthBeforeCollapse = null;

        function toggleCodeSubpanel(forceState) {{
            const editor = document.getElementById('editor-subpanel');
            const resizer = document.getElementById('internal-resizer');
            const btnReopenCode = document.getElementById('btn-reopen-code');
            const navSubpanel = document.getElementById('nav-subpanel');
            const sidebar = document.getElementById('sidebar');

            if (typeof forceState === 'boolean') {{
                isCodeCollapsed = forceState;
            }} else {{
                isCodeCollapsed = !isCodeCollapsed;
            }}

            if (isCodeCollapsed) {{
                editor.style.display = 'none';
                resizer.style.display = 'none';
                btnReopenCode.style.display = 'inline-flex';
                savedSidebarWidthBeforeCollapse = sidebar.offsetWidth;
                const navW = navSubpanel ? (navSubpanel.offsetWidth || 300) : 300;
                updateSidebarWidth(navW + 2);
            }} else {{
                editor.style.display = 'flex';
                if (!navSubpanel.classList.contains('hidden')) {{
                    resizer.style.display = 'block';
                }}
                btnReopenCode.style.display = 'none';
                const targetW = savedSidebarWidthBeforeCollapse || 680;
                updateSidebarWidth(Math.max(500, targetW));
            }}
            if (window.network) setTimeout(() => network.redraw(), 100);
        }}

        // 8. Alterna visibilidade do Grafo (Recolher / Expandir)
        let isGraphCollapsed = false;
        let savedSidebarWidthBeforeGraphCollapse = null;

        function toggleGraphPanel(forceState) {{
            const networkContainer = document.getElementById('network-container');
            const resizer = document.getElementById('resizer');
            const sidebarToggle = document.getElementById('sidebar-toggle');
            const sidebar = document.getElementById('sidebar');
            const btnToggleGraph = document.getElementById('btn-toggle-graph');

            if (typeof forceState === 'boolean') {{
                isGraphCollapsed = forceState;
            }} else {{
                isGraphCollapsed = !isGraphCollapsed;
            }}

            if (isGraphCollapsed) {{
                networkContainer.style.display = 'none';
                if (resizer) resizer.style.display = 'none';
                if (sidebarToggle) sidebarToggle.style.display = 'none';
                savedSidebarWidthBeforeGraphCollapse = sidebar.style.width || (sidebar.offsetWidth + 'px');
                sidebar.style.width = '100%';
                sidebar.style.minWidth = '100%';
                sidebar.style.maxWidth = '100%';
                if (btnToggleGraph) {{
                    btnToggleGraph.innerHTML = '🌐 Reabrir Grafo';
                    btnToggleGraph.style.background = '#272822';
                    btnToggleGraph.style.color = '#a6e22e';
                    btnToggleGraph.style.borderColor = '#a6e22e';
                }}
            }} else {{
                networkContainer.style.display = 'block';
                if (resizer) resizer.style.display = 'block';
                if (sidebarToggle) sidebarToggle.style.display = 'block';
                const prevW = savedSidebarWidthBeforeGraphCollapse || '600px';
                sidebar.style.width = prevW;
                sidebar.style.minWidth = '380px';
                sidebar.style.maxWidth = '90vw';
                if (btnToggleGraph) {{
                    btnToggleGraph.innerHTML = '🌐 Grafo';
                    btnToggleGraph.style.background = '';
                    btnToggleGraph.style.color = '';
                    btnToggleGraph.style.borderColor = '';
                }}
                if (window.network) {{
                    setTimeout(() => {{
                        network.redraw();
                    }}, 100);
                }}
            }}
        }}

        // Função de recolhimento progressivo em 2 estágios (1º Código • 2º Árvore)
        function handleStageCollapse() {{
            const editor = document.getElementById('editor-subpanel');
            const isEditorOpen = editor && editor.style.display !== 'none';
            if (isEditorOpen) {{
                toggleCodeSubpanel(true);
            }} else {{
                toggleSidebar();
            }}
        }}

        // Alterna visibilidade da barra lateral inteira
        function toggleSidebar() {{
            const sb = document.getElementById('sidebar');
            const btnReopen = document.getElementById('sidebar-reopen-btn');
            const graphToolbar = document.getElementById('graph-toolbar');
            sb.classList.toggle('collapsed');
            const isCollapsed = sb.classList.contains('collapsed');
            if (btnReopen) btnReopen.style.display = isCollapsed ? 'inline-flex' : 'none';
            if (graphToolbar) graphToolbar.style.left = isCollapsed ? '52px' : '16px';
            if (window.network) setTimeout(() => network.redraw(), 260);
        }}

        function updateSidebarWidth(newWidth) {{
            const sidebar = document.getElementById('sidebar');
            sidebar.style.width = newWidth + 'px';
            sidebar.style.minWidth = newWidth + 'px';
            if (window.network) network.redraw();
            try {{
                localStorage.setItem('graf_lens_sidebar_width', newWidth);
            }} catch (e) {{}}
        }}

        // 7. Redimensionamento do Resizer Externo (Sidebar vs Grafo)
        const resizer = document.getElementById('resizer');
        const sidebar = document.getElementById('sidebar');
        let isResizing = false;

        resizer.addEventListener('mousedown', (e) => {{
            isResizing = true;
            resizer.classList.add('dragging');
            document.body.style.cursor = 'col-resize';
            document.body.style.userSelect = 'none';
        }});

        window.addEventListener('mousemove', (e) => {{
            if (!isResizing) return;
            const newWidth = Math.max(380, Math.min(window.innerWidth - 200, e.clientX));
            updateSidebarWidth(newWidth);
        }});

        window.addEventListener('mouseup', () => {{
            if (isResizing) {{
                isResizing = false;
                resizer.classList.remove('dragging');
                document.body.style.cursor = '';
                document.body.style.userSelect = '';
                if (window.network) network.redraw();
            }}
        }});

        // 8. Redimensionamento do Resizer Interno (Árvore vs Código)
        const internalResizer = document.getElementById('internal-resizer');
        const navSubpanel = document.getElementById('nav-subpanel');
        let isInternalResizing = false;

        internalResizer.addEventListener('mousedown', (e) => {{
            isInternalResizing = true;
            internalResizer.classList.add('dragging');
            document.body.style.cursor = 'col-resize';
            document.body.style.userSelect = 'none';
        }});

        window.addEventListener('mousemove', (e) => {{
            if (!isInternalResizing) return;
            const sidebarRect = sidebar.getBoundingClientRect();
            const relX = e.clientX - sidebarRect.left;
            const newNavWidth = Math.max(180, Math.min(sidebarRect.width - 240, relX));
            navSubpanel.style.width = newNavWidth + 'px';
            navSubpanel.style.minWidth = newNavWidth + 'px';
        }});

        window.addEventListener('mouseup', () => {{
            if (isInternalResizing) {{
                isInternalResizing = false;
                internalResizer.classList.remove('dragging');
                document.body.style.cursor = '';
                document.body.style.userSelect = '';
                try {{
                    const w = parseInt(navSubpanel.style.width, 10);
                    if (w) localStorage.setItem('graf_lens_nav_width', w);
                }} catch (e) {{}}
            }}
        }});

        // Restauração das larguras personalizadas do usuário salvas no localStorage
        try {{
            const savedSidebarWidth = localStorage.getItem('graf_lens_sidebar_width');
            if (savedSidebarWidth) {{
                updateSidebarWidth(parseInt(savedSidebarWidth, 10));
            }}
            const savedNavWidth = localStorage.getItem('graf_lens_nav_width');
            if (savedNavWidth && navSubpanel) {{
                navSubpanel.style.width = savedNavWidth + 'px';
                navSubpanel.style.minWidth = savedNavWidth + 'px';
            }}
        }} catch (e) {{}}

        function copyCurrentCode() {{
            if (!Mediator.currentNode || !rawFileSources[Mediator.currentNode.file]) return;
            const code = rawFileSources[Mediator.currentNode.file];
            navigator.clipboard.writeText(code).then(() => {{
                showToast('📋 Código copiado com sucesso!');
            }});
        }}

        function toggleEditMode(forceState) {{
            if (!currentLoadedFilePath) {{
                showToast('⚠️ Selecione um arquivo na árvore lateral antes de editar.', 'error');
                return;
            }}
            if (typeof forceState === 'boolean') {{
                isEditMode = forceState;
            }} else {{
                isEditMode = !isEditMode;
            }}

            const tableContainer = document.getElementById('sublime-table-container');
            const textarea = document.getElementById('sublime-editor-textarea');
            const btnEdit = document.getElementById('btn-toggle-edit');
            const btnSave = document.getElementById('btn-save-code');
            const statusLang = document.getElementById('sublime-status-lang');

            if (isEditMode) {{
                tableContainer.style.display = 'none';
                textarea.style.display = 'block';
                textarea.value = rawFileSources[currentLoadedFilePath] || '';
                btnEdit.innerHTML = '👁️ Visualizar';
                btnEdit.style.background = '#fd971f';
                btnEdit.style.color = '#111';
                btnSave.style.display = 'inline-flex';
                statusLang.innerText = `${{statusLang.innerText.split('(')[0].trim()}} (Modo Edição • Ctrl+S para Salvar)`;
                textarea.focus();
            }} else {{
                textarea.style.display = 'none';
                tableContainer.style.display = 'block';
                btnEdit.innerHTML = '✏️ Editar';
                btnEdit.style.background = '';
                btnEdit.style.color = '';
                btnSave.style.display = 'none';
                Mediator.loadCode(currentLoadedFilePath);
            }}
        }}

        async function saveCurrentCode() {{
            if (!currentLoadedFilePath) return;
            const textarea = document.getElementById('sublime-editor-textarea');
            const content = textarea.value;
            const btnSave = document.getElementById('btn-save-code');
            const originalText = btnSave.innerHTML;
            btnSave.innerHTML = '⏳ Salvando...';
            btnSave.disabled = true;

            await executeBackendApi('/api/save-file', {{
                path: currentLoadedFilePath,
                content: content
            }}, '💾 Arquivo salvo com sucesso no disco!');

            btnSave.innerHTML = originalText;
            btnSave.disabled = false;
            rawFileSources[currentLoadedFilePath] = content;
        }}

        // Atalhos de teclado: Tab (4 espaços) e Ctrl+S / Cmd+S para salvar instantaneamente
        document.addEventListener('DOMContentLoaded', () => {{
            const editorTextarea = document.getElementById('sublime-editor-textarea');
            if (editorTextarea) {{
                editorTextarea.addEventListener('keydown', (e) => {{
                    if (e.key === 'Tab') {{
                        e.preventDefault();
                        const start = editorTextarea.selectionStart;
                        const end = editorTextarea.selectionEnd;
                        editorTextarea.value = editorTextarea.value.substring(0, start) + '    ' + editorTextarea.value.substring(end);
                        editorTextarea.selectionStart = editorTextarea.selectionEnd = start + 4;
                    }} else if ((e.ctrlKey || e.metaKey) && e.key === 's') {{
                        e.preventDefault();
                        saveCurrentCode();
                    }}
                }});
            }}

            window.addEventListener('keydown', (e) => {{
                if ((e.ctrlKey || e.metaKey) && e.key === 's') {{
                    if (isEditMode) {{
                        e.preventDefault();
                        saveCurrentCode();
                    }}
                }}
            }});
        }});

        // 9. Busca em tempo real
        function onSearchInput(query) {{
            query = (query || '').toLowerCase().trim();

            if (!query) {{
                nodes.forEach(n => nodes.update({{ id: n.id, hidden: false }}));
            }} else {{
                nodes.forEach(n => {{
                    const match = n.label.toLowerCase().includes(query) || n.id.toLowerCase().includes(query);
                    nodes.update({{ id: n.id, hidden: !match }});
                }});
            }}

            document.querySelectorAll('.tree-file-name, .tree-symbol-row').forEach(el => {{
                const text = el.innerText.toLowerCase();
                const node = el.closest('.tree-node') || el;
                if (!query || text.includes(query)) {{
                    node.style.display = '';
                    if (query && text.includes(query)) {{
                        let p = node.parentElement;
                        while (p && p.classList.contains('tree-children')) {{
                            p.classList.add('open');
                            const arrow = p.previousElementSibling?.querySelector('.tree-arrow');
                            if (arrow) arrow.classList.add('open');
                            p = p.parentElement.closest('.tree-children');
                        }}
                    }}
                }} else {{
                    if (el.classList.contains('tree-file-name')) {{
                        node.style.display = 'none';
                    }}
                }}
            }});
        }}

        // 10. Sincronização em Tempo Real (Live Reload via SSE)
        function initLiveReload() {{
            if (location.protocol.startsWith('http')) {{
                const badge = document.createElement('div');
                badge.id = 'live-indicator';
                badge.style.cssText = 'position:fixed;bottom:12px;right:12px;background:#a6e22e;color:#1e1e1e;padding:4px 10px;border-radius:12px;font-size:11px;font-weight:bold;z-index:9999;box-shadow:0 2px 8px rgba(0,0,0,0.5);display:flex;align-items:center;gap:6px;font-family:sans-serif;pointer-events:none;';
                badge.innerHTML = '<span style="width:8px;height:8px;background:#272822;border-radius:50%;display:inline-block;"></span> AO VIVO (Watch Mode)';
                document.body.appendChild(badge);

                const saved = sessionStorage.getItem('lens_session_state');
                if (saved) {{
                    try {{
                        const s = JSON.parse(saved);
                        sessionStorage.removeItem('lens_session_state');
                        if (s.nodeId) {{
                            setTimeout(() => Mediator.select(s.nodeId, 'restore'), 100);
                        }} else if (s.file) {{
                            setTimeout(() => Mediator.loadCode(s.file, s.line || 1), 100);
                        }}
                        if (s.navTab) switchNavTab(s.navTab);
                    }} catch (e) {{}}
                }}

                const evtSource = new EventSource('/events');
                evtSource.addEventListener('update', () => {{
                    fetchLiveUpdate();
                }});
                evtSource.addEventListener('reload', () => {{
                    fetchLiveUpdate();
                }});

                evtSource.onerror = () => {{
                    badge.style.background = '#fd971f';
                    badge.innerHTML = '⚠️ Reconectando...';
                }};
                evtSource.onopen = () => {{
                    badge.style.background = '#a6e22e';
                    badge.innerHTML = '<span style="width:8px;height:8px;background:#272822;border-radius:50%;display:inline-block;"></span> AO VIVO (Watch Mode)';
                }};
            }}
        }}
        initLiveReload();

        // 11. Menu de Contexto da Árvore (Criar Pasta/MD, Renomear, Excluir)
        let activeContextType = null;
        let activeContextPath = null;
        let activeContextName = null;

        function openTreeContextMenu(e, type, relPath, name) {{
            activeContextType = type;
            activeContextPath = relPath || '';
            activeContextName = name;

            const menu = document.getElementById('tree-context-menu');
            menu.innerHTML = '';

            const header = document.createElement('div');
            header.className = 'tree-context-header';
            header.innerText = (type === 'directory' ? '📁 ' : '📄 ') + name;
            menu.appendChild(header);

            if (type === 'directory') {{
                const btnNewFolder = document.createElement('button');
                btnNewFolder.className = 'tree-context-item';
                btnNewFolder.innerHTML = '<span>📁</span> Criar pasta';
                btnNewFolder.onclick = () => promptCreateFolder(activeContextPath);
                menu.appendChild(btnNewFolder);

                const btnNewFile = document.createElement('button');
                btnNewFile.className = 'tree-context-item';
                btnNewFile.innerHTML = '<span>📄</span> Criar arquivo';
                btnNewFile.onclick = () => promptCreateFile(activeContextPath);
                menu.appendChild(btnNewFile);

                const btnRename = document.createElement('button');
                btnRename.className = 'tree-context-item';
                btnRename.innerHTML = '<span>✏️</span> Renomear pasta';
                btnRename.onclick = () => promptRename(activeContextPath, activeContextName);
                menu.appendChild(btnRename);

                const btnDelete = document.createElement('button');
                btnDelete.className = 'tree-context-item danger';
                btnDelete.innerHTML = '<span>🗑️</span> Excluir pasta';
                btnDelete.onclick = () => promptDelete(activeContextPath, activeContextName, true);
                menu.appendChild(btnDelete);
            }} else {{
                const btnRename = document.createElement('button');
                btnRename.className = 'tree-context-item';
                btnRename.innerHTML = '<span>✏️</span> Renomear arquivo';
                btnRename.onclick = () => promptRename(activeContextPath, activeContextName);
                menu.appendChild(btnRename);

                const btnDelete = document.createElement('button');
                btnDelete.className = 'tree-context-item danger';
                btnDelete.innerHTML = '<span>🗑️</span> Excluir arquivo';
                btnDelete.onclick = () => promptDelete(activeContextPath, activeContextName, false);
                menu.appendChild(btnDelete);
            }}

            const posX = Math.min(e.clientX + 10, window.innerWidth - 190);
            const posY = Math.min(e.clientY + 5, window.innerHeight - 200);
            menu.style.left = posX + 'px';
            menu.style.top = posY + 'px';
            menu.style.display = 'flex';
        }}

        function closeTreeContextMenu() {{
            const menu = document.getElementById('tree-context-menu');
            if (menu) menu.style.display = 'none';
        }}

        document.addEventListener('click', (e) => {{
            if (!e.target.closest('#tree-context-menu')) {{
                closeTreeContextMenu();
            }}
        }});

        async function executeBackendApi(endpoint, payload, actionSuccessMsg) {{
            const baseUrl = location.protocol.startsWith('http') ? '' : 'http://127.0.0.1:7357';
            try {{
                const res = await fetch(baseUrl + endpoint, {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify(payload)
                }});
                const data = await res.json();
                if (data.success) {{
                    showToast(actionSuccessMsg);
                    if (data.data) {{
                        applyLiveUpdate(data.data);
                    }} else {{
                        fetchLiveUpdate();
                    }}
                }} else {{
                    showToast('❌ Erro: ' + (data.error || 'Operação falhou'), 'error');
                }}
            }} catch (err) {{
                showToast('⚠️ O servidor HTTP local do GrafLean não está respondendo.', 'error');
            }}
        }}

        async function promptCreateFolder(parentRelPath) {{
            closeTreeContextMenu();
            const targetDesc = parentRelPath || 'raiz do projeto';
            const folderName = window.prompt(`Criar nova pasta dentro de "${{targetDesc}}":`);
            if (!folderName || !folderName.trim()) return;

            const finalRelPath = parentRelPath ? `${{parentRelPath}}/${{folderName.trim()}}` : folderName.trim();
            await executeBackendApi('/api/create-folder', {{ path: finalRelPath }}, `✅ Pasta "${{folderName.trim()}}" criada com sucesso!`);
        }}

        async function promptCreateFile(parentRelPath) {{
            closeTreeContextMenu();
            const targetDesc = parentRelPath || 'raiz do projeto';
            let fileName = window.prompt(`Criar arquivo em "${{targetDesc}}":`, 'novo_arquivo.md');
            if (!fileName || !fileName.trim()) return;

            const finalRelPath = parentRelPath ? `${{parentRelPath}}/${{fileName.trim()}}` : fileName.trim();
            if (parentRelPath) {{
                openFolders.add(parentRelPath);
                try {{
                    localStorage.setItem('graf_lens_open_folders', JSON.stringify(Array.from(openFolders)));
                }} catch (e) {{}}
            }}
            await executeBackendApi('/api/create-file', {{ path: finalRelPath, content: '' }}, `✅ Arquivo "${{fileName.trim()}}" criado com sucesso!`);
        }}

        async function promptRename(relPath, currentName) {{
            closeTreeContextMenu();
            const newName = window.prompt(`Renomear "${{currentName}}" para:`, currentName);
            if (!newName || !newName.trim() || newName.trim() === currentName) return;

            await executeBackendApi('/api/rename', {{ old_path: relPath, new_name: newName.trim() }}, `✅ Renomeado para "${{newName.trim()}}"!`);
        }}

        async function promptDelete(relPath, currentName, isDir) {{
            closeTreeContextMenu();
            const confirmMsg = `⚠️ ATENÇÃO: Deseja realmente excluir permanentemente ${{isDir ? 'a pasta' : 'o arquivo'}} "${{currentName}}"?\\n\\nEsta ação não poderá ser desfeita.`;
            if (!window.confirm(confirmMsg)) return;

            await executeBackendApi('/api/delete', {{ path: relPath }}, `🗑️ "${{currentName}}" foi excluído com sucesso!`);
        }}
    </script>

    <!-- Menu Flutuante Contextual para Pastas e Arquivos -->
    <div id="tree-context-menu" class="tree-context-menu" style="display:none;"></div>
</body>
</html>
"""
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html_template)

        return output_path


if __name__ == "__main__":
    import sys
    target_dir = sys.argv[1] if len(sys.argv) > 1 else "."
    g = ProjectGraph(target_dir)
    g.scan_project()
    g.save_to_file()
    viz = ArchitectureVisualizer(g)
    path = viz.generate_html()
    print(f"Mapa visual gerado com sucesso em: {path}")
