"""YOLO 分类器 — 1500行专干一件事："这个操作该不该放行"

对标 Claude Code：
- YOLO = "You Only Live Once" 分类器
- 判断这个操作的风险等级
- 不是一刀切的block，而是分场景决策

场景分析：
1. 用户明确授权的操作 → 放行
2. 工作区内操作 → 低风险
3. 跨工作区操作 → 中风险
4. 系统级操作 → 高风险
5. 网络外发 → 高风险
"""

import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Optional


class YOLODecision(str, Enum):
    ALLOW = "allow"  # 放行
    ALLOW_WITH_LOG = "allow_with_log"  # 放行但记录
    ASK_USER = "ask_user"  # 需要用户确认
    BLOCK = "block"  # 阻止
    SANDBOX_ONLY = "sandbox_only"  # 仅在沙箱中执行


@dataclass
class YOLOContext:
    """YOLO 决策上下文"""

    command: str
    workdir: str  # 当前工作目录
    user_authorized: bool = False  # 用户是否明确授权
    in_workspace: bool = True  # 是否在工作区内
    is_git_operation: bool = False  # 是否git操作
    is_file_write: bool = False  # 是否文件写入
    is_network_call: bool = False  # 是否网络请求
    is_system_modification: bool = False  # 是否修改系统
    file_paths: list[str] = None  # 涉及的文件路径
    history_similar_allowed: bool = False  # 同类操作是否曾被允许


class YOLOClassifier:
    """YOLO分类器

    决策流程：
    1. 用户授权？ → ALLOW
    2. 命中CRITICAL规则？ → BLOCK
    3. 工作区内？ → ALLOW_WITH_LOG
    4. 跨工作区？ → ASK_USER
    5. 系统级 → SANDBOX_ONLY or BLOCK
    """

    # 安全的工作区路径（规范化）
    SAFE_PATHS = [
        r"D:\bobo\openclaw-foreign",
        r"D:\bobo",
    ]

    # 永远允许的安全命令模式
    ALWAYS_ALLOW_PATTERNS = [
        r"^git\s+(status|log|diff|branch|add|commit|push|pull|fetch|checkout)",
        r"^npm\s+(run|test|install|ci|build|start|dev)",
        r"^python\s+\S+\.py",
        r"^python3?\s+\S+\.py",
        r"^node\s+\S+\.(js|mjs)",
        r"^pip\s+(install|list|freeze)",
        r"^npx\s+",
        r"^yarn\s+",
        r"^cargo\s+",
        r"^go\s+(build|test|run|mod)",
        r"^dir\b",
        r"^ls\b",
        r"^cat\b",
        r"^type\b",
        r"^echo\b",
        r"^mkdir\b",
        r"^cd\b",
        r"^Get-ChildItem",
        r"^Select-Object",
        r"^gh\s+(repo|issue|pr|auth)",
    ]

    # 需要沙箱的命令
    SANDBOX_PATTERNS = [
        r"(rm\s+-rf|del\s+/[fsq])",
        r"sudo\s+",
        r"chmod\s+",
        r"chown\s+",
    ]

    # 永远阻止的命令
    ALWAYS_BLOCK_PATTERNS = [
        r":\(\)\s*\{\s*:\s*\|\:",
        r"mkfs\.",
        r">\s*/dev/[hs]d",
        r"dd\s+if=",
        r"format\s+[A-Z]:",
    ]

    def __init__(self, workdir: str = None):
        self.workdir = workdir or os.getcwd()
        self.decision_log: list[dict] = []

    def classify(self, command: str, context: Optional[YOLOContext] = None) -> YOLODecision:
        """分类命令风险等级
        返回 YOLODecision
        """
        if context is None:
            context = self._build_context(command)

        # 1. 永远阻止
        if self._matches_any(command, self.ALWAYS_BLOCK_PATTERNS):
            return self._decide(YOLODecision.BLOCK, command, "命中永久阻止规则")

        # 2. 用户授权
        if context.user_authorized:
            return self._decide(YOLODecision.ALLOW, command, "用户已授权")

        # 3. 安全命令模式
        if self._matches_any(command, self.ALWAYS_ALLOW_PATTERNS):
            return self._decide(YOLODecision.ALLOW, command, "命中安全命令模式")

        # 4. 需要沙箱
        if self._matches_any(command, self.SANDBOX_PATTERNS):
            return self._decide(YOLODecision.SANDBOX_ONLY, command, "需要沙箱隔离")

        # 5. 系统修改
        if context.is_system_modification:
            return self._decide(YOLODecision.ASK_USER, command, "涉及系统修改")

        # 6. 网络外发
        if context.is_network_call:
            return self._decide(YOLODecision.ASK_USER, command, "涉及网络外发")

        # 7. 工作区内 → 放行但记录
        if context.in_workspace:
            return self._decide(YOLODecision.ALLOW_WITH_LOG, command, "工作区内操作")

        # 8. 默认：询问
        return self._decide(YOLODecision.ASK_USER, command, "默认需要确认")

    def _build_context(self, command: str) -> YOLOContext:
        """从命令构建上下文"""
        normalized = os.path.normpath(self.workdir)

        return YOLOContext(
            command=command,
            workdir=self.workdir,
            in_workspace=any(normalized.startswith(os.path.normpath(p)) for p in self.SAFE_PATHS),
            is_git_operation=bool(re.match(r"^git\s+", command)),
            is_file_write=bool(re.search(r"\b(write|create|touch|new-item)\b", command, re.IGNORECASE)),
            is_network_call=bool(re.search(r"\b(curl|wget|fetch|http|https|socket)\b", command, re.IGNORECASE)),
            is_system_modification=bool(
                re.search(
                    r"\b(install|uninstall|remove|delete|modify|update|upgrade|register|unregister)\b",
                    command,
                    re.IGNORECASE,
                )
            ),
        )

    def _matches_any(self, command: str, patterns: list[str]) -> bool:
        return any(re.search(p, command, re.IGNORECASE) for p in patterns)

    def _decide(self, decision: YOLODecision, command: str, reason: str) -> YOLODecision:
        self.decision_log.append(
            {
                "command": command[:200],
                "decision": decision.value,
                "reason": reason,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )
        return decision

    def get_decision_stats(self) -> dict:
        """获取决策统计"""
        by_decision = {}
        for entry in self.decision_log:
            d = entry["decision"]
            by_decision[d] = by_decision.get(d, 0) + 1

        return {
            "total_decisions": len(self.decision_log),
            "by_decision": by_decision,
            "recent": self.decision_log[-10:] if self.decision_log else [],
        }
