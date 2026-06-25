---
name: sensitive-data-leak
enabled: true
event: file_write
action: warn
category: security
severity: high
conditions:
  - field: new_text
    operator: regex_match
    pattern: (?:password|passwd|pwd|secret|credential|api[_-]?key|access[_-]?key)\s*[:=]\s*['\"]
---
⚠️ 敏感数据泄露风险：检测到明文密码/凭证。

在代码中硬编码密码/密钥会导致泄露风险。
- 使用环境变量: `os.environ["DB_PASSWORD"]`
- 使用 `.env` 文件（已加入 .gitignore）
- 日志中避免输出敏感字段
- 提交前检查：`git diff --cached | grep -i password`
