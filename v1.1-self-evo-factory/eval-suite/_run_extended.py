import subprocess, sys, json, os
os.environ['PYTHONIOENCODING'] = 'utf-8'

def run(cmd, timeout=30):
    r = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=timeout)
    return r.returncode, r.stdout, r.stderr

base = r'D:\bobo\openclaw-foreign\workspace\v1.1-self-evo-factory'

# Test 06: token-saver compression
print('TEST 06: Token-saver compression')
rc, out, err = run([sys.executable,
    r'D:\bobo\openclaw-foreign\workspace\skills\token-saver\run.py',
    '--command', 'python -c "for i in range(500): print(\'line_\' + str(i))"',
    '--json', '--max-lines', '50'])
d = json.loads(out)
pct = d['stats']['stdout_compression_pct']
print(f"  {'PASS' if pct > 50 else 'FAIL'}: {d['stats']['stdout_original_lines']}->{d['stats']['stdout_compressed_lines']} lines ({pct}%)")

# Test 07: exit code passthrough
print('TEST 07: Token-saver exit code')
rc1, _, _ = run([sys.executable,
    r'D:\bobo\openclaw-foreign\workspace\skills\token-saver\run.py',
    '--command', 'python -c "exit(42)"'])
print(f"  {'PASS' if rc1 == 42 else 'FAIL'}: exit code {rc1}")

# Test 08: sandbox security
print('TEST 08: Sandbox security')
sb_path = r'D:\bobo\openclaw-foreign\workspace\skills\sandbox-executor\run.py'
rc, out, err = run([sys.executable, sb_path, '--verify', '--json'], timeout=45)
d = json.loads(out)
print(f"  {'PASS' if d.get('secure') else 'FAIL'}: {d.get('verdict', 'unknown')}")

# Test 09: sandbox normal
print('TEST 09: Sandbox normal exec')
rc, out, err = run([sys.executable, sb_path, '--cmd', 'echo hello_sandbox', '--json'], timeout=30)
d = json.loads(out)
print(f"  {'PASS' if 'hello_sandbox' in d.get('stdout','') else 'FAIL'}: stdout has hello_sandbox")

# Test 10: self_improve dry run
print('TEST 10: Self-improve dry run')
rc, out, err = run([sys.executable, base + r'\pipeline\self_improve.py', 'self_coder', '--dry-run'], timeout=45)
print(f"  {'PASS' if 'Report saved' in out else 'FAIL'}")

# Test 11: full pipeline
print('TEST 11: Full pipeline')
rc1, out1, _ = run([sys.executable, base + r'\pipeline\self_coder.py', '--rules', base + r'\pipeline\self_coder.py'])
zero_err = '[ERR]' not in out1
rc2, out2, _ = run([sys.executable, base + r'\eval-suite\test_self_coder.py'])
all_green = 'ALL GREEN' in out2
print(f"  {'PASS' if zero_err and all_green else 'FAIL'}: 0_errors={zero_err} all_green={all_green}")

print()
print('Done.')
