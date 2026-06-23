#!/usr/bin/env python3
"""
release-notes-generator — Generate release notes from git history.
Parses git log between two revisions and generates organized release notes.

Usage:
  python run.py --from v1.0.0 --to v1.1.0
  python run.py --from v1.0.0 --json
  python run.py --last-tag --format markdown
"""

import argparse
import json
import os
import re
import subprocess
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path


COMMIT_PATTERNS = {
    "feat": {"label": "Features", "emoji": "✨"},
    "fix": {"label": "Bug Fixes", "emoji": "🐛"},
    "docs": {"label": "Documentation", "emoji": "📝"},
    "style": {"label": "Styling", "emoji": "💄"},
    "refactor": {"label": "Refactoring", "emoji": "♻️"},
    "perf": {"label": "Performance", "emoji": "⚡"},
    "test": {"label": "Tests", "emoji": "✅"},
    "chore": {"label": "Chores", "emoji": "🔧"},
    "ci": {"label": "CI/CD", "emoji": "👷"},
    "build": {"label": "Build", "emoji": "📦"},
    "revert": {"label": "Reverts", "emoji": "⏪"},
    "security": {"label": "Security", "emoji": "🔒"},
    "deps": {"label": "Dependencies", "emoji": "📌"},
    "breaking": {"label": "BREAKING CHANGES", "emoji": "💥"},
    "other": {"label": "Other", "emoji": "📋"},
}

CONVENTIONAL_COMMIT_RE = re.compile(
    r'^(?P<type>\w+)(?:\((?P<scope>[^)]+)\))?(?P<breaking>!)?:\s*(?P<message>.+)$',
    re.IGNORECASE,
)

BREAKING_RE = re.compile(r'BREAKING CHANGE:', re.IGNORECASE)


def get_git_log(from_ref: str, to_ref: str, repo_path: str = None) -> dict:
    """Get git log between two refs."""
    cwd = repo_path or os.getcwd()

    if to_ref:
        range_spec = f"{from_ref}..{to_ref}"
    else:
        range_spec = from_ref

    result = {
        "range": range_spec,
        "from_ref": from_ref,
        "to_ref": to_ref or "HEAD",
        "commits": [],
        "error": None,
    }

    try:
        # Check if in a git repo
        subprocess.run(
            ["git", "rev-parse", "--git-dir"],
            cwd=cwd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        result["error"] = "Not a git repository or git not found"
        return result

    try:
        proc = subprocess.run(
            [
                "git", "log", range_spec,
                "--pretty=format:%H|%an|%ae|%ai|%s",
                "--no-merges",
            ],
            cwd=cwd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
        )
        if proc.returncode != 0:
            result["error"] = f"git log failed: {proc.stderr.strip()}"
            return result

        for line in proc.stdout.strip().split("\n"):
            if not line.strip():
                continue
            parts = line.split("|", 4)
            if len(parts) >= 5:
                sha, author, email, date_str, subject = parts
                result["commits"].append({
                    "sha": sha[:8],
                    "full_sha": sha,
                    "author": author,
                    "email": email,
                    "date": date_str,
                    "subject": subject,
                })

        result["commit_count"] = len(result["commits"])
    except subprocess.TimeoutExpired:
        result["error"] = "git log timed out"
    except Exception as e:
        result["error"] = str(e)

    return result


def classify_commit(subject: str) -> tuple:
    """Classify a commit message into a category."""
    m = CONVENTIONAL_COMMIT_RE.match(subject)
    if m:
        ctype = m.group("type").lower()
        scope = m.group("scope") or ""
        msg = m.group("message")
        is_breaking = bool(m.group("breaking")) or bool(BREAKING_RE.search(subject))

        if is_breaking:
            return "breaking", msg, scope

        if ctype in COMMIT_PATTERNS and ctype != "breaking":
            return ctype, msg, scope

    # Check for breaking changes anywhere
    if BREAKING_RE.search(subject):
        return "breaking", subject, ""

    return "other", subject, ""


def generate_notes(git_data: dict, format: str = "markdown", version: str = None) -> str:
    """Generate release notes from git data."""
    if git_data.get("error"):
        return f"Error: {git_data['error']}"

    commits = git_data.get("commits", [])
    if not commits:
        return "No commits found in this range."

    categorized = defaultdict(list)
    for commit in commits:
        ctype, message, scope = classify_commit(commit["subject"])
        categorized[ctype].append({
            "sha": commit["sha"],
            "subject": message,
            "scope": scope,
            "author": commit["author"],
        })

    if format == "json":
        cat_data = {}
        for cat, items in categorized.items():
            info = COMMIT_PATTERNS.get(cat, COMMIT_PATTERNS["other"])
            cat_data[info["label"]] = [
                {
                    "sha": i["sha"],
                    "message": i["subject"],
                    "scope": i["scope"],
                    "author": i["author"],
                } for i in items
            ]
        return json.dumps({
            "version": version or git_data.get("from_ref", "Unnamed"),
            "range": git_data["range"],
            "commit_count": git_data["commit_count"],
            "categories": cat_data,
        }, indent=2, ensure_ascii=False)

    # Markdown format
    lines = []
    version_title = version or git_data.get("from_ref", "Release")
    lines.append(f"# {version_title}")
    lines.append(f"")
    lines.append(f"**Range:** `{git_data['range']}`  ")
    lines.append(f"**Commits:** {git_data['commit_count']}  ")
    lines.append(f"**Date:** {datetime.now(timezone.utc).strftime('%Y-%m-%d')}  ")
    lines.append("")

    for cat_key in ["breaking", "feat", "fix", "perf", "refactor", "security",
                    "deps", "docs", "test", "style", "ci", "build", "chore", "revert", "other"]:
        items = categorized.get(cat_key, [])
        if not items:
            continue
        info = COMMIT_PATTERNS.get(cat_key, COMMIT_PATTERNS["other"])
        lines.append(f"## {info['emoji']} {info['label']}")
        lines.append("")
        for item in items:
            scope_str = f"**({item['scope']})** " if item["scope"] else ""
            lines.append(f"- {item['sha']}: {scope_str}{item['subject']} (@{item['author']})")
        lines.append("")

    return "\n".join(lines)


def get_latest_tags(cwd: str = None) -> list:
    """Get the two most recent tags."""
    cwd = cwd or os.getcwd()
    try:
        proc = subprocess.run(
            ["git", "tag", "--sort=-creatordate"],
            cwd=cwd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=10,
        )
        tags = [t for t in proc.stdout.strip().split("\n") if t]
        return tags[:2]
    except Exception:
        return []


def main():
    parser = argparse.ArgumentParser(
        description="release-notes-generator — Generate release notes from git history",
    )
    parser.add_argument("--from", dest="from_ref", default=None, help="Starting ref/tag/commit")
    parser.add_argument("--to", dest="to_ref", default="HEAD", help="Ending ref/tag/commit (default: HEAD)")
    parser.add_argument("--last-tag", action="store_true", help="Use the most recent two tags")
    parser.add_argument("--version", default=None, help="Version label for the release")
    parser.add_argument("--dir", default=os.getcwd(), help="Git repository path (default: cwd)")
    parser.add_argument("--format", default="markdown", choices=["markdown", "json"], help="Output format")
    parser.add_argument("--output", default=None, help="Write output to file")
    parser.add_argument("--dry-run", action="store_true", default=True, help="Preview only (default)")
    parser.add_argument("--no-dry-run", action="store_false", dest="dry_run", help="Write to --output file")
    parser.add_argument("--json", action="store_true", help="JSON output (shorthand for --format json)")

    args = parser.parse_args()

    if args.json:
        args.format = "json"

    # Determine from/to refs
    if args.last_tag:
        tags = get_latest_tags(args.dir)
        if len(tags) >= 2:
            from_ref = tags[1]
            to_ref = tags[0]
        elif len(tags) == 1:
            from_ref = tags[0]
            to_ref = "HEAD"
        else:
            print("ERROR: No tags found in repository.", file=sys.stderr)
            sys.exit(1)
    elif args.from_ref:
        from_ref = args.from_ref
        to_ref = args.to_ref
    else:
        # Default: last tag to HEAD
        tags = get_latest_tags(args.dir)
        from_ref = tags[0] if tags else "HEAD~50"
        to_ref = "HEAD"

    git_data = get_git_log(from_ref, to_ref, args.dir)
    notes = generate_notes(git_data, format=args.format, version=args.version)

    # Output
    if args.output and not args.dry_run:
        try:
            Path(args.output).write_text(notes, encoding="utf-8")
            print(f"Release notes written to: {args.output}")
        except Exception as e:
            print(f"ERROR writing to {args.output}: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        if args.output:
            print(f"[DRY-RUN] Would write to: {args.output}")
            print("---")
        print(notes)

    if git_data.get("error"):
        sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main()
