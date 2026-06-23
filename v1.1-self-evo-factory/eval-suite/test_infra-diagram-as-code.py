#!/usr/bin/env python3
"""Test suite for infra-diagram-as-code run.py"""
import json
import os
import subprocess
import sys
import tempfile

RUN_PY = os.path.join(os.path.dirname(__file__), "..", "..", "skills", "infra-diagram-as-code", "run.py")

def run(cmd_args):
    return subprocess.run(
        ["python", RUN_PY] + cmd_args,
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )

def test_default_template_output():
    """Test: default (microservices) template generates output."""
    proc = run(["--dry-run", "--json"])
    assert proc.returncode == 0
    data = json.loads(proc.stdout)
    assert "nodes" in data
    assert len(data["nodes"]) > 0
    assert "edges" in data
    print("[PASS] test_default_template_output (nodes={})".format(len(data["nodes"])))

def test_mermaid_format():
    """Test: mermaid format produces valid diagram."""
    proc = run(["--template", "aws", "--format", "mermaid"])
    assert proc.returncode == 0
    output = proc.stdout
    assert ("graph" in output or "flowchart" in output)
    assert "CloudFront" in output
    assert "-->" in output
    print("[PASS] test_mermaid_format")

def test_cicd_template():
    """Test: CI/CD template in mermaid format (avoids unicode issues)."""
    proc = run(["--template", "cicd", "--format", "mermaid"])
    assert proc.returncode == 0
    output = proc.stdout
    assert ("graph" in output or "flowchart" in output)
    assert "Pipeline" in output or "CI" in output
    print("[PASS] test_cicd_template")

if __name__ == "__main__":
    test_default_template_output()
    test_mermaid_format()
    test_cicd_template()
    print("\nAll infra-diagram-as-code tests passed!")
