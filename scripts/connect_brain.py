import sys, os
sys.path.insert(0, r"D:\bobo\projects\v1.1-self-evo-factory")

from scripts.agnes_client import call_llm  # 免费 LLM 客户端
from core.self_evolve import SelfEvolver, QualityScorer

# 故意"病态"代码：SQL注入 + eval + 空函数 + 死循环风险 + 硬编码密码
BAD_CODE = '''import os

def get_user(uid, pwd):
    password = "admin123"
    query = "SELECT * FROM users WHERE id=" + uid
    result = os.system(query)
    return eval(result)

def loop():
    while True:
        pass

def empty():
    pass
'''

print("=== 1) 考官评分（应 < 65 才能触发修复）===")
sc = QualityScorer()
pre = sc.score(BAD_CODE, "code")
print("total:", pre["total"])
print("issues:", [i["msg"] for i in pre["issues"]])

print("\n=== 2) 连接 LLM 并运行真实自进化闭环 ===")
ev = SelfEvolver(cloud_fn=call_llm)
print("llm_available:", ev.health()["llm_available"])

out, meta = ev.evolve(BAD_CODE, "修复这段代码：SQL注入、eval、空函数、死循环、硬编码密码", agent_type="code")

print("\n=== 进化结果 ===")
print("final_score:", meta["final_score"])
print("iterations:", meta["iterations"])
print("rolled_back:", meta["rolled_back"])
print("issues:", meta["issues"])
print("\n--- 修复后的代码 ---")
print(out)

print("\n=== 3) 修复后复评 ===")
post = sc.score(out, "code")
print("post total:", post["total"], "(pre was", pre["total"], ")")
