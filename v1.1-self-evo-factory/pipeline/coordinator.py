#!/usr/bin/env python3
"""V3.0 Coordinator — 步骤调度引擎 (skeleton → alpha)

耦合 Planner 输出，按 DAG 依赖顺序执行技能 run.py，
收集结构化 JSON 结果，失败时触发 @repair 守护。

Usage:
  python coordinator.py --steps '[{"action":"security-audit","params":{},"depends_on":[]}]'
  python coordinator.py --plan "deploy and audit"  # 调用 planner + 执行
"""

import argparse
import json
import subprocess
import sys
import time
from collections import deque
from pathlib import Path
from typing import Any, Dict, List

SKILLS_DIR = Path(r"D:\bobo\openclaw-foreign\skills")


def exec_skill(action: str, params: dict, dry_run: bool = False) -> Dict[str, Any]:
    """Execute a skill run.py and return structured result."""
    skill_path = SKILLS_DIR / action / "run.py"
    if not skill_path.exists():
        return {"ok": False, "error": f"Skill not found: {action}"}

    cmd = [sys.executable, str(skill_path)]
    if dry_run:
        cmd.extend(["--dry-run", "--json"])
    else:
        cmd.append("--json")

    start = time.time()
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=60,
            cwd=str(skill_path.parent),
        )
        elapsed = round(time.time() - start, 2)

        output = result.stdout.strip() or result.stderr.strip() or ""
        try:
            data = json.loads(output)
            data["_exit_code"] = result.returncode
            data["_elapsed"] = elapsed
            return data
        except json.JSONDecodeError:
            return {
                "ok": result.returncode == 0,
                "exit_code": result.returncode,
                "elapsed": elapsed,
                "raw_output": output[:500],
            }
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "Timed out after 60s", "_elapsed": 60}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def topological_sort(steps: List[dict]) -> List[str]:
    """Topological sort of steps by dependencies."""
    in_degree = {}
    graph = {}
    all_actions = set()

    for s in steps:
        a = s["action"]
        all_actions.add(a)
        if a not in in_degree:
            in_degree[a] = 0
            graph[a] = []
        for dep in s.get("depends_on", []):
            all_actions.add(dep)
            if dep not in in_degree:
                in_degree[dep] = 0
                graph[dep] = []
            graph[dep].append(a)
            in_degree[a] = in_degree.get(a, 0) + 1

    # Ensure all deps exist in in_degree
    for d in list(graph.keys()):
        if d not in in_degree:
            in_degree[d] = 0

    q = deque([a for a in in_degree if in_degree[a] == 0])
    order = []

    while q:
        node = q.popleft()
        if node in all_actions:
            order.append(node)
        for child in graph.get(node, []):
            in_degree[child] -= 1
            if in_degree[child] == 0:
                q.append(child)

    return order


def run_pipeline(steps: List[dict], dry_run: bool = False) -> dict:
    """Execute steps in dependency order."""
    order = topological_sort(steps)
    results = {}
    ok_count = 0

    print(f"Execution order: {' → '.join(order) if order else '(none)'}")

    for action in order:
        step_info = next((s for s in steps if s["action"] == action), {})
        params = step_info.get("params", {})
        print(f"\n▶ Running: {action} ...")
        result = exec_skill(action, params, dry_run=dry_run)
        results[action] = result

        if result.get("ok", result.get("_exit_code", 1) == 0 if "_exit_code" in result else True):
            ok_count += 1
            print(f"  ✅ {action}")
        else:
            print(f"  ❌ {action}: {result.get('error', result.get('raw_output', 'unknown'))}")

    return {
        "total": len(order),
        "passed": ok_count,
        "failed": len(order) - ok_count,
        "results": results,
    }


def main():
    parser = argparse.ArgumentParser(description="V3.0 Coordinator - step scheduler")
    parser.add_argument("--steps", help="JSON array of steps")
    parser.add_argument("--plan", help="User goal (use Planner to generate steps)")
    parser.add_argument("--dry-run", action="store_true", help="Preview mode")
    parser.add_argument("--dump-order", action="store_true", help="Only show execution order")

    args = parser.parse_args()

    steps = []

    if args.steps:
        steps = json.loads(args.steps)
    elif args.plan:
        from planner import Planner

        p = Planner()
        plan_steps = p.plan(args.plan)
        steps = p.to_dict(plan_steps)
        print(f"Planned {len(steps)} steps from goal: {args.plan}")
    else:
        # Default demo
        steps = [
            {"action": "security-audit", "params": {"dir": "."}, "depends_on": []},
            {"action": "deployment-automation", "params": {"env": "dev"}, "depends_on": ["security-audit"]},
        ]
        print("No --steps or --plan provided. Using demo pipeline.")

    if args.dump_order:
        order = topological_sort(steps)
        print(" → ".join(order))
        return 0

    result = run_pipeline(steps, dry_run=args.dry_run)
    print(f"\n{'=' * 50}")
    print(f"Pipeline complete: {result['passed']}/{result['total']} passed")
    if args.dry_run:
        print("[DRY RUN only — no real execution]")

    return 0 if result["failed"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
