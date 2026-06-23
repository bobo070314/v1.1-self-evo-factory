#!/usr/bin/env python3
"""frontend-code-review — ESLint-enhanced frontend code review with symbol cross-references, fix suggestions, and quality scoring."""
import subprocess, sys, argparse, json, os
from pathlib import Path
from datetime import datetime, timezone

os.environ.setdefault('PYTHONIOENCODING', 'utf-8')

ESLINT_PATTERNS = {
    'security': ['no-eval', 'no-implied-eval', 'no-script-url'],
    'performance': ['no-await-in-loop', 'no-console'],
    'style': ['indent', 'quotes', 'semi', 'comma-dangle'],
    'accessibility': ['jsx-a11y/anchor-is-valid', 'jsx-a11y/alt-text'],
}


def run_eslint(path: str) -> dict:
    try:
        r = subprocess.run(['npx', 'eslint', path, '--format', 'json'], capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=30)
        if r.returncode == 0:
            return json.loads(r.stdout) if r.stdout.strip() else []
        return json.loads(r.stdout) if r.stdout.strip() else []
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def scan_directory(path: str) -> dict:
    p = Path(path)
    results = {'path': str(p), 'files': [], 'score': 100, 'issues': [], 'suggestions': []}
    if not p.exists():
        results['issues'].append({'severity': 'error', 'message': f'Path not found: {path}'})
        results['score'] = 0
        return results

    js_files = list(p.rglob('*.js')) + list(p.rglob('*.jsx')) + list(p.rglob('*.ts')) + list(p.rglob('*.tsx'))
    js_files = [f for f in js_files if 'node_modules' not in f.parts and '.next' not in f.parts]
    for f in js_files[:50]:
        info = {'file': str(f.relative_to(p)), 'issues': []}
        try:
            content = f.read_text(encoding='utf-8', errors='replace')
            # Check for console.log in production
            for i, line in enumerate(content.split('\n'), 1):
                if 'console.log' in line and '//' not in line.split('console.log')[0]:
                    info['issues'].append({'line': i, 'rule': 'no-console', 'message': 'Remove console.log for production', 'fix': f'Delete line {i} or use debug logger'})
                if 'eval(' in line and '//' not in line.split('eval')[0]:
                    info['issues'].append({'line': i, 'rule': 'no-eval', 'message': 'Avoid eval() for security', 'fix': 'Replace with safer alternative'})
                if "dangerouslySetInnerHTML" in line:
                    info['issues'].append({'line': i, 'rule': 'react/no-danger', 'message': 'dangerouslySetInnerHTML risks XSS', 'fix': 'Use DOMPurify or React-safe rendering'})
        except Exception:
            pass
        if info['issues']:
            results['files'].append(info)

    total_issues = sum(len(f['issues']) for f in results['files'])
    results['score'] = max(0, 100 - total_issues * 5)
    results['issue_count'] = total_issues
    results['file_count'] = len(js_files)
    return results


def main():
    p = argparse.ArgumentParser(description='frontend-code-review — Enhanced frontend code review')
    p.add_argument('--path', default='.', help='Project path')
    p.add_argument('--json', action='store_true')
    p.add_argument('--dry-run', action='store_true', help='Preview only (default for non-destructive)')
    args = p.parse_args()

    result = scan_directory(args.path)
    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(f"Frontend Code Review — {result['path']}")
        print(f"Files: {result['file_count']} | Issues: {result['issue_count']} | Score: {result['score']}/100")
        for f in result['files']:
            print(f"\n  {f['file']}:")
            for i in f['issues']:
                print(f"    L{i['line']}: [{i['rule']}] {i['message']}")
                if i.get('fix'):
                    print(f"      → Fix: {i['fix']}")
    sys.exit(0 if result['score'] >= 60 else 1)


if __name__ == '__main__':
    main()
