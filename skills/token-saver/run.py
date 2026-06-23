#!/usr/bin/env python3
"""token-saver — Command Output Compressor.
========================================
Compresses verbose command output to save tokens in AI context.
Pass-through exit codes. Typical compression: 82% (200 lines -> 36 lines).

Usage:
  python token-saver.py --command "npm test"
  python token-saver.py --command "git log --oneline -20" --max-lines 50
  python token-saver.py --file output.txt
"""

import argparse
import os
import re
import subprocess
import sys


def compress_output(text: str, max_lines: int = 100) -> str:
    """Compress verbose output while preserving key information."""
    lines = text.split("\n")
    original_count = len(lines)

    if original_count <= max_lines:
        return text, original_count, original_count

    compressed = []

    # Strategy 1: Keep first N lines (usually the important stuff)
    head_lines = min(10, max_lines // 4)
    compressed.extend(lines[:head_lines])
    if head_lines < original_count:
        compressed.append(f"... [skipped {original_count - head_lines - 10} lines] ...")

    # Strategy 2: Keep last 10 lines (summary/errors)
    tail_start = max(head_lines, original_count - (max_lines // 4))
    if tail_start > head_lines:
        compressed.extend(lines[tail_start:])

    # Strategy 3: Extract error lines
    error_lines = []
    error_patterns = [
        r"(?i)\berror\b",
        r"(?i)\bfail(ed|ure)?\b",
        r"(?i)\bexception\b",
        r"(?i)\btraceback\b",
        r"(?i)\bpanic\b",
        r"(?i)\bfatal\b",
        r"(?i)\bunresolved\b",
        r"(?i)\bconflict\b",
        r"(?i)\bdenied\b",
        r"(?i)\bnot found\b",
    ]
    for i, line in enumerate(lines):
        if i < head_lines or i >= tail_start:
            continue  # Already included
        for pat in error_patterns:
            if re.search(pat, line):
                error_lines.append(f"  [L{i + 1}] {line[:120]}")
                break  # One match per line

    if error_lines:
        compressed.append(f"\n--- Errors/Warnings ({len(error_lines)} found) ---")
        compressed.extend(error_lines[:20])  # Cap at 20 errors

    result = "\n".join(compressed)
    compressed_count = len(result.split("\n"))

    return result, original_count, compressed_count


def run_command(cmd: str, max_lines: int = 100) -> dict:
    """Run a shell command and compress its output."""
    result = subprocess.run(
        cmd,
        shell=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=300,
    )

    stdout_compressed, stdout_orig, stdout_new = compress_output(result.stdout, max_lines)
    stderr_compressed, stderr_orig, stderr_new = compress_output(result.stderr, max_lines)

    return {
        "exit_code": result.returncode,
        "stdout": stdout_compressed,
        "stderr": stderr_compressed,
        "stats": {
            "stdout_original_lines": stdout_orig,
            "stdout_compressed_lines": stdout_new,
            "stdout_compression_pct": round((1 - stdout_new / max(1, stdout_orig)) * 100, 1),
            "stderr_original_lines": stderr_orig,
            "stderr_compressed_lines": stderr_new,
        },
    }


def compress_file(filepath: str, max_lines: int = 100) -> dict:
    """Compress a file's contents."""
    path = os.path.abspath(filepath)
    if not os.path.exists(path):
        return {
            "exit_code": 1,
            "stdout": "",
            "stderr": f"File not found: {filepath}",
            "stats": {},
        }

    text = open(path, encoding="utf-8", errors="replace").read()
    compressed, orig, new = compress_output(text, max_lines)

    return {
        "exit_code": 0,
        "stdout": compressed,
        "stderr": "",
        "stats": {
            "file": filepath,
            "original_lines": orig,
            "compressed_lines": new,
            "compression_pct": round((1 - new / max(1, orig)) * 100, 1),
        },
    }


def main():
    parser = argparse.ArgumentParser(description="Token Saver — Compress command output")
    parser.add_argument("--command", "-c", help="Command to run and compress")
    parser.add_argument("--file", "-f", help="File to compress")
    parser.add_argument("--max-lines", "-m", type=int, default=100, help="Max output lines (default: 100)")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--stats-only", action="store_true", help="Only show compression stats")
    args = parser.parse_args()

    if args.command:
        result = run_command(args.command, args.max_lines)
    elif args.file:
        result = compress_file(args.file, args.max_lines)
    else:
        print("ERROR: Use --command or --file", file=sys.stderr)
        sys.exit(1)

    if args.json:
        import json

        print(json.dumps(result, indent=2, ensure_ascii=False))
    elif args.stats_only:
        stats = result.get("stats", {})
        print(
            f"Compression: {stats.get('compression_pct', 'N/A')}% "
            f"({stats.get('original_lines', '?')} -> {stats.get('compressed_lines', '?')} lines)"
        )
    else:
        if result.get("stderr"):
            print(result["stderr"], file=sys.stderr)
        print(result["stdout"])
        stats = result.get("stats", {})
        if stats:
            print(f"\n--- compression: {stats.get('compression_pct', '?')}% ---", file=sys.stderr)

    sys.exit(result["exit_code"])


if __name__ == "__main__":
    main()
