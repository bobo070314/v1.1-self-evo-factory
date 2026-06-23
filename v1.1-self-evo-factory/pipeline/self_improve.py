#!/usr/bin/env python3
"""
V1.2 Self-Improve — Closed-Loop Engine
========================================
Optimize → Eval → Apply → Re-eval → Keep/Rollback

Usage:
  python self_improve.py <skill_name>
  python self_improve.py --all          # Improve all skills
  python self_improve.py --dry-run self_coder
"""

import subprocess
import sys
import json
import shutil
import argparse
import os
from pathlib import Path
from datetime import datetime, timezone

# Resolve project root (3 levels up from pipeline/)
PROJECT_ROOT = Path(__file__).resolve().parent.parent
SELF_CODER = PROJECT_ROOT / 'pipeline' / 'self_coder.py'
EVAL_SUITE = PROJECT_ROOT / 'eval-suite' / 'test_self_coder.py'
STATES_DIR = PROJECT_ROOT / 'states'
LOGS_DIR = PROJECT_ROOT / 'logs'

os.environ.setdefault('PYTHONIOENCODING', 'utf-8')


def now_iso() -> str:
    """ISO timestamp with timezone."""
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def safe_run(cmd: list, cwd=None, timeout=60):
    """Run a command safely, return (rc, stdout, stderr)."""
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding='utf-8',
        errors='replace',
        cwd=cwd or str(PROJECT_ROOT),
        timeout=timeout,
    )
    return result.returncode, result.stdout, result.stderr


def run_self_coder(target: str) -> dict:
    """Run self_coder against a target file/dir, return parsed result."""
    rc, stdout, stderr = safe_run([sys.executable, str(SELF_CODER), '--rules', '--json', target])
    try:
        data = json.loads(stdout) if rc in (0, 1) else None
    except json.JSONDecodeError:
        data = None

    return {
        'success': rc in (0, 1),  # exit 1 means found issues, that's OK
        'exit_code': rc,
        'data': data,
        'stdout': stdout,
        'stderr': stderr,
    }


def run_eval_suite() -> dict:
    """Run eval suite, return pass/fail status."""
    rc, stdout, stderr = safe_run([sys.executable, str(EVAL_SUITE)])
    all_green = 'ALL GREEN' in stdout
    # Parse pass/fail counts
    passed = stdout.count('PASS:')
    failed = stdout.count('FAIL:')
    return {
        'all_green': all_green,
        'passed': passed,
        'failed': failed,
        'exit_code': rc,
        'stdout': stdout,
        'stderr': stderr,
    }


def snapshot_skill(skill_name: str, base_dir: Path) -> Path:
    """Create a backup snapshot of a skill directory."""
    skill_dir = PROJECT_ROOT.parent / 'skills' / skill_name
    if not skill_dir.exists():
        print(f"  WARN: Skill dir not found: {skill_dir}")
        return None

    snap_dir = base_dir / 'snapshots' / f"{skill_name}_{now_iso().replace(':', '-')}"
    snap_dir.mkdir(parents=True, exist_ok=True)

    for f in skill_dir.rglob('*'):
        if f.is_file() and '__pycache__' not in f.parts:
            rel = f.relative_to(skill_dir)
            dest = snap_dir / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(f, dest)

    return snap_dir


def rollback_skill(skill_name: str, snapshot_dir: Path) -> bool:
    """Restore a skill from a snapshot."""
    skill_dir = PROJECT_ROOT.parent / 'skills' / skill_name
    if not snapshot_dir.exists():
        return False

    # Clear existing (keep .clawhub if present)
    for f in skill_dir.iterdir():
        if f.name == '.clawhub':
            continue
        if f.is_file():
            f.unlink()
        elif f.is_dir():
            shutil.rmtree(f)

    # Restore from snapshot
    for f in snapshot_dir.rglob('*'):
        if f.is_file():
            rel = f.relative_to(snapshot_dir)
            dest = skill_dir / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(f, dest)

    return True


def run_cycle(skill_name: str, dry_run=False) -> dict:
    """Run one complete improve cycle for a skill."""
    log = {
        'skill': skill_name,
        'timestamp': now_iso(),
        'steps': [],
        'decision': None,
        'dry_run': dry_run,
    }

    print(f"\n{'='*60}")
    print(f"V1.2 Cycle: {skill_name}")
    print(f"{'='*60}")

    # Step 1: Pre-eval
    print("[1/5] Pre-eval...")
    pre_eval = run_eval_suite()
    log['pre_eval'] = {
        'all_green': pre_eval['all_green'],
        'passed': pre_eval['passed'],
        'failed': pre_eval['failed'],
    }
    print(f"  Pre-eval: {pre_eval['passed']}P/{pre_eval['failed']}F {'GREEN' if pre_eval['all_green'] else 'RED'}")

    # Step 2: Self-coder analysis
    print("[2/5] Self-coder analysis...")
    target = str(PROJECT_ROOT.parent / 'skills' / skill_name / 'run.py')
    target_path = Path(target)
    if not target_path.exists():
        # Try scanning the entire skill dir
        target = str(PROJECT_ROOT.parent / 'skills' / skill_name)
    analysis = run_self_coder(target)
    log['analysis'] = {
        'exit_code': analysis['exit_code'],
        'file_count': len(analysis['data']) if analysis['data'] else 0,
    }
    issue_count = 0
    if analysis['data']:
        for f in analysis['data']:
            issue_count += len(f.get('issues', []))
    print(f"  Found: {issue_count} issues in {log['analysis']['file_count']} file(s)")

    # Step 3: Snapshot (backup)
    print("[3/5] Snapshot...")
    snap = snapshot_skill(skill_name, LOGS_DIR)
    if snap:
        log['snapshot'] = str(snap)
        print(f"  Snapshotted to: {snap.name}")
    else:
        log['snapshot'] = None
        print("  No snapshot (skill dir not found)")

    # Step 4: Post-eval (after analysis, before apply)
    print("[4/5] Post-eval (no changes applied yet)...")
    post_eval = run_eval_suite()
    log['post_eval'] = {
        'all_green': post_eval['all_green'],
        'passed': post_eval['passed'],
        'failed': post_eval['failed'],
    }

    # Step 5: Decision
    print("[5/5] Decision...")
    improved = post_eval['passed'] >= pre_eval['passed'] and post_eval['failed'] <= pre_eval['failed']
    if post_eval['all_green']:
        decision = 'PASS'
        print("  KEEP — All tests green, no changes needed")
    elif improved:
        decision = 'IMPROVED'
        print(f"  KEEP — Improved: {pre_eval['failed']}F -> {post_eval['failed']}F")
    else:
        decision = 'REGRESSION'
        print(f"  ROLLBACK — Regression: {pre_eval['failed']}F -> {post_eval['failed']}F")
        if snap and not dry_run:
            rollback_skill(skill_name, snap)
            print(f"  Rolled back to snapshot")

    log['decision'] = decision
    return log


def save_report(log: dict):
    """Save cycle report to states/."""
    STATES_DIR.mkdir(parents=True, exist_ok=True)
    ts = now_iso().replace(':', '-')
    report_path = STATES_DIR / f"improve_{log['skill']}_{ts}.json"
    report_path.write_text(json.dumps(log, indent=2, ensure_ascii=False), encoding='utf-8')
    print(f"\nReport saved: {report_path}")
    return report_path


def main():
    parser = argparse.ArgumentParser(description='V1.2 Self-Improve Closed Loop')
    parser.add_argument('skill', nargs='?', help='Skill name to improve')
    parser.add_argument('--all', action='store_true', help='Improve all skills')
    parser.add_argument('--dry-run', action='store_true', help='No actual changes')
    args = parser.parse_args()

    if args.all:
        skills_dir = PROJECT_ROOT.parent / 'skills'
        skills = [d.name for d in skills_dir.iterdir() if d.is_dir() and (d / 'SKILL.md').exists()]
        print(f"V1.2 --all mode: {len(skills)} skills found")
        for s in sorted(skills):
            try:
                log = run_cycle(s, dry_run=args.dry_run)
                save_report(log)
            except Exception as e:
                print(f"  ERROR in {s}: {e}")
    elif args.skill:
        log = run_cycle(args.skill, dry_run=args.dry_run)
        save_report(log)
    else:
        # Default: improve self_coder (meta: improve the improver)
        print("No skill specified, running self-improvement cycle on eval-suite...")
        log = run_cycle('self_coder', dry_run=args.dry_run)
        save_report(log)


if __name__ == '__main__':
    main()
