---
name: log-injection
enabled: true
event: file_write
action: warn
category: security
severity: medium
conditions:
  - field: new_text
    operator: regex_match
    pattern: (?:logging\.(?:info|warn|error|debug)\(|logger\.(?:info|warn|error|debug)|console\.log\(|print\()
  - field: new_text
    operator: not_contains
    pattern: (?:sanitize|escape|clean|replace\()\w+|
  - field: new_text
    operator: regex_match
    pattern: (?:\+|\bf\w+|%\w+|\.format\(|f['\"]).*\b(request|user_input|params|body|query|args|data)\b
---
⚠️ 日志注入风险：日志中直接输出用户输入。

日志注入可伪造日志条目或触发 SIEM 告警绕过。
- 去除换行符: `log_line.replace("\\n", "").replace("\\r", "")`
- 结构化日志（JSON）避免格式字符串注入
- Python: 用 `%s` 占位符而非 `f-string` 拼接用户输入
- 对敏感字段做脱敏: `mask_email(user_input)`
