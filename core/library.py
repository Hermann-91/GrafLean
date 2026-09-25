"""
Módulo de Gerenciamento da Biblioteca de Projetos e Acelerador de IA — GrafLean Hub.
Responsável pela persistência centralizada (~/.graflean/config.json), cache de múltiplos
projetos e isolamento do modo AI Context Accelerator (.graflean/ com auto-gitignore).
"""

from __future__ import annotations
import os
import json
import shutil
import hashlib
import re
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any

from core.models import ProjectMetadata


class LibraryManager:
    """
    Gerenciador da biblioteca central do GrafLean e do ecossistema de múltiplos projetos.
    Opera 100% com a biblioteca padrão do Python, sem dependências externas.
    """

    DEFAULT_BASE_DIR = os.path.expanduser("~/.graflean")

    def __init__(self, base_dir: Optional[str] = None):
        self.base_dir = os.path.abspath(os.path.expanduser(base_dir or self.DEFAULT_BASE_DIR))
        self.config_path = os.path.join(self.base_dir, "config.json")
        self.library_dir = os.path.join(self.base_dir, "library")
        self.projects: Dict[str, ProjectMetadata] = {}
        self._ensure_storage()
        self._load_config()

    def _ensure_storage(self) -> None:
        """Garante que a estrutura de diretórios ~/.graflean/ e library/ existam no disco."""
        os.makedirs(self.base_dir, exist_ok=True)
        os.makedirs(self.library_dir, exist_ok=True)

    def _load_config(self) -> None:
        """Carrega as configurações e projetos registrados a partir de config.json."""
        if not os.path.exists(self.config_path):
            self._save_config()
            return

        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            projects_data = data.get("projects", {})
            self.projects = {
                pid: ProjectMetadata.from_dict(pdata)
                for pid, pdata in projects_data.items()
            }
        except (json.JSONDecodeError, OSError):
            self.projects = {}

    def _save_config(self) -> None:
        """Persiste atomicamente o estado da biblioteca em config.json."""
        data = {
            "version": "1.0",
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "projects": {pid: proj.to_dict() for pid, proj in self.projects.items()}
        }
        tmp_file = f"{self.config_path}.tmp"
        with open(tmp_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        os.replace(tmp_file, self.config_path)

    @staticmethod
    def generate_project_id(path: str) -> str:
        """Gera um identificador determinístico e seguro baseado no nome da pasta e hash do caminho."""
        norm_path = os.path.abspath(os.path.expanduser(path)).rstrip("/\\")
        folder_name = os.path.basename(norm_path)
        clean_name = re.sub(r"[^a-zA-Z0-9_-]", "_", folder_name).lower() or "project"
        path_hash = hashlib.sha256(norm_path.encode("utf-8")).hexdigest()[:8]
        return f"{clean_name}_{path_hash}"

    def register_project(
        self,
        path: str,
        name: Optional[str] = None,
        ai_accelerator: bool = True
    ) -> ProjectMetadata:
        """Registra um projeto na biblioteca central e configura o Acelerador de IA se solicitado."""
        norm_path = os.path.abspath(os.path.expanduser(path))
        if not os.path.isdir(norm_path):
            raise FileNotFoundError(f"Diretório do projeto não encontrado: {norm_path}")

        project_id = self.generate_project_id(norm_path)
        project_name = name or os.path.basename(norm_path)

        project_cache = self.get_project_cache_dir(project_id)
        os.makedirs(project_cache, exist_ok=True)

        if ai_accelerator:
            self.sync_project_gitignore(norm_path)
            local_graflean = os.path.join(norm_path, ".graflean")
            os.makedirs(local_graflean, exist_ok=True)

        metadata = ProjectMetadata(
            id=project_id,
            name=project_name,
            path=norm_path,
            ai_accelerator=ai_accelerator,
            last_scanned=None
        )

        self.projects[project_id] = metadata
        self._save_config()
        return metadata

    def remove_project(self, project_id: str, purge_local_folder: bool = True) -> bool:
        """Remove um projeto da biblioteca, limpando seu cache e pasta .graflean/ local se solicitado."""
        if project_id not in self.projects:
            return False

        project = self.projects[project_id]
        project_cache = self.get_project_cache_dir(project_id)
        if os.path.exists(project_cache):
            shutil.rmtree(project_cache, ignore_errors=True)

        if purge_local_folder and project.ai_accelerator and os.path.isdir(project.path):
            local_graflean = os.path.join(project.path, ".graflean")
            if os.path.exists(local_graflean):
                shutil.rmtree(local_graflean, ignore_errors=True)

        del self.projects[project_id]
        self._save_config()
        return True

    def toggle_ai_accelerator(self, project_id: str, enable: bool) -> bool:
        """Alterna o modo Acelerador de IA de um projeto cadastrado."""
        if project_id not in self.projects:
            return False

        project = self.projects[project_id]
        project.ai_accelerator = enable

        if enable and os.path.isdir(project.path):
            self.sync_project_gitignore(project.path)
            local_graflean = os.path.join(project.path, ".graflean")
            os.makedirs(local_graflean, exist_ok=True)

        self._save_config()
        return True

    def sync_project_gitignore(self, project_path: str) -> None:
        """Garante que .graflean/ esteja listado no .gitignore do projeto para evitar commits acidentais."""
        norm_path = os.path.abspath(os.path.expanduser(project_path))
        gitignore_path = os.path.join(norm_path, ".gitignore")

        entry = ".graflean/"
        if os.path.exists(gitignore_path):
            try:
                with open(gitignore_path, "r", encoding="utf-8") as f:
                    content = f.read()
                lines = [line.strip() for line in content.splitlines()]
                if entry in lines or ".graflean" in lines:
                    return

                separator = "\n" if not content.endswith("\n") and content else ""
                new_content = f"{content}{separator}\n# GrafLean AI Context Accelerator\n{entry}\n"
                with open(gitignore_path, "w", encoding="utf-8") as f:
                    f.write(new_content)
            except OSError:
                pass
        else:
            try:
                with open(gitignore_path, "w", encoding="utf-8") as f:
                    f.write(f"# GrafLean AI Context Accelerator\n{entry}\n")
            except OSError:
                pass

    def list_projects(self) -> List[ProjectMetadata]:
        """Retorna a lista de todos os projetos cadastrados na biblioteca."""
        return list(self.projects.values())

    def get_project(self, project_id: str) -> Optional[ProjectMetadata]:
        """Busca os metadados de um projeto pelo seu ID."""
        return self.projects.get(project_id)

    def get_project_cache_dir(self, project_id: str) -> str:
        """Retorna o caminho absoluto do diretório de cache do projeto na biblioteca."""
        return os.path.join(self.library_dir, project_id)

    def update_project_metrics(
        self,
        project_id: str,
        node_count: int,
        edge_count: int,
        avg_instability: float,
        has_cycles: bool
    ) -> Optional[ProjectMetadata]:
        """Atualiza as métricas de arquitetura e o timestamp da última varredura do projeto."""
        if project_id not in self.projects:
            return None

        project = self.projects[project_id]
        project.node_count = node_count
        project.edge_count = edge_count
        project.avg_instability = round(avg_instability, 2)
        project.has_cycles = has_cycles
        project.last_scanned = datetime.now(timezone.utc).isoformat()

        self._save_config()
        return project

    def save_project_graph(self, project_id: str, graph: Any) -> str:
        """Salva o grafo na biblioteca central e sincroniza .graflean/ (graph.json e architecture.md) se modo IA ativo."""
        project = self.projects.get(project_id)
        if not project:
            raise KeyError(f"Projeto com ID '{project_id}' não encontrado na biblioteca.")

        # 1. Salva na biblioteca central (~/.graflean/library/{id}/graph.json)
        cache_dir = self.get_project_cache_dir(project_id)
        central_graph_path = os.path.join(cache_dir, "graph.json")
        graph.save_to_file(central_graph_path)

        # 2. Se modo Acelerador de IA ativo, replica localmente no repositório
        if project.ai_accelerator and os.path.isdir(project.path):
            local_graflean = os.path.join(project.path, ".graflean")
            os.makedirs(local_graflean, exist_ok=True)
            local_graph_path = os.path.join(local_graflean, "graph.json")
            graph.save_to_file(local_graph_path)
            self._generate_architecture_summary(project, graph, os.path.join(local_graflean, "architecture.md"))

        # 3. Atualiza métricas e timestamp no config.json
        total_nodes = len(graph.nodes)
        total_edges = len(graph.edges)
        has_cycles = any(getattr(n.metrics, "has_cycles", False) for n in graph.nodes.values())
        instabilities = [
            n.metrics.instability for n in graph.nodes.values()
            if getattr(n, "symbol_type", None) and n.symbol_type.value in ("class", "file")
        ]
        avg_instability = sum(instabilities) / len(instabilities) if instabilities else 0.0

        self.update_project_metrics(
            project_id=project_id,
            node_count=total_nodes,
            edge_count=total_edges,
            avg_instability=avg_instability,
            has_cycles=has_cycles
        )

        return central_graph_path

    def _generate_architecture_summary(self, project: ProjectMetadata, graph: Any, output_path: str) -> None:
        """Gera resumo executivo conciso em Markdown (< 3k tokens) para agentes de IA."""
        classes = [n for n in graph.nodes.values() if getattr(n, "symbol_type", None) and n.symbol_type.value == "class"]
        cycles = [n.name for n in graph.nodes.values() if getattr(n.metrics, "has_cycles", False)]

        lines = [
            f"# 🏛️ Resumo Arquitetural — {project.name}",
            f"> Gerado automaticamente pelo GrafLean em {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}.",
            "",
            f"* **Nós Totais:** {len(graph.nodes)} | **Conexões:** {len(graph.edges)}",
            f"* **Classes Identificadas:** {len(classes)}",
            f"* **Ciclos de Dependência:** {'⚠️ ' + ', '.join(cycles[:10]) if cycles else '✅ Nenhum ciclo detectado'}",
            "",
            "## 📦 Componentes Principais (Top Classes):",
        ]
        for c in sorted(classes, key=lambda x: x.metrics.afferent_coupling, reverse=True)[:15]:
            lines.append(f"- **{c.name}** (`{os.path.basename(c.file_path)}`): Ca={c.metrics.afferent_coupling}, Ce={c.metrics.efferent_coupling}, I={c.metrics.instability}")

        with open(output_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")

