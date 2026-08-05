#!/usr/bin/env python3
"""install_hooks.py — Inject the AGNES Gatekeeper into .git/hooks/pre-commit.

Idempotent: safe to run repeatedly; backs up an existing pre-commit hook.

Usage:
  python scripts/install_hooks.py         # install (idempotent)
  python scripts/install_hooks.py --uninstall
"""

import argparse
import os
import shutil
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
HOOK_FILE = PROJECT / ".git" / "hooks" / "pre-commit"
GATEKEEPER = PROJECT / "scripts" / "gatekeeper.py"


HOOK_TEMPLATE = r"""#!/bin/sh
# AGNES Gatekeeper pre-commit hook (installed by scripts/install_hooks.py)
# Quality gate: diagnose + self-heal staged files before commit.
export PYTHONIOENCODING=utf-8
exec python "{gatekeeper}" "$@"
"""


def install():
    if not (PROJECT / ".git").is_dir():
        print(f"错误: 不是 git 仓库根目录: {PROJECT}")
        return 1
    if not GATEKEEPER.exists():
        print(f"错误: 找不到 gatekeeper: {GATEKEEPER}")
        return 1

    # 备份现有 hook
    if HOOK_FILE.exists() and "AGNES Gatekeeper" not in HOOK_FILE.read_text(encoding="utf-8", errors="replace"):
        bak = HOOK_FILE.with_suffix(".bak")
        shutil.copy2(HOOK_FILE, bak)
        print(f"已备份原 hook -> {bak.name}")

    HOOK_FILE.write_text(HOOK_TEMPLATE.format(gatekeeper=str(GATEKEEPER).replace("\\", "/")),
                         encoding="utf-8")
    # chmod +x (Windows git bash 需要)
    try:
        os.chmod(HOOK_FILE, 0o755)
    except OSError:
        pass
    print(f"✅ AGNES Gatekeeper 已安装: {HOOK_FILE}")
    print("   每次 git commit 将自动执行质量门禁。")
    return 0


def uninstall():
    if HOOK_FILE.exists() and "AGNES Gatekeeper" in HOOK_FILE.read_text(encoding="utf-8", errors="replace"):
        HOOK_FILE.unlink()
        print(f"已移除 Gatekeeper hook: {HOOK_FILE}")
    bak = HOOK_FILE.with_suffix(".bak")
    if bak.exists():
        shutil.move(bak, HOOK_FILE)
        print(f"已恢复原 hook: {bak.name}")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Install/uninstall AGNES Gatekeeper pre-commit hook")
    ap.add_argument("--uninstall", action="store_true", help="移除 hook")
    args = ap.parse_args()
    sys.exit(uninstall() if args.uninstall else install())
