#!/usr/bin/env python3
"""Test suite for code-navigator run.py"""
import json
import os
import subprocess
import sys
import tempfile

RUN_PY = os.path.join(os.path.dirname(__file__), "..", "..", "skills", "code-navigator", "run.py")

def run(cmd_args):
    return subprocess.run(
        ["python", RUN_PY] + cmd_args,
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )

def test_find_python_functions():
    """Test: find functions in Python source."""
    with tempfile.TemporaryDirectory() as tmpdir:
        pyfile = os.path.join(tmpdir, "test.py")
        with open(pyfile, "w", encoding="utf-8") as f:
            f.write("def hello():\n    pass\n\ndef world():\n    return 42\n\nclass MyClass:\n    def method(self):\n        pass\n")

        proc = run(["--file", pyfile, "--list", "functions", "--json"])
        data = json.loads(proc.stdout)
        funcs = [r for r in data["results"] if r["type"] in ("function",)]
        assert len(funcs) >= 2  # hello and world
        names = {r["name"] for r in funcs}
        assert "hello" in names
        assert "world" in names
        print("[PASS] test_find_python_functions (found {})".format(len(funcs)))

def test_fuzzy_search():
    """Test: fuzzy search works."""
    with tempfile.TemporaryDirectory() as tmpdir:
        pyfile = os.path.join(tmpdir, "test.py")
        with open(pyfile, "w", encoding="utf-8") as f:
            f.write("def handleClick():\n    pass\n\ndef handleSubmit():\n    pass\n")

        proc = run(["--file", pyfile, "--fuzzy", "handle", "--json"])
        data = json.loads(proc.stdout)
        assert data["symbol_count"] >= 1
        print("[PASS] test_fuzzy_search (found {})".format(data["symbol_count"]))

if __name__ == "__main__":
    test_find_python_functions()
    test_fuzzy_search()
    print("\nAll code-navigator tests passed!")
