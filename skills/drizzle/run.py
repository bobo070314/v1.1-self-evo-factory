#!/usr/bin/env python3
"""drizzle — drizzle-kit wrapper with --dry-run and --json support.
Wraps `npx drizzle-kit` commands for cross-platform database schema management.

Usage:
  python run.py --config ./drizzle.config.ts --status
  python run.py --config ./drizzle.config.ts --push --dry-run
  python run.py --config ./drizzle.config.ts --generate --json
"""

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


def find_drizzle_bin(config_dir: str) -> str:
    """Find drizzle-kit binary."""
    # Try local node_modules
    for name in ["drizzle-kit.cmd", "drizzle-kit"]:
        local = Path(config_dir) / "node_modules" / ".bin" / name
        if local.exists():
            return str(local)
    # Try npx
    return "npx drizzle-kit"


def find_config(config_dir: str, config_arg: str = None) -> str:
    """Find drizzle config file."""
    if config_arg:
        cfg_path = Path(config_arg)
        if cfg_path.exists():
            return str(cfg_path)

    # Auto-detect
    for name in ["drizzle.config.ts", "drizzle.config.js", "drizzle.config.mjs"]:
        cfg = Path(config_dir) / name
        if cfg.exists():
            return str(cfg)

    return None


def run_drizzle_command(config_path: str, args_list: list, dry_run: bool = False) -> dict:
    """Run a drizzle-kit command."""
    config_dir = os.path.dirname(os.path.abspath(config_path))
    drizzle_bin = find_drizzle_bin(config_dir)

    if drizzle_bin == "npx drizzle-kit":
        cmd = ["npx", "drizzle-kit"] + args_list
    else:
        cmd = [drizzle_bin] + args_list

    result = {
        "command": " ".join(cmd),
        "config": config_path,
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
            cwd=config_dir,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=120,
            env={**os.environ, "DRIZZLE_CONFIG": config_path} if config_path else None,
        )
        result["exit_code"] = proc.returncode
        result["stdout"] = proc.stdout[:10000]
        result["stderr"] = proc.stderr[:5000]
    except subprocess.TimeoutExpired:
        result["error"] = "drizzle-kit command timed out (120s)"
    except FileNotFoundError:
        result["error"] = "drizzle-kit not found. Run 'npm install drizzle-kit' first."
    except Exception as e:
        result["error"] = str(e)

    return result


def main():
    parser = argparse.ArgumentParser(
        description="drizzle — drizzle-kit wrapper with --dry-run and --json support",
    )
    parser.add_argument("--config", default=None, help="Path to drizzle config file")
    parser.add_argument("--dir", default=os.getcwd(), help="Project directory (default: cwd)")
    parser.add_argument("--status", action="store_true", help="Check migration status")
    parser.add_argument("--generate", action="store_true", help="Generate migration files")
    parser.add_argument("--push", action="store_true", help="Push schema changes to database")
    parser.add_argument("--drop", action="store_true", help="Drop all tables (DANGEROUS)")
    parser.add_argument("--check", action="store_true", help="Check schema for differences")
    parser.add_argument("--dry-run", action="store_true", default=True, help="Preview only (default)")
    parser.add_argument("--no-dry-run", action="store_false", dest="dry_run", help="Actually run commands")
    parser.add_argument("--json", action="store_true", help="Output as JSON")

    args = parser.parse_args()

    config_path = find_config(args.dir, args.config)
    output = {
        "config_path": config_path,
        "config_found": config_path is not None,
        "dry_run": args.dry_run,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "results": {},
    }

    if not config_path:
        output["error"] = "No drizzle config found. Use --config or create drizzle.config.ts"
        if args.json:
            print(json.dumps(output, indent=2, ensure_ascii=False))
        else:
            print("ERROR: No drizzle config found.")
            print("  Expected: drizzle.config.ts, drizzle.config.js, or drizzle.config.mjs")
            print("  Use --config to specify the path.")
        sys.exit(1)

    os.path.dirname(os.path.abspath(config_path))

    if args.status:
        output["results"]["status"] = run_drizzle_command(config_path, ["check"], dry_run=args.dry_run)

    if args.generate:
        output["results"]["generate"] = run_drizzle_command(config_path, ["generate"], dry_run=args.dry_run)

    if args.push:
        output["results"]["push"] = run_drizzle_command(config_path, ["push"], dry_run=args.dry_run)

    if args.drop:
        output["results"]["drop"] = run_drizzle_command(config_path, ["drop"], dry_run=args.dry_run)

    if args.check:
        output["results"]["check"] = run_drizzle_command(config_path, ["check"], dry_run=args.dry_run)

    if not any([args.status, args.generate, args.push, args.drop, args.check]):
        # Default: show status
        output["results"]["status"] = run_drizzle_command(config_path, ["check"], dry_run=args.dry_run)

    if args.json:
        print(json.dumps(output, indent=2, ensure_ascii=False))
    else:
        mode = "[DRY-RUN]" if args.dry_run else "[LIVE]"
        print(f"{mode} drizzle — {config_path}")
        for action, res in output["results"].items():
            if isinstance(res, dict):
                action_emoji = "[DANGER]" if action == "drop" else f"[{action}]"
                if res.get("dry_run"):
                    print(f"  {action_emoji}: {res['stdout']}")
                elif res.get("error"):
                    print(f"  {action_emoji}: ERROR: {res['error']}")
                else:
                    status = "OK" if res.get("exit_code") == 0 else f"FAIL(exit={res.get('exit_code')})"
                    print(f"  {action_emoji}: {status}")

    has_error = any(
        r.get("error") or (r.get("exit_code") is not None and r["exit_code"] != 0)
        for r in output["results"].values()
        if isinstance(r, dict)
    )
    sys.exit(1 if has_error and not args.dry_run else 0)


if __name__ == "__main__":
    main()
