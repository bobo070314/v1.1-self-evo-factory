"""API 成本追踪器 — 记录每一次 API 调用的花费

对标 Claude Code：
- 按模型/按天/按任务分组统计
- 自动检测无效 API 调用
- 成本预算告警
"""

from dataclasses import dataclass
from datetime import datetime, timezone

# 各模型价格（美元/1M tokens，2026年参考价）
MODEL_PRICING = {
    "deepseek/deepseek-v4-pro": {"input": 0.14, "output": 0.28},
    "deepseek/deepseek-chat": {"input": 0.14, "output": 0.28},
    "deepseek/deepseek-reasoner": {"input": 0.55, "output": 2.19},
    "openai/gpt-4o": {"input": 2.50, "output": 10.00},
    "openai/gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "anthropic/claude-sonnet-4-20250514": {"input": 3.00, "output": 15.00},
    "anthropic/claude-opus-4-20250514": {"input": 15.00, "output": 75.00},
    "google/gemini-2.5-flash": {"input": 0.15, "output": 0.60},
}


@dataclass
class APICallRecord:
    """单次 API 调用记录"""

    timestamp: str
    model: str
    input_tokens: int
    output_tokens: int
    cached_tokens: int = 0  # 缓存命中的输入 tokens
    cost_usd: float = 0.0
    task_id: str = ""  # 关联任务ID
    success: bool = True
    error: str = ""
    duration_ms: int = 0


class APICostTracker:
    """API 成本追踪器

    记录每次调用，按维度统计：
    - 按模型
    - 按天
    - 按任务
    - 缓存节省
    """

    def __init__(self, budget_limit_usd: float = 5.0):
        self.records: list[APICallRecord] = []
        self.budget_limit = budget_limit_usd

    def record(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
        cached_tokens: int = 0,
        task_id: str = "",
        success: bool = True,
        error: str = "",
        duration_ms: int = 0,
    ) -> APICallRecord:
        """记录一次 API 调用"""
        pricing = MODEL_PRICING.get(model, {"input": 0.14, "output": 0.28})

        # 输入 token 中缓存的部分不计费
        billable_input = max(0, input_tokens - cached_tokens)
        # 缓存费用（通常为原价的 50%）
        cache_cost = (cached_tokens / 1_000_000) * pricing["input"] * 0.5

        cost = (
            (billable_input / 1_000_000) * pricing["input"]
            + (output_tokens / 1_000_000) * pricing["output"]
            + cache_cost
        )

        record = APICallRecord(
            timestamp=datetime.now(timezone.utc).isoformat(),
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cached_tokens=cached_tokens,
            cost_usd=round(cost, 6),
            task_id=task_id,
            success=success,
            error=error,
            duration_ms=duration_ms,
        )

        self.records.append(record)
        return record

    def total_cost(self) -> float:
        """总花费"""
        return round(sum(r.cost_usd for r in self.records), 6)

    def cost_by_model(self) -> dict:
        """按模型统计"""
        by_model = {}
        for r in self.records:
            if r.model not in by_model:
                by_model[r.model] = {"calls": 0, "cost_usd": 0, "input_tokens": 0, "output_tokens": 0}
            by_model[r.model]["calls"] += 1
            by_model[r.model]["cost_usd"] = round(by_model[r.model]["cost_usd"] + r.cost_usd, 6)
            by_model[r.model]["input_tokens"] += r.input_tokens
            by_model[r.model]["output_tokens"] += r.output_tokens
        return by_model

    def cost_by_day(self) -> dict:
        """按天统计"""
        by_day = {}
        for r in self.records:
            day = r.timestamp[:10]
            if day not in by_day:
                by_day[day] = {"calls": 0, "cost_usd": 0, "input_tokens": 0, "output_tokens": 0}
            by_day[day]["calls"] += 1
            by_day[day]["cost_usd"] = round(by_day[day]["cost_usd"] + r.cost_usd, 6)
            by_day[day]["input_tokens"] += r.input_tokens
            by_day[day]["output_tokens"] += r.output_tokens
        return by_day

    def cost_by_task(self) -> dict:
        """按任务统计"""
        by_task = {}
        for r in self.records:
            tid = r.task_id or "uncategorized"
            if tid not in by_task:
                by_task[tid] = {"calls": 0, "cost_usd": 0}
            by_task[tid]["calls"] += 1
            by_task[tid]["cost_usd"] = round(by_task[tid]["cost_usd"] + r.cost_usd, 6)
        return by_task

    def budget_status(self) -> dict:
        """预算状态"""
        total = self.total_cost()
        remaining = round(self.budget_limit - total, 6)
        percent = (total / self.budget_limit * 100) if self.budget_limit > 0 else 0

        status = "ok"
        if percent >= 90:
            status = "critical"
        elif percent >= 70:
            status = "warning"

        return {
            "budget_limit_usd": self.budget_limit,
            "spent_usd": total,
            "remaining_usd": remaining,
            "percent_used": f"{percent:.1f}%",
            "status": status,
        }

    def detect_waste(self) -> list[dict]:
        """检测浪费的调用（无效/重复/错误）"""
        waste = []

        # 失败的调用
        failed = [r for r in self.records if not r.success]
        if failed:
            total_wasted = sum(r.cost_usd for r in failed)
            waste.append(
                {
                    "type": "failed_calls",
                    "count": len(failed),
                    "wasted_usd": round(total_wasted, 6),
                    "suggestion": "重试逻辑可能有问题，检查错误原因",
                    "sample_errors": [r.error[:100] for r in failed[:3] if r.error],
                }
            )

        # 0 output token 的调用（可能是格式错误）
        zero_output = [r for r in self.records if r.success and r.output_tokens == 0]
        if len(zero_output) > 3:
            total_wasted = sum(r.cost_usd for r in zero_output)
            waste.append(
                {
                    "type": "zero_output",
                    "count": len(zero_output),
                    "wasted_usd": round(total_wasted, 6),
                    "suggestion": f"{len(zero_output)}次调用产出0 token，可能prompt有问题",
                }
            )

        # 重复任务ID的高频调用
        task_counts = {}
        for r in self.records:
            if r.task_id:
                task_counts[r.task_id] = task_counts.get(r.task_id, 0) + 1

        heavy_tasks = {k: v for k, v in task_counts.items() if v >= 10}
        if heavy_tasks:
            waste.append(
                {
                    "type": "high_frequency",
                    "tasks": heavy_tasks,
                    "suggestion": "某些任务调用过于频繁，检查是否有循环调用或缓存失效",
                }
            )

        return waste

    def summary(self) -> dict:
        """完整摘要"""
        return {
            "total_calls": len(self.records),
            "total_cost_usd": self.total_cost(),
            "by_model": self.cost_by_model(),
            "by_day": self.cost_by_day(),
            "budget": self.budget_status(),
            "waste_detection": self.detect_waste(),
            "cached_tokens_saved": sum(r.cached_tokens for r in self.records),
            "avg_duration_ms": round(sum(r.duration_ms for r in self.records) / max(len(self.records), 1)),
        }

    def reset(self):
        self.records = []
