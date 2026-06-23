"""V2.14 — setup_new_env.py
=========================
One-click environment setup for v1.1-self-evo-factory.
Handles Python deps, pre-commit, environment validation,
and runs full test suite (eval + deep + api validation).
"""

import os
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
os.environ.setdefault("PYTHONIOENCODING", "utf-8")


def run(cmd, description="", timeout=60):
    """Run a command and print status."""
    print(f"  ▶ {description or ' '.join(cmd)}")
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            cwd=str(PROJECT_ROOT),
        )
        if result.returncode == 0:
            print(f"    ✅ OK ({result.returncode})")
            return True, result.stdout
        else:
            print(f"    ⚠️ Exit {result.returncode}: {result.stderr[:200]}")
            return False, result.stderr
    except FileNotFoundError:
        print(f"    ❌ Command not found: {cmd[0]}")
        return False, f"{cmd[0]} not found"
    except Exception as e:
        print(f"    ❌ Error: {e}")
        return False, str(e)


def check_python():
    """Verify Python version."""
    print("\n[1/8] Checking Python version...")
    v = sys.version_info
    if v.major >= 3 and v.minor >= 11:
        print(f"  ✅ Python {v.major}.{v.minor}.{v.micro}")
        return True
    else:
        print(f"  ❌ Python {v.major}.{v.minor} — need 3.11+")
        return False


def check_git():
    """Verify Git."""
    print("\n[2/8] Checking Git...")
    ok, out = run(["git", "--version"], "Git version")
    return ok


def check_docker():
    """Verify Docker (optional)."""
    print("\n[3/8] Checking Docker (optional)...")
    ok, _ = run(["docker", "--version"], "Docker version")
    if not ok:
        print("    ℹ️ Docker not found — sandbox-executor will use native fallback")
    return True  # Optional


def install_ruff():
    """Install/upgrade ruff."""
    print("\n[4/8] Installing Python tools...")
    tools = ["ruff", "pre-commit"]
    for tool in tools:
        ok, _ = run(
            [sys.executable, "-m", "pip", "install", "--upgrade", tool],
            f"pip install {tool}",
        )
        if not ok:
            print(f"    ⚠️ {tool} install failed — manual install may be needed")
    return True


def verify_project():
    """Run basic project validation."""
    print("\n[5/8] Verifying project structure...")

    required_dirs = ["pipeline", "eval-suite", "scripts", "states", "logs", "docs"]
    for d in required_dirs:
        exists = (PROJECT_ROOT / d).exists()
        print(f"  {'✅' if exists else '❌'} {d}/ {'exists' if exists else 'MISSING'}")

    required_files = [
        "pipeline/planner.py",
        "pipeline/coordinator.py",
        "pipeline/validate_apis.py",
        "pipeline/self_coder.py",
        "pipeline/self_improve.py",
        "eval-suite/run_all.py",
        "eval-suite/test_deep_skills.py",
        "docs/V3_ROADMAP.md",
    ]
    for f in required_files:
        exists = (PROJECT_ROOT / f).exists()
        print(f"  {'✅' if exists else '❌'} {f} {'exists' if exists else 'MISSING'}")


def run_skill_validation():
    """Run skill --version check on all 148 skills."""
    print("\n[6/8] Validating 148 skills (--version)...")
    ok, out = run(
        [
            sys.executable,
            "-c",
            """
import subprocess, sys
from pathlib import Path
BASE = Path(r"D:/bobo/openclaw-foreign/skills")
total = 0; passed = 0
for d in sorted(BASE.iterdir()):
    if not d.is_dir() or d.name.startswith('.') or d.name == 'qclaw-shared': continue
    rp = d / 'run.py'
    if not rp.exists(): continue
    total += 1
    r = subprocess.run([sys.executable, str(rp), '--version'], capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=10)
    if r.returncode == 0 and 'live' in r.stdout: passed += 1
print(f'Skills: {passed}/{total}')
""",
        ],
        "148 skills --version check",
        timeout=300,
    )
    return ok


def run_deep_tests():
    """Run deep skill tests."""
    print("\n[7/8] Running deep skill tests...")
    test_script = PROJECT_ROOT / "eval-suite" / "test_deep_skills.py"
    if test_script.exists():
        ok, _ = run([sys.executable, str(test_script)], "eval-suite/test_deep_skills.py", timeout=120)
        return ok
    else:
        print("  ⚠️ test_deep_skills.py not found")
        return True


def run_api_validation():
    """Validate API skills."""
    print("\n[8/8] Validating API skills...")
    api_script = PROJECT_ROOT / "pipeline" / "validate_apis.py"
    if api_script.exists():
        ok, _ = run([sys.executable, str(api_script)], "pipeline/validate_apis.py", timeout=180)
        return ok
    else:
        print("  ⚠️ validate_apis.py not found")
        return True


def main():
    print("=" * 60)
    print("V2.14 — Full Environment Setup & Validation")
    print("=" * 60)

    checks = [
        ("Python 3.11+", check_python()),
        ("Git", check_git()),
        ("Docker", check_docker()),
        ("Python tools", install_ruff()),
        ("Project structure", verify_project()),
        ("Skill validation", run_skill_validation()),
        ("Deep tests", run_deep_tests()),
        ("API validation", run_api_validation()),
    ]

    print()
    print("=" * 60)
    print("Summary")
    print("=" * 60)
    for name, ok in checks:
        print(f"  {'✅' if ok else '❌'} {name}")

    failed = [name for name, ok in checks if not ok]
    if failed:
        print(f"\n⚠️ Setup complete with warnings: {', '.join(failed)}")
        return 1
    else:
        print("\n✅ Full setup complete — all 8 checks passed!")
        return 0


if __name__ == "__main__":
    sys.exit(main())
