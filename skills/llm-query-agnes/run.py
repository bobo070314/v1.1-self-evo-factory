#!/usr/bin/env python3
"""llm-query-agnes — Free LLM query via agnes-2.5-flash (OpenAI-compatible).

Zero-cost LLM access for skill pipelines and SelfEvolver fixes. Standard library only.

Usage:
  python run.py --prompt "修复这段代码" --json
  python run.py --prompt "..." --max-tokens 2048 --temperature 0.1
  python run.py --version
"""

import argparse
import json
import os
import sys
import urllib.request
import urllib.error

API_URL = "https://apihub.agnes-ai.com/v1/chat/completions"
DEFAULT_MODEL = "agnes-2.5-flash"
VERSION = "0.2.0"


def call_llm(prompt: str, model: str = DEFAULT_MODEL, max_tokens: int = 1024,
             temperature: float = 0.2, api_key: str = None) -> str:
    """Call agnes chat completions. Returns reply text. Raises on error."""
    key = api_key or os.environ.get("AGNES_API_KEY", "")
    if not key:
        raise RuntimeError("AGNES_API_KEY 未设置")

    body = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    req = urllib.request.Request(
        API_URL,
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": "Bearer " + key,
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return data["choices"][0]["message"]["content"]


def main() -> int:
    ap = argparse.ArgumentParser(description="Free LLM query via agnes-2.5-flash")
    ap.add_argument("--prompt", help="User prompt text")
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--max-tokens", type=int, default=1024)
    ap.add_argument("--temperature", type=float, default=0.2)
    ap.add_argument("--json", action="store_true", help="Output machine-readable JSON")
    ap.add_argument("--dry-run", action="store_true", help="Print request info without calling API")
    ap.add_argument("--version", action="version", version=f"llm-query-agnes {VERSION}")
    args = ap.parse_args()

    if not args.prompt:
        ap.error("--prompt 是必填参数")

    if args.dry_run:
        info = {
            "url": API_URL,
            "model": args.model,
            "max_tokens": args.max_tokens,
            "temperature": args.temperature,
            "key_present": bool(os.environ.get("AGNES_API_KEY", "")),
        }
        print(json.dumps(info, ensure_ascii=False, indent=2) if args.json else
              f"[dry-run] {info['url']} model={info['model']} key={'yes' if info['key_present'] else 'NO'}")
        return 0

    try:
        out = call_llm(args.prompt, args.model, args.max_tokens, args.temperature)
    except urllib.error.HTTPError as e:
        print(f"HTTP_ERROR {e.code}: {e.read().decode('utf-8', 'replace')[:400]}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {e}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps({"text": out}, ensure_ascii=False, indent=2))
    else:
        print(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
