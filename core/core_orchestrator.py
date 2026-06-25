#!/usr/bin/env python3
"""
core_orchestrator.py — 铁钳龙虾之脑 (v1.0.0)
================================================
10 护城河模块的统一编排器。

Pipeline: Memory → Safety → Coordinator → Cache → Execute → Accept → Protect → Store → Legacy

进化引擎 evolution_engine.py 降级为可选插件，通过 on_event() 回调接入。
"""

import json
import os
import sys
import time
import atexit
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional, Dict, List, Any

# === 配置（消除硬编码） ===
TZ = timezone(timedelta(hours=8))
CONFIG_DIR = os.environ.get(
    "LOBSTER_CONFIG_DIR",
    str(Path(__file__).resolve().parent.parent / "config"),
)
STATE_DIR = os.environ.get(
    "LOBSTER_STATE_DIR",
    str(Path(__file__).resolve().parent.parent / "data" / "state"),
)
CACHE_DIR = os.environ.get(
    "LOBSTER_CACHE_DIR",
    str(Path(__file__).resolve().parent.parent / "data" / "cache"),
)

# 确保目录存在
Path(CONFIG_DIR).mkdir(parents=True, exist_ok=True)
Path(STATE_DIR).mkdir(parents=True, exist_ok=True)
Path(CACHE_DIR).mkdir(parents=True, exist_ok=True)

VERSION = "1.0.0"

# === 熔断开关 ===
# 默认禁用旧引擎的代码自动补丁（安全漏洞）
LEGACY_PATCH_ENABLED = os.environ.get("LOBSTER_LEGACY_PATCH", "0") == "1"
# 旧引擎补丁需过 YOLO 二次审核（即使 LEGACY_PATCH_ENABLED=1）
LEGACY_PATCH_YOLO_REVIEW = os.environ.get("LOBSTER_LEGACY_PATCH_YOLO", "1") == "1"


def _atomic_write(path: Path, data: str):
    """原子写入：先写 .tmp 再 rename，避免断电损坏状态文件。"""
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.parent.mkdir(parents=True, exist_ok=True)
    tmp.write_text(data, encoding="utf-8")
    tmp.replace(path)


def ts():
    return datetime.now(TZ).isoformat()


# ═══════════════════════════════════════════════════════════════════════
# CoreOrchestrator
# ═══════════════════════════════════════════════════════════════════════


class CoreOrchestrator:
    """统一编排器：串联 10 个护城河模块 + 旧引擎回调。"""

    def __init__(self):
        self._state: Dict[str, Any] = {}
        self._started_at = ts()
        self._initialized = False
        self._pipeline_stats = {"requests": 0, "blocked": 0, "cached": 0, "rejected": 0, "errored": 0}

        # 各模块延迟初始化
        self._memory_system = None
        self._yolo = None
        self._coordinator = None
        self._cache = None
        self._acceptance = None
        self._protector = None
        self._kairos = None
        self._legacy_evo = None

        # 初始化完成标志
        self._init_modules()
        atexit.register(self.shutdown)

    # ── 初始化 ──────────────────────────────────────────────────────

    def _init_modules(self):
        """依次加载 10 个护城河模块。失败不阻塞，graceful degradation。"""
        init_log = []

        # 1. 记忆系统 (3 files)
        try:
            import core.memory_types as mtypes
            # retriever_agent uses implicit `from memory_types import ...`
            # Ensure core/ is on path for its internal imports
            core_dir = str(Path(__file__).resolve().parent)
            if core_dir not in sys.path:
                sys.path.insert(0, core_dir)
            from core.retriever_agent import RetrieverAgent
            self._mtypes = mtypes
            self._memory_system = RetrieverAgent()
            init_log.append("memory:ok")
        except Exception as e:
            init_log.append(f"memory:fail({e})")

        # 2. YOLO 安全分类器 (23 道检测)
        try:
            import core.yolo_classifier as yolo_mod
            self._yolo = yolo_mod
            init_log.append("yolo:ok")
        except Exception as e:
            init_log.append(f"yolo:fail({e})")

        # 3. Coordinator (30 条规则 + 调度)
        try:
            from core.coordinator_agent import CoordinatorAgent
            self._coordinator = CoordinatorAgent()
            init_log.append("coordinator:ok")
        except Exception as e:
            init_log.append(f"coordinator:fail({e})")

        # 4. 缓存管理器 (14 种失败类型)
        try:
            from core.cache_manager import CacheManager
            self._cache = CacheManager()
            init_log.append("cache:ok")
        except Exception as e:
            init_log.append(f"cache:fail({e})")

        # 5. 验收橡皮图章
        try:
            from core.acceptance import AcceptanceGate
            self._acceptance = AcceptanceGate
            init_log.append("acceptance:ok")
        except Exception as e:
            init_log.append(f"acceptance:fail({e})")

        # 6. 反蒸馏保护
        try:
            from core.anti_distillation import AntiDistillation
            self._protector = AntiDistillation()
            init_log.append("anti-distill:ok")
        except Exception as e:
            init_log.append(f"anti-distill:fail({e})")

        # 7. Kairos CVE 监听器
        try:
            from core.kairos_scheduler import KairosScheduler
            self._kairos = KairosScheduler()
            init_log.append("kairos:ok")
        except Exception as e:
            init_log.append(f"kairos:fail({e})")

        # 8. 旧进化引擎（可选插件）
        self._init_legacy(init_log)

        self._initialized = True
        self._state["init_log"] = init_log
        self._state["version"] = VERSION
        self._state["started_at"] = self._started_at
        self._save_state()

    def _init_legacy(self, init_log: List[str]):
        """加载旧引擎，注入正确路径，默认禁用自动补丁。"""
        try:
            # 修正旧引擎的硬编码 BASE 路径
            import core.evolution_engine as evo
            # 覆盖 BASE 为当前项目路径
            evo.BASE = Path(__file__).resolve().parent.parent
            evo.SKILLS = evo.BASE / "skills"
            evo.LOGS = evo.BASE / ".deploy" / "logs"
            evo.STATE_FILE = evo.BASE / "data" / "state" / "evo_state.json"
            evo.REASONER_PY = evo.SKILLS / "causal-reasoner" / "run.py"
            evo.EVAL_LOG = evo.LOGS / "eval.jsonl"

            self._legacy_evo = evo
            init_log.append("legacy_evo:ok")

            # 熔断：默认禁用自动补丁
            if not LEGACY_PATCH_ENABLED:
                # 猴子补丁：让 _apply_safe_patches 永远返回 False
                evo._apply_safe_patches = lambda *a, **kw: False
                init_log.append("legacy_patch:DISABLED")
            else:
                init_log.append("legacy_patch:ENABLED(explicit)")
        except Exception as e:
            init_log.append(f"legacy_evo:fail({e})")

    # ── 主 Pipeline ─────────────────────────────────────────────────

    def handle(self, user_input: str, context: Optional[Dict] = None) -> Dict:
        """
        完整流水线：记忆 → 安全 → 协调 → 缓存 → 执行 → 验收 → 保护 → 存储 → 旧引擎回调。

        返回 dict:
          { "ok": bool, "result": str, "blocked": bool, "cached": bool,
            "memory_used": int, "pipeline_steps": [...] }
        """
        context = context or {}
        steps = []
        self._pipeline_stats["requests"] += 1

        # ─── Step 1: 记忆检索 ────────────────────────────────────
        memories = self._step_memory(user_input, steps)

        # ─── Step 2: 安全预审（轻量：仅做输入格式检查）────────────
        # YOLO 是代码审计器，不适合拦截用户自然语言输入
        # 真正的安全审计在 Step 6（验收）对生成结果执行

        # ─── Step 3: Coordinator 调度 ────────────────────────────
        plan = self._step_coordinate(user_input, memories, context, steps)
        if plan is None:
            return self._respond(ok=False, result="Coordinator rejected: no plan generated",
                                 blocked=True, steps=steps, memories=len(memories))

        # ─── Step 4: 缓存检查 ────────────────────────────────────
        plan_hash = self._hash_plan(plan)
        cached = self._step_cache_get(plan_hash, steps)
        if cached:
            self._pipeline_stats["cached"] += 1
            return self._respond(ok=True, result=cached, cached=True, steps=steps,
                                 memories=len(memories))

        # ─── Step 5: 执行计划 ────────────────────────────────────
        raw_result = self._step_execute(plan, steps)
        if raw_result is None:
            self._pipeline_stats["errored"] += 1
            return self._respond(ok=False, result="Execution failed", steps=steps,
                                 memories=len(memories))

        # ─── Step 6: YOLO 安全审计（对生成结果）───────────────────
        if not self._step_safety_audit(raw_result, steps):
            self._pipeline_stats["blocked"] += 1
            return self._respond(ok=False, result="Generated code blocked by YOLO security audit",
                                 blocked=True, steps=steps, memories=len(memories))

        # ─── Step 7: 验收 ────────────────────────────────────────
        if not self._step_accept(raw_result, plan, steps):
            self._pipeline_stats["rejected"] += 1
            return self._respond(ok=False, result="Output rejected by acceptance gate",
                                 blocked=True, steps=steps, memories=len(memories))

        # ─── Step 8: 反蒸馏保护 ──────────────────────────────────
        protected = self._step_protect(raw_result, steps)

        # ─── Step 8: 记忆存储 ────────────────────────────────────
        self._step_memory_store(user_input, protected, steps)

        # ─── Step 9: 缓存写入 ────────────────────────────────────
        self._step_cache_set(plan_hash, protected, steps)

        # ─── Step 10: 旧引擎回调 ─────────────────────────────────
        self._step_legacy(user_input, protected, steps)

        return self._respond(ok=True, result=protected, steps=steps, memories=len(memories))

    # ── Pipeline Steps ──────────────────────────────────────────────

    def _step_memory(self, user_input: str, steps: List) -> List[Dict]:
        if self._memory_system is None:
            steps.append("memory:unavailable")
            return []
        try:
            memories = self._memory_system.retrieve(user_input)
            steps.append(f"memory:{len(memories)}_hits")
            return memories
        except Exception as e:
            steps.append(f"memory:error({e})")
            return []

    def _step_safety(self, user_input: str, steps: List) -> bool:
        """轻量输入检查。YOLO 不适合自然语言输入拦截。"""
        steps.append("safety:passthrough")
        return True

    def _step_safety_audit(self, raw_result: str, steps: List) -> bool:
        """对 AI 生成的代码做 YOLO 安全审计。"""
        if self._yolo is None:
            steps.append("yolo_audit:unavailable")
            return True
        try:
            result = self._yolo.classify(raw_result)
            if not result.get("passed", True):
                severity = result.get("severity_counts", {})
                steps.append(f"yolo_audit:BLOCKED({result.get('total_failures',0)}_issues,{severity})")
                return False
            steps.append("yolo_audit:pass")
            return True
        except Exception as e:
            steps.append(f"yolo_audit:error({e})")
            return True  # 审计故障时放行

    def _step_coordinate(self, user_input, memories, context, steps):
        if self._coordinator is None:
            steps.append("coordinator:unavailable")
            return {"action": "passthrough", "input": user_input}
        try:
            plan = self._coordinator.dispatch(user_input)
            steps.append(f"coordinator:{plan.get('action','unknown')}")
            return plan
        except Exception as e:
            steps.append(f"coordinator:error({e})")
            return {"action": "passthrough", "input": user_input}

    def _step_cache_get(self, plan_hash, steps):
        if self._cache is None:
            steps.append("cache:unavailable")
            return None
        try:
            cached = self._cache.get(plan_hash)
            if cached:
                steps.append("cache:HIT")
            else:
                steps.append("cache:MISS")
            return cached
        except Exception as e:
            steps.append(f"cache:error({e})")
            return None

    def _step_execute(self, plan, steps):
        """执行计划。目前透传，后续接入 local_llm + DeepSeek API。"""
        try:
            # 如果有 coordinator 生成的 agent 分配，按 agent 执行
            action = plan.get("action", "passthrough")
            agent = plan.get("agent")

            if action == "passthrough":
                steps.append("execute:passthrough")
                return plan.get("input", "")

            # TODO: 实际调用 agent 执行
            steps.append(f"execute:{action}({agent or 'default'})")
            return f"[Execution result for action={action}]"
        except Exception as e:
            steps.append(f"execute:error({e})")
            return None

    def _step_accept(self, raw_result, plan, steps):
        if self._acceptance is None:
            steps.append("acceptance:unavailable")
            return True  # 无验收时放行
        try:
            # 从 agent_id 推断验收器类型
            agent_id = plan.get("agent_id", plan.get("agent_type", "pass"))
            type_map = {"vis": "vis", "code": "code", "ops": "ops", "qa": "code", "doc": "doc", "sec": "code"}
            agent_type = plan.get("agent_type", type_map.get(agent_id, "pass"))
            if agent_type == "pass":
                result = {"passed": True}
            elif agent_type == "vis":
                result = self._acceptance.check_vis(raw_result)
            elif agent_type == "cso":
                result = self._acceptance.check_cso(raw_result)
            elif agent_type == "code":
                result = self._acceptance.check_code(raw_result)
            else:
                result = {"passed": True}

            if result.get("passed"):
                steps.append("acceptance:PASS")
                return True
            else:
                failures = result.get("failures", [])
                steps.append(f"acceptance:REJECTED({len(failures)}_failures:{failures[:2]})")
                # 自动存入纠正记忆
                self._store_correction(raw_result, failures)
                return False
        except Exception as e:
            steps.append(f"acceptance:error({e})")
            return True  # 验收故障时放行

    def _step_protect(self, raw_result, steps):
        if self._protector is None:
            steps.append("protect:unavailable")
            return raw_result
        try:
            # 注入水印
            watermarked = self._protector.embed_watermark(raw_result)
            steps.append("protect:watermarked")
            return watermarked
        except Exception as e:
            steps.append(f"protect:error({e})")
            return raw_result

    def _step_memory_store(self, user_input, result, steps):
        if self._memory_system is None:
            steps.append("store:unavailable")
            return
        try:
            from core.extractor import get_extractor
            extractor = get_extractor()
            if self._mtypes:
                fragment = self._mtypes.MemoryFragment(
                    content=user_input[:500],
                    memory_class=self._mtypes.MemoryClass.PROJECT_STATE,
                    weight=0.7,
                    source="orchestrator",
                )
                # 异步存储（不阻塞 pipeline）
                extractor.enqueue(fragment)
                steps.append("store:enqueued")
            else:
                steps.append("store:no_mtypes")
        except Exception as e:
            steps.append(f"store:error({e})")

    def _step_cache_set(self, plan_hash, result, steps):
        if self._cache is None:
            steps.append("cache_set:unavailable")
            return
        try:
            self._cache.set(plan_hash, result)
            steps.append("cache_set:ok")
        except Exception as e:
            steps.append(f"cache_set:error({e})")

    def _step_legacy(self, user_input, result, steps):
        if self._legacy_evo is None:
            steps.append("legacy:unavailable")
            return
        try:
            state = self._legacy_evo.load_state()
            self._legacy_evo.log_cycle(state, {
                "action": "orchestrator_feedback",
                "input": user_input[:200],
                "result": result[:200],
            })
            self._legacy_evo.save_state(state)
            steps.append("legacy:logged")
        except Exception as e:
            steps.append(f"legacy:error({e})")

    # ── 纠正记忆 ──────────────────────────────────────────────────

    def _store_correction(self, result, failures):
        """验收失败时自动存入纠正记忆，权重 1.0 最高优先级。"""
        if self._memory_system is None:
            return
        try:
            if self._mtypes is None:
                return
            from core.extractor import get_extractor
            correction_text = f"CORRECTION: Output rejected. Failures: {failures}"
            fragment = self._mtypes.MemoryFragment(
                content=correction_text,
                memory_class=self._mtypes.MemoryClass.CORRECTIONS,
                weight=1.0,
                source="acceptance_gate",
            )
            get_extractor().enqueue(fragment)
        except Exception:
            pass

    # ── 辅助方法 ──────────────────────────────────────────────────

    def _hash_plan(self, plan: Dict) -> str:
        """生成计划哈希用于缓存键。"""
        import hashlib
        raw = json.dumps(plan, sort_keys=True, ensure_ascii=False, default=str)
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    def _respond(self, ok, result, blocked=False, cached=False, steps=None, memories=0):
        return {
            "ok": ok,
            "result": result,
            "blocked": blocked,
            "cached": cached,
            "memory_used": memories,
            "pipeline_steps": steps or [],
            "timestamp": ts(),
        }

    # ── 生命周期 ──────────────────────────────────────────────────

    def shutdown(self):
        """优雅关闭。"""
        if self._kairos:
            try:
                self._kairos.stop()
            except Exception:
                pass
        # 保存最终状态
        self._state["shutdown_at"] = ts()
        self._save_state()

    def health(self) -> Dict:
        """健康检查：返回所有模块的可用状态。"""
        status = {
            "version": VERSION,
            "initialized": self._initialized,
            "started_at": self._started_at,
            "uptime_seconds": (datetime.now(TZ) - datetime.fromisoformat(self._started_at)).total_seconds(),
            "modules": {
                "memory": self._memory_system is not None,
                "yolo": self._yolo is not None,
                "coordinator": self._coordinator is not None,
                "cache": self._cache is not None,
                "acceptance": self._acceptance is not None,
                "anti_distill": self._protector is not None,
                "kairos": self._kairos is not None,
                "legacy_evo": self._legacy_evo is not None,
            },
            "pipeline_stats": self._pipeline_stats,
            "init_log": self._state.get("init_log", []),
        }
        # 附加各模块的详细健康信息
        if self._memory_system:
            try:
                status["memory_detail"] = self._memory_system.health()
            except Exception:
                pass
        if self._kairos:
            try:
                status["kairos_detail"] = self._kairos.health()
            except Exception:
                pass
        return status

    def _save_state(self):
        """原子写入状态文件。"""
        state_path = Path(STATE_DIR) / "orchestrator_state.json"
        _atomic_write(state_path, json.dumps(self._state, indent=2, ensure_ascii=False, default=str))


# ═══════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════

def main():
    import argparse

    parser = argparse.ArgumentParser(description="CoreOrchestrator - 铁钳龙虾之脑")
    parser.add_argument("--health", action="store_true", help="打印健康状态 JSON")
    parser.add_argument("--test", type=str, default=None, help="测试输入字符串")
    parser.add_argument("--once", action="store_true", help="单次运行后退出")
    parser.add_argument("--daemon", action="store_true", help="守护模式，循环运行")
    parser.add_argument("--interval", type=int, default=60, help="守护模式间隔(秒)")
    parser.add_argument("--json", action="store_true", help="JSON 输出")

    args = parser.parse_args()

    orch = CoreOrchestrator()

    if args.health:
        h = orch.health()
        if args.json:
            print(json.dumps(h, indent=2, ensure_ascii=False, default=str))
        else:
            print(f"CoreOrchestrator v{h['version']}")
            print(f"  Uptime: {h['uptime_seconds']:.0f}s")
            print(f"  Modules: {json.dumps(h['modules'])}")
            print(f"  Stats: {h['pipeline_stats']}")
            print(f"  Init: {h['init_log']}")
        return

    if args.test:
        result = orch.handle(args.test)
        print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
        return

    if args.daemon or args.once:
        orch._daemon_loop(interval=args.interval, once=args.once)
        return

    parser.print_help()


if __name__ == "__main__":
    main()
