#!/usr/bin/env python3
"""core/extractor.py - Background memory extractor

Listens to conversation logs and extracts implicit memory signals.
Runs in a daemon thread. You never notice it working.
Pattern: "I like X" -> WHO_YOU_ARE, "don't use X" -> CORRECTIONS, etc.
"""

import os
import re
import sys
import time
import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List, Callable

try:
    from memory_types import MemoryFragment, MemoryClass, EXTRACT_TRIGGERS
except ImportError:
    from core.memory_types import MemoryFragment, MemoryClass, EXTRACT_TRIGGERS

UTC = timezone.utc
TZ = timezone(__import__("datetime").timedelta(hours=8))

BASE_DIR = Path(__file__).resolve().parent.parent
MEMORY_STORE = BASE_DIR / "data" / "memory_store.jsonl"
OBSERVE_LOG = BASE_DIR / "data" / "openclaw.log"  # Primary watch target

# Fallback: also watch conversation transcript if available
TRANSCRIPT_DIR = Path(os.environ.get("OPENCLAW_TRANSCRIPT_DIR", str(BASE_DIR / "data")))

POLL_INTERVAL_S = 10  # Every 10 seconds


class MemoryExtractor:
    """Daemon thread that watches logs and auto-extracts memories."""

    def __init__(self, on_memory: Optional[Callable] = None):
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._extracted_count = 0
        self._last_position = 0
        self._on_memory = on_memory or self._default_store
        self._seen_hashes: set = set()  # Dedup by content hash

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

    def _loop(self):
        while self._running:
            try:
                self._scan_logs()
            except Exception:
                pass
            time.sleep(POLL_INTERVAL_S)

    def _scan_logs(self):
        """Scan observed log file and transcripts for memory signals."""
        sources = []

        # Main log file
        if OBSERVE_LOG.exists():
            with open(OBSERVE_LOG, "r", encoding="utf-8", errors="replace") as f:
                f.seek(self._last_position)
                text = f.read()
                if text:
                    sources.append(("openclaw.log", text))

        # Transcript files (last 5)
        if TRANSCRIPT_DIR.exists():
            transcripts = sorted(TRANSCRIPT_DIR.glob("*.txt"), key=lambda p: p.stat().st_mtime, reverse=True)[:5]
            for tp in transcripts:
                try:
                    content = tp.read_text(encoding="utf-8", errors="replace")
                    sources.append((tp.name, content))
                except Exception:
                    pass

        for source_name, text in sources:
            self._extract_from_text(text, source_name)

    def _extract_from_text(self, text: str, source: str):
        """Apply trigger regexes and create MemoryFragments."""
        for pattern, mem_class in EXTRACT_TRIGGERS:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                # Capture surrounding context (50 chars before, 100 after)
                start = max(0, match.start() - 50)
                end = min(len(text), match.end() + 100)
                context = text[start:end].strip()

                # Dedup by text hash
                content_hash = hash(context)
                if content_hash in self._seen_hashes:
                    continue
                self._seen_hashes.add(content_hash)

                fragment = MemoryFragment(
                    text=context,
                    memory_class=mem_class,
                    source=f"extractor:{source}",
                    tags=[source, mem_class.value],
                )
                fragment.timestamp = datetime.now(UTC).isoformat()

                self._on_memory(fragment)
                self._extracted_count += 1

    @staticmethod
    def _default_store(fragment: MemoryFragment) -> None:
        """Default: append to JSONL store."""
        MEMORY_STORE.parent.mkdir(parents=True, exist_ok=True)
        with open(MEMORY_STORE, "a", encoding="utf-8") as f:
            f.write(json.dumps(fragment.to_dict(), ensure_ascii=False) + "\n")


# ---- Singleton ----
_extractor: Optional[MemoryExtractor] = None


def get_extractor() -> MemoryExtractor:
    global _extractor
    if _extractor is None:
        _extractor = MemoryExtractor()
        _extractor.start()
    return _extractor


def stop_extractor():
    global _extractor
    if _extractor:
        _extractor.stop()
        _extractor = None


# ---- CLI ----
if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser(description="Background memory extractor daemon")
    p.add_argument("--start", action="store_true", help="Start the extractor daemon")
    p.add_argument("--status", action="store_true", help="Show status")
    p.add_argument("--json", action="store_true")
    args = p.parse_args()

    if args.status:
        ext = get_extractor()
        out = {
            "running": ext._running,
            "extracted_count": ext.extracted_count,
            "poll_interval_s": POLL_INTERVAL_S,
            "watch_log": str(OBSERVE_LOG),
            "store": str(MEMORY_STORE),
        }
        if args.json:
            print(json.dumps(out, indent=2, ensure_ascii=False))
        else:
            print(f"Extractor running: {out['running']}")
            print(f"Memories extracted: {out['extracted_count']}")
        sys.exit(0)

    if args.start:
        ext = get_extractor()
        print(f"[extractor] Started daemon thread (interval={POLL_INTERVAL_S}s)")
        print(f"[extractor] Watching: {OBSERVE_LOG}")
        try:
            while True:
                time.sleep(10)
                if ext.extracted_count > 0:
                    print(f"[extractor] Extracted {ext.extracted_count} memories so far")
        except KeyboardInterrupt:
            stop_extractor()
            print("[extractor] Stopped")

    import sys
    sys.exit(0)
