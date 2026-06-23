#!/usr/bin/env python3
"""
V1.5 Eval Suite — Extended Test Cases
Tests for: token-saver + sandbox-executor + self_improve
"""

import subprocess
import sys
import os
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SKILLS_ROOT = PROJECT_ROOT.parent / 'skills'

os.environ.setdefault('PYTHONIOENCODING', 'utf-8')


def safe_run(cmd, timeout=30):
    r = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=timeout)
    return r.returncode, r.stdout, r.stderr


# ─── test_06_token_saver ───────────────────────────────────────

def test_06_token_saver_compress():
    """Token saver compresses large output."""
    print("TEST 06: Token-saver compression")
    token_saver = SKILLS_ROOT / 'token-saver' / 'run.py'
    if not token_saver.exists():
        print("  SKIP: token-saver not found")
        return True

    # Generate 500 lines of fake output
    rc, stdout, stderr = safe_run([
        sys.executable, str(token_saver),
        '--command', 'python -c "for i in range(500): print(f\'line_{i}\')"',
        '--json',
        '--max-lines', '50',
    ])
    data = json.loads(stdout)
    orig = data['stats']['stdout_original_lines']
    comp = data['stats']['stdout_compressed_lines']
    pct = data['stats']['stdout_compression_pct']

    if orig > comp and pct > 50:
        print(f"  PASS: {orig}->{comp} lines ({pct}% compression)")
        return True
    else:
        print(f"  FAIL: {orig}->{comp} lines ({pct}%)")
        return False


def test_07_token_saver_exit_code():
    """Token saver passes through exit codes."""
    print("TEST 07: Token-saver exit code passthrough")
    token_saver = SKILLS_ROOT / 'token-saver' / 'run.py'

    rc1, _, _ = safe_run([sys.executable, str(token_saver), '--command', 'python -c "exit(0)"'])
    rc2, _, _ = safe_run([sys.executable, str(token_saver), '--command', 'python -c "exit(42)"'])

    if rc1 == 0 and rc2 == 42:
        print("  PASS: exit codes 0 and 42 passed through correctly")
        return True
    else:
        print(f"  FAIL: got {rc1} and {rc2}, expected 0 and 42")
        return False


# ─── test_08_sandbox ───────────────────────────────────────────

def test_08_sandbox_security():
    """Sandbox blocks destructive operations."""
    print("TEST 08: Sandbox security verification")
    sandbox = SKILLS_ROOT / 'sandbox-executor' / 'run.py'
    if not sandbox.exists():
        print("  SKIP: sandbox-executor not found")
        return True

    rc, stdout, stderr = safe_run([
        sys.executable, str(sandbox), '--verify', '--json',
    ], timeout=45)
    data = json.loads(stdout)
    if data.get('secure'):
        print(f"  PASS: {data['verdict']}")
        return True
    else:
        print(f"  FAIL: {data['verdict']} (sandbox_type={data.get('sandbox_type')})")
        return False


def test_09_sandbox_normal_exec():
    """Sandbox runs normal commands correctly."""
    print("TEST 09: Sandbox normal execution")
    sandbox = SKILLS_ROOT / 'sandbox-executor' / 'run.py'

    rc, stdout, stderr = safe_run([
        sys.executable, str(sandbox), '--cmd', 'echo hello_world', '--json',
    ], timeout=30)
    data = json.loads(stdout)
    if 'hello_world' in data.get('stdout', ''):
        print(f"  PASS: Normal command executed in {data['sandbox']}")
        return True
    else:
        print(f"  FAIL: stdout={data.get('stdout', '')[:100]}")
        return False


# ─── test_10_self_improve ──────────────────────────────────────

def test_10_self_improve_dry():
    """Self-improve dry run completes without error."""
    print("TEST 10: Self-improve dry run")
    improve = PROJECT_ROOT / 'pipeline' / 'self_improve.py'

    rc, stdout, stderr = safe_run([
        sys.executable, str(improve), 'self_coder', '--dry-run',
    ], timeout=45)

    if 'Report saved' in stdout and rc == 0:
        print("  PASS: Dry run completed, report saved")
        return True
    else:
        print(f"  FAIL: rc={rc}, stderr={stderr[:200]}")
        return False


# ─── test_11_full_pipeline ─────────────────────────────────────

def test_11_full_pipeline():
    """End-to-end: self_coder + eval + self_improve."""
    print("TEST 11: Full pipeline e2e")

    # 1. self_coder self-scan
    rc1, stdout1, _ = safe_run([
        sys.executable, str(PROJECT_ROOT / 'pipeline' / 'self_coder.py'),
        '--rules', str(PROJECT_ROOT / 'pipeline' / 'self_coder.py'),
    ])
    zero_errors = '[ERR]' not in stdout1

    # 2. eval suite
    rc2, stdout2, _ = safe_run([
        sys.executable, str(PROJECT_ROOT / 'eval-suite' / 'test_self_coder.py'),
    ])
    all_green = 'ALL GREEN' in stdout2

    if zero_errors and all_green:
        print("  PASS: self_coder 0 errors + eval 5/5 green")
        return True
    else:
        print(f"  FAIL: zero_errors={zero_errors}, all_green={all_green}")
        return False


# ─── Main ──────────────────────────────────────────────────────

def main():
    tests = [
        ('Token-saver compression', test_06_token_saver_compress),
        ('Token-saver exit code', test_07_token_saver_exit_code),
        ('Sandbox security', test_08_sandbox_security),
        ('Sandbox normal exec', test_09_sandbox_normal_exec),
        ('Self-improve dry run', test_10_self_improve_dry),
        ('Full pipeline e2e', test_11_full_pipeline),
    ]

    print("=" * 50)
    print("V1.5 Eval Suite — Extended Tests (6 new)")
    print("=" * 50)
    print()

    passed = 0
    failed = 0

    for name, test_fn in tests:
        try:
            if test_fn():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"  CRASH: {e}")
            failed += 1
        print()

    print("=" * 50)
    print(f"RESULTS: {passed}/{passed + failed} passed")
    if failed == 0:
        print("ALL GREEN!")
    else:
        print(f"{failed} test(s) FAILED")
    print("=" * 50)

    return 0 if failed == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
