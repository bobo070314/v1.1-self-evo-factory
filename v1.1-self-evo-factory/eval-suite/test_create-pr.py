#!/usr/bin/env python3
"""Test suite for create-pr run.py"""
import json
import os
import subprocess
import sys
import tempfile

RUN_PY = os.path.join(os.path.dirname(__file__), "..", "..", "skills", "create-pr", "run.py")

def run(cmd_args):
    return subprocess.run(
        ["python", RUN_PY] + cmd_args,
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )

def test_dry_run_pr_creation():
    """Test: dry-run PR creation outputs preview."""
    with tempfile.TemporaryDirectory() as tmpdir:
        subprocess.run(["git", "init"], cwd=tmpdir, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=tmpdir, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=tmpdir, capture_output=True)
        test_file = os.path.join(tmpdir, "test.txt")
        with open(test_file, "w") as f:
            f.write("hello")
        subprocess.run(["git", "add", "."], cwd=tmpdir, capture_output=True)
        subprocess.run(["git", "commit", "-m", "test commit"], cwd=tmpdir, capture_output=True)

        proc = run(["--dir", tmpdir, "--title", "Test PR", "--body", "This is a test", "--dry-run", "--json"])
        assert proc.returncode == 0, f"Exit {proc.returncode}: {proc.stderr}"
        data = json.loads(proc.stdout)
        assert data["dry_run"] is True
        assert data["title"] == "Test PR"
        assert "pr" in data
        print("[PASS] test_dry_run_pr_creation")

def test_graceful_degradation_without_gh():
    """Test: gracefully degrades when gh CLI is not available."""
    with tempfile.TemporaryDirectory() as tmpdir:
        subprocess.run(["git", "init"], cwd=tmpdir, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=tmpdir, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=tmpdir, capture_output=True)
        test_file = os.path.join(tmpdir, "test.txt")
        with open(test_file, "w") as f:
            f.write("hello")
        subprocess.run(["git", "add", "."], cwd=tmpdir, capture_output=True)
        subprocess.run(["git", "commit", "-m", "test"], cwd=tmpdir, capture_output=True)

        proc = run(["--dir", tmpdir, "--title", "Test PR", "--body", "test", "--json"])
        data = json.loads(proc.stdout)
        assert "pr" in data
        print("[PASS] test_graceful_degradation_without_gh")

if __name__ == "__main__":
    test_dry_run_pr_creation()
    test_graceful_degradation_without_gh()
    print("\nAll create-pr tests passed!")
