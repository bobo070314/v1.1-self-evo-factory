#!/usr/bin/env python3
"""
db-migrations — Prisma Migration Scripts
=========================================
Runs Prisma migration commands (cross-platform Python wrapper).
Supports: migrate dev, migrate status, migrate diff, db push.

Usage:
  python run.py --command status --schema ./prisma/schema.prisma
  python run.py --command dev           # default: --dry-run
  python run.py --command dev --no-dry-run
  python run.py --json --command status
"""

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


VALID_COMMANDS = {
    "dev": "prisma migrate dev",
    "status": "prisma migrate status",
    "diff": "prisma migrate diff",
    "push": "prisma db push",
    "reset": "prisma migrate reset",
    "deploy": "prisma migrate deploy",
    "generate": "prisma generate",
}


def find_schema_path(schema_arg=None):
    """Locate the Prisma schema file."""
    if schema_arg:
        path = Path(schema_arg)
        if path.is_file():
            return str(path.resolve())
        return None

    # Auto-detect
    search_dirs = [Path.cwd()]
    for d in search_dirs:
        for candidate in [
            d / "prisma" / "schema.prisma",
            d / "schema.prisma",
        ]:
            if candidate.is_file():
                return str(candidate.resolve())

    return None


def run_prisma_command(command, schema_path=None, dry_run=True, extra_args=None):
    """Execute a Prisma command."""
    if command not in VALID_COMMANDS:
        return {
            "success": False,
            "error": f"Unknown command: {command}. Valid: {', '.join(VALID_COMMANDS.keys())}",
        }

    cmd = ["npx"] + VALID_COMMANDS[command].split()

    if schema_path:
        cmd.extend(["--schema", schema_path])

    if command == "dev" and dry_run:
        # For dev with dry-run: prisma migrate dev --create-only
        # This creates the migration without applying it
        cmd.append("--create-only")

    if extra_args:
        cmd.extend(extra_args)

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=120,
        )

        return {
            "success": result.returncode == 0,
            "command": command,
            "full_command": " ".join(cmd),
            "exit_code": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "dry_run": dry_run,
            "schema": schema_path,
        }
    except FileNotFoundError:
        return {
            "success": False,
            "error": "npx not found. Please install Node.js and Prisma: npm install prisma --save-dev",
            "command": command,
        }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "error": "Prisma command timed out (120s)",
            "command": command,
        }


def parse_prisma_status(stdout):
    """Parse 'prisma migrate status' output."""
    status = {"applied": [], "pending": [], "database_ok": True}

    if "Database is up to date" in stdout or "No pending migrations" in stdout:
        return status

    for line in stdout.splitlines():
        line = line.strip()
        if "applied" in line.lower() and not line.startswith("Database"):
            status["applied"].append(line)
        elif "pending" in line.lower():
            # Next lines might list pending migrations
            pass

    if "error" in stdout.lower():
        status["database_ok"] = False

    return status


def main():
    parser = argparse.ArgumentParser(
        prog="db-migrations",
        description="Prisma migration scripts (cross-platform Python wrapper)",
    )
    parser.add_argument(
        "--command",
        choices=list(VALID_COMMANDS.keys()),
        default="status",
        help="Prisma command to run (default: status)",
    )
    parser.add_argument(
        "--schema",
        default=None,
        help="Path to schema.prisma (auto-detected if omitted)",
    )
    parser.add_argument(
        "--no-dry-run",
        action="store_true",
        help="Disable --create-only for migrate dev (applies migration immediately)",
    )
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--dry-run", action="store_true", help="Preview command without executing")
    args, unknown = parser.parse_known_args()

    # Resolve schema path
    schema_path = find_schema_path(args.schema)
    if not schema_path and args.command != "generate":
        result = {
            "success": False,
            "error": "Prisma schema not found. Specify with --schema or run from project root with prisma/schema.prisma",
            "command": args.command,
        }
        if args.json:
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            print(f"ERROR: {result['error']}", file=sys.stderr)
        return 1

    # Pre-flight: dry-run mode
    if args.dry_run:
        cmd = ["npx"] + VALID_COMMANDS[args.command].split()
        if schema_path:
            cmd.extend(["--schema", schema_path])
        if args.command == "dev" and not args.no_dry_run:
            cmd.append("--create-only")

        result = {
            "dry_run": True,
            "command": args.command,
            "full_command": " ".join(cmd),
            "schema": schema_path,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        if args.json:
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            print(f"[DRY-RUN] Command: {' '.join(cmd)}")
            print(f"[DRY-RUN] Schema: {schema_path or '(not specified)'}")
        return 0

    # Execute
    is_dry = not args.no_dry_run
    result = run_prisma_command(
        args.command,
        schema_path=schema_path,
        dry_run=is_dry,
        extra_args=unknown,
    )
    result["timestamp"] = datetime.now(timezone.utc).isoformat()

    # Parse status output
    if args.command == "status" and result.get("stdout"):
        result["parsed"] = parse_prisma_status(result["stdout"])

    if args.json:
        # Truncate for JSON
        if "stdout" in result and len(result.get("stdout", "")) > 5000:
            result["stdout"] = result["stdout"][-5000:]
        if "stderr" in result and len(result.get("stderr", "")) > 2000:
            result["stderr"] = result["stderr"][-2000:]
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        if result.get("success"):
            msg = f"SUCCESS: prisma migrate {args.command}"
            if result.get("dry_run"):
                msg += " (--create-only / dry-run mode)"
            print(msg)
            if result.get("parsed") and args.command == "status":
                parsed = result["parsed"]
                if parsed.get("applied"):
                    print(f"  Applied migrations: {len(parsed['applied'])}")
                if parsed.get("pending"):
                    print(f"  Pending migrations: {len(parsed['pending'])}")
        else:
            if "error" in result:
                print(f"ERROR: {result['error']}", file=sys.stderr)
            else:
                print(f"FAILED: prisma migrate {args.command} (exit code {result.get('exit_code')})", file=sys.stderr)
                if result.get("stderr"):
                    print(result["stderr"][:1000], file=sys.stderr)

    return 0 if result.get("success") else 1


if __name__ == "__main__":
    sys.exit(main())
