#!/usr/bin/env python3
"""
V1.6 — Bulk Inject 72 Stub Skills
===================================
Generates minimal viable stubs for extraDirs skills.
Each gets: SKILL.md (with YAML frontmatter) + _meta.json
Does NOT overwrite existing skills.
"""

import json
from pathlib import Path

SKILLS_ROOT = Path(r'D:\bobo\openclaw-foreign\workspace\skills')

# 72 stub skills (names from MEMORY.md extraDirs list)
STUB_NAMES = [
    "create-skill", "agent-testing", "db-migrations", "add-setting-env",
    "code-navigator", "frontend-code-review", "security-audit", "drizzle",
    "release-notes-generator", "deployment-automation", "create-pr",
    "infra-diagram-as-code", "notion-api", "linear-api", "wecom-cli",
    "slack-bot", "discord-bot", "telegram-bot", "email-notifier",
    "github-issue-tracker", "github-pr-reviewer", "github-release-publisher",
    "npm-publisher", "docker-image-builder", "k8s-deployer",
    "terraform-runner", "ansible-runner", "helm-chart-generator",
    "api-doc-generator", "openapi-validator", "graphql-schema-gen",
    "json-schema-validator", "yaml-linter", "markdown-linter",
    "spell-checker", "link-checker", "image-optimizer",
    "svg-optimizer", "css-minifier", "js-bundler",
    "webpack-config-gen", "vite-config-gen", "eslint-config-gen",
    "prettier-config-gen", "tsconfig-gen", "dockerfile-gen",
    "compose-file-gen", "nginx-config-gen", "env-file-gen",
    "readme-gen", "changelog-gen", "license-gen",
    "gitignore-gen", "editorconfig-gen", "ci-cd-pipeline-gen",
    "test-data-generator", "mock-server", "api-stub-generator",
    "database-seeder", "fixture-generator", "schema-diff",
    "data-migration-helper", "backup-script", "restore-script",
    "log-analyzer", "error-tracker", "performance-profiler",
    "memory-leak-detector", "bundle-analyzer", "dependency-auditor",
    "license-compliance-checker", "vulnerability-scanner",
]

SKILL_MD_TEMPLATE = """---
name: {name}
description: {desc}
version: 0.1.0
type: skill
status: stub
---

# {name}

Stub skill — implementation pending.

## Description
{desc}

## Status
- [ ] Implementation
- [ ] Tests
- [ ] Documentation
"""

META_TEMPLATE = {
    "name": "{name}",
    "version": "0.1.0",
    "status": "stub",
    "entry": "run.py",
    "note": "Auto-generated stub by V1.6 injector"
}

DESCRIPTIONS = {
    "create-skill": "Skill factory with context snapshot bootstrapping",
    "agent-testing": "Multi-framework test runner (pytest/vitest/jest/cargo/go)",
    "db-migrations": "Prisma migration scripts (cross-platform Python)",
    "add-setting-env": "Environment variable validator (.env vs .env.example)",
    "code-navigator": "Symbol-level code navigation (functions/classes/interfaces)",
    "frontend-code-review": "ESLint-enhanced review with symbol cross-references",
    "security-audit": "Static code security auditor (SQLi/XSS/secrets/command injection)",
    "drizzle": "drizzle-kit wrapper with --dry-run and --json support",
    "release-notes-generator": "Generate release notes from git history",
    "deployment-automation": "Deploy/rollback/health check automation",
    "create-pr": "Create GitHub pull requests with templates",
    "infra-diagram-as-code": "Generate infrastructure diagrams as Mermaid/JSON",
}

def inject_stubs():
    created = 0
    skipped = 0
    existing_skills = set(d.name for d in SKILLS_ROOT.iterdir() if d.is_dir())

    # Check which stubs are also live skills
    for name in STUB_NAMES:
        if name in existing_skills:
            print(f"  SKIP (exists): {name}")
            skipped += 1
            continue

        desc = DESCRIPTIONS.get(name, f"Stub skill: {name}")
        skill_dir = SKILLS_ROOT / name
        skill_dir.mkdir(parents=True, exist_ok=True)

        # SKILL.md
        (skill_dir / 'SKILL.md').write_text(
            SKILL_MD_TEMPLATE.format(name=name, desc=desc),
            encoding='utf-8'
        )

        # _meta.json
        meta = META_TEMPLATE.copy()
        meta['name'] = name
        (skill_dir / '_meta.json').write_text(
            json.dumps(meta, indent=2, ensure_ascii=False),
            encoding='utf-8'
        )

        print(f"  CREATED: {name}")
        created += 1

    return created, skipped


if __name__ == '__main__':
    print("V1.6 Bulk Stub Injector")
    print(f"Target dir: {SKILLS_ROOT}")
    print(f"Stub count: {len(STUB_NAMES)}")
    print()
    c, s = inject_stubs()
    print()
    print(f"Done: {c} created, {s} skipped (already exist)")
    print(f"Total skills dir now: {len(list(SKILLS_ROOT.iterdir()))}")
