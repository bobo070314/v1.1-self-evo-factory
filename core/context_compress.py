#!/usr/bin/env python3
"""Token compression - context headroom manager for qwen3.5:2b 3GB VRAM"""
import re
from typing import List, Dict

# Context thresholds (qwen3.5:2b ~3GB VRAM)
MAX_TOKENS = 25000  # Context window limit
HEADROOM = 2000     # Keep headroom for response

def compress_context(memories: List[Dict], current_tokens: int) -> List[Dict]:
    """Remove low-value memories to stay under token limit."""
    if current_tokens <= (MAX_TOKENS - HEADROOM):
        return memories
    
    # Sort by score (descending), keep top
    sorted_mems = sorted(memories, key=lambda m: m.get("score", 0), reverse=True)
    
    # Remove lowest scores until under limit
    while current_tokens > (MAX_TOKENS - HEADROOM * 2) and sorted_mems:
        removed = sorted_mems.pop()
        current_tokens -= len(removed.get("text", "")) // 4
    
    return sorted_mems

def truncate_output(text: str, max_tokens: int = 15000) -> str:
    """Hard truncate if exceeding limit."""
    tokens = len(text) // 4
    if tokens > max_tokens:
        return text[:max_tokens * 4]
    return text