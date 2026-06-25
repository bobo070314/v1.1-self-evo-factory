---
name: hardcoded-secret-yolo
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
⚠️ BLOCKED: 检测到硬编码密钥。

禁止将密钥直接写入代码文件。
- 使用环境变量: `os.environ["API_KEY"]`
- 使用 `.env` 文件（加入 `.gitignore`）
- 使用密钥管理服务
- 测试密钥请加 `# nosec` 豁免
