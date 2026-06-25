#!/usr/bin/env python3
"""GitHub 全链缺口审计"""
import os, sys, json, subprocess

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

WSDIR = r'D:\bobo\openclaw-foreign\workspace'
SKILLS = r'D:\bobo\openclaw-foreign\skills'
CONFIG = r'D:\bobo\openclaw-foreign\openclaw.json'
REPO = r'D:\bobo\projects\v1.1-self-evo-factory'
GAPS = []

def gap(msg):
    GAPS.append(msg)
    print(f'  [GAP] {msg}')

def ok(msg):
    print(f'  [OK]  {msg}')

def run(cmd, cwd=None, timeout=10):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True,
                           encoding='utf-8', errors='replace',
                           timeout=timeout, cwd=cwd)
        return r.returncode, r.stdout.strip(), r.stderr.strip()
    except Exception as e:
        return -1, '', str(e)

print('=' * 70)
print('GITHUB FULL CHAIN AUDIT')
print('=' * 70)

# === 1. openclaw.json entries ===
print('\n--- [1] openclaw.json GitHub entries ---')
d = json.load(open(CONFIG, 'r', encoding='utf-8-sig'))
ents = d['skills']['entries']
gh_names = [
    'github-actions-generator', 'web-deploy-github', 'create-pr', 'create-issue',
    'release-notes-generator', 'deployment-automation', 'version-release',
    'github-ai-trends', 'read-github', 'github',
]
for s in gh_names:
    if s in ents:
        en = ents[s].get('enabled', False)
        if en:
            ok(f'{s}: enabled')
        else:
            gap(f'{s}: entries exists but NOT enabled')
    else:
        gap(f'{s}: NOT in entries')

# === 2. extraDirs GitHub skill dirs ===
print('\n--- [2] extraDirs GitHub skill dirs ---')
gh_names_set = set(gh_names)
gh_skills = [d for d in os.listdir(SKILLS) if os.path.isdir(os.path.join(SKILLS,d)) and
             ('github' in d.lower() or d in gh_names_set)]
for dname in sorted(gh_skills):
    dp = os.path.join(SKILLS, dname)
    runpy = os.path.join(dp, 'run.py')
    has_run = os.path.isfile(runpy)
    in_ents = dname in ents
    enabled = in_ents and ents[dname].get('enabled', False)
    v = '--'
    if has_run:
        rc, out, _ = run([sys.executable, runpy, '--version'], cwd=dp, timeout=5)
        v = out if rc == 0 else 'ERR'
    issues = []
    if not in_ents:
        issues.append('NO_ENTRY')
    if not enabled:
        issues.append('DISABLED')
    if not has_run:
        issues.append('NO_RUNPY')
    status = ' | '.join(issues)
    if status:
        gap(f'{dname:30s} {status}')
    else:
        ok(f'{dname:30s} v={v}')

# === 3. scripts/github/ ===
print('\n--- [3] scripts/github/ ---')
gd = os.path.join(WSDIR, 'scripts', 'github')
if os.path.isdir(gd):
    for f in sorted(os.listdir(gd)):
        fp = os.path.join(gd, f)
        sz = os.path.getsize(fp)
        try:
            compile(open(fp, encoding='utf-8', errors='replace').read(), fp, 'exec')
            ok(f'{f:40s} {sz:>6}B syntax OK')
        except SyntaxError as e:
            gap(f'{f:40s} {sz:>6}B SYNTAX ERROR: {str(e)[:40]}')
else:
    gap('scripts/github/ dir MISSING')

# === 4. scripts/ root orphan GitHub scripts ===
print('\n--- [4] scripts/ root orphan GitHub scripts ---')
sd = os.path.join(WSDIR, 'scripts')
if os.path.isdir(sd):
    orphans = [f for f in os.listdir(sd) if f.endswith('.py') and
               ('github' in f.lower() or 'gh_' in f.lower() or 'kairos' in f.lower())]
    for f in sorted(orphans):
        gap(f'{f} in scripts/ root (should be in scripts/github/)')
else:
    ok('no orphan scripts in root')

# === 5. gh-enterprise-baseline ===
print('\n--- [5] gh-enterprise-baseline sub-repos ---')
base = os.path.join(WSDIR, 'gh-enterprise-baseline')
if os.path.isdir(base):
    missing = []
    for d in sorted(os.listdir(base)):
        dp = os.path.join(base, d)
        if not os.path.isdir(dp) or not os.path.isdir(os.path.join(dp, '.git')):
            continue
        rc, origin, _ = run(['git', '-C', dp, 'remote', 'get-url', 'origin'], timeout=5)
        if rc == 0 and 'github.com' in origin:
            ok(f'{d:30s} origin OK')
        else:
            gap(f'{d:30s} NO/MISSING origin remote')
            missing.append(d)
    if not missing:
        ok('all 10 sub-repos have valid GitHub origins')
else:
    gap('gh-enterprise-baseline dir MISSING')

# === 6. v1.1-self-evo-factory repo ===
print('\n--- [6] v1.1-self-evo-factory GitHub remote ---')
rc, origin, _ = run(['git', '-C', REPO, 'remote', 'get-url', 'origin'], timeout=5)
if rc == 0 and 'github.com' in origin:
    ok(f'origin={origin}')
else:
    gap(f'origin MISSING or wrong: {origin}')

# also check workspace remote
rc2, origin2, _ = run(['git', '-C', WSDIR, 'remote', 'get-url', 'origin'], timeout=5)
if rc2 == 0 and 'github.com' in origin2:
    ok(f'workspace origin={origin2}')
else:
    gap(f'workspace origin: {origin2}')

# === 7. kairos integration ===
print('\n--- [7] kairos_scheduler.py GitHub watcher ---')
try:
    sys.path.insert(0, REPO)
    from core.kairos_scheduler import KairosScheduler
    ks = KairosScheduler()
    h = ks.health() if hasattr(ks, 'health') else {}
    repos = h.get('watched_repos', [])
    if repos:
        ok(f'watched repos: {repos}')
    else:
        gap('kairos: no watched repos')
except Exception as e:
    gap(f'kairos import error: {str(e)[:60]}')

# === 8. GitHub Token ===
print('\n--- [8] GitHub Token availability ---')
token = os.environ.get('GH_TOKEN') or os.environ.get('GITHUB_TOKEN') or ''
if token:
    ok(f'token present: length {len(token)}')
else:
    gap('NO GitHub token in env vars')

rc, out, _ = run(['gh', 'auth', 'status'], timeout=5)
if rc == 0:
    ok('gh CLI authenticated')
else:
    gap(f'gh CLI status: {out[:60]}')

# === 9. OpenClaw built-in github skill ===
print('\n--- [9] OpenClaw built-in github skill available ---')
rc, out, _ = run(['C:\\Users\\asus\\AppData\\Roaming\\npm\\openclaw.cmd', 'skills', 'list'], timeout=10)
if rc == 0:
    if 'github' in out.lower():
        ok('openclaw built-in github skill found')
    else:
        gap('openclaw built-in github skill NOT in list')
else:
    gap(f'openclaw skills list error: {out[:60]}')

# === SUMMARY ===
print(f'\n{"=" * 70}')
if GAPS:
    print(f'GAPS FOUND: {len(GAPS)}')
    for g in GAPS:
        print(f'  [GAP] {g}')
else:
    print('NO GAPS FOUND - ALL CLEAN')
print(f'{"=" * 70}')
sys.exit(1 if GAPS else 0)
