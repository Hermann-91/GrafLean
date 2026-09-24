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
                "git": node.git_status or ""
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
        for node in self.graph.nodes.values():
            if node.file_path and os.path.isfile(node.file_path):
                if node.file_path not in file_sources:
                    try:
                        with open(node.file_path, "r", encoding="utf-8", errors="replace") as f:
                            file_sources[node.file_path] = f.read()
                    except Exception:
                        file_sources[node.file_path] = ""

        def safe_json(data) -> str:
            # Escapa < e > como unicode \u003c e \u003e para garantir conformidade estrita com RFC 8259 (JSON)
            # e impedir que qualquer tag HTML/JS (ex: </script>, <!--) interfira no parser do navegador.
            return json.dumps(data, ensure_ascii=False).replace("<", "\\u003c").replace(">", "\\u003e")

        nodes_json = safe_json(nodes_data)
        edges_json = safe_json(edges_data)
        tree_json = safe_json(tree_data)
        sources_json = safe_json(file_sources)

        html_template = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Sublime Architecture Lens — Workspace Integrado</title>
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

        /* Floating Toggle Button */
        #sidebar-toggle {{
            position: absolute;
            top: 15px;
            left: 595px;
            z-index: 150;
            background: #1e1e2e;
            color: #89b4fa;
            border: 1px solid #45475a;
            border-radius: 8px;
            padding: 8px 12px;
            cursor: pointer;
            font-size: 14px;
            font-weight: bold;
            box-shadow: 0 4px 12px rgba(0,0,0,0.4);
            transition: background 0.2s ease;
        }}
        #sidebar-toggle:hover {{
            background: #313244;
            color: #b4befe;
        }}
        #sidebar.collapsed ~ #sidebar-toggle {{
            left: 15px !important;
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

        /* Legend */
        .legend {{
            background: rgba(24, 24, 37, 0.5);
            padding: 6px 8px;
            border-radius: 6px;
            border: 1px solid rgba(69, 71, 90, 0.4);
            font-size: 10px;
            display: flex;
            flex-direction: column;
            gap: 3px;
        }}
        .legend-item {{ display: flex; align-items: center; gap: 6px; }}
        .dot {{ width: 8px; height: 8px; border-radius: 50%; }}

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
            <div>
                <div class="brand-title">🏛️ GrafLens</div>
                <div class="brand-sub">Workspace Integrado de Arquitetura & Orquestração</div>
            </div>
            <div style="display:flex; gap:6px; align-items:center;">
                <button class="sublime-btn" onclick="openAgentModal()" style="border-color:#a6e22e; color:#a6e22e; font-weight:600;" title="Criar Pasta ou Especificação Markdown para Agentes">
                    🤖 + Criar (Agente)
                </button>
                <button class="sublime-btn" id="btn-reopen-nav" onclick="toggleNavSubpanel()" style="display:none;" title="Mostrar Árvore/Inspetor">
                    📁 Navegador
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

                    <div class="legend">
                        <div class="legend-item"><span class="dot" style="background:#f9e2af;"></span> <b>Arquivo (Negrito)</b></div>
                        <div class="legend-item"><span class="dot" style="background:#89b4fa;"></span> Classe</div>
                        <div class="legend-item"><span class="dot" style="background:#b4befe;"></span> Interface</div>
                        <div class="legend-item"><span class="dot" style="background:#a6e3a1;"></span> Método / Função</div>
                        <div class="legend-item"><span class="git-badge git-badge-new" style="margin:0;">+ Novo</span> Arquivo não rastreado</div>
                        <div class="legend-item"><span class="git-badge git-badge-mod" style="margin:0;">~ Mod</span> Arquivo modificado</div>
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
                        </div>
                        <div class="sublime-toolbar-actions">
                            <button class="sublime-btn" onclick="copyCurrentCode()" title="Copiar Código">📋 Copiar</button>
                        </div>
                    </div>

                    <div class="sublime-code-viewport" id="code-viewport">
                        <div id="sublime-table-container">
                            <div style="padding: 20px; color: #75715e; font-family: monospace;">
                                // Clique em qualquer arquivo ou símbolo da árvore à esquerda para carregar o código...
                            </div>
                        </div>
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

    <button id="sidebar-toggle" onclick="toggleSidebar()" title="Recolher/Expandir Barra Lateral">◀</button>

    <div id="network"></div>

    <!-- Dados Protegidos e Imunes a Conflito de Tags Internas -->
    <script type="application/json" id="data-nodes">{nodes_json}</script>
    <script type="application/json" id="data-edges">{edges_json}</script>
    <script type="application/json" id="data-tree">{tree_json}</script>
    <script type="application/json" id="data-sources">{sources_json}</script>

    <script>
        const rawNodes = JSON.parse(document.getElementById('data-nodes').textContent);
        const rawEdges = JSON.parse(document.getElementById('data-edges').textContent);
        const rawTree = JSON.parse(document.getElementById('data-tree').textContent);
        const rawFileSources = JSON.parse(document.getElementById('data-sources').textContent);
        let currentNavTab = 'tree';

        const colorMap = {{
            "class": "#89b4fa",
            "interface": "#b4befe",
            "method": "#a6e3a1",
            "function": "#94e2d5",
            "file": "#f9e2af"
        }};

        // 1. Vis.js Network Setup
        const nodes = new vis.DataSet(rawNodes.map(n => ({{
            id: n.id,
            label: n.label,
            title: (n.git === "new" ? "[+ Git: Novo]\\n" : (n.git === "modified" ? "[~ Git: Modificado]\\n" : "")) + n.title,
            color: {{
                background: n.type === "file" ? "#2a281e" : (colorMap[n.type] || "#cdd6f4"),
                border: n.git === "new" ? "#a6e22e" : (n.git === "modified" ? "#fd971f" : (n.type === "file" ? "#f9e2af" : (n.cycle ? "#f38ba8" : (n.deep ? "#a6e3a1" : "#45475a"))))
            }},
            borderWidth: (n.git === "new" || n.git === "modified") ? 3 : (n.type === "file" ? 2 : (n.cycle ? 3 : 1)),
            size: Math.max(12, Math.min(30, 10 + n.ca * 3)),
            shape: n.type === "file" ? "box" : "dot",
            font: {{
                color: n.type === "file" ? "#f9e2af" : "#cdd6f4",
                size: n.type === "file" ? 11 : 12,
                bold: n.type === "file"
            }}
        }})));

        const edges = new vis.DataSet(rawEdges.map(e => ({{
            from: e.source,
            to: e.target,
            arrows: "to",
            color: {{ color: "#45475a", highlight: "#89b4fa" }},
            width: 1
        }})));

        const container = document.getElementById('network');
        const network = new vis.Network(container, {{ nodes, edges }}, {{
            interaction: {{ hover: true, tooltipDelay: 50, selectConnectedEdges: true }},
            physics: {{
                solver: "forceAtlas2Based",
                forceAtlas2Based: {{ gravitationalConstant: -55, centralGravity: 0.01, springLength: 95 }}
            }}
        }});

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
                    const existsInGraph = nodes.get(nodeId);
                    if (existsInGraph) {{
                        network.selectNodes([nodeId]);
                        network.focus(nodeId, {{
                            scale: 1.1,
                            animation: {{ duration: 500, easingFunction: 'easeInOutQuad' }}
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
                const container = document.getElementById('sublime-table-container');
                const tabFilename = document.getElementById('sublime-tab-filename');
                const statusPos = document.getElementById('sublime-status-pos');
                const statusLang = document.getElementById('sublime-status-lang');

                if (!filePath || !rawFileSources[filePath]) {{
                    container.innerHTML = '<div style="padding: 20px; color: #75715e;">// Arquivo não disponível no cache.</div>';
                    tabFilename.innerText = 'Sem arquivo';
                    return;
                }}

                const source = rawFileSources[filePath];
                const fileName = filePath.split('/').pop();
                tabFilename.innerText = fileName;

                let lang = 'python';
                let langLabel = 'Python';
                if (filePath.endsWith('.php')) {{ lang = 'php'; langLabel = 'PHP'; }}
                else if (filePath.endsWith('.js') || filePath.endsWith('.jsx')) {{ lang = 'javascript'; langLabel = 'JavaScript'; }}
                else if (filePath.endsWith('.ts') || filePath.endsWith('.tsx')) {{ lang = 'typescript'; langLabel = 'TypeScript'; }}
                else if (filePath.endsWith('.html') || filePath.endsWith('.blade.php')) {{ lang = 'html'; langLabel = 'HTML / Blade'; }}

                statusPos.innerText = `Line ${{targetLine || 1}}, Column 1`;
                statusLang.innerText = `UTF-8 | ${{langLabel}}`;

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
                alert('Selecione um arquivo ou classe para copiar o contexto.');
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
                    alert('📋 Prompt arquitetural copiado com sucesso!\\nPronto para colar no terminal do seu agente.');
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

                const row = document.createElement('div');
                row.className = 'tree-row';
                row.onclick = (e) => {{
                    e.stopPropagation();
                    const childrenEl = dirDiv.querySelector('.tree-children');
                    const arrow = row.querySelector('.tree-arrow');
                    if (childrenEl) {{
                        childrenEl.classList.toggle('open');
                        arrow.classList.toggle('open');
                    }}
                }};

                const arrow = document.createElement('span');
                arrow.className = 'tree-arrow open';
                arrow.innerText = '▶';

                const icon = document.createElement('span');
                icon.innerText = '📁';

                const name = document.createElement('span');
                name.innerText = comp.name;

                row.appendChild(arrow);
                row.appendChild(icon);
                row.appendChild(name);
                dirDiv.appendChild(row);

                const childrenDiv = document.createElement('div');
                childrenDiv.className = 'tree-children open';
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

        // 5. Eventos do Grafo Vis.js
        network.on("click", function(params) {{
            if (params.nodes.length > 0) {{
                Mediator.select(params.nodes[0], 'network');
            }}
        }});

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

        // Alterna visibilidade da barra lateral inteira
        function toggleSidebar() {{
            const sb = document.getElementById('sidebar');
            const btn = document.getElementById('sidebar-toggle');
            sb.classList.toggle('collapsed');
            btn.innerText = sb.classList.contains('collapsed') ? '▶' : '◀';
            if (window.network) setTimeout(() => network.redraw(), 260);
        }}

        function updateSidebarWidth(newWidth) {{
            const sidebar = document.getElementById('sidebar');
            const toggleBtn = document.getElementById('sidebar-toggle');
            sidebar.style.width = newWidth + 'px';
            sidebar.style.minWidth = newWidth + 'px';
            if (!sidebar.classList.contains('collapsed')) {{
                toggleBtn.style.left = (newWidth + 15) + 'px';
            }}
            if (window.network) network.redraw();
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
            }}
        }});

        function copyCurrentCode() {{
            if (!Mediator.currentNode || !rawFileSources[Mediator.currentNode.file]) return;
            const code = rawFileSources[Mediator.currentNode.file];
            navigator.clipboard.writeText(code).then(() => {{
                alert('Código copiado com sucesso!');
            }});
        }}

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
                evtSource.addEventListener('reload', () => {{
                    sessionStorage.setItem('lens_session_state', JSON.stringify({{
                        nodeId: Mediator.selectedId,
                        file: Mediator.currentNode ? Mediator.currentNode.file : null,
                        line: Mediator.currentNode ? Mediator.currentNode.line : 1,
                        navTab: currentNavTab
                    }}));
                    location.reload();
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

        // 11. Modal de Criação de Recursos para Agentes
        let currentModalTab = 'md';

        function openAgentModal() {{
            const modal = document.getElementById('agent-modal-overlay');
            const filePathInput = document.getElementById('modal-file-path');
            const folderPathInput = document.getElementById('modal-folder-path');
            const errBox = document.getElementById('modal-error-msg');
            const okBox = document.getElementById('modal-success-msg');

            errBox.style.display = 'none';
            okBox.style.display = 'none';
            folderPathInput.value = '';

            // Se um nó estiver selecionado, sugere nome de arquivo contextualizado
            if (Mediator.currentNode) {{
                const cleanName = Mediator.currentNode.label.replace(/[^a-zA-Z0-9_-]/g, '_');
                filePathInput.value = `docs/specs/TASK_${{cleanName}}.md`;
            }} else {{
                filePathInput.value = 'docs/specs/TASK_ORCHESTRATION.md';
            }}

            switchModalTab('md');
            modal.style.display = 'flex';
        }}

        function closeAgentModal() {{
            document.getElementById('agent-modal-overlay').style.display = 'none';
        }}

        function switchModalTab(tab) {{
            currentModalTab = tab;
            document.getElementById('modal-tab-md').classList.toggle('active', tab === 'md');
            document.getElementById('modal-tab-folder').classList.toggle('active', tab === 'folder');
            document.getElementById('modal-pane-md').style.display = tab === 'md' ? 'flex' : 'none';
            document.getElementById('modal-pane-folder').style.display = tab === 'folder' ? 'flex' : 'none';
            document.getElementById('modal-error-msg').style.display = 'none';
            document.getElementById('modal-success-msg').style.display = 'none';
        }}

        async function submitAgentModal() {{
            const errBox = document.getElementById('modal-error-msg');
            const okBox = document.getElementById('modal-success-msg');
            errBox.style.display = 'none';
            okBox.style.display = 'none';

            const isHttp = location.protocol.startsWith('http');

            if (currentModalTab === 'folder') {{
                const folderPath = document.getElementById('modal-folder-path').value.trim();
                if (!folderPath) {{
                    errBox.innerText = 'Por favor, informe o caminho da pasta.';
                    errBox.style.display = 'block';
                    return;
                }}

                if (isHttp) {{
                    try {{
                        const res = await fetch('/api/create-folder', {{
                            method: 'POST',
                            headers: {{ 'Content-Type': 'application/json' }},
                            body: JSON.stringify({{ path: folderPath }})
                        }});
                        const data = await res.json();
                        if (data.success) {{
                            okBox.innerText = `✅ Pasta criada com sucesso: ${{data.created}}`;
                            okBox.style.display = 'block';
                            setTimeout(closeAgentModal, 1000);
                        }} else {{
                            errBox.innerText = `❌ Erro: ${{data.error || 'Falha ao criar pasta'}}`;
                            errBox.style.display = 'block';
                        }}
                    }} catch (e) {{
                        errBox.innerText = `❌ Erro de comunicação: ${{e.message}}`;
                        errBox.style.display = 'block';
                    }}
                }} else {{
                    const cmd = `graf-lens-new folder "${{folderPath}}"`;
                    navigator.clipboard.writeText(cmd).then(() => {{
                        okBox.innerHTML = `📋 Modo estático: comando copiado para o terminal:<br><code>${{cmd}}</code>`;
                        okBox.style.display = 'block';
                    }});
                }}
            }} else {{
                const filePath = document.getElementById('modal-file-path').value.trim();
                const template = document.getElementById('modal-select-template').value;
                if (!filePath) {{
                    errBox.innerText = 'Por favor, informe o caminho do arquivo Markdown.';
                    errBox.style.display = 'block';
                    return;
                }}

                const contextData = {{}};
                if (Mediator.currentNode) {{
                    contextData.target = `${{Mediator.currentNode.label}} (${{Mediator.currentNode.type}})`;
                    contextData.inbound = rawEdges.filter(e => e.target === Mediator.currentNode.id).map(e => formatConnLabel(e.source)).join(', ') || 'Nenhum';
                    contextData.outbound = rawEdges.filter(e => e.source === Mediator.currentNode.id).map(e => formatConnLabel(e.target)).join(', ') || 'Nenhuma';
                }}

                if (isHttp) {{
                    try {{
                        const res = await fetch('/api/create-file', {{
                            method: 'POST',
                            headers: {{ 'Content-Type': 'application/json' }},
                            body: JSON.stringify({{
                                path: filePath,
                                template: template,
                                context: contextData
                            }})
                        }});
                        const data = await res.json();
                        if (data.success) {{
                            okBox.innerText = `✅ Arquivo criado com sucesso: ${{data.created}}`;
                            okBox.style.display = 'block';
                            setTimeout(closeAgentModal, 1000);
                        }} else {{
                            errBox.innerText = `❌ Erro: ${{data.error || 'Falha ao criar arquivo'}}`;
                            errBox.style.display = 'block';
                        }}
                    }} catch (e) {{
                        errBox.innerText = `❌ Erro de comunicação: ${{e.message}}`;
                        errBox.style.display = 'block';
                    }}
                }} else {{
                    const cmd = `graf-lens-new md "${{filePath}}" --template ${{template}}`;
                    navigator.clipboard.writeText(cmd).then(() => {{
                        okBox.innerHTML = `📋 Modo estático: comando copiado para o terminal:<br><code>${{cmd}}</code>`;
                        okBox.style.display = 'block';
                    }});
                }}
            }}
        }}
    </script>

    <!-- Modal de Criação de Recursos para Agentes -->
    <div id="agent-modal-overlay" style="display:none; position:fixed; top:0; left:0; width:100%; height:100%; background:rgba(0,0,0,0.78); backdrop-filter:blur(4px); z-index:9999; justify-content:center; align-items:center;">
        <div style="background:#181825; border:1px solid #45475a; border-radius:10px; width:490px; max-width:92vw; box-shadow:0 16px 40px rgba(0,0,0,0.6); overflow:hidden; display:flex; flex-direction:column;">
            <div style="padding:14px 18px; border-bottom:1px solid #313244; display:flex; justify-content:space-between; align-items:center; background:#11111b;">
                <span style="font-weight:700; color:#89b4fa; font-size:14px;">🤖 Criar Recurso para Agentes</span>
                <button onclick="closeAgentModal()" style="background:transparent; border:none; color:#a6adc8; font-size:16px; cursor:pointer;" title="Fechar">✕</button>
            </div>
            <div style="padding:16px 18px; display:flex; flex-direction:column; gap:12px;">
                <div style="display:flex; gap:8px;">
                    <button class="nav-tab-btn active" id="modal-tab-md" onclick="switchModalTab('md')">📄 Especificação (.md)</button>
                    <button class="nav-tab-btn" id="modal-tab-folder" onclick="switchModalTab('folder')">📁 Nova Pasta</button>
                </div>
                
                <div id="modal-pane-md" style="display:flex; flex-direction:column; gap:10px;">
                    <label style="font-size:12px; color:#a6adc8;">Template de Orquestração:</label>
                    <select id="modal-select-template" style="background:#11111b; border:1px solid #45475a; color:#cdd6f4; padding:8px; border-radius:6px; font-size:12px; outline:none;">
                        <option value="task">📋 Tarefa do Agente (TASK.md)</option>
                        <option value="spec">🏛️ Especificação Arquitetural (SPEC.md)</option>
                        <option value="context">🧠 Contexto Operacional (CONTEXT.md)</option>
                        <option value="empty">📝 Documento Vazio</option>
                    </select>
                    <label style="font-size:12px; color:#a6adc8;">Caminho Relativo do Arquivo (.md):</label>
                    <input type="text" id="modal-file-path" placeholder="Ex: docs/specs/TASK_AUTH.md" style="background:#11111b; border:1px solid #45475a; color:#cdd6f4; padding:8px 10px; border-radius:6px; font-size:12px; outline:none;">
                    <div style="font-size:11px; color:#6c7086;" id="modal-md-help">Será criado com os dados arquiteturais do nó ativo vinculados ao template.</div>
                </div>

                <div id="modal-pane-folder" style="display:none; flex-direction:column; gap:10px;">
                    <label style="font-size:12px; color:#a6adc8;">Caminho Relativo da Pasta:</label>
                    <input type="text" id="modal-folder-path" placeholder="Ex: docs/specs ou src/modules/auth" style="background:#11111b; border:1px solid #45475a; color:#cdd6f4; padding:8px 10px; border-radius:6px; font-size:12px; outline:none;">
                    <div style="font-size:11px; color:#6c7086;">Cria a pasta com segurança no projeto (proteção contra path traversal).</div>
                </div>

                <div id="modal-error-msg" style="display:none; color:#f38ba8; font-size:12px; background:rgba(243,139,168,0.15); padding:8px 10px; border-radius:6px; border:1px solid rgba(243,139,168,0.3);"></div>
                <div id="modal-success-msg" style="display:none; color:#a6e22e; font-size:12px; background:rgba(166,226,46,0.15); padding:8px 10px; border-radius:6px; border:1px solid rgba(166,226,46,0.3);"></div>
            </div>
            <div style="padding:12px 18px; border-top:1px solid #313244; display:flex; justify-content:flex-end; gap:8px; background:#11111b;">
                <button class="sublime-btn" onclick="closeAgentModal()">Cancelar</button>
                <button class="sublime-btn" id="modal-btn-submit" onclick="submitAgentModal()" style="background:#a6e22e; color:#1e1e1e; font-weight:700; border-color:#a6e22e;">Criar Recurso</button>
            </div>
        </div>
    </div>
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
