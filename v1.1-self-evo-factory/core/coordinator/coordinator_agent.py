"""Coordinator Agent — AI 项目经理

对标 Claude Code 的 Coordinator：
- 接收自然语言命令
- 拆分任务 → 分配给 Agent
- 验收每个 Agent 的产出
- 拒绝橡皮图章："完成了"不算完，要证据
"""

import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional


class TaskStatus(str, Enum):
    PENDING = "pending"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    SUBMITTED = "submitted"  # Agent说做完了
    VERIFIED = "verified"  # Coordinator验收通过
    REJECTED = "rejected"  # Coordinator打回
    FAILED = "failed"


class VerificationLevel(str, Enum):
    """验收严格程度"""

    STRICT = "strict"  # 必须有可验证的输出（文件/测试/日志）
    NORMAL = "normal"  # 有合理证据即可
    TRUST_BUT_VERIFY = "trust_but_verify"  # 允许一次快速通过，第二次严查
    RUBBER_STAMP = "rubber_stamp"  # ❌ 永远不用！这是反面教材


@dataclass
class Task:
    """单个任务"""

    id: str
    description: str
    assigned_to: str = ""  # Agent名称
    status: TaskStatus = TaskStatus.PENDING
    acceptance_criteria: list[str] = field(default_factory=list)  # 验收标准
    evidence: list[str] = field(default_factory=list)  # 产出证据（文件路径、测试结果等）
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    completed_at: Optional[str] = None
    rejection_reason: str = ""
    retry_count: int = 0
    max_retries: int = 3
    parent_task_id: Optional[str] = None  # 依赖任务
    dependencies: list[str] = field(default_factory=list)

    def is_blocked(self) -> bool:
        return bool(self.dependencies)

    def can_retry(self) -> bool:
        return self.retry_count < self.max_retries


@dataclass
class Mission:
    """一次完整的任务 = 多个 Task 组成"""

    id: str
    goal: str  # 自然语言目标
    tasks: list[Task] = field(default_factory=list)
    status: TaskStatus = TaskStatus.PENDING
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    completed_at: Optional[str] = None
    log: list[str] = field(default_factory=list)  # 执行日志


class CoordinatorAgent:
    """AI 项目经理

    核心原则：
    1. 不接受橡皮图章 — 每个任务必须有可验证的证据
    2. 自然语言命令 → 任务拆解 → 分配 → 验收
    3. 失败自动重试（最多3次），重试前反馈修正方向
    """

    def __init__(self, verify_level: VerificationLevel = VerificationLevel.NORMAL):
        self.verify_level = verify_level
        self.missions: dict[str, Mission] = {}
        self.active_tasks: dict[str, Task] = {}

    # ---------- 任务拆解 ----------
    def plan_mission(self, goal: str, mission_id: Optional[str] = None) -> Mission:
        """自然语言目标 → 任务拆解
        返回 Mission 对象，包含拆解后的 Task 列表
        """
        if mission_id is None:
            mission_id = f"mission_{int(time.time())}"

        mission = Mission(id=mission_id, goal=goal)

        # 任务拆解（规则引擎 + 模板）
        tasks = self._decompose(goal)
        for i, task_desc in enumerate(tasks):
            task = Task(
                id=f"{mission_id}_t{i + 1}",
                description=task_desc,
                acceptance_criteria=self._generate_criteria(task_desc),
            )
            mission.tasks.append(task)
            self.active_tasks[task.id] = task

        mission.status = TaskStatus.IN_PROGRESS
        mission.log.append(f"[PLAN] 目标拆解为 {len(tasks)} 个子任务")
        self.missions[mission_id] = mission

        return mission

    def _decompose(self, goal: str) -> list[str]:
        """基于关键词的任务拆解（第一阶段：规则引擎，第二阶段：LLM）"""
        tasks = []

        has_security = any(kw in goal for kw in ["审计", "安全", "audit", "security", "漏洞", "扫描"])
        has_deploy = any(kw in goal for kw in ["部署", "build", "deploy", "发布", "上线"])
        has_code = any(kw in goal for kw in ["写", "代码", "实现", "开发", "create", "implement"])
        has_fix = any(kw in goal for kw in ["修复", "bug", "fix", "修", "改"])

        # 复合任务：部署+安全 → 先审计后部署
        if has_security and has_deploy:
            tasks.append("扫描目标代码库（部署前安全审计）")
            tasks.append("识别安全漏洞（SQL注入/XSS/命令注入/路径穿越/密钥泄漏）")
            tasks.append("生成审计报告并判断是否放行")
            tasks.append("检查构建环境（依赖/版本）")
            tasks.append("执行构建命令并记录输出")
            tasks.append("验证构建产物完整性")
            tasks.append("部署到目标环境")
            tasks.append("健康检查（至少3项指标）")

        # 安全审计
        elif has_security:
            tasks.append("扫描目标代码库")
            tasks.append("识别安全漏洞（SQL注入/XSS/命令注入/路径穿越/密钥泄漏）")
            tasks.append("生成审计报告")

        # 代码相关
        elif has_code:
            tasks.append("分析需求并输出接口设计")
            tasks.append("编写核心代码实现")
            tasks.append("编写测试用例（至少3个）")
            tasks.append("运行测试并确认全部通过")

        # 文件操作
        elif any(kw in goal for kw in ["文件", "读", "查", "搜", "grep", "find", "search"]):
            tasks.append("定位目标文件/目录")
            tasks.append("检索相关内容并汇总")
            tasks.append("输出结构化结果")

        # 部署/Build
        elif any(kw in goal for kw in ["部署", "build", "deploy", "发布", "上线"]):
            tasks.append("检查构建环境（依赖/版本）")
            tasks.append("执行构建命令并记录输出")
            tasks.append("验证构建产物完整性")
            tasks.append("部署到目标环境")
            tasks.append("健康检查（至少3项指标）")

        # 修复/Bug
        elif any(kw in goal for kw in ["修复", "bug", "fix", "修", "改"]):
            tasks.append("定位问题根因")
            tasks.append("提出修复方案")
            tasks.append("实施修复")
            tasks.append("验证修复（回归测试）")

        # 通用
        else:
            tasks.append(f"分析目标: {goal}")
            tasks.append("制定执行计划")
            tasks.append("分步执行")
            tasks.append("验证结果")

        return tasks

    def _generate_criteria(self, task_desc: str) -> list[str]:
        """自动生成验收标准"""
        criteria = []

        if any(kw in task_desc for kw in ["代码", "实现", "开发", "写"]):
            criteria.append("代码文件存在且语法正确")
            criteria.append("测试用例全部通过")
            criteria.append("无明显安全漏洞（SQL注入/XSS/命令注入）")

        elif any(kw in task_desc for kw in ["测试", "test"]):
            criteria.append("测试命令执行成功（exit code = 0）")
            criteria.append("至少3个测试用例")
            criteria.append("覆盖正常路径 + 边界条件")

        elif any(kw in task_desc for kw in ["部署", "deploy", "build"]):
            criteria.append("构建命令 exit code = 0")
            criteria.append("产物文件存在且非空")
            criteria.append("健康检查端点返回 200")

        elif any(kw in task_desc for kw in ["审计", "安全", "扫描", "audit", "security", "漏洞"]):
            criteria.append("扫描覆盖所有目标文件")
            criteria.append("漏洞按严重性分级（CRITICAL/HIGH/MEDIUM/LOW）")
            criteria.append("每个漏洞有修复建议")

        elif any(kw in task_desc for kw in ["修复", "fix", "bug"]):
            criteria.append("原问题复现步骤不再触发")
            criteria.append("回归测试通过")
            criteria.append("无新增 linter 警告")

        else:
            criteria.append("输出结果可验证（退出码/文件/日志）")
            criteria.append("无异常错误信息")

        return criteria

    # ---------- 验收 ----------
    def verify_task(self, task: Task, evidence: list[str]) -> tuple[bool, str]:
        """验收一个任务的产出
        返回：(通过?, 原因)

        拒绝橡皮图章检查：
        - evidence 为空 → 拒绝
        - evidence 只有 "done" "完成" "ok" → 拒绝
        - 测试类任务没有 exit code → 拒绝
        """
        # 橡皮图章检测
        rubber_stamps = {"done", "完成", "ok", "好了", "做完了", "pass", "success", "yes", "true"}
        clean_evidence = [e.lower().strip() for e in evidence]
        if len(clean_evidence) == 1 and clean_evidence[0] in rubber_stamps:
            return False, "❌ 橡皮图章拒绝！需要可验证的证据（文件路径/测试输出/命令结果），不是一句'做完了'"

        # 证据为空
        if not evidence:
            return False, "❌ 无任何证据！至少需要1条可验证的产出（文件路径/测试输出/日志）"

        # 按验收标准逐条检查
        for criterion in task.acceptance_criteria:
            if not self._check_criterion(criterion, evidence):
                return False, f"❌ 未通过验收标准: {criterion}"

        return True, "✅ 验收通过"

    def _check_criterion(self, criterion: str, evidence: list[str]) -> bool:
        """检查单条验收标准"""
        combined = " ".join(evidence).lower()

        if "exit code" in criterion.lower() or "退出码" in criterion:
            return any("exit code" in e.lower() or "退出码" in e for e in evidence)

        if "文件存在" in criterion or "file" in criterion.lower():
            return any(".py" in e or ".js" in e or ".ts" in e or ".json" in e for e in evidence)

        if "健康检查" in criterion or "health" in criterion.lower() or "200" in criterion:
            return any("200" in e or "ok" in e.lower() or "healthy" in e.lower() for e in evidence)

        if "测试" in criterion or "test" in criterion.lower():
            return any("pass" in e.lower() or "通过" in e for e in evidence)

        # 默认：有证据就过
        return len(evidence) > 0

    # ---------- 任务流程 ----------
    def submit_task(self, task_id: str, evidence: list[str]) -> dict:
        """Agent 提交任务，Coordinator 验收"""
        task = self.active_tasks.get(task_id)
        if not task:
            return {"ok": False, "error": f"任务 {task_id} 不存在"}

        task.evidence = evidence
        task.status = TaskStatus.SUBMITTED

        passed, reason = self.verify_task(task, evidence)

        if passed:
            task.status = TaskStatus.VERIFIED
            task.completed_at = datetime.now(timezone.utc).isoformat()
        else:
            task.rejection_reason = reason
            if task.can_retry():
                task.status = TaskStatus.REJECTED
                task.retry_count += 1
                reason += f"\n📎 请修正后重新提交（剩余重试次数: {task.max_retries - task.retry_count}）"
            else:
                task.status = TaskStatus.FAILED
                reason += f"\n💀 已达最大重试次数（{task.max_retries}），任务失败"

        return {
            "ok": passed,
            "task_id": task_id,
            "status": task.status.value,
            "reason": reason,
            "retry_count": task.retry_count,
        }

    def get_mission_report(self, mission_id: str) -> dict:
        """生成任务报告"""
        mission = self.missions.get(mission_id)
        if not mission:
            return {"error": f"任务 {mission_id} 不存在"}

        task_statuses = {}
        for task in mission.tasks:
            task_statuses[task.id] = {
                "description": task.description,
                "status": task.status.value,
                "assigned_to": task.assigned_to,
                "retry_count": task.retry_count,
                "rejection_reason": task.rejection_reason,
            }

        verified = sum(1 for t in mission.tasks if t.status == TaskStatus.VERIFIED)
        failed = sum(1 for t in mission.tasks if t.status == TaskStatus.FAILED)
        pending = sum(1 for t in mission.tasks if t.status in (TaskStatus.PENDING, TaskStatus.IN_PROGRESS))

        return {
            "mission_id": mission_id,
            "goal": mission.goal,
            "total_tasks": len(mission.tasks),
            "verified": verified,
            "failed": failed,
            "pending": pending,
            "progress": f"{verified}/{len(mission.tasks)}",
            "tasks": task_statuses,
            "log": mission.log,
        }
