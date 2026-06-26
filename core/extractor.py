#!/usr/bin/env python3
"""core/extractor.py - Background memory extractor (v2.0)
========================================================
升级：
- 新增对话提取（从 OpenClaw 的 message log 提取）
- 记忆持久化到 SQLite（代替 JSONL）
- 四种记忆类型差异化提取策略
- 后台 daemon 同时监控 log + 对话
- 自动去重 + 上下文提取

Claude Code 51 万行启示：提取不是扫文件，是持续的"听讲"。
"""

import os
import re
import sys
import time
import json
import threading
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional, List, Callable, Dict

try:
    from core.memory_types import MemoryFragment, MemoryClass, EXTRACT_TRIGGERS
except ImportError:
    from memory_types import MemoryFragment, MemoryClass, EXTRACT_TRIGGERS

try:
    from core.memory_store import get_store
except ImportError:
    get_store = None

UTC = timezone.utc
TZ = timezone(timedelta(hours=8))

BASE_DIR = Path(__file__).resolve().parent.parent
MEMORY_STORE = BASE_DIR / "data" / "memory_store.jsonl"  # fallback
OBSERVE_LOG = BASE_DIR / "data" / "openclaw.log"
CHAT_LOG_DIR = Path(os.environ.get("OPENCLAW_CHAT_DIR", str(BASE_DIR / "data" / "chats")))

POLL_INTERVAL_S = 10
MAX_TRANSCRIPT_FILES = 10


class MemoryExtractor:
    """Daemon 线程：从日志 + 对话中自动提取并存储记忆。

    提取策略（四种记忆类型的差异化处理）：
    - WHO_YOU_ARE: "我喜欢/我是" 等身份声明 → 高权重存储
    - CORRECTIONS: "不要用/改成" 等更正 → 立即存储，最高权重
    - PROJECT_STATE: "项目是/当前状态" 等 → 附带时间戳
    - RESOURCES: "这里有文档/代码在" → 存入链接和路径
    """

    def __init__(self):
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._extracted_count = 0
        self._log_position = 0
        self._chat_position = {}  # 按文件追踪
        self._seen_hashes: set = set()
        self._store = get_store() if get_store else None

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True, name="MemoryExtractor")
        self._thread.start()

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)

    @property
    def extracted_count(self) -> int:
        return self._extracted_count

    def enqueue(self, fragment: Dict) -> bool:
        """外部写入记忆（orchestrator 调用）"""
        try:
            mf = MemoryFragment(
                text=fragment.get("text", ""),
                memory_class=fragment.get("memory_class", "UNKNOWN"),
                source=fragment.get("source", "manual"),
                tags=fragment.get("tags", []),
            )
            if isinstance(fragment, dict) and "timestamp" in fragment:
                mf.timestamp = fragment["timestamp"]
            else:
                mf.timestamp = datetime.now(UTC).isoformat()
            self._store_memory(mf)
            return True
        except Exception:
            return False

    def _loop(self):
        while self._running:
            try:
                self._scan_logs()
                self._scan_chat_logs()
            except Exception:
                pass
            time.sleep(POLL_INTERVAL_S)

    def _scan_logs(self):
        """扫描 openclaw.log"""
        if not OBSERVE_LOG.exists():
            return
        try:
            with open(OBSERVE_LOG, "r", encoding="utf-8", errors="replace") as f:
                f.seek(self._log_position)
                text = f.read()
                if text:
                    self._extract_from_text(text, "openclaw.log")
                    self._log_position = f.tell()
        except Exception:
            pass

    def _scan_chat_logs(self):
        """扫描聊天对话文件"""
        if not CHAT_LOG_DIR.exists():
            return
        try:
            files = sorted(CHAT_LOG_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)[:MAX_TRANSCRIPT_FILES]
            files += sorted(CHAT_LOG_DIR.glob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)[:MAX_TRANSCRIPT_FILES]
            for fp in files:
                last_pos = self._chat_position.get(str(fp), 0)
                if os.path.getsize(fp) <= last_pos:
                    continue
                try:
                    with open(fp, "r", encoding="utf-8", errors="replace") as f:
                        f.seek(last_pos)
                        for line in f:
                            line = line.strip()
                            if not line:
                                continue
                            try:
                                msg = json.loads(line)
                            except json.JSONDecodeError:
                                continue
                            # 提取用户消息（不是 AI 消息）
                            role = msg.get("role", "") or msg.get("from", "") or ""
                            if role not in ("assistant", "ai", "bot", "claw"):
                                content = msg.get("content", msg.get("text", msg.get("message", "")))
                                if content and len(content) > 5:
                                    self._extract_from_text(content, f"chat:{fp.name}")
                        self._chat_position[str(fp)] = f.tell()
                except Exception:
                    pass
        except Exception:
            pass

    
    # ── 记忆压缩（Claude Code 风格）────────────────────────────────────
    def _should_store_fragment(self, fragment: MemoryFragment) -> bool:
        """压缩策略：超过阈值跳过模糊内容，优先 CORRECTIONS/WHO_YOU_ARE"""
        # 长度检查
        if len(fragment.text) > 2000:
            return False
        # 质量检查：跳过模糊内容
        fuzzy_words = ["todo", "待优化", "考虑", "可能", "大概"]
        if any(w in fragment.text.lower() for w in fuzzy_words):
            return False
        return True

def _extract_from_text(self, text: str, source: str):
        """应用触发词正则，记忆提取"""
        for pattern, mem_class in EXTRACT_TRIGGERS:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                start = max(0, match.start() - 50)
                end = min(len(text), match.end() + 100)
                context = text[start:end].strip()

                content_hash = hash(context)
                if content_hash in self._seen_hashes:
                    continue
                self._seen_hashes.add(content_hash)

                # 保持 seen hash 不无限增长
                if len(self._seen_hashes) > 10000:
                    self._seen_hashes = set(list(self._seen_hashes)[-5000:])

                fragment = MemoryFragment(
                    text=context,
                    memory_class=mem_class,
                    source=source,
                    tags=[source, mem_class.value],
                )
                fragment.timestamp = datetime.now(UTC).isoformat()

                self._store_memory(fragment)
                self._extracted_count += 1

        # 额外：提取明显的偏好声明（即使不在 EXTRACT_TRIGGERS 里）
        self._extract_preferences(text, source)

    def _extract_preferences(self, text: str, source: str):
        """额外的偏好提取：我喜欢/习惯/不喜欢等"""
        pref_patterns = [
            (r"我[很喜欢爱用](.*?)[。，,.!]", "WHO_YOU_ARE"),
            (r"我习惯(.*?)[。，,.!]", "WHO_YOU_ARE"),
            (r"我不[喜欢爱用](.*?)[。，,.!]", "CORRECTIONS"),
            (r"(?:不要|别用|别[再用])(.*?)[。，,.!]", "CORRECTIONS"),
            (r"帮我记[住录一下](.*?)[。，,.!]", "WHO_YOU_ARE"),
        ]
        for pattern, mem_class in pref_patterns:
            for match in re.finditer(pattern, text):
                content = match.group(0).strip()
                content_hash = hash(content + "pref")
                if content_hash in self._seen_hashes:
                    continue
                self._seen_hashes.add(content_hash)
                fragment = MemoryFragment(
                    text=content,
                    memory_class=MemoryClass[mem_class],
                    source=source,
                    tags=[source, "preference"],
                )
                fragment.timestamp = datetime.now(UTC).isoformat()
                self._store_memory(fragment)
                self._extracted_count += 1

    def _store_memory(self, fragment):
        """存储记忆（优先 SQLite，回退 JSONL）"""
        if self._store:
            try:
                self._store.store(fragment.to_dict() if hasattr(fragment, 'to_dict') else fragment)
                return
            except Exception:
                pass
        # fallback: JSONL
        MEMORY_STORE.parent.mkdir(parents=True, exist_ok=True)
        with open(MEMORY_STORE, "a", encoding="utf-8") as f:
            d = fragment.to_dict() if hasattr(fragment, 'to_dict') else fragment
            f.write(json.dumps(d, ensure_ascii=False) + "\n")


# ---- Singleton ----
_extractor: Optional[MemoryExtractor] = None


def get_extractor() -> MemoryExtractor:
    global _extractor
    if _extractor is None:
        _extractor = MemoryExtractor()
    return _extractor


def stop_extractor():
    global _extractor
    if _extractor:
        _extractor.stop()
        _extractor = None


# ---- CLI ----
if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--start", action="store_true")
    p.add_argument("--status", action="store_true")
    p.add_argument("--json", action="store_true")
    args = p.parse_args()

    if args.status:
        ext = get_extractor()
        out = {"running": ext._running, "extracted": ext.extracted_count}
        print(json.dumps(out, indent=2, ensure_ascii=False) if args.json else f"Running: {out['running']}, Extracted: {out['extracted']}")
        sys.exit(0)

    if args.start:
        ext = get_extractor()
        ext.start()
        print(f"[extractor] Started (10s interval)")
        try:
            while True:
                time.sleep(10)
        except KeyboardInterrupt:
            ext.stop()

    sys.exit(0)
