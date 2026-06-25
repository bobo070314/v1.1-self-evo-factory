---
name: xss-reflected
enabled: true
event: file_write
action: warn
category: security
severity: critical
conditions:
  - field: new_text
    operator: regex_match
    pattern: (?:innerHTML\s*=|outerHTML\s*=|dangerouslySetInnerHTML|v-html|\.html\()(?:(?!\bDOMPurify\b|\bescape\b).)*
---
⚠️ XSS 风险：检测到直接将用户输入插入 HTML。

未转义的用户输入插入 HTML/React 模板会导致 XSS 攻击。
- React: 默认用 `{userInput}`（自动转义），不要用 `dangerouslySetInnerHTML`
- Vue: 用 `{{ userInput }}` 而非 `v-html`
- DOM: 用 `textContent` 而非 `innerHTML`
- 必要 HTML: 使用 DOMPurify 过滤
