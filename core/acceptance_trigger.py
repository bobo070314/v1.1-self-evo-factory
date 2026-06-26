#!/usr/bin/env python3
"""Acceptance Trigger - Standalone validator for Claude Code style quality gate"""
import sys
sys.path.insert(0, r"D:\bobo\projects\v1.1-self-evo-factory")

from core.coordinator_agent import get_coordinator

def validate_output(agent_id: str, output: str) -> bool:
    coord = get_coordinator()
    result = coord.check_verdict(agent_id, output)
    return result.passed

if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("agent_id")
    p.add_argument("output_file")
    args = p.parse_args()
    
    output = Path(args.output_file).read_text(encoding="utf-8", errors="replace")
    passed = validate_output(args.agent_id, output)
    print(f"ACCEPTED: {passed}")
    sys.exit(0 if passed else 1)