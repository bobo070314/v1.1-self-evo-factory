#!/usr/bin/env python3
"""markdown-linter: Lint markdown files for common formatting issues."""

import argparse
import json
import re
import sys
from pathlib import Path

VERSION = "1.0.1"
TOOLCHAIN = "Agnes Toolchain"


def read_file(path: Path):
    """Read file with graceful encoding error handling. Returns str or None."""
    for encoding in ("utf-8", "utf-8-sig", "latin-1"):
        try:
            return path.read_text(encoding=encoding)
        except (UnicodeDecodeError, UnicodeError):
            continue
        except FileNotFoundError:
            return None
        except OSError:
            return None
    return None


def lint_content(content: str, filepath: str) -> list[dict]:
    """Lint markdown content and return a list of issues."""
    issues = []
    lines = content.splitlines()

    # Track code block state
    in_code_block = False
    code_fence_pattern = re.compile(r"^(`{3,}|~{3,})")

    for i, line in enumerate(lines, start=1):
        # Check unclosed code blocks at end of file
        if in_code_block and i == len(lines):
            issues.append({
                "file": filepath,
                "line": i,
                "column": 1,
                "severity": "error",
                "message": "Unclosed code block (missing closing fence)",
                "rule": "unclosed-code-block"
            })

        # Track code block entry/exit
        fence_match = code_fence_pattern.match(line)
        if fence_match:
            if not in_code_block:
                in_code_block = True
                code_fence_char = fence_match.group(1)[0]
                code_fence_len = len(fence_match.group(1))
            else:
                # Check if this line closes the code block
                close_match = re.match(r"^(`{3,}|~{3,})\s*$", line)
                if close_match:
                    close_char = close_match.group(1)[0]
                    close_len = len(close_match.group(1))
                    if close_char == code_fence_char and close_len >= code_fence_len:
                        in_code_block = False

        # Check for duplicate headings
        heading_match = re.match(r"^(#{1,6})\s+(.+)$", line)
        if heading_match and not in_code_block:
            heading_text = heading_match.group(2).strip()
            heading_level = len(heading_match.group(1))
            key = f"{heading_level}:{heading_text}"
            if not hasattr(lint_content, "_headings"):
                lint_content._headings = {}
            if key in lint_content._headings:
                issues.append({
                    "file": filepath,
                    "line": i,
                    "column": 1,
                    "severity": "warning",
                    "message": f"Duplicate heading: '{heading_text}'",
                    "rule": "duplicate-heading",
                    "previous_line": lint_content._headings[key]
                })
            else:
                lint_content._headings[key] = i

        # Check missing blank lines after headings
        if heading_match and not in_code_block:
            if i < len(lines):
                next_line = lines[i]  # i is 1-based, lines is 0-based
                if next_line.strip() != "":
                    issues.append({
                        "file": filepath,
                        "line": i,
                        "column": 1,
                        "severity": "info",
                        "message": "Missing blank line after heading",
                        "rule": "missing-blank-after-heading"
                    })

        # Check missing blank lines before headings
        if heading_match and not in_code_block and i > 1:
            prev_line = lines[i - 2]  # i is 1-based
            if prev_line.strip() != "":
                issues.append({
                    "file": filepath,
                    "line": i,
                    "column": 1,
                    "severity": "info",
                    "message": "Missing blank line before heading",
                    "rule": "missing-blank-before-heading"
                })

        # Check trailing whitespace
        if line != line.rstrip() and line.strip() != "":
            issues.append({
                "file": filepath,
                "line": i,
                "column": len(line.rstrip()) + 1,
                "severity": "warning",
                "message": "Trailing whitespace",
                "rule": "trailing-whitespace"
            })

        # Check missing blank line after code block
        if in_code_block is False and i < len(lines):
            fence_match_next = code_fence_pattern.match(line)
            if fence_match_next:
                if i + 1 <= len(lines):
                    next_line_idx = i  # i is 1-based, next line is i (0-based)
                    if next_line_idx < len(lines):
                        next_line = lines[next_line_idx]
                        if next_line.strip() != "":
                            issues.append({
                                "file": filepath,
                                "line": i,
                                "column": 1,
                                "severity": "info",
                                "message": "Missing blank line after code block",
                                "rule": "missing-blank-after-code-block"
                            })

    # Reset headings dict for next file
    lint_content._headings = {}

    return issues


def lint_file(path: Path) -> list[dict]:
    """Lint a single markdown file."""
    content = read_file(path)
    if content is None:
        return [{
            "file": str(path),
            "line": 1,
            "column": 1,
            "severity": "error",
            "message": f"File not found: {path}",
            "rule": "file-not-found"
        }]

    try:
        return lint_content(content, str(path))
    except Exception as e:
        return [{
            "file": str(path),
            "line": 1,
            "column": 1,
            "severity": "error",
            "message": f"Error reading file: {e}",
            "rule": "read-error"
        }]


def format_text(issues: list[dict]) -> str:
    """Format issues as human-readable text."""
    if not issues:
        return "No issues found.\n"

    lines = []
    for issue in issues:
        line_num = issue.get("line", "?")
        col_num = issue.get("column", "?")
        severity = issue.get("severity", "unknown")
        message = issue.get("message", "")
        rule = issue.get("rule", "")
        filepath = issue.get("file", "")

        if line_num is not None and col_num is not None:
            loc = f"{filepath}:{line_num}:{col_num}"
        elif line_num is not None:
            loc = f"{filepath}:{line_num}"
        else:
            loc = filepath

        lines.append(f"[{severity.upper():7}] {loc} ({rule}) {message}")

    return "\n".join(lines) + "\n"


def format_json(issues: list[dict]) -> str:
    """Format issues as JSON."""
    return json.dumps(issues, indent=2, ensure_ascii=False) + "\n"


def main():
    parser = argparse.ArgumentParser(
        description="Lint markdown files to detect common formatting issues.",
        prog="markdown-linter"
    )
    parser.add_argument(
        "files",
        nargs="*",
        metavar="FILE",
        help="Markdown files to lint"
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"markdown-linter v{VERSION} (part of {TOOLCHAIN})",
        help="Show program version and exit"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="json_output",
        help="Output results in JSON format"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Dry run mode (check only, no modifications)"
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress output when no issues found"
    )

    args = parser.parse_args()

    # Handle no files provided
    if not args.files:
        # Read from stdin if no files provided
        if sys.stdin.isatty():
            if not args.quiet:
                parser.print_help()
            sys.exit(0)

        content = sys.stdin.read()
        if content:
            issues = lint_content(content, "<stdin>")
        else:
            issues = []
    else:
        issues = []
        for file_arg in args.files:
            path = Path(file_arg)
            if path.is_file():
                file_issues = lint_file(path)
                issues.extend(file_issues)
            else:
                issues.append({
                    "file": str(path),
                    "line": 1,
                    "column": 1,
                    "severity": "error",
                    "message": f"File not found: {path}",
                    "rule": "file-not-found"
                })

    # Output results
    if args.json_output:
        n_err = sum(1 for i in issues if i["severity"] == "error")
        n_warn = sum(1 for i in issues if i["severity"] in ("warning", "info"))
        payload = {
            "tool": "markdown-linter",
            "version": VERSION,
            "summary": {"error": n_err, "warning": n_warn},
            "issues": issues,
        }
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        if issues or not args.quiet:
            print(format_text(issues))

    # Exit-code semantics: 0 no errors / 1 errors / 2 warnings only
    n_err = sum(1 for i in issues if i["severity"] == "error")
    n_warn = sum(1 for i in issues if i["severity"] in ("warning", "info"))
    if n_err > 0:
        sys.exit(1)
    sys.exit(2 if n_warn > 0 else 0)


if __name__ == "__main__":
    main()