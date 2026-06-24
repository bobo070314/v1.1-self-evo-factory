"""危险提示标注器 — 标注"改了就炸缓存"的地方

对标 Claude Code 的 DANGEROUS_UNCACHED_PROMPT：
- 标注哪些系统提示词/工具定义/配置如果改了会破坏缓存
- 提供保护机制：改之前先检查
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class DangerousArea:
    """危险区域标注"""

    id: str
    name: str  # 名称
    description: str  # 为什么危险
    location: str  # 位置（文件名/函数名）
    impact: str  # 改动后果
    last_modified: Optional[str] = None
    protected: bool = True  # 是否保护


class DangerousPromptTracker:
    """危险提示标注器

    维护一份"改了就炸"的清单，对标 Claude Code 的
    DANGEROUS_UNCACHED_PROMPT 函数。
    """

    # 预置的危险区域
    DANGEROUS_AREAS = [
        DangerousArea(
            id="D001",
            name="系统提示词头",
            description="系统提示词的前512个字符。改动这里会导致所有会话的缓存全部失效。",
            location="openclaw.json → system.prompt",
            impact="所有活跃会话缓存失效 → 瞬时成本飙升5-10x",
        ),
        DangerousArea(
            id="D002",
            name="工具定义签名",
            description="工具的 name/description/parameters schema。改动任何一个都会使缓存失效。",
            location="skills/*/SKILL.md frontmatter",
            impact="所有使用该技能的会话缓存失效",
        ),
        DangerousArea(
            id="D003",
            name="温度参数",
            description="模型温度参数。缓存基于完全相同的参数组合。",
            location="openclaw.json → model.temperature",
            impact="所有会话缓存失效（温度是缓存key的一部分）",
        ),
        DangerousArea(
            id="D004",
            name="模型选择",
            description="切换模型会导致所有缓存失效（不同模型的缓存不共享）。",
            location="openclaw.json → model.default",
            impact="全部缓存失效 → 历史对话全部重新计算",
        ),
        DangerousArea(
            id="D005",
            name="stop_sequences",
            description="停止序列。缓存key的一部分，改动失效。",
            location="openclaw.json → model.stopSequences",
            impact="所有会话缓存失效",
        ),
        DangerousArea(
            id="D006",
            name="max_tokens",
            description="最大输出 token。缓存key的一部分。",
            location="openclaw.json → model.maxTokens",
            impact="所有会话缓存失效",
        ),
        DangerousArea(
            id="D007",
            name="SKILL.md 编译输出",
            description="SKILL.md 编译后的 XML 注入系统提示词。任何技能注册/注销都会改变这个。",
            location="skills/*/SKILL.md (被OpenClaw编译)",
            impact="新增/移除技能 → 系统提示词变化 → 缓存全灭",
        ),
        DangerousArea(
            id="D008",
            name="MEMORY.md 注入",
            description="MEMORY.md 在会话启动时注入。高频编辑会导致每次启动的缓存miss。",
            location="workspace/MEMORY.md",
            impact="新会话首次调用缓存miss（可接受，但频繁编辑会累积成本）",
        ),
    ]

    def __init__(self):
        self.areas = {a.id: a for a in self.DANGEROUS_AREAS}

    def check_before_edit(self, location: str) -> list[DangerousArea]:
        """在编辑某个位置前检查
        返回可能受影响的危险区域列表
        """
        affected = []
        loc_lower = location.lower()

        for area in self.areas.values():
            area_loc_lower = area.location.lower()
            # 模糊匹配
            if any(part in area_loc_lower or part in loc_lower for part in area_loc_lower.split(" → ")):
                affected.append(area)

        return affected

    def get_all_dangerous(self) -> list[DangerousArea]:
        return list(self.areas.values())

    def get_by_id(self, area_id: str) -> Optional[DangerousArea]:
        return self.areas.get(area_id)

    def add_area(self, area: DangerousArea):
        self.areas[area.id] = area

    def format_warning(self, affected: list[DangerousArea]) -> str:
        """格式化警告信息"""
        if not affected:
            return ""

        lines = ["⚠️ 危险操作！以下缓存区域会受影响："]
        for area in affected:
            lines.append(f"  • {area.name} ({area.id})")
            lines.append(f"    位置: {area.location}")
            lines.append(f"    后果: {area.impact}")
            lines.append("")

        lines.append("💡 建议：")
        lines.append("  1. 确认这是必要的改动")
        lines.append("  2. 选择低峰期操作")
        lines.append("  3. 改动后观察成本变化")
        lines.append("  4. 如果只是测试，考虑用 dry-run / shadow 模式")

        return "\n".join(lines)
