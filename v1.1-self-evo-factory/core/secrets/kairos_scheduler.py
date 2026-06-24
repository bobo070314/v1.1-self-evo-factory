"""Kairos 7x24h 定时任务调度器

对标 Claude Code 的 Kairos：
- AI 自己跑，不等人叫
- 监听 GitHub / 跑数据 / 发通知
- 定时 + 事件触发双模式

触发类型：
- cron: 定时触发（如每天9:00跑日报）
- webhook: GitHub webhook 触发
- file_watch: 文件变化触发
- interval: 固定间隔
"""

import json
import os
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Callable, Optional


class TriggerType(str, Enum):
    CRON = "cron"
    WEBHOOK = "webhook"
    FILE_WATCH = "file_watch"
    INTERVAL = "interval"
    MANUAL = "manual"


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class KairosTrigger:
    """触发器定义"""

    type: TriggerType
    config: dict  # cron表达式 / webhook URL / 文件路径 / 间隔秒数


@dataclass
class KairosTask:
    """Kairos 任务"""

    id: str
    name: str
    description: str
    trigger: KairosTrigger
    action: str  # 要执行的动作（自然语言或命令）
    enabled: bool = True
    last_run: Optional[str] = None
    last_status: TaskStatus = TaskStatus.PENDING
    run_count: int = 0
    fail_count: int = 0
    max_failures: int = 3  # 连续失败上限（超过自动禁用）
    timeout_seconds: int = 300
    on_failure_action: str = "alert"  # alert / retry / skip / disable


class KairosScheduler:
    """Kairos 7x24h 调度器

    预置任务：
    1. 每日日报（9:00）
    2. GitHub 仓库监听
    3. 记忆库维护
    4. 技能健康检查
    """

    # 预置任务模板
    PRESET_TASKS = [
        KairosTask(
            id="daily_report",
            name="每日日报",
            description="每天早上9点生成技能健康度和API测试报告",
            trigger=KairosTrigger(type=TriggerType.CRON, config={"cron": "0 9 * * *", "tz": "Asia/Shanghai"}),
            action="运行 eval-suite/run_all.py 并生成报告",
        ),
        KairosTask(
            id="github_watchdog",
            name="GitHub仓库监听",
            description="每小时检查 GitHub 仓库有无新 issue/PR/star",
            trigger=KairosTrigger(type=TriggerType.INTERVAL, config={"interval_seconds": 3600}),
            action="调用 gh CLI 检查仓库动态",
        ),
        KairosTask(
            id="memory_maintenance",
            name="记忆库维护",
            description="每天凌晨2点清理过期记忆、重建索引",
            trigger=KairosTrigger(type=TriggerType.CRON, config={"cron": "0 2 * * *", "tz": "Asia/Shanghai"}),
            action="清理过期记忆 + 重建 TF-IDF 索引 + 输出统计",
        ),
        KairosTask(
            id="skill_health_check",
            name="技能健康检查",
            description="每4小时检查所有技能的 --version --json 可用性",
            trigger=KairosTrigger(type=TriggerType.INTERVAL, config={"interval_seconds": 14400}),
            action="遍历所有技能 run.py --version --json 并统计通过率",
        ),
        KairosTask(
            id="cost_report",
            name="成本日报",
            description="每天18:00发送API成本报告",
            trigger=KairosTrigger(type=TriggerType.CRON, config={"cron": "0 18 * * *", "tz": "Asia/Shanghai"}),
            action="汇总当天API调用成本并生成报告",
        ),
        KairosTask(
            id="security_scan",
            name="定时安全扫描",
            description="每天凌晨3点全量安全扫描",
            trigger=KairosTrigger(type=TriggerType.CRON, config={"cron": "0 3 * * *", "tz": "Asia/Shanghai"}),
            action="运行 security-audit --target . --json",
        ),
        KairosTask(
            id="git_auto_commit",
            name="自动提交变更",
            description="每小时检查工作区是否有未提交变更并自动处理",
            trigger=KairosTrigger(type=TriggerType.INTERVAL, config={"interval_seconds": 3600}),
            action="检查 git status，如果有变更自动 add+commit+push",
            enabled=False,  # 默认关闭，需手动开启
        ),
    ]

    def __init__(self, state_file: str = "states/kairos_state.json"):
        self.tasks: dict[str, KairosTask] = {}
        self.state_file = state_file
        self._running = False
        self._threads: dict[str, threading.Thread] = {}
        self._callbacks: dict[str, Callable] = {}

        # 加载预置任务
        for task in self.PRESET_TASKS:
            self.tasks[task.id] = task

        self._load_state()

    def _load_state(self):
        """加载持久化状态"""
        try:
            with open(self.state_file, "r", encoding="utf-8") as f:
                state = json.load(f)

            for task_id, task_state in state.get("tasks", {}).items():
                if task_id in self.tasks:
                    self.tasks[task_id].last_run = task_state.get("last_run")
                    self.tasks[task_id].last_status = TaskStatus(task_state.get("last_status", "pending"))
                    self.tasks[task_id].run_count = task_state.get("run_count", 0)
                    self.tasks[task_id].fail_count = task_state.get("fail_count", 0)
                    self.tasks[task_id].enabled = task_state.get("enabled", True)
        except (FileNotFoundError, json.JSONDecodeError):
            pass

    def _save_state(self):
        """持久化状态"""
        os.makedirs(os.path.dirname(self.state_file), exist_ok=True)
        state = {
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "tasks": {
                tid: {
                    "last_run": t.last_run,
                    "last_status": t.last_status.value,
                    "run_count": t.run_count,
                    "fail_count": t.fail_count,
                    "enabled": t.enabled,
                }
                for tid, t in self.tasks.items()
            },
        }
        with open(self.state_file, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2, ensure_ascii=False)

    def register_callback(self, task_id: str, callback: Callable):
        """注册任务回调函数"""
        self._callbacks[task_id] = callback

    def execute_task(self, task_id: str) -> dict:
        """手动触发一个任务"""
        task = self.tasks.get(task_id)
        if not task:
            return {"ok": False, "error": f"任务 {task_id} 不存在"}
        if not task.enabled:
            return {"ok": False, "error": f"任务 {task_id} 已禁用"}

        return self._run_task(task)

    def _run_task(self, task: KairosTask) -> dict:
        """执行单个任务"""
        task.last_status = TaskStatus.RUNNING
        task.last_run = datetime.now(timezone.utc).isoformat()

        try:
            # 如果有注册回调，调用回调
            callback = self._callbacks.get(task.id)
            if callback:
                success = callback(task)
            else:
                # 模拟执行（生产环境接入真实exec）
                success = True

            if success:
                task.last_status = TaskStatus.COMPLETED
                task.run_count += 1
                task.fail_count = 0  # 重置连续失败计数
                result = {"ok": True, "task_id": task.id, "status": "completed"}
            else:
                task.last_status = TaskStatus.FAILED
                task.fail_count += 1
                result = {"ok": False, "task_id": task.id, "status": "failed"}

                # 连续失败超限 → 自动禁用
                if task.fail_count >= task.max_failures:
                    task.enabled = False
                    result["note"] = f"连续失败 {task.fail_count} 次，已自动禁用"

        except Exception as e:
            task.last_status = TaskStatus.FAILED
            task.fail_count += 1
            result = {"ok": False, "task_id": task.id, "status": "failed", "error": str(e)}

        self._save_state()
        return result

    def run_all_due(self) -> list[dict]:
        """运行所有到期任务"""
        results = []
        now = datetime.now(timezone.utc)

        for task in self.tasks.values():
            if not task.enabled:
                continue

            # 简单判断：interval类型检查上次运行时间
            if task.trigger.type == TriggerType.INTERVAL:
                interval = task.trigger.config.get("interval_seconds", 3600)
                if task.last_run:
                    last = datetime.fromisoformat(task.last_run)
                    if (now - last).total_seconds() < interval:
                        continue

            results.append(self._run_task(task))

        return results

    def get_task(self, task_id: str) -> Optional[KairosTask]:
        return self.tasks.get(task_id)

    def list_tasks(self) -> list[dict]:
        """列出所有任务"""
        return [
            {
                "id": t.id,
                "name": t.name,
                "trigger": t.trigger.type.value,
                "enabled": t.enabled,
                "last_run": t.last_run,
                "last_status": t.last_status.value,
                "run_count": t.run_count,
                "fail_count": t.fail_count,
            }
            for t in self.tasks.values()
        ]

    def enable_task(self, task_id: str) -> bool:
        if task_id in self.tasks:
            self.tasks[task_id].enabled = True
            self.tasks[task_id].fail_count = 0
            self._save_state()
            return True
        return False

    def disable_task(self, task_id: str) -> bool:
        if task_id in self.tasks:
            self.tasks[task_id].enabled = False
            self._save_state()
            return True
        return False

    def stats(self) -> dict:
        """调度器统计"""
        total = len(self.tasks)
        enabled = sum(1 for t in self.tasks.values() if t.enabled)
        running = sum(1 for t in self.tasks.values() if t.last_status == TaskStatus.RUNNING)
        failed = sum(1 for t in self.tasks.values() if t.last_status == TaskStatus.FAILED)
        completed = sum(1 for t in self.tasks.values() if t.last_status == TaskStatus.COMPLETED)

        return {
            "total_tasks": total,
            "enabled": enabled,
            "disabled": total - enabled,
            "running": running,
            "completed": completed,
            "failed": failed,
            "by_trigger": {
                trigger.value: sum(1 for t in self.tasks.values() if t.trigger.type == trigger)
                for trigger in TriggerType
            },
        }
