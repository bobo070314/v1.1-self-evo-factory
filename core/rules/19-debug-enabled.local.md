---
name: debug-enabled
enabled: true
event: file_write
action: warn
category: quality
severity: medium
conditions:
  - field: new_text
    operator: regex_match
    pattern: (?:debug\s*=\s*True|DEBUG\s*=\s*True|app\.run\(.*debug=True|FLASK_DEBUG=1|NODE_ENV\s*=\s*['\"]?development)
---
⚠️ Debug 模式开启：生产环境不应启用调试模式。

生产环境开启 Debug 模式会泄露敏感信息。
- 环境区分: `DEBUG = os.environ.get("DEBUG", "False").lower() == "true"`
- Flask: 用 `FLASK_ENV=production`
- Node: `NODE_ENV=production`
- Django: 关闭 `DEBUG = True`
