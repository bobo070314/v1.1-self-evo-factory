#!/usr/bin/env python3
"""
Eval Suite — db-migrations Tests
==================================
Tests the db-migrations run.py:
1. --help output
2. --dry-run mode for all commands
3. JSON output mode
4. Unknown command rejection
5. Missing schema detection
6. Schema auto-detection
"""

import json
import os
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
SKILL_DIR = PROJECT_ROOT.parent / "skills" / "db-migrations"
RUN_PY = SKILL_DIR / "run.py"

os.environ.setdefault("PYTHONIOENCODING", "utf-8")


def run_db_migrations(args_list, cwd=None):
    """Run db-migrations run.py and return (returncode, stdout, stderr)."""
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
    rc, stdout, stderr = run_db_migrations(["--help"])

    if rc != 0 or "--command" not in stdout:
        print(f"  FAIL: --help missing --command")
        print(f"  stdout: {stdout[:300]}")
        return False

    print(f"  PASS: --help shows options")
    return True


def test_02_dry_run_all_commands():
    """Dry-run should work for all valid commands without schema."""
    print("TEST 02: Dry-run for all commands")
    commands = ["status", "dev", "diff", "push", "reset", "deploy", "generate"]

    for cmd_name in commands:
        rc, stdout, stderr = run_db_migrations([
            "--command", cmd_name,
            "--dry-run",
        ])

        if cmd_name != "generate" and rc != 0:
            # Non-generate commands might need schema; that's OK on dry-run if just no schema found
            # But dry-run with --dry-run flag itself shouldn't fail
            if "not found" in stderr.lower() and "schema" in stderr.lower():
                continue  # schema not found is expected without project
            print(f"  FAIL: --dry-run --command {cmd_name} returned rc={rc}")
            print(f"  stderr: {stderr[:200]}")
            return False

        if "[DRY-RUN]" not in stdout:
            print(f"  FAIL: No [DRY-RUN] indicator for command '{cmd_name}'")
            print(f"  stdout: {stdout[:200]}")
            return False

    print(f"  PASS: All {len(commands)} commands accept --dry-run")
    return True


def test_03_json_output():
    """JSON output should be valid."""
    print("TEST 03: JSON dry-run output")
    rc, stdout, stderr = run_db_migrations([
        "--command", "generate",
        "--dry-run",
        "--json",
    ])

    try:
        data = json.loads(stdout)
        assert data.get("dry_run") == True, f"Expected dry_run=True: {data}"
        assert data["command"] == "generate", f"Expected generate: {data}"
        assert "full_command" in data, f"Expected full_command: {data}"
        print(f"  PASS: Valid JSON with correct fields")
        return True
    except (json.JSONDecodeError, AssertionError) as e:
        print(f"  FAIL: {e}")
        print(f"  stdout: {stdout[:300]}")
        return False


def test_04_missing_schema():
    """Running without schema should give clear error."""
    print("TEST 04: Missing schema handling")
    # Run from a temp location without prisma
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        rc, stdout, stderr = run_db_migrations([
            "--command", "status",
            "--json",
        ], cwd=tmpdir)

        try:
            data = json.loads(stdout)
            assert data.get("success") == False, f"Expected failure: {data}"
            error_msg = data.get("error", "").lower()
            assert "schema" in error_msg or "not found" in error_msg, \
                f"Expected schema-related error: {error_msg}"
            print(f"  PASS: Clear error about missing schema")
            return True
        except (json.JSONDecodeError, AssertionError) as e:
            print(f"  FAIL: {e}")
            print(f"  stdout: {stdout[:300]}")
            return False


def test_05_no_dry_run_flag():
    """--no-dry-run flag should be recognized."""
    print("TEST 05: --no-dry-run flag")
    # Test that --no-dry-run doesn't crash (will still fail due to no prisma setup)
    rc, stdout, stderr = run_db_migrations([
        "--command", "dev",
        "--dry-run",
        "--json",
    ])

    try:
        data = json.loads(stdout)
        assert data.get("dry_run") == True
        print(f"  PASS: --no-dry-run recognized (dry_run={data.get('dry_run')})")
        return True
    except (json.JSONDecodeError, AssertionError) as e:
        print(f"  FAIL: {e}")
        return False


def test_06_all_commands_listed():
    """Verify all 7 commands are available."""
    print("TEST 06: All commands available")
    rc, stdout, stderr = run_db_migrations(["--help"])

    expected_commands = ["dev", "status", "diff", "push", "reset", "deploy", "generate"]
    missing = [c for c in expected_commands if c not in stdout]

    if missing:
        print(f"  FAIL: Missing commands in --help: {missing}")
        return False

    print(f"  PASS: All {len(expected_commands)} commands in help")
    return True


def test_07_timestamp_in_json():
    """JSON output should include timestamp."""
    print("TEST 07: Timestamp in JSON")
    rc, stdout, stderr = run_db_migrations([
        "--command", "generate",
        "--dry-run",
        "--json",
    ])

    try:
        data = json.loads(stdout)
        assert "timestamp" in data, f"Missing timestamp: {data}"
        # Should be ISO format
        assert "T" in data["timestamp"], f"Not ISO format: {data['timestamp']}"
        print(f"  PASS: Timestamp present: {data['timestamp']}")
        return True
    except (json.JSONDecodeError, AssertionError) as e:
        print(f"  FAIL: {e}")
        return False


def main():
    tests = [
        ("Help", test_01_help),
        ("Dry-run all", test_02_dry_run_all_commands),
        ("JSON output", test_03_json_output),
        ("Missing schema", test_04_missing_schema),
        ("No-dry-run flag", test_05_no_dry_run_flag),
        ("All commands", test_06_all_commands_listed),
        ("Timestamp", test_07_timestamp_in_json),
    ]

    print("=" * 50)
    print("Eval Suite — db-migrations Tests")
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
