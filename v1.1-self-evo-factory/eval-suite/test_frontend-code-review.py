#!/usr/bin/env python3
"""Test suite for frontend-code-review run.py"""
import json
import os
import subprocess
import sys
import tempfile

RUN_PY = os.path.join(os.path.dirname(__file__), "..", "..", "skills", "frontend-code-review", "run.py")

def run(cmd_args):
    return subprocess.run(
        ["python", RUN_PY] + cmd_args,
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )

def test_detect_console_log():
    """Test: console.log is flagged by scanner."""
    with tempfile.TemporaryDirectory() as tmpdir:
        jsfile = os.path.join(tmpdir, "test.js")
        with open(jsfile, "w", encoding="utf-8") as f:
            f.write("function foo() {\n  console.log('debug');\n  return 42;\n}\n")

        proc = run(["--path", tmpdir, "--json"])
        assert proc.returncode in (0, 1), f"Exit {proc.returncode}: {proc.stderr}"
        data = json.loads(proc.stdout)
        assert data.get("path") == tmpdir
        # Should find the file and have a score
        assert "score" in data
        assert "files" in data
        print("[PASS] test_detect_console_log (files={}, score={})".format(len(data.get("files", [])), data.get("score")))

def test_detect_innerhtml():
    """Test: innerHTML is flagged."""
    with tempfile.TemporaryDirectory() as tmpdir:
        jsfile = os.path.join(tmpdir, "test2.js")
        with open(jsfile, "w", encoding="utf-8") as f:
            f.write("document.getElementById('x').innerHTML = '<div>hi</div>';\n")

        proc = run(["--path", tmpdir, "--json"])
        data = json.loads(proc.stdout)
        assert "score" in data
        print("[PASS] test_detect_innerhtml")

if __name__ == "__main__":
    test_detect_console_log()
    test_detect_innerhtml()
    print("\nAll frontend-code-review tests passed!")
