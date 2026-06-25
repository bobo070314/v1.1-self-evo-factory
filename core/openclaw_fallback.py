# -*- coding: utf-8 -*-
"""
OpenClaw 集成器 — 将 local_llm.py 三级回退注入到 OpenClaw 执行链。
当 OpenClaw 工具链（web_search/web_fetch/browser）因断网失效时，
自动回退到本地 LLM 或离线引擎。
"""

import os
import sys
import json
from typing import Optional, Tuple

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))


class OpenClawFallback:
    """OpenClaw 离线回退适配器"""

    def __init__(self):
        self._llm = None
        self._health = None

    @property
    def llm(self):
        if self._llm is None:
            from core.local_llm import chat, health
            self._llm = chat
            self._health = health
        return self._llm

    def health(self) -> dict:
        return self._health() if self._health else {"status": "uninitialized"}

    def query(self, prompt: str) -> Tuple[str, str]:
        """统一查询入口，返回 (响应, 来源)"""
        return self.llm(prompt)

    def is_offline(self) -> bool:
        """检查是否完全离线（Ollama + Cloud 都不可用）"""
        h = self.health()
        return not h.get("ollama_alive", False) and not h.get("internet", False)


# CLI
if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    fb = OpenClawFallback()

    if "--health" in sys.argv:
        print(json.dumps(fb.health(), indent=2, ensure_ascii=False))
    elif "--poll" in sys.argv:
        # 心跳用：检查离线状态
        offline = fb.is_offline()
        h = fb.health()
        status = "OFFLINE" if offline else "ONLINE"
        print(f"[openclaw_fb] {status} | ollama={h.get('ollama_alive')} | net={h.get('internet')} | offline_engine={h.get('offline_engine')}")
    else:
        prompt = sys.argv[1] if len(sys.argv) > 1 else "你好"
        text, src = fb.query(prompt)
        print(f"[{src}] {text}")
