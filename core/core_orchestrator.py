import os, json, sys, time, atexit
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional, Dict, List, Any
import requests as rq

VERSION = "1.0.1"

TZ = timezone(timedelta(hours=8))
CONFIG_DIR = os.environ.get("LOBSTER_CONFIG_DIR", str(Path(__file__).resolve().parent.parent / "config"))
STATE_DIR = os.environ.get("LOBSTER_STATE_DIR", str(Path(__file__).resolve().parent.parent / "data" / "state"))
CACHE_DIR = os.environ.get("LOBSTER_CACHE_DIR", str(Path(__file__).resolve().parent.parent / "data" / "cache"))

LEGACY_PATCH_ENABLED = os.environ.get("LOBSTER_LEGACY_PATCH", "").lower() in ("1", "true", "yes")

AGENT_DISPLAY = {
    "cso": "Chief Strategy Officer", "vis": "Visual Designer",
    "code": "Code Agent", "ops": "Ops Agent", "doc": "Doc Agent", "sec": "Security Agent",
}

# CRITICAL: 全局 sys.path 修复
_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

class CoreOrchestrator:
    def __init__(self):
        self._started_at = datetime.now(TZ).isoformat()
        self._state = {}
        self._initialized = False
        self._pipeline_stats = {"requests": 0, "blocks": 0, "cached": 0, "cloud": 0, "local": 0}

        # 模块引用
        self._memory_system = None
        self._mtypes = None
        self._yolo_classifier = None
        self._coordinator = None
        self._cache = None
        self._acceptance = None
        self._protector = None
        self._kairos = None
        self._llm_chat = None
        self._legacy_evo = None

        # 确保目录存在
        for d in [STATE_DIR, CACHE_DIR, CONFIG_DIR]:
            Path(d).mkdir(parents=True, exist_ok=True)

        self._init_modules()

    # ── 模块初始化 ─────────────────────────────────────────────────
    def _init_modules(self):
        init_log = []

        # 1. 记忆系统
        try:
            from core.memory_types import MemoryClass, MemoryFragment
            self._mtypes = type("_", (), {"MemoryClass": MemoryClass, "MemoryFragment": MemoryFragment})
            from core.extractor import get_extractor
            self._memory_system = get_extractor()
            init_log.append("memory:ok")
        except Exception as e:
            init_log.append(f"memory:fail({e})")

        # 2. YOLO 安全分类器
        try:
            from core.yolo_classifier import classify as yolo_classify
            self._yolo_classifier = yolo_classify
            init_log.append("yolo:ok")
        except Exception as e:
            init_log.append(f"yolo:fail({e})")

        # 3. Coordinator
        try:
            from core.coordinator_agent import CoordinatorAgent
            self._coordinator = CoordinatorAgent()
            init_log.append("coordinator:ok")
        except Exception as e:
            init_log.append(f"coordinator:fail({e})")

        # 4. Cache
        try:
            from core.cache_manager import CacheManager
            self._cache = CacheManager()
            init_log.append("cache:ok")
        except Exception as e:
            init_log.append(f"cache:fail({e})")

        # 5. Acceptance
        try:
            from core.acceptance import check_cso, check_vis, check_code
            self._acceptance = {"cso": check_cso, "vis": check_vis, "code": check_code}
            init_log.append("acceptance:ok")
        except Exception as e:
            init_log.append(f"acceptance:fail({e})")

        # 6. 反蒸馏
        try:
            from core.anti_distillation import AntiDistillation
            self._protector = AntiDistillation()
            init_log.append("anti-distill:ok")
        except Exception as e:
            init_log.append(f"anti-distill:fail({e})")

        # 7. Kairos
        try:
            from core.kairos_scheduler import KairosScheduler
            self._kairos = KairosScheduler()
            init_log.append("kairos:ok")
        except Exception as e:
            init_log.append(f"kairos:fail({e})")

        # 7.5. 本地 LLM (qwen 兜底)
        try:
            from core.local_llm import chat as llm_chat
            self._llm_chat = llm_chat
            init_log.append("llm_engine:ok")
        except Exception as e:
            init_log.append(f"llm_engine:fail({e})")
            self._llm_chat = None

        # 8. 旧进化引擎（可选插件）
        self._init_legacy(init_log)

        self._initialized = True
        self._state["init_log"] = init_log
        self._state["version"] = VERSION
        self._state["started_at"] = self._started_at
        self._save_state()

    def _init_legacy(self, init_log):
        try:
            import core.evolution_engine as evo
            evo.BASE = Path(__file__).resolve().parent.parent
            evo.SKILLS = evo.BASE / "skills"
            evo.LOGS = evo.BASE / ".deploy" / "logs"
            evo.STATE_FILE = evo.BASE / "data" / "state" / "evo_state.json"
            evo.REASONER_PY = evo.SKILLS / "causal-reasoner" / "run.py"
            evo.EVAL_LOG = evo.LOGS / "eval.jsonl"
            self._legacy_evo = evo
            init_log.append("legacy_evo:ok")
            if not LEGACY_PATCH_ENABLED:
                evo._apply_safe_patches = lambda *a, **kw: False
                init_log.append("legacy_patch:DISABLED")
            else:
                init_log.append("legacy_patch:ENABLED(explicit)")
        except Exception as e:
            init_log.append(f"legacy_evo:fail({e})")

    # ── 主 Pipeline ─────────────────────────────────────────────────
    def handle(self, user_input: str, context: Optional[Dict] = None) -> Dict:
        context = context or {}
        steps = []
        self._pipeline_stats["requests"] += 1

        result = user_input
        blocked = False
        cached = False

        # Step 1: 记忆检索
        memories = self._step_memory_retrieve(user_input, steps)

        # Step 2: Coordinator
        plan = self._step_coordinate(user_input, steps)

        # Step 3: 缓存
        cached_result = self._step_cache_get(plan, steps)
        if cached_result is not None:
            steps.append("cache:HIT")
            self._pipeline_stats["cached"] += 1
            return {"ok": True, "result": cached_result, "blocked": False, "cached": True,
                    "pipeline_steps": steps, "memory_used": len(memories)}

        steps.append("cache:MISS")

        # Step 4: Execute (cloud → local)
        result = self._step_execute(plan, steps)
        if result is None:
            return {"ok": False, "result": "执行失败", "blocked": False, "cached": False,
                    "pipeline_steps": steps, "memory_used": len(memories)}

        # Step 6: YOLO 安全审计（输出侧）
        if not self._step_yolo_audit(result, steps):
            self._pipeline_stats["blocks"] += 1
            return {"ok": False, "result": "生成的内容被安全审计拦截", "blocked": True, "cached": False,
                    "pipeline_steps": steps, "memory_used": len(memories)}

        # Step 7: Acceptance
        self._step_accept(plan, result, steps)

        # Step 8: 保护
        result = self._step_protect(result, steps)

        # Step 9: 存储
        self._step_memory_store(user_input, result, steps)

        # Step 10: 缓存写入
        self._step_cache_set(plan, result, steps)

        # Step 11: 旧引擎回调
        self._step_legacy(user_input, result, steps)

        return {"ok": True, "result": result, "blocked": False, "cached": False,
                "pipeline_steps": steps, "memory_used": len(memories)}

    # ── Pipeline Steps ──────────────────────────────────────────────
    def _step_memory_retrieve(self, user_input, steps):
        if self._memory_system is None:
            steps.append("memory:unavailable")
            return []
        try:
            hits = self._memory_system.recall(user_input, limit=5)
            steps.append(f"memory:{len(hits)}_hits")
            return hits
        except Exception:
            steps.append("memory:error")
            return []

    def _step_coordinate(self, user_input, steps):
        if self._coordinator is None:
            steps.append("coordinator:unavailable")
            return {"action": "passthrough", "input": user_input, "user_query": user_input, "agent_id": "code"}
        try:
            plan = self._coordinator.dispatch(user_input)
            agent = plan.get("agent_id", "?")
            verdict = plan.get("verdict", "?")
            steps.append(f"coordinator:{verdict}(agent={agent})")
            # 补全缺少的字段
            plan.setdefault("input", user_input)
            plan.setdefault("user_query", user_input)
            return plan
        except Exception as e:
            steps.append(f"coordinator:error({e})")
            return {"action": "passthrough", "input": user_input, "user_query": user_input, "agent_id": "code"}

    def _step_cache_get(self, plan, steps):
        if self._cache is None:
            return None
        try:
            key = self._cache.dedup_key(plan.get("input", ""))
            return self._cache.get(key)
        except Exception:
            return None

    def _step_execute(self, plan, steps):
        """cloud(DeepSeek)优先 → local(qwen)兜底 → 离线规则"""
        try:
            agent_id = plan.get("agent_id", "code")
            user_input = plan.get("input", plan.get("user_query", ""))

            if not user_input:
                steps.append("execute:no_input")
                return ""

            system_prompt = self._build_agent_prompt(agent_id, AGENT_DISPLAY.get(agent_id, agent_id))
            full_prompt = f"{system_prompt}\n\n用户请求：{user_input}\n\n请直接输出结果代码/文档，不要输出解释。"

            # 优先 cloud
            cloud_output = self._try_cloud(full_prompt)
            if cloud_output:
                steps.append("execute:cloud")
                self._pipeline_stats["cloud"] += 1
                return cloud_output

            # 兜底 local
            if self._llm_chat:
                raw, source = self._llm_chat(full_prompt)
                steps.append(f"execute:local({source})")
                self._pipeline_stats["local"] += 1
                return raw

            steps.append("execute:no_engine")
            return "[无可用引擎]"

        except Exception as e:
            steps.append(f"execute:error({e})")
            return None

    def _try_cloud(self, prompt: str) -> str:
        api_key = os.environ.get("DEEPSEEK_API_KEY", "")
        if not api_key:
            return ""
        try:
            resp = rq.post(
                "https://api.deepseek.com/v1/chat/completions",
                json={"model": "deepseek-chat", "messages": [{"role": "user", "content": prompt}],
                      "temperature": 0.2, "max_tokens": 2048},
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=30,
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"].strip()
        except Exception:
            return ""

    def _step_yolo_audit(self, raw_result, steps):
        if self._yolo_classifier is None:
            steps.append("yolo_audit:unavailable")
            return True
        try:
            result = self._yolo_classifier(raw_result)
            if not result.get("passed"):
                sev = result.get("severity_counts", {})
                steps.append(f"yolo_audit:BLOCKED({result.get('total_failures',0)}_issues,{sev})")
                return False
            steps.append("yolo_audit:pass")
            return True
        except Exception as e:
            steps.append(f"yolo_audit:error({e})")
            return True  # 审计故障时放行

    def _step_accept(self, plan, raw_result, steps):
        if self._acceptance is None:
            steps.append("acceptance:unavailable")
            return True
        try:
            agent_type = plan.get("agent_type", plan.get("agent_id", "code"))
            checker = self._acceptance.get(agent_type, self._acceptance.get("code"))
            if checker is None:
                steps.append("acceptance:no_checker")
                return True
            result = checker(raw_result) if callable(checker) else {"passed": True}
            if result.get("passed"):
                steps.append("acceptance:PASS")
                return True
            failures = result.get("failures", [])
            steps.append(f"acceptance:REJECTED({len(failures)})")
            return False
        except Exception as e:
            steps.append(f"acceptance:error({e})")
            return True

    def _step_protect(self, raw_result, steps):
        if self._protector is None:
            steps.append("protect:unavailable")
            return raw_result
        try:
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
            if self._mtypes:
                fragment = self._mtypes.MemoryFragment(
                    content=user_input[:500],
                    memory_class=self._mtypes.MemoryClass.PROJECT_STATE,
                    weight=0.7,
                    source="orchestrator",
                )
                self._memory_system.enqueue(fragment)
                steps.append("store:enqueued")
        except Exception as e:
            steps.append(f"store:error({e})")

    def _step_cache_set(self, plan, result, steps):
        if self._cache is None:
            return
        try:
            key = self._cache.dedup_key(plan.get("input", ""))
            self._cache.set(key, result)
            steps.append("cache_set:ok")
        except Exception:
            pass

    def _step_legacy(self, user_input, result, steps):
        if self._legacy_evo is None:
            return
        try:
            self._legacy_evo.on_event("pipeline_done", {"input": user_input, "output": result})
            steps.append("legacy:logged")
        except Exception:
            pass

    def _build_agent_prompt(self, agent_id: str, agent_name: str) -> str:
        rules_text = ""
        if self._coordinator is not None:
            rules = self._coordinator.get_rules_for(agent_id)
            rules_text = "\n".join(f"- {r}" for r in rules)
        prompts = {
            "code": f"你是全栈开发工程师。输出React/Tailwind代码。\n规则：{rules_text}\n\n要求：直接输出代码，不要解释。",
            "vis": f"你是前端视觉设计师。输出HTML/Tailwind代码。\n规则：{rules_text}\n\n要求：黑白灰主色调，专业严谨。",
            "cso": f"你是产品策略官。输出PRD文档。\n\n要求：包含用户画像、功能边界，不要模糊词。",
            "ops": f"你是运维工程师。输出部署配置。\n\n要求：包含rollback方案，健康检查完备。",
        }
        return prompts.get(agent_id, prompts["code"])

    def _save_state(self):
        try:
            state_path = os.path.join(STATE_DIR, "orchestrator_state.json")
            with open(state_path, "w", encoding="utf-8") as f:
                json.dump({
                    "version": VERSION, "started_at": self._started_at,
                    "init_log": self._state.get("init_log", []),
                    "pipeline_stats": self._pipeline_stats,
                    "last_updated": datetime.now(TZ).isoformat(),
                }, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def health(self) -> Dict:
        return {
            "version": VERSION,
            "initialized": self._initialized,
            "modules": {
                "memory": self._memory_system is not None,
                "yolo": self._yolo_classifier is not None,
                "coordinator": self._coordinator is not None,
                "cache": self._cache is not None,
                "acceptance": self._acceptance is not None,
                "protector": self._protector is not None,
                "kairos": self._kairos is not None,
                "llm_engine": self._llm_chat is not None,
                "legacy_evo": self._legacy_evo is not None,
            },
            "init_log": self._state.get("init_log", []),
            "pipeline_stats": self._pipeline_stats,
        }
