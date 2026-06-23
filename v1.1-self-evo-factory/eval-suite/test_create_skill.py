#!/usr/bin/env python3
"""
Eval Suite — create-skill Tests
=================================
Tests the create-skill run.py:
1. Creates a skill from basic template
2. Creates a skill from advanced template
3. Dry-run mode
4. JSON output mode
5. Duplicate skill detection
6. Invalid name rejection
7. --help works
"""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
SKILL_DIR = PROJECT_ROOT.parent / "skills" / "create-skill"
RUN_PY = SKILL_DIR / "run.py"

os.environ.setdefault("PYTHONIOENCODING", "utf-8")


def run_create_skill(args_list):
    """Run create-skill run.py and return (returncode, stdout, stderr)."""
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


def cleanup(name):
    """Remove test skill directory."""
    target = SKILL_DIR.parent / name
    if target.exists():
        shutil.rmtree(target, ignore_errors=True)


def test_01_create_basic_skill():
    """Create a basic skill template."""
    print("TEST 01: Create basic skill")
    name = "__test_basic_skill__"
    cleanup(name)

    rc, stdout, stderr = run_create_skill([
        "--name", name,
        "--description", "A test basic skill",
    ])

    target = SKILL_DIR.parent / name
    success = rc == 0 and target.is_dir()

    if not success:
        print(f"  FAIL: rc={rc}")
        print(f"  stdout: {stdout[:300]}")
        print(f"  stderr: {stderr[:300]}")
        cleanup(name)
        return False

    # Verify files exist
    for fname in ["SKILL.md", "_meta.json", "run.py"]:
        if not (target / fname).is_file():
            print(f"  FAIL: Missing {fname}")
            cleanup(name)
            return False

    # Verify _meta.json content
    meta = json.loads((target / "_meta.json").read_text(encoding="utf-8"))
    if meta.get("name") != name:
        print(f"  FAIL: Wrong name in _meta.json: {meta.get('name')}")
        cleanup(name)
        return False

    # Verify SKILL.md has the description
    skill_md = (target / "SKILL.md").read_text(encoding="utf-8")
    if "A test basic skill" not in skill_md:
        print(f"  FAIL: Description not in SKILL.md")
        cleanup(name)
        return False

    print(f"  PASS: Basic skill created with 3 files")
    cleanup(name)
    return True


def test_02_create_advanced_skill():
    """Create an advanced skill template."""
    print("TEST 02: Create advanced skill")
    name = "__test_advanced_skill__"
    cleanup(name)

    rc, stdout, stderr = run_create_skill([
        "--name", name,
        "--description", "Advanced test skill",
        "--template", "advanced",
    ])

    target = SKILL_DIR.parent / name
    success = rc == 0 and target.is_dir()

    if not success:
        print(f"  FAIL: rc={rc}")
        print(f"  stderr: {stderr[:300]}")
        cleanup(name)
        return False

    # Advanced template should have subcommands
    run_py_content = (target / "run.py").read_text(encoding="utf-8")
    if "subparsers" not in run_py_content:
        print(f"  FAIL: Advanced template missing subparsers")
        cleanup(name)
        return False

    print(f"  PASS: Advanced skill created with subcommand support")
    cleanup(name)
    return True


def test_03_dry_run():
    """Dry-run should not create directory."""
    print("TEST 03: Dry-run mode")
    name = "__test_dryrun_skill__"
    cleanup(name)

    rc, stdout, stderr = run_create_skill([
        "--name", name,
        "--description", "Dry run test",
        "--dry-run",
    ])

    target = SKILL_DIR.parent / name
    dir_created = target.exists()

    if dir_created:
        print(f"  FAIL: Directory created despite --dry-run")
        cleanup(name)
        return False

    if "[DRY-RUN]" not in stdout:
        print(f"  FAIL: No dry-run indicator in output")
        print(f"  stdout: {stdout[:200]}")
        return False

    print(f"  PASS: Dry-run did not create directory")
    return True


def test_04_json_output():
    """JSON output should produce valid JSON."""
    print("TEST 04: JSON output mode")
    name = "__test_json_skill__"
    cleanup(name)

    rc, stdout, stderr = run_create_skill([
        "--name", name,
        "--description", "JSON test",
        "--json",
    ])

    try:
        data = json.loads(stdout)
        assert data.get("success") == True, f"Expected success: {data}"
        assert data["name"] == name, f"Wrong name: {data.get('name')}"
        assert len(data.get("files_created", [])) == 3, f"Expected 3 files: {data}"
        print(f"  PASS: Valid JSON with correct fields")
        cleanup(name)
        return True
    except (json.JSONDecodeError, AssertionError) as e:
        print(f"  FAIL: {e}")
        print(f"  stdout: {stdout[:300]}")
        cleanup(name)
        return False


def test_05_duplicate_skill():
    """Creating duplicate skill should fail."""
    print("TEST 05: Duplicate skill detection")
    name = "__test_dup_skill__"
    cleanup(name)

    # First create
    rc1, _, _ = run_create_skill(["--name", name, "--description", "First"])
    # Second create (should fail)
    rc2, stdout2, stderr2 = run_create_skill(["--name", name, "--description", "Second"])

    if rc2 == 0:
        print(f"  FAIL: Duplicate creation should fail (rc={rc2})")
        cleanup(name)
        return False

    if "already exists" not in stdout2 + stderr2:
        print(f"  FAIL: No 'already exists' message")
        print(f"  out: {stdout2[:200]} | err: {stderr2[:200]}")
        cleanup(name)
        return False

    print(f"  PASS: Duplicate skill correctly rejected")
    cleanup(name)
    return True


def test_06_invalid_name():
    """Invalid skill names should be rejected."""
    print("TEST 06: Invalid name rejection")

    bad_names = ["name/with/slash", "name\\with\\backslash"]
    all_ok = True

    for bad_name in bad_names:
        rc, stdout, stderr = run_create_skill([
            "--name", bad_name,
            "--description", "Bad name test",
        ])
        if rc == 0:
            print(f"  FAIL: Should reject name '{bad_name}'")
            all_ok = False

    if all_ok:
        print(f"  PASS: Invalid names correctly rejected")
    return all_ok


def test_07_help():
    """--help should work."""
    print("TEST 07: --help output")
    rc, stdout, stderr = run_create_skill(["--help"])

    if rc != 0 or "--name" not in stdout:
        print(f"  FAIL: --help output missing expected content")
        print(f"  stdout: {stdout[:300]}")
        return False

    print(f"  PASS: --help shows usage")
    return True


def main():
    tests = [
        ("Basic skill", test_01_create_basic_skill),
        ("Advanced skill", test_02_create_advanced_skill),
        ("Dry-run", test_03_dry_run),
        ("JSON output", test_04_json_output),
        ("Duplicate detection", test_05_duplicate_skill),
        ("Invalid name", test_06_invalid_name),
        ("Help", test_07_help),
    ]

    print("=" * 50)
    print("Eval Suite — create-skill Tests")
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
