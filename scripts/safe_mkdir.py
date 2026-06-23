#!/usr/bin/env python3
"""scripts/safe_mkdir.py — Idempotent directory creation.
Returns exit 0 even if directories already exist. No stderr noise.
"""

import sys
from pathlib import Path


def main():
    created = 0
    skipped = 0
    for arg in sys.argv[1:]:
        p = Path(arg)
        if p.exists():
            skipped += 1
        else:
            p.mkdir(parents=True, exist_ok=True)
            created += 1
    if created or skipped:
        print(f"safe_mkdir: {created} created, {skipped} already exist", file=sys.stdout)
    return 0


if __name__ == "__main__":
    sys.exit(main())
