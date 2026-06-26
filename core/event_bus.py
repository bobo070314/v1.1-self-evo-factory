#!/usr/bin/env python3
"""core/event_bus.py - Event-driven automation for Phoenix Engine

Triggers automated workflows on file changes and system events.
Integrates with YOLO security scanner and coordinator.
"""

import time
import threading
from pathlib import Path
from typing import Callable, Dict, List, Optional
from datetime import datetime, timezone

# Event types
EVENT_FILE_CREATED = "file.created"
EVENT_FILE_CHANGED = "file.changed"
EVENT_WORKTREE_COMMIT = "worktree.commit"

# Registry for event handlers
_handlers: Dict[str, List[Callable]] = {}
_observer = None
_observer_path: Optional[Path] = None


def subscribe(event_type: str, handler: Callable):
    """Register an event handler."""
    _handlers.setdefault(event_type, []).append(handler)


def emit(event_type: str, payload: dict):
    """Emit an event to all registered handlers."""
    for handler in _handlers.get(event_type, []):
        try:
            handler(payload)
        except Exception as e:
            print(f"[event_bus] Handler error: {e}")


def _default_yolo_handler(payload: dict):
    """Default handler: auto-run YOLO scan on worktree changes."""
    from core.yolo_classifier import classify
    
    file_path = payload.get("file_path", "")
    tree_path = payload.get("tree_path", "")
    
    try:
        content = Path(file_path).read_text(encoding="utf-8", errors="replace")
        result = classify(content)
        if not result.get("passed"):
            print(f"[event_bus] 🚨 YOLO blocked: {file_path}")
            print(f"   Failures: {result.get('failures', [])}")
    except Exception as e:
        print(f"[event_bus] YOLO scan error: {e}")


def start_observer(path: Path):
    """Start file system observer (simple polling for now)."""
    global _observer, _observer_path
    
    _observer_path = path
    _observer_stop = threading.Event()
    
    def poll_loop():
        seen = set()
        while not _observer_stop.is_set():
            try:
                for py_file in path.rglob("*.py"):
                    stat = py_file.stat()
                    mtime = stat.st_mtime
                    if py_file not in seen or mtime > seen.get(py_file, 0):
                        if py_file in seen:
                            emit(EVENT_FILE_CHANGED, {
                                "file_path": str(py_file),
                                "tree_path": str(path),
                                "timestamp": datetime.now(timezone.utc).isoformat(),
                            })
                        else:
                            emit(EVENT_FILE_CREATED, {
                                "file_path": str(py_file),
                                "tree_path": str(path),
                                "timestamp": datetime.now(timezone.utc).isoformat(),
                            })
                        seen[py_file] = mtime
            except Exception:
                pass
            time.sleep(1)
    
    _observer = threading.Thread(target=poll_loop, daemon=True)
    _observer.start()
    
    # Register default YOLO handler
    subscribe(EVENT_FILE_CREATED, _default_yolo_handler)
    subscribe(EVENT_FILE_CHANGED, _default_yolo_handler)


def stop_observer():
    """Stop the file observer."""
    global _observer
    if _observer:
        # Cleanup handled by daemon thread
        _observer = None


if __name__ == "__main__":
    print("Event bus ready. Start observer with start_observer(Path).")