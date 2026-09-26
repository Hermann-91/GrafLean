"""
Módulo do Servidor Central Multiprojeto e Hub da Biblioteca — GrafLean Hub.
Permite gerenciar múltiplos projetos simultâneos, navegar entre workspaces,
consumir APIs de orquestração e monitorar alterações em tempo real via SSE.
"""

from __future__ import annotations
import os
import sys
import time
import json
import threading
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
from typing import Dict, Set, Optional, Any, List

# Garante importação do core
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from core.models import ProjectMetadata
from core.library import LibraryManager
from core.graph import ProjectGraph
from core.visualizer import ArchitectureVisualizer
from core.change_manager import ChangeManager, ChangeEvent
from core.creator import create_folder, create_file, create_markdown_spec, rename_resource, delete_resource


class ThreadedHubServer(ThreadingMixIn, HTTPServer):
    """Servidor HTTP multi-thread para conexões simultâneas da UI e SSE."""
    daemon_threads = True
    allow_reuse_address = True


class ProjectSession:
    """Encapsula o estado em memória e monitoramento de um projeto ativo no Hub."""

    WATCH_EXTENSIONS = (
        ".php", ".py", ".js", ".ts", ".jsx", ".tsx",
        ".blade.php", ".html", ".css", ".json", ".md"
    )
    IGNORE_DIRS = {
        ".git", "node_modules", "vendor", "__pycache__",
        ".idea", ".vscode", "dist", "build", ".gemini"
    }

    def __init__(self, project: ProjectMetadata, library_manager: LibraryManager):
        self.project = project
        self.library_manager = library_manager
        self.graph = ProjectGraph(self.project.path)
        self.visualizer = ArchitectureVisualizer(self.graph)
        self.file_snapshots: Dict[str, float] = {}
        self.clients: Set[BaseHTTPRequestHandler] = set()
        self.clients_lock = threading.Lock()
        self.initialized = False
        self.change_manager = ChangeManager(self.project.path)
        self.change_manager.subscribe(lambda evt: self.notify_clients(evt.event, evt.data))

    def initialize(self) -> None:
        """Carrega ou escaneia o grafo inicial e mapeia os arquivos monitorados."""
        cache_dir = self.library_manager.get_project_cache_dir(self.project.id)
        central_graph = os.path.join(cache_dir, "graph.json")
        local_graph = os.path.join(self.project.path, ".graflean", "graph.json")

        if os.path.isfile(central_graph):
            try:
                self.graph = ProjectGraph.load_from_file(central_graph)
                self.visualizer = ArchitectureVisualizer(self.graph)
            except Exception:
                self.rescan()
        elif self.project.ai_accelerator and os.path.isfile(local_graph):
            try:
                self.graph = ProjectGraph.load_from_file(local_graph)
                self.visualizer = ArchitectureVisualizer(self.graph)
            except Exception:
                self.rescan()
        else:
            self.rescan()

        self.file_snapshots = self.get_tracked_files()
        self.initialized = True

    def rescan(self) -> ProjectMetadata:
        """Executa varredura completa do projeto e atualiza a biblioteca."""
        self.graph.scan_project()
        self.library_manager.save_project_graph(self.project.id, self.graph)
        self.visualizer = ArchitectureVisualizer(self.graph)
        self.file_snapshots = self.get_tracked_files()
        self.notify_clients("reload")
        return self.project

    def get_tracked_files(self) -> Dict[str, float]:
        """Retorna {caminho: mtime} dos arquivos monitorados no projeto."""
        snapshots = {}
        if not os.path.isdir(self.project.path):
            return snapshots

        for root, dirs, files in os.walk(self.project.path):
            dirs[:] = [d for d in dirs if d not in self.IGNORE_DIRS and not d.startswith(".")]
            for d in dirs:
                dir_path = os.path.join(root, d)
                try:
                    snapshots[dir_path] = os.path.getmtime(dir_path)
                except OSError:
                    pass
            for file in files:
                if file in ("arch_map.html", ".arch_graph.json"):
                    continue
                if any(file.endswith(ext) for ext in self.WATCH_EXTENSIONS):
                    full_path = os.path.join(root, file)
                    try:
                        snapshots[full_path] = os.path.getmtime(full_path)
                    except OSError:
                        pass
        return snapshots

    def notify_clients(self, event_type: str = "update", data: Optional[Dict[str, Any]] = None) -> None:
        """Envia mensagem SSE reativa para todos os clientes conectados a este projeto."""
        with self.clients_lock:
            disconnected = set()
            payload = json.dumps(data or {}, ensure_ascii=False)
            for client in self.clients:
                try:
                    msg = f"event: {event_type}\ndata: {payload}\n\n".encode("utf-8")
                    client.wfile.write(msg)
                    client.wfile.flush()
                except Exception:
                    disconnected.add(client)
            self.clients -= disconnected

    def get_live_data(self) -> Dict[str, Any]:
        """Gera payload reativo para a árvore, fontes de código e nós."""
        from core.tree import ProjectTreeBuilder
        tree_builder = ProjectTreeBuilder(self.graph.root_dir, self.graph.nodes)
        tree_data = tree_builder.build().to_dict()

        # Lazy Loading: arquivos são carregados sob demanda via /api/file-content
        file_sources = {}

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

        edges_data = [
            {
                "source": edge.source_id,
                "target": edge.target_id,
                "type": edge.edge_type.value,
                "desc": edge.description or ""
            }
            for edge in self.graph.edges
        ]

        return {
            "tree": tree_data,
            "sources": file_sources,
            "nodes": nodes_data,
            "edges": edges_data
        }

    def search_project_content(self, query: str, max_results: int = 80, case_sensitive: bool = False) -> List[Dict[str, Any]]:
        """Realiza busca textual ultra-rápida (estilo ripgrep/Sublime) no conteúdo dos arquivos do projeto."""
        results = []
        if not query or not os.path.isdir(self.project.path):
            return results

        target_query = query if case_sensitive else query.lower()
        TEXT_EXTS = {
            ".php", ".py", ".js", ".ts", ".jsx", ".tsx", ".html", ".css", ".scss",
            ".json", ".md", ".yaml", ".yml", ".sh", ".bash", ".sql", ".xml", ".svg",
            ".blade.php", ".env", ".gitignore", ".editorconfig", ".txt"
        }
        IGNORE_SEARCH_DIRS = {
            ".git", "node_modules", "vendor", "__pycache__", ".venv",
            "storage", "dist", "build", ".cache", ".graflean"
        }
        proj_path = os.path.abspath(self.project.path)

        for root, dirs, files in os.walk(proj_path):
            dirs[:] = [d for d in dirs if d not in IGNORE_SEARCH_DIRS and not d.startswith(".git")]
            for file in files:
                if file in ("arch_map.html", ".arch_graph.json", "graph.json"):
                    continue
                if file.startswith(".") and file not in (".env", ".gitignore", ".editorconfig"):
                    continue
                if not any(file.endswith(ext) for ext in TEXT_EXTS) and not file.startswith("."):
                    continue

                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, proj_path)
                try:
                    if os.path.getsize(full_path) > 2 * 1024 * 1024:
                        continue
                    with open(full_path, "r", encoding="utf-8", errors="replace") as f:
                        for line_num, line in enumerate(f, start=1):
                            line_to_check = line if case_sensitive else line.lower()
                            if target_query in line_to_check:
                                snippet = line.strip()
                                if len(snippet) > 200:
                                    snippet = snippet[:200] + "..."
                                results.append({
                                    "file": rel_path,
                                    "line": line_num,
                                    "snippet": snippet,
                                    "match": query
                                })
                                if len(results) >= max_results:
                                    return results
                except Exception:
                    continue
        return results


class HubManager:
    """Gerencia as sessões em memória e sincronização em background da biblioteca."""

    def __init__(self, base_dir: Optional[str] = None):
        self.library = LibraryManager(base_dir=base_dir)
        self.sessions: Dict[str, ProjectSession] = {}
        self.sessions_lock = threading.Lock()
        self.running = False
        self._watcher_thread: Optional[threading.Thread] = None

    def get_or_create_session(self, project_id: str) -> Optional[ProjectSession]:
        """Obtém ou instancia a sessão de um projeto cadastrado."""
        with self.sessions_lock:
            if project_id in self.sessions:
                return self.sessions[project_id]

            project = self.library.get_project(project_id)
            if not project:
                return None

            session = ProjectSession(project, self.library)
            session.initialize()
            self.sessions[project_id] = session
            return session

    def register_and_index(self, path: str, name: Optional[str] = None, ai_accelerator: bool = True) -> ProjectMetadata:
        """Registra um projeto, indexa imediatamente e salva o grafo."""
        meta = self.library.register_project(path, name=name, ai_accelerator=ai_accelerator)
        session = ProjectSession(meta, self.library)
        session.rescan()
        with self.sessions_lock:
            self.sessions[meta.id] = session
        return meta

    def remove_project(self, project_id: str, purge_local_folder: bool = True) -> bool:
        """Remove o projeto da biblioteca e encerra sua sessão em memória."""
        with self.sessions_lock:
            if project_id in self.sessions:
                del self.sessions[project_id]
        return self.library.remove_project(project_id, purge_local_folder=purge_local_folder)

    def start_background_watcher(self, poll_interval: float = 1.0) -> None:
        """Inicia a verificação de alterações de arquivos para todas as sessões ativas."""
        self.running = True

        def loop():
            while self.running:
                time.sleep(poll_interval)
                with self.sessions_lock:
                    active_sessions = list(self.sessions.values())

                for session in active_sessions:
                    try:
                        current = session.get_tracked_files()
                        if len(current) != len(session.file_snapshots) or any(
                            current.get(p) != session.file_snapshots.get(p) for p in current
                        ):
                            session.change_manager.compute_filesystem_delta(session.file_snapshots, current)
                            try:
                                from core.git_tracker import GitTracker
                                status_map = GitTracker(session.project.path).get_status_map()
                                session.change_manager.update_git_status(status_map)
                            except Exception:
                                pass
                            session.rescan()
                    except Exception:
                        pass

        self._watcher_thread = threading.Thread(target=loop, daemon=True)
        self._watcher_thread.start()

    def stop(self) -> None:
        """Para o monitoramento de background."""
        self.running = False


class HubRequestHandler(BaseHTTPRequestHandler):
    """Manipulador HTTP das requisições do Hub, API REST e Workspaces."""

    server_hub: HubServer

    def log_message(self, format, *args):
        pass  # Mantém saída do terminal limpa

    def _send_json(self, status_code: int, data: dict):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(body)

    def _send_html(self, status_code: int, html_content: str):
        body = html_content.encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def _get_project_context(self) -> Optional[ProjectSession]:
        """Identifica a sessão ativa do projeto por parâmetro ou cabeçalho Referer."""
        # 1. Tenta identificar na URL /p/<project_id> ou /events/<project_id>
        parts = self.path.split("?")[0].strip("/").split("/")
        if len(parts) >= 2 and parts[0] in ("p", "events", "live-data"):
            session = self.server_hub.manager.get_or_create_session(parts[1])
            if session:
                return session

        # 2. Tenta identificar via cabeçalho Referer
        referer = self.headers.get("Referer", "")
        if referer:
            ref_path = urllib.parse.urlparse(referer).path
            ref_parts = ref_path.strip("/").split("/")
            if len(ref_parts) >= 2 and ref_parts[0] == "p":
                return self.server_hub.manager.get_or_create_session(ref_parts[1])

        # 3. Fallback para primeiro projeto cadastrado se existir
        projects = self.server_hub.manager.library.list_projects()
        if projects:
            return self.server_hub.manager.get_or_create_session(projects[0].id)
        return None

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path.rstrip("/")
        if not path:
            path = "/"

        # Rota 1: Manifesto PWA
        if path == "/manifest.json":
            manifest = {
                "name": "GrafLean IDE Hub",
                "short_name": "GrafLean",
                "start_url": "/",
                "display": "standalone",
                "background_color": "#0c0d0e",
                "theme_color": "#141517",
                "description": "Architecture-First IDE & Top-Down Lens Hub"
            }
            self._send_json(200, manifest)
            return

        # Rota PWA: Service Worker para cache e instalação no desktop
        if path == "/service-worker.js":
            sw_code = """
            const CACHE_NAME = 'graflean-hub-v1';
            self.addEventListener('install', (e) => {
                self.skipWaiting();
            });
            self.addEventListener('activate', (e) => {
                e.waitUntil(clients.claim());
            });
            self.addEventListener('fetch', (e) => {
                if (e.request.url.includes('/api/') || e.request.url.includes('/events')) {
                    return;
                }
                e.respondWith(fetch(e.request).catch(() => caches.match(e.request)));
            });
            """
            body = sw_code.strip().encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/javascript; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        # Rota 2: Dashboard Hub Central da Biblioteca
        if path == "/":
            self._send_html(200, self._render_hub_dashboard())
            return

        # Rota 3: API para listar projetos cadastrados
        if path == "/api/projects":
            projects = [p.to_dict() for p in self.server_hub.manager.library.list_projects()]
            self._send_json(200, {"success": True, "projects": projects})
            return

        # Rota 4: Workspace do Projeto (/p/<project_id>)
        if path.startswith("/p/"):
            project_id = path[3:]
            session = self.server_hub.manager.get_or_create_session(project_id)
            if not session:
                self._send_html(404, "<h1>404 — Projeto não encontrado no GrafLean Hub</h1><p><a href='/'>Voltar para a Biblioteca</a></p>")
                return

            content = session.visualizer.render_html()

            # Injeta botão de retorno para a biblioteca no cabeçalho do Workspace
            btn_hub = (
                '<a href="/" style="display:inline-flex; align-items:center; gap:5px; text-decoration:none; '
                'color:#66d9ef; background:#141414; border:1px solid #282828; padding:3px 10px; border-radius:6px; '
                'font-size:12px; font-weight:600; margin-right:8px;" title="Voltar ao Hub da Biblioteca">◀ Biblioteca</a>'
            )
            content = content.replace('<div class="brand-title">', btn_hub + '<div class="brand-title">', 1)
            self._send_html(200, content)
            return

        # Rota 5: Canal SSE para Live Reload (/events ou /events/<project_id>)
        if path == "/events" or path.startswith("/events/"):
            session = self._get_project_context()
            if not session:
                self.send_response(404)
                self.end_headers()
                return

            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "keep-alive")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()

            with session.clients_lock:
                session.clients.add(self)

            try:
                while self.server_hub.manager.running:
                    time.sleep(1)
            except Exception:
                pass
            finally:
                with session.clients_lock:
                    session.clients.discard(self)
            return

        # Rota 6: API de Live Data (/api/data e /api/live-data)
        if path in ("/api/data", "/api/live-data"):
            session = self._get_project_context()
            if not session:
                self._send_json(404, {"error": "Nenhum projeto associado à sessão."})
                return
            self._send_json(200, {"success": True, "data": session.get_live_data()})
            return

        # Rota 7: API para obter conteúdo de arquivo sob demanda (Lazy Loading)
        if path == "/api/file-content":
            session = self._get_project_context()
            if not session:
                self._send_json(404, {"success": False, "error": "Sessão do projeto não identificada."})
                return
            query = urllib.parse.parse_qs(parsed.query)
            target_path = query.get("path", [""])[0].strip()
            if not target_path:
                self._send_json(400, {"success": False, "error": "Parâmetro 'path' não fornecido."})
                return

            proj_root = os.path.abspath(session.project.path)
            full_path = target_path if os.path.isabs(target_path) else os.path.join(proj_root, target_path)
            full_path = os.path.abspath(full_path)

            if not full_path.startswith(proj_root):
                self._send_json(403, {"success": False, "error": "Acesso não autorizado fora do diretório do projeto."})
                return

            if not os.path.isfile(full_path):
                self._send_json(404, {"success": False, "error": "Arquivo não encontrado."})
                return

            try:
                with open(full_path, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()
                self._send_json(200, {"success": True, "path": full_path, "content": content})
            except Exception as e:
                self._send_json(500, {"success": False, "error": str(e)})
            return

        self._send_json(404, {"error": f"Rota não encontrada: {path}"})

    def do_POST(self):
        content_len = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_len) if content_len > 0 else b"{}"

        try:
            payload = json.loads(body.decode("utf-8")) if body else {}
        except Exception:
            payload = {}

        path = self.path.rstrip("/")

        # API: Encerrar Servidor Python (Shutdown)
        if path == "/api/shutdown":
            self._send_json(200, {"success": True, "message": "Servidor GrafLean encerrado."})
            def _terminate():
                time.sleep(0.2)
                if hasattr(self.server_hub, "_on_shutdown_test_hook"):
                    self.server_hub._on_shutdown_test_hook()
                else:
                    os._exit(0)
            threading.Thread(target=_terminate, daemon=True).start()
            return

        # API: Adicionar novo projeto
        if path == "/api/projects/add":
            proj_path = payload.get("path")
            proj_name = payload.get("name")
            ai_acc = payload.get("ai_accelerator", True)

            if not proj_path or not os.path.isdir(os.path.expanduser(proj_path)):
                self._send_json(400, {"success": False, "error": "Caminho do diretório inválido ou inexistente."})
                return

            try:
                meta = self.server_hub.manager.register_and_index(proj_path, name=proj_name, ai_accelerator=ai_acc)
                self._send_json(200, {"success": True, "project": meta.to_dict()})
            except Exception as e:
                self._send_json(500, {"success": False, "error": str(e)})
            return

        # API: Alternar modo IA
        if path == "/api/projects/toggle-ai":
            pid = payload.get("project_id")
            enable = payload.get("enable", True)
            ok = self.server_hub.manager.library.toggle_ai_accelerator(pid, enable=enable)
            self._send_json(200, {"success": ok})
            return

        # API: Forçar re-varredura
        if path == "/api/projects/rescan":
            pid = payload.get("project_id")
            session = self.server_hub.manager.get_or_create_session(pid)
            if not session:
                self._send_json(404, {"success": False, "error": "Projeto não encontrado."})
                return
            meta = session.rescan()
            self._send_json(200, {"success": True, "project": meta.to_dict()})
            return

        # API: Remover projeto
        if path == "/api/projects/remove":
            pid = payload.get("project_id")
            purge = payload.get("purge_local", True)
            ok = self.server_hub.manager.remove_project(pid, purge_local_folder=purge)
            self._send_json(200, {"success": ok})
            return

        # Ações do Sistema de Arquivos do Projeto Ativo
        session = self._get_project_context()
        if not session:
            self._send_json(404, {"success": False, "error": "Sessão do projeto não identificada."})
            return

        proj_root = session.project.path

        if path == "/api/save-file":
            rel_path = payload.get("path", "").strip()
            content = payload.get("content", "")
            full_path = os.path.join(proj_root, rel_path)
            try:
                with open(full_path, "w", encoding="utf-8") as f:
                    f.write(content)
                session.rescan()
                self._send_json(200, {"success": True, "message": "Arquivo salvo com sucesso!"})
            except Exception as e:
                self._send_json(500, {"success": False, "error": str(e)})
            return

        if path == "/api/search-content":
            query = payload.get("query", "").strip()
            case_sensitive = payload.get("case_sensitive", False)
            max_results = min(int(payload.get("max_results", 80)), 200)

            if not query:
                self._send_json(200, {"success": True, "results": []})
                return

            results = session.search_project_content(query, max_results=max_results, case_sensitive=case_sensitive)
            self._send_json(200, {"success": True, "results": results})
            return

        if path == "/api/file-content":
            rel_path = payload.get("path", "").strip()
            if not rel_path:
                self._send_json(400, {"success": False, "error": "Parâmetro 'path' não fornecido."})
                return
            full_path = rel_path if os.path.isabs(rel_path) else os.path.join(proj_root, rel_path)
            full_path = os.path.abspath(full_path)
            if not full_path.startswith(os.path.abspath(proj_root)):
                self._send_json(403, {"success": False, "error": "Acesso não autorizado fora do diretório do projeto."})
                return
            if not os.path.isfile(full_path):
                self._send_json(404, {"success": False, "error": "Arquivo não encontrado."})
                return
            try:
                with open(full_path, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()
                self._send_json(200, {"success": True, "path": full_path, "content": content})
            except Exception as e:
                self._send_json(500, {"success": False, "error": str(e)})
            return

        # Rota: Alterar status de execução da IA
        if path == "/api/ai-state":
            target_path = payload.get("path", "").strip()
            state = payload.get("state", "idle").strip()
            if not target_path:
                self._send_json(400, {"success": False, "error": "Parâmetro 'path' não fornecido."})
                return
            evt = session.change_manager.set_ai_state(target_path, state)
            self._send_json(200, {
                "success": True,
                "event": evt.data,
                "summary": session.change_manager.get_summary()
            })
            return

        # Rota: Consultar resumo de alterações ativas (Git + IA)
        if path == "/api/changes":
            self._send_json(200, {
                "success": True,
                "summary": session.change_manager.get_summary()
            })
            return

        if path == "/api/create-folder":
            rel_path = payload.get("path", "").strip()
            try:
                full_path = create_folder(proj_root, rel_path)
                session.rescan()
                self._send_json(200, {"success": True, "created": full_path, "data": session.get_live_data()})
            except Exception as e:
                self._send_json(400, {"success": False, "error": str(e)})
            return

        if path == "/api/create-file":
            rel_path = payload.get("path", "").strip()
            content = payload.get("content", "")
            try:
                full_path = create_file(proj_root, rel_path, content=content)
                session.rescan()
                self._send_json(200, {"success": True, "created": full_path, "data": session.get_live_data()})
            except Exception as e:
                self._send_json(400, {"success": False, "error": str(e)})
            return

        if path == "/api/rename":
            old_path = payload.get("old_path", "").strip()
            new_name = payload.get("new_name", "").strip()
            try:
                renamed = rename_resource(proj_root, old_path, new_name)
                session.rescan()
                self._send_json(200, {"success": True, "renamed": renamed, "data": session.get_live_data()})
            except Exception as e:
                self._send_json(400, {"success": False, "error": str(e)})
            return

        if path == "/api/delete":
            rel_path = payload.get("path", "").strip()
            try:
                deleted = delete_resource(proj_root, rel_path)
                session.rescan()
                self._send_json(200, {"success": True, "deleted": deleted, "data": session.get_live_data()})
            except Exception as e:
                self._send_json(400, {"success": False, "error": str(e)})
            return

        self._send_json(404, {"success": False, "error": f"Endpoint não reconhecido: {path}"})

    def _render_hub_dashboard(self) -> str:
        """Renderiza a interface Web da Biblioteca de Projetos com estética Monokai OLED Glassmorphic."""
        projects = self.server_hub.manager.library.list_projects()

        cards_html = ""
        if not projects:
            cards_html = """
            <div class="empty-state">
                <div style="font-size: 48px; margin-bottom: 12px;">📁</div>
                <h3>Nenhum projeto cadastrado na biblioteca</h3>
                <p>Cadastre um repositório para analisar a arquitetura e acelerar seus agentes de IA.</p>
                <button class="btn btn-primary" onclick="openModal()" style="margin-top: 15px;">➕ Adicionar Primeiro Projeto</button>
            </div>
            """
        else:
            for p in projects:
                mode_badge = (
                    '<span class="badge badge-ai" title="Mantém .graflean/ local protegido no .gitignore">⚡ Acelerador de IA</span>'
                    if p.ai_accelerator else
                    '<span class="badge badge-zero" title="Zero poluição local — 100% no cache ~/.graflean/">🛡️ Zero-Footprint</span>'
                )
                cycle_badge = (
                    '<span style="color:#f92672; font-weight:bold;">⚠️ Ciclos Detectados</span>'
                    if p.has_cycles else
                    '<span style="color:#a6e22e; font-weight:bold;">✅ Acíclico</span>'
                )

                cards_html += f"""
                <div class="project-card" id="card-{p.id}">
                    <div class="card-header">
                        <div>
                            <div class="card-title">{p.name}</div>
                            <div class="card-path" title="{p.path}">{p.path}</div>
                        </div>
                        {mode_badge}
                    </div>

                    <div class="metrics-grid">
                        <div class="metric-item">
                            <div class="metric-label">NÓS</div>
                            <div class="metric-val">{p.node_count}</div>
                        </div>
                        <div class="metric-item">
                            <div class="metric-label">CONEXÕES</div>
                            <div class="metric-val">{p.edge_count}</div>
                        </div>
                        <div class="metric-item">
                            <div class="metric-label">INSTABILIDADE (I)</div>
                            <div class="metric-val">{p.avg_instability}</div>
                        </div>
                        <div class="metric-item">
                            <div class="metric-label">INTEGRIDADE</div>
                            <div class="metric-val" style="font-size: 13px;">{cycle_badge}</div>
                        </div>
                    </div>

                    <div class="card-footer">
                        <a href="/p/{p.id}" target="_blank" class="btn btn-primary" title="Abrir Workspace em nova aba do navegador">🚀 Abrir Workspace</a>
                        <div style="display:flex; gap:6px;">
                            <button class="btn btn-secondary" onclick="rescanProject('{p.id}')" title="Re-escanear">🔄</button>
                            <button class="btn btn-secondary" onclick="toggleAi('{p.id}', {str(not p.ai_accelerator).lower()})" title="Alternar Modo IA">⚡</button>
                            <button class="btn btn-danger" onclick="removeProject('{p.id}', '{p.name}')" title="Remover da Biblioteca">🗑️</button>
                        </div>
                    </div>
                </div>
                """

        return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>GrafLean Hub — Biblioteca de Projetos</title>
    <link rel="manifest" href="/manifest.json">
    <style>
        :root {{
            --bg-base: #000000;
            --bg-surface: rgba(10, 10, 10, 0.85);
            --border: rgba(255, 255, 255, 0.08);
            --text-main: #f8f8f2;
            --text-muted: #75715e;
            --accent-green: #a6e22e;
            --accent-cyan: #66d9ef;
            --accent-pink: #f92672;
            --accent-purple: #ae81ff;
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            background-color: var(--bg-base);
            color: var(--text-main);
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            min-height: 100vh;
            padding: 30px 40px;
        }}
        .hub-container {{ max-width: 1200px; margin: 0 auto; }}
        header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 35px;
            padding-bottom: 20px;
            border-bottom: 1px solid var(--border);
        }}
        .brand {{ display: flex; align-items: center; gap: 12px; }}
        .brand h1 {{
            font-size: 26px;
            font-weight: 800;
            background: linear-gradient(135deg, var(--accent-green), var(--accent-cyan));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}
        .brand span {{ color: var(--text-muted); font-size: 13px; }}
        .header-actions {{ display: flex; gap: 10px; }}
        .btn {{
            padding: 9px 16px;
            border-radius: 8px;
            font-size: 13px;
            font-weight: 600;
            cursor: pointer;
            border: 1px solid transparent;
            transition: all 0.2s ease;
            text-decoration: none;
            display: inline-flex;
            align-items: center;
            gap: 6px;
        }}
        .btn-primary {{
            background: linear-gradient(135deg, #272822, #1e1f1c);
            color: var(--accent-green);
            border-color: var(--accent-green);
        }}
        .btn-primary:hover {{
            background: var(--accent-green);
            color: #111;
            box-shadow: 0 0 15px rgba(166, 226, 46, 0.4);
        }}
        .btn-secondary {{
            background: #141414;
            color: var(--text-main);
            border-color: var(--border);
        }}
        .btn-secondary:hover {{ background: #222222; border-color: rgba(255,255,255,0.2); }}
        .btn-danger {{
            background: rgba(249, 38, 114, 0.15);
            color: var(--accent-pink);
            border-color: rgba(249, 38, 114, 0.3);
        }}
        .btn-danger:hover {{ background: var(--accent-pink); color: #fff; }}
        .grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(360px, 1fr));
            gap: 22px;
        }}
        .project-card {{
            background: var(--bg-surface);
            backdrop-filter: blur(14px);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 20px;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            transition: transform 0.2s, border-color 0.2s, box-shadow 0.2s;
        }}
        .project-card:hover {{
            transform: translateY(-3px);
            border-color: rgba(102, 217, 239, 0.3);
            box-shadow: 0 8px 24px rgba(0, 0, 0, 0.4);
        }}
        .card-header {{ display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 15px; }}
        .card-title {{ font-size: 18px; font-weight: 700; color: #fff; }}
        .card-path {{ font-size: 12px; color: var(--text-muted); margin-top: 4px; font-family: monospace; max-width: 230px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}
        .badge {{
            font-size: 10px;
            font-weight: 700;
            padding: 3px 8px;
            border-radius: 6px;
            text-transform: uppercase;
        }}
        .badge-ai {{ background: rgba(166, 226, 46, 0.15); color: var(--accent-green); border: 1px solid var(--accent-green); }}
        .badge-zero {{ background: rgba(102, 217, 239, 0.15); color: var(--accent-cyan); border: 1px solid var(--accent-cyan); }}
        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 10px;
            background: rgba(0, 0, 0, 0.3);
            padding: 12px;
            border-radius: 8px;
            margin-bottom: 18px;
        }}
        .metric-item {{ display: flex; flex-direction: column; }}
        .metric-label {{ font-size: 10px; font-weight: 600; color: var(--text-muted); letter-spacing: 0.5px; }}
        .metric-val {{ font-size: 15px; font-weight: 700; color: var(--text-main); margin-top: 2px; }}
        .card-footer {{ display: flex; justify-content: space-between; align-items: center; }}
        .empty-state {{
            grid-column: 1 / -1;
            text-align: center;
            padding: 60px 20px;
            background: var(--bg-surface);
            border: 1px dashed var(--border);
            border-radius: 12px;
        }}
        /* Modal */
        .modal-overlay {{
            position: fixed;
            top: 0; left: 0; right: 0; bottom: 0;
            background: rgba(0, 0, 0, 0.75);
            backdrop-filter: blur(8px);
            display: none;
            justify-content: center;
            align-items: center;
            z-index: 1000;
        }}
        .modal-box {{
            background: #18191e;
            border: 1px solid rgba(255, 255, 255, 0.12);
            border-radius: 14px;
            width: 480px;
            padding: 26px;
            box-shadow: 0 16px 40px rgba(0,0,0,0.6);
        }}
        .modal-title {{ font-size: 19px; font-weight: 700; margin-bottom: 18px; }}
        .form-group {{ margin-bottom: 15px; }}
        .form-group label {{ display: block; font-size: 12px; font-weight: 600; margin-bottom: 6px; color: var(--text-muted); }}
        .form-group input[type="text"] {{
            width: 100%;
            padding: 10px 12px;
            border-radius: 8px;
            background: #0e0f12;
            border: 1px solid var(--border);
            color: #fff;
            font-size: 13px;
        }}
        .form-group input[type="text"]:focus {{ outline: none; border-color: var(--accent-cyan); }}
        .checkbox-label {{ display: flex; align-items: center; gap: 8px; font-size: 13px; cursor: pointer; color: var(--text-main); }}
        .toast {{
            position: fixed; bottom: 20px; right: 20px;
            background: #1e1f29; border: 1px solid var(--border);
            color: #fff; padding: 12px 18px; border-radius: 8px;
            font-size: 13px; font-weight: 600; box-shadow: 0 4px 14px rgba(0,0,0,0.5);
            display: none; z-index: 2000;
        }}
    </style>
</head>
<body>
    <div class="hub-container">
        <header>
            <div class="brand">
                <div style="font-size: 32px;">🏛️</div>
                <div>
                    <h1>GrafLean Hub</h1>
                    <span>Workspace Centralizado & Architecture-First IDE</span>
                </div>
            </div>
            <div class="header-actions">
                <button class="btn btn-secondary" id="btn-install-pwa" style="display:none;" onclick="installPwa()">📲 Instalar App</button>
                <button class="btn btn-secondary" onclick="location.reload()">🔄 Atualizar</button>
                <button class="btn btn-primary" onclick="openModal()">➕ Novo Projeto</button>
                <button class="btn btn-secondary" onclick="shutdownServer()" title="Encerrar servidor GrafLean (finaliza processo Python e fecha janela)" style="color:var(--accent-pink); border-color:rgba(249,38,114,0.3); padding:8px 12px;">⏻</button>
            </div>
        </header>

        <main class="grid">
            {cards_html}
        </main>
    </div>

    <!-- Modal Adicionar Projeto -->
    <div class="modal-overlay" id="add-modal">
        <div class="modal-box">
            <div class="modal-title">➕ Adicionar Projeto ao GrafLean Hub</div>
            <div class="form-group">
                <label>CAMINHO ABSOLUTO DA PASTA NO DISCO</label>
                <input type="text" id="proj-path" placeholder="/home/usuario/meu-projeto">
            </div>
            <div class="form-group">
                <label>NOME DE EXIBIÇÃO (OPCIONAL)</label>
                <input type="text" id="proj-name" placeholder="Meu Projeto">
            </div>
            <div class="form-group">
                <label class="checkbox-label">
                    <input type="checkbox" id="proj-ai" checked>
                    <span>Ativar Acelerador de IA (cria <code>.graflean/</code> local com auto-gitignore)</span>
                </label>
            </div>
            <div style="display:flex; justify-content:flex-end; gap:10px; margin-top:24px;">
                <button class="btn btn-secondary" onclick="closeModal()">Cancelar</button>
                <button class="btn btn-primary" onclick="submitAddProject()">Cadastrar e Escanear</button>
            </div>
        </div>
    </div>

    <div class="toast" id="toast"></div>

    <script>
        // PWA Service Worker & Instalação
        if ('serviceWorker' in navigator) {{
            navigator.serviceWorker.register('/service-worker.js').catch(() => {{}});
        }}
        let deferredPrompt = null;
        window.addEventListener('beforeinstallprompt', (e) => {{
            e.preventDefault();
            deferredPrompt = e;
            const btn = document.getElementById('btn-install-pwa');
            if (btn) btn.style.display = 'inline-flex';
        }});
        async function installPwa() {{
            if (!deferredPrompt) return;
            deferredPrompt.prompt();
            deferredPrompt = null;
        }}

        function shutdownServer() {{
            if (!confirm("Deseja realmente desligar o GrafLean Hub? O processo Python será finalizado e a janela será fechada.")) return;
            fetch('/api/shutdown', {{ method: 'POST', headers: {{ 'Content-Type': 'application/json' }} }})
                .finally(() => {{
                    try {{
                        window.open('', '_self', '');
                        window.close();
                    }} catch (e) {{}}
                    document.body.innerHTML = `
                        <div style="height:100vh; display:flex; flex-direction:column; align-items:center; justify-content:center; background:#000; color:#f8f8f2; font-family:sans-serif; text-align:center;">
                            <div style="font-size:48px; margin-bottom:16px;">🛑</div>
                            <h2 style="margin:0 0 10px 0; font-size:22px;">GrafLean Hub Encerrado</h2>
                            <p style="color:#75715e; font-size:14px; margin:0 0 20px 0;">O processo Python foi finalizado com sucesso. Você já pode fechar esta aba.</p>
                            <button onclick="window.close()" class="btn btn-secondary">Fechar Aba</button>
                        </div>
                    `;
                }});
        }}

        function showToast(msg) {{
            const t = document.getElementById('toast');
            t.innerText = msg;
            t.style.display = 'block';
            setTimeout(() => {{ t.style.display = 'none'; }}, 3000);
        }}

        function openModal() {{ document.getElementById('add-modal').style.display = 'flex'; }}
        function closeModal() {{ document.getElementById('add-modal').style.display = 'none'; }}

        async function submitAddProject() {{
            const path = document.getElementById('proj-path').value.trim();
            const name = document.getElementById('proj-name').value.trim();
            const ai = document.getElementById('proj-ai').checked;
            if (!path) return alert('Por favor, informe o caminho do projeto.');

            try {{
                const res = await fetch('/api/projects/add', {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{ path, name, ai_accelerator: ai }})
                }});
                const data = await res.json();
                if (data.success) {{
                    closeModal();
                    location.reload();
                }} else {{
                    alert('Erro: ' + (data.error || 'Falha ao cadastrar'));
                }}
            }} catch (err) {{
                alert('Erro de conexão com o servidor do Hub.');
            }}
        }}

        async function rescanProject(pid) {{
            showToast('🔄 Re-escaneando arquitetura...');
            const res = await fetch('/api/projects/rescan', {{
                method: 'POST',
                headers: {{ 'Content-Type': 'application/json' }},
                body: JSON.stringify({{ project_id: pid }})
            }});
            const data = await res.json();
            if (data.success) {{
                showToast('✅ Varredura concluída!');
                setTimeout(() => location.reload(), 600);
            }}
        }}

        async function toggleAi(pid, enable) {{
            const res = await fetch('/api/projects/toggle-ai', {{
                method: 'POST',
                headers: {{ 'Content-Type': 'application/json' }},
                body: JSON.stringify({{ project_id: pid, enable }})
            }});
            const data = await res.json();
            if (data.success) location.reload();
        }}

        async function removeProject(pid, name) {{
            if (!confirm(`Remover "${{name}}" da biblioteca do GrafLean?`)) return;
            const res = await fetch('/api/projects/remove', {{
                method: 'POST',
                headers: {{ 'Content-Type': 'application/json' }},
                body: JSON.stringify({{ project_id: pid, purge_local: true }})
            }});
            const data = await res.json();
            if (data.success) location.reload();
        }}
    </script>
</body>
</html>
"""


class HubServer:
    """Servidor Principal GrafLean Hub — PWA Local."""

    def __init__(self, base_dir: Optional[str] = None, host: str = "127.0.0.1", port: int = 7357):
        self.host = host
        self.port = port
        self.manager = HubManager(base_dir=base_dir)
        self.server: Optional[ThreadedHubServer] = None
        self._server_thread: Optional[threading.Thread] = None

    def start(self, block: bool = False, open_browser: bool = False) -> None:
        """Inicia o servidor e o monitoramento em background."""
        self.manager.start_background_watcher()

        handler_cls = HubRequestHandler
        handler_cls.server_hub = self

        self.server = ThreadedHubServer((self.host, self.port), handler_cls)
        # Atualiza a porta real se vinculada a porta efêmera (0)
        self.port = self.server.server_port

        if open_browser:
            import webbrowser
            webbrowser.open(f"http://{self.host}:{self.port}")

        if block:
            try:
                self.server.serve_forever()
            except KeyboardInterrupt:
                self.stop()
        else:
            self._server_thread = threading.Thread(target=self.server.serve_forever, daemon=True)
            self._server_thread.start()

    def stop(self) -> None:
        """Encerra o servidor de forma limpa."""
        self.manager.stop()
        if self.server:
            self.server.shutdown()
            self.server.server_close()
