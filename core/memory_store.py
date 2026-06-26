#!/usr/bin/env python3
"""
core/memory_store.py — 记忆持久化存储 (v1.0)
==========================================
SQLite 持久化，支持记忆分级（hot/warm/cold）、自动压缩和摘要。

设计：
- SQLite 替代 JSONL，支持随机存取和查询
- 记忆分级：hot (最近7天)、warm (30天)、cold (>30天)
- 自动压缩：cold 记忆自动摘要压缩节省空间
- 四种记忆类型有各自的存储策略
- 检索时按权重 + 时效性排序
"""

import json
import os
import re
import sqlite3
import sys
import threading
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional, Dict, List, Any, Tuple

try:
    from core.memory_types import MemoryClass, MemoryFragment, EXTRACT_TRIGGERS
except ImportError:
    from memory_types import MemoryClass, MemoryFragment, EXTRACT_TRIGGERS

TZ = timezone(timedelta(hours=8))
BASE = Path(__file__).resolve().parent.parent
DB_PATH = BASE / "data" / "memory_store.db"

# 记忆分级阈值（天）
TIER_HOT_DAYS = 7
TIER_WARM_DAYS = 30

# 压缩策略
COMPRESS_AFTER_DAYS = 30
COMPRESS_MAX_CHARS = 200


class MemoryStore:
    """
    SQLite 持久化记忆存储。线程安全。"""

    _lock = threading.Lock()
    _instance = None

    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._db_path = str(DB_PATH)
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
        self._store_count = 0
        self._lock = threading.Lock()

    def _init_db(self):
        with self._get_conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS memories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    content TEXT NOT NULL,
                    memory_class TEXT NOT NULL,
                    source TEXT DEFAULT '',
                    tags TEXT DEFAULT '[]',
                    timestamp TEXT NOT NULL,
                    weight REAL DEFAULT 1.0,
                    compressed INTEGER DEFAULT 0,
                    parent_id INTEGER DEFAULT NULL,
                    created_at TEXT DEFAULT (datetime('now'))
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_memories_class ON memories(memory_class)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_memories_timestamp ON memories(timestamp)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_memories_source ON memories(source)")
            # 全文搜索
            try:
                conn.execute("CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts USING fts5(content, memory_class, tags, content=memories, content_rowid=id)")
            except Exception:
                pass  # FTS5 不可用时不建

    def _get_conn(self):
        conn = sqlite3.connect(self._db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def store(self, fragment: MemoryFragment) -> int:
        """存入一条记忆，返回 id"""
        with self._lock:
            with self._get_conn() as conn:
                tags_json = json.dumps(fragment.get("tags", []), ensure_ascii=False)
                weight = fragment.get("weight", MemoryClass.get_weight(fragment.get("memory_class", "WHO_YOU_ARE")))
                ts = fragment.get("timestamp", datetime.now(UTC).isoformat())
                cur = conn.execute(
                    "INSERT INTO memories (content, memory_class, source, tags, timestamp, weight) VALUES (?, ?, ?, ?, ?, ?)",
                    (fragment.get("text", ""), fragment.get("memory_class", "UNKNOWN"),
                     fragment.get("source", ""), tags_json, ts, weight)
                )
                self._store_count += 1
                return cur.lastrowid

    def retrieve(self, query: str, top_k: int = 5, memory_class: Optional[str] = None) -> List[Dict]:
        """检索记忆。优先用 FTS5 全文搜索，回退到 LIKE"""
        results = []

        # 尝试 FTS5
        try:
            with self._get_conn() as conn:
                if self._fts_available(conn):
                    sql = """
                        SELECT m.*, rank
                        FROM memories_fts
                        JOIN memories m ON memories_fts.rowid = m.id
                        WHERE memories_fts MATCH ?
                    """
                    params = [self._fts_query(query)]
                    if memory_class:
                        sql += " AND m.memory_class = ?"
                        params.append(memory_class)
                    sql += " ORDER BY rank LIMIT ?"
                    params.append(top_k * 2)  # 多拿一些再做权重排序
                    rows = conn.execute(sql, params).fetchall()
                    results = [dict(r) for r in rows]
        except Exception:
            pass

        # 回退 LIKE
        if not results:
            with self._get_conn() as conn:
                terms = re.findall(r'[\w\u4e00-\u9fff]+', query)[:5]
                conditions = []
                params = []
                for t in terms:
                    conditions.append("content LIKE ?")
                    params.append(f"%{t}%")
                if memory_class:
                    conditions.append("memory_class = ?")
                    params.append(memory_class)
                if conditions:
                    sql = f"SELECT * FROM memories WHERE {' AND '.join(conditions)} ORDER BY weight DESC, timestamp DESC LIMIT ?"
                    params.append(top_k * 2)
                    rows = conn.execute(sql, params).fetchall()
                    results = [dict(r) for r in rows]

        # 权重排序：corrections 永远优先
        results.sort(key=lambda r: (
            -(r.get("weight", 1.0) if r.get("memory_class") == "CORRECTIONS" else r.get("weight", 0.5)),
            -self._parse_ts(r.get("timestamp", ""))
        ))

        return results[:top_k]

    def _fts_available(self, conn) -> bool:
        try:
            conn.execute("SELECT count(*) FROM memories_fts")
            return True
        except Exception:
            return False

    @staticmethod
    def _fts_query(text: str) -> str:
        """将中文/英文查询转为 FTS5 查询"""
        # 对中文，直接用 OR 连接（FTS5 支持中文分词的 OR）
        terms = re.findall(r'[\w\u4e00-\u9fff]+', text)
        if not terms:
            return text
        return " OR ".join(f'"{t}"' for t in terms[:5])

    @staticmethod
    def _parse_ts(ts: str) -> float:
        try:
            dt = datetime.fromisoformat(ts)
            return dt.timestamp()
        except Exception:
            return 0

    def get_stats(self) -> Dict:
        with self._get_conn() as conn:
            total = conn.execute("SELECT count(*) FROM memories").fetchone()[0]
            by_class = {}
            for r in conn.execute("SELECT memory_class, count(*) as cnt FROM memories GROUP BY memory_class").fetchall():
                by_class[r["memory_class"]] = r["cnt"]
            return {
                "total": total,
                "by_class": by_class,
                "db_path": self._db_path,
                "store_count": self._store_count,
            }

    def cleanup(self):
        """压缩 cold 记忆"""
        cutoff = (datetime.now(TZ) - timedelta(days=COMPRESS_AFTER_DAYS)).isoformat()
        with self._get_conn() as conn:
            cold = conn.execute(
                "SELECT id, content FROM memories WHERE timestamp < ? AND compressed = 0",
                (cutoff,)
            ).fetchall()
            for row in cold:
                compressed = row["content"][:COMPRESS_MAX_CHARS]
                if len(compressed) < len(row["content"]):
                    conn.execute(
                        "UPDATE memories SET content = ?, compressed = 1 WHERE id = ?",
                        (compressed, row["id"])
                    )


# Singleton
_store: Optional[MemoryStore] = None


def get_store() -> MemoryStore:
    global _store
    if _store is None:
        _store = MemoryStore()
    return _store

    def record_reward(self, action: str, reward: float, metadata: Dict = None):
        """记录奖惩（RL 风格）"""
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action": action,
            "reward": reward,
            "metadata": metadata or {},
        }
        self._rewards.append(entry)
        self._save_rewards()

    def get_avg_reward(self, action: str) -> float:
        """获取平均奖惩"""
        rewards = [e["reward"] for e in self._rewards if e["action"] == action]
        return sum(rewards) / len(rewards) if rewards else 0.0

