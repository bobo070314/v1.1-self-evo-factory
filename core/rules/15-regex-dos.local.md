---
name: regex-dos
enabled: true
event: file_write
action: warn
category: security
severity: medium
conditions:
  - field: new_text
    operator: regex_match
    pattern: (?:\(\.\*\)\+|\(\.\+\).*\{|\(\.\*\)\{|\(\.\+\).*\+|\(\.\*\)\?)
---
⚠️ ReDoS 风险：检测到可能 ReDoS 的正则表达式。

嵌套量词如 `(.*)+` 可导致指数级回溯。
- 避免在用户输入的 regex 中使用嵌套量词
- 使用 `re.DEFAULT_FLAGS` 超时机制
- Python: `regex` 库有超时参数
- Node.js: 用 `safe-regex` 检测
