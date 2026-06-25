# -*- coding: utf-8 -*-
"""
BM25 关键词检索（离线全文搜索）
纯 Python 实现，不依赖 numpy/scipy，不依赖网络。
用于三级回退 Level 2 的 fallback：无向量库时的文档检索。
"""

import re
import math
from collections import defaultdict
from typing import List, Tuple


class BM25Fallback:
    """轻量 BM25，纯 Python，零依赖"""

    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.documents: List[str] = []
        self.doc_tokens: List[List[str]] = []
        self.doc_len: List[int] = []
        self.avgdl: float = 0
        self.idf: dict = {}
        self._tokenized = False

    @staticmethod
    def tokenize(text: str) -> List[str]:
        """中文+英文混合分词"""
        # 中文按字切，英文按空格
        tokens = []
        for chunk in re.split(r'([a-zA-Z0-9]+)', text.lower()):
            chunk = chunk.strip()
            if not chunk:
                continue
            if re.match(r'[a-zA-Z0-9]+', chunk):
                tokens.append(chunk)
            else:
                tokens.extend(ch for ch in chunk if not ch.isspace())
        return tokens

    def index(self, documents: List[str]):
        """索引文档集合"""
        self.documents = list(documents)
        self.doc_tokens = [self.tokenize(d) for d in self.documents]
        self.doc_len = [len(t) for t in self.doc_tokens]
        self.avgdl = sum(self.doc_len) / max(len(self.doc_len), 1)

        # IDF
        N = len(self.documents)
        df = defaultdict(int)
        for tokens in self.doc_tokens:
            for token in set(tokens):
                df[token] += 1
        self.idf = {
            t: math.log(1 + (N - f + 0.5) / (f + 0.5))
            for t, f in df.items()
        }
        self._tokenized = True

    def search(self, query: str, top_k: int = 5) -> List[Tuple[int, float, str]]:
        """返回 [(索引, 分数, 文档)]"""
        if not self._tokenized:
            raise RuntimeError("请先 index()")

        q_tokens = self.tokenize(query)
        scores = []

        for i, doc_tokens in enumerate(self.doc_tokens):
            score = 0.0
            doc_len = self.doc_len[i]
            tf = defaultdict(int)
            for t in doc_tokens:
                tf[t] += 1

            for q in q_tokens:
                if q not in self.idf:
                    continue
                f = tf.get(q, 0)
                idf_val = self.idf[q]
                numerator = f * (self.k1 + 1)
                denominator = f + self.k1 * (1 - self.b + self.b * doc_len / self.avgdl)
                score += idf_val * numerator / max(denominator, 0.001)

            if score > 0:
                scores.append((i, score, self.documents[i]))

        scores.sort(key=lambda x: -x[1])
        return scores[:top_k]


# CLI test
if __name__ == "__main__":
    docs = [
        "猫抓是一个本地AI工作伙伴，专门帮助用户进行前端开发和全栈编程。",
        "Ollama是一个本地大语言模型运行框架，支持GPU推理。",
        "GitHub是全球最大的代码托管平台，支持Git版本控制。",
        "DeepSeek是一个强大的中文大语言模型，具有优秀的代码能力。",
        "离线规则引擎可以在没有网络和LLM的情况下处理简单的查询。",
    ]
    bm = BM25Fallback()
    bm.index(docs)

    import sys
    q = sys.argv[1] if len(sys.argv) > 1 else "什么是猫抓"
    results = bm.search(q)
    for idx, score, doc in results:
        print(f"  [{idx}] score={score:.3f} | {doc[:60]}")
