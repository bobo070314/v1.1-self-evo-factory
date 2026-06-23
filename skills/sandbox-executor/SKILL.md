---
name: sandbox-executor
description: Docker-isolated command runner with security constraints
version: 1.0.0
type: skill
status: live
---

# sandbox-executor

Runs commands in a read-only Docker container with:
- read-only root filesystem
- no new privileges
- dropped ALL capabilities
- network disabled by default
- 256MB memory limit

Falls back to native execution if Docker unavailable.
