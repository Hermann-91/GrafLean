"""
Módulo do Gerenciador de Mudanças (Change Manager).
Responsável pelo rastreamento desacoplado de Estado da IA vs Estado do Git,
geração de eventos semânticos em tempo real e emissão de patches incrementais.
"""

import time
import json
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Set, Optional, Callable, Any


class AIState(str, Enum):
    """Estados operacionais da Inteligência Artificial sobre arquivos e símbolos."""
    IDLE = "idle"
    CREATING = "creating"
    EDITING = "editing"
    ANALYZING = "analyzing"
    FINISHED = "finished"
    ERROR = "error"


class GitState(str, Enum):
    """Estados rastreados pelo Git no repositório."""
    UNTRACKED = "untracked"
    MODIFIED = "modified"
    DELETED = "deleted"
    STAGED = "staged"
    COMMITTED = "committed"


@dataclass(frozen=True)
class ChangeEvent:
    """Evento semântico de alteração para transmissão via SSE."""
    event: str
    data: Dict[str, Any]
    timestamp: float = field(default_factory=time.time)

    def to_sse(self) -> str:
        """Formata o evento no padrão RFC de Server-Sent Events (SSE)."""
        payload = json.dumps(self.data, ensure_ascii=False)
        return f"event: {self.event}\ndata: {payload}\n\n"


class ChangeManager:
    """
    Gerenciador de Mudanças em Tempo Real.
    Separa estritamente o estado transitório da IA do histórico persistente do Git,
    calcula deltas estruturais e transmite patches incrementais.
    """

    def __init__(self, root_dir: str):
        self.root_dir = root_dir
        self.ai_states: Dict[str, AIState] = {}
        self.git_states: Dict[str, GitState] = {}
        self._listeners: Set[Callable[[ChangeEvent], None]] = set()

    def subscribe(self, callback: Callable[[ChangeEvent], None]) -> None:
        """Inscreve um ouvinte para receber eventos de alteração."""
        self._listeners.add(callback)

    def unsubscribe(self, callback: Callable[[ChangeEvent], None]) -> None:
        """Remove a inscrição de um ouvinte."""
        self._listeners.discard(callback)

    def emit(self, event_type: str, data: Dict[str, Any]) -> ChangeEvent:
        """Cria e despacha um evento para todos os ouvintes inscritos."""
        evt = ChangeEvent(event=event_type, data=data)
        for listener in list(self._listeners):
            try:
                listener(evt)
            except Exception:
                pass
        return evt

    def set_ai_state(self, path: str, state: AIState | str) -> ChangeEvent:
        """Define o estado da IA para um determinado arquivo ou símbolo."""
        state_enum = AIState(state) if isinstance(state, str) else state
        self.ai_states[path] = state_enum
        return self.emit("ai_state", {
            "path": path,
            "state": state_enum.value
        })

    def clear_ai_state(self, path: str) -> Optional[ChangeEvent]:
        """Limpa o estado da IA quando uma operação for concluída."""
        if path in self.ai_states:
            del self.ai_states[path]
            return self.emit("ai_state", {
                "path": path,
                "state": AIState.IDLE.value
            })
        return None

    def update_git_status(self, status_map: Dict[str, str]) -> List[ChangeEvent]:
        """
        Atualiza o mapa de status do Git e emite eventos semânticos
        apenas para arquivos cujo status sofreu mutação.
        """
        events = []
        new_states: Dict[str, GitState] = {}
        for path, status_str in status_map.items():
            try:
                # Mapeia novos para untracked se necessário
                if status_str in ("new", "?", "A"):
                    st = GitState.UNTRACKED
                elif status_str in ("modified", "M"):
                    st = GitState.MODIFIED
                elif status_str in ("deleted", "D"):
                    st = GitState.DELETED
                elif status_str in ("staged", "S"):
                    st = GitState.STAGED
                else:
                    st = GitState.MODIFIED
                new_states[path] = st
            except Exception:
                continue

        # Verifica alterações de status
        all_paths = set(self.git_states.keys()) | set(new_states.keys())
        for path in all_paths:
            old_st = self.git_states.get(path)
            cur_st = new_states.get(path)

            if old_st != cur_st:
                if cur_st is None:
                    # Arquivo foi commitado e não está mais dirty
                    evt = self.emit("git_status", {"path": path, "status": GitState.COMMITTED.value})
                else:
                    evt = self.emit("git_status", {"path": path, "status": cur_st.value})
                events.append(evt)

        self.git_states = new_states
        return events

    def compute_filesystem_delta(
        self,
        old_snapshots: Dict[str, float],
        new_snapshots: Dict[str, float]
    ) -> List[ChangeEvent]:
        """
        Calcula a diferença entre snapshots de arquivos e emite eventos
        semânticos granulares: node_created, node_changed, node_deleted.
        """
        events = []
        old_keys = set(old_snapshots.keys())
        new_keys = set(new_snapshots.keys())

        # Arquivos novos
        for added_path in new_keys - old_keys:
            events.append(self.emit("node_created", {
                "path": added_path,
                "status": "new"
            }))

        # Arquivos excluídos
        for deleted_path in old_keys - new_keys:
            events.append(self.emit("node_deleted", {
                "path": deleted_path,
                "status": "deleted"
            }))

        # Arquivos modificados (mtime alterado)
        for common_path in old_keys & new_keys:
            if old_snapshots[common_path] != new_snapshots[common_path]:
                events.append(self.emit("node_changed", {
                    "path": common_path,
                    "status": "modified"
                }))

        return events

    def get_summary(self) -> Dict[str, Any]:
        """Retorna resumo das mudanças ativas para exibição na aba Change Graph / Mini-map."""
        total_ai_active = sum(1 for s in self.ai_states.values() if s not in (AIState.IDLE, AIState.FINISHED))
        untracked = [p for p, s in self.git_states.items() if s == GitState.UNTRACKED]
        modified = [p for p, s in self.git_states.items() if s == GitState.MODIFIED]
        deleted = [p for p, s in self.git_states.items() if s == GitState.DELETED]

        return {
            "ai_active_count": total_ai_active,
            "ai_tasks": {p: s.value for p, s in self.ai_states.items()},
            "git_summary": {
                "new": len(untracked),
                "modified": len(modified),
                "deleted": len(deleted),
                "total": len(untracked) + len(modified) + len(deleted)
            },
            "new_files": untracked,
            "modified_files": modified,
            "deleted_files": deleted
        }
