"""缓存管理器 — 追踪14种缓存失败原因

对标 Claude Code：
- 14种缓存失败原因全记录
- 每种失败有原因/影响/修复建议
- 缓存命中率统计

缓存失败的14种原因：
1. TOKEN_LIMIT — 超 token 上限
2. PROMPT_TOO_LONG — 提示词过长
3. TOOL_RESULT_LARGE — 工具返回过大
4. MESSAGE_COUNT — 消息数超限
5. IMAGE_INCLUDED — 含图片（不可缓存）
6. SYSTEM_PROMPT_CHANGED — 系统提示词变了
7. TOOL_DEFINITION_CHANGED — 工具定义变了
8. TEMPERATURE_CHANGED — 温度参数变了
9. MODEL_SWITCHED — 模型切换
10. STREAMING_ENABLED — 流式输出
11. FUNCTION_CALL — 函数调用干扰
12. STOP_SEQUENCE_HIT — 命中停止序列
13. CONTENT_FILTER — 内容审查触发
14. PROVIDER_ERROR — 提供商报错
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum


class CacheFailureReason(str, Enum):
    TOKEN_LIMIT = "token_limit"
    PROMPT_TOO_LONG = "prompt_too_long"
    TOOL_RESULT_LARGE = "tool_result_large"
    MESSAGE_COUNT = "message_count"
    IMAGE_INCLUDED = "image_included"
    SYSTEM_PROMPT_CHANGED = "system_prompt_changed"
    TOOL_DEFINITION_CHANGED = "tool_definition_changed"
    TEMPERATURE_CHANGED = "temperature_changed"
    MODEL_SWITCHED = "model_switched"
    STREAMING_ENABLED = "streaming_enabled"
    FUNCTION_CALL = "function_call"
    STOP_SEQUENCE_HIT = "stop_sequence_hit"
    CONTENT_FILTER = "content_filter"
    PROVIDER_ERROR = "provider_error"


# 每种失败原因的可修复性
FIXABLE = {
    CacheFailureReason.TOKEN_LIMIT: True,
    CacheFailureReason.PROMPT_TOO_LONG: True,
    CacheFailureReason.TOOL_RESULT_LARGE: True,
    CacheFailureReason.MESSAGE_COUNT: True,
    CacheFailureReason.IMAGE_INCLUDED: False,  # 图片天然不可缓存
    CacheFailureReason.SYSTEM_PROMPT_CHANGED: False,  # 故意的
    CacheFailureReason.TOOL_DEFINITION_CHANGED: False,
    CacheFailureReason.TEMPERATURE_CHANGED: True,
    CacheFailureReason.MODEL_SWITCHED: False,
    CacheFailureReason.STREAMING_ENABLED: True,
    CacheFailureReason.FUNCTION_CALL: False,
    CacheFailureReason.STOP_SEQUENCE_HIT: False,
    CacheFailureReason.CONTENT_FILTER: False,
    CacheFailureReason.PROVIDER_ERROR: False,
}

# 修复建议
FIX_SUGGESTIONS = {
    CacheFailureReason.TOKEN_LIMIT: "缩短上下文或减少工具返回内容",
    CacheFailureReason.PROMPT_TOO_LONG: "精简系统提示词，控制 < 2000 tokens",
    CacheFailureReason.TOOL_RESULT_LARGE: "用 token-saver 压缩工具输出",
    CacheFailureReason.MESSAGE_COUNT: "定期触发对话压缩（>50轮时）",
    CacheFailureReason.TEMPERATURE_CHANGED: "保持温度参数一致",
    CacheFailureReason.STREAMING_ENABLED: "批量请求时禁用流式",
}


@dataclass
class CacheEvent:
    """单次缓存事件"""

    timestamp: str
    reason: CacheFailureReason
    hit: bool  # True=命中, False=未命中
    tokens_saved: int = 0  # 节省的 token 数
    tokens_wasted: int = 0  # 浪费的 token 数
    context_size: int = 0  # 当时上下文大小
    fixable: bool = False
    suggestion: str = ""


class CacheManager:
    """缓存管理器

    追踪每次 API 调用的缓存命中/未命中情况，
    分析失败原因，给出优化建议。
    """

    def __init__(self):
        self.events: list[CacheEvent] = []
        self.total_calls: int = 0
        self.total_hits: int = 0
        self.total_tokens_saved: int = 0
        self.total_tokens_wasted: int = 0

    def record_hit(self, tokens_saved: int, context_size: int = 0):
        """记录缓存命中"""
        self.total_calls += 1
        self.total_hits += 1
        self.total_tokens_saved += tokens_saved

        self.events.append(
            CacheEvent(
                timestamp=datetime.now(timezone.utc).isoformat(),
                reason=None,
                hit=True,
                tokens_saved=tokens_saved,
                context_size=context_size,
            )
        )

    def record_miss(
        self,
        reason: CacheFailureReason,
        tokens_wasted: int,
        context_size: int = 0,
    ):
        """记录缓存未命中"""
        self.total_calls += 1
        self.total_tokens_wasted += tokens_wasted

        self.events.append(
            CacheEvent(
                timestamp=datetime.now(timezone.utc).isoformat(),
                reason=reason,
                hit=False,
                tokens_wasted=tokens_wasted,
                context_size=context_size,
                fixable=FIXABLE.get(reason, False),
                suggestion=FIX_SUGGESTIONS.get(reason, ""),
            )
        )

    def hit_rate(self) -> float:
        """缓存命中率"""
        if self.total_calls == 0:
            return 0.0
        return self.total_hits / self.total_calls

    def savings_report(self) -> dict:
        """省钱报告"""
        # 假设 $2/1M tokens (DeepSeek 价格)
        COST_PER_1M = 2.0
        saved_cost = (self.total_tokens_saved / 1_000_000) * COST_PER_1M
        wasted_cost = (self.total_tokens_wasted / 1_000_000) * COST_PER_1M

        # 按原因分组
        by_reason = {}
        for e in self.events:
            if not e.hit and e.reason:
                reason_key = e.reason.value
                if reason_key not in by_reason:
                    by_reason[reason_key] = {"count": 0, "tokens_wasted": 0, "fixable": e.fixable}
                by_reason[reason_key]["count"] += 1
                by_reason[reason_key]["tokens_wasted"] += e.tokens_wasted

        return {
            "total_calls": self.total_calls,
            "total_hits": self.total_hits,
            "hit_rate": f"{self.hit_rate():.1%}",
            "tokens_saved": self.total_tokens_saved,
            "tokens_wasted": self.total_tokens_wasted,
            "estimated_saved_cost": f"${saved_cost:.4f}",
            "estimated_wasted_cost": f"${wasted_cost:.4f}",
            "failures_by_reason": by_reason,
            "top_fixable": sorted(
                [(k, v) for k, v in by_reason.items() if v["fixable"]],
                key=lambda x: x[1]["tokens_wasted"],
                reverse=True,
            )[:5],
        }

    def get_fix_suggestions(self) -> list[str]:
        """获取可操作的优化建议"""
        suggestions = []
        report = self.savings_report()

        for reason, data in report.get("failures_by_reason", {}).items():
            if data["fixable"] and data["count"] >= 3:
                try:
                    enum_reason = CacheFailureReason(reason)
                    fix = FIX_SUGGESTIONS.get(enum_reason, "")
                    if fix:
                        suggestions.append(
                            f"[{reason}] 发生 {data['count']} 次，浪费 ~{data['tokens_wasted']} tokens → {fix}"
                        )
                except ValueError:
                    pass

        if self.hit_rate() < 0.3 and self.total_calls >= 10:
            suggestions.append(
                f"⚠️ 缓存命中率仅 {self.hit_rate():.0%}，建议检查："
                f"1) 温度参数是否一致 2) 系统提示词是否频繁变化 3) 是否开启了流式"
            )

        return suggestions

    def reset(self):
        """重置统计"""
        self.events = []
        self.total_calls = 0
        self.total_hits = 0
        self.total_tokens_saved = 0
        self.total_tokens_wasted = 0
