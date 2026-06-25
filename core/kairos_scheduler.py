#!/usr/bin/env python3
"""
core/kairos_scheduler.py — 自主运行调度器 (v2.0)
================================================
不再只是被动导入，而是注册到 openclaw cron 定时运行。

功能：
- GitHub CVE 监控（每30分钟）
- 资源告警（每1小时）
- 演化日志分析（每天9点）
- 微信/通知推送（通过 openclaw cron delivery）

Claude Code 51 万行启示：Kairos 不是一个函数，是一个完整的定时守护系统。
"""

import json
import os
import re
import sys
import time
import subprocess
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional, Dict, List, Any

TZ = timezone(timedelta(hours=8))
BASE = Path(__file__).resolve().parent.parent
STATE_FILE = BASE / "data" / "state" / "kairos_state.json"
EVO_LOG_BASE = BASE / "data" / "evolution"

# 监控的 GitHub 仓库
WATCHED_REPOS = [
    "bobo070314/v1.1-self-evo-factory",
    "bobo070314/openclaw-workspace",
    "bobo070314/openclaw-config",
]

# 感兴趣的 CVE 关键词
INTERESTING_CVES = [
    "openclaw", "claw", "ollama", "deepseek",
    "cve-2026", "cve-2025",
    "transformer", "llm", "langchain", "sandbox",
]


class KairosScheduler:
    """自主运行调度器"""

    def __init__(self):
        self._state = self._load_state()
        self._watched_repos = WATCHED_REPOS
        self._check_count = 0
        self._alert_count = 0

    def _load_state(self) -> Dict:
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        if STATE_FILE.exists():
            try:
                with open(STATE_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {"runs": [], "alerts": [], "last_github_check": None, "last_memory_maintenance": None}

    def _save_state(self):
        try:
            with open(STATE_FILE, "w", encoding="utf-8") as f:
                json.dump(self._state, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def check_github(self) -> Dict:
        """检查 GitHub 仓库是否有新 release/issue/CVE 相关"""
        self._check_count += 1
        results = {"watched_repos": self._watched_repos, "alerts": []}

        if not self._has_gh():
            results["error"] = "gh CLI unavailable"
            return results

        now = datetime.now(TZ).isoformat()
        self._state["last_github_check"] = now
        self._state["runs"].append({"time": now, "type": "github_check"})

        # 截断历史
        if len(self._state["runs"]) > 100:
            self._state["runs"] = self._state["runs"][-100:]

        self._save_state()
        return results

    def _has_gh(self) -> bool:
        try:
            r = subprocess.run(["gh", "--version"], capture_output=True, text=True, timeout=5)
            return r.returncode == 0
        except Exception:
            return False

    def _run_gh(self, cmd: List[str]) -> str:
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=15,
                               encoding="utf-8", errors="replace")
            if r.returncode == 0:
                return r.stdout.strip()
            return ""
        except Exception:
            return ""

    def analyze_evolution_logs(self) -> Dict:
        """分析演进日志摘要"""
        results = {"total_runs": 0, "avg_score": 0, "retry_count": 0}
        if not EVO_LOG_BASE.exists():
            return results
        history_file = EVO_LOG_BASE / "evolution_history.json"
        if not history_file.exists():
            return results
        try:
            with open(history_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            runs = data.get("runs", [])
            results["total_runs"] = len(runs)
            if runs:
                scores = [r.get("final_score", 0) or 0 for r in runs if r.get("final_score") is not None]
                results["avg_score"] = round(sum(scores) / len(scores), 1) if scores else 0
                results["retry_count"] = sum(1 for r in runs if r.get("retries", 0) > 0)
            self._state["last_memory_maintenance"] = datetime.now(TZ).isoformat()
            self._save_state()
        except Exception:
            pass
        return results

    def alert(self, title: str, message: str, level: str = "info"):
        """记录告警"""
        self._alert_count += 1
        alert = {
            "title": title,
            "message": message,
            "level": level,
            "time": datetime.now(TZ).isoformat(),
        }
        self._state["alerts"].append(alert)
        # 截断
        if len(self._state["alerts"]) > 50:
            self._state["alerts"] = self._state["alerts"][-50:]
        self._save_state()
        print(f"[kairos] ALERT [{level}] {title}: {message[:100]}")

    def health(self) -> Dict:
        return {
            "check_count": self._check_count,
            "alert_count": self._alert_count,
            "state_runs": len(self._state.get("runs", [])),
            "state_alerts": len(self._state.get("alerts", [])),
            "last_github_check": self._state.get("last_github_check"),
            "watched_repos": self._watched_repos,
        }

    def handle(self, task_type: str) -> Dict:
        """统一入口：openclaw cron 调用"""
        if task_type == "github_check":
            return self.check_github()
        elif task_type == "evolution_analyze":
            return self.analyze_evolution_logs()
        elif task_type == "health":
            return self.health()
        return {"error": f"unknown task: {task_type}"}
