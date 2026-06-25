#!/usr/bin/env python3
"""
git_safe_push.py — 过滤 PowerShell stderr 误判的 git push 包装器。
PowerShell 把 git 所有 stderr 输出当错误，导致 exit code 1。
此包装器只对真正的 fatal/error 返回非零。
"""
import subprocess
import sys
import os

os.environ.setdefault("PYTHONIOENCODING", "utf-8")

# Figure out repo root from script location
import pathlib
REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent

FATAL_KEYWORDS = [b"fatal:", b"error:", b"Permission denied", b"cannot lock", b"refusing to merge"]


def is_real_error(stderr: bytes) -> bool:
    for kw in FATAL_KEYWORDS:
        if kw in stderr:
            return True
    return False


def main():
    result = subprocess.run(
        ["git", "push", "origin", "master"],
        capture_output=True,
        cwd=str(REPO_ROOT),
    )
    stdout = result.stdout.decode("utf-8", errors="replace").strip()
    stderr = result.stderr.decode("utf-8", errors="replace").strip()

    if stdout:
        print(stdout)
    if stderr:
        print(stderr, file=sys.stderr)

    if result.returncode != 0 and is_real_error(result.stderr):
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
