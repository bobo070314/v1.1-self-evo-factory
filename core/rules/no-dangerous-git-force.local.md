---
name: no-dangerous-git-force
enabled: true
event: bash
action: block
category: ops
severity: critical
conditions:
  - field: command
    operator: regex_match
    pattern: ^git\s+push\s+.*\s+-f
---
⚠️ BLOCKED: `git push --force` 会被坏历史。

强制推送会覆盖远程分支历史，如果是团队仓库会导致他人工作丢失。

安全替代方案：
- `git push --force-with-lease`（安全强推，会检查远程是否有新提交）
- 先 `git push --dry-run` 确认影响范围
- 对 main/master 分支永远不要 force push
