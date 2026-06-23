#!/usr/bin/env python3
"""Test suite for security-audit run.py"""
import json
import os
import subprocess
import sys
import tempfile

RUN_PY = os.path.join(os.path.dirname(__file__), "..", "..", "skills", "security-audit", "run.py")

def run(cmd_args):
    return subprocess.run(
        ["python", RUN_PY] + cmd_args,
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )

def test_detect_hardcoded_secret():
    """Test: hardcoded API key is detected."""
    with tempfile.TemporaryDirectory() as tmpdir:
        pyfile = os.path.join(tmpdir, "test.py")
        with open(pyfile, "w", encoding="utf-8") as f:
            f.write('API_KEY = "sk-1234567890abcdef"\n')

        proc = run(["--file", pyfile, "--json"])
        data = json.loads(proc.stdout)
        assert len(data["vulnerabilities"]) >= 1
        assert any("secret" in v["message"].lower() for v in data["vulnerabilities"])
        print("[PASS] test_detect_hardcoded_secret")

def test_detect_sql_injection():
    """Test: raw SQL execution is detected."""
    with tempfile.TemporaryDirectory() as tmpdir:
        pyfile = os.path.join(tmpdir, "test.py")
        with open(pyfile, "w", encoding="utf-8") as f:
            f.write('cursor.execute(f"SELECT * FROM users WHERE id = {user_id}")\n')

        proc = run(["--file", pyfile, "--json"])
        data = json.loads(proc.stdout)
        assert any("SQL" in v["message"] for v in data["vulnerabilities"])
        print("[PASS] test_detect_sql_injection")

if __name__ == "__main__":
    test_detect_hardcoded_secret()
    test_detect_sql_injection()
    print("\nAll security-audit tests passed!")
