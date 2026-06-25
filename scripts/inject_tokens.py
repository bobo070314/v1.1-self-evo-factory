#!/usr/bin/env python3
import os, sys, json, subprocess
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

REPO = r'D:\bobo\projects\v1.1-self-evo-factory'
api_file = os.path.join(REPO, 'config', 'api_tokens.json')

# Get gh token
r = subprocess.run(['gh', 'auth', 'token'], capture_output=True, text=True, timeout=10)
token = r.stdout.strip()
print(f'Token: {token[:10]}...{token[-6:]}')

# Write
os.makedirs(os.path.dirname(api_file), exist_ok=True)
with open(api_file, 'w', encoding='utf-8') as f:
    json.dump({'GITHUB_TOKEN': token, 'GH_TOKEN': token}, f, indent=2)
print(f'Wrote {api_file}')

# Verify read
with open(api_file, 'r', encoding='utf-8') as f:
    data = json.load(f)
t = data.get('GITHUB_TOKEN', '')
print(f'Verified: GITHUB_TOKEN={t[:10]}...{t[-4:]}')

# API check
r = subprocess.run(['gh', 'api', 'rate_limit', '--jq', '.rate.remaining'],
                   capture_output=True, text=True, timeout=10)
print(f'API remaining: {r.stdout.strip()}')
