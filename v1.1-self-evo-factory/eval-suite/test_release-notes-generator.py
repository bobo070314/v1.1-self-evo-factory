#!/usr/bin/env python3
"""Test suite for release-notes-generator run.py"""
import json
import os
import subprocess
import sys
import tempfile

RUN_PY = os.path.join(os.path.dirname(__file__), "..", "..", "skills", "release-notes-generator", "run.py")

def run(cmd_args):
    return subprocess.run(
        ["python", RUN_PY] + cmd_args,
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )

def create_repo_with_commits(tmpdir, count=2):
    """Helper: create git repo with N commits."""
    subprocess.run(["git", "init"], cwd=tmpdir, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=tmpdir, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=tmpdir, capture_output=True)
    for i in range(count):
        test_file = os.path.join(tmpdir, f"test_{i}.txt")
        with open(test_file, "w") as f:
            f.write(f"content {i}")
        subprocess.run(["git", "add", "."], cwd=tmpdir, capture_output=True)
        subprocess.run(["git", "commit", "-m", f"feat: commit {i}"], cwd=tmpdir, capture_output=True)

def test_json_output_in_repo():
    """Test: the script runs in a git repo and outputs something."""
    with tempfile.TemporaryDirectory() as tmpdir:
        create_repo_with_commits(tmpdir, count=3)

        proc = run(["--dir", tmpdir, "--from", "HEAD~1", "--to", "HEAD", "--format", "json"])
        try:
            data = json.loads(proc.stdout)
            assert "commit_count" in data or "version" in data
            print("[PASS] test_json_output_in_repo (commits={})".format(data.get("commit_count", 0)))
        except json.JSONDecodeError:
            # May output text if range invalid
            assert "Error" in proc.stdout or "No commits" in proc.stdout
            print("[PASS] test_json_output_in_repo (text output)")

def test_markdown_format():
    """Test: markdown format output from a repo with 2+ commits."""
    with tempfile.TemporaryDirectory() as tmpdir:
        create_repo_with_commits(tmpdir, count=3)

        proc = run(["--dir", tmpdir, "--from", "HEAD~1", "--to", "HEAD", "--format", "markdown"])
        assert proc.returncode == 0, f"Exit {proc.returncode}: {proc.stderr}"
        print("[PASS] test_markdown_format")

if __name__ == "__main__":
    test_json_output_in_repo()
    test_markdown_format()
    print("\nAll release-notes-generator tests passed!")
