---
name: xxe-vulnerable
enabled: true
event: file_write
action: warn
category: security
severity: high
conditions:
  - field: new_text
    operator: regex_match
    pattern: (?:XMLParser\(|lxml\.parse|xml\.dom\.minidom\.parse|xml\.etree|SimpleXML|Xerces|DocumentBuilder)
  - field: new_text
    operator: not_contains
    pattern: (?:XXE|entity_expansion|resolve_external|setFeature|FEATURE_SECURE_PROCESSING)
---
⚠️ XXE 注入风险：XML 解析器可能允许外部实体扩展。

XML 外部实体(XXE)攻击可读取服务器文件或导致 SSRF。
- 禁用 DTD 和外部实体: `parser.setFeature("http://apache.org/xml/features/disallow-doctype-decl", true)`
- Python: `defusedxml` 库替代标准 XML 库
- 优先使用 JSON 而非 XML
