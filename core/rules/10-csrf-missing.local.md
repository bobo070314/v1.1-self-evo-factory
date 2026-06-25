---
name: csrf-missing
enabled: true
event: file_write
action: warn
category: security
severity: high
conditions:
  - field: new_text
    operator: regex_match
    pattern: <form.*?</form>
  - field: new_text
    operator: not_contains
    pattern: csrf_token
---
⚠️ CSRF 保护缺失：检测到 form 标签但无 CSRF token。

POST 请求需要 CSRF 保护防止跨站请求伪造。
- Django: `{% csrf_token %}` 在 form 中
- Flask: `{{ form.hidden_tag() }}` 或手动加 token
- Express: 使用 `csurf` 中间件
- Next.js API Routes: 检查 header/cookie token
