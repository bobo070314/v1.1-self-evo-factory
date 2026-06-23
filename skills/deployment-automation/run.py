#!/usr/bin/env python3
"""
deployment-automation — Deploy/rollback/health check automation.
Automates deployment workflows with health checks, rollback capability,
and dry-run preview.

Usage:
  python run.py --config deploy.yaml --deploy
  python run.py --config deploy.yaml --rollback
  python run.py --config deploy.yaml --health-check
"""

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


DEFAULT_HEALTH_CHECK_URL = "http://localhost:3000/health"
DEFAULT_HEALTH_TIMEOUT = 30
DEFAULT_HEALTH_INTERVAL = 2


def load_config(config_path: str) -> dict:
    """Load deployment config from YAML or JSON file."""
    path = Path(config_path)
    if not path.exists():
        return {}

    content = path.read_text(encoding="utf-8", errors="replace")

    if path.suffix in (".yaml", ".yml"):
        try:
            import yaml
            return yaml.safe_load(content) or {}
        except ImportError:
            # Fallback: simple key=value parsing
            result = {}
            for line in content.split("\n"):
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if ":" in line:
                    key, val = line.split(":", 1)
                    result[key.strip()] = val.strip()
            return result
    elif path.suffix == ".json":
        return json.loads(content)

    return {}


def run_command(cmd: list, cwd: str = None, dry_run: bool = True) -> dict:
    """Run a shell command."""
    result = {
        "command": " ".join(cmd),
        "dry_run": dry_run,
        "exit_code": None,
        "stdout": "",
        "stderr": "",
        "error": None,
    }

    if dry_run:
        result["stdout"] = f"[DRY-RUN] Would run: {' '.join(cmd)}"
        return result

    try:
        proc = subprocess.run(
            cmd,
            cwd=cwd or os.getcwd(),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=300,
        )
        result["exit_code"] = proc.returncode
        result["stdout"] = proc.stdout[:10000]
        result["stderr"] = proc.stderr[:5000]
    except subprocess.TimeoutExpired:
        result["error"] = "Command timed out (300s)"
    except FileNotFoundError as e:
        result["error"] = f"Command not found: {e}"
    except Exception as e:
        result["error"] = str(e)

    return result


def health_check(url: str, timeout: int = DEFAULT_HEALTH_TIMEOUT,
                 interval: int = DEFAULT_HEALTH_INTERVAL, dry_run: bool = True) -> dict:
    """Perform HTTP health check on a deployed service."""
    result = {
        "url": url,
        "timeout": timeout,
        "interval": interval,
        "dry_run": dry_run,
        "healthy": None,
        "status_code": None,
        "attempts": 0,
        "elapsed_seconds": 0,
        "error": None,
    }

    if dry_run:
        result["healthy"] = True
        result["stdout"] = f"[DRY-RUN] Would health-check: {url} (timeout={timeout}s, interval={interval}s)"
        return result

    try:
        import urllib.request
    except ImportError:
        result["error"] = "urllib not available"
        return result

    start = time.time()
    max_attempts = timeout // interval

    for attempt in range(1, max_attempts + 1):
        result["attempts"] = attempt
        try:
            req = urllib.request.Request(url, method="GET")
            resp = urllib.request.urlopen(req, timeout=5)
            result["status_code"] = resp.status
            if 200 <= resp.status < 400:
                result["healthy"] = True
                result["elapsed_seconds"] = round(time.time() - start, 2)
                return result
        except Exception as e:
            pass

        if attempt < max_attempts:
            time.sleep(interval)

    result["healthy"] = False
    result["elapsed_seconds"] = round(time.time() - start, 2)
    result["error"] = f"Health check failed after {result['attempts']} attempts"
    return result


def deploy(config: dict, dry_run: bool = True) -> dict:
    """Run deployment steps from config."""
    steps = []
    step_configs = config.get("deploy", {}).get("steps", [])

    if not step_configs:
        # Default: git pull + install + build + restart
        steps = [
            {"name": "git-pull", "run": ["git", "pull"], "description": "Pull latest changes"},
            {"name": "install-deps", "run": ["npm", "install"], "description": "Install dependencies"},
            {"name": "build", "run": ["npm", "run", "build"], "description": "Build project"},
        ]
    else:
        steps = step_configs

    results = []
    for step in steps:
        name = step.get("name", "unnamed")
        desc = step.get("description", "")
        cmd = step.get("run", [])

        if isinstance(cmd, str):
            cmd = cmd.split()

        res = {
            "step": name,
            "description": desc,
            "command": " ".join(cmd),
        }
        if cmd:
            cmd_res = run_command(cmd, dry_run=dry_run)
            res.update({
                "exit_code": cmd_res["exit_code"],
                "stdout": cmd_res["stdout"][:2000],
                "stderr": cmd_res["stderr"][:1000],
                "error": cmd_res.get("error"),
            })
            if cmd_res.get("exit_code") and cmd_res["exit_code"] != 0 and not dry_run:
                res["failed"] = True
                results.append(res)
                results.append({"step": "deploy-aborted", "reason": f"Step '{name}' failed"})
                break
        else:
            res["error"] = "No command specified"

        results.append(res)

    return {
        "deploy_results": results,
        "deploy_success": all(not r.get("failed") for r in results),
    }


def rollback(config: dict, dry_run: bool = True) -> dict:
    """Run rollback steps from config."""
    steps = config.get("rollback", {}).get("steps", [])

    if not steps:
        steps = [
            {"name": "git-revert", "run": ["git", "checkout", "-"], "description": "Revert to previous commit"},
            {"name": "restart", "run": ["echo", "Restart service"], "description": "Restart service"},
        ]

    results = []
    for step in steps:
        name = step.get("name", "unnamed")
        cmd = step.get("run", [])

        if isinstance(cmd, str):
            cmd = cmd.split()

        res = {
            "step": name,
            "description": step.get("description", ""),
            "command": " ".join(cmd),
        }
        if cmd:
            cmd_res = run_command(cmd, dry_run=dry_run)
            res.update({
                "exit_code": cmd_res["exit_code"],
                "stdout": cmd_res["stdout"][:2000],
                "stderr": cmd_res["stderr"][:1000],
                "error": cmd_res.get("error"),
            })
        results.append(res)

    return {
        "rollback_results": results,
        "rollback_success": True,
    }


def main():
    parser = argparse.ArgumentParser(
        description="deployment-automation — Deploy/rollback/health check automation",
    )
    parser.add_argument("--config", default="deploy.yaml", help="Deployment config file (default: deploy.yaml)")
    parser.add_argument("--deploy", action="store_true", help="Run deployment")
    parser.add_argument("--rollback", action="store_true", help="Run rollback")
    parser.add_argument("--health-check", action="store_true", help="Run health check")
    parser.add_argument("--health-url", default=None, help="Health check URL (overrides config)")
    parser.add_argument("--timeout", type=int, default=DEFAULT_HEALTH_TIMEOUT, help=f"Health check timeout in seconds (default: {DEFAULT_HEALTH_TIMEOUT})")
    parser.add_argument("--dry-run", action="store_true", default=True, help="Preview only, no actual commands (default)")
    parser.add_argument("--no-dry-run", action="store_false", dest="dry_run", help="Actually execute commands")
    parser.add_argument("--json", action="store_true", help="Output as JSON")

    args = parser.parse_args()

    config = load_config(args.config)
    output = {
        "config": args.config,
        "config_loaded": bool(config),
        "dry_run": args.dry_run,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "results": {},
    }

    if args.deploy:
        output["results"]["deploy"] = deploy(config, dry_run=args.dry_run)

    if args.rollback:
        output["results"]["rollback"] = rollback(config, dry_run=args.dry_run)

    if args.health_check:
        health_url = args.health_url or config.get("health_check", {}).get("url", DEFAULT_HEALTH_CHECK_URL)
        output["results"]["health_check"] = health_check(
            health_url, timeout=args.timeout, dry_run=args.dry_run
        )

    if not any([args.deploy, args.rollback, args.health_check]):
        # Default: health check only
        health_url = args.health_url or config.get("health_check", {}).get("url", DEFAULT_HEALTH_CHECK_URL)
        output["results"]["health_check"] = health_check(
            health_url, timeout=args.timeout, dry_run=args.dry_run
        )

    if args.json:
        print(json.dumps(output, indent=2, ensure_ascii=False))
    else:
        mode = "[DRY-RUN]" if args.dry_run else "[LIVE]"
        print(f"{mode} deployment-automation")
        print(f"  Config: {args.config} ({'loaded' if output['config_loaded'] else 'not found, using defaults'})")

        for action, res in output["results"].items():
            if action == "deploy":
                print(f"\n  Deploy:")
                for step in res.get("deploy_results", []):
                    status = "SKIPPED" if step.get("dry_run") else (
                        "FAILED" if step.get("failed") else "OK" if step.get("exit_code") == 0 else f"exit={step.get('exit_code')}")
                    print(f"    [{status}] {step['step']}: {step['command']}")
                    if step.get("error"):
                        print(f"      ERROR: {step['error']}")

            elif action == "rollback":
                print(f"\n  Rollback:")
                for step in res.get("rollback_results", []):
                    print(f"    [STEP] {step['step']}: {step['command']}")

            elif action == "health_check":
                print(f"\n  Health Check:")
                if res.get("dry_run"):
                    print(f"    {res.get('stdout', 'DRY-RUN')}")
                else:
                    status = "HEALTHY" if res.get("healthy") else "UNHEALTHY"
                    print(f"    {status} — {res['url']} (attempts={res['attempts']}, elapsed={res['elapsed_seconds']}s)")
                    if res.get("error"):
                        print(f"    ERROR: {res['error']}")

    has_error = False
    for res in output["results"].values():
        if isinstance(res, dict):
            if res.get("health_check"):
                hc = res["health_check"]
                if not hc.get("dry_run") and not hc.get("healthy"):
                    has_error = True
            if res.get("deploy_results"):
                for s in res["deploy_results"]:
                    if s.get("failed"):
                        has_error = True
            if res.get("deploy_success") is False:
                has_error = True

    sys.exit(1 if has_error else 0)


if __name__ == "__main__":
    main()
