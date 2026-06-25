---
name: no-insecure-http
enabled: true
event: file_write
action: warn
category: security
severity: high
conditions:
  - field: new_text
    operator: regex_match
    pattern: http://(?!localhost|127\.0\.0\.1)
  - field: command
    operator: not_contains
    pattern: "# nosec"
---
⚠️ WARNING: HTTP 明文传输不安全。

对非 localhost 的请求请使用 HTTPS：
- `http://api.example.com` → `https://api.example.com`
- Python requests: `requests.get("https://...")`
- curl: `curl https://...`

仅在以下情况可豁免：
- localhost / 127.0.0.1（本地开发）
- 测试环境（加 `# nosec` 注释）
