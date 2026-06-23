#!/usr/bin/env python3
"""create-skill — Skill Factory.
=============================
Creates a new skill directory from a template, generating:
  - SKILL.md
  - _meta.json
  - run.py (skeleton)

Usage:
  python run.py --name my-skill --description "does things" [--template basic|advanced]
  python run.py --help
  python run.py --json --name my-skill --description "test"
"""

import argparse
import json
import sys
from pathlib import Path

SKILLS_DIR = Path(__file__).resolve().parent.parent

SKILL_MD_TEMPLATE = """---
name: {name}
description: {description}
version: 0.1.0
type: skill
status: ready
---

# {name}

{description}

## Usage

```bash
python run.py --help
python run.py --some-arg
```

## Status
- [x] Implementation
- [ ] Tests
- [ ] Documentation
"""

RUN_PY_TEMPLATE = '''#!/usr/bin/env python3
"""{name} — {description}"""

import argparse
import json
import sys
from datetime import datetime, timezone


def run(args):
    """Main logic."""
    result = {{
        "skill": "{name}",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "args": vars(args),
    }}

    if args.dry_run:
        print("[DRY-RUN] Would execute, output:")
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"Skill '{name}' executed successfully.")
    return 0


def main():
    parser = argparse.ArgumentParser(
        prog="{name}",
        description="{description}",
    )
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--dry-run", action="store_true", help="Preview without executing")
    args = parser.parse_args()
    return run(args)


if __name__ == "__main__":
    sys.exit(main())
'''

ADVANCED_RUN_PY_TEMPLATE = '''#!/usr/bin/env python3
"""{name} — {description}

Advanced template with subcommand support and logging.
"""

import argparse
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] {name}: %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
log = logging.getLogger("{name}")


def cmd_build(args):
    """Build command handler."""
    log.info("Running build...")
    result = {{"action": "build", "status": "ok"}}
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print("Build completed.")
    return 0


def cmd_clean(args):
    """Clean command handler."""
    log.info("Running clean...")
    result = {{"action": "clean", "status": "ok"}}
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print("Clean completed.")
    return 0


def main():
    parser = argparse.ArgumentParser(
        prog="{name}",
        description="{description}",
    )
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--dry-run", action="store_true", help="Preview without executing")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose logging")

    subparsers = parser.add_subparsers(dest="command", help="Subcommands")

    bp = subparsers.add_parser("build", help="Build the project")
    bp.set_defaults(func=cmd_build)

    cp = subparsers.add_parser("clean", help="Clean artifacts")
    cp.set_defaults(func=cmd_clean)

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    if args.dry_run:
        log.info("[DRY-RUN] Would execute command=%s", args.command or "(none)")
        return 0

    if hasattr(args, "func"):
        return args.func(args)

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
'''


def create_skill(name, description, template="basic", base_dir=None):
    """Create a new skill directory with all required files."""
    target_dir = Path(base_dir) if base_dir else SKILLS_DIR
    skill_dir = target_dir / name

    if skill_dir.exists():
        return {
            "success": False,
            "error": f"Skill directory already exists: {skill_dir}",
        }

    files_created = []

    try:
        skill_dir.mkdir(parents=True, exist_ok=False)
    except OSError as e:
        return {"success": False, "error": f"Cannot create directory: {e}"}

    try:
        # SKILL.md
        skill_md = SKILL_MD_TEMPLATE.format(name=name, description=description)
        (skill_dir / "SKILL.md").write_text(skill_md, encoding="utf-8")
        files_created.append(str(skill_dir / "SKILL.md"))

        # _meta.json
        meta = {
            "name": name,
            "description": description,
            "version": "0.1.0",
            "status": "ready",
            "entry": "run.py",
        }
        (skill_dir / "_meta.json").write_text(
            json.dumps(meta, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        files_created.append(str(skill_dir / "_meta.json"))

        # run.py
        if template == "advanced":
            run_content = ADVANCED_RUN_PY_TEMPLATE.format(name=name, description=description)
        else:
            run_content = RUN_PY_TEMPLATE.format(name=name, description=description)
        (skill_dir / "run.py").write_text(run_content, encoding="utf-8")
        files_created.append(str(skill_dir / "run.py"))

    except OSError as e:
        return {"success": False, "error": f"Write error: {e}"}

    return {
        "success": True,
        "skill_dir": str(skill_dir),
        "name": name,
        "template": template,
        "files_created": files_created,
    }


def main():
    parser = argparse.ArgumentParser(
        prog="create-skill",
        description="Skill factory — creates new skill directories from templates",
    )
    parser.add_argument(
        "--name",
        required=True,
        help="Skill name (directory name, e.g. my-skill)",
    )
    parser.add_argument(
        "--description",
        required=True,
        help="Skill description",
    )
    parser.add_argument(
        "--template",
        choices=["basic", "advanced"],
        default="basic",
        help="Template type (default: basic)",
    )
    parser.add_argument(
        "--dir",
        default=None,
        help="Base directory for the skill (default: skills/ dir)",
    )
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="Preview only, no file creation (default)",
    )
    parser.add_argument(
        "--no-dry-run",
        action="store_false",
        dest="dry_run",
        help="Actually create files",
    )

    args = parser.parse_args()

    # Validate name
    name = args.name.strip()
    if not name or "/" in name or "\\" in name:
        result = {"success": False, "error": f"Invalid skill name: {args.name!r}"}
        if args.json:
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            print(f"ERROR: {result['error']}", file=sys.stderr)
        return 1

    base_dir = args.dir if args.dir else None

    if args.dry_run:
        target_dir = Path(base_dir) if base_dir else SKILLS_DIR
        result = {
            "dry_run": True,
            "name": name,
            "description": args.description,
            "template": args.template,
            "target_dir": str(target_dir / name),
        }
        if args.json:
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            print(f"[DRY-RUN] Would create skill '{name}' at {result['target_dir']}")
            print(f"  Description: {args.description}")
            print(f"  Template: {args.template}")
        return 0

    result = create_skill(name, args.description, args.template, base_dir)

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        if result["success"]:
            print(f"SUCCESS: Skill '{name}' created at {result['skill_dir']}")
            print(f"  Template: {args.template}")
            print("  Files:")
            for f in result["files_created"]:
                print(f"    - {f}")
        else:
            print(f"ERROR: {result['error']}", file=sys.stderr)

    return 0 if result["success"] else 1


if __name__ == "__main__":
    sys.exit(main())
