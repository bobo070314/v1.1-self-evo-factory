#!/usr/bin/env python3
"""
core/core_orchestrator.py — 铁钳龙虾之脑 (v2.0)
================================================
6 大护城河升级模块全部集成。

Pipeline 7 步精简版：
1. 记忆检索（SQLite 持久化）
2. Coordinator 调度
3. 缓存查询（多级缓存 + TTL）
4. 执行（cloud first + local fallback）
5. AI 验收（快速检查 → LLM 深度语义审查）
   ↓ 如果验收未通过或质量分不足
   ├─ 自我迭代（评分 → 修复 → 重执行 → 回滚保护）
6. 反蒸馏保护（思维扰动 + 金丝雀水印）
7. 记忆存储 + 缓存写入 + Kairos 回调
"""

import json
import os
import sys
import time
import socket
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional, Dict, List, Any
import requests as rq

VERSION = "2.0.0"

TZ = timezone(timedelta(hours=8))
BASE = Path(__file__).resolve().parent.parent

# 全局 sys.path 修复
if str(BASE) not in sys.path:
    sys.path.insert(0, str(BASE))

AGENT_DISPLAY = {
    "cso": "Chief Strategy Officer",
    "vis": "Visual Designer",
    "code": "Code Agent",
    "ops": "Ops Agent",
    "doc": "Doc Agent",
    "sec": "Security Agent",
}


def _extract_output(text: str) -> str:
    """精准提取 [OUTPUT]...[/OUTPUT] 块，无标签时返回空"""
    if not text:
        return ""
    import re
    m = re.search(r'\[OUTPUT\](.*?)\[/OUTPUT\]', text, re.DOTALL | re.IGNORECASE)
    if m:
        return m.group(1).strip()
    # 没标签但很短——可能只吐了结果
    if len(text) < 100:
        return text.strip()
    return ""   # 长文本无标签视为无效


class CoreOrchestrator:
    def __init__(self):
        self._started_at = datetime.now(TZ).isoformat()
        self._pipeline_stats = {"requests": 0, "cloud": 0, "local": 0, "cached": 0, "evolved": 0, "blocked": 0}

        # 模块引用
        self._memory_retriever = None
        self._memory_store_mgr = None
        self._extractor = None
        self._coordinator = None
        self._cache = None
        self._fast_gate = None
        self._ai_acceptance = None
        self._self_evolver = None
        self._protector = None
        self._kairos = None
        self._llm_chat = None
        self._rules_orchestrator = None

        self._init_modules()

    def _init_modules(self):
        init_log = []

        # 0. LLM 引擎（cloud + local）
        self._cloud_fn = self._make_cloud_fn()
        try:
            from core.local_llm import chat as llm_chat
            self._llm_chat = llm_chat
            init_log.append("llm_engine:ok")
        except Exception as e:
            init_log.append(f"llm_engine:fail({e})")

        # 1. 记忆系统（SQLite 持久化 + daemon 提取器）
        try:
            from core.memory_store import get_store
            self._memory_store_mgr = get_store()
            init_log.append("memory_store:ok")
        except Exception as e:
            init_log.append(f"memory_store:fail({e})")
        try:
            from core.retriever_agent import get_retriever
            self._memory_retriever = get_retriever()
            init_log.append("memory_retrieve:ok")
        except Exception as e:
            init_log.append(f"memory_retrieve:fail({e})")
        try:
            from core.extractor import get_extractor
            self._extractor = get_extractor()
            self._extractor.start()
            init_log.append("extractor:ok")
        except Exception as e:
            init_log.append(f"extractor:fail({e})")

        # 2. Coordinator
        try:
            from core.coordinator_agent import CoordinatorAgent
            self._coordinator = CoordinatorAgent()
            init_log.append("coordinator:ok")
        except Exception as e:
            init_log.append(f"coordinator:fail({e})")

        # 3. 多级缓存
        try:
            from core.cache_manager import CacheManager
            self._cache = CacheManager()
            init_log.append("cache:ok")
        except Exception as e:
            init_log.append(f"cache:fail({e})")

        # 4. AI 验收（快速检查 → LLM 深度审查）
        try:
            from core.ai_acceptance import AIAcceptanceGate
            self._ai_acceptance = AIAcceptanceGate(cloud_fn=self._try_cloud)
            init_log.append("ai_acceptance:ok")
        except Exception as e:
            init_log.append(f"ai_acceptance:fail({e})")

        # 5. 自我迭代闭环
        try:
            from core.self_evolve import SelfEvolver
            self._self_evolver = SelfEvolver(llm_chat_fn=self._llm_chat, cloud_fn=self._try_cloud)
            init_log.append("self_evolver:ok")
        except Exception as e:
            init_log.append(f"self_evolver:fail({e})")

        # 6. 反蒸馏
        try:
            from core.anti_distillation import AntiDistillation
            self._protector = AntiDistillation()
            init_log.append("anti_distill:ok")
        except Exception as e:
            init_log.append(f"anti_distill:fail({e})")

        # 7. Kairos
        try:
            from core.kairos_scheduler import KairosScheduler
            self._kairos = KairosScheduler()
            init_log.append("kairos:ok")
        except Exception as e:
            init_log.append(f"kairos:fail({e})")

        # 8. 规则编排器（文件驱动安全门禁）
        try:
            from core.rules_orchestrator import RulesOrchestrator
            self._rules_orchestrator = RulesOrchestrator()
            init_log.append("rules_orchestrator:ok")
        except Exception as e:
            init_log.append(f"rules_orchestrator:fail({e})")

        self._init_log = init_log
        self._initialized = True

    def _make_cloud_fn(self):
        """生成可调用的 cloud LLM 函数"""
        def cloud_fn(prompt: str) -> str:
            return self._try_cloud(prompt)
        return cloud_fn

    def _try_cloud(self, prompt: str, require_tags: bool = False) -> str:
        """调用 DeepSeek API"""
        api_key = os.environ.get("DEEPSEEK_API_KEY", "")
        if not api_key:
            return ""
        try:
            resp = rq.post(
                "https://api.deepseek.com/v1/chat/completions",
                json={
                    "model": "deepseek-chat",
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.2,
                    "max_tokens": 4096,
                },
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=60,
            )
            resp.raise_for_status()
            raw = resp.json()["choices"][0]["message"]["content"].strip()
            if require_tags:
                extracted = _extract_output(raw)
                return extracted if extracted else raw
            return raw
        except Exception:
            return ""

    def _build_agent_prompt(self, agent_id: str) -> str:
        rules_text = ""
        if self._coordinator:
            rules = self._coordinator.get_rules_for(agent_id)
            rules_text = "\n".join(f"- {r}" for r in rules)
        name = AGENT_DISPLAY.get(agent_id, agent_id)
        prompts = {
            "code": f"你是全栈开发工程师，输出代码。\n规则：{rules_text}\n\n要求：TypeScript + React + Tailwind，直接输出代码。",
            "vis": f"你是前端视觉设计师。\n规则：{rules_text}\n\n要求：HTML/Tailwind，黑白灰，专业严谨。",
            "cso": f"你是产品策略官。\n\n要求：PRD文档，包含用户画像、竞争分析、功能边界、路线图。",
            "ops": f"你是运维工程师。\n\n要求：包含部署配置、rollback方案、健康检查。",
        }
        return prompts.get(agent_id, prompts.get("code", f"你是{name}。请处理用户请求。"))

    # ── 主 Pipeline ─────────────────────────────────────────────────
    def handle(self, user_input: str, context: Optional[Dict] = None) -> Dict:
        context = context or {}
        steps = []
        self._pipeline_stats["requests"] += 1

        plan = {"action": "passthrough", "input": user_input, "user_query": user_input, "agent_id": "code"}
        memories = []

        # Step 1: 记忆检索
        if self._memory_retriever:
            try:
                memories = self._memory_retriever.retrieve(user_input, top_k=5)
                if isinstance(memories, list):
                    steps.append(f"memory:{len(memories)}_hits")
                else:
                    steps.append("memory:0_hits")
            except Exception as e:
                steps.append(f"memory:error({e})")

        # Step 2: Coordinator
        if self._coordinator:
            try:
                plan = self._coordinator.dispatch(user_input)
                plan.setdefault("input", user_input)
                plan.setdefault("user_query", user_input)
                plan.setdefault("agent_id", "code")
                agent = plan.get("agent_id", "?")
                steps.append(f"coordinator:{plan.get('verdict','unknown')}(agent={agent})")
            except Exception as e:
                steps.append(f"coordinator:error({e})")

        # Step 3: 缓存查询
        if self._cache:
            try:
                cache_key = self._cache.dedup_key(user_input)
                cached = self._cache.get(cache_key, "exec")
                if cached is not None:
                    steps.append("cache:HIT")
                    self._pipeline_stats["cached"] += 1
                    return {"ok": True, "result": cached, "blocked": False, "cached": True,
                            "pipeline_steps": steps, "memory_used": len(memories)}
                steps.append("cache:MISS")
            except Exception as e:
                steps.append(f"cache:error({e})")

        # Step 4: 执行
        result = self._execute(plan, steps)
        if result is None:
            return {"ok": False, "result": "执行失败", "blocked": False, "cached": False,
                    "pipeline_steps": steps, "memory_used": len(memories)}

        # Step 4.5: 规则检查（文件驱动安全门禁）
        if self._rules_orchestrator:
            try:
                rule_result = self._rules_orchestrator.check_output(result)
                if rule_result["blocked"]:
                    steps.append(f"rules:blocked({','.join(rule_result['triggered'])})")
                    self._pipeline_stats["blocked"] += 1
                    return {
                        "ok": False,
                        "result": f"被规则阻断: {','.join(rule_result['triggered'])}",
                        "blocked": True,
                        "cached": False,
                        "pipeline_steps": steps,
                        "memory_used": len(memories),
                    }
                for w in rule_result["warnings"]:
                    steps.append(f"rules:warn({w})")
                if rule_result["triggered"]:
                    steps.append(f"rules:checked({len(rule_result['triggered'])}_triggers)")
            except Exception as e:
                steps.append(f"rules:error({e})")

        # Step 5: AI 验收 + 自我迭代
        result = self._check_and_evolve(result, user_input, plan, steps)

        # Step 6: 反蒸馏保护
        if self._protector:
            try:
                result = self._protector.embed_watermark(result, plan.get("agent_id", "code"))
                steps.append("protect:watermarked")
            except Exception as e:
                steps.append(f"protect:error({e})")

        # Step 7: 记忆存储
        self._store_memory(user_input, result, steps)

        # Step 8: 缓存写入
        if self._cache:
            try:
                cache_key = self._cache.dedup_key(user_input)
                self._cache.set(cache_key, result, "exec")
                steps.append("cache_set:ok")
            except Exception as e:
                self._cache and self._cache.record_failure("CACHE_WRITE_FAIL")
                steps.append(f"cache_set:error({e})")

        # Step 9: Kairos 回调（非阻塞）
        if self._kairos and steps.count("self_evolved") > 0:
            try:
                self._kairos.alert("self_evolution", "Pipeline triggered self-evolution cycle", "info")
            except Exception:
                pass

        return {"ok": True, "result": result, "blocked": False, "cached": False,
                "pipeline_steps": steps, "memory_used": len(memories)}

    def _execute(self, plan: Dict, steps: List[str]) -> Optional[str]:
        """执行：cloud first → local fallback"""
        agent_id = plan.get("agent_id", "code")
        user_input = plan.get("input", plan.get("user_query", ""))

        if not user_input:
            steps.append("execute:no_input")
            return ""

        raw_prompt = self._build_agent_prompt(agent_id)
        if user_input:
            raw_prompt += f"\n\n用户请求：{user_input}"
        prompt = raw_prompt + "\n\nCRITICAL: Wrap your final answer in [OUTPUT]...[/OUTPUT] tags. No text outside.\n[OUTPUT]"
        cloud_result = self._try_cloud(prompt, require_tags=True)
        if cloud_result:
            steps.append("execute:cloud")
            self._pipeline_stats["cloud"] += 1
            return cloud_result

        if self._llm_chat:
            # local 分支用不含标签的干净 prompt（qwen 不理解 [OUTPUT] 标签）
            local_prompt = f"{self._build_agent_prompt(agent_id)}\n\n用户请求：{user_input}\n\n直接输出结果，不要额外解释。"
            try:
                raw, source = self._llm_chat(local_prompt)
                steps.append(f"execute:local({source})")
                return raw if raw else f"[{agent_id}] 无法生成内容"
            except Exception as e:
                steps.append(f"execute:local_error({e})")

        steps.append("execute:fallback")
        return f"[{agent_id}] 无法生成内容: 所有引擎不可用"

    def _check_and_evolve(self, result: str, user_input: str, plan: Dict, steps: List[str]) -> str:
        """
        AI 验收 + 自我迭代。
        流程：
        1. AI 深度审查（FastGate + LLM 语义）
        2. 如果质量分 < 阈值 → 自我迭代（评分→修复→重执行→回滚）
        """
        agent_type = plan.get("agent_id", "code")

        # AI 验收
        if self._ai_acceptance:
            try:
                review = self._ai_acceptance.check(result, agent_type)
                score = review.get("final_score", 70)
                issues = review.get("issues", [])
                verdict = review.get("verdict", "PASS")
                steps.append(f"ai_accept:{verdict}({score}分)")

                # 如果分数不足，自我迭代
                if verdict == "FAIL" and self._self_evolver:
                    steps.append("self_evolve:starting")
                    evolved, evo_info = self._self_evolver.evolve(
                        result, user_input, agent_type
                    )
                    if evo_info.get("iterations", 1) > 1:
                        self._pipeline_stats["evolved"] += 1
                        steps.append(f"self_evolve:done({evo_info.get('final_score',0):.0f}分,{evo_info.get('iterations',0)}次迭代)")
                        if evo_info.get("rolled_back"):
                            steps.append("self_evolve:rolled_back")
                        result = evolved
                    else:
                        steps.append("self_evolve:skip(无需迭代)")

            except Exception as e:
                steps.append(f"ai_accept:error({e})")
        else:
            steps.append("ai_accept:unavailable")

        return result

    def _store_memory(self, user_input: str, result: str, steps: List[str]):
        """记忆存储"""
        if not self._memory_store_mgr and not self._extractor:
            steps.append("store:unavailable")
            return

        try:
            from core.memory_types import MemoryClass

            fragment = {
                "text": f"用户查询: {user_input[:200]}\n结果: {result[:200]}",
                "memory_class": "PROJECT_STATE",
                "source": "orchestrator",
                "tags": ["pipeline", "execute"],
            }

            # 优先 SQLite store
            if self._memory_store_mgr:
                try:
                    from core.memory_types import MemoryFragment
                    mf = MemoryFragment(**fragment)
                    self._memory_store_mgr.store(mf.to_dict())
                    steps.append("store:sqlite")
                    return
                except Exception:
                    pass

            # 兜底 extractor
            if self._extractor:
                self._extractor.enqueue(fragment)
                steps.append("store:extractor")

        except Exception as e:
            steps.append(f"store:error({e})")

    def _register_cron_jobs(self):
        """注册 Kairos cron 任务到 openclaw（通过 cron tool）"""
        try:
            from core.kairos_scheduler import KairosScheduler
            k = KairosScheduler()
            # GitHub 检查每 30 分钟
            k.alert("cron_setup", "kairos crons would be registered here", "info")
        except Exception:
            pass

    def health(self) -> Dict:
        return {
            "version": VERSION,
            "initialized": self._initialized,
            "modules": {
                "memory_store": self._memory_store_mgr is not None,
                "memory_retrieve": self._memory_retriever is not None,
                "extractor": self._extractor is not None,
                "coordinator": self._coordinator is not None,
                "cache": self._cache is not None,
                "ai_acceptance": self._ai_acceptance is not None,
                "self_evolver": self._self_evolver is not None,
                "protector": self._protector is not None,
                "kairos": self._kairos is not None,
                "llm_engine": self._llm_chat is not None,
                "cloud_api": bool(os.environ.get("DEEPSEEK_API_KEY", "")),
                "rules_orchestrator": self._rules_orchestrator is not None,
            },
            "init_log": getattr(self, "_init_log", []),
            "pipeline_stats": self._pipeline_stats,
        }
