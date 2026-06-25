---
name: unsafe-deserialization
enabled: true
event: file_write
action: block
category: security
severity: critical
conditions:
  - field: new_text
    operator: regex_match
    pattern: (?:pickle\.loads?\(|yaml\.load\([^)]*(?!SafeLoader|FullLoader)|numpy\.load\(|torch\.load\()
---
⚠️ BLOCKED: 不安全的反序列化函数。

pickle/yaml.load(无SafeLoader)/numpy.load/torch.load 可执行任意代码。
- 用 JSON 替代 pickle: `json.loads()`
- YAML: 用 `yaml.safe_load()` 而非 `yaml.load()`
- 如必须用，确保数据源可信且已签名
