#!/usr/bin/env python3
"""security-audit — Static code security auditor.
Checks for SQL injection, XSS, hardcoded secrets, command injection,
path traversal, and other common security vulnerabilities.

Usage:
  python run.py --dir ./src
  python run.py --file ./src/app.py --json
  python run.py --dir ./ --severity error
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

# ─── Vulnerability Patterns ────────────────────────────────────

SECURITY_PATTERNS = [
    # SQL Injection
    {
        "id": "SEC-SQL-001",
        "pattern": r'(?:execute|cursor\.execute|raw)\s*\(\s*(?:f["\']|["\'][^"\']+["\']\s*%\s*|["\'][^"\']*\{\s*\w+\s*\})',
        "severity": "error",
        "message": "Potential SQL injection — use parameterized queries",
        "fix": "Use parameterized queries: cursor.execute(query, (param,))",
        "languages": [".py"],
    },
    {
        "id": "SEC-SQL-002",
        "pattern": r'\.query\s*\(\s*[`"\']\s*(?:SELECT|INSERT|UPDATE|DELETE)',
        "severity": "error",
        "message": "Raw SQL query with user input — potential SQL injection",
        "fix": "Use ORM or parameterized queries",
        "languages": [".js", ".ts", ".tsx"],
    },
    # XSS
    {
        "id": "SEC-XSS-001",
        "pattern": r"\.innerHTML\s*=\s*[^=]",
        "severity": "error",
        "message": "Unsafe innerHTML assignment — potential XSS vulnerability",
        "fix": "Use textContent or sanitize with DOMPurify",
        "languages": [".js", ".ts", ".tsx", ".jsx", ".html"],
    },
    {
        "id": "SEC-XSS-002",
        "pattern": r"document\.write\s*\(",
        "severity": "error",
        "message": "document.write() — potential XSS and CSP bypass",
        "fix": "Use DOM manipulation methods instead",
        "languages": [".js", ".ts", ".tsx", ".jsx"],
    },
    # Hardcoded Secrets
    {
        "id": "SEC-SECRET-001",
        "pattern": r'(?i)(?:api[_-]?key|secret|password|token)\s*[:=]\s*["\'][A-Za-z0-9_\-]{8,}["\']',
        "severity": "error",
        "message": "Hardcoded secret detected — never commit credentials",
        "fix": "Use environment variables: os.environ.get('SECRET')",
        "languages": [".py", ".js", ".ts", ".tsx", ".jsx", ".go", ".rs"],
    },
    {
        "id": "SEC-SECRET-002",
        "pattern": r'(?i)(?:DEEPSEEK_API_KEY|OPENAI_API_KEY|GITHUB_TOKEN|AWS_ACCESS_KEY|STRIPE_KEY)\s*=\s*["\'][^"\']+["\']',
        "severity": "error",
        "message": "Known API key pattern hardcoded — use environment variables",
        "fix": "Use environment variables or a secrets manager",
        "languages": [".py", ".js", ".ts", ".tsx", ".jsx", ".go", ".rs"],
    },
    # Command Injection
    {
        "id": "SEC-CMD-001",
        "pattern": r"os\.system\s*\(",
        "severity": "error",
        "message": "os.system() can lead to command injection — use subprocess.run()",
        "fix": "Use subprocess.run(cmd, shell=False) with list arguments",
        "languages": [".py"],
    },
    {
        "id": "SEC-CMD-002",
        "pattern": r"(?:exec|eval)\s*\(\s*[^)]*\+[^)]*\)",
        "severity": "error",
        "message": "Dynamic code execution with string concatenation — command injection risk",
        "fix": "Avoid exec/eval, or sanitize input strictly",
        "languages": [".py", ".js", ".ts", ".tsx", ".jsx"],
    },
    # Path Traversal
    {
        "id": "SEC-PATH-001",
        "pattern": r"open\s*\(\s*[^)]*\.\.[^)]*\)",
        "severity": "error",
        "message": "File path with '..' — potential path traversal vulnerability",
        "fix": "Sanitize paths with os.path.realpath() and restrict to safe directories",
        "languages": [".py"],
    },
    {
        "id": "SEC-PATH-002",
        "pattern": r"path\.join\s*\(\s*[^)]*request",
        "severity": "warning",
        "message": "Path constructed from request data — potential path traversal",
        "fix": "Validate and sanitize user-supplied path components",
        "languages": [".py", ".js", ".ts"],
    },
    # Insecure Deserialization
    {
        "id": "SEC-DESER-001",
        "pattern": r"pickle\.loads?\s*\(",
        "severity": "error",
        "message": "Unsafe pickle deserialization — remote code execution risk",
        "fix": "Use JSON or another safe serialization format",
        "languages": [".py"],
    },
    # Weak Cryptography
    {
        "id": "SEC-CRYPTO-001",
        "pattern": r"(?i)md5\s*\(",
        "severity": "warning",
        "message": "MD5 is cryptographically broken — use SHA-256 or better",
        "fix": "Use hashlib.sha256() instead",
        "languages": [".py", ".js", ".ts", ".go"],
    },
    {
        "id": "SEC-CRYPTO-002",
        "pattern": r"(?i)sha1\s*\(",
        "severity": "warning",
        "message": "SHA-1 is cryptographically weak — use SHA-256 or better",
        "fix": "Use hashlib.sha256() instead",
        "languages": [".py", ".js", ".ts", ".go"],
    },
]

EXCLUDED_DIRS = {"node_modules", "__pycache__", ".git", "dist", "build", ".next", "vendor", "target"}
SUPPORTED_EXTENSIONS = {".py", ".js", ".ts", ".tsx", ".jsx", ".go", ".rs", ".html", ".php", ".java"}


def scan_file(filepath: str) -> dict:
    """Scan a single file for security vulnerabilities."""
    result = {
        "file": filepath,
        "vulnerabilities": [],
        "lines_scanned": 0,
    }

    path = Path(filepath)
    if path.suffix not in SUPPORTED_EXTENSIONS:
        return result

    try:
        content = path.read_text(encoding="utf-8", errors="replace")
        lines = content.split("\n")
        result["lines_scanned"] = len(lines)
    except Exception:
        return result

    for i, line in enumerate(lines, 1):
        for rule in SECURITY_PATTERNS:
            if path.suffix not in rule["languages"]:
                continue
            # Skip commented lines
            stripped = line.strip()
            if stripped.startswith("#") or stripped.startswith("//") or stripped.startswith("/*"):
                continue
            if re.search(rule["pattern"], line):
                # Avoid duplicate findings on same line
                existing = [v for v in result["vulnerabilities"] if v["line"] == i and v["rule_id"] == rule["id"]]
                if existing:
                    continue
                result["vulnerabilities"].append(
                    {
                        "line": i,
                        "rule_id": rule["id"],
                        "severity": rule["severity"],
                        "message": rule["message"],
                        "fix": rule["fix"],
                        "code": stripped[:120],
                    }
                )

    return result


def scan_directory(directory: str, min_severity: str = "warning") -> dict:
    """Scan all files in a directory for security vulnerabilities."""
    all_file_results = []
    root = Path(directory)

    for filepath in root.rglob("*"):
        if not filepath.is_file():
            continue
        if filepath.suffix not in SUPPORTED_EXTENSIONS:
            continue
        # Skip excluded dirs
        parts = set(filepath.parts)
        if parts & EXCLUDED_DIRS:
            continue

        file_result = scan_file(str(filepath))
        if file_result["vulnerabilities"]:
            all_file_results.append(file_result)

    # Aggregate stats
    total_vulns = sum(len(fr["vulnerabilities"]) for fr in all_file_results)
    by_severity = {"error": 0, "warning": 0, "info": 0}
    by_rule = {}
    for fr in all_file_results:
        for vuln in fr["vulnerabilities"]:
            by_severity[vuln["severity"]] = by_severity.get(vuln["severity"], 0) + 1
            by_rule[vuln["rule_id"]] = by_rule.get(vuln["rule_id"], 0) + 1

    return {
        "directory": directory,
        "files_scanned": len(all_file_results),
        "total_vulnerabilities": total_vulns,
        "by_severity": by_severity,
        "by_rule": by_rule,
        "files": all_file_results,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def main():
    parser = argparse.ArgumentParser(
        description="security-audit — Static code security auditor",
    )
    parser.add_argument("--dir", default=os.getcwd(), help="Directory to scan (default: cwd)")
    parser.add_argument("--file", default=None, help="Scan a single file")
    parser.add_argument(
        "--severity",
        default="warning",
        choices=["info", "warning", "error"],
        help="Minimum severity to report (default: warning)",
    )
    parser.add_argument("--dry-run", action="store_true", default=True, help="Scan only, no changes (default)")
    parser.add_argument(
        "--no-dry-run", action="store_false", dest="dry_run", help="Scan and report (same as --dry-run for this skill)"
    )
    parser.add_argument("--json", action="store_true", help="Output as JSON")

    args = parser.parse_args()

    if args.file:
        result = scan_file(args.file)
        output = {
            "file": args.file,
            "vulnerabilities": result["vulnerabilities"],
            "lines_scanned": result["lines_scanned"],
        }
    else:
        output = scan_directory(args.dir, min_severity=args.severity)

    if args.json:
        print(json.dumps(output, indent=2, ensure_ascii=False))
    else:
        print("security-audit — Static Code Security Audit")
        if args.file:
            print(f"  File: {args.file}")
            print(f"  Lines scanned: {output['lines_scanned']}")
            vulns = output["vulnerabilities"]
            if vulns:
                print(f"  Vulnerabilities found: {len(vulns)}")
                for v in vulns:
                    emoji = "[CRIT]" if v["severity"] == "error" else "[WARN]"
                    print(f"  {emoji} [{v['rule_id']}] L{v['line']}: {v['message']}")
                    print(f"     Fix: {v['fix']}")
                    print(f"     Code: {v['code']}")
            else:
                print("  No vulnerabilities found!")
        else:
            print(f"  Directory: {output['directory']}")
            print(f"  Files with issues: {output['files_scanned']}")
            print(f"  Total vulnerabilities: {output['total_vulnerabilities']}")
            print(f"  By severity: {output['by_severity']}")
            print("  By rule:")
            for rule_id, count in sorted(output["by_rule"].items()):
                print(f"    {rule_id}: {count}")

            # Show top files
            if output["files"]:
                top_files = sorted(output["files"], key=lambda x: len(x["vulnerabilities"]), reverse=True)[:10]
                print("\n  Top files (first 10):")
                for fr in top_files:
                    err_count = sum(1 for v in fr["vulnerabilities"] if v["severity"] == "error")
                    warn_count = sum(1 for v in fr["vulnerabilities"] if v["severity"] == "warning")
                    print(
                        f"    {fr['file']}: {len(fr['vulnerabilities'])} issues "
                        f"(errors={err_count}, warnings={warn_count})"
                    )

    error_count = (
        output.get("by_severity", {}).get("error", 0)
        if not args.file
        else sum(1 for v in output.get("vulnerabilities", []) if v["severity"] == "error")
    )
    sys.exit(1 if error_count > 0 else 0)


if __name__ == "__main__":
    main()
