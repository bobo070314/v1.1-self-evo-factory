---
name: missing-rate-limit
enabled: true
event: file_write
action: warn
category: ops
severity: medium
conditions:
  - field: new_text
    operator: regex_match
    pattern: (?:@app\.route|router\.(?:get|post|put|delete)|def\s+\w+\(.*request|app\.(?:get|post))
  - field: new_text
    operator: not_contains
    pattern: (?:rate_limit|ratelimit|throttle|limiter|throttling)
---
⚠️ 缺少速率限制：API 端点可能被滥用。

未做限流的端点可能被 DDoS 或暴力破解。
- Flask: `flask-limiter` 扩展
- Express: `express-rate-limit` 中间件
- 全局: Nginx/Cloudflare 配置限流
- 登录/注册端点建议严格限流
