#!/usr/bin/env python3
"""gatekeeper.py — AGNES Gatekeeper: pre-commit quality gate.

On every commit, inspects staged files (git diff --cached --name-only) and runs
the SelfHealer diagnostic on each. Policy:

  - healthy                -> allow
  - fixable (self-healed)  -> warn, tell user to re-add + commit (non-blocking)
  - un-healable (stubborn) -> BLOCK the commit (exit non-zero)

Integrate via install_hooks.py -> .git/hooks/pre-commit.

This turns the immune system from "manual inspection" into enforced gatekeeping:
bad code never enters the repo silently.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT))
from core.self_evolve import SelfHealer, BASE  # noqa: E402

# 后缀 → verifier（复用 SelfHealer 的映射）
CHECK_EXTS = set(SelfHealer.VERIFIERS.keys()) | {".py"}


def staged_files():
    """Return list of staged file paths (git diff --cached --name-only)."""
    r = subprocess.run(["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace",
                       cwd=str(PROJECT), timeout=30)
    if r.returncode != 0:
        return []
    return [ln.strip() for ln in r.stdout.splitlines() if ln.strip()]


def diagnose_file(healer, rel):
    path = PROJECT / rel
    if not path.exists():
        return None
    return healer.diagnose(path)


def main():
    staged = staged_files()
    if not staged:
        return 0

    healer = SelfHealer()
    targets = [p for p in staged if Path(p).suffix.lower() in CHECK_EXTS]
    if not targets:
        return 0

    report = {"healthy": [], "fixed": [], "blocked": []}
    for rel in targets:
        path = PROJECT / rel
        diag = diagnose_file(healer, rel)
        if diag is None:
            continue
        rc, data = diag
        n_err = data.get("summary", {}).get("error", 0) if isinstance(data, dict) else 0
        n_warn = data.get("summary", {}).get("warning", 0) if isinstance(data, dict) else 0
        # 健康：无 error。仅警告(warnings/info, rc=2)不阻塞提交——0/1/2 语义里只有 error 才拦截。
        if n_err == 0 and rc in (0, 2):
            report["healthy"].append(rel + (f" ({n_warn} 警告)" if n_warn else ""))
            continue
        # has hard error -> try self-heal
        try:
            res = healer.heal(path, verbose=False)
        except Exception as e:
            res = {"success": False, "action": f"error:{e}"}
        if res.get("success") and res.get("action", "") in ("healed", "fixable"):
            report["fixed"].append(rel)
        elif res.get("action") == "healthy":
            report["healthy"].append(rel)
        else:
            report["blocked"].append(rel)

    # ── 输出化验单 ──
    if report["healthy"]:
        for f in report["healthy"]:
            print(f"[gatekeeper] ✅ 体检通过: {f}")
    if report["fixed"]:
        for f in report["fixed"]:
            print(f"[gatekeeper] 🛠️ 已自愈: {f} — 请重新 git add 后 commit")
    if report["blocked"]:
        for f in report["blocked"]:
            print(f"[gatekeeper] ⛔ 拦截: {f} — 顽固病灶，需人工修复后重新 add+commit")

    # ── 判决 ──
    if report["blocked"]:
        print("\n[gatekeeper] ❌ 提交被拦截（存在自愈失败的文件）")
        return 1
    if report["fixed"]:
        print("\n[gatekeeper] ⚠️ 有文件被自动自愈，请重新 git add + commit 后再提交")
        # 不硬拦截自愈成功的（提示用户重 add），但为了确保新内容入库，仍返回 0 让流程继续？
        # 策略：自愈已改 worktree，但未 re-add，直接放行会导致旧内容入库。
        # 安全选择：仍放行但强提示（用户需手动 re-add 才真正提交新内容）。
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
