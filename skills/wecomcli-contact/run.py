#!/usr/bin/env python3
"""wecomcli-contact — WeCom contact queries — users, departments, tags."""

import argparse
import json
import sys
from datetime import datetime, timezone


def run(args):
    """Main logic."""
    result = {
        "skill": "wecomcli-contact",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "args": vars(args),
    }

    if args.dry_run:
        print("[DRY-RUN] Would execute, output:")
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print("Skill 'wecomcli-contact' executed successfully.")
    return 0


def main():
    parser = argparse.ArgumentParser(
        prog="wecomcli-contact",
        description="WeCom contact queries — users, departments, tags",
    )
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--dry-run", action="store_true", help="Preview without executing")
    args = parser.parse_args()
    return run(args)


if __name__ == "__main__":
    sys.exit(main())
