#!/usr/bin/env python3
"""Test suite for deployment-automation run.py"""
import json
import os
import subprocess
import sys
import tempfile

RUN_PY = os.path.join(os.path.dirname(__file__), "..", "..", "skills", "deployment-automation", "run.py")

def run(cmd_args):
    return subprocess.run(
        ["python", RUN_PY] + cmd_args,
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )

def test_health_check_dry_run():
    """Test: health check dry-run."""
    proc = run(["--health-check", "--dry-run", "--json"])
    data = json.loads(proc.stdout)
    assert data["dry_run"] is True
    assert "results" in data
    hc = data["results"].get("health_check", {})
    assert hc.get("dry_run") is True
    print("[PASS] test_health_check_dry_run")

def test_deploy_dry_run():
    """Test: deploy dry-run with config."""
    with tempfile.TemporaryDirectory() as tmpdir:
        cfg = os.path.join(tmpdir, "deploy.yaml")
        with open(cfg, "w", encoding="utf-8") as f:
            f.write("""deploy:
  steps:
    - name: test-step
      run: echo hello
""")
        proc = run(["--config", cfg, "--deploy", "--dry-run", "--json"])
        data = json.loads(proc.stdout)
        assert data["dry_run"] is True
        assert "deploy" in data["results"]
        print("[PASS] test_deploy_dry_run")

if __name__ == "__main__":
    test_health_check_dry_run()
    test_deploy_dry_run()
    print("\nAll deployment-automation tests passed!")
