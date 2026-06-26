#!/usr/bin/env python3
"""Phoenix Demo: Full autonomous pipeline demonstration."""
import sys
sys.path.insert(0, r"D:\bobo\projects\v1.1-self-evo-factory")

from pathlib import Path
from core.worktree_manager import WorktreeManager
from core.yolo_classifier import classify

def main():
    wm = WorktreeManager(base_path=Path(r"D:\bobo\projects\v1.1-self-evo-factory"))
    
    # Step 1: Create isolated worktree
    tree_path = wm.create_isolated_tree("phoenix_demo_001")
    print(f"[Phoenix] Isolated worktree created: {tree_path}")
    
    # Step 2: Write demo file
    demo_file = tree_path / "safe_code.py"
    demo_file.write_text("print('Hello from Phoenix isolation!')\nx = 1 + 2\nprint(x)\n", encoding="utf-8")
    print(f"[Phoenix] Demo file written: {demo_file}")
    
    # Step 3: YOLO Scan
    code = demo_file.read_text(encoding="utf-8")
    result = classify(code)
    print(f"[Phoenix] YOLO Scan: Passed={result['passed']}")
    
    # Step 4: Cleanup
    wm.cleanup_tree("phoenix_demo_001")
    print("[Phoenix] Isolation demo complete. Worktree cleaned up.")

if __name__ == "__main__":
    main()