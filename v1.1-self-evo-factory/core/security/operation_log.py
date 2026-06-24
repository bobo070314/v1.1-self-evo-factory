"""操作日志 — 谁干了什么，可追溯

对标 Claude Code：完整操作审计链
- 每步操作记录：谁/什么/何时/结果
- Hash链确保不可篡改
- 支持回溯和复盘
"""

import hashlib
import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


@dataclass
class OperationLogEntry:
    """单条操作日志"""

    id: str  # 唯一ID
    timestamp: str  # ISO时间戳
    action: str  # 操作类型
    command: str  # 执行的命令
    workdir: str  # 工作目录
    result: str  # success / failed / blocked
    exit_code: Optional[int] = None
    duration_ms: Optional[int] = None  # 耗时
    safety_check: Optional[str] = None  # 安全检查结果
    yolo_decision: Optional[str] = None  # YOLO决策
    hash_prev: str = ""  # 上一条日志的hash（防篡改链）
    metadata: dict = field(default_factory=dict)


class OperationLogger:
    """操作日志记录器

    特性：
    - Hash链防篡改
    - JSON持久化
    - 自动轮转（单文件上限10MB）
    - 可查询/过滤
    """

    def __init__(self, log_dir: str = "logs/operations"):
        self.log_dir = log_dir
        self.current_log_file: str = ""
        self._prev_hash: str = ""
        os.makedirs(log_dir, exist_ok=True)
        self._init_log_file()

    def _init_log_file(self):
        """初始化或恢复日志文件"""
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        self.current_log_file = os.path.join(self.log_dir, f"ops_{today}.jsonl")

        # 恢复上一条hash
        if os.path.exists(self.current_log_file):
            try:
                with open(self.current_log_file, "r", encoding="utf-8") as f:
                    lines = f.readlines()
                    if lines:
                        last = json.loads(lines[-1].strip())
                        self._prev_hash = last.get("hash_self", "")
            except (json.JSONDecodeError, IndexError):
                self._prev_hash = ""

    def log(
        self,
        action: str,
        command: str,
        result: str,
        workdir: str = "",
        exit_code: Optional[int] = None,
        duration_ms: Optional[int] = None,
        safety_check: Optional[str] = None,
        yolo_decision: Optional[str] = None,
        metadata: dict = None,
    ) -> str:
        """记录一条操作日志
        返回日志ID
        """
        timestamp = datetime.now(timezone.utc).isoformat()

        # 生成唯一ID
        raw_id = f"{timestamp}:{action}:{command[:100]}"
        log_id = hashlib.sha256(raw_id.encode()).hexdigest()[:16]

        # 计算本条hash
        entry_data = json.dumps(
            {
                "id": log_id,
                "timestamp": timestamp,
                "action": action,
                "command": command[:500],
                "workdir": workdir,
                "result": result,
                "prev_hash": self._prev_hash,
            },
            sort_keys=True,
        )
        hash_self = hashlib.sha256(entry_data.encode()).hexdigest()

        entry = OperationLogEntry(
            id=log_id,
            timestamp=timestamp,
            action=action,
            command=command[:500],
            workdir=workdir,
            result=result,
            exit_code=exit_code,
            duration_ms=duration_ms,
            safety_check=safety_check,
            yolo_decision=yolo_decision,
            hash_prev=self._prev_hash,
            metadata=metadata or {},
        )

        # 写入
        self._append(entry, hash_self)
        self._prev_hash = hash_self

        return log_id

    def _append(self, entry: OperationLogEntry, hash_self: str):
        """追加到日志文件"""
        # 轮转检查
        if os.path.exists(self.current_log_file) and os.path.getsize(self.current_log_file) > 10 * 1024 * 1024:
            self._rotate()

        record = {
            "id": entry.id,
            "timestamp": entry.timestamp,
            "action": entry.action,
            "command": entry.command,
            "workdir": entry.workdir,
            "result": entry.result,
            "exit_code": entry.exit_code,
            "duration_ms": entry.duration_ms,
            "safety_check": entry.safety_check,
            "yolo_decision": entry.yolo_decision,
            "hash_prev": entry.hash_prev,
            "hash_self": hash_self,
            "metadata": entry.metadata,
        }

        with open(self.current_log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    def _rotate(self):
        """轮转日志文件"""
        new_name = self.current_log_file.replace(".jsonl", f"_{int(datetime.now(timezone.utc).timestamp())}.jsonl")
        try:
            os.rename(self.current_log_file, new_name)
        except OSError:
            pass

    def query(
        self,
        action: str = None,
        result: str = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict]:
        """查询操作日志"""
        results = []
        if not os.path.exists(self.current_log_file):
            return results

        with open(self.current_log_file, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    entry = json.loads(line.strip())
                    if action and entry.get("action") != action:
                        continue
                    if result and entry.get("result") != result:
                        continue
                    results.append(entry)
                except json.JSONDecodeError:
                    continue

        # 倒序（最新在前）
        results.reverse()
        return results[offset : offset + limit]

    def verify_chain(self) -> tuple[bool, str]:
        """验证Hash链完整性"""
        if not os.path.exists(self.current_log_file):
            return True, "日志文件不存在（空链）"

        prev_hash = ""
        line_num = 0

        with open(self.current_log_file, "r", encoding="utf-8") as f:
            for line in f:
                line_num += 1
                try:
                    entry = json.loads(line.strip())
                except json.JSONDecodeError:
                    return False, f"第{line_num}行JSON解析失败"

                # 检查prev_hash
                expected_prev = entry.get("hash_prev", "")
                if expected_prev != prev_hash:
                    return False, f"第{line_num}行Hash链断裂: 期望 {prev_hash[:8]}... 实际 {expected_prev[:8]}..."

                # 重新计算hash
                verify_data = json.dumps(
                    {
                        "id": entry.get("id", ""),
                        "timestamp": entry.get("timestamp", ""),
                        "action": entry.get("action", ""),
                        "command": entry.get("command", ""),
                        "workdir": entry.get("workdir", ""),
                        "result": entry.get("result", ""),
                        "prev_hash": entry.get("hash_prev", ""),
                    },
                    sort_keys=True,
                )
                computed_hash = hashlib.sha256(verify_data.encode()).hexdigest()

                if computed_hash != entry.get("hash_self", ""):
                    return False, f"第{line_num}行Hash校验失败（可能被篡改）"

                prev_hash = entry.get("hash_self", "")

        return True, f"Hash链验证通过 ({line_num}条记录)"

    def stats(self) -> dict:
        """日志统计"""
        if not os.path.exists(self.current_log_file):
            return {"total_entries": 0}

        total = 0
        by_result = {}
        by_action = {}
        blocked_count = 0

        with open(self.current_log_file, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    entry = json.loads(line.strip())
                    total += 1
                    r = entry.get("result", "unknown")
                    by_result[r] = by_result.get(r, 0) + 1
                    a = entry.get("action", "unknown")
                    by_action[a] = by_action.get(a, 0) + 1
                    if r == "blocked":
                        blocked_count += 1
                except json.JSONDecodeError:
                    pass

        return {
            "total_entries": total,
            "by_result": by_result,
            "by_action": by_action,
            "blocked_operations": blocked_count,
            "chain_verified": self.verify_chain()[0],
        }
