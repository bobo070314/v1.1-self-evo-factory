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
    """Test: console.log is flagged as error."""
    with tempfile.TemporaryDirectory() as tmpdir:
        jsfile = os.path.join(tmpdir, "test.js")
        with open(jsfile, "w", encoding="utf-8") as f:
            f.write("function foo() {\n  console.log('debug');\n  return 42;\n}\n")

        proc = run(["--file", jsfile, "--json"])
        data = json.loads(proc.stdout)
        # Should have at least one issue (console.log)
        assert len(data["issues"]) >= 1
        assert any("Console" in i["message"] for i in data["issues"])
        print("[PASS] test_detect_console_log (issues={})".format(len(data["issues"])))

def test_detect_innerhtml():
    """Test: innerHTML is flagged."""
    with tempfile.TemporaryDirectory() as tmpdir:
        jsfile = os.path.join(tmpdir, "test.js")
        with open(jsfile, "w", encoding="utf-8") as f:
            f.write("document.getElementById('x').innerHTML = '<div>hi</div>';\n")

        proc = run(["--file", jsfile, "--json"])
        data = json.loads(proc.stdout)
        assert any("innerHTML" in i["message"] for i in data["issues"])
        print("[PASS] test_detect_innerhtml")

if __name__ == "__main__":
    test_detect_console_log()
    test_detect_innerhtml()
    print("\nAll frontend-code-review tests passed!")
