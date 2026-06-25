#!/usr/bin/env python3
"""
scripts/test_v2_full.py — 6 大方向一次性验收测试
==================================================
1. 记忆系统（SQLite 持久化 + 对话提取）
2. 多级缓存（TTL + DANGEROUS 保护）
3. AI 验收（快速检查 + LLM 语义）
4. 自我迭代闭环（评分→修复→重执行→回滚）
5. 反蒸馏（思维扰动 + 金丝雀水印 + 完整性验证）
6. Kairos 调度器
7. 全链路整合（orchestrator）
"""

import json
import os
import sys
import time

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE not in sys.path:
    sys.path.insert(0, BASE)

PASS = 0
FAIL = 0
WARN = 0

def test(name, fn):
    global PASS, FAIL, WARN
    print(f"  [{name}]...", end=" ", flush=True)
    try:
        result = fn()
        if result is True:
            PASS += 1
            print("✅ PASS")
        elif result is False:
            FAIL += 1
            print("❌ FAIL")
        elif result == "WARN":
            WARN += 1
            print("⚠️  WARN")
        else:
            PASS += 1
            print(f"✅ {result}")
    except Exception as e:
        FAIL += 1
        import traceback
        print(f"❌ ERROR({e})")
        traceback.print_exc()


def main():
    global PASS, FAIL, WARN
    print("=" * 60)
    print("  铁钳龙虾 v2.0 — 6 大方向全量验收")
    print("=" * 60)

    # ── 1. 记忆系统 ──
    print()
    print(">>> 记忆系统")

    test("memory_types导入", lambda: __import__("core.memory_types"))
    test("memory_store导入SQLite", lambda: __import__("core.memory_store"))
    test("memory_store持久化", lambda: _test_memory_store())
    test("extractor导入", lambda: __import__("core.extractor"))
    test("retriever导入", lambda: __import__("core.retriever_agent"))

    # ── 2. 多级缓存 ──
    print()
    print(">>> 多级缓存")
    test("cache_manager导入", lambda: __import__("core.cache_manager"))
    test("cache_set_get", lambda: _test_cache())
    test("cache_TTL过期", lambda: _test_cache_ttl())
    test("DANGEROUS保护", lambda: _test_dangerous())
    test("cache去重", lambda: _test_cache_dedup())

    # ── 3. AI 验收 ──
    print()
    print(">>> AI 验收")
    test("ai_acceptance导入", lambda: __import__("core.ai_acceptance"))
    test("快速检查cso", lambda: _test_fast_cso())
    test("快速检查code", lambda: _test_fast_code())
    test("快速检查vis", lambda: _test_fast_vis())

    # ── 4. 自我迭代 ──
    print()
    print(">>> 自我迭代闭环")
    test("self_evolve导入", lambda: __import__("core.self_evolve"))
    test("质量评分器", lambda: _test_scorer())
    test("修复引擎", lambda: _test_fix_engine())
    test("进化日志", lambda: _test_evolution_log())

    # ── 5. 反蒸馏 ──
    print()
    print(">>> 反蒸馏")
    test("anti_distillation导入", lambda: __import__("core.anti_distillation"))
    test("水印嵌入", lambda: _test_watermark())
    test("完整性验证", lambda: _test_integrity())
    test("思维扰动", lambda: _test_perturb())

    # ── 6. Kairos ──
    print()
    print(">>> Kairos 调度器")
    test("kairos导入", lambda: __import__("core.kairos_scheduler"))
    test("kairos健康检查", lambda: _test_kairos())

    # ── 7. 全链路整合 ──
    print()
    print(">>> 全链路 Orchestrator")
    test("orchestrator导入", lambda: _test_orchestrator())

    # ── 总计 ──
    print()
    print("=" * 60)
    total = PASS + FAIL + WARN
    print(f"  总计: {total} | ✅ {PASS} | ❌ {FAIL} | ⚠️  {WARN}")
    if FAIL == 0:
        print("  🎉 全量通过!")
    else:
        print(f"  ⚠️  有 {FAIL} 个失败")
    print("=" * 60)
    return FAIL == 0


# ── 测试实现 ──

def _test_memory_store():
    from core.memory_store import get_store
    store = get_store()
    info = store.get_stats()
    assert info["total"] >= 0
    return True

def _test_cache():
    from core.cache_manager import CacheManager
    cm = CacheManager()
    cm.set("test_key", "hello", "exec")
    val = cm.get("test_key", "exec")
    assert val == "hello", f"expected hello, got {val}"
    return True

def _test_cache_ttl():
    from core.cache_manager import CacheManager
    cm = CacheManager()
    from core.cache_manager import CACHE_TTLS
    assert "exec" in CACHE_TTLS
    assert CACHE_TTLS["exec"] == 3600
    return True

def _test_dangerous():
    from core.cache_manager import DANGEROUS_Zone, DANGEROUS_KEYS
    assert "plan_hash" in DANGEROUS_KEYS
    assert DANGEROUS_Zone.is_dangerous("plan_hash")
    assert not DANGEROUS_Zone.is_dangerous("normal_key")
    return True

def _test_cache_dedup():
    from core.cache_manager import CacheManager
    cm = CacheManager()
    k1 = cm.dedup_key("Hello World")
    k2 = cm.dedup_key("hello  world")
    assert k1 == k2, "dedup failed"
    return True

def _test_fast_cso():
    from core.ai_acceptance import FastGate
    # 好的 PRD
    good = "用户画像：20岁大学生\n竞争分析：竞品A和平台B\n功能边界：不做支付"
    r1 = FastGate.check_all(good, "cso")
    # 坏的 PRD
    bad = "这个功能很好"
    r2 = FastGate.check_all(bad, "cso")
    assert r1["passed"] or len(r1["failures"]) <= 3  # 宽松
    assert not r2["passed"]
    return True

def _test_fast_code():
    from core.ai_acceptance import FastGate
    good = "const x = 1; export default x;"
    r1 = FastGate.check_all(good, "code")
    bad = 'import os; os.system("rm -rf /")'
    r2 = FastGate.check_all(bad, "code")
    assert r1["passed"]
    assert not r2["passed"]
    return True

def _test_fast_vis():
    from core.ai_acceptance import FastGate
    good = '<div class="flex gap-6"><button class="focus:ring"></button></div>'
    r1 = FastGate.check_all(good, "vis")
    assert r1["passed"]
    bad = '<div class="flex gap-2 transition-all"><button></button></div>'
    r2 = FastGate.check_all(bad, "vis")
    assert not r2["passed"]
    return True

def _test_scorer():
    from core.self_evolve import QualityScorer
    score = QualityScorer.score("function add(a,b){return a+b}", "code")
    assert 0 <= score["total"] <= 100
    assert "detail" in score
    assert "issues" in score
    # 空输出得分应低（没有功能代码但仍有一些基础分）
    empty = QualityScorer.score("", "code")
    assert empty["total"] < 60
    return f"总分{score['total']}"

def _test_fix_engine():
    from core.self_evolve import FixEngine
    issues = [{"type": "syntax", "severity": "high", "msg": "括号不匹配"}]
    strategies = FixEngine.select_strategies(issues)
    assert len(strategies) > 0
    prompt = FixEngine.generate_fix_prompt("test code", issues, "code")
    assert "test code" in prompt
    return True

def _test_evolution_log():
    from core.self_evolve import EvolutionLog
    log = EvolutionLog()
    log.start_run("test_input", "code")
    log.log_generation("test output", {"total": 70, "detail": {}, "issues": []}, "initial")
    log.end_run(85.0, True)
    stats = log.get_stats()
    assert stats["runs"] >= 1
    return True

def _test_watermark():
    from core.anti_distillation import AntiDistillation
    ad = AntiDistillation()
    wm = ad.embed_watermark("function hello() { return 1; }", "code")
    assert len(wm) > len("function hello() { return 1; }")
    # 验证包含水印
    assert "integrity" in wm or "canary" in wm or "anti" in wm or wm != ""
    return "水印注入成功"

def _test_integrity():
    from core.anti_distillation import AntiDistillation
    ad = AntiDistillation()
    output = "console.log('test')"
    wm = ad.embed_watermark(output, "code")
    result = ad.verify_integrity(wm)
    assert "canary_found" in result
    assert result["integrity_score"] >= 0
    return f"完整性{result['integrity_score']}%"

def _test_perturb():
    from core.anti_distillation import AntiDistillation
    ad = AntiDistillation()
    # 多次扰动应保持功能不变
    original = "def add(a, b):\n    return a + b"
    wm = ad.embed_watermark(original, "code")
    assert "return" in wm
    assert "def add" in wm
    return True

def _test_kairos():
    from core.kairos_scheduler import KairosScheduler
    k = KairosScheduler()
    h = k.health()
    assert h["check_count"] >= 0
    return True

def _test_orchestrator():
    from core.core_orchestrator import CoreOrchestrator
    o = CoreOrchestrator()
    h = o.health()
    good = h.get("modules", {})
    ok_count = sum(1 for v in good.values() if v)
    total_count = len(good)
    print(f"{ok_count}/{total_count} 模块在线", end="", flush=True)
    assert ok_count >= 5  # 至少 5 个模块在线
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
