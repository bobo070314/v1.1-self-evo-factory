---
name: link-checker
description: Validate URLs in Markdown/HTML/text files over HTTP with status classification, retry, and JSON output.
version: 1.0.0
type: skill
status: live
---

# link-checker

工业级链接体检工具：从 Markdown / HTML / 纯文本中提取 URL，逐个做 HTTP 检查，
输出状态分级（ok / redirect / client_error / server_error / error）与机器可读 JSON。

## 使用

```bash
python run.py input.md          # 检查文件内所有链接，人类可读输出
python run.py input.md --json   # JSON 输出（供 Gatekeeper/流水线消费）
python run.py input.md --dry-run# 只提取不联网（离线体检）
echo "https://example.com" | python run.py -   # 标准输入
python run.py --version
```

## 退出码语义

- `0`：全部链接有效（或 dry-run 提取成功）
- `1`：存在至少一个失效链接
- `2`：文件不存在 / 输入错误

## 能力边界

- **HEAD 优先，GET 降级**：服务器拒绝 HEAD（405/501）时自动重试 GET
- **重试退避**：最多 2 次重试，0.8s 起指数退避
- **URL 规范化**：剔除尾部标点噪声（`).,;:!?`）、去重、保序
- **超时保护**：单请求 8s 超时，不会无限挂起

## 输出示例

```
link-checker 1.0.0: 4 URLs (1 ok / 3 broken) [live]
  OK  https://example.com  (ok)
  !!  https://example.com/dead  (HTTP 404)
```

## 注意

- 网络检查依赖外网连通性，httpbin 类测试服务可能限流（503/超时），属正常
- `--dry-run` 是纯本地操作，零网络、零 Token 成本
