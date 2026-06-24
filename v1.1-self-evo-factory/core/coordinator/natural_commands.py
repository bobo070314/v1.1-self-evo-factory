"""自然语言命令解析器 — 把你的话翻译成任务

对标 Claude Code：用自然语言管 Agent
"不要橡皮图章式的验收" → 系统理解并执行
"""

import re
from dataclasses import dataclass
from typing import Optional


@dataclass
class ParsedCommand:
    """解析后的命令"""

    action: str  # create / fix / deploy / search / test / review
    target: str  # 目标描述
    constraints: list[str]  # 约束条件
    evidence_required: list[str]  # 要求的证据类型
    priority: str = "normal"  # low / normal / high / critical
    deadline: Optional[str] = None


class NaturalCommandParser:
    """自然语言命令解析器

    阶段1：规则引擎 + 正则（当前实现）
    阶段2：LLM 增强（当规则引擎无法确定时调用）
    """

    # 动作词 → action 映射
    ACTION_PATTERNS = {
        "create": [
            r"(写|创建|新建|生成|做一个?|开发|实现|build|create|make|generate|implement)",
        ],
        "fix": [
            r"(修复|修|改|修一下|改正|纠正|fix|repair|correct|patch)",
        ],
        "deploy": [
            r"(部署|发布|上线|deploy|release|publish|ship)",
        ],
        "search": [
            r"(找|搜|查|检索|定位|搜索|find|search|locate|grep|look)",
        ],
        "test": [
            r"(测试|验证|检查|跑一下|test|verify|check|validate)",
        ],
        "review": [
            r"(审查|审核|review|audit|检查代码|代码审查|code.?review)",
        ],
        "refactor": [
            r"(重构|整理|优化结构|refactor|restructure|clean.?up)",
        ],
    }

    # 约束词
    CONSTRAINT_PATTERNS = [
        (r"(不要|禁止|避免|别)[再]?(.+?)(?:[，,。\.!！]|$)", "negative"),
        (r"(必须|一定要|务必|确保)(.+?)(?:[，,。\.!！]|$)", "must"),
        (r"(优先|尽快|马上|立即|urgent|asap)", "urgent"),
        (r"(慢慢来|不急|有空再做)", "low_priority"),
        (r"(用|使用|采用)[：:\s]*(.+?)(?:框架|语言|工具|技术)", "tool_constraint"),
    ]

    # 证据要求
    EVIDENCE_PATTERNS = [
        (r"(测试通过|test.?pass|all.?green)", "test_pass"),
        (r"(文件存在|创建文件|产出文件)", "file_exists"),
        (r"(exit.?code|退出码|返回码)", "exit_code"),
        (r"(健康检查|health.?check|200)", "http_status"),
        (r"(没有错误|无报错|no.?error)", "no_error"),
        (r"(橡皮图章|不要敷衍|仔细验收|严格验收)", "strict_verify"),
    ]

    def parse(self, command: str) -> ParsedCommand:
        """解析自然语言命令
        返回 ParsedCommand 对象
        """
        action = self._detect_action(command)
        target = self._extract_target(command, action)
        constraints = self._extract_constraints(command)
        evidence = self._extract_evidence_requirements(command)
        priority = self._detect_priority(command)

        return ParsedCommand(
            action=action,
            target=target,
            constraints=constraints,
            evidence_required=evidence,
            priority=priority,
        )

    def _detect_action(self, command: str) -> str:
        for action, patterns in self.ACTION_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, command, re.IGNORECASE):
                    return action
        return "create"  # 默认

    def _extract_target(self, command: str, action: str) -> str:
        """提取目标描述（动作词后面的内容）"""
        for patterns in self.ACTION_PATTERNS.values():
            for pattern in patterns:
                match = re.search(pattern + r"[：:\s]*([^，,。\.]+)", command)
                if match:
                    target = match.group(1).strip()
                    if len(target) > 2:
                        return target

        # 回退：去掉动作词后的剩余内容
        for patterns in self.ACTION_PATTERNS.values():
            for pattern in patterns:
                command = re.sub(pattern, "", command, count=1, flags=re.IGNORECASE)

        return command.strip().strip("，,。.")

    def _extract_constraints(self, command: str) -> list[str]:
        constraints = []
        for pattern, ctype in self.CONSTRAINT_PATTERNS:
            matches = re.findall(pattern, command)
            for match in matches:
                text = match if isinstance(match, str) else match[-1] if isinstance(match, tuple) else str(match)
                constraints.append(f"[{ctype}] {text}")

        # 橡皮图章相关
        if re.search(r"(橡皮图章|敷衍|随便|糊弄)", command):
            constraints.append("[must] 严格验收，拒绝橡皮图章式输出")

        return constraints

    def _extract_evidence_requirements(self, command: str) -> list[str]:
        evidence = []
        for pattern, ev_type in self.EVIDENCE_PATTERNS:
            if re.search(pattern, command, re.IGNORECASE):
                evidence.append(ev_type)

        # 强制证据：如果命令里有"验收""严格""审查"，要求 test_pass
        if re.search(r"(验收|严格|审查|审核)", command) and "test_pass" not in evidence:
            evidence.append("test_pass")

        return evidence if evidence else ["file_exists"]  # 默认至少要求文件存在

    def _detect_priority(self, command: str) -> str:
        if re.search(r"(紧急|立刻|马上|立即|urgent|asap|critical)", command, re.IGNORECASE):
            return "critical"
        if re.search(r"(尽快|优先|重要|important|high)", command, re.IGNORECASE):
            return "high"
        if re.search(r"(不急|慢慢来|有空|low)", command, re.IGNORECASE):
            return "low"
        return "normal"


# 便利函数
def parse_command(cmd: str) -> ParsedCommand:
    parser = NaturalCommandParser()
    return parser.parse(cmd)
