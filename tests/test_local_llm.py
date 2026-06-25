# -*- coding: utf-8 -*-
"""local_llm.py 三级回退验收测试"""
import sys, os, json, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.local_llm import chat, health, is_ollama_alive

print("=" * 50)
print("猫抓 local_llm.py 验收测试")
print("=" * 50)

# 1) Health check
print("\n[1/3] 健康检查...")
h = health()
print(json.dumps(h, indent=2, ensure_ascii=False))

# 2) 本地推理
print("\n[2/3] 本地推理 (Ollama)...")
t0 = time.time()
if is_ollama_alive():
    resp, src = chat("用中文回答：你是谁？一句话")
    elapsed = time.time() - t0
    print(f"  source: {src}")
    print(f"  time: {elapsed:.1f}s")
    print(f"  response: {resp}")
    assert src == "local", f"Expected local, got {src}"
    assert resp and resp != "[本地模型返回空]", f"Empty response"
    print("  [PASS]")
else:
    print("  [SKIP] Ollama not alive")

# 3) 降级逻辑
print("\n[3/3] 降级逻辑验证...")
resp, src = chat("天气怎么样")
print(f"  source: {src}")
print(f"  response: {resp[:80]}...")
assert src in ("local", "offline"), f"Unexpected source: {src}"
print("  [PASS]")

print("\n" + "=" * 50)
print("[DONE] 猫抓本地大脑就绪。")
print("=" * 50)
