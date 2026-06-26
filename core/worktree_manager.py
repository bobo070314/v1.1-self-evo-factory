#!/usr/bin/env python3
"""core/worktree_manager.py - Git worktree isolation for safe code execution

Ensures all agent code changes happen in isolated environments.
Supports auto-lifecycle management and cleanup.
"""

import subprocess
import shutil
from pathlib import Path
from typing import Optional, Dict
from datetime import datetime, timezone

class WorktreeManager:
    """Manages git worktrees for isolated code execution."""
    
    def __init__(self, base_path: Path = None):
        self.base_path = base_path or Path.cwd()
        self._active: Dict[str, Path] = {}
    
    def create_isolated_tree(self, task_id: str) -> Path:
        """Create a git worktree for isolated execution. Returns the worktree path."""
        tree_name = f"worktree_{task_id[:8]}"
        tree_path = self.base_path / tree_name
        
        try:
            subprocess.run(
                ["git", "worktree", "add", str(tree_path), "--detach"],
                check=True,
                capture_output=True,
            )
            self._active[task_id] = tree_path
            return tree_path
        except subprocess.CalledProcessError:
            # Already exists or git error - create empty dir
            tree_path.mkdir(parents=True, exist_ok=True)
            return tree_path
    
    def cleanup_tree(self, task_id: str) -> bool:
        """Remove the isolated worktree."""
        tree_path = self._active.get(task_id)
        if not tree_path:
            return False
        
        try:
            # Remove worktree reference
            subprocess.run(
                ["git", "worktree", "remove", str(tree_path), "--force"],
                capture_output=True,
            )
            # Remove directory if still exists
            if tree_path.exists():
                shutil.rmtree(tree_path)
            del self._active[task_id]
            return True
        except Exception:
            return False
    
    def write_file(self, task_id: str, relative_path: str, content: str) -> Path:
        """Write a file inside the isolated worktree."""
        tree_path = self._active.get(task_id) or self.create_isolated_tree(task_id)
        file_path = tree_path / relative_path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding="utf-8")
        return file_path
    
    def read_file(self, task_id: str, relative_path: str) -> Optional[str]:
        """Read a file from the isolated worktree."""
        tree_path = self._active.get(task_id)
        if not tree_path:
            return None
        file_path = tree_path / relative_path
        return file_path.read_text(encoding="utf-8") if file_path.exists() else None


def get_worktree_manager() -> WorktreeManager:
    """Singleton accessor."""
    return WorktreeManager()


if __name__ == "__main__":
    wm = WorktreeManager()
    print(f"Worktree manager initialized at: {wm.base_path}")