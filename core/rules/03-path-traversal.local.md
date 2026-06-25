---
name: path-traversal
enabled: true
event: file_write
action: warn
category: security
severity: critical
conditions:
  - field: new_text
    operator: regex_match
    pattern: \.\.\/|\.\.\\|open\(['\"]\.\.\/
---
⚠️ 路径穿越风险：检测到 `../` 路径拼接。

用户输入拼接到文件路径可能导致读取/写入任意文件。
- 使用 `os.path.realpath()` 或 `os.path.abspath()` 约束路径
- 对用户输入做白名单验证
- 使用 `pathlib.Path.resolve()` 并检查前缀
