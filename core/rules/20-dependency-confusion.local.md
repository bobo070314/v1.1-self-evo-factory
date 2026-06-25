---
name: dependency-confusion
enabled: true
event: file_write
action: warn
category: ops
severity: high
conditions:
  - field: new_text
    operator: regex_match
    pattern: npm\s+(?:install|i)\s+(?!@)(?:[^/]*$)
---
⚠️ Dependency Confusion 风险：安装来自 npm 的非 scoped 包。

公有 registry 上可能存在同名恶意包。
- 内部包使用 scope: `@yourcompany/package-name`
- 配置 npm registry 白名单
- 使用 lockfile 固定版本
- pip: 配置 `--index-url` 指向私有仓库
