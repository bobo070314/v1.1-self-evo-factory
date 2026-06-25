---
name: prototype-pollution
enabled: true
event: file_write
action: warn
category: security
severity: high
conditions:
  - field: new_text
    operator: regex_match
    pattern: \[['\"]__proto__['\"]\]|constructor\.prototype|Object\.assign\(.*\.__proto__|\[['\"]constructor['\"]\]\s*\[['\"]prototype['\"]
---
⚠️ Prototype Pollution 风险。

通过 `__proto__` 或 `constructor.prototype` 污染 JavaScript 原型链，可能导致 RCE 或属性篡改。
- 使用 `Object.create(null)` 创建纯净对象
- 冻结原型: `Object.freeze(Object.prototype)`
- 验证 JSON.parse 结果，去除 __proto__ 键
- 使用 Map 替代普通对象作为映射
