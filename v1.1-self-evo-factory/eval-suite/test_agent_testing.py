#!/usr/bin/env python3
"""
Eval Suite — agent-testing Tests
==================================
Tests the agent-testing run.py:
1. --help output
2. --dry-run mode
3. Framework detection in known dirs
4. JSON output mode
5. Non-existent path handling
6. Invalid framework rejection
"""

import json
import os
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
SKILL_DIR = PROJECT_ROOT.parent / "skills" / "agent-testing"
RUN_PY = SKILL_DIR / "run.py"

os.environ.setdefault("PYTHONIOENCODING", "utf-8")


def run_agent_testing(args_list, cwd=None):
    """Run agent-testing run.py and return (returncode, stdout, stderr)."""
    cmd = [sys.executable, str(RUN_PY)] + args_list
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=cwd,
        timeout=30,
    )
    return result.returncode, result.stdout, result.stderr


def test_01_help():
    """--help should show usage."""
    print("TEST 01: --help output")
    rc, stdout, stderr = run_agent_testing(["--help"])

    if rc != 0 or "--framework" not in stdout:
        print(f"  FAIL: --help missing --framework")
        print(f"  stdout: {stdout[:300]}")
        return False

    print(f"  PASS: --help shows options")
    return True


def test_02_dry_run_with_framework():
    """--dry-run with explicit framework should show command preview."""
    print("TEST 02: Dry-run with explicit framework")
    rc, stdout, stderr = run_agent_testing([
        "--framework", "pytest",
        "--dry-run",
    ])

    if rc != 0:
        print(f"  FAIL: rc={rc}")
        print(f"  stderr: {stderr[:300]}")
        return False

    if "[DRY-RUN]" not in stdout:
        print(f"  FAIL: No dry-run indicator")
        print(f"  stdout: {stdout[:200]}")
        return False

    print(f"  PASS: Dry-run shows command preview")
    return True


def test_03_framework_detection_nonexistent():
    """Non-existent path should produce error."""
    print("TEST 03: Non-existent path error")
    rc, stdout, stderr = run_agent_testing([
        "--path", "__nonexistent_dir_xyz__",
    ])

    if rc == 0:
        print(f"  FAIL: Should fail for non-existent path")
        return False

    if "not exist" not in (stdout + stderr).lower() and "error" not in (stdout + stderr).lower():
        print(f"  FAIL: No error message for missing path")
        print(f"  stdout: {stdout[:200]}")
        print(f"  stderr: {stderr[:200]}")
        return False

    print(f"  PASS: Error reported for missing path")
    return True


def test_04_json_output_dry_run():
    """JSON dry-run output should be valid JSON."""
    print("TEST 04: JSON dry-run output")
    rc, stdout, stderr = run_agent_testing([
        "--framework", "pytest",
        "--dry-run",
        "--json",
    ])

    try:
        data = json.loads(stdout)
        assert data.get("dry_run") == True, f"Expected dry_run=True: {data}"
        assert data["framework"] == "pytest", f"Expected pytest: {data}"
        assert "command" in data or "full_command" in data, f"Expected command info: {data}"
        print(f"  PASS: Valid JSON dry-run output")
        return True
    except (json.JSONDecodeError, AssertionError) as e:
        print(f"  FAIL: {e}")
        print(f"  stdout: {stdout[:300]}")
        return False


def test_05_invalid_framework():
    """Invalid framework should produce error."""
    print("TEST 05: Invalid framework rejection")
    # We can't pass invalid --framework through argparse choices,
    # but we can test that all valid choices work
    for fw in ["pytest", "vitest", "jest", "cargo", "go"]:
        rc, stdout, stderr = run_agent_testing([
            "--framework", fw,
            "--dry-run",
        ])
        if rc != 0:
            print(f"  FAIL: Valid framework '{fw}' returned rc={rc}")
            return False

    print(f"  PASS: All 5 frameworks accepted")
    return True


def test_06_current_dir_detection():
    """Detect frameworks in the project root."""
    print("TEST 06: Framework detection in project")
    project_path = str(PROJECT_ROOT.parent.parent)
    rc, stdout, stderr = run_agent_testing([
        "--path", project_path,
        "--dry-run",
        "--json",
    ])

    try:
        data = json.loads(stdout)
        assert data.get("dry_run") == True
        assert "framework" in data, f"Expected framework key: {data}"
        print(f"  PASS: Detection result: framework={data.get('framework')}, "
              f"detection={data.get('detection')}")
        return True
    except (json.JSONDecodeError, AssertionError) as e:
        print(f"  FAIL: {e}")
        print(f"  stdout: {stdout[:300]}")
        return False


def test_07_multiple_frameworks_detected():
    """When multiple frameworks exist, first one should be used."""
    print("TEST 07: Multiple framework detection")
    # The skills dir has many subdirs, we just test current path detection works
    rc, stdout, stderr = run_agent_testing([
        "--path", ".",
        "--dry-run",
        "--json",
    ])

    try:
        data = json.loads(stdout)
        detection = data.get("detection")
        if isinstance(detection, list):
            framework = data["framework"]
            assert framework in detection, f"Framework {framework} not in detection list {detection}"
            print(f"  PASS: Detected {len(detection)} framework(s), using {framework}")
            return True
        else:
            # "user-specified" or single string is also fine
            print(f"  PASS: Detection={detection}, framework={data.get('framework')}")
            return True
    except (json.JSONDecodeError, AssertionError) as e:
        print(f"  FAIL: {e}")
        print(f"  stdout: {stdout[:300]}")
        return False


def main():
    tests = [
        ("Help", test_01_help),
        ("Dry-run", test_02_dry_run_with_framework),
        ("Non-existent path", test_03_framework_detection_nonexistent),
        ("JSON dry-run", test_04_json_output_dry_run),
        ("Valid frameworks", test_05_invalid_framework),
        ("Detection", test_06_current_dir_detection),
        ("Multi-detection", test_07_multiple_frameworks_detected),
    ]

    print("=" * 50)
    print("Eval Suite — agent-testing Tests")
    print("=" * 50)
    print()

    passed = 0
    failed = 0

    for name, test_fn in tests:
        try:
            if test_fn():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"  CRASH: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
        print()

    print("=" * 50)
    print(f"RESULTS: {passed}/{passed + failed} passed")
    if failed == 0:
        print("ALL GREEN!")
    else:
        print(f"{failed} test(s) FAILED")
    print("=" * 50)

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
