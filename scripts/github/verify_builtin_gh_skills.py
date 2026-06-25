#!/usr/bin/env python3
"""Inject GitHub token + verify built-in skills"""
import sys, os, subprocess, json

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

REPO = r'D:\bobo\projects\v1.1-self-evo-factory'

def run(cmd, timeout=10):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True,
                           encoding='utf-8', errors='replace', timeout=timeout)
        return r.returncode, r.stdout.strip(), r.stderr.strip()
    except Exception as e:
        return -1, '', str(e)

# 1. gh token
rc, out, err = run(['gh', 'auth', 'token'])
if rc == 0 and len(out) > 20:
    token = out.split('\n')[0].strip()
    print(f'gh token: {token[:10]}...{token[-6:]} (len={len(token)})')

    # Inject
    api_file = os.path.join(REPO, 'config', 'api_tokens.json')
    os.makedirs(os.path.dirname(api_file), exist_ok=True)
    api = {}
    if os.path.isfile(api_file):
        with open(api_file, 'r', encoding='utf-8') as f:
            api = json.load(f)
    api['GITHUB_TOKEN'] = token
    api['GH_TOKEN'] = token
    with open(api_file, 'w', encoding='utf-8') as f:
        json.dump(api, f, indent=2, ensure_ascii=False)
    print(f'Token injected -> {api_file}')

    # Set env vars for this session
    os.environ['GH_TOKEN'] = token
    os.environ['GITHUB_TOKEN'] = token

    # API rate limit check
    rc2, out2, _ = run(['gh', 'api', 'rate_limit', '--jq', '.rate.remaining'])
    if rc2 == 0:
        print(f'API rate remaining: {out2}')
    else:
        print(f'API check failed: rc={rc2}')
else:
    print(f'gh token FAILED: rc={rc} err={err[:80]}')

# 2. Check OpenClaw built-in skills
print()
base_skills = r'C:\Users\asus\AppData\Roaming\npm\node_modules\openclaw\skills'
if os.path.isdir(base_skills):
    gh_skills = [d for d in os.listdir(base_skills) if 'github' in d.lower()]
    if gh_skills:
        print(f'Built-in GitHub skills found: {gh_skills}')
    else:
        print('No built-in GitHub skills (may use a different path)')
else:
    print(f'Base skills path not found: {base_skills}')

# Alternative: check OpenClaw data path
alt_path = os.path.expanduser(r'~\.openclaw\skills')
if os.path.isdir(alt_path):
    gh_skills = [d for d in os.listdir(alt_path) if 'github' in d.lower()]
    print(f'Alt skills path ({alt_path}): {gh_skills}')

# 3. kairos
print()
try:
    sys.path.insert(0, REPO)
    from core.kairos_scheduler import KairosScheduler
    ks = KairosScheduler()
    h = ks.health() if hasattr(ks, 'health') else {}
    print(f'kairos: repos={h.get("watched_repos",[])} interval={h.get("poll_interval",0)}s')
except Exception as e:
    print(f'kairos: {str(e)[:60]}')

print()
print('DONE')
