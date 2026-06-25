#!/usr/bin/env python3
"""core/memory_types.py - 4-class memory classification with weights

Claude Code equivalent: WHO_YOU_ARE / CORRECTIONS / PROJECT_STATE / RESOURCES
Each class has a fixed retrieval weight. Corrections dominate all other classes.
"""

from enum import Enum
from typing import Dict, Any

# ---- Memory classification enum ----
class MemoryClass(str, Enum):
    WHO_YOU_ARE = "who_you_are"      # User identity, preferences, style
    CORRECTIONS = "corrections"       # Fixes: "don't use animate-spin", "never rm -rf"
    PROJECT_STATE = "project_state"   # What we're building, current phase, open PRs
    RESOURCES = "resources"           # Docs, links, references, knowledge base

# ---- Fixed weights (corrections dominate) ----
MEMORY_WEIGHTS: Dict[MemoryClass, float] = {
    MemoryClass.CORRECTIONS:    1.0,   # Highest - user corrections ALWAYS surface first
    MemoryClass.WHO_YOU_ARE:    0.9,   # Identity/ preferences next
    MemoryClass.PROJECT_STATE:  0.7,   # What we're working on
    MemoryClass.RESOURCES:      0.5,   # Reference material, nice-to-have
}

# ---- Memory fragment schema ----
class MemoryFragment:
    """A single stored memory with classification and weight."""
    __slots__ = ("id", "text", "memory_class", "source", "timestamp", "tags")

    def __init__(self, text: str, memory_class: MemoryClass, source: str = "auto",
                 tags: list = None):
        self.text = text
        self.memory_class = memory_class
        self.source = source          # "extractor", "manual", "acceptance", "conversation"
        self.tags = tags or []
        self.timestamp = None          # Set on save
        self.id = None                 # Set on save

    def retrieval_weight(self) -> float:
        """Fixed weight for ranking. Corrections=1.0 always wins ties."""
        return MEMORY_WEIGHTS.get(self.memory_class, 0.5)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "text": self.text,
            "class": self.memory_class.value,
            "weight": self.retrieval_weight(),
            "source": self.source,
            "tags": self.tags,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "MemoryFragment":
        f = cls(
            text=d["text"],
            memory_class=MemoryClass(d["class"]),
            source=d.get("source", "auto"),
            tags=d.get("tags", []),
        )
        f.id = d.get("id")
        f.timestamp = d.get("timestamp")
        return f


# ---- Trigger keywords for background extraction ----
EXTRACT_TRIGGERS = [
    # Positive
    (r"我喜欢", MemoryClass.WHO_YOU_ARE),
    (r"我偏好", MemoryClass.WHO_YOU_ARE),
    (r"我习惯", MemoryClass.WHO_YOU_ARE),
    (r"我的技术栈", MemoryClass.WHO_YOU_ARE),
    # Corrections
    (r"错了", MemoryClass.CORRECTIONS),
    (r"不要再用", MemoryClass.CORRECTIONS),
    (r"重做", MemoryClass.CORRECTIONS),
    (r"永远不要", MemoryClass.CORRECTIONS),
    (r"别.*(?:用|写|改|删)", MemoryClass.CORRECTIONS),
    (r"记住.*教训", MemoryClass.CORRECTIONS),
    # Project state
    (r"当前项目", MemoryClass.PROJECT_STATE),
    (r"任务.*完成", MemoryClass.PROJECT_STATE),
    (r"PR.*合并", MemoryClass.PROJECT_STATE),
    (r"部署到", MemoryClass.PROJECT_STATE),
    (r"release", MemoryClass.PROJECT_STATE),
    # Resources
    (r"参考", MemoryClass.RESOURCES),
    (r"文档", MemoryClass.RESOURCES),
    (r"API.*地址", MemoryClass.RESOURCES),
    (r"配置.*路径", MemoryClass.RESOURCES),
]


if __name__ == "__main__":
    import argparse, json
    p = argparse.ArgumentParser(description="Memory type definitions")
    p.add_argument("--json", action="store_true")
    args = p.parse_args()

    out = {
        "classes": [c.value for c in MemoryClass],
        "weights": {k.value: v for k, v in MEMORY_WEIGHTS.items()},
        "trigger_count": len(EXTRACT_TRIGGERS),
        "version": "1.0.0",
    }
    if args.json:
        print(json.dumps(out, indent=2, ensure_ascii=False))
    else:
        print(f"Memory classes: {len(MemoryClass)}")
        print(f"Extract triggers: {len(EXTRACT_TRIGGERS)}")
