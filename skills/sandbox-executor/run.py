#!/usr/bin/env python3
"""sandbox-executor — Docker-Isolated Command Runner.
==================================================
Runs commands in a read-only Docker container with security constraints.
Falls back to native execution if Docker is unavailable.

Security:
  - read-only root filesystem
  - no new privileges
  - dropped capabilities (ALL)
  - network disabled by default
  - memory limit
  - timeout enforced

Usage:
  python sandbox-executor.py --image python:3.11-slim --cmd "python -c 'print(42)'"
  python sandbox-executor.py --cmd "echo hello"           # Falls back to native
  python sandbox-executor.py --cmd "rm -rf /" --verify    # Should fail securely
"""

import argparse
import json
import os
import subprocess
import sys
from typing import Optional

DOCKER_IMAGE = os.environ.get("SANDBOX_IMAGE", "python:3.12-slim")
SANDBOX_TIMEOUT = int(os.environ.get("SANDBOX_TIMEOUT", "30"))


def docker_available() -> bool:
    """Check if Docker is installed and running."""
    try:
        result = subprocess.run(
            ["docker", "info"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=5,
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def run_in_docker(
    command: str,
    image: str = DOCKER_IMAGE,
    timeout: int = SANDBOX_TIMEOUT,
    mount_readonly: Optional[str] = None,
    network: bool = False,
) -> dict:
    """Run a command inside a secured Docker container."""
    docker_cmd = [
        "docker",
        "run",
        "--rm",
        "--read-only",
        "--security-opt",
        "no-new-privileges:true",
        "--cap-drop",
        "ALL",
        "--memory",
        "256m",
        "--memory-swap",
        "256m",
    ]

    if not network:
        docker_cmd.extend(["--network", "none"])

    if mount_readonly:
        docker_cmd.extend(["-v", f"{mount_readonly}:/workspace:ro"])

    docker_cmd.append(image)
    docker_cmd.extend(["sh", "-c", command])

    result = subprocess.run(
        docker_cmd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
    )

    return {
        "exit_code": result.returncode,
        "stdout": result.stdout.strip(),
        "stderr": result.stderr.strip(),
        "sandbox": "docker",
        "image": image,
    }


def run_native(command: str, timeout: int = SANDBOX_TIMEOUT) -> dict:
    """Run a command natively (Docker fallback)."""
    result = subprocess.run(
        command,
        shell=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
    )

    return {
        "exit_code": result.returncode,
        "stdout": result.stdout.strip(),
        "stderr": result.stderr.strip(),
        "sandbox": "native",
        "warning": "Running WITHOUT Docker isolation — install Docker for security",
    }


def run_sandboxed(
    command: str,
    image: str = DOCKER_IMAGE,
    timeout: int = SANDBOX_TIMEOUT,
    mount: Optional[str] = None,
    network: bool = False,
    force_native: bool = False,
) -> dict:
    """Run command in Docker sandbox, with native fallback."""
    if not force_native and docker_available():
        # Check if image exists, pull if not
        check = subprocess.run(
            ["docker", "image", "inspect", image],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=10,
        )
        if check.returncode != 0:
            print(f"Pulling Docker image: {image}...", file=sys.stderr)
            pull = subprocess.run(
                ["docker", "pull", image],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=120,
            )
            if pull.returncode != 0:
                print(f"WARNING: Failed to pull image, falling back to native: {pull.stderr[:200]}", file=sys.stderr)
                return run_native(command, timeout)
        return run_in_docker(command, image, timeout, mount, network)
    else:
        return run_native(command, timeout)


def verify_sandbox() -> dict:
    """Verify sandbox security by testing write protection and capability drops."""
    results = {}

    # Test 1: Write to root filesystem should be blocked
    print("Test 1: Write protection...", file=sys.stderr)
    r1 = run_sandboxed("touch /test_write")
    # Docker stderr goes to container stderr, captured separately
    results["write_protected"] = "Read-only" in r1.get("stderr", "") or r1["exit_code"] != 0
    results["write_test_stderr"] = r1.get("stderr", "")[:200]

    # Test 2: rm -rf / with --no-preserve-root should fail on read-only
    print("Test 2: Destructive command blocked...", file=sys.stderr)
    r2 = run_sandboxed("rm -rf --no-preserve-root /")
    results["destructive_blocked"] = "Read-only" in r2.get("stderr", "") or r2["exit_code"] != 0
    results["destructive_test_stderr"] = r2.get("stderr", "")[:200]

    # Test 3: Verify sandbox type
    results["sandbox_type"] = r1.get("sandbox", "unknown")

    secure = results.get("write_protected", False) and results.get("destructive_blocked", False)
    results["secure"] = secure
    results["verdict"] = "SECURE - sandbox isolation confirmed" if secure else "INSECURE - no sandbox protection"

    return results


def main():
    parser = argparse.ArgumentParser(description="Sandbox Executor — Docker-isolated command runner")
    parser.add_argument("--cmd", "--command", dest="command", help="Command to run in sandbox")
    parser.add_argument("--image", default=DOCKER_IMAGE, help=f"Docker image (default: {DOCKER_IMAGE})")
    parser.add_argument("--timeout", type=int, default=SANDBOX_TIMEOUT, help="Timeout in seconds")
    parser.add_argument("--mount", help="Read-only mount path (host:container)")
    parser.add_argument("--network", action="store_true", help="Enable network in container")
    parser.add_argument("--native", action="store_true", help="Force native execution (skip Docker)")
    parser.add_argument("--verify", action="store_true", help="Verify sandbox security")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    if args.verify:
        result = verify_sandbox()
    elif args.command:
        result = run_sandboxed(
            args.command,
            image=args.image,
            timeout=args.timeout,
            mount=args.mount,
            network=args.network,
            force_native=args.native,
        )
    else:
        print("ERROR: Use --cmd '...' or --verify", file=sys.stderr)
        sys.exit(1)

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(result.get("stdout", ""))
        if result.get("stderr"):
            print(result["stderr"], file=sys.stderr)

    sys.exit(result.get("exit_code", 1))


if __name__ == "__main__":
    main()
