#!/usr/bin/env python3
"""core/coordinator_agent.py — Multi-Agent Coordinator with Quality Gates

Loads coordinator_rules.md at startup.
Every agent output goes through: Dispatch → Check → Accept/Reject → Feedback Loop.

Flow:
1. User request comes in
2. Select appropriate agent(s) from registry
3. Dispatch task to agent
4. Run acceptance check against coordinator_rules
5. If REJECT → send feedback → agent retries (max 3 rounds)
6. If ACCEPT → return to user
"""

import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any

import requests

BASE_DIR = Path(__file__).resolve().parent.parent
RULES_FILE = BASE_DIR / "core" / "coordinator_rules.md"

OLLAMA_URL = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11634")
OLLAMA_MODEL = os.environ.get("OLLAMA_CHECKER_MODEL", "qwen3.5:2b")
CHECKER_TIMEOUT = int(os.environ.get("CHECKER_TIMEOUT", "60"))

AGENT_REGISTRY = {
    "cso":  {"name": "Chief Strategy Officer", "desc": "PRD, competitive analysis, product strategy"},
    "vis":  {"name": "Visual Designer", "desc": "Tailwind CSS, responsive layout, visual components"},
    "code": {"name": "Code Agent", "desc": "Python/TypeScript, refactor, fix bugs, write tests"},
    "ops":  {"name": "Ops Agent", "desc": "Deploy, CI/CD, Docker, infrastructure"},
    "doc":  {"name": "Doc Agent", "desc": "API docs, README, technical writing"},
    "sec":  {"name": "Security Agent", "desc": "Security audit, vulnerability scan, compliance"},
}

MAX_RETRY_ROUNDS = 3


class AcceptanceResult:
    """Result of running a quality gate check."""
    __slots__ = ("passed", "agent_id", "failures", "warnings", "checker_output")

    def __init__(self, agent_id: str, passed: bool = True, failures: list = None, warnings: list = None):
        self.agent_id = agent_id
        self.passed = passed
        self.failures = failures or []
        self.warnings = warnings or []
        self.checker_output = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "passed": self.passed,
            "failures": self.failures,
            "warnings": self.warnings,
        }

    def __bool__(self):
        return self.passed


class CoordinatorAgent:
    """Loads rules, dispatches tasks, runs acceptance, closes feedback loop."""

    def __init__(self, rules_file: Optional[Path] = None):
        self.rules_file = rules_file or RULES_FILE
        self.rules: Dict[str, List[str]] = {}
        self._load_rules()
        self._history: List[Dict] = []  # Audit trail

    # ---- Load rules from Markdown ----
    def _load_rules(self):
        """Parse coordinator_rules.md into structured dict."""
        if not self.rules_file.exists():
            print(f"[coordinator] WARNING: rules file not found: {self.rules_file}")
            return

        raw = self.rules_file.read_text(encoding="utf-8", errors="replace")
        current_agent = None

        for line in raw.splitlines():
            line = line.rstrip()

            # Skip markdown headings, comments, separators
            if line.startswith("#") or line.startswith("---") or line.startswith("==="):
                continue

            # Agent header: e.g. "CSO:" (plain text, not a markdown heading)
            header_match = re.match(r"^([A-Z]+):\s*$", line)
            if header_match:
                current_agent = header_match.group(1).lower()
                self.rules.setdefault(current_agent, [])
                continue

            # Rule line: "  - Rule description" (2-space or more indent then dash)
            rule_match = re.match(r"^\s+-\s+(.+)", line)
            if current_agent and rule_match:
                rule = rule_match.group(1).strip()
                if rule and not rule.startswith("Format:"):
                    self.rules[current_agent].append(rule)

    def get_rules_for(self, agent_id: str) -> List[str]:
        """Get rules for a specific agent, plus GLOBAL rules."""
        specific = self.rules.get(agent_id.lower(), [])
        global_rules = self.rules.get("global", [])
        return specific + global_rules

    # ---- Dispatch: select agent(s) from query ----
    def select_agent(self, user_query: str) -> str:
        """Pick the best agent for this query. Simple keyword routing as baseline."""
        q = user_query.lower()

        keywords = {
            "sec":  ["安全", "漏洞", "审计", "security", "vuln", "audit"],
            "code": ["代码", "重构", "bug", "fix", "refactor", "实现", "函数", "组件"],
            "vis":  ["样式", "css", "tailwind", "ui", "配色", "布局", "响应式", "动画"],
            "ops":  ["部署", "docker", "ci", "服务器", "deploy", "发布", "ci/cd"],
            "doc":  ["文档", "readme", "api文档", "说明", "doc"],
            "cso":  ["产品", "需求", "prd", "竞品", "策略", "分析", "规划"],
        }

        scores = {}
        for agent_id, kw_list in keywords.items():
            scores[agent_id] = sum(1 for kw in kw_list if kw in q)

        if not scores or max(scores.values()) == 0:
            return "code"  # Default to code agent

        return max(scores, key=scores.get)

    # ---- Acceptance check via Ollama ----
    def check_output(self, agent_id: str, output: str, task: str = "") -> AcceptanceResult:
        """Run quality gate check against coordinator_rules using qwen3.5:2b."""

        result = AcceptanceResult(agent_id)

        rules = self.get_rules_for(agent_id)
        if not rules:
            # No rules defined for this agent → pass by default
            return result

        # Build prompt: "here are the rules, here is the output, was it violated?"
        rules_text = "\n".join(f"- {r}" for r in rules)
        output_truncated = output[:2000]  # Don't overload the small model

        prompt = (
            f"You are a quality gate checker. Given the following rules and agent output, "
            f"check if any rules are VIOLATED. Return ONLY a JSON object.\n\n"
            f"AGENT: {agent_id.upper()}\n"
            f"TASK: {task}\n\n"
            f"RULES TO CHECK:\n{rules_text}\n\n"
            f"AGENT OUTPUT:\n{output_truncated}\n\n"
            f'Return JSON: {{"passed": true/false, "failures": ["violated rule 1", ...], "warnings": ["soft issue 1", ...]}}'
        )

        try:
            resp = requests.post(
                f"{OLLAMA_URL}/api/generate",
                json={
                    "model": OLLAMA_MODEL,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"num_predict": 200, "temperature": 0.1},
                },
                timeout=CHECKER_TIMEOUT,
            )
            resp.raise_for_status()
            body = resp.json()

            answer = body.get("response", "") or body.get("thinking", "")

            # Extract JSON from response
            json_match = re.search(r"\{[\s\S]*\}", answer)
            if json_match:
                try:
                    parsed = json.loads(json_match.group())
                    result.passed = parsed.get("passed", True)
                    result.failures = parsed.get("failures", [])
                    result.warnings = parsed.get("warnings", [])
                    result.checker_output = answer
                except json.JSONDecodeError:
                    pass

        except (requests.RequestException, KeyError):
            # Ollama down → pass by default (don't block user)
            result.warnings.append("Checker unavailable - gate skipped")

        # Also run quick regex-based checks for high-signal patterns
        self._hard_checks(agent_id, output, result)

        return result

    @staticmethod
    def _hard_checks(agent_id: str, output: str, result: AcceptanceResult):
        """Fast regex-based checks that don't need LLM."""
        out_lower = output.lower()

        # GLOBAL checks
        fuzzy_words = ["todo", "待优化", "可以考虑", "probably", "maybe later"]
        for word in fuzzy_words:
            if word in out_lower:
                result.failures.append(f"Contains fuzzy word: '{word}'")

        # Rubber-stamping: output repeats user input verbatim (simple check: first 50 chars)
        if len(output) > 100 and output[:50] in output[50:]:
            result.warnings.append("Potential rubber-stamping detected (repeated content)")

        # Agent-specific hard checks
        if agent_id == "vis":
            if "gap-2" in output and "gap-6" not in output:
                result.failures.append("CSS spacing violation: uses gap-2 (minimum gap-6 required)")

        if agent_id == "ops":
            if "rollback" not in out_lower and "回滚" not in out_lower:
                if "deploy" in out_lower or "部署" in out_lower:
                    result.warnings.append("OPS output missing rollback plan")

        result.passed = len(result.failures) == 0

    # ---- Full dispatch loop ----
    def dispatch(self, user_query: str, agent_output_fn=None) -> Dict[str, Any]:
        """
        Full coordination cycle:
        1. Select agent
        2. Dispatch (caller provides output via agent_output_fn or returns which agent)
        3. Check
        4. Retry if failed (up to MAX_RETRY_ROUNDS)
        """

        agent_id = self.select_agent(user_query)
        rules = self.get_rules_for(agent_id)

        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "user_query": user_query[:200],
            "selected_agent": agent_id,
            "rules_applied": len(rules),
            "rounds": 0,
            "verdict": "pending",
        }

        # If caller provides an agent output function, run the full loop
        if agent_output_fn:
            for round_num in range(1, MAX_RETRY_ROUNDS + 1):
                entry["rounds"] = round_num

                output = agent_output_fn(agent_id, user_query)
                check = self.check_output(agent_id, output, user_query)

                if check.passed:
                    entry["verdict"] = "accepted"
                    entry["check_result"] = check.to_dict()
                    break

                entry["verdict"] = f"rejected_round_{round_num}"
                entry["last_feedback"] = json.dumps(check.failures, ensure_ascii=False)

                if round_num == MAX_RETRY_ROUNDS:
                    entry["verdict"] = "rejected_max_rounds"
            else:
                output = "(no output)"
        else:
            entry["verdict"] = f"agent_selected:{agent_id}"
            output = None

        self._history.append(entry)
        return {
            "agent_id": agent_id,
            "output": output,
            "verdict": entry["verdict"],
            "rounds": entry.get("rounds", 0),
        }

    # ---- Health check ----
    def health(self) -> Dict:
        return {
            "rules_file": str(self.rules_file),
            "rules_loaded": len(self.rules),
            "agent_rules": {k: len(v) for k, v in self.rules.items()},
            "registry_agents": len(AGENT_REGISTRY),
            "history_count": len(self._history),
            "rule_total": sum(len(v) for v in self.rules.values()),
        }


# ---- Singleton ----
_coordinator: Optional[CoordinatorAgent] = None


def get_coordinator() -> CoordinatorAgent:
    global _coordinator
    if _coordinator is None:
        _coordinator = CoordinatorAgent()
    return _coordinator


# ---- CLI ----
if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser(description="Multi-Agent Coordinator with Quality Gates")
    p.add_argument("query", nargs="?", help="User query to route")
    p.add_argument("--health", action="store_true", help="Health check")
    p.add_argument("--json", action="store_true")
    args = p.parse_args()

    coord = get_coordinator()

    if args.health:
        h = coord.health()
        if args.json:
            print(json.dumps(h, indent=2, ensure_ascii=False))
        else:
            print(f"Rules file: {h['rules_file']}")
            print(f"Rules loaded: {h['rules_loaded']} agents, {h['rule_total']} total rules")
            print(f"Agent rules: {h['agent_rules']}")
        sys.exit(0)

    if args.query:
        result = coord.dispatch(args.query)
        if args.json:
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            print(f"Agent: {result['agent_id']}")
            print(f"Verdict: {result['verdict']}")
        sys.exit(0)

    sys.exit(0)
