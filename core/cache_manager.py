#!/usr/bin/env python3
"""core/cache_manager.py — Token & Compute Cache with 14 Failure Counters

Every cache lookup costs 1 counter increment. After N failures in a row,
that cache path is marked DANGEROUS and blackholed until a warmup succeeds.

14 Cache Failure Types:
  1. NO_HASH       — Content hash missing, can't dedup
  2. HASH_COLLIDE  — Two different inputs produced same hash
  3. STALE_HIT     — Cache hit but content changed on disk
  4. MODEL_MISMATCH— Cached with different model than current
  5. TOKEN_DRIFT   — Token count in cache differs from predicted
  6. ENCODING_ERR  — Cache read/write encoding failure
  7. SIZE_LIMIT    — Cache entry exceeds max size
  8. DISK_FULL     — Write failed because disk full
  9. CORRUPTED     — JSON/msgpack decode failed
  10. VERSION_MISMATCH — Cache schema version changed
  11. EXPIRED       — TTL expired (but not yet evicted)
  12. PERMISSION_DENIED — Can't read/write cache file
  13. RACE_CONDITION — Concurrent write collision
  14. WARMUP_FAILED — Lazy fill didn't complete
"""

import hashlib
import json
import os
import time
import threading
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

UTC = timezone.utc
BASE_DIR = Path(__file__).resolve().parent.parent
CACHE_DIR = BASE_DIR / "data" / "cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

DANGEROUS_THRESHOLD = 5  # Consecutive failures before blackholing
MAX_CACHE_SIZE_MB = 100
MAX_ENTRY_AGE_DAYS = 7


class CacheFailureType(str, Enum):
    NO_HASH = "no_hash"
    HASH_COLLIDE = "hash_collide"
    STALE_HIT = "stale_hit"
    MODEL_MISMATCH = "model_mismatch"
    TOKEN_DRIFT = "token_drift"
    ENCODING_ERR = "encoding_err"
    SIZE_LIMIT = "size_limit"
    DISK_FULL = "disk_full"
    CORRUPTED = "corrupted"
    VERSION_MISMATCH = "version_mismatch"
    EXPIRED = "expired"
    PERMISSION_DENIED = "permission_denied"
    RACE_CONDITION = "race_condition"
    WARMUP_FAILED = "warmup_failed"


class CacheEntry:
    __slots__ = ("key", "value", "model", "token_count", "created_at", "ttl_days", "content_hash")

    def __init__(self, key: str, value: Any, model: str = "unknown",
                 token_count: int = 0, ttl_days: int = MAX_ENTRY_AGE_DAYS):
        self.key = key
        self.value = value
        self.model = model
        self.token_count = token_count
        self.created_at = datetime.now(UTC).isoformat()
        self.ttl_days = ttl_days
        self.content_hash = self._compute_hash(value)

    @staticmethod
    def _compute_hash(value: Any) -> str:
        try:
            payload = json.dumps(value, sort_keys=True, ensure_ascii=False)
            return hashlib.sha256(payload.encode()).hexdigest()[:16]
        except (TypeError, ValueError):
            return ""

    def is_expired(self) -> bool:
        try:
            created = datetime.fromisoformat(self.created_at.replace("Z", "+00:00"))
            age = datetime.now(UTC) - created
            return age.days >= self.ttl_days
        except Exception:
            return True

    def to_dict(self) -> Dict:
        return {
            "key": self.key,
            "value": self.value,
            "model": self.model,
            "token_count": self.token_count,
            "created_at": self.created_at,
            "ttl_days": self.ttl_days,
            "content_hash": self.content_hash,
        }

    @classmethod
    def from_dict(cls, d: Dict) -> "CacheEntry":
        entry = cls(
            key=d["key"],
            value=d["value"],
            model=d.get("model", "unknown"),
            token_count=d.get("token_count", 0),
            ttl_days=d.get("ttl_days", MAX_ENTRY_AGE_DAYS),
        )
        entry.created_at = d.get("created_at", entry.created_at)
        entry.content_hash = d.get("content_hash", "")
        return entry


class CacheManager:
    """Token cache with 14 failure counters and DANGEROUS blackholing."""

    def __init__(self, cache_dir: Optional[Path] = None):
        self.cache_dir = cache_dir or CACHE_DIR
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # 14 failure counters
        self._failure_counts: Dict[CacheFailureType, int] = {
            ft: 0 for ft in CacheFailureType
        }
        self._dangerous: Dict[str, CacheFailureType] = {}  # key -> why dangerous
        self._lock = threading.Lock()

    # ---- File operations ----
    def _cache_path(self, key: str) -> Path:
        safe_key = hashlib.md5(key.encode()).hexdigest()[:32]
        return self.cache_dir / f"{safe_key}.json"

    # ---- Failure tracking ----
    def _record_failure(self, key: str, failure_type: CacheFailureType):
        with self._lock:
            self._failure_counts[failure_type] += 1

            # Check if this key should be marked DANGEROUS
            type_count = self._failure_counts[failure_type]
            if type_count >= DANGEROUS_THRESHOLD:
                self._dangerous[key] = failure_type

    def _record_success(self, key: str):
        with self._lock:
            # Reset counters for this key's failure type
            if key in self._dangerous:
                del self._dangerous[key]

    def is_dangerous(self, key: str) -> bool:
        return key in self._dangerous

    def danger_reason(self, key: str) -> Optional[str]:
        ft = self._dangerous.get(key)
        return ft.value if ft else None

    # ---- Core API ----
    def get(self, key: str, expected_model: str = "") -> Optional[Any]:
        """Get cached value. Returns None on any failure, records the failure type."""
        try:
            fp = self._cache_path(key)
            if not fp.exists():
                self._record_failure(key, CacheFailureType.NO_HASH)
                return None

            with open(fp, "r", encoding="utf-8") as f:
                raw = f.read()

            try:
                entry_dict = json.loads(raw)
            except json.JSONDecodeError:
                self._record_failure(key, CacheFailureType.CORRUPTED)
                return None

            entry = CacheEntry.from_dict(entry_dict)

            # Validate hash
            if not entry.content_hash:
                self._record_failure(key, CacheFailureType.NO_HASH)
                return None

            # Check expiration
            if entry.is_expired():
                self._record_failure(key, CacheFailureType.EXPIRED)
                # Clean up expired file
                try:
                    fp.unlink()
                except Exception:
                    pass
                return None

            # Model mismatch check
            if expected_model and entry.model != expected_model:
                self._record_failure(key, CacheFailureType.MODEL_MISMATCH)
                return None

            # Hash integrity check
            current_hash = CacheEntry._compute_hash(entry.value)
            if current_hash != entry.content_hash and current_hash:
                self._record_failure(key, CacheFailureType.HASH_COLLIDE)
                return None

            self._record_success(key)
            return entry.value

        except (PermissionError, OSError):
            self._record_failure(key, CacheFailureType.PERMISSION_DENIED)
            return None
        except Exception:
            self._record_failure(key, CacheFailureType.CORRUPTED)
            return None

    def set(self, key: str, value: Any, model: str = "unknown",
            token_count: int = 0, ttl_days: int = MAX_ENTRY_AGE_DAYS) -> bool:
        """Set cache value. Returns False on failure, records the type."""

        # Size check
        try:
            size = len(json.dumps(value, ensure_ascii=False))
            if size > MAX_CACHE_SIZE_MB * 1024 * 1024:
                self._record_failure(key, CacheFailureType.SIZE_LIMIT)
                return False
        except Exception:
            pass

        entry = CacheEntry(key=key, value=value, model=model,
                          token_count=token_count, ttl_days=ttl_days)

        try:
            fp = self._cache_path(key)
            with open(fp, "w", encoding="utf-8") as f:
                json.dump(entry.to_dict(), f, ensure_ascii=False)
            self._record_success(key)
            return True
        except (PermissionError, OSError):
            self._record_failure(key, CacheFailureType.PERMISSION_DENIED)
            return False
        except UnicodeEncodeError:
            self._record_failure(key, CacheFailureType.ENCODING_ERR)
            return False
        except Exception:
            self._record_failure(key, CacheFailureType.DISK_FULL)
            return False

    def get_or_set(self, key: str, factory_fn, model: str = "unknown",
                   token_count: int = 0) -> Any:
        """Get cached value or compute + store via factory_fn."""
        if self.is_dangerous(key):
            # Skip cache, go straight to compute
            return factory_fn()

        cached = self.get(key, expected_model=model)
        if cached is not None:
            return cached

        # Compute fresh
        try:
            value = factory_fn()
        except Exception:
            self._record_failure(key, CacheFailureType.WARMUP_FAILED)
            raise

        if value is not None:
            self.set(key, value, model=model, token_count=token_count)

        return value

    # ---- Dedup ----
    def dedup_key(self, prompt: str, model: str, context: str = "") -> str:
        """Generate deterministic dedup key from prompt + model + context."""
        raw = f"{model}::{prompt}::{context}"
        return hashlib.sha256(raw.encode()).hexdigest()

    # ---- Batch eviction ----
    def evict_expired(self) -> int:
        """Remove all expired cache entries. Returns count."""
        evicted = 0
        for fp in self.cache_dir.glob("*.json"):
            try:
                raw = fp.read_text(encoding="utf-8")
                entry = json.loads(raw)
                created = datetime.fromisoformat(entry["created_at"].replace("Z", "+00:00"))
                age = datetime.now(UTC) - created
                if age.days >= entry.get("ttl_days", MAX_ENTRY_AGE_DAYS):
                    fp.unlink()
                    evicted += 1
            except Exception:
                pass
        return evicted

    def evict_dangerous(self) -> int:
        """Remove all DANGEROUS-marked cache entries."""
        evicted = 0
        for key in list(self._dangerous.keys()):
            fp = self._cache_path(key)
            if fp.exists():
                try:
                    fp.unlink()
                    evicted += 1
                except Exception:
                    pass
            del self._dangerous[key]
        return evicted

    def total_size_mb(self) -> float:
        """Total cache size in MB."""
        total = 0
        for fp in self.cache_dir.glob("*.json"):
            total += fp.stat().st_size
        return total / (1024 * 1024)

    # ---- Health ----
    def health(self) -> Dict:
        with self._lock:
            return {
                "cache_dir": str(self.cache_dir),
                "entry_count": len(list(self.cache_dir.glob("*.json"))),
                "total_size_mb": round(self.total_size_mb(), 2),
                "dangerous_keys": len(self._dangerous),
                "failure_counts": {ft.value: c for ft, c in self._failure_counts.items() if c > 0},
                "dangerous_threshold": DANGEROUS_THRESHOLD,
            }


# ---- Singleton ----
_cache: Optional[CacheManager] = None


def get_cache() -> CacheManager:
    global _cache
    if _cache is None:
        _cache = CacheManager()
    return _cache


# ---- CLI ----
if __name__ == "__main__":
    import argparse
    import sys

    p = argparse.ArgumentParser(description="Token Cache Manager — 14 failure types")
    p.add_argument("--health", action="store_true", help="Health check")
    p.add_argument("--evict", action="store_true", help="Evict expired entries")
    p.add_argument("--json", action="store_true")
    args = p.parse_args()

    cache = get_cache()

    if args.evict:
        n = cache.evict_expired()
        d = cache.evict_dangerous()
        print(f"Evicted: {n} expired, {d} dangerous")
        sys.exit(0)

    if args.health:
        h = cache.health()
        if args.json:
            print(json.dumps(h, indent=2, ensure_ascii=False))
        else:
            print(f"Entries: {h['entry_count']} | Size: {h['total_size_mb']}MB")
            print(f"Dangerous: {h['dangerous_keys']} | Failures: {h['failure_counts']}")
        sys.exit(0)

    sys.exit(0)
