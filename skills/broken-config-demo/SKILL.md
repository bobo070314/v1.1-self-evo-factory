---
name: broken-config-demo
description: "Demo fixture for the self-healing loop: a config whose _meta.json is repaired automatically by Agnes LLM when it has syntax errors. Run scripts/test_self_healing.py to exercise the Diagnosis→Fix→Verify loop."
version: 0.1.0
type: skill
status: demo
---

# broken-config-demo

Demo fixture proving the **self-healing loop**:

```
yaml-linter (diagnose) → Agnes LLM (fix) → yaml-linter (verify rc=0)
```

## Usage

```bash
# Force a syntax error (Tab indentation) then watch it heal itself
python scripts/test_self_healing.py   # heals skills/broken-config-demo/_meta.json

# Or self-heal any yaml/json file:
python scripts/test_self_healing.py path/to/some.yaml
```

## How it works

1. `test_self_healing.py` runs `skills/yaml-linter/run.py --json` on the target.
2. If lint errors exist, original content + linter diagnostics are sent to
   Agnes (`scripts/agnes_client.py`, zero-cost `agnes-2.5-flash`).
3. LLM returns the repaired content; script writes it back.
4. Linter re-runs; exit 0 = **evolved** (success). On failure, content is rolled back.

This is the building block that turns self_evolve.py from a "grader" into a
"doctor": tool discovers problem → LLM solves it → tool verifies solution.
