#!/usr/bin/env python3
"""Phoenix Coordinator Integration Test."""
import sys
sys.path.insert(0, r"D:\bobo\projects\v1.1-self-evo-factory")

from core.coordinator_agent import CoordinatorAgent

def test_phoenix_coordination():
    coord = CoordinatorAgent()
    print("[Phoenix] Testing parallel_dispatch with worktree isolation...")
    result = coord.parallel_dispatch("Write a React counter component")
    print(f"[Phoenix] Parallel dispatch result: {result}")
    
    print("[Phoenix] Integration test complete!")

if __name__ == "__main__":
    test_phoenix_coordination()