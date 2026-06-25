---
name: unvalidated-redirect
enabled: true
event: file_write
action: warn
category: security
severity: high
conditions:
  - field: new_text
    operator: regex_match
    pattern: (?:window\.location\s*=|location\.href\s*=|location\.assign\()
---
⚠️ 未验证的客户端重定向：检测到 window.location 赋值。

直接使用用户输入赋值到 location 存在 XSS/钓鱼风险。
- 在白名单上下文中使用
- 考虑使用路由跳转而非直接 URL 赋值
- 如果必须使用，对 URL 做 URL.parse 验证
