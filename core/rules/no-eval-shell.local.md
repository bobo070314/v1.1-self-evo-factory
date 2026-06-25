---
name: no-eval-shell
enabled: true
event: file_write
action: block
category: security
severity: critical
conditions:
  - field: new_text
    operator: regex_match
    pattern: (?:eval\(|os\.system\(|subprocess\(.*shell\s*=\s*True)
  - field: new_text
    operator: not_contains
    pattern: "# nosec"
---
⚠️ BLOCKED: 检测到 eval() / os.system() / subprocess(shell=True)。

这些函数在接收用户输入时会导致命令注入漏洞。

安全替代方案：
- 命令参数传递：`subprocess.run(["ls", "-la"])`（无 shell）
- 表达式计算：用 AST 表达式解析器替代 eval
- os.system：改用 subprocess.run 并关闭 shell=True

如果确实需要且输入可控，请加 `# nosec` 注释豁免。
