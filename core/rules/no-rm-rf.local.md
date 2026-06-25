---
name: no-rm-rf
enabled: true
event: bash
action: block
category: security
severity: critical
conditions:
  - field: command
    operator: regex_match
    pattern: ^rm\s+-rf
---
⚠️ BLOCKED: `rm -rf` 会递归删除，且不可恢复。

使用安全的删除方式：
- 删除文件: `rm <路径>`
- 清空目录: `rm -rf <路径>/`（确认路径正确）
- 对根目录操作请先 `ls` 确认
