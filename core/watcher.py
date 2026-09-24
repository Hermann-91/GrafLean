"""
Módulo de Monitoramento Contínuo e Sincronização em Tempo Real (Watch Mode).
Utiliza exclusivamente a biblioteca padrão do Python (http.server, threading, time, os).
Detecta alterações no sistema de arquivos, re-escaneia o grafo arquitetural
e notifica os navegadores conectados via Server-Sent Events (SSE) para live reload instantâneo.
"""

import os
import sys
import time
import json
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
from typing import Dict, Set, Optional, Any

# Garante importação do core
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from core.graph import ProjectGraph
from core.visualizer import ArchitectureVisualizer


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """Servidor HTTP multi-thread para conexões simultâneas de páginas e SSE."""
    daemon_threads = True
    allow_reuse_address = True


class ArchitectureWatcher:
    """
    Monitor de Arquitetura em Tempo Real.
    Combina varredura de mtime a cada intervalo definido com servidor HTTP/SSE integrado.
    """

    WATCH_EXTENSIONS = (
        ".php", ".py", ".js", ".ts", ".jsx", ".tsx",
        ".blade.php", ".html", ".css", ".json", ".md"
    )

    IGNORE_DIRS = {
        ".git", "node_modules", "vendor", "__pycache__",
        ".idea", ".vscode", "dist", "build", ".gemini"
    }

    def __init__(self, target_dir: str, port: int = 7357, poll_interval: float = 0.8):
        self.target_dir = os.path.abspath(target_dir)
        self.port = port
        self.poll_interval = poll_interval
        self.graph = ProjectGraph(self.target_dir)
        self.visualizer = ArchitectureVisualizer(self.graph)
        self.html_path = os.path.join(self.target_dir, "arch_map.html")

        self.file_snapshots: Dict[str, float] = {}
        self.clients: Set[BaseHTTPRequestHandler] = set()
        self.clients_lock = threading.Lock()
        self.running = False
        self.server: Optional[ThreadedHTTPServer] = None
        self._watcher_thread: Optional[threading.Thread] = None

    def get_tracked_files(self) -> Dict[str, float]:
        """Varre o diretório e retorna um dicionário {caminho_absoluto: mtime}."""
        snapshots = {}
        for root, dirs, files in os.walk(self.target_dir):
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

    def has_changes(self, current: Dict[str, float]) -> bool:
        """Verifica se houve arquivos adicionados, modificados ou removidos."""
        if len(current) != len(self.file_snapshots):
            return True
        for path, mtime in current.items():
            if path not in self.file_snapshots or self.file_snapshots[path] != mtime:
                return True
        return False

    def notify_clients(self):
        """Dispara evento SSE 'update' reativo para todos os navegadores conectados."""
        with self.clients_lock:
            disconnected = set()
            for client in self.clients:
                try:
                    msg = "event: update\ndata: {}\n\n".encode("utf-8")
                    client.wfile.write(msg)
                    client.wfile.flush()
                except Exception:
                    disconnected.add(client)
            self.clients -= disconnected

    def get_live_data(self) -> Dict[str, Any]:
        """Retorna os dados reativos da árvore e arquivos em memória."""
        from core.tree import ProjectTreeBuilder
        tree_builder = ProjectTreeBuilder(self.graph.root_dir, self.graph.nodes)
        tree_data = tree_builder.build().to_dict()
        file_sources = {}
        all_paths = set(node.file_path for node in self.graph.nodes.values() if node.file_path)
        if hasattr(tree_builder, "files_map"):
            for rel_f in tree_builder.files_map.keys():
                all_paths.add(os.path.join(self.graph.root_dir, rel_f))
        for f_path in all_paths:
            if os.path.isfile(f_path) and os.path.getsize(f_path) <= 500 * 1024:
                try:
                    with open(f_path, "r", encoding="utf-8", errors="replace") as f:
                        file_sources[f_path] = f.read()
                except Exception:
                    pass
        return {
            "tree": tree_data,
            "sources": file_sources,
            "nodes": [n.to_dict() for n in self.graph.nodes.values()],
            "edges": [e.to_dict() for e in self.graph.edges]
        }

    def build_initial(self) -> float:
        """Executa a primeira indexação e gera o HTML inicial."""
        start = time.perf_counter()
        self.graph.scan_project()
        self.graph.save_to_file()
        self.visualizer.generate_html(self.html_path)
        self.file_snapshots = self.get_tracked_files()
        duration_ms = (time.perf_counter() - start) * 1000
        return duration_ms

    def start_watching(self, open_browser: bool = True):
        """Inicia o monitoramento de arquivos e o servidor HTTP."""
        duration_ms = self.build_initial()
        print(f"🚀 [Watch Mode] Indexação inicial concluída em {duration_ms:.1f}ms!")
        print(f"📊 {len(self.graph.nodes)} nós e {len(self.graph.edges)} conexões mapeadas.")
        print(f"📡 Servidor ativo em: http://localhost:{self.port}")
        print(f"👀 Monitorando alterações em: {self.target_dir}")
        print("Pressione Ctrl+C para encerrar.\n")

        if open_browser:
            import webbrowser
            webbrowser.open(f"http://localhost:{self.port}")

        self.running = True
        self._watcher_thread = threading.Thread(target=self._watch_loop, daemon=True)
        self._watcher_thread.start()

        self._start_server()

    def _watch_loop(self):
        """Loop de monitoramento que roda em thread secundária."""
        while self.running:
            time.sleep(self.poll_interval)
            current = self.get_tracked_files()
            if self.has_changes(current):
                start = time.perf_counter()
                try:
                    self.graph.scan_project()
                    self.graph.save_to_file()
                    self.visualizer.generate_html(self.html_path)
                    self.file_snapshots = current
                    elapsed = (time.perf_counter() - start) * 1000
                    print(f"🔄 [Watch] Alteração detectada! Mapa atualizado em {elapsed:.1f}ms. Sincronizando navegador...")
                    self.notify_clients()
                except Exception as e:
                    print(f"⚠️ [Watch] Erro ao re-escanear: {e}")

    def _start_server(self):
        from core.creator import create_folder, create_markdown_spec, rename_resource, delete_resource, TEMPLATES
        watcher = self

        class WatcherHandler(BaseHTTPRequestHandler):
            def log_message(self, format, *args):
                pass  # Mantém o terminal limpo

            def _send_json(self, status_code: int, data: dict):
                body = json.dumps(data, ensure_ascii=False).encode("utf-8")
                self.send_response(status_code)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
                self.send_header("Access-Control-Allow-Headers", "Content-Type")
                self.send_header("Access-Control-Allow-Private-Network", "true")
                self.end_headers()
                self.wfile.write(body)

            def do_OPTIONS(self):
                self.send_response(204)
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
                self.send_header("Access-Control-Allow-Headers", "Content-Type")
                self.send_header("Access-Control-Allow-Private-Network", "true")
                self.end_headers()

            def do_GET(self):
                if self.path == "/events":
                    self.send_response(200)
                    self.send_header("Content-Type", "text/event-stream")
                    self.send_header("Cache-Control", "no-cache")
                    self.send_header("Connection", "keep-alive")
                    self.send_header("Access-Control-Allow-Origin", "*")
                    self.end_headers()

                    with watcher.clients_lock:
                        watcher.clients.add(self)

                    try:
                        while watcher.running:
                            time.sleep(15)
                            self.wfile.write(b": ping\n\n")
                            self.wfile.flush()
                    except Exception:
                        pass
                    finally:
                        with watcher.clients_lock:
                            watcher.clients.discard(self)

                elif self.path == "/api/templates":
                    self._send_json(200, {
                        "templates": list(TEMPLATES.keys()),
                        "examples": {k: TEMPLATES[k][:120] + "..." for k in TEMPLATES}
                    })

                elif self.path == "/api/data":
                    return self._send_json(200, {
                        "success": True,
                        "data": watcher.get_live_data()
                    })

                elif self.path in ("/", "/index.html", "/arch_map.html"):
                    if not os.path.exists(watcher.html_path):
                        self.send_error(404, "Mapa arquitetural não encontrado.")
                        return
                    try:
                        with open(watcher.html_path, "rb") as f:
                            content = f.read()
                        self.send_response(200)
                        self.send_header("Content-Type", "text/html; charset=utf-8")
                        self.send_header("Content-Length", str(len(content)))
                        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
                        self.end_headers()
                        self.wfile.write(content)
                    except Exception as e:
                        self.send_error(500, str(e))
                else:
                    self.send_error(404, "Arquivo não encontrado.")

            def do_POST(self):
                content_len = int(self.headers.get("Content-Length", 0))
                raw_body = self.rfile.read(content_len).decode("utf-8") if content_len > 0 else "{}"
                try:
                    payload = json.loads(raw_body)
                except Exception:
                    payload = {}

                if self.path == "/api/create-folder":
                    folder_path = payload.get("path", "").strip()
                    if not folder_path:
                        return self._send_json(400, {"success": False, "error": "Caminho da pasta é obrigatório."})
                    try:
                        created = create_folder(watcher.target_dir, folder_path)
                        rel_created = os.path.relpath(created, watcher.target_dir)
                        watcher.build_initial()
                        watcher.notify_clients()
                        return self._send_json(200, {"success": True, "created": rel_created, "data": watcher.get_live_data()})
                    except Exception as e:
                        return self._send_json(400, {"success": False, "error": str(e)})

                elif self.path == "/api/create-file":
                    file_path = payload.get("path", "").strip()
                    custom_content = payload.get("content", "")

                    if not file_path:
                        return self._send_json(400, {"success": False, "error": "Caminho do arquivo é obrigatório."})
                    try:
                        from core.creator import create_file
                        created = create_file(watcher.target_dir, file_path, content=custom_content)
                        rel_created = os.path.relpath(created, watcher.target_dir)
                        watcher.build_initial()
                        watcher.notify_clients()
                        return self._send_json(200, {"success": True, "created": rel_created, "data": watcher.get_live_data()})
                    except Exception as e:
                        return self._send_json(400, {"success": False, "error": str(e)})

                elif self.path == "/api/rename":
                    old_path = payload.get("old_path", "").strip()
                    new_name = payload.get("new_name", "").strip()
                    if not old_path or not new_name:
                        return self._send_json(400, {"success": False, "error": "Caminhos original e novo são obrigatórios."})
                    try:
                        from core.creator import rename_resource
                        renamed = rename_resource(watcher.target_dir, old_path, new_name)
                        rel_renamed = os.path.relpath(renamed, watcher.target_dir)
                        watcher.build_initial()
                        watcher.notify_clients()
                        return self._send_json(200, {"success": True, "renamed": rel_renamed, "data": watcher.get_live_data()})
                    except Exception as e:
                        return self._send_json(400, {"success": False, "error": str(e)})

                elif self.path == "/api/delete":
                    target_path = payload.get("path", "").strip()
                    if not target_path:
                        return self._send_json(400, {"success": False, "error": "Caminho do recurso é obrigatório."})
                    try:
                        from core.creator import delete_resource
                        deleted = delete_resource(watcher.target_dir, target_path)
                        rel_deleted = os.path.relpath(deleted, watcher.target_dir)
                        watcher.build_initial()
                        watcher.notify_clients()
                        return self._send_json(200, {"success": True, "deleted": rel_deleted, "data": watcher.get_live_data()})
                    except Exception as e:
                        return self._send_json(400, {"success": False, "error": str(e)})

                elif self.path == "/api/save-file":
                    file_path = payload.get("path", "").strip()
                    content = payload.get("content", "")
                    if not file_path:
                        return self._send_json(400, {"success": False, "error": "Caminho do arquivo é obrigatório."})
                    try:
                        from core.creator import save_file_content
                        saved = save_file_content(watcher.target_dir, file_path, content)
                        rel_saved = os.path.relpath(saved, watcher.target_dir)
                        watcher.build_initial()
                        watcher.notify_clients()
                        return self._send_json(200, {"success": True, "saved": rel_saved, "data": watcher.get_live_data()})
                    except Exception as e:
                        return self._send_json(400, {"success": False, "error": str(e)})

                self._send_json(404, {"success": False, "error": "Rota não encontrada."})

        try:
            port = self.port
            for p in range(port, port + 30):
                try:
                    self.server = ThreadedHTTPServer(("127.0.0.1", p), WatcherHandler)
                    self.port = p
                    break
                except OSError:
                    continue
            self.server.serve_forever()
        except KeyboardInterrupt:
            print("\n🛑 Encerrando Watch Mode...")
        finally:
            self.stop()

    def stop(self):
        self.running = False
        if self.server:
            try:
                self.server.shutdown()
                self.server.server_close()
            except Exception:
                pass
