---
name: sql-injection
enabled: true
event: file_write
action: warn
category: security
severity: critical
conditions:
  - field: new_text
    operator: regex_match
    pattern: (?:SELECT|INSERT|UPDATE|DELETE).*['\"]\s*\+\s*(?:user_input|request\.GET|request\.POST|req\.body)
---
⚠️ SQL 注入风险：检测字符串拼接构建 SQL。

直接拼接用户输入到 SQL 语句会导致 SQL 注入攻击。
- 使用参数化查询：`cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))`
- ORM 框架（Prisma/SQLAlchemy/TypeORM）自动参数化
- 永远不要 `f"SELECT ... WHERE id = '{user_id}'"`
