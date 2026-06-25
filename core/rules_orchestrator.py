#!/usr/bin/env python3
"""core/rules_orchestrator.py — 规则文件驱动的安全门禁 (v1.0)

在 core_orchestrator 的 Pipeline Step 4 (execute) 和 Step 5 (acceptance) 之间
插入规则检查，对 AI 输出做安全审查。

规则加载自 core/rules/*.local.md，由 config_loader 解析 YAML frontmatter。
- block 规则触发时：拦截输出，不走后续步骤
- warn 规则触发时：在 steps 里加警告标记，但不阻断
"""

import os
import sys
from typing import Dict, List, Optional

from core.rules.config_loader import load_rules, evaluate_rules

RULES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "rules")


class RulesOrchestrator:
    """规则编排器：加载本地规则文件并在 pipeline 中执行安全审查。"""

    def __init__(self):
        self._rules = []
        self._loaded = False
        self._load()

    def _load(self):
        """加载 core/rules/*.local.md 所有规则文件。"""
        try:
            self._rules = load_rules(RULES_DIR)
            self._loaded = True
        except Exception as e:
            print(f"[rules_orch] load fail: {e}", file=sys.stderr)
            self._loaded = False

    def check_output(self, output: str) -> Dict:
        """对 AI 输出做 file_write 事件评估。

        检测输出中是否包含硬编码密钥、敏感信息等。

        Returns:
            {"blocked": bool, "warnings": [str], "triggered": [str]}
        """
        if not self._loaded or not self._rules:
            return {"blocked": False, "warnings": [], "triggered": []}

        field_values = {
            "new_text": output or "",
            "content": output or "",
        }
        return self._evaluate("file_write", field_values)

    def check_command(self, command: str) -> Dict:
        """对命令做 bash 事件评估。

        检测危险命令如 rm -rf、git push -f 等。

        Returns:
            {"blocked": bool, "warnings": [], "triggered": [str]}
        """
        if not self._loaded or not self._rules:
            return {"blocked": False, "warnings": [], "triggered": []}

        field_values = {
            "command": command or "",
            "content": command or "",
        }
        return self._evaluate("bash", field_values)

    def _evaluate(self, event_type: str, field_values: Dict[str, str]) -> Dict:
        """内核对 field_values 做规则评估，分类 block/warn。"""
        results = evaluate_rules(self._rules, event_type, field_values)

        blocked = []
        warnings = []
        triggered = []

        for rule, msg in results:
            triggered.append(rule.name)
            if rule.action == "block":
                blocked.append(rule.name)
            else:
                warnings.append(rule.name)

        return {
            "blocked": len(blocked) > 0,
            "warnings": warnings,
            "triggered": triggered,
        }

    def health(self) -> Dict:
        """返回规则加载状态。"""
        return {
            "loaded": self._loaded,
            "rule_count": len(self._rules),
        }

    def reload(self):
        """重新加载规则文件（用于规则热更新场景）。"""
        self._rules = []
        self._loaded = False
        self._load()
