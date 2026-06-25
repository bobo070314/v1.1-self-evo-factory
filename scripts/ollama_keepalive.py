"""Ollama 保活脚本 — 每 4 分钟 ping /api/tags，防 5 分钟 keep_alive 过期"""
import time, sys, os

for k in ["HTTP_PROXY", "http_proxy", "HTTPS_PROXY", "https_proxy", "ALL_PROXY"]:
    os.environ.pop(k, None)

import requests
s = requests.Session()
s.trust_env = False

URL = "http://127.0.0.1:11634/api/tags"
INTERVAL = 240  # 4 分钟

print(f"🦞 Ollama keepalive daemon started (interval={INTERVAL}s)", file=sys.stderr, flush=True)
while True:
    try:
        r = s.get(URL, timeout=5)
        stamp = time.strftime("%H:%M:%S")
        if r.status_code == 200:
            print(f"[{stamp}] alive", flush=True)
        else:
            print(f"[{stamp}] WARN status={r.status_code}", file=sys.stderr, flush=True)
    except Exception as e:
        print(f"[{stamp}] ERROR {e}", file=sys.stderr, flush=True)
    time.sleep(INTERVAL)
