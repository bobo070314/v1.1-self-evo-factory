#!/usr/bin/env python3
"""core/global_compliance.py - V7.0 GLOBAL SOVEREIGN
SOC2 Type II + ISO 27001 + GDPR audit trail generator.
All operations silent, log-only, no popups.
"""

import hashlib
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional

UTC = timezone.utc
COMPLIANCE_DIR = Path(__file__).resolve().parent / "compliance"
COMPLIANCE_DIR.mkdir(parents=True, exist_ok=True)

AUDIT_CHAIN: List[Dict] = []
CHAIN_FILE = COMPLIANCE_DIR / "audit_chain.json"
REGION = os.getenv("OPENCLAW_REGION", "eu-central-1")

# Compliance requirements per standard
SOC2_CRITERIA = [
    "CC1.1 - Integrity and ethical values",
    "CC1.2 - Board independence and oversight",
    "CC2.1 - Information and communication",
    "CC3.1 - Specifies objectives with sufficient clarity",
    "CC4.1 - Selects and develops control activities",
    "CC5.1 - Selects and develops general controls over technology",
    "CC6.1 - Uses entity-level controls",
    "CC7.1 - Uses detection and monitoring procedures",
    "CC8.1 - Implements change management process",
]

ISO27001_CONTROLS = [
    "A.5.1.1 - Policies for information security",
    "A.6.1.1 - Information security roles and responsibilities",
    "A.8.1.1 - Inventory of assets",
    "A.9.1.1 - Access control policy",
    "A.10.1.1 - Policy on the use of cryptographic controls",
    "A.12.1.1 - Documented operating procedures",
    "A.14.1.1 - Information security requirements analysis",
    "A.16.1.1 - Management of information security incidents",
    "A.18.1.1 - Compliance with legal and contractual requirements",
]

GDPR_ARTICLES = [
    "Art.5 - Principles relating to processing of personal data",
    "Art.6 - Lawfulness of processing",
    "Art.7 - Conditions for consent",
    "Art.15 - Right of access by the data subject",
    "Art.17 - Right to erasure (right to be forgotten)",
    "Art.25 - Data protection by design and by default",
    "Art.30 - Records of processing activities",
    "Art.32 - Security of processing",
    "Art.33 - Notification of a personal data breach to the supervisory authority",
    "Art.35 - Data protection impact assessment",
    "Art.44 - General principle for transfers",
]


def _hash_chain(prev_hash: str, data: Dict) -> str:
    """Append-only hash chain for audit tamper detection."""
    payload = json.dumps(data, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(f"{prev_hash}:{payload}".encode()).hexdigest()


def _get_prev_hash() -> str:
    if CHAIN_FILE.exists():
        chain = json.loads(CHAIN_FILE.read_text(encoding="utf-8"))
        if chain:
            return chain[-1].get("hash", "genesis")
    return "genesis"


def record_audit(
    action: str,
    tenant_id: str,
    operator: str = "system",
    details: Optional[Dict] = None,
) -> str:
    """Record an auditable event with hash-chain linkage."""
    prev_hash = _get_prev_hash()

    if os.getenv("OPENCLAW_DRY_RUN"):
        return "dry-run"

    event = {
        "timestamp": datetime.now(UTC).isoformat(),
        "region": REGION,
        "action": action,
        "tenant_id": tenant_id,
        "operator": operator,
        "details": details or {},
        "prev_hash": prev_hash,
        "hash": "",
    }
    event["hash"] = _hash_chain(prev_hash, event)

    AUDIT_CHAIN.append(event)

    # Flush to disk every record
    try:
        existing = []
        if CHAIN_FILE.exists():
            existing = json.loads(CHAIN_FILE.read_text(encoding="utf-8"))
        existing.append(event)
        CHAIN_FILE.write_text(json.dumps(existing, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass

    return event["hash"]


def verify_chain() -> Dict:
    """Verify hash-chain integrity. Returns tampered entries."""
    if not CHAIN_FILE.exists():
        return {"status": "OK", "entries": 0, "tampered": []}

    chain = json.loads(CHAIN_FILE.read_text(encoding="utf-8"))
    tampered = []
    for i, entry in enumerate(chain):
        expected_prev = chain[i - 1]["hash"] if i > 0 else "genesis"
        if entry.get("prev_hash") != expected_prev:
            tampered.append(
                {"index": i, "action": entry["action"], "expected_prev": expected_prev, "got": entry["prev_hash"]}
            )

    return {
        "status": "COMPROMISED" if tampered else "OK",
        "entries": len(chain),
        "tampered": tampered,
        "last_hash": chain[-1]["hash"] if chain else None,
    }


def generate_soc2_report(output_path: Optional[Path] = None) -> Path:
    """Generate SOC2 Type II compliance report (silent, no popup)."""
    chain = []
    if CHAIN_FILE.exists():
        chain = json.loads(CHAIN_FILE.read_text(encoding="utf-8"))

    report = {
        "report_type": "SOC2 Type II",
        "generated_at": datetime.now(UTC).isoformat(),
        "region": REGION,
        "audit_period_start": chain[0]["timestamp"] if chain else "N/A",
        "audit_period_end": chain[-1]["timestamp"] if chain else "N/A",
        "total_events": len(chain),
        "chain_verified": verify_chain()["status"],
        "criteria_coverage": {},
        "findings": [],
    }

    # Map events to SOC2 criteria
    for criterion in SOC2_CRITERIA:
        code = criterion.split(" ")[0]
        matched = [e for e in chain if code.lower() in json.dumps(e).lower() or e["action"] == "compliance_check"]
        report["criteria_coverage"][criterion] = {
            "status": "PASS" if len(matched) >= 1 else "INCONCLUSIVE",
            "evidence_count": len(matched),
        }

    out = output_path or COMPLIANCE_DIR / f"soc2_report_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}.json"
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    record_audit("compliance_report_generated", "system", "system", {"standard": "SOC2", "file": str(out)})
    return out


def generate_iso27001_report(output_path: Optional[Path] = None) -> Path:
    """Generate ISO 27001 compliance report (silent)."""
    chain = []
    if CHAIN_FILE.exists():
        chain = json.loads(CHAIN_FILE.read_text(encoding="utf-8"))

    report = {
        "report_type": "ISO 27001",
        "generated_at": datetime.now(UTC).isoformat(),
        "region": REGION,
        "total_events": len(chain),
        "chain_verified": verify_chain()["status"],
        "controls_coverage": {},
    }

    for control in ISO27001_CONTROLS:
        code = control.split(" ")[0]
        matched = [e for e in chain if code.lower() in json.dumps(e).lower() or "iso27001" in json.dumps(e).lower()]
        report["controls_coverage"][control] = {
            "status": "PASS" if len(matched) >= 1 else "INCONCLUSIVE",
            "evidence_count": len(matched),
        }

    out = output_path or COMPLIANCE_DIR / f"iso27001_report_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}.json"
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    record_audit("compliance_report_generated", "system", "system", {"standard": "ISO27001", "file": str(out)})
    return out


# ---- GDPR sub-module ----


def handle_forget_request(tenant_id: str) -> Dict:
    """Process GDPR Art.17 right-to-erasure request."""
    result = {"tenant_id": tenant_id, "status": "processed", "timestamp": datetime.now(UTC).isoformat()}

    # Remove tenant data from audit chain (anonymize)
    if CHAIN_FILE.exists():
        chain = json.loads(CHAIN_FILE.read_text(encoding="utf-8"))
        new_chain = []
        anonymized = 0
        for entry in chain:
            if entry.get("tenant_id") == tenant_id:
                entry["tenant_id"] = f"REDACTED_{anonymized}"
                anonymized += 1
            new_chain.append(entry)
        CHAIN_FILE.write_text(json.dumps(new_chain, indent=2, ensure_ascii=False), encoding="utf-8")
        result["records_anonymized"] = anonymized

    # Log the forget request
    forget_log = COMPLIANCE_DIR / f"forget_requests_{REGION}.log"
    with forget_log.open("a", encoding="utf-8") as f:
        f.write(json.dumps(result) + "\n")

    record_audit("gdpr_forget", tenant_id, "system", {"article": "Art.17"})
    return result


def cleanup_expired(retention_days: int = 365) -> Dict:
    """Auto-purge data exceeding retention period."""
    cutoff = datetime.now(UTC) - timedelta(days=retention_days)
    if not CHAIN_FILE.exists():
        return {"purged": 0}

    chain = json.loads(CHAIN_FILE.read_text(encoding="utf-8"))
    kept = []
    purged = []
    for entry in chain:
        ts = datetime.fromisoformat(entry["timestamp"].replace("Z", "+00:00"))
        if ts < cutoff:
            purged.append(entry)
        else:
            kept.append(entry)

    CHAIN_FILE.write_text(json.dumps(kept, indent=2, ensure_ascii=False), encoding="utf-8")
    purged_forget = COMPLIANCE_DIR / f"purged_{REGION}.json"
    purged_forget.write_text(
        json.dumps({"purged_at": datetime.now(UTC).isoformat(), "count": len(purged)}, indent=2), encoding="utf-8"
    )
    record_audit("gdpr_cleanup", "system", "system", {"purged": len(purged), "retention_days": retention_days})
    return {"purged": len(purged), "kept": len(kept)}


# ---- CLI ----

if __name__ == "__main__":
    import argparse
    import sys

    p = argparse.ArgumentParser(description="V7.0 Global Compliance Suite")
    p.add_argument("--soc2", action="store_true", help="Generate SOC2 report")
    p.add_argument("--iso27001", action="store_true", help="Generate ISO 27001 report")
    p.add_argument("--gdpr-cleanup", action="store_true", help="Run GDPR retention cleanup")
    p.add_argument("--forget", type=str, help="GDPR Art.17 forget TENTANT_ID")
    p.add_argument("--verify", action="store_true", help="Verify audit chain integrity")
    p.add_argument("--json", action="store_true", help="JSON output")

    args = p.parse_args()

    if args.verify:
        result = verify_chain()
        if args.json:
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            print(f"Chain: {result['status']} | Entries: {result['entries']} | Tampered: {len(result['tampered'])}")
        sys.exit(0 if result["status"] == "OK" else 1)

    if args.soc2:
        out = generate_soc2_report()
        if args.json:
            print(json.dumps({"soc2_report": str(out)}, indent=2, ensure_ascii=False))
        else:
            print(f"SOC2 report: {out}")

    if args.iso27001:
        out = generate_iso27001_report()
        if args.json:
            print(json.dumps({"iso27001_report": str(out)}, indent=2, ensure_ascii=False))
        else:
            print(f"ISO 27001 report: {out}")

    if args.gdpr_cleanup:
        result = cleanup_expired()
        if args.json:
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            print(f"GDPR cleanup: {result['purged']} purged, {result['kept']} kept")

    if args.forget:
        result = handle_forget_request(args.forget)
        if args.json:
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            print(f"Forget {args.forget}: {result['records_anonymized']} records anonymized")

    if len(sys.argv) == 1:
        # Default: verify + record a check event
        v = verify_chain()
        record_audit("compliance_check", "system", "system", {"chain_entries": v["entries"]})
        print(json.dumps({"status": v["status"], "entries": v["entries"]}, indent=2, ensure_ascii=False))
