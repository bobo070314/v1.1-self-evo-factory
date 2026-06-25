# -*- coding: utf-8 -*-
"""运行 local_llm.py 并写入文件（避免 GBK 终端炸输出）"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.local_llm import chat

prompt = sys.argv[1] if len(sys.argv) > 1 else "你好，一句话"
text, src = chat(prompt)

outfile = os.path.join(os.path.dirname(__file__), "..", "ollama_last_output.txt")
with open(outfile, "w", encoding="utf-8") as f:
    f.write(f"[{src}] {text}\n")

print(f"[{src}] {text}")
