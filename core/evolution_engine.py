#!/usr/bin/env python3
"""Evolution Engine v0.1.0 --- V4.1/V4.5/V5.0 core
==================================================
- Monitors eval results (V4.1)
- Auto-adjusts causal-reasoner Bayesian weights (V4.1)
- Generates self-PR via Git (V4.1)
- Multi-Agent orchestration: SecAgent / OpsAgent / AnalystAgent (V4.5)
- Zero-touch maintenance: auto-rollback, log purge, anomaly escalation (V5.0)
"""

import json
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

VERSION = "0.1.0"
TZ = timezone(timedelta(hours=8))

BASE = Path("D:/bobo/openclaw-foreign")
SKILLS = BASE / "skills"
LOGS = BASE / ".deploy" / "logs"
STATE_FILE = BASE / "core" / "evo_state.json"
REASONER_PY = SKILLS / "causal-reasoner" / "run.py"
EVAL_LOG = LOGS / "eval.jsonl"

AGENTS = {
    "sec": SKILLS / "security-audit" / "run.py",
    "ops": SKILLS / "deployment-automation" / "run.py",
    "analyst": SKILLS / "causal-reasoner" / "run.py",
}


def ts():
    return datetime.now(TZ).isoformat()


def load_state():
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    base = {
        "weights": {
            "deploy": 0.9,
            "high_traffic": 0.5,
            "config_change": 0.7,
            "build_process": 0.6,
            "disk_write": 0.8,
            "memory_leak": 0.7,
            "git_push": 0.8,
            "cron_job": 0.4,
        },
        "last_adjustment": None,
        "last_pr": None,
        "misattributions": {},
        "cycle_count": 0,
    }
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(base, indent=2), encoding="utf-8")
    return base


def save_state(state):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")


# ═══════════════════════════════════════════════════════════════════════
# V4.1: Self-DNA Editor --- read eval, adjust weights, commit PR
# ═══════════════════════════════════════════════════════════════════════


def analyze_eval_logs(state):
    """Read eval results; if >3 consecutive misattributions, adjust weights."""
    if not EVAL_LOG.exists():
        return False

    lines = EVAL_LOG.read_text(encoding="utf-8").strip().split("\n")[-20:]
    mis = state.setdefault("misattributions", {})

    for line in lines:
        try:
            r = json.loads(line)
            wrong = r.get("wrong_cause")
            real = r.get("real_cause")
            if wrong and real:
                mis.setdefault(f"{wrong}->{real}", []).append(ts())
        except json.JSONDecodeError:
            continue

    for key, timestamps in list(mis.items()):
        # Keep only last 24h
        cutoff = (datetime.now(TZ) - timedelta(hours=24)).isoformat()
        mis[key] = [t for t in timestamps if t > cutoff]
        if len(mis[key]) >= 3:
            wrong_cause, real_cause = key.split("->")
            adjust_weight(state, wrong_cause, real_cause)
            # Reset after adjustment
            mis[key] = []
            return True
    return False


def adjust_weight(state, weaken: str, strengthen: str):
    """Lower weight of misattributed cause, raise weight of real cause."""
    w = state.setdefault("weights", {})
    old_w = w.get(weaken, 0.5)
    old_s = w.get(strengthen, 0.5)

    w[weaken] = round(max(0.1, old_w - 0.15), 2)
    w[strengthen] = round(min(0.95, old_s + 0.1), 2)

    now = ts()
    state["last_adjustment"] = now
    print(f"[EVO] {now} Weight adjusted: {weaken} {old_w}->{w[weaken]}, {strengthen} {old_s}->{w[strengthen]}")


def inject_weights_into_reasoner(state):
    """Write current weights into causal-reasoner's run.py as a comment block."""
    if not REASONER_PY.exists():
        print("[EVO] WARNING: causal-reasoner/run.py not found")
        return

    content = REASONER_PY.read_text(encoding="utf-8")
    weights = state.get("weights", {})

    marker_start = "# === AUTO-TUNED BY EVOLUTION ENGINE ==="
    marker_end = "# === END AUTO-TUNE ==="

    new_block = f"{marker_start}\n# Last adjustment: {state.get('last_adjustment', 'never')}\nAUTO_WEIGHTS = {json.dumps(weights)}\n{marker_end}"

    if marker_start in content:
        # Replace existing block
        import re

        content = re.sub(
            rf"{re.escape(marker_start)}.*?{re.escape(marker_end)}",
            new_block,
            content,
            flags=re.DOTALL,
        )
    else:
        # Append after imports, before main logic
        content = content.replace(
            "# -- Prior belief table",
            f"{new_block}\n\n# -- Prior belief table",
        )

        # If no Prior table marker, append after docstring
        if new_block not in content:
            content += f"\n\n{new_block}\n"

    REASONER_PY.write_text(content, encoding="utf-8")

    # Git commit (local self-PR)
    subprocess.run(
        ["git", "-C", str(SKILLS), "add", "causal-reasoner/run.py"], check=False, encoding="utf-8", errors="replace"
    )
    res = subprocess.run(
        [
            "git",
            "-C",
            str(SKILLS),
            "commit",
            "-m",
            f"Auto-tune: adjust Bayesian weights ({state.get('last_adjustment', 'now')})",
        ],
        check=False,
        encoding="utf-8",
        errors="replace",
    )
    if res.returncode == 0:
        state["last_pr"] = ts()
        print(f"[EVO] {ts()} Self-PR committed to skills repo")


# ═══════════════════════════════════════════════════════════════════════
# V4.5: Multi-Agent Orchestration
# ═══════════════════════════════════════════════════════════════════════


def orchestrate_agents(state):
    """Check health; delegate tasks to specialized agents via JSONL bus."""
    alerts = detect_alerts()

    for alert in alerts:
        agent_type = dispatch_alert(alert["type"])
        sys.stdout.flush()

        if agent_type == "sec":
            task_agent("sec", f"--audit {alert['detail']}", alert)
        elif agent_type == "ops":
            task_agent("ops", f"--repair {alert['detail']}", alert)
        elif agent_type == "analyst":
            task_agent("analyst", f"--trace {alert['detail']}", alert)

        log_cycle(state, {"action": "orchestrate", "alert": alert, "agent": agent_type})


def detect_alerts():
    """Read .daemon/state.json and check for actionable alerts."""
    alerts = []
    daemon_state = BASE / "skills" / ".daemon" / "state.json"

    if daemon_state.exists():
        try:
            ds = json.loads(daemon_state.read_text(encoding="utf-8"))
            for check in ds.get("checks", []):
                if check.get("alert"):
                    alerts.append(
                        {
                            "type": check["type"],
                            "severity": "high" if check.get("value", 0) > check.get("threshold", 80) + 10 else "medium",
                            "message": check.get("message", "Unknown"),
                            "detail": check.get("details", {}),
                        }
                    )
        except (json.JSONDecodeError, KeyError):
            pass

    # Simulate disk/log/security checks
    import shutil

    disk_usage = round(100 - (shutil.disk_usage(BASE).free / shutil.disk_usage(BASE).total * 100), 1)
    if disk_usage > 90:
        alerts.append(
            {
                "type": "disk",
                "severity": "high",
                "message": f"Disk usage {disk_usage}%",
                "detail": f"disk_usage_{disk_usage}pct",
            }
        )

    return alerts


def dispatch_alert(alert_type):
    """Route alert to the right agent."""
    mapping = {
        "tokens": "sec",
        "cpu": "ops",
        "memory": "ops",
        "disk": "ops",
        "logs": "sec",
        "git": "ops",
        "prompts": "sec",
    }
    return mapping.get(alert_type, "analyst")


def task_agent(agent_id, args_str, alert):
    """Run agent skill with given args."""
    script = AGENTS.get(agent_id)
    if not script:
        print(f"[EVO] Unknown agent: {agent_id}")
        return

    cmd = (
        [sys.executable, str(script), "--dry-run", args_str.split()[0]]
        if "--dry-run" not in sys.argv
        else [sys.executable, str(script)] + args_str.split()
    )

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30)
        if result.returncode != 0:
            print(f"[EVO] Agent {agent_id} failed: {result.stderr[:200]}")
        else:
            print(f"[EVO] Agent {agent_id} dispatched: {alert['message']}")
    except subprocess.TimeoutExpired:
        print(f"[EVO] Agent {agent_id} timed out")
    except Exception as e:
        print(f"[EVO] Agent {agent_id} error: {e}")


# ═══════════════════════════════════════════════════════════════════════
# V5.0: Zero-Touch Maintenance
# ═══════════════════════════════════════════════════════════════════════


def auto_maintenance(state):
    """Handle routine maintenance automatically. Only escalate unknowns."""
    actions = []

    # Disk cleanup
    import shutil

    disk_usage = round(100 - (shutil.disk_usage(str(BASE)).free / shutil.disk_usage(str(BASE)).total * 100), 1)
    if disk_usage > 90:
        print(f"[EVO] Disk {disk_usage}% -> purging logs older than 7 days")
        purge_old_logs()
        actions.append("purged_old_logs")

    # Deploy failure auto-rollback (check deploy log)
    deploy_log = LOGS / "deploy.log"
    if deploy_log.exists():
        last_deploy = deploy_log.read_text(encoding="utf-8").strip().split("\n")[-5:]
        fail_count = sum(1 for line in last_deploy if "FAILURE" in line or "error" in line.lower())
        if fail_count >= 3:
            print("[EVO] Deploy failure detected -> auto-rollback")
            rollback()
            actions.append("auto_rollback")

    # Unknown anomalies -> escalate only
    daemon_state = BASE / "skills" / ".daemon" / "state.json"
    if daemon_state.exists():
        try:
            ds = json.loads(daemon_state.read_text(encoding="utf-8"))
            total_alerts = ds.get("alerts", 0)
            if total_alerts >= 3:
                print(f"[EVO] {total_alerts} persistent alerts -> UNKNOWN, escalate to human")
                log_cycle(
                    state,
                    {
                        "action": "escalate",
                        "alerts": total_alerts,
                        "message": "Multiple persistent alerts; manual review needed",
                    },
                )
                actions.append("escalated")
        except Exception:
            pass

    return actions


def purge_old_logs():
    """Delete log files older than 7 days."""
    if not LOGS.exists():
        return
    cutoff = time.time() - 7 * 86400
    for f in LOGS.glob("*.jsonl"):
        if f.stat().st_mtime < cutoff:
            f.unlink(missing_ok=True)
    for f in LOGS.glob("*.log"):
        if f.stat().st_mtime < cutoff:
            f.unlink(missing_ok=True)


def rollback():
    """Trigger deployment-automation rollback."""
    script = AGENTS["ops"]
    subprocess.run(
        [sys.executable, str(script), "--rollback"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=60,
        check=False,
    )


# ═══════════════════════════════════════════════════════════════════════
# Cycle logging
# ═══════════════════════════════════════════════════════════════════════


def log_cycle(state, extra=None):
    LOGS.mkdir(parents=True, exist_ok=True)
    entry = {
        "ts": ts(),
        "cycle": state.get("cycle_count", 0),
        "weights": state.get("weights", {}),
        "last_adjustment": state.get("last_adjustment"),
    }
    if extra:
        entry["extra"] = extra
    with open(LOGS / "evo.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


# ═══════════════════════════════════════════════════════════════════════
# Main loop
# ═══════════════════════════════════════════════════════════════════════


def main():
    print(f"[EVO] Evolution Engine v{VERSION} starting...")
    state = load_state()

    parser = None  # No argparse needed; run as daemon
    one_shot = "--once" in sys.argv

    while True:
        state["cycle_count"] = state.get("cycle_count", 0) + 1
        now = ts()
        print(f"\n[EVO] Cycle {state['cycle_count']} @ {now}")

        # V4.1: Self-DNA
        mutated = analyze_eval_logs(state)
        if mutated:
            inject_weights_into_reasoner(state)

        # V4.5: Multi-Agent
        orchestrate_agents(state)

        # V5.0: Zero-Touch
        actions = auto_maintenance(state)
        if actions:
            print(f"[EVO] Maintenance actions: {actions}")

        log_cycle(state)
        save_state(state)

        if one_shot:
            break

        time.sleep(60)


if __name__ == "__main__":
    main()
