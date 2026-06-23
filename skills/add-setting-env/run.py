#!/usr/bin/env python3
"""add-setting-env — Environment Variable Validator.
=================================================
Compares .env.example with .env to find:
  - Missing variables (in .env.example but not in .env)
  - Extra variables (in .env but not in .env.example)
  - Mismatched values (optional check against defaults)

Usage:
  python run.py --env .env --example .env.example
  python run.py --json --env .env --example .env.example
  python run.py --dry-run --example .env.example
"""

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path


def parse_env_file(filepath):
    """Parse a .env file, returning {KEY: value} dict.

    Handles:
      - KEY=value
      - KEY="value"
      - KEY='value'
      - export KEY=value
      - Comments (# ...)
      - Blank lines
    """
    variables = {}
    path = Path(filepath)

    if not path.is_file():
        return None, f"File not found: {filepath}"

    try:
        content = path.read_text(encoding="utf-8")
    except Exception as e:
        return None, f"Cannot read {filepath}: {e}"

    for line_no, line in enumerate(content.splitlines(), 1):
        # Strip comments (but not comments inside quotes)
        stripped = line.strip()

        # Skip blank lines and full-line comments
        if not stripped or stripped.startswith("#"):
            continue

        # Handle export prefix
        if stripped.startswith("export "):
            stripped = stripped[7:].strip()

        # Parse KEY=VALUE
        match = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$", stripped)
        if not match:
            continue  # Skip malformed lines

        key = match.group(1)
        raw_value = match.group(2).strip()

        # Strip surrounding quotes
        if raw_value.startswith('"') and raw_value.endswith('"'):
            value = raw_value[1:-1]
        elif raw_value.startswith("'") and raw_value.endswith("'"):
            value = raw_value[1:-1]
        else:
            value = raw_value

        variables[key] = value

    return variables, None


def validate_env(example_vars, env_vars):
    """Compare example vars against env vars and return diff."""
    missing = {}
    extra = {}
    value_mismatches = {}

    for key in sorted(example_vars):
        if key not in env_vars:
            missing[key] = example_vars[key]
        else:
            # Check if the key exists but has no value set
            if env_vars[key] == "" and example_vars[key] != "":
                value_mismatches[key] = {
                    "expected": example_vars[key],
                    "actual": "(empty)",
                    "reason": "Empty value in .env",
                }

    for key in sorted(env_vars):
        if key not in example_vars:
            extra[key] = env_vars[key]

    return {
        "missing": missing,
        "extra": extra,
        "value_mismatches": value_mismatches,
        "total_expected": len(example_vars),
        "total_actual": len(env_vars),
        "is_valid": len(missing) == 0 and len(value_mismatches) == 0,
    }


def auto_resolve_paths(env_arg, example_arg):
    """Auto-resolve file paths with common defaults."""
    results = {"env": None, "example": None, "errors": []}

    cwd = Path.cwd()
    search_paths = [cwd] + list(cwd.parents)[:3]

    # Resolve .env.example
    if example_arg:
        p = Path(example_arg)
        if p.is_file():
            results["example"] = str(p.resolve())
        else:
            results["errors"].append(f"Example file not found: {example_arg}")
    else:
        for base in search_paths:
            for name in [".env.example", ".env.sample", ".env.template", "env.example"]:
                candidate = base / name
                if candidate.is_file():
                    results["example"] = str(candidate.resolve())
                    break
            if results["example"]:
                break
        if not results["example"]:
            results["errors"].append("No .env.example found. Specify with --example or create one.")

    # Resolve .env
    if env_arg:
        p = Path(env_arg)
        if p.is_file():
            results["env"] = str(p.resolve())
        else:
            results["errors"].append(f".env file not found: {env_arg}")
    else:
        for base in search_paths:
            candidate = base / ".env"
            if candidate.is_file():
                results["env"] = str(candidate.resolve())
                break
        if not results["env"]:
            results["errors"].append("No .env found. Specify with --env or create one.")

    return results


def generate_suggestions(missing, extra, example_path):
    """Generate actionable suggestions."""
    suggestions = []

    if missing:
        lines = []
        for key in sorted(missing):
            val = missing[key]
            if val:
                lines.append(f"{key}={val}")
            else:
                lines.append(f"{key}=")
        suggestions.append(
            f"Add {len(missing)} missing variable(s) to .env:\n" + "\n".join(f"  {line}" for line in lines)
        )

    if extra:
        extra_keys = sorted(extra)
        suggestions.append(
            f"Found {len(extra)} variable(s) in .env not in {Path(example_path).name}: {', '.join(extra_keys)}"
        )

    if not suggestions:
        suggestions.append("All required variables are present. No changes needed.")

    return suggestions


def main():
    parser = argparse.ArgumentParser(
        prog="add-setting-env",
        description="Validate .env against .env.example — find missing/extra variables",
    )
    parser.add_argument(
        "--env",
        default=None,
        help="Path to .env file (auto-detected if omitted)",
    )
    parser.add_argument(
        "--example",
        default=None,
        help="Path to .env.example file (auto-detected if omitted)",
    )
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--dry-run", action="store_true", help="Preview without full validation")
    args = parser.parse_args()

    timestamp = datetime.now(timezone.utc).isoformat()

    # Resolve paths
    resolved = auto_resolve_paths(args.env, args.example)

    if resolved["errors"]:
        result = {
            "success": False,
            "timestamp": timestamp,
            "errors": resolved["errors"],
            "env_path": resolved["env"],
            "example_path": resolved["example"],
        }
        if args.json:
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            for err in resolved["errors"]:
                print(f"ERROR: {err}", file=sys.stderr)
        return 1

    env_path = resolved["env"]
    example_path = resolved["example"]

    if args.dry_run:
        result = {
            "dry_run": True,
            "timestamp": timestamp,
            "env_path": env_path,
            "example_path": example_path,
        }
        if args.json:
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            print("[DRY-RUN] Would validate:")
            print(f"  .env:         {env_path}")
            print(f"  .env.example: {example_path}")
        return 0

    # Parse both files
    example_vars, err = parse_env_file(example_path)
    if err:
        result = {"success": False, "timestamp": timestamp, "error": err}
        if args.json:
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            print(f"ERROR: {err}", file=sys.stderr)
        return 1

    env_vars, err = parse_env_file(env_path)
    if err:
        result = {"success": False, "timestamp": timestamp, "error": err}
        if args.json:
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            print(f"ERROR: {err}", file=sys.stderr)
        return 1

    # Validate
    validation = validate_env(example_vars, env_vars)
    suggestions = generate_suggestions(validation["missing"], validation["extra"], example_path)

    result = {
        "success": validation["is_valid"],
        "timestamp": timestamp,
        "env_path": env_path,
        "example_path": example_path,
        "validation": validation,
        "suggestions": suggestions,
    }

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print("ENV Validation Report")
        print(f"  .env:         {env_path}")
        print(f"  .env.example: {example_path}")
        print(f"  Expected: {validation['total_expected']} variables")
        print(f"  Actual:   {validation['total_actual']} variables")
        print()

        if validation["is_valid"]:
            print("✓ All required variables are present.")
        else:
            if validation["missing"]:
                print(f"✗ Missing variables ({len(validation['missing'])}):")
                for key in sorted(validation["missing"]):
                    val = validation["missing"][key]
                    print(f"    {key}" + (f" (default: {val})" if val else ""))
            if validation["extra"]:
                print(f"⚠ Extra variables in .env ({len(validation['extra'])}):")
                for key in sorted(validation["extra"]):
                    print(f"    {key}")
            if validation["value_mismatches"]:
                print(f"⚠ Empty values ({len(validation['value_mismatches'])}):")
                for key in sorted(validation["value_mismatches"]):
                    print(f"    {key}: expected {validation['value_mismatches'][key]['expected']}")

            print()
            print("Suggestions:")
            for s in suggestions:
                print(s)

    return 0 if validation["is_valid"] else 1


if __name__ == "__main__":
    sys.exit(main())
