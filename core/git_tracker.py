"""
Módulo de Rastreamento de Status do Git (GitTracker).
Executa inspeções determinísticas de alta performance (< 5ms) via 'git status --porcelain'
para identificar arquivos novos (untracked/added), modificados e deletados.
"""

import os
import subprocess
from typing import Dict, Optional


class GitStatusType:
    NEW = "new"              # Arquivo novo criado (untracked ?? ou added A)
    MODIFIED = "modified"    # Arquivo modificado (M)
    DELETED = "deleted"      # Arquivo removido (D)


class GitTracker:
    """
    Rastreador leve de status do Git para projetos monitorados pelo GrafLean.
    """

    def __init__(self, root_dir: str):
        self.root_dir = os.path.abspath(root_dir)

    def is_git_repository(self) -> bool:
        """Verifica se o diretório raiz pertence a um repositório Git."""
        try:
            res = subprocess.run(
                ["git", "-C", self.root_dir, "rev-parse", "--is-inside-work-tree"],
                capture_output=True,
                text=True,
                timeout=1
            )
            return res.returncode == 0 and res.stdout.strip() == "true"
        except (subprocess.SubprocessError, FileNotFoundError, OSError):
            return False

    def get_status_map(self) -> Dict[str, str]:
        """
        Retorna um dicionário mapeando o caminho absoluto do arquivo para seu status Git:
        { '/path/to/file.php': 'new' | 'modified' | 'deleted' }
        Tempo de resposta médio: < 5ms.
        """
        if not self.is_git_repository():
            return {}

        status_map: Dict[str, str] = {}
        try:
            res = subprocess.run(
                ["git", "-C", self.root_dir, "status", "--porcelain", "-uall"],
                capture_output=True,
                text=True,
                timeout=2
            )
            if res.returncode != 0:
                return {}

            for line in res.stdout.splitlines():
                if len(line) < 4:
                    continue
                code = line[:2]
                rel_path = line[3:].strip()
                # Remove aspas se o Git colocar aspas em nomes com espaços/acentos
                if rel_path.startswith('"') and rel_path.endswith('"'):
                    rel_path = rel_path[1:-1]

                abs_path = os.path.abspath(os.path.join(self.root_dir, rel_path))

                if "??" in code or "A" in code:
                    st = GitStatusType.NEW
                elif "M" in code:
                    st = GitStatusType.MODIFIED
                elif "D" in code:
                    st = GitStatusType.DELETED
                else:
                    st = GitStatusType.MODIFIED

                status_map[abs_path] = st
                status_map[rel_path] = st

        except (subprocess.SubprocessError, OSError):
            pass

        return status_map
