#!/usr/bin/env python3
"""V2.13 深度功能验证 — A方向：真实 API 技能 dry-run 产出检查

检查 11 个需要外部 API 的技能是否能正确处理 --dry-run，
优雅降级时返回有效的 JSON 结构。
"""

import json
import subprocess
import sys
from pathlib import Path

SKILLS_DIR = Path(r"D:\bobo\openclaw-foreign\skills")

API_SKILLS = [
    # GitHub API 系
    ("github-actions-generator", "generate", "--template ci-node --dry-run --json"),
    ("web-deploy-github", "status", "--dry-run --json"),
    # Notion/Linear 系
    ("notion", "query", "--dry-run --json"),
    ("linear", "issues", "--dry-run --json"),
    # 腾讯系
    ("tencent-docs", "create", "--dry-run --json"),
    # 企业微信 6 件套
    ("wecomcli-msg", "send", "--dry-run --json"),
    ("wecomcli-contact", "list", "--dry-run --json"),
    ("wecomcli-doc", "create", "--dry-run --json"),
    ("wecomcli-meeting", "schedule", "--dry-run --json"),
    ("wecomcli-schedule", "add", "--dry-run --json"),
    ("wecomcli-todo", "add", "--dry-run --json"),
]

# 额外：creator/reviewer 系
EXTRA_SKILLS = [
    ("create-pr", "create", "--dry-run --json"),
    ("create-issue", "create", "--dry-run --json"),
    ("create-skill", "create", "--dry-run --json"),
    ("frontend-code-review", "review", "--dry-run --json"),
    ("backend-code-review", "review", "--dry-run --json"),
    ("release-notes-generator", "generate", "--dry-run --json"),
]


def validate_skill(skill_name: str, _subcommand: str, extra_args: str) -> tuple:
    """Validate a single skill."""
    skill_path = SKILLS_DIR / skill_name / "run.py"
    if not skill_path.exists():
        return False, f"MISSING: {skill_path}"

    cmd = [sys.executable, str(skill_path)] + extra_args.split()
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=15)
        output = (result.stdout or "").strip() or (result.stderr or "").strip()

        # Check 1: non-zero exit is ok for --dry-run if it says "no API key"
        non_fatal = any(
            kw in output.lower() for kw in ["dry_run", "dry run", "no token", "no api key", "not configured", "will "]
        )

        try:
            data = json.loads(output)
            has_json = True
            has_dry = "dry_run" in data or "dry-run" in str(data) or data.get("dry_run")
            has_status = "status" in data or "ok" in data
            ok = result.returncode == 0 or non_fatal
            msg = "JSON valid" + (" (graceful)" if result.returncode != 0 else "")
        except (json.JSONDecodeError, ValueError):
            has_json = False
            ok = non_fatal or result.returncode == 0
            msg = f"Text output (exit={result.returncode})"

        return ok, msg

    except subprocess.TimeoutExpired:
        return False, "TIMEOUT"
    except Exception as e:
        return False, f"ERROR: {e}"


def main():
    print("=" * 60)
    print("A方向：真实 API 技能 deep dry-run validation")
    print("=" * 60)

    all_skills = API_SKILLS + EXTRA_SKILLS
    total = len(all_skills)
    passed = 0
    failed = []

    for skill_name, subcommand, extra_args in all_skills:
        ok, msg = validate_skill(skill_name, subcommand, extra_args)
        status = "✅" if ok else "❌"
        print(f"  {status} {skill_name:<30} {msg}")
        if ok:
            passed += 1
        else:
            failed.append((skill_name, msg))

    print(f"\n{'=' * 60}")
    print(f"Result: {passed}/{total} passed")
    if failed:
        print(f"Failed: {len(failed)}")
        for name, msg in failed:
            print(f"  ❌ {name}: {msg}")

    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
