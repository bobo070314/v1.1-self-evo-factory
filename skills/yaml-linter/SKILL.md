---
name: yaml-linter
description: "Industrial-grade YAML diagnostic linter: precise [Line, Col] errors via PyYAML MarkedYAMLError, TAB detection, exit-code semantics (0/1/2), machine-readable JSON."
version: 1.0.1
type: skill
status: live
---

# yaml-linter

Diagnostic-expert YAML linter with precise line/column errors, TAB detection,
and professional CLI semantics. Part of the **Agnes Toolchain**.

## Usage

```bash
python run.py file.yaml                # human-readable report
python run.py file.yaml --json         # machine-readable JSON
python run.py --dry-run file.yaml      # validate path only (no content read)
echo "a: 1" | python run.py -          # lint from stdin
python run.py --version
```

## Options

| Arg | Description |
|-----|-------------|
| `--json` | Machine-readable JSON (tool/version/summary/files/diagnostics) |
| `--dry-run` | Validate environment + input paths only, don't read content |
| `--version` | Print `yaml-linter v1.0.1 (part of Agnes Toolchain)` |

## Exit Codes (semantic)

| Code | Meaning |
|------|---------|
| `0` | Valid / no errors (may have warnings) |
| `1` | Hard syntax error (fatal) |
| `2` | Warnings only (valid but style-recommended fixes) |

## JSON Schema (--json)

```json
{
  "tool": "yaml-linter",
  "version": "1.0.1",
  "dry_run": false,
  "summary": {"error": 2, "warning": 1},
  "files": [{
    "file": "a.yaml",
    "error": 2, "warning": 1,
    "diagnostics": [
      {"status": "error", "line": 5, "column": 1,
       "reason": "found character '\\t' that cannot start any token", "rule": "yaml-syntax"}
    ]
  }]
}
```

## Diagnostics

- **PyYAML path** (preferred): precise `Line`/`Col` from `MarkedYAMLError.problem_mark`,
  plus parser context lines. Requires PyYAML (`pip install pyyaml`).
- **Heuristic fallback** (no PyYAML): line-level TAB / indent-even / colon-space /
  quote-balance checks, reported as warnings.

## Engineering

- Exit codes map to machine-state (0 clean, 1 fatal, 2 warning) — CI-friendly.
- JSON diagnostics carry stable `status/line/column/reason/rule` fields.
