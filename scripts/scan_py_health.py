#!/usr/bin/env python3
"""scan run.py syntax health (py_compile) across all skills — zero cost."""
import os, subprocess, sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
SKILLS = PROJECT / "skills"

ok, broken = [], []
for d in sorted(SKILLS.iterdir()):
    if not d.is_dir():
        continue
    for fname in ("run.py",):
        p = d / fname
        if not p.exists():
            continue
        r = subprocess.run([sys.executable, "-m", "py_compile", str(p)],
                           capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30)
        if r.returncode == 0:
            ok.append(p.relative_to(PROJECT))
        else:
            broken.append((p.relative_to(PROJECT), r.stderr[:200]))

print(f"run.py 总数: {len(ok)+len(broken)}")
print(f"✅ 语法健康: {len(ok)}")
print(f"❌ 语法错误: {len(broken)}")
for p, e in broken:
    print(f"    {p}:\n      {e.strip().splitlines()[-1] if e.strip() else ''}")
