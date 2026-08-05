#!/usr/bin/env python3
"""dry-run factory immune-system scan: only diagnose, no LLM, no writes.

Scans all skills/*/_meta.json (and run.py) and reports how many have issues
that SelfHealer could fix. This measures "coverage" without spending LLM calls.

Usage: python scripts/scan_health.py
"""
import json, os, subprocess, sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
SKILLS = PROJECT / "skills"
YAML_LINTER = SKILLS / "yaml-linter" / "run.py"

def probe(path):
    r = subprocess.run([sys.executable, str(YAML_LINTER), str(path), "--json"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30)
    try:
        data = json.loads(r.stdout)
    except json.JSONDecodeError:
        return r.returncode, {}
    return r.returncode, data

errs, warnings, ok, missing = [], [], [], []
for d in sorted(SKILLS.iterdir()):
    if not d.is_dir():
        continue
    for fname in ("_meta.json",):
        p = d / fname
        if not p.exists():
            continue
        rc, data = probe(p)
        n_err = data.get("summary", {}).get("error", 0)
        n_warn = data.get("summary", {}).get("warning", 0)
        if n_err > 0:
            errs.append((str(p.relative_to(PROJECT)), n_err, rc))
        elif n_warn > 0:
            warnings.append((str(p.relative_to(PROJECT)), n_warn))
        else:
            ok.append(str(p.relative_to(PROJECT)))

print(f"扫描技能目录: {len([d for d in SKILLS.iterdir() if d.is_dir()])} 个")
print(f"\n_meta.json 总数(含demo): {len(ok)+len(errs)+len(warnings)}")
print(f"\n✅ 健康 (0 错误 0 警告): {len(ok)}")
print(f"⚠️  有警告: {len(warnings)}")
for p, n in warnings[:10]:
    print(f"    {p} ({n} 警告)")
print(f"❌ 有错误: {len(errs)}")
for p, n, rc in errs[:15]:
    print(f"    {p} ({n} 错误, rc={rc})")
