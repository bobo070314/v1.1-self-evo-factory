---
name: insecure-crypto
enabled: true
event: file_write
action: warn
category: security
severity: high
conditions:
  - field: new_text
    operator: regex_match
    pattern: (?:MD5|SHA-1|DES_|3DES|RC4|ECB|PBEWithMD5AndDES|RSA/ECB|hashlib\.md5|Crypto\.Cipher\.DES)
---
⚠️ 不安全的加密算法：检测到 MD5/SHA-1/DES/RC4/ECB 模式。

这些算法已被攻破或不安全。
- 密码哈希: bcrypt / argon2 / scrypt
- 签名: SHA-256 / SHA-3 / HMAC-SHA256
- 对称加密: AES-256-GCM（注意 AEAD，不要只用 ECB/CBC）
- Python: `cryptography` 库而非 `Crypto`
