# HEARTBEAT.md

## Periodic Checks (rotate through these, ~2-4x per day)

### ⚙️ subconscious-daemon health
Run: `$env:PYTHONIOENCODING="utf-8"; python D:\bobo\openclaw-foreign\skills\subconscious-daemon\run.py --json`
- If `status: OK` -> silent
- If `status: ALERT` -> surface to user with details
- Track last check in `memory/heartbeat-state.json`

### 🔐 Token Vault health
Run: `$env:PYTHONIOENCODING="utf-8"; cd D:\bobo\openclaw-foreign\workspace\v1.1-self-evo-factory; python pipeline\test_api_skills.py --check-health --json`
- If `populated: 0` or `ok: false` -> alert user

### 📦 Git status
Run: `git -C D:\bobo\openclaw-foreign\workspace status --short`
- Uncommitted work? -> note it

### 🧪 API skills
Run: `$env:PYTHONIOENCODING="utf-8"; cd D:\bobo\openclaw-foreign\workspace\v1.1-self-evo-factory; python pipeline\test_api_skills.py --json`
- Failures > 0? -> investigate and report

## Schedule Suggestion
- Morning (9:00): full API test + git status
- Midday (13:00): daemon + vault
- Evening (19:00): daemon + git status
- Night (23:00): daemon only (silent unless alerts)
