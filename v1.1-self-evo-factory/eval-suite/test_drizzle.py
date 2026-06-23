#!/usr/bin/env python3
"""Test suite for drizzle run.py"""
import json
import os
import subprocess
import sys
import tempfile

RUN_PY = os.path.join(os.path.dirname(__file__), "..", "..", "skills", "drizzle", "run.py")

def run(cmd_args):
    return subprocess.run(
        ["python", RUN_PY] + cmd_args,
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )

def test_dry_run_no_config():
    """Test: dry-run with no config shows error."""
    with tempfile.TemporaryDirectory() as tmpdir:
        proc = run(["--dir", tmpdir, "--dry-run", "--json"])
        # exit 1 because no config found
        data = json.loads(proc.stdout)
        assert data.get("config_found") is False
        assert "error" in data
        print("[PASS] test_dry_run_no_config")

def test_dry_run_with_config():
    """Test: dry-run with a config file works."""
    with tempfile.TemporaryDirectory() as tmpdir:
        cfg_path = os.path.join(tmpdir, "drizzle.config.ts")
        with open(cfg_path, "w", encoding="utf-8") as f:
            f.write('export default { schema: "./schema.ts", out: "./migrations" };\n')

        proc = run(["--config", cfg_path, "--status", "--dry-run", "--json"])
        assert proc.returncode == 0, f"Exit {proc.returncode}: {proc.stderr}"
        data = json.loads(proc.stdout)
        assert data["config_found"] is True
        assert "results" in data
        print("[PASS] test_dry_run_with_config")

if __name__ == "__main__":
    test_dry_run_no_config()
    test_dry_run_with_config()
    print("\nAll drizzle tests passed!")
