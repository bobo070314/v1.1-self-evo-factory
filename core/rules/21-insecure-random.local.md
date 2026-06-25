---
name: insecure-random
enabled: true
event: file_write
action: warn
category: security
severity: medium
conditions:
  - field: new_text
    operator: regex_match
    pattern: (?:random\.(?:rand|choice|shuffle|sample)|Math\.random|rand\(\)|randn\(\))(?!.*\b(?:secure|crypto)\b)
---
⚠️ 不安全的随机数：用于密码学场景时应使用安全随机数。

非安全随机函数（random/Math.random/rand）可被预测。
- Python: `secrets.token_hex(32)` 替代 `random.choice`
- JS: `crypto.randomBytes()` 替代 `Math.random()`
- C/Go: 使用 `crypto/rand` 而非 `math/rand`
- 仅用于非密码学场景（如游戏、测试）时可豁免
