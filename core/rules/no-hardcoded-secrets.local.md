---
name: no-hardcoded-secrets
enabled: true
event: file_write
action: block
category: security
severity: critical
conditions:
  - field: new_text
    operator: regex_match
    pattern: (?:sk-[A-Za-z0-9]{32,}|ghp_[A-Za-z0-9]{36}|BEGIN\s+(?:RSA|EC|DSA|OPENSSH)\s+PRIVATE\s+KEY)
---
⚠️ BLOCKED: 检测到硬编码密钥/Token。

禁止将密钥直接写入代码：
- 使用环境变量: `os.environ["API_KEY"]`
- 使用 `.env` 文件（加入 `.gitignore`）
- 使用密钥管理服务（Vault / AWS Secrets Manager）

如果是测试密钥或在文档中，请用 `# nosec` 注释豁免。
