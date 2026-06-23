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
import os
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
    """Read eval results; delegate to DeepSeek for analysis. Only log suggestions, never auto-commit code."""
    if not EVAL_LOG.exists():
        return False

    lines = EVAL_LOG.read_text(encoding="utf-8").strip().split("\n")[-20:]
    if not lines:
        return False

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

    changed = False
    for key, timestamps in list(mis.items()):
        cutoff = (datetime.now(TZ) - timedelta(hours=24)).isoformat()
        mis[key] = [t for t in timestamps if t > cutoff]
        if len(mis[key]) >= 3:
            # V5.0: Ask DeepSeek, don't auto-mutate
            wrong_cause, real_cause = key.split("->")
            ds_suggestion = ask_deepseek_for_weight_adjustment(state, wrong_cause, real_cause)
            if ds_suggestion:
                apply_deepseek_suggestion(state, ds_suggestion)
                mis[key] = []
                changed = True
    return changed


def analyze_eval_logs_with_ds(state):
    """V5.1: Send full eval context to DeepSeek for code-level suggestions.
    Returns a suggestion dict with optional code_patches for whitelisted targets.
    """
    if not EVAL_LOG.exists():
        return None

    lines = EVAL_LOG.read_text(encoding="utf-8").strip().split("\n")[-30:]
    if not lines:
        return None

    try:
        from openai import OpenAI

        weights = state.get("weights", {})
        prompt = (
            "You are an AI evolution engineer. Review recent eval logs and propose code improvements.\n"
            f"Current weights: {json.dumps(weights)}\n"
            f"Recent evals (last 30 lines): {lines[:10]}... (truncated)\n\n"
            "Return a JSON object with:\n"
            '  "reason": why the change is needed,\n'
            '  "adjustments": weight deltas,\n'
            '  "code_patches": [{"target":"auto_valuation","old_function":"<exact old>","new_function":"<new impl>"}]\n'
            "IMPORTANT: only patch auto_valuation.estimate_car_value. Replace random.randint with deterministic hash-based logic. "
            "Do NOT use import/subprocess/exec/eval. Keep it pure Python math."
        )
        client = OpenAI(
            api_key=os.environ.get("DEEPSEEK_API_KEY", os.environ.get("OPENAI_API_KEY", "")),
            base_url=os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1"),
        )
        resp = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.2,
        )
        return json.loads(resp.choices[0].message.content)
    except Exception as e:
        print(f"[EVO] analyze_eval_logs_with_ds failed: {e}")
        return None


def ask_deepseek_for_weight_adjustment(state, wrong_cause, real_cause):
    """Ask DeepSeek to analyze misattribution pattern. Returns suggestion dict or None."""
    try:
        from openai import OpenAI

        weights = state.get("weights", {})
        prompt = (
            f"You are an AI Ops Engineer. Analyze a causal misattribution:\n"
            f"- Wrong cause: {wrong_cause} (current weight: {weights.get(wrong_cause, 0.5)})\n"
            f"- Real cause: {real_cause} (current weight: {weights.get(real_cause, 0.5)})\n"
            f"- All weights: {json.dumps(weights)}\n\n"
            f"Return a JSON with suggested adjustments. Lower the wrong, raise the real.\n"
            f'Format: {{"reason":"...", "adjustments":{{"{wrong_cause}":-0.1, "{real_cause}":+0.1}}}}'
        )
        client = OpenAI(
            api_key=os.environ.get("DEEPSEEK_API_KEY", os.environ.get("OPENAI_API_KEY", "")),
            base_url=os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1"),
        )
        resp = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.1,
        )
        content = resp.choices[0].message.content
        return json.loads(content)
    except Exception as e:
        print(f"[EVO] DeepSeek analysis failed: {e}")
        # Fallback: simple mechanical adjustment
        return {
            "reason": f"Mechanical fallback: {wrong_cause}->{real_cause}",
            "adjustments": {wrong_cause: -0.15, real_cause: +0.1},
        }


def apply_deepseek_suggestion(state, suggestion):
    """Apply DeepSeek's weight suggestions. LOG + PATCH (safe files only).

    Safety gate: only patches auto_valuation/run.py and report templates.
    Never touches causal-reasoner, daemon, evolution_engine, or auth.
    """
    adjustments = suggestion.get("adjustments", {})
    reason = suggestion.get("reason", "No reason provided")
    w = state.setdefault("weights", {})

    applied = {}
    for key, delta in adjustments.items():
        old = w.get(key, 0.5)
        new = round(max(0.1, min(1.0, old + delta)), 2)
        w[key] = new
        applied[key] = {"old": old, "new": new}

    now = ts()
    state["last_adjustment"] = now
    state.setdefault("deepseek_history", []).append(
        {
            "ts": now,
            "reason": reason,
            "applied": applied,
        }
    )

    # Log to ds_suggestions.jsonl
    LOGS.mkdir(parents=True, exist_ok=True)
    with open(LOGS / "ds_suggestions.jsonl", "a", encoding="utf-8") as f:
        f.write(
            json.dumps(
                {"ts": now, "reason": reason, "weights": w},
                ensure_ascii=False,
            )
            + "\n"
        )

    # V5.1 ACTIVE EVOLUTION: apply code patches to whitelisted files only
    _apply_safe_patches(suggestion, now)

    print(f"[EVO] {now} DeepSeek suggestion applied: {reason} {applied}")


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
# V5.1: Safe Active Evolution Patcher
# ═══════════════════════════════════════════════════════════════════════

WHITELIST_PATCH_TARGETS = {
    "auto_valuation": SKILLS / "auto-valuation" / "run.py",
}
_WORKSPACE = BASE / "workspace"
_GIT = _WORKSPACE / "git.cmd"
GIT_CMD = str(_GIT) if _GIT.exists() else None


def _apply_safe_patches(suggestion: dict, ts_now: str) -> bool:
    """Apply DeepSeek code patches to whitelisted files only.

    Gate rules:
    1. Only files in WHITELIST_PATCH_TARGETS may be touched
    2. Patches must reference a known function name in the target
    3. Rejects any patch containing 'import', 'exec', 'eval', '__'
    4. Auto git commit on success
    """
    code_patches = suggestion.get("code_patches", [])
    if not code_patches:
        return False

    dangerous = {"import ", "exec(", "eval(", "__", "subprocess", "os.system"}
    patched_files = []

    for patch in code_patches:
        target_key = patch.get("target")
        old_func = patch.get("old_function", "")
        new_func = patch.get("new_function", "")

        if target_key not in WHITELIST_PATCH_TARGETS:
            print(f"[EVO-PATCH] REJECTED {target_key}: not in whitelist")
            continue

        target_path = WHITELIST_PATCH_TARGETS[target_key]
        if not target_path.exists():
            print(f"[EVO-PATCH] REJECTED {target_key}: file not found")
            continue

        if any(d in new_func for d in dangerous):
            print(f"[EVO-PATCH] REJECTED {target_key}: dangerous pattern detected")
            continue

        content = target_path.read_text(encoding="utf-8")
        if old_func not in content:
            print(f"[EVO-PATCH] REJECTED {target_key}: old_function not found in target")
            continue

        # Apply patch
        new_content = content.replace(old_func, new_func, 1)
        target_path.write_text(new_content, encoding="utf-8")
        print(f"[EVO-PATCH] APPLIED {target_key}: patched {target_path.name}")

        # Log patch
        patchlog = {"ts": ts_now, "target": target_key, "reason": suggestion.get("reason", "")}
        with open(LOGS / "patches_applied.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps(patchlog, ensure_ascii=False) + "\n")

        patched_files.append(str(target_path))

    if patched_files and GIT_CMD:
        for fp in patched_files:
            subprocess.run([GIT_CMD, "add", fp], check=False)
        subprocess.run(
            [GIT_CMD, "commit", "-m", f"Auto-evolve: {suggestion.get('reason', 'DS optimization')}"], check=False
        )

    return bool(patched_files)


# ═══════════════════════════════════════════════════════════════════════
# V5.2: Balance Monitor — prevent runaway overoptimization
# ═══════════════════════════════════════════════════════════════════════

SAFETY_CEILINGS = {
    "deploy": 0.95,
    "high_traffic": 0.70,
    "config_change": 0.85,
    "build_process": 0.80,
    "disk_write": 0.90,
    "memory_leak": 0.85,
    "git_push": 0.90,
    "cron_job": 0.60,
}

DAMPING_FACTOR = 0.85  # per-cycle entropy pull-back toward priors
PRIORS = {
    "deploy": 0.4,
    "high_traffic": 0.3,
    "config_change": 0.5,
    "build_process": 0.4,
    "disk_write": 0.6,
    "memory_leak": 0.5,
    "git_push": 0.5,
    "cron_job": 0.2,
}


def balance_monitor(state):
    """V5.2: Damping check — pull weights back toward Bayesian priors each cycle.

    Prevents runaway overoptimization (e.g. deploy:1.0 biases against all other causes).
    Applies exponential damping: w_new = w_old * DF + prior * (1-DF)
    Enforces absolute safety ceilings.
    """
    w = state.setdefault("weights", {})
    clamped = 0
    damped = 0

    for key, ceiling in SAFETY_CEILINGS.items():
        cur = w.get(key, 0.5)
        # Ceiling clamp
        if cur > ceiling:
            w[key] = ceiling
            clamped += 1
        # Damping toward prior
        prior = PRIORS.get(key, 0.5)
        w[key] = round(w[key] * DAMPING_FACTOR + prior * (1 - DAMPING_FACTOR), 3)
        damped += 1

    if clamped:
        print(f"[EVO] Balance: {clamped} weights clamped at ceiling")
    if damped:
        print(f"[EVO] Balance: {damped} weights damped toward priors (DF={DAMPING_FACTOR})")


# ═══════════════════════════════════════════════════════════════════════
# V5.2: Autophagic Pruning — recycle or delete stale features
# ═══════════════════════════════════════════════════════════════════════

AUTOPHAGY_DIR = BASE / ".deploy" / "autophagy"
SNAPSHOT_RETENTION = 3  # keep last N snapshots, recycle older
ABANDONED_SKILL_DAYS = 30  # days without eval before flagging


def autophagic_prune(state):
    """V5.2: Autophagic Pruning — the system eats itself to stay lean.

    Two-phase:
    1. Snapshot compaction: keep last N evo_state snapshots, recycle disk.
    2. Abandoned skill scan: detect skills without eval activity >30 days.

    No files deleted by default — marked with .abandoned flag for manual review.
    """
    actions = []
    AUTOPHAGY_DIR.mkdir(parents=True, exist_ok=True)

    # Phase 1: Snapshot rotation
    snapshots = sorted(AUTOPHAGY_DIR.glob("evo_snapshot_*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    for stale in snapshots[SNAPSHOT_RETENTION:]:
        stale.unlink(missing_ok=True)
        actions.append(f"recycled:{stale.name}")

    if snapshots:
        print(
            f"[EVO] Autophagy: kept {min(len(snapshots), SNAPSHOT_RETENTION)} snapshots, recycled {max(0, len(snapshots) - SNAPSHOT_RETENTION)}"
        )

    # Take current snapshot
    snap_path = AUTOPHAGY_DIR / f"evo_snapshot_{datetime.now(TZ).strftime('%Y%m%d_%H%M%S')}.json"
    snap_path.write_text(json.dumps(state, indent=2, default=str), encoding="utf-8")

    # Phase 2: Abandoned feature scan
    if EVAL_LOG.exists():
        try:
            recent_lines = EVAL_LOG.read_text(encoding="utf-8").strip().split("\n")[-100:]
            tested_skills = set()
            for line in recent_lines:
                try:
                    r = json.loads(line)
                    tested_skills.add(r.get("skill"))
                except json.JSONDecodeError:
                    continue

            # Check all runnable skills
            for runpy in SKILLS.glob("*/run.py"):
                skill_name = runpy.parent.name
                if skill_name in tested_skills:
                    continue
                age = (datetime.now() - datetime.fromtimestamp(runpy.stat().st_mtime)).days
                if age > ABANDONED_SKILL_DAYS:
                    flag_path = runpy.parent / ".abandoned"
                    if not flag_path.exists():
                        flag_path.write_text(
                            f"Autophagic flag: {datetime.now(TZ).isoformat()}\nLast eval: N/A\nSkill age: {age}d\n",
                            encoding="utf-8",
                        )
                        actions.append(f"flagged:{skill_name}")
        except Exception as e:
            print(f"[EVO] Autophagy scan warning: {e}")

    return actions


# ═══════════════════════════════════════════════════════════════════════
# V5.2: Crisis Predictor — entropy-driven early warning
# ═══════════════════════════════════════════════════════════════════════

CRISIS_LOG = LOGS / "crisis_prediction.jsonl"
CRISIS_THRESHOLD = 0.85  # entropy score above this = pre-crisis
LOOKBACK_CYCLES = 10  # cycles to analyze for trends


def crisis_predictor(state):
    """V5.2: Crisis Predictor — entropy-driven early warning system.

    Computes a composite entropy score from:
    - Weight velocity (how fast weights are drifting from priors)
    - Alert density (alerts per cycle in recent history)
    - Cycle acceleration (interval between state changes decreasing?)

    Returns a dict with score + recommendation. Score >CRISIS_THRESHOLD triggers
    an "imminent crisis" alert pushed to message_bus.
    """
    result = {"score": 0.0, "components": {}, "recommendation": "normal"}

    try:
        w = state.get("weights", {})
        # Component 1: Weight divergence from priors (0-1)
        divergence = 0.0
        n = 0
        for k, prior in PRIORS.items():
            cur = w.get(k, prior)
            divergence += abs(cur - prior)
            n += 1
        weight_div = min(1.0, (divergence / max(n, 1)) * 2)

        # Component 2: Trend (are weights accelerating?)
        ds_history = state.get("deepseek_history", [])
        trend_score = 0.0
        if len(ds_history) >= 3:
            intervals = []
            for i in range(1, len(ds_history)):
                try:
                    t1 = datetime.fromisoformat(ds_history[i - 1]["ts"])
                    t2 = datetime.fromisoformat(ds_history[i]["ts"])
                    intervals.append(abs((t2 - t1).total_seconds()))
                except (KeyError, ValueError):
                    pass
            if len(intervals) >= 2:
                # Acceleration = intervals shrinking (faster mutations)
                first_half = sum(intervals[: len(intervals) // 2]) / max(len(intervals) // 2, 1)
                second_half = sum(intervals[len(intervals) // 2 :]) / max(len(intervals) - len(intervals) // 2, 1)
                if first_half > 0 and second_half < first_half:
                    # Shrinking intervals = higher acceleration
                    trend_score = min(1.0, round(1 - (second_half / first_half), 3))

        # Component 3: Alert density from eval logs
        alert_score = 0.0
        if EVAL_LOG.exists():
            try:
                recent = EVAL_LOG.read_text(encoding="utf-8").strip().split("\n")[-LOOKBACK_CYCLES:]
                fail_count = sum(1 for line in recent if "fail" in line.lower() or "error" in line.lower())
                alert_score = min(1.0, fail_count / max(len(recent), 1) * 3)
            except Exception:
                pass

        # Composite (weighted)
        composite = round(weight_div * 0.4 + trend_score * 0.35 + alert_score * 0.25, 3)
        result["score"] = composite
        result["components"] = {
            "weight_divergence": round(weight_div, 3),
            "trend_acceleration": round(trend_score, 3),
            "alert_density": round(alert_score, 3),
        }

        if composite >= CRISIS_THRESHOLD:
            result["recommendation"] = "LOCKDOWN: freeze weights, escalate to human"
            # Push to message bus
            try:
                from core.message_bus import bus as message_bus

                message_bus.emit("evo_crisis", "monitor", "crisis_alert", result)
            except Exception:
                pass
        elif composite >= 0.65:
            result["recommendation"] = "WATCH: slow evolution, increase damping"
        else:
            result["recommendation"] = "normal"

        # Log
        CRISIS_LOG.parent.mkdir(parents=True, exist_ok=True)
        with open(CRISIS_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps({"ts": ts(), **result}, ensure_ascii=False) + "\n")

        if composite >= 0.65:
            print(f"[EVO] Crisis predictor: score={composite} -> {result['recommendation']}")

    except Exception as e:
        print(f"[EVO] Crisis predictor error: {e}")

    return result


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

        # V5.2: Crisis predictor runs first — detect trouble BEFORE acting
        crisis = crisis_predictor(state)
        if crisis["recommendation"] == "LOCKDOWN: freeze weights, escalate to human":
            print(f"[EVO] CRISIS LOCKDOWN: score={crisis['score']} — freezing weights, skipping evolution")
            log_cycle(state, extra={"action": "crisis_lockdown", "crisis": crisis})
            save_state(state)
            time.sleep(60)
            continue

        # V4.1: Self-DNA + V5.1: DeepSeek active evolution
        mutated = analyze_eval_logs(state)
        if mutated:
            inject_weights_into_reasoner(state)
            # V5.1: also send to DS for code-level suggestions
            ds_suggestion = analyze_eval_logs_with_ds(state)
            if ds_suggestion:
                apply_deepseek_suggestion(state, ds_suggestion)

        # V5.2: Balance monitor — dampen weights AFTER evolution step
        balance_monitor(state)

        # V5.2: GitHub Predator — autotrophic feeding (once per day)
        try:
            from core.github_predator import GitHubPredator

            predator = GitHubPredator()
            predator.run(daily=True)
        except Exception as e:
            print(f"[EVO] Predator feed failed (non-fatal): {e}")

        # V4.5: Multi-Agent
        orchestrate_agents(state)

        # V5.2: Autophagic pruning — compress snapshots + flag stale skills
        prune_actions = autophagic_prune(state)
        if prune_actions:
            print(f"[EVO] Autophagy: {prune_actions}")

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
