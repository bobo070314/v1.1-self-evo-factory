---
name: llm-query-agnes
description: Free LLM query via agnes-2.5-flash (OpenAI-compatible, zero cost). Single-call text completion for agent pipelines and SelfEvolver fixes.
version: 0.2.0
type: skill
status: live
---

# llm-query-agnes

Free LLM access for skill pipelines. Calls `https://apihub.agnes-ai.com/v1/chat/completions`
with model `agnes-2.5-flash` (cost = 0, context 128K, max_tokens 8192).
No external dependency (standard library `urllib` only).

## Usage

```bash
python run.py --prompt "修复这段代码" --json
python run.py --prompt "..." --max-tokens 2048 --temperature 0
python run.py --version
python run.py --help
```

## Options

| Arg | Description |
|-----|-------------|
| `--prompt` | (required) User prompt text |
| `--model` | Default `agnes-2.5-flash` |
| `--max-tokens` | Default 1024 |
| `--temperature` | Default 0.2 |
| `--json` | Output machine-readable JSON |
| `--dry-run` | Print request info without calling API |

## Auth

Environment variable `AGNES_API_KEY` (loaded from OpenClaw env). The gateway
does not verify a local key — use the real env value for external calls.

## Notes

- Do NOT use `127.0.0.1:18789` — that is the Control UI port, not the LLM API.
- Model id is `agnes-2.5-flash` (no `agnes/` provider prefix).
