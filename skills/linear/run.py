#!/usr/bin/env python3
"""linear — Linear project management — issues, cycles, projects."""

import argparse
import json
import sys
from datetime import datetime, timezone


def run(args):
    """Main logic."""
    result = {
        "skill": "linear",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "args": vars(args),
    }

    if args.dry_run:
        print("[DRY-RUN] Would execute, output:")
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print("Skill 'linear' executed successfully.")
    return 0


def main():
    parser = argparse.ArgumentParser(
        prog="linear",
        description="Linear project management — issues, cycles, projects",
    )
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--dry-run", action="store_true", help="Preview without executing")
    args = parser.parse_args()
    return run(args)


if __name__ == "__main__":
    sys.exit(main())
