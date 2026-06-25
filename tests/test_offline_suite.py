# -*- coding: utf-8 -*-
"""猫抓离线大脑 — 全量验收测试（5项）"""
import sys, os, json
sys.path.insert(0, 'D:/bobo/projects/v1.1-self-evo-factory')
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

passed = 0
failed = 0

def check(name, condition, detail=""):
    global passed, failed
    if condition:
        passed += 1
        print(f"  [PASS] {name}")
    else:
        failed += 1
        print(f"  [FAIL] {name} | {detail}")

print("=" * 50)
print("猫抓离线大脑全量验收 (5项)")
print("=" * 50)

# ── 1. 仓库分家 ──
print("\n[1/5] 仓库分家...")
import subprocess
r = subprocess.run(["git", "-C", "D:/bobo/openclaw-foreign/workspace", "remote", "get-url", "origin"],
                   capture_output=True, text=True, encoding="utf-8", errors="replace")
check("Workspace remote != v1.1 factory", "openclaw-foreign-workspace" in r.stdout, r.stdout.strip())

# ── 2. 离线规则引擎 ──
print("\n[2/5] 离线规则引擎...")
from core.offline_engine import match
resp1, rule1 = match("你好")
check("greeting 规则", rule1 is not None and "你好" in rule1)
resp2, rule2 = match("代码有bug")
check("代码 规则", rule2 is not None and "代码" in rule2)
resp3, rule3 = match("今天天气怎么样")
check("天气 规则", rule3 is not None and "天气" in rule3)
resp4, rule4 = match("xyzzy_nomatch_999")
check("无匹配回退", rule4 is None and len(resp4) > 10, f"resp={resp4[:50]}")

# ── 3. BM25 检索 ──
print("\n[3/5] BM25 检索...")
from core.bm25_fallback import BM25Fallback
bm = BM25Fallback()
bm.index(["猫抓本地AI助手", "Ollama GPU推理", "GitHub SSH push", "React Tailwind", "Python Windows坑点"])
results = bm.search("AI助手")
check("BM25 检索命中", len(results) > 0 and "猫抓" in results[0][2], f"top={results[0][2][:40]}")
check("BM25 分数>0", results[0][1] > 0, f"score={results[0][1]:.3f}")

# ── 4. 向量存储 ──
print("\n[4/5] 向量存储...")
from core.local_vector_store import LocalVectorStore
store = LocalVectorStore()
store.add(["猫抓本地AI助手离线大脑", "Python Windows GBK终端坑点", "React Next.js Tailwind建站"])
r = store.search("AI")
check("向量搜索返回结果", len(r) > 0)
check("向量搜索AI命中", "AI" in r[0][0] or "猫抓" in r[0][0], f"top={r[0][0][:40]}")

# ── 5. 三级回退整合 ──
print("\n[5/5] 三级回退整合...")
from core.local_llm import chat, health, is_ollama_alive
h = health()
print(f"  health: {json.dumps(h, ensure_ascii=False)}")
check("health 包含 ollama_alive", "ollama_alive" in h)
check("health 包含 offline_engine", h.get("offline_engine") == True)
check("health 包含 bm25", h.get("bm25") == True)

# 离线模式验证（如果 Ollama 在线就验证来源）
resp, src = chat("代码报错了怎么办")
check("chat 有返回", len(resp) > 10, f"resp={resp[:60]}")
check("chat 来源合法", src in ("local", "cloud", "offline"), f"src={src}")
print(f"  chat source: {src}")

print("\n" + "=" * 50)
print(f"[DONE] {passed}/{passed+failed} 通过", end="")
if failed > 0:
    print(f", {failed} 失败")
else:
    print(" — 全部通过！")
print("=" * 50)
