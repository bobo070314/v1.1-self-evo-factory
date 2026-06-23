#!/usr/bin/env python3
"""agent-testing — Multi-Framework Test Runner.
============================================
Auto-detects the test framework and runs the appropriate test command.
Supported frameworks: pytest, vitest, jest, cargo test, go test.

Usage:
  python run.py --path /project
  python run.py --framework pytest --path /project/src
  python run.py --json --path /project
"""

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

FRAMEWORK_DETECTION = {
    "pytest": ["pytest.ini", "pyproject.toml", "setup.cfg", "conftest.py"],
    "vitest": ["vitest.config.ts", "vitest.config.js", "vitest.config.mjs"],
    "jest": ["jest.config.ts", "jest.config.js", "jest.config.mjs", "jest.config.json"],
    "cargo": ["Cargo.toml"],
    "go": ["go.mod", "go.sum"],
}

FRAMEWORK_COMMANDS = {
    "pytest": ["pytest", "-v"],
    "vitest": ["npx", "vitest", "run"],
    "jest": ["npx", "jest"],
    "cargo": ["cargo", "test"],
    "go": ["go", "test", "./..."],
}

FRAMEWORK_JSON_FLAGS = {
    "pytest": ["--json-report", "--json-report-file=-"],
    "vitest": ["--reporter=json"],
    "jest": ["--json"],
    "cargo": [],
    "go": ["-json"],
}


def detect_framework(project_path):
    """Detect which test frameworks are available in the project."""
    path = Path(project_path).resolve()
    if not path.exists():
        return None, f"Path does not exist: {project_path}"

    if not path.is_dir():
        path = path.parent

    detected = []
    for framework, markers in FRAMEWORK_DETECTION.items():
        for marker in markers:
            if (path / marker).exists():
                detected.append(framework)
                break

    if not detected:
        # Fallback: check for test directories
        for test_dir in ["tests", "test", "__tests__", "spec"]:
            if (path / test_dir).is_dir():
                # Check file extensions to guess
                for ext, fw in [
                    (".py", "pytest"),
                    (".test.ts", "vitest"),
                    (".spec.ts", "vitest"),
                    (".test.js", "jest"),
                    (".spec.js", "jest"),
                ]:
                    test_path = path / test_dir
                    if list(test_path.glob(f"*{ext}")):
                        detected.append(fw)
                        break
                if detected:
                    break

    return detected, None


def run_tests(framework, project_path, json_output=False, extra_args=None):
    """Run tests using the specified framework."""
    cmd = list(FRAMEWORK_COMMANDS.get(framework, []))
    if not cmd:
        return {
            "success": False,
            "error": f"Unknown framework: {framework}",
            "framework": framework,
        }

    if json_output:
        json_flags = FRAMEWORK_JSON_FLAGS.get(framework, [])
        cmd.extend(json_flags)

    if extra_args:
        cmd.extend(extra_args)

    try:
        result = subprocess.run(
            cmd,
            cwd=str(project_path),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=300,
        )
        parsed = parse_test_output(framework, result.stdout, result.stderr, result.returncode)

        return {
            "success": result.returncode == 0,
            "framework": framework,
            "exit_code": result.returncode,
            "command": " ".join(cmd),
            "cwd": str(project_path),
            "stdout": result.stdout,
            "stderr": result.stderr,
            "parsed": parsed,
        }
    except FileNotFoundError:
        return {
            "success": False,
            "error": f"Command not found: {cmd[0]}. Is '{framework}' installed?",
            "framework": framework,
        }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "error": "Test run timed out (300s)",
            "framework": framework,
        }


def parse_test_output(framework, stdout, stderr, exit_code):
    """Parse test output to extract summary information."""
    parsed = {
        "total": None,
        "passed": None,
        "failed": None,
        "skipped": None,
        "duration_sec": None,
    }

    if framework == "pytest":
        # Try parsing pytest summary line: "== X passed, Y failed in Zs =="
        import re

        match = re.search(r"(\d+)\s+passed", stdout)
        if match:
            parsed["passed"] = int(match.group(1))
        match = re.search(r"(\d+)\s+failed", stdout)
        if match:
            parsed["failed"] = int(match.group(1))
        match = re.search(r"(\d+)\s+skipped", stdout)
        if match:
            parsed["skipped"] = int(match.group(1))
        match = re.search(r"in\s+([\d.]+)s", stdout)
        if match:
            parsed["duration_sec"] = float(match.group(1))
        if parsed["passed"] is not None and parsed["failed"] is not None:
            parsed["total"] = parsed["passed"] + parsed["failed"] + (parsed["skipped"] or 0)

    elif framework in ("vitest", "jest"):
        # Try parsing JSON output
        try:
            import re

            json_start = stdout.rfind("{")
            if json_start >= 0:
                data = json.loads(stdout[json_start:])
                parsed["total"] = data.get("numTotalTestSuites") or data.get("numTotalTests")
                parsed["passed"] = data.get("numPassedTests")
                parsed["failed"] = data.get("numFailedTests")
        except (json.JSONDecodeError, KeyError):
            pass

        if parsed["total"] is None:
            # Fallback to text summary
            import re

            match = re.search(r"Tests:\s+(\d+)\s+passed.*?(\d+)\s+failed.*?(\d+)\s+total", stdout, re.IGNORECASE)
            if match:
                parsed["passed"] = int(match.group(1))
                parsed["failed"] = int(match.group(2))
                parsed["total"] = int(match.group(3))

    elif framework == "go":
        # go test -json: count pass/fail events
        import re

        passed = 0
        failed = 0
        for line in stdout.splitlines():
            try:
                event = json.loads(line)
                if event.get("Action") == "pass":
                    passed += 1
                elif event.get("Action") == "fail":
                    failed += 1
            except json.JSONDecodeError:
                continue
        if passed or failed:
            parsed["passed"] = passed
            parsed["failed"] = failed
            parsed["total"] = passed + failed

    elif framework == "cargo":
        # cargo test summary: "test result: ok. X passed; Y failed; Z ignored"
        import re

        match = re.search(r"test result:.*?(\d+)\s+passed.*?(\d+)\s+failed.*?(\d+)\s+ignored", stdout)
        if match:
            parsed["passed"] = int(match.group(1))
            parsed["failed"] = int(match.group(2))
            parsed["skipped"] = int(match.group(3))
            parsed["total"] = parsed["passed"] + parsed["failed"] + parsed["skipped"]

    return parsed


def main():
    parser = argparse.ArgumentParser(
        prog="agent-testing",
        description="Multi-framework test runner (pytest/vitest/jest/cargo/go)",
    )
    parser.add_argument(
        "--path",
        default=".",
        help="Project root path (default: current directory)",
    )
    parser.add_argument(
        "--framework",
        choices=list(FRAMEWORK_COMMANDS.keys()),
        help="Force a specific framework (auto-detect if omitted)",
    )
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--dry-run", action="store_true", help="Show what would run without executing")
    args, unknown = parser.parse_known_args()

    project_path = Path(args.path).resolve()
    result = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "path": str(project_path),
        "dry_run": args.dry_run,
    }

    # Framework selection
    if args.framework:
        framework = args.framework
        result["detection"] = "user-specified"
    else:
        detected, error = detect_framework(project_path)
        if error:
            result.update({"success": False, "error": error})
            if args.json:
                print(json.dumps(result, indent=2, ensure_ascii=False))
            else:
                print(f"ERROR: {error}", file=sys.stderr)
            return 1
        if not detected:
            result.update(
                {
                    "success": False,
                    "error": "No supported test framework detected. Supported: pytest, vitest, jest, cargo, go",
                }
            )
            if args.json:
                print(json.dumps(result, indent=2, ensure_ascii=False))
            else:
                print(f"ERROR: No supported test framework detected in {project_path}", file=sys.stderr)
                print("Supported frameworks: pytest, vitest, jest, cargo test, go test")
            return 1
        framework = detected[0]
        result["detection"] = detected

    result["framework"] = framework

    if args.dry_run:
        cmd = list(FRAMEWORK_COMMANDS.get(framework, ["<unknown>"]))
        result["command"] = " ".join(cmd)
        result["success"] = True
        if args.json:
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            print(f"[DRY-RUN] Framework: {framework}")
            print(f"[DRY-RUN] Command: {' '.join(cmd)}")
            print(f"[DRY-RUN] CWD: {project_path}")
        return 0

    # Run tests
    run_result = run_tests(framework, project_path, json_output=args.json, extra_args=unknown)
    result.update(run_result)

    if args.json:
        # Truncate stdout/stderr for JSON output to keep it reasonable
        if "stdout" in result:
            result["stdout"] = result["stdout"][-5000:] if len(result["stdout"]) > 5000 else result["stdout"]
        if "stderr" in result:
            result["stderr"] = result["stderr"][-2000:] if len(result["stderr"]) > 2000 else result["stderr"]
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        if result.get("success"):
            parsed = result.get("parsed", {})
            print(f"SUCCESS: {framework} tests passed")
            if parsed.get("total") is not None:
                print(
                    f"  Total: {parsed['total']}, Passed: {parsed.get('passed', '?')}, "
                    f"Failed: {parsed.get('failed', 0)}, Skipped: {parsed.get('skipped', 0)}"
                )
                if parsed.get("duration_sec"):
                    print(f"  Duration: {parsed['duration_sec']:.2f}s")
        else:
            if "error" in result:
                print(f"ERROR: {result['error']}", file=sys.stderr)
            else:
                print(f"FAILED: {framework} tests returned exit code {result.get('exit_code', '?')}", file=sys.stderr)
                if result.get("stderr"):
                    print(result["stderr"][:1000], file=sys.stderr)

    return 0 if result.get("success") else 1


if __name__ == "__main__":
    sys.exit(main())
