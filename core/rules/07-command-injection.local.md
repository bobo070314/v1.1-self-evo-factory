---
name: command-injection
enabled: true
event: file_write
action: block
category: security
severity: critical
conditions:
  - field: new_text
    operator: regex_match
    pattern: (?:subprocess\(.*shell\s*=\s*True|os\.popen\(|exec\(|eval\(|__import__)
  - field: new_text
    operator: not_contains
    pattern: "# nosec"
---
⚠️ BLOCKED: 命令注入风险。

检测到 shell=True / eval / exec 等危险函数。
- 用参数列表: `subprocess.run(["ls", "-la"])` 而非 `subprocess.run("ls -la", shell=True)`
- 避免 eval/exec 执行用户输入
- 如果确实需要请加 `# nosec` 注释
