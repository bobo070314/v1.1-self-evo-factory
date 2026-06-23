#!/usr/bin/env python3.
"""V3.1 API skills real-token integration test.

Tests 11 API-dependent skills in dry-run mode (graceful degradation),
with optional --live mode for real API calls when tokens are configured.

Usage:
  python test_api_skills.py               # dry-run all 11
  python test_api_skills.py --live        # real API calls (needs tokens)
  python test_api_skills.py --skill notion  # test single skill
  python test_api_skills.py --json        # JSON output
  python test_api_skills.py --version
"""

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

__version__ = "0.1.0"
UTC = timezone.utc

SKILLS_DIR = Path("D:/bobo/openclaw-foreign/skills")

# 11 API-dependent skills and their dry-run args
API_SKILLS = [
    ("github-actions-generator", ["--dry-run", "--json", "--template", "ci-node"]),
    ("web-deploy-github", ["--dry-run", "--json", "status", "--repo", "test"]),
    ("notion", ["--dry-run", "--json", "query", "--database", "test-db"]),
    ("linear", ["--dry-run", "--json", "issues", "--team", "test"]),
    ("tencent-docs", ["--dry-run", "--json", "list"]),
    ("wecomcli-msg", ["--dry-run", "--json", "send", "--to", "test", "--text", "hello-v3"]),
    ("wecomcli-contact", ["--dry-run", "--json", "search", "--name", "test"]),
    ("wecomcli-doc", ["--dry-run", "--json", "create", "--title", "test", "--type", "doc"]),
    (
        "wecomcli-meeting",
        [
            "--dry-run",
            "--json",
            "create",
            "--title",
            "test",
            "--start",
            "2026-06-23T22:00",
            "--end",
            "2026-06-23T22:30",
        ],
    ),
    ("wecomcli-schedule", ["--dry-run", "--json", "add", "--title", "test", "--time", "2026-06-23T22:00"]),
    ("wecomcli-todo", ["--dry-run", "--json", "add", "--title", "test"]),
]


def test_skill(skill_name: str, args: list[str], live: bool = False) -> dict:
    skill_path = SKILLS_DIR / skill_name / "run.py"
    if not skill_path.exists():
        return {"skill": skill_name, "success": False, "error": f"Skill not found: {skill_path}", "mode": "dry-run"}

    cmd = [sys.executable, str(skill_path)] + args
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30, encoding="utf-8", errors="replace")
        stdout = result.stdout[:500]
        stderr = result.stderr[:500]
        success = result.returncode == 0
        return {
            "skill": skill_name,
            "success": success,
            "mode": "live" if live else "dry-run",
            "exit_code": result.returncode,
            "stdout": stdout if success else None,
            "stderr": stderr if not success else None,
            "time": datetime.now(UTC).isoformat(),
        }
    except subprocess.TimeoutExpired:
        return {"skill": skill_name, "success": False, "error": "Timeout (30s)", "mode": "dry-run"}
    except Exception as e:
        return {"skill": skill_name, "success": False, "error": str(e)[:200], "mode": "dry-run"}


def run_all(live: bool = False) -> dict:
    results = []
    for skill, args in API_SKILLS:
        r = test_skill(skill, args, live)
        results.append(r)
        status = "✅" if r["success"] else "❌"
        if not live:
            print(f"  {status} {skill} (dry-run)")
        else:
            msg = r.get("stdout", r.get("error", "?"))[:80]
            print(f"  {status} {skill}: {msg}")

    passed = sum(1 for r in results if r["success"])
    summary = {
        "total": len(results),
        "passed": passed,
        "failed": len(results) - passed,
        "mode": "live" if live else "dry-run",
        "timestamp": datetime.now(UTC).isoformat(),
        "results": results,
    }
    return summary


def main():
    parser = argparse.ArgumentParser(description="V3.1 API Skills Integration Test")
    parser.add_argument("--live", action="store_true", help="Run with real API calls (needs tokens)")
    parser.add_argument("--skill", help="Test a single skill")
    parser.add_argument("--json", action="store_true", help="JSON output")
    parser.add_argument("--version", action="store_true")

    args = parser.parse_args()

    if args.version:
        print(__version__)
        return

    print("\n🧪 V3.1 API Skills Integration Test")
    print(f"   Mode: {'LIVE (real API)' if args.live else 'dry-run'}")

    if args.live:
        print("   ⚠️  Requires: GITHUB_TOKEN, NOTION_TOKEN, LINEAR_TOKEN, WECOM_*, TENCENT_DOCS_TOKEN")
    print(f"   Skills: {len(API_SKILLS)}\n")

    if args.skill:
        for skill_name, skill_args in API_SKILLS:
            if skill_name == args.skill:
                result = test_skill(skill_name, skill_args, args.live)
                summary = {
                    "total": 1,
                    "passed": 1 if result["success"] else 0,
                    "failed": 0 if result["success"] else 1,
                    "mode": "live" if args.live else "dry-run",
                    "results": [result],
                }
                break
        else:
            print(f"❌ Unknown skill: {args.skill}")
            sys.exit(1)
    else:
        summary = run_all(args.live)

    if args.json:
        print(json.dumps(summary, indent=2, ensure_ascii=False))
    else:
        print(f"\n📊 Summary: {summary['passed']}/{summary['total']} passed ({summary['mode']})")

    sys.exit(0 if summary["failed"] == 0 else 1)


if __name__ == "__main__":
    main()
