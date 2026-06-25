---
name: cors-misconfig
enabled: true
event: file_write
action: warn
category: security
severity: high
conditions:
  - field: new_text
    operator: regex_match
    pattern: Access-Control-Allow-Origin\s*:\s*\*
---
⚠️ CORS 配置过于宽松：`Access-Control-Allow-Origin: *`。

允许任意来源跨域访问可能导致数据泄露。
- 指定具体的允许域名: `https://yourdomain.com`
- 动态 CORS: 根据 Origin header 白名单匹配
- 带认证的请求不能使用 `*`
- 不要同时设置 `Access-Control-Allow-Credentials: true` 和 `Origin: *`
