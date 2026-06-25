# -*- coding: utf-8 -*-
"""
本地向量存储（离线语义搜索）
纯 Python 实现，零外部依赖，零网络。
用于三级回退 Level 2：纯本地向量检索。
"""
import json
import math
import os
import hashlib
from typing import List, Tuple


class LocalVectorStore:
    """简易向量存储 — 纯本地，零云端"""

    def __init__(self, storage_dir: str = None):
        self.storage_dir = storage_dir or os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "..", "data", "vectors"
        )
        os.makedirs(self.storage_dir, exist_ok=True)
        self.vectors: dict = {}      # id -> list[float]
        self.documents: dict = {}    # id -> text
        self._loaded = False

    @staticmethod
    def _digest(text: str) -> str:
        return hashlib.sha256(text.encode()).hexdigest()[:16]

    @staticmethod
    def _dot(a: list, b: list) -> float:
        return sum(x * y for x, y in zip(a, b))

    @staticmethod
    def _norm(v: list) -> float:
        return math.sqrt(sum(x * x for x in v)) or 1e-8

    @staticmethod
    def _cosine(a: list, b: list) -> float:
        return LocalVectorStore._dot(a, b) / (LocalVectorStore._norm(a) * LocalVectorStore._norm(b))

    def simple_embed(self, text: str, dim: int = 64) -> list:
        """
        简易"伪嵌入"：字符 n-gram 哈希 + 频率统计投影。
        纯 Python，零模型下载。
        """
        vec = [0.0] * dim
        seed = int(self._digest(text), 16) % (2**31)
        rng_state = seed

        # 字符频率投影
        freq = {}
        for ch in text:
            freq[ch] = freq.get(ch, 0) + 1
        for ch, cnt in freq.items():
            idx = ord(ch) % dim
            vec[idx] += cnt / max(len(text), 1)

        # 伪随机扰动（线性同余）
        for i in range(dim):
            rng_state = (rng_state * 1103515245 + 12345) & 0x7fffffff
            vec[i] += (rng_state / 0x7fffffff) * 0.01

        # 归一化
        n = self._norm(vec)
        return [v / n for v in vec]

    def add(self, texts: List[str]):
        for text in texts:
            doc_id = self._digest(text)
            if doc_id in self.vectors:
                continue
            self.vectors[doc_id] = self.simple_embed(text)
            self.documents[doc_id] = text

    def search(self, query: str, top_k: int = 5) -> List[Tuple[str, float]]:
        """返回 [(text, score)]"""
        if not self.vectors:
            return []
        q_vec = self.simple_embed(query)
        results = []
        for doc_id, vec in self.vectors.items():
            score = self._cosine(q_vec, vec)
            if score > 0:
                results.append((self.documents[doc_id], score))
        results.sort(key=lambda x: -x[1])
        return results[:top_k]

    def save(self):
        path = os.path.join(self.storage_dir, "store.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"documents": self.documents}, f, ensure_ascii=False)

    def load(self) -> bool:
        self._loaded = True
        path = os.path.join(self.storage_dir, "store.json")
        if not os.path.exists(path):
            return False
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        docs = list(data["documents"].values())
        self.add(docs)
        return True


# CLI test
if __name__ == "__main__":
    store = LocalVectorStore()
    docs = [
        "猫抓本地AI助手，离线大脑",
        "Ollama GPU推理，qwen3.5模型",
        "GitHub SSH push配置",
        "React Tailwind前端项目",
        "Python subprocess Windows坑点",
    ]
    store.add(docs)

    import sys
    q = sys.argv[1] if len(sys.argv) > 1 else "AI助手"
    results = store.search(q)
    for text, score in results:
        print(f"  [{score:.3f}] {text}")
