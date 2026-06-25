#!/usr/bin/env python3
"""core/retriever_agent.py - Small model (qwen3.5:2b) as retrieval agent

Every user message hits this first:
1. Semantic recall via Ollama (cheap, local, fast-ish)
2. Rerank by memory_type weight (CORRECTIONS=1.0 always wins)
3. Return Top-5 fragments
4. The big model (DeepSeek) only thinks, never searches

This saves ~30% API tokens per request.
"""

import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Optional

import requests

from memory_types import MemoryFragment, MemoryClass, MEMORY_WEIGHTS

UTC = timezone.utc
BASE_DIR = Path(__file__).resolve().parent.parent
MEMORY_STORE = BASE_DIR / "data" / "memory_store.jsonl"

OLLAMA_URL = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11634")
OLLAMA_MODEL = os.environ.get("OLLAMA_RETRIEVER_MODEL", "qwen3.5:2b")
RETRIEVER_TIMEOUT = int(os.environ.get("RETRIEVER_TIMEOUT", "90"))


class RetrieverAgent:
    """Small-model retrieval. Cheap, always-on. DeepSeek never touches the index."""

    def __init__(self, store_path: Optional[Path] = None):
        self.store_path = store_path or MEMORY_STORE
        self._cache: List[MemoryFragment] = []
        self._cache_loaded = False

    # ---- Load all fragments from disk ----
    def _load_store(self) -> List[MemoryFragment]:
        if self._cache_loaded and self._cache:
            return self._cache

        fragments = []
        if self.store_path.exists():
            with open(self.store_path, "r", encoding="utf-8", errors="replace") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        d = json.loads(line)
                        fragments.append(MemoryFragment.from_dict(d))
                    except (json.JSONDecodeError, KeyError):
                        pass
        self._cache = fragments
        self._cache_loaded = True
        return fragments

    def reload(self):
        """Force reload from disk."""
        self._cache_loaded = False
        self._cache = []
        return self._load_store()

    # ---- Semantic recall via Ollama ----
    def _semantic_recall(self, query: str, candidates: List[MemoryFragment]) -> List[MemoryFragment]:
        """Ask qwen3.5:2b which fragments are relevant. Returns scored candidates."""
        if not candidates:
            return []

        # Build prompt: "here are N memories, which ones match this query?"
        candidate_texts = []
        for i, frag in enumerate(candidates):
            candidate_texts.append(f"{i}. [{frag.memory_class.value}] {frag.text[:200]}")

        prompt = (
            f"You are a memory retrieval assistant. Given a user query, select the MOST RELEVANT "
            f"memory fragments from the list below. Return ONLY a JSON array of indices (e.g. [0, 3, 7]).\n\n"
            f"USER QUERY: {query}\n\n"
            f"MEMORY FRAGMENTS:\n" + "\n".join(candidate_texts) +
            f"\n\nReturn ONLY a JSON array of the most relevant indices. Max 10 indices."
        )

        try:
            resp = requests.post(
                f"{OLLAMA_URL}/api/generate",
                json={
                    "model": OLLAMA_MODEL,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "num_predict": 100,
                        "temperature": 0.1,
                    },
                },
                timeout=RETRIEVER_TIMEOUT,
            )
            resp.raise_for_status()
            body = resp.json()

            # qwen3.5 may put answer in 'response' or 'thinking'
            answer = body.get("response", "") or body.get("thinking", "")

            # Extract JSON array from response
            match = re.search(r"\[[\d,\s]+\]", answer)
            if match:
                indices = json.loads(match.group())
                return [candidates[i] for i in indices if 0 <= i < len(candidates)]

        except (requests.RequestException, json.JSONDecodeError, KeyError) as e:
            pass  # Fall back to BM25 below

        # If Ollama failed, do simple keyword overlap as fallback
        return self._keyword_fallback(query, candidates)

    @staticmethod
    def _keyword_fallback(query: str, candidates: List[MemoryFragment]) -> List[MemoryFragment]:
        """Simple overlap scoring when Ollama is down."""
        query_lower = query.lower()
        scored = []
        for frag in candidates:
            text_lower = frag.text.lower()
            # Count overlapping words
            score = sum(1 for w in query_lower.split() if w in text_lower)
            if score > 0:
                scored.append((score, frag))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [f for _, f in scored[:10]]

    # ---- Rerank: combine semantic score + memory weight (corrections=1.0 always wins) ----
    def _rerank(self, fragments: List[MemoryFragment]) -> List[MemoryFragment]:
        """Sort by: memory_class weight (desc), then relevance (implicit from order)."""
        # Group by class weight
        return sorted(fragments, key=lambda f: MEMORY_WEIGHTS.get(f.memory_class, 0.5), reverse=True)

    # ---- Main API: retrieve ----
    def retrieve(self, query: str, top_k: int = 5) -> List[MemoryFragment]:
        """Main entry point. Returns Top-K most relevant memories."""
        all_fragments = self._load_store()
        if not all_fragments:
            return []

        # Phase 1: Semantic recall (or keyword fallback)
        recalled = self._semantic_recall(query, all_fragments)

        # Phase 2: Rerank by weight (corrections first)
        reranked = self._rerank(recalled)

        return reranked[:top_k]

    # ---- Format as context string for DeepSeek ----
    def retrieve_as_context(self, query: str, top_k: int = 5) -> str:
        """Retrieve and format as context string ready for injection into DeepSeek prompt."""
        fragments = self.retrieve(query, top_k)
        if not fragments:
            return ""

        lines = ["[RELEVANT MEMORIES]", ""]
        for frag in fragments:
            label = frag.memory_class.value.upper()
            lines.append(f"[{label}] {frag.text[:300]}")

        return "\n".join(lines)

    # ---- Health check ----
    def health(self) -> Dict:
        fragments = self._load_store()
        class_counts = {}
        for f in fragments:
            class_counts[f.memory_class.value] = class_counts.get(f.memory_class.value, 0) + 1

        ol_status = "unknown"
        try:
            r = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
            ol_status = "ok" if r.status_code == 200 else f"http_{r.status_code}"
        except Exception:
            ol_status = "unreachable"

        return {
            "total_fragments": len(fragments),
            "class_distribution": class_counts,
            "ollama_status": ol_status,
            "ollama_model": OLLAMA_MODEL,
            "store_path": str(self.store_path),
        }


# ---- Singleton ----
_retriever: Optional[RetrieverAgent] = None


def get_retriever() -> RetrieverAgent:
    global _retriever
    if _retriever is None:
        _retriever = RetrieverAgent()
    return _retriever


# ---- CLI ----
if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser(description="Small-model memory retriever (qwen3.5:2b)")
    p.add_argument("query", nargs="?", help="Query to retrieve memories for")
    p.add_argument("--top", type=int, default=5, help="Number of results")
    p.add_argument("--health", action="store_true", help="Health check")
    p.add_argument("--json", action="store_true")
    args = p.parse_args()

    if args.health:
        r = get_retriever()
        result = r.health()
        if args.json:
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            print(f"Fragments: {result['total_fragments']}")
            print(f"Distribution: {result['class_distribution']}")
            print(f"Ollama: {result['ollama_status']}")
        sys.exit(0)

    if args.query:
        r = get_retriever()
        context = r.retrieve_as_context(args.query, args.top)
        if args.json:
            fragments = r.retrieve(args.query, args.top)
            print(json.dumps([f.to_dict() for f in fragments], indent=2, ensure_ascii=False))
        else:
            print(context)
        sys.exit(0)

    sys.exit(0)
