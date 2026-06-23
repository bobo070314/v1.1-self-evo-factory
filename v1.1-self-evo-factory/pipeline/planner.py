#!/usr/bin/env python3
"""V3.0 Planner — 任务拆解引擎 (skeleton → alpha)

Usage:
  python planner.py "deploy app and ensure security"
  python planner.py --json "audit codebase"
"""

import argparse
import json
import sys
from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class Step:
    action: str  # 技能名/动作
    params: dict  # 参数
    depends_on: List[str] = field(default_factory=list)
    description: str = ""


class Planner:
    """任务拆解器 — 用户目标 → Step DAG"""

    # V3.0-alpha: 关键词 → 技能映射表
    KEYWORD_MAP: Dict[str, List[str]] = {
        "security": ["security-audit"],
        "audit": ["security-audit"],
        "deploy": ["deployment-automation"],
        "review": ["frontend-code-review", "backend-code-review"],
        "code": ["code-navigator"],
        "pr": ["create-pr"],
        "issue": ["create-issue"],
        "note": ["release-notes-generator"],
        "migrate": ["db-migrations"],
        "drizzle": ["drizzle"],
        "diagram": ["infra-diagram-as-code"],
        "test": ["agent-testing"],
        "clone": ["clone-project"],
        "env": ["add-setting-env"],
    }

    # 依赖关系（硬编码 → V3.0-beta 换 LLM）
    DEPENDENCIES: Dict[str, List[str]] = {
        "deployment-automation": ["security-audit"],  # 部署前先审计
        "create-pr": ["frontend-code-review"],  # PR 前先 review
    }

    def plan(self, goal: str) -> List[Step]:
        """将目标拆解为步骤 DAG"""
        goal_lower = goal.lower()
        matched_skills = []

        for keyword, skills in self.KEYWORD_MAP.items():
            if keyword in goal_lower:
                for sk in skills:
                    if sk not in matched_skills:
                        matched_skills.append(sk)

        if not matched_skills:
            # Fallback: 单步执行
            return [Step(action="execute", params={"goal": goal}, description="Direct execution")]

        steps = []
        for skill in matched_skills:
            deps = self.DEPENDENCIES.get(skill, [])
            steps.append(Step(action=skill, params={}, depends_on=deps, description=f"Auto-matched: {skill}"))

        return steps

    def to_dict(self, steps: List[Step]) -> List[dict]:
        return [
            {"action": s.action, "params": s.params, "depends_on": s.depends_on, "description": s.description}
            for s in steps
        ]


def main():
    parser = argparse.ArgumentParser(description="V3.0 Planner - task decomposition engine")
    parser.add_argument("goal", nargs="?", default="deploy app and ensure security", help="User goal")
    parser.add_argument("--json", action="store_true", help="JSON output")
    parser.add_argument("--keyword-map", action="store_true", help="Show keyword→skill map")

    args = parser.parse_args()

    if args.keyword_map:
        print(json.dumps(Planner.KEYWORD_MAP, indent=2))
        return 0

    p = Planner()
    steps = p.plan(args.goal)

    output = {
        "goal": args.goal,
        "step_count": len(steps),
        "steps": p.to_dict(steps),
    }

    if args.json:
        print(json.dumps(output, indent=2, ensure_ascii=False))
    else:
        print(f"Goal: {args.goal}")
        print(f"Steps: {len(steps)}")
        for i, s in enumerate(steps, 1):
            deps = f" (depends: {', '.join(s.depends_on)})" if s.depends_on else ""
            print(f"  {i}. {s.action}{deps}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
