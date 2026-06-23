#!/usr/bin/env python3
"""
Eval Suite — add-setting-env Tests
====================================
Tests the add-setting-env run.py:
1. --help output
2. --dry-run mode
3. Missing variable detection
4. Extra variable detection
5. Valid env (no issues)
6. JSON output mode
7. Missing file handling
8. Auto-detection of .env files
"""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
SKILL_DIR = PROJECT_ROOT.parent / "skills" / "add-setting-env"
RUN_PY = SKILL_DIR / "run.py"

os.environ.setdefault("PYTHONIOENCODING", "utf-8")


def run_add_setting_env(args_list):
    """Run add-setting-env run.py and return (returncode, stdout, stderr)."""
    cmd = [sys.executable, str(RUN_PY)] + args_list
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
    )
    return result.returncode, result.stdout, result.stderr


def create_temp_env_files(example_content=None, env_content=None):
    """Create temporary .env.example and .env files. Returns (tmpdir, example_path, env_path)."""
    tmpdir = tempfile.mkdtemp()
    example_path = os.path.join(tmpdir, ".env.example")
    env_path = os.path.join(tmpdir, ".env")

    if example_content is not None:
        Path(example_path).write_text(example_content, encoding="utf-8")
    if env_content is not None:
        Path(env_path).write_text(env_content, encoding="utf-8")

    return tmpdir, example_path, env_path


def test_01_help():
    """--help should show usage."""
    print("TEST 01: --help output")
    rc, stdout, stderr = run_add_setting_env(["--help"])

    if rc != 0 or "--example" not in stdout:
        print(f"  FAIL: --help missing --example")
        print(f"  stdout: {stdout[:300]}")
        return False

    print(f"  PASS: --help shows options")
    return True


def test_02_dry_run():
    """Dry-run should not need actual files."""
    print("TEST 02: Dry-run mode")
    rc, stdout, stderr = run_add_setting_env([
        "--dry-run",
        "--env", "/tmp/fake.env",
        "--example", "/tmp/fake.env.example",
    ])

    if rc != 0:
        print(f"  FAIL: Dry-run should succeed even with fake paths (rc={rc})")
        print(f"  stderr: {stderr[:300]}")
        return False

    if "[DRY-RUN]" not in stdout:
        print(f"  FAIL: No dry-run indicator")
        print(f"  stdout: {stdout[:200]}")
        return False

    print(f"  PASS: Dry-run works with fake paths")
    return True


def test_03_missing_variables():
    """Detect variables in .env.example that are missing from .env."""
    print("TEST 03: Missing variable detection")

    example = """# Database
DATABASE_URL=postgresql://localhost:5432/db
DATABASE_HOST=localhost
DATABASE_PORT=5432

# App
APP_NAME=myapp
APP_ENV=development
APP_PORT=3000
"""

    env = """DATABASE_URL=postgresql://prod:5432/db
APP_NAME=myapp
"""

    tmpdir, example_path, env_path = create_temp_env_files(example, env)

    rc, stdout, stderr = run_add_setting_env([
        "--example", example_path,
        "--env", env_path,
        "--json",
    ])

    try:
        data = json.loads(stdout)
        validation = data.get("validation", {})
        missing = validation.get("missing", {})

        expected_missing = {"DATABASE_HOST", "DATABASE_PORT", "APP_ENV", "APP_PORT"}
        actual_missing = set(missing.keys())

        if expected_missing != actual_missing:
            print(f"  FAIL: Expected missing {expected_missing}, got {actual_missing}")
            return False

        assert data.get("success") == False, "Should be invalid"
        print(f"  PASS: Detected {len(missing)} missing variables correctly")
        return True
    except (json.JSONDecodeError, AssertionError, KeyError) as e:
        print(f"  FAIL: {e}")
        print(f"  stdout: {stdout[:500]}")
        return False


def test_04_extra_variables():
    """Detect variables in .env that are not in .env.example."""
    print("TEST 04: Extra variable detection")

    example = """APP_NAME=myapp
APP_PORT=3000
"""

    env = """APP_NAME=myapp
APP_PORT=3000
EXTRA_VAR=something
ANOTHER_EXTRA=hello
"""

    tmpdir, example_path, env_path = create_temp_env_files(example, env)

    rc, stdout, stderr = run_add_setting_env([
        "--example", example_path,
        "--env", env_path,
        "--json",
    ])

    try:
        data = json.loads(stdout)
        validation = data.get("validation", {})
        extra = validation.get("extra", {})

        expected_extra = {"EXTRA_VAR", "ANOTHER_EXTRA"}
        actual_extra = set(extra.keys())

        if expected_extra != actual_extra:
            print(f"  FAIL: Expected extra {expected_extra}, got {actual_extra}")
            return False

        print(f"  PASS: Detected {len(extra)} extra variables correctly")
        return True
    except (json.JSONDecodeError, AssertionError, KeyError) as e:
        print(f"  FAIL: {e}")
        print(f"  stdout: {stdout[:500]}")
        return False


def test_05_all_valid():
    """All variables present and matching should report valid."""
    print("TEST 05: Valid .env (no issues)")

    example = """APP_NAME=myapp
APP_PORT=3000
DATABASE_URL=postgresql://localhost/db
"""

    env = """APP_NAME=myapp
APP_PORT=3000
DATABASE_URL=postgresql://localhost/db
"""

    tmpdir, example_path, env_path = create_temp_env_files(example, env)

    rc, stdout, stderr = run_add_setting_env([
        "--example", example_path,
        "--env", env_path,
        "--json",
    ])

    try:
        data = json.loads(stdout)
        validation = data.get("validation", {})

        assert data.get("success") == True, f"Expected valid: {data}"
        assert validation.get("is_valid") == True, f"Expected is_valid=True"
        assert len(validation.get("missing", {})) == 0
        assert len(validation.get("extra", {})) == 0

        print(f"  PASS: Valid env correctly reported")
        return True
    except (json.JSONDecodeError, AssertionError, KeyError) as e:
        print(f"  FAIL: {e}")
        print(f"  stdout: {stdout[:500]}")
        return False


def test_06_json_output():
    """JSON output includes all required fields."""
    print("TEST 06: JSON output structure")

    example = "APP_NAME=myapp\n"
    env = "APP_NAME=myapp\n"

    tmpdir, example_path, env_path = create_temp_env_files(example, env)

    rc, stdout, stderr = run_add_setting_env([
        "--example", example_path,
        "--env", env_path,
        "--json",
    ])

    try:
        data = json.loads(stdout)
        required_keys = ["success", "timestamp", "env_path", "example_path", "validation", "suggestions"]
        missing_keys = [k for k in required_keys if k not in data]

        if missing_keys:
            print(f"  FAIL: Missing keys: {missing_keys}")
            return False

        assert "timestamp" in data
        assert "T" in data["timestamp"], f"Not ISO: {data['timestamp']}"

        print(f"  PASS: JSON has all {len(required_keys)} required keys")
        return True
    except (json.JSONDecodeError, AssertionError) as e:
        print(f"  FAIL: {e}")
        print(f"  stdout: {stdout[:500]}")
        return False


def test_07_missing_file():
    """Missing file should produce clear error."""
    print("TEST 07: Missing file handling")
    rc, stdout, stderr = run_add_setting_env([
        "--example", "/tmp/__nonexistent__.env.example",
        "--env", "/tmp/__nonexistent__.env",
        "--json",
    ])

    try:
        data = json.loads(stdout)
        assert data.get("success") == False, f"Expected failure: {data}"
        assert data.get("errors"), f"Expected errors list: {data}"
        print(f"  PASS: Error reported for missing files")
        return True
    except (json.JSONDecodeError, AssertionError) as e:
        print(f"  FAIL: {e}")
        return False


def test_08_comments_and_blanks():
    """Parser should handle comments, blank lines, and export keyword."""
    print("TEST 08: Comments, blanks, and export handling")

    example = """# Database config
DATABASE_URL=postgresql://localhost/db

# App config
APP_NAME=myapp
export APP_PORT=3000

# Blank line above this
"""

    env = """# This is a comment
DATABASE_URL=postgresql://localhost/db

APP_NAME=myapp
export APP_PORT=3000
"""

    tmpdir, example_path, env_path = create_temp_env_files(example, env)

    rc, stdout, stderr = run_add_setting_env([
        "--example", example_path,
        "--env", env_path,
        "--json",
    ])

    try:
        data = json.loads(stdout)
        validation = data.get("validation", {})

        assert data.get("success") == True, f"Expected success: {data}"
        assert len(validation.get("missing", {})) == 0, f"Unexpected missing: {validation.get('missing')}"

        print(f"  PASS: Comments and export handled correctly")
        return True
    except (json.JSONDecodeError, AssertionError) as e:
        print(f"  FAIL: {e}")
        print(f"  stdout: {stdout[:500]}")
        return False


def test_09_quoted_values():
    """Parser should strip quotes from values."""
    print("TEST 09: Quoted value handling")

    example = """SINGLE_QUOTED='hello world'
DOUBLE_QUOTED="foo bar"
UNQUOTED=plain
"""

    env = """SINGLE_QUOTED=hello world
DOUBLE_QUOTED=foo bar
UNQUOTED=plain
"""

    tmpdir, example_path, env_path = create_temp_env_files(example, env)

    rc, stdout, stderr = run_add_setting_env([
        "--example", example_path,
        "--env", env_path,
        "--json",
    ])

    try:
        data = json.loads(stdout)
        assert data.get("success") == True, f"Expected success: {data}"
        print(f"  PASS: Quoted values correctly parsed")
        return True
    except (json.JSONDecodeError, AssertionError) as e:
        print(f"  FAIL: {e}")
        print(f"  stdout: {stdout[:500]}")
        return False


def test_10_suggestions_when_invalid():
    """Suggestions should be generated when variables are missing."""
    print("TEST 10: Suggestions for invalid env")

    example = "MISSING_VAR=default_value\nANOTHER=some_default\n"
    env = ""

    tmpdir, example_path, env_path = create_temp_env_files(example, env)

    rc, stdout, stderr = run_add_setting_env([
        "--example", example_path,
        "--env", env_path,
        "--json",
    ])

    try:
        data = json.loads(stdout)
        suggestions = data.get("suggestions", [])
        assert len(suggestions) > 0, f"Expected suggestions: {data}"
        assert "MISSING_VAR" in suggestions[0] or "2 missing" in suggestions[0].lower()
        print(f"  PASS: Suggestions generated")
        return True
    except (json.JSONDecodeError, AssertionError) as e:
        print(f"  FAIL: {e}")
        print(f"  stdout: {stdout[:500]}")
        return False


def main():
    tests = [
        ("Help", test_01_help),
        ("Dry-run", test_02_dry_run),
        ("Missing vars", test_03_missing_variables),
        ("Extra vars", test_04_extra_variables),
        ("All valid", test_05_all_valid),
        ("JSON output", test_06_json_output),
        ("Missing file", test_07_missing_file),
        ("Comments/blanks", test_08_comments_and_blanks),
        ("Quoted values", test_09_quoted_values),
        ("Suggestions", test_10_suggestions_when_invalid),
    ]

    print("=" * 50)
    print("Eval Suite — add-setting-env Tests")
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
