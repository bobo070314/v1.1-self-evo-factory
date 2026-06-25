#!/usr/bin/env python3
"""core/rules/config_loader.py — 猫抓版规则加载器

仿 hookify 的 YAML frontmatter + Markdown 规则文件格式。
每个规则文件是 .local.md，含 YAML frontmatter:

```yaml
---
name: no-rm-rf
enabled: true
event: bash          # bash | file_write | all
action: block        # block | warn
conditions:
  - field: command
    operator: regex_match
    pattern: "^rm\\s+-rf"
---
⚠️ Blocked: 危险命令 `rm -rf`。理由：{{reason}}
```

支持 6 种条件操作符：regex_match / contains / equals / not_contains / starts_with / ends_with
支持 AND 逻辑（所有条件同时满足才触发）
"""

import os, re, sys, glob
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field


@dataclass
class Condition:
    field: str     # "command" | "file_path" | "new_text" | "content"
    operator: str  # "regex_match" | "contains" | "equals" | "not_contains" | "starts_with" | "ends_with"
    pattern: str   # Value to match

    @classmethod
    def from_dict(cls, data: Dict) -> "Condition":
        return cls(
            field=data.get("field", "content"),
            operator=data.get("operator", "regex_match"),
            pattern=data.get("pattern", ""),
        )

    def evaluate(self, field_value: str) -> bool:
        """Evaluate this condition against a field value."""
        if not field_value:
            return False
        if self.operator == "regex_match":
            try:
                return bool(re.search(self.pattern, field_value))
            except re.error:
                return False
        elif self.operator == "contains":
            return self.pattern in field_value
        elif self.operator == "equals":
            return field_value == self.pattern
        elif self.operator == "not_contains":
            return self.pattern not in field_value
        elif self.operator == "starts_with":
            return field_value.startswith(self.pattern)
        elif self.operator == "ends_with":
            return field_value.endswith(self.pattern)
        return False


@dataclass
class Rule:
    name: str
    enabled: bool = True
    event: str = "all"         # bash | file_write | all
    conditions: List[Condition] = field(default_factory=list)
    action: str = "warn"       # block | warn
    category: str = "generic"  # security | quality | style
    severity: str = "high"     # critical | high | medium | low
    message: str = ""          # Warning/block message from Markdown body

    def evaluate(self, event_type: str, field_values: Dict[str, str]) -> Optional[str]:
        """Evaluate all conditions. Returns message if triggered, None if not."""
        if not self.enabled:
            return None
        if self.event != "all" and self.event != event_type:
            return None
        for cond in self.conditions:
            val = field_values.get(cond.field, "")
            if not cond.evaluate(val):
                return None  # AND logic: all must pass
        return self.message

    @classmethod
    def from_frontmatter(cls, frontmatter: Dict, message: str) -> "Rule":
        conditions = []
        if "conditions" in frontmatter:
            conditions = [Condition.from_dict(c) for c in frontmatter["conditions"]]
        if not conditions and "pattern" in frontmatter:
            # Legacy style: single pattern → auto-create condition
            event = frontmatter.get("event", "all")
            field_map = {"bash": "command", "file_write": "new_text", "all": "content"}
            conditions = [Condition(field=field_map.get(event, "content"), operator="regex_match", pattern=frontmatter["pattern"])]
        return cls(
            name=frontmatter.get("name", "unnamed"),
            enabled=frontmatter.get("enabled", True),
            event=frontmatter.get("event", "all"),
            conditions=conditions,
            action=frontmatter.get("action", "warn"),
            category=frontmatter.get("category", "generic"),
            severity=frontmatter.get("severity", "high"),
            message=message.strip(),
        )


def extract_frontmatter(content: str) -> tuple:
    """Extract YAML-like frontmatter (--- ... ---) and body from markdown."""
    if not content.startswith("---"):
        return {}, content

    parts = content.split("---", 2)
    if len(parts) < 3:
        return {}, content

    raw = parts[1]
    body = parts[2].strip()

    # Simple key-value parser (no nested YAML)
    frontmatter = {}
    current_key = None
    current_list = []
    current_dict = {}
    in_list = False
    in_dict_item = False

    for line in raw.splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        indent = len(line) - len(line.lstrip())

        if indent == 0 and ":" in line and not s.startswith("-"):
            # Finalize previous list/dict
            if in_list and current_key:
                if in_dict_item and current_dict:
                    current_list.append(current_dict)
                    current_dict = {}
                frontmatter[current_key] = current_list
                in_list = False
                in_dict_item = False
                current_list = []
            # New top-level key
            k, v = s.split(":", 1)
            k = k.strip()
            v = v.strip()
            if not v:
                current_key = k
                in_list = True
            else:
                if v.lower() == "true":
                    v = True
                elif v.lower() == "false":
                    v = False
                frontmatter[k] = v

        elif s.startswith("-") and in_list:
            if in_dict_item and current_dict:
                current_list.append(current_dict)
                current_dict = {}
            item = s[1:].strip()
            if ":" in item and "," in item:
                # Inline dict: - field: command, operator: regex_match
                d = {}
                for part in item.split(","):
                    if ":" in part:
                        k, v = part.split(":", 1)
                        d[k.strip()] = v.strip().strip('"').strip("'")
                current_list.append(d)
                in_dict_item = False
            elif ":" in item:
                in_dict_item = True
                k, v = item.split(":", 1)
                current_dict = {k.strip(): v.strip().strip('"').strip("'")}
            else:
                current_list.append(item.strip('"').strip("'"))
                in_dict_item = False

        elif indent > 2 and in_dict_item and ":" in line:
            k, v = s.split(":", 1)
            current_dict[k.strip()] = v.strip().strip('"').strip("'")

    if in_list and current_key:
        if in_dict_item and current_dict:
            current_list.append(current_dict)
        frontmatter[current_key] = current_list

    return frontmatter, body


def load_rules(rules_dir: str = None, event: str = None) -> List[Rule]:
    """Load all .local.md rule files from directory.

    Args:
        rules_dir: Directory to scan (default: core/rules/)
        event: Optional filter ("bash", "file_write", "all")
    """
    if rules_dir is None:
        rules_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)))
    else:
        rules_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", rules_dir)

    pattern = os.path.join(rules_dir, "*.local.md")
    files = glob.glob(pattern)

    rules = []
    for fp in files:
        try:
            with open(fp, "r", encoding="utf-8") as f:
                content = f.read()
            frontmatter, body = extract_frontmatter(content)
            if not frontmatter:
                continue
            rule = Rule.from_frontmatter(frontmatter, body)
            if not rule.enabled:
                continue
            if event and rule.event != "all" and rule.event != event:
                continue
            rules.append(rule)
        except (IOError, OSError) as e:
            print(f"[rules] warn: skip {os.path.basename(fp)}: {e}", file=sys.stderr)

    return rules


def evaluate_rules(rules: List[Rule], event_type: str, field_values: Dict[str, str]) -> List[tuple]:
    """Evaluate all rules. Returns list of (rule, message) for triggered rules."""
    results = []
    for rule in rules:
        msg = rule.evaluate(event_type, field_values)
        if msg:
            results.append((rule, msg))
    return results
