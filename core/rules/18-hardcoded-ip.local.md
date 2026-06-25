---
name: hardcoded-ip
enabled: true
event: file_write
action: warn
category: security
severity: medium
conditions:
  - field: new_text
    operator: regex_match
    pattern: \b(?:\d{1,3}\.){3}\d{1,3}\b
  - field: file_path
    operator: not_contains
    pattern: \.env|config.*\.(?:json|yaml|yml|toml|ini)
---
⚠️ 硬编码 IP 地址：代码中检测到 IP 地址。

硬编码 IP 地址降低代码可移植性，可能导致连接失败。
- 使用配置变量: `DB_HOST = os.environ.get("DB_HOST", "localhost")`
- 配置文件: `.env` 或 `config.yaml` 集中管理
- 容器环境: 通过环境变量注入 IP
