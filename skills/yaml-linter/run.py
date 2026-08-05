#!/usr/bin/env python3
"""yaml-linter — Industrial-grade YAML diagnostic linter.

Diagnosis expert for YAML files: precise line/column errors via PyYAML
MarkedYAMLError, TAB detection, exit-code semantics, and machine-readable JSON.

Usage:
  python run.py file.yaml
  python run.py file.yaml --json
  python run.py --dry-run file.yaml      # validate env + path only
  echo "a: 1" | python run.py -

Exit codes:
  0  file is valid (no errors, possibly warnings)
  1  hard syntax/compatibility error (fatal)
  2  warnings only (valid YAML but recommended style fixes)
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path

VERSION = "1.0.1"
TOOLCHAIN = "Agnes Toolchain"

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False


# ── Diagnostic record helpers ──────────────────────────────

class Diag:
    __slots__ = ("status", "line", "column", "reason", "rule")

    def __init__(self, status, line, column, reason, rule=""):
        self.status = status      # "error" | "warning"
        self.line = line          # 1-based, 0 = unknown
        self.column = column      # 1-based, 0 = unknown
        self.reason = reason
        self.rule = rule

    def to_dict(self):
        return {
            "status": self.status,
            "line": self.line,
            "column": self.column,
            "reason": self.reason,
            "rule": self.rule,
        }


# ── Heuristic (no PyYAML) checkers ─────────────────────────

def _check_tab(line, lineno, out):
    if "\t" in line[: len(line) - len(line.lstrip("\t"))]:
        out.append(Diag("error", lineno, 1,
                        "found tab character used for indentation", "tab-indent"))


def _check_indent(line, lineno, out):
    stripped = line.rstrip()
    if not stripped or stripped.lstrip().startswith("#"):
        return
    indent = len(stripped) - len(stripped.lstrip())
    if indent > 0 and indent % 2 != 0:
        out.append(Diag("warning", lineno, indent + 1,
                        f"inconsistent indentation (column {indent}, expected multiple of 2)",
                        "indent-even"))


def _check_colon(line, lineno, out):
    stripped = line.rstrip()
    if re.search(r":\S", stripped) and "://" not in stripped:
        if re.match(r"^[^#\s]+:", stripped):
            col = stripped.find(":") + 1
            out.append(Diag("warning", lineno, col,
                            "missing space after colon", "colon-space"))


def _check_quotes(line, lineno, out):
    stripped = line.rstrip()
    for q, name in (("'", "single"), ('"', "double")):
        # strip escaped quotes
        cnt = stripped.count(q)
        cnt -= stripped.count("\\" + q)
        if cnt % 2 != 0:
            col = max(stripped.rfind(q), 0) + 1
            out.append(Diag("warning", lineno, col,
                            f"mismatched {name} quotes", "quote-balance"))


def heuristic_validate(content, out):
    for i, line in enumerate(content.split("\n"), start=1):
        _check_tab(line, i, out)
        _check_indent(line, i, out)
        _check_colon(line, i, out)
        _check_quotes(line, i, out)


# ── PyYAML validation (precise line/column) ────────────────

def pyyaml_validate(content, out):
    if not HAS_YAML:
        # fallback: heuristic only, mark as degraded
        heuristic_validate(content, out)
        return
    try:
        yaml.safe_load(content)
    except yaml.YAMLError as e:
        mark = getattr(e, "problem_mark", None)
        line = (mark.line + 1) if mark else 0
        col = (mark.column + 1) if mark else 0
        problem = getattr(e, "problem", None) or str(e)
        out.append(Diag("error", line, col, problem, "yaml-syntax"))
        # ParseError also carries context line — surface it
        if isinstance(e, yaml.parser.ParserError):
            context = getattr(e, "context", None)
            if context:
                out.append(Diag("error", line, col, context, "yaml-context"))
    # heuristic warnings on valid bases (duplicates / style)
    heuristic_validate(content, out)


# ── Input handling ─────────────────────────────────────────

def lint_text(content, source, out):
    if not content.strip():
        return
    pyyaml_validate(content, out)


def lint_file(path, out, dry_run=False):
    p = Path(path)
    if not p.exists():
        out.append(Diag("error", 0, 0, f"file not found: {path}", "file-missing"))
        return False
    if not p.is_file():
        out.append(Diag("error", 0, 0, f"not a regular file: {path}", "file-type"))
        return False
    if dry_run:
        return True  # dry-run: path verified, do not read large content
    try:
        content = p.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        try:
            content = p.read_text(encoding="latin-1")
        except Exception as e:
            out.append(Diag("error", 0, 0, f"encoding error: {e}", "encoding"))
            return False
    except Exception as e:
        out.append(Diag("error", 0, 0, f"read error: {e}", "read"))
        return False
    lint_text(content, str(p), out)
    return True


# ── CLI ────────────────────────────────────────────────────

def parse_args():
    ap = argparse.ArgumentParser(
        prog="yaml-linter",
        description="Industrial-grade YAML diagnostic linter (PyYAML precise line/column + TAB detection).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Exit codes:\n"
            "  0  valid/no errors (may have warnings)\n"
            "  1  hard syntax error\n"
            "  2  warnings only\n"
        ),
    )
    ap.add_argument("files", nargs="*", help="YAML files to lint; '-' = stdin")
    ap.add_argument("--version", action="version",
                    version=f"yaml-linter v{VERSION} (part of {TOOLCHAIN})")
    ap.add_argument("--json", action="store_true", dest="json_output",
                    help="machine-readable JSON output")
    ap.add_argument("--dry-run", action="store_true",
                    help="validate environment + input paths only (no content read)")
    return ap.parse_args()


def main():
    args = parse_args()
    files = args.files if args.files else ["-"]
    results = []
    overall = {"error": 0, "warning": 0}

    for f in files:
        out = []
        if f == "-":
            content = sys.stdin.read()
            lint_text(content, "<stdin>", out)
            src = "<stdin>"
        else:
            ok = lint_file(f, out, args.dry_run)
            src = f
        per = {"error": 0, "warning": 0}
        for d in out:
            per[d.status] += 1
        overall["error"] += per["error"]
        overall["warning"] += per["warning"]
        results.append({
            "file": src,
            **per,
            "diagnostics": [d.to_dict() for d in out],
        })

    payload = {
        "tool": "yaml-linter",
        "version": VERSION,
        "dry_run": args.dry_run,
        "summary": overall,
        "files": results,
    }

    if args.json_output:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        for r in results:
            if r["diagnostics"]:
                print(f"{r['file']}:")
                for d in r["diagnostics"]:
                    loc = f"[Line {d['line']}, Col {d['column']}] " if d["line"] else ""
                    print(f"  {loc}{d['status'].upper()}: {d['reason']}")
            elif args.dry_run:
                print(f"{r['file']}: dry-run OK (path valid)")
            else:
                print(f"{r['file']}: OK")
        print(f"summary: {overall['error']} error(s), {overall['warning']} warning(s)")

    # Exit-code semantics: 0 clean-ish / 1 errors / 2 warnings only
    if overall["error"] > 0:
        return 1
    if overall["warning"] > 0:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
