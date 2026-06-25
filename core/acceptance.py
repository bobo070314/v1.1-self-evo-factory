#!/usr/bin/env python3
"""core/acceptance.py — No Rubber-Stamping Quality Gate

Two hard gate functions:
- check_cso(): PRD must have required sections, concrete data, competitive analysis
- check_vis(): CSS spacing/color/accessibility checks

These run BEFORE the LLM-based coordinator check, as a fast rejection layer.
If acceptance fails here, the output never reaches the user.
"""

import re
from typing import Dict, List, Tuple


class AcceptanceGate:
    """Fast, deterministic quality checks. No LLM needed."""

    FAIL = "fail"
    WARN = "warn"
    PASS = "pass"

    @staticmethod
    def check_cso(output: str) -> Dict:
        """Check Chief Strategy Officer output (PRD)."""
        failures = []
        warnings = []

        # Must-have sections
        required_sections = {
            "用户画像": ["用户画像", "user persona", "目标用户"],
            "竞争分析": ["竞争分析", "competitive", "竞品"],
            "功能边界": ["功能边界", "不做什么", "scope", "out of scope"],
        }

        for section_name, keywords in required_sections.items():
            found = any(kw in output for kw in keywords)
            if not found:
                failures.append(f"CSO缺少必需章节: {section_name}")

        # Concrete data in user persona
        if "用户画像" in output or "persona" in output.lower():
            age_pattern = re.search(r"\d{2}\s*[岁歳]", output)
            if not age_pattern:
                failures.append("用户画像缺少具体年龄数据")

        # Competitive analysis: must name at least 2 competitors
        competitor_count = len(re.findall(r"[Aa-z0-9\s]{3,20}(?:平台|网站|产品|工具|app|APP|system|服务)", output))
        if competitor_count < 2:
            failures.append("竞争分析未列出至少2个竞品")

        # Vague word detection
        vague_words = ["可以考虑", "将来", "后期", "maybe", "perhaps", "TODO", "待定"]
        for word in vague_words:
            if word in output:
                warnings.append(f"包含模糊词: '{word}'")

        passed = len(failures) == 0
        return {
            "passed": passed,
            "agent": "cso",
            "failures": failures,
            "warnings": warnings,
        }

    @staticmethod
    def check_vis(output: str) -> Dict:
        """Check Visual Designer output (Tailwind CSS)."""
        failures = []
        warnings = []

        # CSS spacing: gap-2/gap-3/gap-4 are banned, gap-6+ required
        bad_gaps = re.findall(r"gap-[234]", output)
        if bad_gaps:
            if "gap-6" not in output and "gap-8" not in output and "gap-10" not in output:
                failures.append(f"CSS间距违规: 使用了 {' '.join(bad_gaps)}，全局gap需≥24px (gap-6+)")

        # Color: ban pure black
        if "#000000" in output or "black" in output.lower():
            if "dark:" not in output:
                warnings.append("使用了纯黑#000000，暗色模式需用#e5e5e5替代")

        # Responsive: must have sm: or md: breakpoint
        if "sm:" not in output and "md:" not in output:
            warnings.append("组件缺少响应式断点 (sm:/md:)")

        # Accessibility: interactive elements need focus ring
        has_interactive = bool(re.search(r"<(button|input|a|select|textarea)", output))
        if has_interactive and "focus:" not in output:
            failures.append("交互元素缺少focus:ring/focus:outline")

        # Animation: ban transition-all
        if "transition-all" in output:
            failures.append("禁止使用transition-all，指定具体属性 (transition-colors/transition-opacity)")

        passed = len(failures) == 0
        return {
            "passed": passed,
            "agent": "vis",
            "failures": failures,
            "warnings": warnings,
        }

    @staticmethod
    def check_code(output: str) -> Dict:
        """Check Code Agent output."""
        failures = []
        warnings = []

        # Dangerous patterns
        dangerous = [
            (r"rm\s+-rf\s+/", "危险命令: rm -rf /"),
            (r"os\.remove\([\"']/", "危险操作: os.remove('/')"),
            (r"subprocess\(shell=True[,\)]", "危险: subprocess(shell=True) 未过滤输入"),
        ]
        for pattern, msg in dangerous:
            if re.search(pattern, output):
                failures.append(msg)

        # Missing type hints (Python)
        py_funcs = re.findall(r"def (\w+)\(([^)]*)\):", output)
        for func_name, params in py_funcs:
            if params and ":" not in params:
                warnings.append(f"函数 '{func_name}' 缺少类型注解")

        # TODO detection
        if "TODO" in output or "# TODO" in output:
            warnings.append("输出中包含TODO标记")

        passed = len(failures) == 0
        return {
            "passed": passed,
            "agent": "code",
            "failures": failures,
            "warnings": warnings,
        }

    @classmethod
    def check(cls, agent_id: str, output: str) -> Dict:
        """Route to appropriate checker."""
        agent_id = agent_id.lower()
        if agent_id == "cso":
            return cls.check_cso(output)
        elif agent_id == "vis":
            return cls.check_vis(output)
        elif agent_id == "code":
            return cls.check_code(output)
        else:
            # No specific checker for this agent → run generic checks
            return cls._check_generic(output)

    @staticmethod
    def _check_generic(output: str) -> Dict:
        failures = []
        warnings = []

        # Generic checks that apply to all agents
        vague = ["TODO", "待优化", "可以考虑", "maybe later"]
        for word in vague:
            if word in output:
                warnings.append(f"包含模糊词: '{word}'")

        # Rubber-stamping: first 50 chars repeated verbatim
        if len(output) > 200:
            head = output[:50]
            rest = output[100:]
            if head in rest:
                failures.append("疑似橡皮图章(用户原文重复)")

        return {
            "passed": len(failures) == 0,
            "agent": "generic",
            "failures": failures,
            "warnings": warnings,
        }


# ---- Convenience functions ----
def check_cso(output: str) -> Dict:
    return AcceptanceGate.check_cso(output)


def check_vis(output: str) -> Dict:
    return AcceptanceGate.check_vis(output)


# ---- CLI ----
if __name__ == "__main__":
    import argparse
    import json
    import sys

    p = argparse.ArgumentParser(description="No-Rubber-Stamp Acceptance Gate")
    p.add_argument("--cso", type=str, help="Check CSO output (file path or inline text)")
    p.add_argument("--vis", type=str, help="Check VIS output (file path or inline text)")
    p.add_argument("--code", type=str, help="Check CODE output (file path or inline text)")
    p.add_argument("--json", action="store_true")
    args = p.parse_args()

    result = None

    for agent_id, input_val in [("cso", args.cso), ("vis", args.vis), ("code", args.code)]:
        if input_val:
            # Try as file path first
            import os
            if os.path.isfile(input_val):
                with open(input_val, "r", encoding="utf-8", errors="replace") as f:
                    input_val = f.read()
            result = AcceptanceGate.check(agent_id, input_val)
            break

    if result:
        if args.json:
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            print(f"Agent: {result['agent']}")
            print(f"Passed: {result['passed']}")
            for f in result["failures"]:
                print(f"  FAIL: {f}")
            for w in result["warnings"]:
                print(f"  WARN: {w}")

    sys.exit(0 if (result and result["passed"]) else 1)
