#!/usr/bin/env python3
"""link-checker — Industrial-grade link validator.

Extracts URLs from Markdown / HTML / plain text and checks each one over HTTP,
with honest status classification, retry with backoff, and machine-readable
JSON output.

Usage:
  python run.py input.md
  python run.py input.md --json
  python run.py input.md --dry-run      # extract only, no network
  echo "https://example.com" | python run.py -
  python run.py --version
"""

import argparse
import json
import re
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path

VERSION = "1.0.0"
TOOLCHAIN = "Agnes Toolchain"

# URL extraction: scheme://host/path... avoiding trailing punctuation.
URL_RE = re.compile(
    r"https?://[^\s<>()\"'\[\]]+",
    re.IGNORECASE,
)
# Trailing punctuation that is not part of a URL (markdown/plain text noise).
TRAILING_TRIM = re.compile(r"[),.;:!?]+$")

TIMEOUT = 8.0
MAX_RETRIES = 2
BACKOFF = 0.8
UA = "link-checker/1.0 (+Agnes Toolchain)"


def extract_urls(text: str) -> list:
    """Extract and normalize URLs; preserve document order, de-dupe."""
    seen = set()
    urls = []
    for raw in URL_RE.findall(text):
        url = TRAILING_TRIM.sub("", raw)
        if url in seen:
            continue
        seen.add(url)
        urls.append(url)
    return urls


def check_url(url: str) -> dict:
    """Check a single URL. Returns status classification record."""
    last_status = 0
    last_err = None
    for attempt in range(MAX_RETRIES + 1):
        req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": UA})
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                return {
                    "url": url,
                    "status": resp.status,
                    "ok": resp.status < 400,
                    "class": _classify(resp.status),
                    "attempts": attempt + 1,
                    "error": None,
                }
        except urllib.error.HTTPError as e:
            # HEAD may be unsupported; retry once with GET on 405/501.
            if e.code in (405, 501) and attempt == 0:
                last_status = e.code
                req = urllib.request.Request(url, method="GET", headers={"User-Agent": UA})
                try:
                    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                        return {
                            "url": url,
                            "status": resp.status,
                            "ok": resp.status < 400,
                            "class": _classify(resp.status),
                            "attempts": attempt + 2,
                            "error": None,
                        }
                except urllib.error.HTTPError as e2:
                    last_status = e2.code
                    last_err = f"HTTP {e2.code}"
                except Exception as e2:
                    last_err = str(e2)
                break
            last_status = e.code
            last_err = f"HTTP {e.code}"
        except urllib.error.URLError as e:
            last_err = e.reason if isinstance(e.reason, str) else str(e.reason)
        except Exception as e:  # socket timeouts etc.
            last_err = str(e)
        if attempt < MAX_RETRIES:
            time.sleep(BACKOFF * (attempt + 1))
    return {
        "url": url,
        "status": last_status if last_status else None,
        "ok": False,
        "class": "error",
        "attempts": MAX_RETRIES + 1,
        "error": last_err,
    }


def _classify(status: int) -> str:
    if 200 <= status < 300:
        return "ok"
    if 300 <= status < 400:
        return "redirect"
    if 400 <= status < 500:
        return "client_error"
    if 500 <= status < 600:
        return "server_error"
    return "unknown"


def run_checks(urls: list, dry_run: bool = False) -> dict:
    results = []
    for url in urls:
        if dry_run:
            results.append({"url": url, "status": None, "ok": True,
                            "class": "extracted", "attempts": 0, "error": None})
        else:
            results.append(check_url(url))
    ok_count = sum(1 for r in results if r["ok"])
    return {
        "tool": "link-checker",
        "version": VERSION,
        "dry_run": dry_run,
        "total": len(results),
        "ok": ok_count,
        "broken": len(results) - ok_count,
        "results": results,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="link-checker", description=__doc__)
    parser.add_argument("path", nargs="?", default="-",
                        help="input file (or - for stdin)")
    parser.add_argument("--json", action="store_true",
                        help="machine-readable JSON output")
    parser.add_argument("--dry-run", action="store_true",
                        help="extract URLs only; no network calls")
    parser.add_argument("--version", action="version",
                        version=f"%(prog)s {VERSION} ({TOOLCHAIN})")
    args = parser.parse_args(argv)

    if args.path == "-":
        text = sys.stdin.read()
        source = "<stdin>"
    else:
        p = Path(args.path)
        if not p.exists():
            print(f"link-checker: error: no such file: {p}", file=sys.stderr)
            return 2
        text = p.read_text(encoding="utf-8", errors="replace")
        source = str(p)

    urls = extract_urls(text)
    report = run_checks(urls, dry_run=args.dry_run)
    report["source"] = source

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"link-checker {VERSION}: {report['total']} URLs "
              f"({report['ok']} ok / {report['broken']} broken) "
              f"[{'dry-run' if args.dry_run else 'live'}]")
        for r in report["results"]:
            mark = "OK " if r["ok"] else "!! "
            detail = r["error"] if r["error"] else r["class"]
            print(f"  {mark} {r['url']}  ({detail})")

    # Exit semantics: 0 = all ok (or dry-run), 1 = at least one broken link.
    return 1 if (not args.dry_run and report["broken"] > 0) else 0


if __name__ == "__main__":
    sys.exit(main())
