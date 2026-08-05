---
name: css-minifier
description: "Industrial-grade CSS minifier: strips comments/whitespace/redundant semicolons while preserving semantics. Exit-code semantics (0/1), honest --dry-run, machine-readable JSON with savings %."
version: 1.0.1
type: skill
status: live
---

# css-minifier

Industrial-grade CSS minifier. Compresses comments, whitespace, and redundant
semicolons (safe cases) while keeping semantic equivalence. Part of the
**Agnes Toolchain**.

## Usage

```bash
python run.py input.css
python run.py input.css --json          # + savings % report
python run.py input.css --dry-run       # validate path only
echo "body { color: red; }" | python run.py -
python run.py --version
```

## Options

| Arg | Description |
|-----|-------------|
| `--json` | Machine-readable JSON (tool/version/file/sizes/savings_pct) |
| `--dry-run` | Validate input path only, never read/minify content |
| `--version` | Print `css-minifier v1.0.1 (part of Agnes Toolchain)` |

## Exit Codes

| Code | Meaning |
|------|---------|
| `0` | Success |
| `1` | Input error (file missing / unreadable) |

## JSON Schema (--json)

```json
{
  "tool": "css-minifier",
  "version": "1.0.1",
  "file": "a.css",
  "minified": ".a{color:red}",
  "original_size": 21,
  "minified_size": 13,
  "savings_pct": 38.1
}
```

## Minification

- Single-pass scanner: preserves string literals, handles `url(...)` context,
  strips `/* */` comments and redundant whitespace outside strings.
- Redundant semicolons before closing braces are removed (CSS-safe).
