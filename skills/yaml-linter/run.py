#!/usr/bin/env python3
"""yaml-linter: Lint YAML files for syntax errors."""

import argparse
import json
import os
import re
import sys

VERSION = "1.0.0"

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False


def parse_args():
    parser = argparse.ArgumentParser(
        description="Lint YAML files for syntax errors including indentation, colons, and quote mismatches."
    )
    parser.add_argument("files", nargs="*", help="YAML files to lint")
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {VERSION}"
    )
    parser.add_argument(
        "--json", action="store_true", dest="json_output",
        help="Output results as JSON"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Parse but do not load/validate with PyYAML (heuristic only)"
    )
    return parser.parse_args()


def check_indentation(line, lineno, errors):
    """Check for inconsistent indentation."""
    stripped = line.rstrip()
    if not stripped or stripped.lstrip().startswith("#"):
        return
    indent = len(stripped) - len(stripped.lstrip())
    # Indentation should be consistent (typically multiples of 2 or 4)
    if indent > 0:
        # Check if indentation is a multiple of 2
        if indent % 2 != 0:
            errors.append({
                "line": lineno,
                "type": "indentation",
                "message": f"Inconsistent indentation at column {indent}"
            })


def check_colons(line, lineno, errors):
    """Check for malformed colons (e.g., missing space after colon in mappings)."""
    stripped = line.rstrip()
    if not stripped:
        return
    # Match key: value pattern - colon not followed by space or end of line
    # But allow URLs and other valid cases
    if re.search(r":[^ \t\n\r\f\v]", stripped) and not re.search(r"https?://", stripped):
        # Check if it's a simple key: value
        if re.match(r"^[^#\s]+:", stripped):
            errors.append({
                "line": lineno,
                "type": "colon",
                "message": "Missing space after colon in key-value pair"
            })


def check_quotes(line, lineno, errors):
    """Check for mismatched quotes."""
    stripped = line.rstrip()
    if not stripped:
        return
    # Count single and double quotes (simple heuristic)
    single_count = stripped.count("'") - stripped.count("\\'")
    double_count = stripped.count('"') - stripped.count('\\"')
    if single_count % 2 != 0:
        errors.append({
            "line": lineno,
            "type": "quote",
            "message": "Mismatched single quotes"
        })
    if double_count % 2 != 0:
        errors.append({
            "line": lineno,
            "type": "quote",
            "message": "Mismatched double quotes"
        })


def heuristic_validate(content, filename, errors):
    """Perform heuristic validation on YAML content."""
    lines = content.split("\n")
    for i, line in enumerate(lines, start=1):
        check_indentation(line, i, errors)
        check_colons(line, i, errors)
        check_quotes(line, i, errors)
    return errors


def pyyaml_validate(content, filename, errors, dry_run=False):
    """Validate using PyYAML if available."""
    if not HAS_YAML or dry_run:
        return heuristic_validate(content, filename, errors)
    try:
        yaml.safe_load(content)
    except yaml.YAMLError as e:
        errors.append({
            "line": getattr(e, "problem_mark", None) and e.problem_mark.line + 1 or "unknown",
            "type": "syntax",
            "message": str(e)
        })
    return errors


def lint_file(filepath, dry_run=False):
    """Lint a single YAML file."""
    errors = []
    if not os.path.exists(filepath):
        errors.append({
            "line": 0,
            "type": "file",
            "message": f"File not found: {filepath}"
        })
        return errors
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
    except UnicodeDecodeError:
        try:
            with open(filepath, "r", encoding="latin-1") as f:
                content = f.read()
        except Exception as e:
            errors.append({
                "line": 0,
                "type": "encoding",
                "message": f"Encoding error: {e}"
            })
            return errors
    except Exception as e:
        errors.append({
            "line": 0,
            "type": "read",
            "message": f"Error reading file: {e}"
        })
        return errors
    if not content.strip():
        return errors
    return pyyaml_validate(content, filepath, errors, dry_run)


def main():
    args = parse_args()
    files = args.files if args.files else ["-"]
    all_results = []
    for filepath in files:
        if filepath == "-":
            # Read from stdin
            content = sys.stdin.read()
            errors = pyyaml_validate(content, "<stdin>", [], args.dry_run)
            all_results.append({
                "file": "<stdin>",
                "errors": errors
            })
        else:
            errors = lint_file(filepath, args.dry_run)
            all_results.append({
                "file": filepath,
                "errors": errors
            })
    if args.json_output:
        print(json.dumps(all_results, indent=2))
    else:
        for result in all_results:
            if result["errors"]:
                print(f"{result['file']}:")
                for err in result["errors"]:
                    line_info = f"line {err['line']}: " if err["line"] != 0 else ""
                    print(f"  {line_info}[{err['type']}] {err['message']}")
            else:
                print(f"{result['file']}: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())