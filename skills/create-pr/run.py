#!/usr/bin/env python3
"""
create-pr — Create GitHub pull requests with templates.
Gracefully degrades when no GitHub token is available.

Usage:
  python run.py --title "Fix login bug" --body "This PR fixes..."
  python run.py --title "Add feature" --base main --head feature/new
  python run.py --title "..." --dry-run --template feature.md
  python run.py --title "..." --json
"""

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


PR_TEMPLATES = {
    "default": """## Summary
{body}

## Changes
- {body}

## Testing
- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] Manual testing completed

## Checklist
- [ ] Code follows project conventions
- [ ] Documentation updated
- [ ] No breaking changes
""",
    "feature": """## Feature
{body}

## Motivation
<!-- Why is this feature needed? -->

## Implementation
<!-- How is this feature implemented? -->

## Screenshots (if applicable)
<!-- Add screenshots -->

## Testing
- [ ] Unit tests added
- [ ] Existing tests pass

## Checklist
- [ ] Code reviewed
- [ ] Feature documented
- [ ] No regression
""",
    "fix": """## Bug Description
{body}

## Root Cause
<!-- What caused the bug? -->

## Fix
<!-- How did you fix it? -->

## Verification
<!-- How can we verify the fix works? -->

## Checklist
- [ ] Fix verified locally
- [ ] Regression tests pass
- [ ] No new issues introduced
""",
}


def get_default_branch(repo_path: str) -> str:
    """Detect the default branch of the repo."""
    cwd = repo_path or os.getcwd()
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=cwd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=10,
        )
        return proc.stdout.strip() or "main"
    except Exception:
        return "main"


def get_remote_info(repo_path: str) -> dict:
    """Get remote repository info from git config."""
    cwd = repo_path or os.getcwd()
    info = {"remote": None, "repo": None, "owner": None, "name": None}

    try:
        proc = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            cwd=cwd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=10,
        )
        remote_url = proc.stdout.strip()
        info["remote"] = remote_url

        # Parse owner/repo from URL
        # ssh: git@github.com:owner/repo.git
        # https: https://github.com/owner/repo.git
        m = re.search(r'[:/]([^/]+)/([^/]+?)(?:\.git)?$', remote_url)
        if m:
            info["owner"] = m.group(1)
            info["name"] = m.group(2)
            info["repo"] = f"{info['owner']}/{info['name']}"
    except Exception:
        pass

    return info


def get_branch_diff(base: str, head: str, repo_path: str) -> dict:
    """Get diff and commit info between two branches."""
    cwd = repo_path or os.getcwd()

    result = {
        "base": base,
        "head": head,
        "commits": [],
        "files_changed": [],
        "diff_summary": "",
        "error": None,
    }

    try:
        # Commits
        proc = subprocess.run(
            ["git", "log", f"{base}..{head}", "--oneline", "--no-merges"],
            cwd=cwd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
        )
        if proc.returncode == 0:
            result["commits"] = [c.strip() for c in proc.stdout.strip().split("\n") if c.strip()]

        # Files changed
        proc2 = subprocess.run(
            ["git", "diff", "--name-only", f"{base}...{head}"],
            cwd=cwd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
        )
        if proc2.returncode == 0:
            result["files_changed"] = [f.strip() for f in proc2.stdout.strip().split("\n") if f.strip()]

        # Diff stat
        proc3 = subprocess.run(
            ["git", "diff", "--stat", f"{base}...{head}"],
            cwd=cwd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
        )
        if proc3.returncode == 0:
            result["diff_summary"] = proc3.stdout.strip()
    except Exception as e:
        result["error"] = str(e)

    return result


def build_pr_body(body: str, template: str, diff_info: dict) -> str:
    """Build the full PR body using a template."""
    tmpl = PR_TEMPLATES.get(template, PR_TEMPLATES["default"])
    pr_body = tmpl.format(body=body)

    # Append diff info
    if diff_info and diff_info.get("commits"):
        pr_body += f"\n## Commits ({len(diff_info['commits'])})\n"
        for commit in diff_info["commits"][:20]:
            pr_body += f"- {commit}\n"

    if diff_info and diff_info.get("files_changed"):
        pr_body += f"\n## Files Changed ({len(diff_info['files_changed'])})\n"
        for f in diff_info["files_changed"][:30]:
            pr_body += f"- `{f}`\n"

    if diff_info and diff_info.get("diff_summary"):
        pr_body += f"\n## Diff Summary\n```\n{diff_info['diff_summary'][:2000]}\n```\n"

    return pr_body


def create_github_pr(title: str, body: str, base: str, head: str,
                     repo_path: str, dry_run: bool = True) -> dict:
    """Create a GitHub PR via gh CLI or API."""
    cwd = repo_path or os.getcwd()
    result = {
        "title": title,
        "base": base,
        "head": head,
        "dry_run": dry_run,
        "pr_url": None,
        "pr_number": None,
        "method": None,
        "error": None,
    }

    # Try gh CLI first
    try:
        gh_check = subprocess.run(
            ["gh", "auth", "status"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=10,
        )
        gh_available = gh_check.returncode == 0
    except FileNotFoundError:
        gh_available = False

    if gh_available:
        result["method"] = "gh-cli"
        if dry_run:
            result["pr_url"] = f"[DRY-RUN] Would create PR via gh CLI"
            return result

        try:
            proc = subprocess.run(
                ["gh", "pr", "create", "--title", title, "--body", body,
                 "--base", base, "--head", head],
                cwd=cwd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=30,
            )
            if proc.returncode == 0:
                output = proc.stdout.strip()
                result["pr_url"] = output
                m = re.search(r'pull/(\d+)', output)
                if m:
                    result["pr_number"] = int(m.group(1))
            else:
                result["error"] = proc.stderr.strip()
        except Exception as e:
            result["error"] = str(e)
    else:
        # Degrade gracefully: generate PR body and instructions
        result["method"] = "manual"
        result["pr_url"] = "[MANUAL] Create PR via GitHub web UI"
        remote_info = get_remote_info(cwd)
        if remote_info.get("repo"):
            result["manual_url"] = f"https://github.com/{remote_info['repo']}/compare/{base}...{head}?expand=1"
            result["pr_url"] = result["manual_url"]
        else:
            result["pr_url"] = f"[MANUAL] Create PR: {base} <- {head}"

    return result


def main():
    parser = argparse.ArgumentParser(
        description="create-pr — Create GitHub pull requests with templates",
    )
    parser.add_argument("--title", required=True, help="PR title")
    parser.add_argument("--body", default="", help="PR description")
    parser.add_argument("--base", default=None, help="Base branch (default: auto-detect)")
    parser.add_argument("--head", default=None, help="Head branch (default: current branch)")
    parser.add_argument("--template", default="default", choices=["default", "feature", "fix"], help="PR template")
    parser.add_argument("--dir", default=os.getcwd(), help="Repository directory (default: cwd)")
    parser.add_argument("--dry-run", action="store_true", default=True, help="Preview only (default)")
    parser.add_argument("--no-dry-run", action="store_false", dest="dry_run", help="Actually create PR")
    parser.add_argument("--json", action="store_true", help="Output as JSON")

    args = parser.parse_args()

    # Auto-detect branches
    base = args.base or get_default_branch(args.dir)
    head = args.head or get_default_branch(args.dir)

    # Get diff info for the PR body
    diff_info = get_branch_diff(base, head, args.dir)
    pr_body = build_pr_body(args.body, args.template, diff_info)

    # Create PR
    pr_result = create_github_pr(args.title, pr_body, base, head, args.dir, dry_run=args.dry_run)

    # Remote info
    remote_info = get_remote_info(args.dir)

    output = {
        "title": args.title,
        "template": args.template,
        "base": base,
        "head": head,
        "dry_run": args.dry_run,
        "remote": remote_info,
        "diff": diff_info,
        "pr": pr_result,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    if args.json:
        # For JSON output, include body preview but truncate
        output["body_preview"] = pr_body[:500]
        print(json.dumps(output, indent=2, ensure_ascii=False))
    else:
        mode = "[DRY-RUN]" if args.dry_run else "[CREATING]"
        print(f"{mode} create-pr: '{args.title}'")
        print(f"  Base: {base} <- Head: {head}")
        if remote_info.get("repo"):
            print(f"  Repo: {remote_info['repo']}")
        print(f"  Template: {args.template}")

        if diff_info.get("commits"):
            print(f"  Commits: {len(diff_info['commits'])}")
        if diff_info.get("files_changed"):
            print(f"  Files changed: {len(diff_info['files_changed'])}")

        print(f"\n  PR URL: {pr_result['pr_url']}")
        if pr_result.get("manual_url"):
            print(f"  Open: {pr_result['manual_url']}")

        if not args.dry_run:
            print(f"\n  Method: {pr_result['method']}")
            if pr_result.get("error"):
                print(f"  ERROR: {pr_result['error']}")

        # Show PR body preview
        print(f"\n{'='*60}")
        print("PR Body Preview:")
        print(f"{'='*60}")
        print(pr_body[:2000])
        if len(pr_body) > 2000:
            print("... (truncated)")

    has_error = bool(pr_result.get("error") and not args.dry_run)
    sys.exit(1 if has_error else 0)


if __name__ == "__main__":
    main()
