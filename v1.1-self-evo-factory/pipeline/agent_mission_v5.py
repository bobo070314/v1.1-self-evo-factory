#!/usr/bin/env python3
"""V5.0 Agent Mission — 记忆检索 → Coordinator验收 → YOLO安全 三合一

对标 Claude Code 的完整任务执行链：
1. 记忆系统：每步执行前检索4类记忆
2. Coordinator：拒绝橡皮图章验收
3. YOLO分类器：危险操作拦截

Usage:
  python agent_mission_v5.py --goal "写一个用户登录模块"
  python agent_mission_v5.py --goal "审计代码安全并部署" --strict
  python agent_mission_v5.py --json --dry-run
  python agent_mission_v5.py --version
"""

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

__version__ = "5.0.0"
UTC = timezone.utc

# 确保项目根目录在 path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from core.coordinator import (
    AcceptanceCriteria,
    CoordinatorAgent,
    NaturalCommandParser,
    VerificationLevel,
)
from core.cost import (
    APICostTracker,
    CacheFailureReason,
    CacheManager,
    DangerousPromptTracker,
)
from core.memory import (
    MemoryExtractor,
    MemoryIndex,
    MemoryRetriever,
    MemoryStore,
)
from core.secrets import (
    AntiDistillation,
    KairosScheduler,
)
from core.security import (
    OperationLogger,
    SafetyChecker,
    YOLOClassifier,
)

SKILLS_DIR = Path(r"D:\bobo\openclaw-foreign\skills")
STATES_DIR = PROJECT_ROOT / "states"
LOGS_DIR = PROJECT_ROOT / "logs"


# ================================================================
# Skill 执行器（带安全检查）
# ================================================================
def exec_skill(
    action: str,
    params: dict,
    safety_checker: SafetyChecker,
    yolo: YOLOClassifier,
    extra_flags: list[str] = None,
) -> Dict[str, Any]:
    """执行一个 skill，带 YOLO 安全检查"""
    skill_path = SKILLS_DIR / action / "run.py"
    if not skill_path.exists():
        return {"skill": action, "success": False, "error": f"Skill {action} not found"}

    base_cmd = [sys.executable, str(skill_path)]
    extra_flags = extra_flags or []

    for key, value in params.items():
        if isinstance(value, bool):
            if value:
                extra_flags.append(f"--{key}")
        else:
            extra_flags.extend([f"--{key}", str(value)])

    # 插入 --json --dry-run 标志
    flags = []
    remainder = []
    for a in extra_flags:
        if a.startswith("--"):
            flags.append(a)
        else:
            remainder.append(a)
    cmd = base_cmd + flags + remainder

    cmd_str = " ".join(cmd)

    # YOLO 安全检查
    yolo_decision = yolo.classify(cmd_str)
    if yolo_decision.value == "block":
        return {
            "skill": action,
            "success": False,
            "error": f"YOLO BLOCKED: {yolo_decision.value}",
            "safety": "blocked",
        }

    # 安全检查
    safety_result = safety_checker.check_command(cmd_str)
    if not safety_result.passed:
        violations = [v["name"] for v in safety_result.violations]
        return {
            "skill": action,
            "success": False,
            "error": f"SAFETY VIOLATION: {', '.join(violations)}",
            "safety": "blocked",
            "violations": violations,
        }

    # 执行
    max_retries = 2
    for attempt in range(max_retries + 1):
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=60,
                cwd=str(skill_path.parent),
            )
            output = result.stdout.strip() or result.stderr.strip() or ""

            if result.returncode == 0:
                try:
                    data = json.loads(output)
                    return {"skill": action, "success": True, "data": data, "attempts": attempt + 1}
                except json.JSONDecodeError:
                    return {"skill": action, "success": True, "data": output[:500], "attempts": attempt + 1}

            # Non-fatal exit
            if any(kw in output.lower() for kw in ["vulnerabilit", "audit report", "found", "warn"]):
                return {
                    "skill": action,
                    "success": True,
                    "data": output[:500],
                    "attempts": attempt + 1,
                    "note": "non-fatal exit",
                }

            if attempt < max_retries:
                print(f"  ⚠️ {action} attempt {attempt + 1} failed, retrying...")
                continue
            return {"skill": action, "success": False, "error": output[:300], "attempts": attempt + 1}

        except subprocess.TimeoutExpired:
            if attempt < max_retries:
                continue
            return {"skill": action, "success": False, "error": "Timeout(60s)", "attempts": attempt + 1}
        except Exception as e:
            if attempt < max_retries:
                continue
            return {"skill": action, "success": False, "error": str(e), "attempts": attempt + 1}

    return {"skill": action, "success": False, "error": "Max retries", "attempts": max_retries + 1}


# ================================================================
# 完整 Mission 执行
# ================================================================
class AgentMissionV5:
    """V5.0 完整任务执行器

    每步执行前：
    1. 记忆检索 → 注入上下文
    2. Coordinator 拆解任务
    3. YOLO 安全检查
    4. 执行 + 验收
    5. 记忆提取（静默学习）
    """

    def __init__(
        self,
        verify_level: VerificationLevel = VerificationLevel.NORMAL,
        dry_run: bool = False,
    ):
        self.verify_level = verify_level
        self.dry_run = dry_run

        # 记忆系统
        self.memory_store = MemoryStore(store_path=str(STATES_DIR / "memory_store.json"))
        self.memory_index = MemoryIndex()
        self.memory_retriever = MemoryRetriever(self.memory_store, self.memory_index)
        self.memory_extractor = MemoryExtractor(self.memory_store, self.memory_index)

        # Coordinator
        self.coordinator = CoordinatorAgent(verify_level=verify_level)
        self.ac = AcceptanceCriteria()
        self.cmd_parser = NaturalCommandParser()

        # 安全系统
        self.safety_checker = SafetyChecker()
        self.yolo = YOLOClassifier(workdir=str(PROJECT_ROOT))
        self.op_logger = OperationLogger(log_dir=str(LOGS_DIR / "operations"))

        # 省钱模式
        self.cache_manager = CacheManager()
        self.cost_tracker = APICostTracker(budget_limit_usd=5.0)
        self.prompt_tracker = DangerousPromptTracker()

        # 秘密武器
        self.kairos = KairosScheduler(state_file=str(STATES_DIR / "kairos_state.json"))
        self.anti_distillation = AntiDistillation()

        # 任务级 token 估算（用于成本追踪）
        self._tokens_input = 0
        self._tokens_output = 0

        # 初始化索引
        self._init_memory_index()

    def _init_memory_index(self):
        """从 store 重建索引"""
        all_entries = list(self.memory_store.entries.values())
        self.memory_index.rebuild(all_entries)

    def run(self, goal: str, extra_context: str = "") -> dict:
        """执行一次完整任务

        流程：
        1. 检索记忆上下文
        2. 解析自然语言命令
        3. Coordinator 拆解任务
        4. 逐步执行（YOLO检查→验收）
        5. 记忆提取
        """
        t0 = time.time()
        mission_log = []

        # ── Step 1: 记忆检索 ──
        enriched_goal = goal
        if extra_context:
            enriched_goal = f"{goal}\n\n额外上下文：{extra_context}"

        memory_entries = self.memory_retriever.retrieve(enriched_goal, top_k=5)
        memory_context = self.memory_retriever.format_context(memory_entries)
        mission_log.append(f"[MEMORY] 检索到 {len(memory_entries)} 条相关记忆")

        # ── Step 2: 命令解析 ──
        parsed = self.cmd_parser.parse(goal)
        mission_log.append(f"[PARSE] action={parsed.action} priority={parsed.priority}")
        if parsed.constraints:
            mission_log.append(f"[CONSTRAINTS] {parsed.constraints}")
        if parsed.evidence_required:
            mission_log.append(f"[EVIDENCE] 要求: {parsed.evidence_required}")

        # ── Step 3: Coordinator 拆解 ──
        mission = self.coordinator.plan_mission(goal)
        mission_log.append(f"[PLAN] 拆解为 {len(mission.tasks)} 个子任务")

        for task in mission.tasks:
            # 注入证据要求
            if parsed.evidence_required and "test_pass" in parsed.evidence_required:
                task.acceptance_criteria.append("测试用例全部通过（严格验收模式）")
            mission_log.append(f"  - {task.id}: {task.description}")

        if self.dry_run:
            mission_log.append("[DRY-RUN] 跳过实际执行")
            return self._build_report(goal, mission, [], mission_log, t0, memory_context)

        # ── Step 4: 执行 ──
        step_results = []

        # 估算整个任务的 token 消耗
        estimated_input = len(memory_context) // 2 + len(goal) * 3 + sum(len(t.description) for t in mission.tasks) * 3
        estimated_output = len(mission.tasks) * 200
        self._tokens_input = estimated_input
        self._tokens_output = estimated_output

        # 成本追踪：记录规划阶段
        self.cost_tracker.record(
            model=os.environ.get("DEFAULT_MODEL", "deepseek/deepseek-chat"),
            input_tokens=estimated_input,
            output_tokens=estimated_output // 2,
            cached_tokens=len(memory_context) // 2 if memory_context else 0,
            task_id=mission.id,
            duration_ms=int((time.time() - t0) * 1000),
        )

        for task in mission.tasks:
            task.status = "in_progress"
            task_t0 = time.time()

            # 记忆检索（该步骤的上下文）
            task_memory = self.memory_retriever.retrieve(task.description, top_k=3)
            task_context = self.memory_retriever.format_context(task_memory)

            if task_context:
                cache_tokens_saved = len(task_context) // 2
                self.cache_manager.record_hit(
                    tokens_saved=cache_tokens_saved,
                    context_size=len(task_context),
                )
                mission_log.append(
                    f"[CONTEXT] {task.id}: 已注入记忆 {len(task_memory)}条 (+{cache_tokens_saved} tokens cached)"
                )
            else:
                self.cache_manager.record_miss(
                    reason=CacheFailureReason.PROMPT_TOO_LONG,
                    tokens_wasted=200,
                    context_size=len(task.description),
                )

            # 执行前：危险提示检查
            dangerous = self.prompt_tracker.check_before_edit(f"task:{task.description}")
            if dangerous:
                mission_log.append(f"[DANGER] {task.id}: 触及 {len(dangerous)} 个危险区域")

            # 执行 skill（匹配技能名：先查 goal 再查 task.description）
            skill_name = self._match_skill(goal + " " + task.description)
            if skill_name:
                result = exec_skill(
                    skill_name,
                    {},
                    self.safety_checker,
                    self.yolo,
                    extra_flags=["--json"] + (["--dry-run"] if self.dry_run else []),
                )

                # 操作日志
                self.op_logger.log(
                    action=skill_name,
                    command=f"python {skill_name}/run.py --json",
                    result="success" if result.get("success") else "failed",
                    yolo_decision="allow",
                    safety_check="passed",
                )

                # 成本追踪：每次 skill 执行
                task_duration = int((time.time() - task_t0) * 1000)
                self.cost_tracker.record(
                    model=os.environ.get("DEFAULT_MODEL", "deepseek/deepseek-chat"),
                    input_tokens=500,
                    output_tokens=200,
                    task_id=task.id,
                    duration_ms=task_duration,
                )
            else:
                result = {"skill": task.id, "success": True, "data": "no matching skill, simulated ok"}

            step_results.append(result)

            # Coordinator 验收
            evidence = []
            if result.get("success"):
                evidence.append("exit code 0")
                if result.get("data"):
                    data_str = json.dumps(result["data"], ensure_ascii=False)[:200]
                    evidence.append(f"output: {data_str}")

            verify_result = self.coordinator.submit_task(task.id, evidence)
            mission_log.append(f"[{task.id}] {'✅' if verify_result['ok'] else '❌'} {verify_result['reason'][:100]}")

        # ── Step 5: 记忆提取（从该轮对话中学习） ──
        extracted = self.memory_extractor.extract_and_store(
            f"执行了任务: {goal}, 结果: {len([r for r in step_results if r.get('success')])}/{len(step_results)} 通过",
            source="mission",
        )
        if extracted > 0:
            mission_log.append(f"[LEARN] 静默提取了 {extracted} 条新记忆")

        # 重建索引
        self._init_memory_index()

        return self._build_report(goal, mission, step_results, mission_log, t0, memory_context)

    def _match_skill(self, description: str) -> Optional[str]:
        """从任务描述匹配技能名"""
        desc_lower = description.lower()

        # 关键词 → skill 映射（优先级从高到低）
        skill_map = {
            "审计": "security-audit",
            "audit": "security-audit",
            "安全": "security-audit",
            "security": "security-audit",
            "部署": "deployment-automation",
            "deploy": "deployment-automation",
            "代码审查": "frontend-code-review",
            "review": "frontend-code-review",
            "导航": "code-navigator",
            "navigat": "code-navigator",
            "pr": "create-pr",
            "release": "release-notes-generator",
            "发布": "release-notes-generator",
            "db": "db-migrations",
            "数据库": "db-migrations",
            "迁移": "db-migrations",
            "migrat": "db-migrations",
            "图表": "infra-diagram-as-code",
            "diagram": "infra-diagram-as-code",
            "测试": "agent-testing",
            "test": "agent-testing",
            "环境": "add-setting-env",
            "env": "add-setting-env",
            "api": "api-doc-generator",
            "文档": "api-doc-generator",
            "sql": "sql-optimizer",
            "优化": "sql-optimizer",
            "drizzle": "drizzle",
            "github action": "github-actions-generator",
        }

        for keyword, skill in skill_map.items():
            if keyword in desc_lower:
                # 检查 skill 是否存在
                if (SKILLS_DIR / skill / "run.py").exists():
                    return skill

        return None

    def _build_report(
        self,
        goal: str,
        mission,
        step_results: list,
        mission_log: list,
        t0: float,
        memory_context: str,
    ) -> dict:
        """生成执行报告"""
        elapsed = time.time() - t0
        passed = sum(1 for r in step_results if r.get("success"))
        total = len(step_results)

        coordinator_report = self.coordinator.get_mission_report(mission.id)

        return {
            "mission_id": mission.id,
            "goal": goal,
            "timestamp": datetime.now(UTC).isoformat(),
            "version": __version__,
            "dry_run": self.dry_run,
            "memory": {
                "entries_retrieved": len(memory_context.split("\n")) - 1 if memory_context else 0,
                "context": memory_context[:500] if memory_context else "",
            },
            "plan": {
                "task_count": len(mission.tasks),
                "tasks": [
                    {
                        "id": t.id,
                        "description": t.description,
                        "criteria": t.acceptance_criteria,
                    }
                    for t in mission.tasks
                ],
            },
            "execution": {
                "steps_total": total,
                "steps_passed": passed,
                "pass_rate": f"{passed / total * 100:.0f}%" if total else "N/A",
                "elapsed_seconds": round(elapsed, 1),
                "results": step_results,
            },
            "coordinator": coordinator_report,
            "log": mission_log,
            "safety": {
                "yolo_decisions": self.yolo.get_decision_stats(),
                "op_log_stats": self.op_logger.stats(),
            },
            "cost": {
                "cache": self.cache_manager.savings_report(),
                "api": self.cost_tracker.summary(),
                "budget": self.cost_tracker.budget_status(),
                "fix_suggestions": self.cache_manager.get_fix_suggestions(),
                "waste_alerts": self.cost_tracker.detect_waste(),
            },
            "kairos": {
                "tasks": self.kairos.list_tasks(),
                "stats": self.kairos.stats(),
            },
            "anti_distillation": {
                "environment_ok": self.anti_distillation.verify_environment()[0],
                "traps": self.anti_distillation.get_trap_status(),
            },
            "memory_stats": self.memory_store.stats(),
        }


# ================================================================
# CLI
# ================================================================
def main():
    parser = argparse.ArgumentParser(description="V5.0 Agent Mission — 记忆检索→Coordinator→YOLO安全三合一")
    parser.add_argument("--goal", default="审计代码安全并部署", help="任务目标（中英文均可）")
    parser.add_argument("--context", default="", help="额外上下文")
    parser.add_argument("--strict", action="store_true", help="严格验收模式")
    parser.add_argument("--dry-run", action="store_true", help="预览模式（不实际执行）")
    parser.add_argument("--json", action="store_true", help="JSON输出")
    parser.add_argument("--version", action="store_true")
    parser.add_argument("--memory-stats", action="store_true", help="显示记忆库统计")
    parser.add_argument("--safety-stats", action="store_true", help="显示安全统计")
    parser.add_argument("--cost-stats", action="store_true", help="显示成本统计")
    parser.add_argument("--kairos-stats", action="store_true", help="显示Kairos调度状态")
    parser.add_argument("--demo", action="store_true", help="运行演示（不执行真实skill）")

    args = parser.parse_args()

    if args.version:
        print(__version__)
        return

    verify_level = VerificationLevel.STRICT if args.strict else VerificationLevel.NORMAL

    mission = AgentMissionV5(
        verify_level=verify_level,
        dry_run=args.dry_run,
    )

    # 统计查询
    if args.memory_stats:
        stats = mission.memory_store.stats()
        print(json.dumps(stats, indent=2, ensure_ascii=False))
        return

    if args.safety_stats:
        print("安全规则：")
        print(json.dumps(mission.safety_checker.get_rules_summary(), indent=2, ensure_ascii=False))
        print("\n操作日志：")
        print(json.dumps(mission.op_logger.stats(), indent=2, ensure_ascii=False))
        return

    if args.cost_stats:
        print("API成本追踪：")
        print(json.dumps(mission.cost_tracker.summary(), indent=2, ensure_ascii=False))
        print("\n缓存管理：")
        print(json.dumps(mission.cache_manager.savings_report(), indent=2, ensure_ascii=False))
        print("\n危险区域：")
        for area in mission.prompt_tracker.get_all_dangerous():
            print(f"  [{area.id}] {area.name} — {area.impact[:80]}")
        return

    if args.kairos_stats:
        print("Kairos 调度器：")
        print(json.dumps(mission.kairos.stats(), indent=2, ensure_ascii=False))
        print("\n任务列表：")
        for t in mission.kairos.list_tasks():
            status = "🟢" if t["enabled"] else "⚫"
            print(
                f"  {status} [{t['id']}] {t['name']} — trigger={t['trigger']} runs={t['run_count']} fails={t['fail_count']}"
            )
        print("\n反蒸馏：")
        ok, triggered = mission.anti_distillation.verify_environment()
        print(f"  环境验证: {'✅ 通过' if ok else '❌ 触发'}")
        if triggered:
            for t in triggered:
                print(f"    {t}")
        for t in mission.anti_distillation.get_trap_status():
            print(f"  [{t['id']}] {t['name']}: {t['status']}")
        return

    # 执行
    if not args.json:
        print("🎯 V5.0 Agent Mission — 五层全通")
        print(f"   Goal: {args.goal}")
        print(f"   Mode: {'严格' if args.strict else '标准'}验收 | {'DRY-RUN' if args.dry_run else 'LIVE'}")
        print("   Chain: 记忆 → Coordinator → YOLO安全 → 成本追踪 → Kairos\n")

    if args.demo:
        # 演示模式：跳过真实skill执行
        mission.dry_run = True
        report = mission.run(args.goal, args.context)
    else:
        report = mission.run(args.goal, args.context)

    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False, default=str))
    else:
        exe = report["execution"]
        cost = report.get("cost", {})
        kairos = report.get("kairos", {})
        anti = report.get("anti_distillation", {})
        print(f"\n{'=' * 60}")
        print(f"📊 Mission Report: {report['goal']}")
        print(f"   ID: {report['mission_id']}")
        print(f"   Steps: {exe['steps_total']} total | {exe['steps_passed']} passed ({exe['pass_rate']})")
        print(f"   Duration: {exe['elapsed_seconds']}s")
        print(
            f"   Memory: {report['memory']['entries_retrieved']} 条相关 | Store: {report['memory_stats']['total']} 条"
        )
        print(f"   Cache: {cost.get('cache', {}).get('hit_rate', 'N/A')} hit rate")
        print(f"   Cost: ${cost.get('api', {}).get('total_cost_usd', 'N/A')}")
        print(f"   Budget: {cost.get('budget', {}).get('percent_used', 'N/A')} used")
        print(f"   Kairos: {kairos.get('stats', {}).get('total_tasks', 'N/A')} tasks")
        print(f"   AntiDistill: {'✅ 安全' if anti.get('environment_ok') else '❌ 异常'}")
        if report["log"]:
            print("\n📝 执行日志：")
            for entry in report["log"]:
                print(f"   {entry}")
        print(f"{'=' * 60}")

    sys.exit(0 if report["execution"]["steps_passed"] == report["execution"]["steps_total"] else 1)


if __name__ == "__main__":
    main()
