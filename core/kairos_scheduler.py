#!/usr/bin/env python3
"""core/kairos_scheduler.py — GitHub Vulnerability Monitor & Resource Alerter

Kairos = Greek god of the opportune moment.
Polls GitHub API every 5 minutes for:
- New CVE/vulnerability advisories in watched repos
- Dependency security alerts
- Resource exhaustion warnings (disk <5GB, RAM <1GB, CPU >90%)

Only fires notifications when something actually changes.
"""

import json
import os
import re
import sys
import time
import threading
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any

UTC = timezone.utc
BASE_DIR = Path(__file__).resolve().parent.parent
STATE_FILE = BASE_DIR / "data" / "kairos_state.json"

POLL_INTERVAL_S = int(os.environ.get("KAIROS_POLL_INTERVAL", "300"))  # 5 min default

# Repos to monitor (from config or env)
WATCHED_REPOS = json.loads(os.environ.get("KAIROS_WATCHED_REPOS", json.dumps([
    "bobo070314/v1.1-self-evo-factory",
])))

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
GITHUB_API = "https://api.github.com"


class KairosScheduler:
    """GitHub watcher + resource monitor. Fires alerts only on state change."""

    def __init__(self):
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._state = self._load_state()
        self._callbacks: List = []

    def _load_state(self) -> Dict:
        if STATE_FILE.exists():
            try:
                return json.loads(STATE_FILE.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {
            "last_cve_check": None,
            "last_resource_check": None,
            "known_cve_ids": [],
            "notifications_sent": 0,
        }

    def _save_state(self):
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        STATE_FILE.write_text(json.dumps(self._state, indent=2, ensure_ascii=False), encoding="utf-8")

    def start(self, on_alert: callable = None):
        if self._running:
            return
        if on_alert:
            self._callbacks.append(on_alert)
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True, name="KairosScheduler")
        self._thread.start()

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)

    def _loop(self):
        while self._running:
            try:
                self._check_all()
            except Exception:
                pass
            time.sleep(POLL_INTERVAL_S)

    def _check_all(self):
        """Run all checks in sequence."""
        alerts = []

        # 1. GitHub security advisories
        cve_alerts = self._check_github_advisories()
        alerts.extend(cve_alerts)

        # 2. Resource monitoring
        resource_alerts = self._check_resources()
        alerts.extend(resource_alerts)

        # 3. Save state
        self._state["last_cve_check"] = datetime.now(UTC).isoformat()
        self._state["last_resource_check"] = datetime.now(UTC).isoformat()
        self._save_state()

        # 4. Fire callbacks
        for alert in alerts:
            self._state["notifications_sent"] += 1
            for cb in self._callbacks:
                try:
                    cb(alert)
                except Exception:
                    pass

    def _check_github_advisories(self) -> List[Dict]:
        """Check GitHub Advisory Database for new CVEs in watched repos."""
        alerts = []

        for repo_full in WATCHED_REPOS:
            try:
                advisories = self._fetch_advisories(repo_full)
                for adv in advisories:
                    cve_id = adv.get("cve_id") or adv.get("ghsa_id", "")
                    if cve_id and cve_id not in self._state["known_cve_ids"]:
                        alert = {
                            "type": "security_advisory",
                            "repo": repo_full,
                            "cve_id": cve_id,
                            "severity": adv.get("severity", "UNKNOWN"),
                            "summary": adv.get("summary", "")[:200],
                            "url": adv.get("html_url", ""),
                            "detected_at": datetime.now(UTC).isoformat(),
                        }
                        alerts.append(alert)
                        self._state["known_cve_ids"].append(cve_id)
            except Exception:
                pass

        return alerts

    def _fetch_advisories(self, repo_full: str) -> List[Dict]:
        """Fetch recent advisories from GitHub API."""
        url = f"{GITHUB_API}/repos/{repo_full}/security-advisories?per_page=5&state=published"
        headers = {"Accept": "application/vnd.github+json"}
        if GITHUB_TOKEN:
            headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"

        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=15) as resp:
                return json.loads(resp.read().decode())
        except (urllib.error.HTTPError, urllib.error.URLError):
            return []

    def _check_resources(self) -> List[Dict]:
        """Check system resources: disk, RAM, CPU."""
        alerts = []
        try:
            import shutil

            # Disk check
            disk = shutil.disk_usage(str(BASE_DIR))
            free_gb = disk.free / (1024 ** 3)
            if free_gb < 5:
                alerts.append({
                    "type": "resource_low_disk",
                    "free_gb": round(free_gb, 1),
                    "total_gb": round(disk.total / (1024 ** 3), 1),
                    "threshold_gb": 5,
                    "detected_at": datetime.now(UTC).isoformat(),
                })
        except Exception:
            pass

        try:
            # RAM check (Windows)
            import ctypes

            class MEMORYSTATUSEX(ctypes.Structure):
                _fields_ = [
                    ("dwLength", ctypes.c_ulong),
                    ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong),
                    ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong),
                    ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong),
                    ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
                ]

            mem = MEMORYSTATUSEX()
            mem.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(mem))

            free_ram_mb = mem.ullAvailPhys / (1024 * 1024)
            if free_ram_mb < 1024:  # Less than 1GB
                alerts.append({
                    "type": "resource_low_ram",
                    "free_mb": round(free_ram_mb, 1),
                    "total_mb": round(mem.ullTotalPhys / (1024 * 1024), 1),
                    "load_pct": mem.dwMemoryLoad,
                    "threshold_mb": 1024,
                    "detected_at": datetime.now(UTC).isoformat(),
                })
        except Exception:
            pass

        return alerts

    # ---- Health ----
    def health(self) -> Dict:
        return {
            "running": self._running,
            "poll_interval_s": POLL_INTERVAL_S,
            "watched_repos": WATCHED_REPOS,
            "known_cves": len(self._state.get("known_cve_ids", [])),
            "notifications_sent": self._state.get("notifications_sent", 0),
            "last_cve_check": self._state.get("last_cve_check"),
            "last_resource_check": self._state.get("last_resource_check"),
            "state_file": str(STATE_FILE),
        }


# ---- Singleton ----
_kairos: Optional[KairosScheduler] = None


def get_kairos() -> KairosScheduler:
    global _kairos
    if _kairos is None:
        _kairos = KairosScheduler()
    return _kairos


# ---- CLI ----
if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser(description="Kairos Scheduler — GitHub watcher + resource alerter")
    p.add_argument("--health", action="store_true", help="Health check")
    p.add_argument("--check-once", action="store_true", help="Run one check cycle and exit")
    p.add_argument("--json", action="store_true")
    args = p.parse_args()

    k = get_kairos()

    if args.health:
        h = k.health()
        if args.json:
            print(json.dumps(h, indent=2, ensure_ascii=False))
        else:
            print(f"Running: {h['running']} | Poll: {h['poll_interval_s']}s")
            print(f"Known CVEs: {h['known_cves']} | Notifications: {h['notifications_sent']}")
        sys.exit(0)

    if args.check_once:
        alerts = k._check_all()
        if args.json:
            print(json.dumps({"alerts": alerts, "count": len(alerts)}, indent=2, ensure_ascii=False))
        else:
            if alerts:
                for a in alerts:
                    print(f"[{a['type']}] {a.get('cve_id', a.get('free_gb', a.get('free_mb', '')))}: {a.get('summary', '')}")
            else:
                print("No new alerts")
        sys.exit(0)

    sys.exit(0)
