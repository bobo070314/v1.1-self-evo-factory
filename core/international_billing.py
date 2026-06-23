#!/usr/bin/env python3
"""core/international_billing.py - V7.0 GLOBAL SOVEREIGN
Multi-currency billing, Stripe integration, tax auto-calculation.
All operations silent, no popups, dry-run safe.
"""

import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

UTC = timezone.utc
BILLING_DIR = Path(__file__).resolve().parent / "compliance"
BILLING_DIR.mkdir(parents=True, exist_ok=True)
LEDGER_FILE = BILLING_DIR / "billing_ledger.json"
REGION = os.getenv("OPENCLAW_REGION", "eu-central-1")

# Regional configuration
REGION_CONFIG = {
    "eu-central-1": {"currency": "EUR", "tax_rate": 0.19, "tax_name": "VAT", "locale": "de-DE"},
    "us-east-1": {"currency": "USD", "tax_rate": 0.08, "tax_name": "Sales Tax", "locale": "en-US"},
    "us-west-2": {"currency": "USD", "tax_rate": 0.00, "tax_name": "Sales Tax", "locale": "en-US"},
    "ap-southeast-1": {"currency": "SGD", "tax_rate": 0.09, "tax_name": "GST", "locale": "en-SG"},
    "ap-northeast-1": {"currency": "JPY", "tax_rate": 0.10, "tax_name": "Consumption Tax", "locale": "ja-JP"},
    "eu-west-2": {"currency": "GBP", "tax_rate": 0.20, "tax_name": "VAT", "locale": "en-GB"},
}

# DeepSeek international pricing (USD per 1M tokens)
PRICING = {
    "deepseek-v4-pro": {"prompt": 1.00, "completion": 2.00},
    "deepseek-v4-flash": {"prompt": 0.50, "completion": 1.00},
    "default": {"prompt": 1.00, "completion": 2.00},
}

# Exchange rates (simplified - production should call exchangerate-api.com)
EXCHANGE_RATES = {
    "USD_EUR": 0.92,
    "USD_GBP": 0.79,
    "USD_SGD": 1.35,
    "USD_JPY": 155.0,
    "USD_CNY": 7.25,
    "EUR_USD": 1.09,
}

STRIPE_API_KEY = os.getenv("STRIPE_API_KEY", "")
STRIPE_ENABLED = bool(STRIPE_API_KEY and STRIPE_API_KEY != "")

if STRIPE_ENABLED:
    try:
        import stripe

        stripe.api_key = STRIPE_API_KEY
    except ImportError:
        STRIPE_ENABLED = False


def _load_ledger() -> List[Dict]:
    if LEDGER_FILE.exists():
        return json.loads(LEDGER_FILE.read_text(encoding="utf-8"))
    return []


def _save_ledger(ledger: List[Dict]) -> None:
    LEDGER_FILE.write_text(json.dumps(ledger, indent=2, ensure_ascii=False), encoding="utf-8")


def _get_region_config() -> Dict:
    return REGION_CONFIG.get(REGION, REGION_CONFIG["us-east-1"])


def _get_exchange_rate(from_curr: str, to_curr: str) -> float:
    if from_curr == to_curr:
        return 1.0
    key = f"{from_curr}_{to_curr}"
    # Reciprocal lookup
    if key not in EXCHANGE_RATES:
        rev = f"{to_curr}_{from_curr}"
        if rev in EXCHANGE_RATES:
            return 1.0 / EXCHANGE_RATES[rev]
        return 1.0
    return EXCHANGE_RATES[key]


def calculate_cost(
    model: str = "default",
    prompt_tokens: int = 0,
    completion_tokens: int = 0,
) -> Dict[str, Any]:
    """Calculate cost in both USD and local currency, with tax."""
    pricing = PRICING.get(model, PRICING["default"])
    region_cfg = _get_region_config()

    # USD cost
    usd_prompt_cost = (prompt_tokens / 1_000_000) * pricing["prompt"]
    usd_completion_cost = (completion_tokens / 1_000_000) * pricing["completion"]
    usd_cost = usd_prompt_cost + usd_completion_cost

    # Local currency
    local_currency = region_cfg["currency"]
    rate = _get_exchange_rate("USD", local_currency)
    local_pre_tax = usd_cost * rate

    # Tax
    tax_rate = region_cfg["tax_rate"]
    tax_amount = local_pre_tax * tax_rate
    total_local = local_pre_tax + tax_amount

    return {
        "model": model,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "usd_cost": round(usd_cost, 6),
        "local_currency": local_currency,
        "local_pre_tax": round(local_pre_tax, 4),
        f"{region_cfg['tax_name']}_rate": tax_rate,
        "tax_amount": round(tax_amount, 4),
        "total_local": round(total_local, 4),
        "exchange_rate": rate,
        "region": REGION,
    }


def record_usage(
    tenant_id: str,
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
    operation: str = "chat_completion",
) -> Dict:
    """Record a billing event to the ledger."""
    cost = calculate_cost(model, prompt_tokens, completion_tokens)
    entry = {
        "timestamp": datetime.now(UTC).isoformat(),
        "tenant_id": tenant_id,
        "region": REGION,
        "model": model,
        "operation": operation,
        **cost,
    }

    if os.getenv("OPENCLAW_DRY_RUN"):
        return entry

    ledger = _load_ledger()
    ledger.append(entry)
    _save_ledger(ledger)
    return entry


def get_tenant_usage(tenant_id: str, since_days: int = 30) -> Dict:
    """Get usage summary for a tenant."""
    ledger = _load_ledger()
    cutoff = datetime.now(UTC) - timedelta(days=since_days)
    region_cfg = _get_region_config()

    tenant_entries = []
    for e in ledger:
        if e.get("tenant_id") == tenant_id:
            ts = datetime.fromisoformat(e["timestamp"].replace("Z", "+00:00"))
            if ts >= cutoff:
                tenant_entries.append(e)

    total_usd = sum(e.get("usd_cost", 0) for e in tenant_entries)
    total_local = sum(e.get("total_local", 0) for e in tenant_entries)
    total_tokens = sum(e.get("prompt_tokens", 0) + e.get("completion_tokens", 0) for e in tenant_entries)

    return {
        "tenant_id": tenant_id,
        "period_days": since_days,
        "operations": len(tenant_entries),
        "total_tokens": total_tokens,
        "total_usd": round(total_usd, 6),
        "total_local": round(total_local, 4),
        "currency": region_cfg["currency"],
    }


def create_invoice(
    tenant_id: str,
    period_days: int = 30,
    customer_email: Optional[str] = None,
) -> Dict:
    """Generate invoice (Stripe if available, local JSON always)."""
    usage = get_tenant_usage(tenant_id, period_days)
    region_cfg = _get_region_config()

    invoice = {
        "invoice_id": f"INV-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}-{tenant_id[:8]}",
        "tenant_id": tenant_id,
        "period_days": period_days,
        "generated_at": datetime.now(UTC).isoformat(),
        "region": REGION,
        "currency": region_cfg["currency"],
        "subtotal": round(usage["total_local"], 4),
        "tax_rate": region_cfg["tax_rate"],
        "tax_name": region_cfg["tax_name"],
        "total": round(usage["total_local"], 4),
        "items": [
            {
                "description": f"OpenClaw AI Usage ({usage['operations']} calls, {usage['total_tokens']} tokens)",
                "amount": round(usage["total_local"], 4),
            }
        ],
    }

    # Stripe integration
    if STRIPE_ENABLED and customer_email:
        try:
            # Create or find customer
            customers = stripe.Customer.list(email=customer_email, limit=1)
            if customers.data:
                stripe_customer = customers.data[0]
            else:
                stripe_customer = stripe.Customer.create(email=customer_email, metadata={"tenant_id": tenant_id})

            # Create invoice
            stripe_invoice = stripe.Invoice.create(
                customer=stripe_customer.id,
                currency=region_cfg["currency"].lower(),
                metadata={"tenant_id": tenant_id, "region": REGION},
                auto_advance=False,
            )

            # Add items
            stripe.InvoiceItem.create(
                customer=stripe_customer.id,
                amount=int(usage["total_local"] * 100),  # Stripe uses cents
                currency=region_cfg["currency"].lower(),
                description=f"OpenClaw AI Usage - {period_days} days",
            )

            stripe_invoice.finalize_invoice()
            invoice["stripe_invoice_id"] = stripe_invoice.id
            invoice["stripe_hosted_url"] = stripe_invoice.hosted_invoice_url
            invoice["stripe_status"] = stripe_invoice.status
        except Exception as e:
            invoice["stripe_error"] = str(e)

    # Save local copy
    invoice_file = BILLING_DIR / f"invoice_{invoice['invoice_id']}.json"
    invoice_file.write_text(json.dumps(invoice, indent=2, ensure_ascii=False), encoding="utf-8")

    return invoice


def check_tenant_balance(tenant_id: str, threshold_usd: float = 10.0) -> Dict:
    """Check if tenant is approaching balance threshold."""
    usage = get_tenant_usage(tenant_id, since_days=30)
    status = "OK"
    if usage["total_usd"] > threshold_usd * 2:
        status = "OVERDUE"
    elif usage["total_usd"] > threshold_usd:
        status = "THRESHOLD"
    return {"tenant_id": tenant_id, "threshold_usd": threshold_usd, "current_usd": usage["total_usd"], "status": status}


# ---- CLI ----

if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser(description="V7.0 International Billing")
    p.add_argument("--calculate", action="store_true", help="Calculate sample cost")
    p.add_argument("--record", type=str, help="Record usage: TENANT_ID")
    p.add_argument("--tokens", type=int, default=1000, help="Tokens for --calculate/--record")
    p.add_argument("--usage", type=str, help="Get tenant usage: TENANT_ID")
    p.add_argument("--invoice", type=str, help="Create invoice: TENANT_ID")
    p.add_argument("--email", type=str, help="Customer email for Stripe invoice")
    p.add_argument("--balance", type=str, help="Check tenant balance: TENANT_ID")
    p.add_argument("--json", action="store_true", help="JSON output")

    args = p.parse_args()

    if args.calculate:
        result = calculate_cost(prompt_tokens=args.tokens)
        if args.json:
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            print(
                f"Cost: {result['usd_cost']} USD / {result['total_local']} {result['local_currency']} (incl. {result.get(g[0], '')}% tax)"
            )

    if args.record:
        result = record_usage(args.record, "deepseek-v4-pro", args.tokens, args.tokens // 2)
        if args.json:
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            print(f"Recorded: {args.record} - {result['usd_cost']} USD")

    if args.usage:
        result = get_tenant_usage(args.usage)
        if args.json:
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            print(
                f"Tenant {args.usage}: {result['operations']} ops, {result['total_usd']} USD ({result['total_local']} {result['currency']})"
            )

    if args.invoice:
        result = create_invoice(args.invoice, customer_email=args.email)
        if args.json:
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            print(f"Invoice {result['invoice_id']}: {result['total']} {result['currency']}")
            if "stripe_invoice_id" in result:
                print(f"Stripe: {result['stripe_invoice_id']} - {result.get('stripe_status', 'unknown')}")

    if args.balance:
        result = check_tenant_balance(args.balance)
        if args.json:
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            print(
                f"Tenant {args.balance}: {result['current_usd']} USD / threshold {args.threshold_usd} USD -> {result['status']}"
            )
