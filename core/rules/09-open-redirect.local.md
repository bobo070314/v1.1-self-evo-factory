---
name: open-redirect
enabled: true
event: file_write
action: warn
category: security
severity: high
conditions:
  - field: new_text
    operator: regex_match
    pattern: (?:redirect\(|redirect_to|res\.redirect|next=|returnUrl|redirect_url)
---
⚠️ 开放重定向风险：检测到重定向参数来自用户输入。

未验证的重定向参数可被用于钓鱼攻击。
- 白名单允许的重定向目标
- 使用固定路由映射: `ALLOWED_REDIRECTS = {"/dashboard", "/profile"}`
- 避免 `redirect(request.GET.get("next"))`
