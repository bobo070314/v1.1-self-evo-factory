#!/usr/bin/env python3.
"""V4.0 Enterprise Governance — RBAC + Audit Chain.

Usage:
  python auth.py init                    # init admin user
  python auth.py add-user <id> <role>   # add user
  python auth.py check <id> <action>    # check permission
  python auth.py audit [--limit 50]    # view audit log
  python auth.py --version
"""

import argparse
import hashlib
import json
import os
import time
from pathlib import Path

__version__ = "4.0.0"

# ── Roles ──────────────────────────────────────────
ROLES = {
    "admin": {"permissions": ["*"], "desc": "Full system access"},
    "developer": {
        "permissions": ["deploy:staging", "audit:read", "code:review", "create:pr", "git:push", "skills:run"],
        "desc": "Standard developer",
    },
    "viewer": {"permissions": ["audit:read", "docs:read", "skills:list"], "desc": "Read-only access"},
    "auditor": {"permissions": ["audit:*", "logs:read", "config:read"], "desc": "Audit and compliance"},
    "operator": {"permissions": ["deploy:*", "monitor:*", "skills:run", "audit:read"], "desc": "Production operator"},
}

AUDIT_DIR = Path.home() / ".openclaw"
AUDIT_FILE = AUDIT_DIR / "audit.jsonl"
USERS_FILE = AUDIT_DIR / "users.json"


# ── User store ─────────────────────────────────────
def load_users() -> dict:
    if USERS_FILE.exists():
        try:
            with open(USERS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def save_users(users: dict):
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    tmp = USERS_FILE.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(users, f, indent=2)
    tmp.replace(USERS_FILE)


# ── Permission check ───────────────────────────────
def can(user_id: str, action: str) -> bool:
    users = load_users()
    if user_id not in users:
        return False
    role = users[user_id].get("role", "viewer")
    if role == "admin":
        return True
    perms = ROLES.get(role, {}).get("permissions", [])
    for perm in perms:
        if perm == "*":
            return True
        if perm.endswith(":*"):
            if action.startswith(perm.replace(":*", ":")):
                return True
        if perm == action:
            return True
    return False


# ── Audit log ──────────────────────────────────────
def audit_log(user_id: str, action: str, result: str, details: dict | None = None):
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    entry = {
        "timestamp": time.time(),
        "ts_human": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime()),
        "user": user_id,
        "action": action,
        "result": result,
        "details": details or {},
        "prev_hash": "",
    }

    # Simple hash-chain for tamper evidence
    try:
        with open(AUDIT_FILE, "rb") as f:
            f.seek(0, os.SEEK_END)
            size = f.tell()
            if size > 0:
                f.seek(max(0, size - 4096))
                tail = f.read()
                entry["prev_hash"] = hashlib.sha256(tail).hexdigest()[:16]
    except OSError:
        pass

    with open(AUDIT_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def get_audit_log(limit: int = 50) -> list[dict]:
    if not AUDIT_FILE.exists():
        return []
    entries = []
    with open(AUDIT_FILE, "r", encoding="utf-8") as f:
        lines = f.readlines()
        for line in lines[-limit:]:
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return entries


# ── Multi-tenancy (simple) ─────────────────────────
def get_tenant(user_id: str) -> str:
    """Resolve tenant ID for multi-tenant isolation."""
    users = load_users()
    return users.get(user_id, {}).get("tenant", "default")


# ── CLI ────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="V4.0 RBAC + Audit Chain")
    sub = parser.add_subparsers(dest="cmd")

    sub.add_parser("init", help="Initialize default admin user")

    add = sub.add_parser("add-user", help="Add a user")
    add.add_argument("user_id")
    add.add_argument("role", choices=list(ROLES.keys()))
    add.add_argument("--tenant", default="default")

    check = sub.add_parser("check", help="Check permission")
    check.add_argument("user_id")
    check.add_argument("action")

    audit_cmd = sub.add_parser("audit", help="View audit log")
    audit_cmd.add_argument("--limit", type=int, default=50)

    parser.add_argument("--version", action="store_true")

    args = parser.parse_args()

    if args.version:
        print(__version__)
        return

    if args.cmd == "init":
        users = load_users()
        if "admin" not in users:
            users["admin"] = {
                "user_id": "admin",
                "role": "admin",
                "tenant": "default",
                "created": time.strftime("%Y-%m-%d"),
            }
            save_users(users)
            print("✅ Admin user initialized")
            audit_log("system", "init", "ok", {"created": "admin"})
        else:
            print("ℹ️  Admin already exists")
        # Show all roles
        print("\n📋 Available roles:")
        for name, cfg in ROLES.items():
            print(f"  {name}: {cfg['desc']} ({len(cfg['permissions'])} permissions)")

    elif args.cmd == "add-user":
        users = load_users()
        users[args.user_id] = {
            "user_id": args.user_id,
            "role": args.role,
            "tenant": args.tenant,
            "created": time.strftime("%Y-%m-%d"),
        }
        save_users(users)
        print(f"✅ User {args.user_id} added with role {args.role}")
        audit_log("admin", "add-user", "ok", {"target": args.user_id, "role": args.role})

    elif args.cmd == "check":
        ok = can(args.user_id, args.action)
        print(f"{'✅ ALLOW' if ok else '❌ DENY'}: {args.user_id} → {args.action}")
        audit_log(args.user_id, args.action, "allowed" if ok else "denied", {})

    elif args.cmd == "audit":
        entries = get_audit_log(args.limit)
        print(f"\n📋 Audit Log ({len(entries)} entries):\n")
        for e in entries:
            ts = e.get("ts_human", "?")
            user = e["user"]
            action = e["action"]
            result = e["result"]
            emoji = "✅" if result == "ok" or result == "allowed" else "❌" if result == "denied" else "📝"
            print(f"  {ts} {emoji} [{user}] {action} → {result}")
        if entries:
            last_hash = entries[-1].get("prev_hash", "N/A")
            print(f"\n🔗 Chain head: {last_hash}")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
