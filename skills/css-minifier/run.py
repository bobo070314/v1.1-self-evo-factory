#!/usr/bin/env python3
"""css-minifier — Industrial-grade CSS minifier.

Compresses CSS (comments / whitespace / redundant semicolons) while preserving
semantic equivalence. Professional CLI: tool-named version, exit-code
semantics, honest --dry-run, and machine-readable JSON.

Usage:
  python run.py input.css
  python run.py input.css --json
  python run.py input.css --dry-run      # validate path only
  echo "body { color: red; }" | python run.py -
  python run.py --version
"""

import argparse
import json
import sys
from pathlib import Path

VERSION = "1.0.1"
TOOLCHAIN = "Agnes Toolchain"


def minify_css(css: str) -> str:
    """Minify CSS: strip comments/whitespace/redundant semicolons outside strings."""
    if not css or not css.strip():
        return ""
    result = []
    i = 0
    length = len(css)
    in_string = None
    in_comment = False
    in_url = False

    while i < length:
        ch = css[i]

        if in_string:
            result.append(ch)
            if ch == "\\" and i + 1 < length:
                i += 1
                result.append(css[i])
            elif ch == in_string:
                in_string = None
            i += 1
            continue

        if ch in ('"', "'"):
            in_string = ch
            result.append(ch)
            i += 1
            continue

        if not in_comment and ch == "/" and i + 1 < length and css[i + 1] == "*":
            in_comment = True
            i += 2
            continue

        if in_comment:
            if ch == "*" and i + 1 < length and css[i + 1] == "/":
                in_comment = False
                i += 2
                continue
            i += 1
            continue

        if ch in (" ", "\t", "\n", "\r"):
            if result and result[-1] not in (" ", "\t", "\n", "\r", "{", "}", ":", ",", ";", "("):
                result.append(" ")
            i += 1
            continue

        if ch == ":" and not in_url:
            if result and result[-1] == "u" and "".join(result[-4:]).lower() == "url":
                in_url = True
            result.append(ch)
            i += 1
            continue

        if ch == ")":
            in_url = False
            result.append(ch)
            i += 1
            continue

        if ch == ";":
            result.append(ch)
            i += 1
            continue

        if ch == "{":
            if result and result[-1] == " ":
                result.pop()
            result.append(ch)
            i += 1
            continue

        if ch == "}":
            result.append(ch)
            i += 1
            continue

        result.append(ch)
        i += 1

    output = "".join(result)
    output = re_sub_semicolons(output)
    return output.rstrip()


def re_sub_semicolons(css: str) -> str:
    """Remove redundant semicolons before closing braces and trailing ones."""
    import re
    css = re.sub(r";\s*\}", "}", css)
    return css


def read_input(path_arg):
    """Read CSS from file (utf-8, latin-1 fallback) or stdin. Returns (content, source)."""
    if path_arg in (None, "-"):
        return sys.stdin.read(), "<stdin>"
    p = Path(path_arg)
    if not p.is_file():
        raise FileNotFoundError(p)
    try:
        return p.read_text(encoding="utf-8"), str(p)
    except UnicodeDecodeError:
        return p.read_text(encoding="latin-1"), str(p)


def parse_args():
    ap = argparse.ArgumentParser(
        prog="css-minifier",
        description="Industrial-grade CSS minifier (comments/whitespace/redundant semicolons).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Exit codes:\n"
            "  0  success\n"
            "  1  input error (file missing / unreadable)\n"
        ),
    )
    ap.add_argument("input", nargs="?", help="Input CSS file; '-' or omit for stdin")
    ap.add_argument("--json", action="store_true", help="machine-readable JSON output")
    ap.add_argument("--dry-run", action="store_true",
                    help="validate input path only, do not minify")
    ap.add_argument("--version", action="version",
                    version=f"css-minifier v{VERSION} (part of {TOOLCHAIN})")
    return ap.parse_args()


def main():
    args = parse_args()
    src_name = args.input if args.input not in (None, "-") else "<stdin>"

    # dry-run: validate only the input path, never read content
    if args.dry_run:
        if args.input not in (None, "-"):
            p = Path(args.input)
            if not p.is_file():
                print(json.dumps({"status": "error", "file": src_name,
                                  "reason": "file not found"}) if args.json
                      else f"{src_name}: dry-run FAILED (file not found)", file=sys.stderr)
                return 1
            print(json.dumps({"status": "ok", "file": src_name, "dry_run": True}) if args.json
                  else f"{src_name}: dry-run OK (path valid)")
        else:
            print(json.dumps({"status": "ok", "file": "<stdin>", "dry_run": True}) if args.json
                  else "<stdin>: dry-run OK")
        return 0

    # real run
    try:
        css, src = read_input(args.input)
    except FileNotFoundError as e:
        print(json.dumps({"status": "error", "file": src_name,
                          "reason": "file not found"}) if args.json
              else f"Error: file not found: {src_name}", file=sys.stderr)
        return 1
    except Exception as e:
        print(json.dumps({"status": "error", "file": src_name, "reason": str(e)}) if args.json
              else f"Error reading {src_name}: {e}", file=sys.stderr)
        return 1

    out = minify_css(css)
    orig_size = len(css)
    min_size = len(out)

    if args.json:
        payload = {
            "tool": "css-minifier",
            "version": VERSION,
            "file": src,
            "minified": out,
            "original_size": orig_size,
            "minified_size": min_size,
            "savings_pct": round(100 * (1 - min_size / orig_size), 1) if orig_size else 0.0,
        }
        print(json.dumps(payload, ensure_ascii=False))
    else:
        print(out)
        if not args.input:
            pass  # stdin pipeline: emit only minified css to stdout
        else:
            print(f"# {src}: {orig_size} -> {min_size} bytes "
                  f"({100 * (1 - min_size / orig_size):.1f}% saved)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
