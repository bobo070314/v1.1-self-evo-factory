#!/usr/bin/env python3
"""
infra-diagram-as-code — Generate infrastructure diagrams as Mermaid/JSON.
Creates architecture diagrams from a declarative YAML/JSON specification.

Usage:
  python run.py --config infra.yaml --output diagram.mmd
  python run.py --template aws --output infra.mmd
  python run.py --config infra.yaml --format json --output infra.json
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path


# ─── Built-in Templates ─────────────────────────────────────────

TEMPLATES = {
    "aws": {
        "name": "AWS Architecture",
        "diagram_type": "graph",
        "nodes": [
            {"id": "user", "label": "User", "shape": "actor"},
            {"id": "cloudfront", "label": "CloudFront CDN", "shape": "service"},
            {"id": "alb", "label": "Application LB", "shape": "service"},
            {"id": "ecs", "label": "ECS Fargate", "shape": "container"},
            {"id": "rds", "label": "RDS Database", "shape": "database"},
            {"id": "elasticache", "label": "ElastiCache Redis", "shape": "storage"},
            {"id": "s3", "label": "S3 Bucket", "shape": "storage"},
        ],
        "edges": [
            {"from": "user", "to": "cloudfront", "label": "HTTPS"},
            {"from": "cloudfront", "to": "alb", "label": "Forward"},
            {"from": "alb", "to": "ecs", "label": "Route"},
            {"from": "ecs", "to": "rds", "label": "SQL"},
            {"from": "ecs", "to": "elasticache", "label": "Cache"},
            {"from": "ecs", "to": "s3", "label": "Read/Write"},
        ],
    },
    "microservices": {
        "name": "Microservices Architecture",
        "diagram_type": "graph",
        "nodes": [
            {"id": "gateway", "label": "API Gateway", "shape": "service"},
            {"id": "auth", "label": "Auth Service", "shape": "service"},
            {"id": "users", "label": "User Service", "shape": "service"},
            {"id": "orders", "label": "Order Service", "shape": "service"},
            {"id": "payments", "label": "Payment Service", "shape": "service"},
            {"id": "notifications", "label": "Notification Service", "shape": "service"},
            {"id": "users_db", "label": "Users DB", "shape": "database"},
            {"id": "orders_db", "label": "Orders DB", "shape": "database"},
            {"id": "queue", "label": "Message Queue", "shape": "queue"},
            {"id": "cache", "label": "Cache", "shape": "storage"},
        ],
        "edges": [
            {"from": "gateway", "to": "auth", "label": "gRPC"},
            {"from": "gateway", "to": "users", "label": "gRPC"},
            {"from": "gateway", "to": "orders", "label": "gRPC"},
            {"from": "orders", "to": "payments", "label": "gRPC"},
            {"from": "orders", "to": "notifications", "label": "Events"},
            {"from": "users", "to": "users_db", "label": "SQL"},
            {"from": "orders", "to": "orders_db", "label": "SQL"},
            {"from": "orders", "to": "queue", "label": "Publish"},
            {"from": "notifications", "to": "queue", "label": "Subscribe"},
            {"from": "users", "to": "cache", "label": "Read/Write"},
        ],
    },
    "cicd": {
        "name": "CI/CD Pipeline",
        "diagram_type": "flowchart",
        "nodes": [
            {"id": "push", "label": "Git Push", "shape": "start"},
            {"id": "lint", "label": "Lint & Format", "shape": "process"},
            {"id": "test", "label": "Unit & Integration Tests", "shape": "process"},
            {"id": "build", "label": "Build Artifacts", "shape": "process"},
            {"id": "scan", "label": "Security Scan", "shape": "process"},
            {"id": "staging", "label": "Deploy Staging", "shape": "process"},
            {"id": "e2e", "label": "E2E Tests", "shape": "process"},
            {"id": "approval", "label": "Manual Approval", "shape": "decision"},
            {"id": "production", "label": "Deploy Production", "shape": "process"},
            {"id": "monitor", "label": "Monitor & Alert", "shape": "end"},
        ],
        "edges": [
            {"from": "push", "to": "lint", "label": "Trigger"},
            {"from": "lint", "to": "test", "label": "Pass"},
            {"from": "test", "to": "build", "label": "Pass"},
            {"from": "build", "to": "scan", "label": ""},
            {"from": "scan", "to": "staging", "label": "Pass"},
            {"from": "staging", "to": "e2e", "label": ""},
            {"from": "e2e", "to": "approval", "label": "Pass"},
            {"from": "approval", "to": "production", "label": "Approved"},
            {"from": "production", "to": "monitor", "label": "Done"},
        ],
    },
}

SHAPE_MAP = {
    "actor": "👤",
    "service": "🔧",
    "container": "📦",
    "database": "🗄️",
    "storage": "💾",
    "queue": "📨",
    "loadbalancer": "⚖️",
    "firewall": "🔥",
    "start": "▶️",
    "process": "⚙️",
    "decision": "❓",
    "end": "🏁",
}


def load_config(config_path: str) -> dict:
    """Load diagram config from YAML/JSON file."""
    path = Path(config_path)
    if not path.exists():
        return None

    content = path.read_text(encoding="utf-8", errors="replace")

    if path.suffix in (".yaml", ".yml"):
        try:
            import yaml
            return yaml.safe_load(content) or {}
        except ImportError:
            # Fallback: simple JSON-like parsing
            return None
    elif path.suffix == ".json":
        return json.loads(content)

    return None


def generate_mermaid(diagram: dict) -> str:
    """Generate Mermaid diagram code."""
    lines = []
    diagram_type = diagram.get("diagram_type", "graph")
    title = diagram.get("name", "Architecture Diagram")

    lines.append(f"%% {title}")
    lines.append(f"%% Generated by infra-diagram-as-code")
    lines.append("")

    if diagram_type == "flowchart":
        lines.append("flowchart TD")
    else:
        lines.append("graph TB")

    # Style nodes
    shape_styles = {
        "actor": "({id}[{label}])",
        "service": "({id}[{label}])",
        "container": "({id}{{{label}}})",
        "database": "[({id})]",
        "storage": "[({id})]",
        "queue": ">{id}]",
        "start": "({id}(({label})))",
        "process": "({id}[{label}])",
        "decision": "({id}{{{label}}})",
        "end": "({id}({label}))",
    }

    lines.append("")
    # Define nodes
    for node in diagram.get("nodes", []):
        nid = node["id"]
        label = node.get("label", nid)
        shape = node.get("shape", "service")
        mermaid_shape = shape_styles.get(shape, f"({nid}[{label}])")
        lines.append(f"    {nid}" + mermaid_shape.format(id=nid, label=label))

    # Define edges
    lines.append("")
    for edge in diagram.get("edges", []):
        src = edge["from"]
        dst = edge["to"]
        lbl = edge.get("label", "")
        if lbl:
            lines.append(f"    {src} -->|{lbl}| {dst}")
        else:
            lines.append(f"    {src} --> {dst}")

    # Style
    lines.append("")
    lines.append("    classDef default fill:#f9f9f9,stroke:#333,stroke-width:2px;")
    lines.append("    classDef database fill:#e1f5fe,stroke:#0277bd;")
    lines.append("    classDef storage fill:#e8f5e9,stroke:#2e7d32;")
    lines.append("    classDef service fill:#fff3e0,stroke:#e65100;")

    return "\n".join(lines)


def generate_ascii(diagram: dict) -> str:
    """Generate ASCII art diagram."""
    lines = []
    title = diagram.get("name", "Architecture Diagram")

    lines.append(f"  {title}")
    lines.append("  " + "=" * len(title))
    lines.append("")

    node_map = {}
    for node in diagram.get("nodes", []):
        shape = node.get("shape", "service")
        icon = SHAPE_MAP.get(shape, "  ")
        label = node.get("label", node["id"])
        node_map[node["id"]] = label
        lines.append(f"  {icon} [{label}]")

    lines.append("")
    lines.append("  Connections:")
    for edge in diagram.get("edges", []):
        src_label = node_map.get(edge["from"], edge["from"])
        dst_label = node_map.get(edge["to"], edge["to"])
        lbl = edge.get("label", "")
        if lbl:
            lines.append(f"    [{src_label}] --({lbl})--> [{dst_label}]")
        else:
            lines.append(f"    [{src_label}] --> [{dst_label}]")

    return "\n".join(lines)


def generate_json_output(diagram: dict) -> str:
    """Generate JSON output of the diagram."""
    return json.dumps({
        "name": diagram.get("name", "Architecture Diagram"),
        "type": diagram.get("diagram_type", "graph"),
        "nodes": diagram.get("nodes", []),
        "edges": diagram.get("edges", []),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }, indent=2, ensure_ascii=False)


def main():
    parser = argparse.ArgumentParser(
        description="infra-diagram-as-code — Generate infrastructure diagrams as Mermaid/JSON",
    )
    parser.add_argument("--config", default=None, help="Path to diagram config (YAML/JSON)")
    parser.add_argument("--template", default=None, choices=["aws", "microservices", "cicd"],
                        help="Use a built-in template")
    parser.add_argument("--format", default="mermaid", choices=["mermaid", "json", "ascii"],
                        help="Output format (default: mermaid)")
    parser.add_argument("--output", default=None, help="Write output to file")
    parser.add_argument("--dry-run", action="store_true", default=True, help="Preview only (default)")
    parser.add_argument("--no-dry-run", action="store_false", dest="dry_run", help="Write to --output file")
    parser.add_argument("--json", action="store_true", help="JSON output (shorthand for --format json)")

    args = parser.parse_args()

    if args.json:
        args.format = "json"

    # Load diagram data
    diagram = None
    if args.config:
        diagram = load_config(args.config)
        if diagram is None:
            print(f"ERROR: Cannot load config from {args.config}", file=sys.stderr)
            print("  File must be valid YAML or JSON with 'nodes' and 'edges' fields.", file=sys.stderr)
            sys.exit(1)
    elif args.template:
        diagram = TEMPLATES.get(args.template)
        if not diagram:
            print(f"ERROR: Unknown template '{args.template}'", file=sys.stderr)
            sys.exit(1)
    else:
        # Use default microservices template
        diagram = TEMPLATES["microservices"]

    # Generate output
    if args.format == "mermaid":
        output_text = generate_mermaid(diagram)
    elif args.format == "json":
        output_text = generate_json_output(diagram)
    elif args.format == "ascii":
        output_text = generate_ascii(diagram)
    else:
        output_text = generate_mermaid(diagram)

    # Write or print
    if args.output and not args.dry_run:
        try:
            Path(args.output).write_text(output_text, encoding="utf-8")
            print(f"Diagram written to: {args.output}")
        except Exception as e:
            print(f"ERROR writing to {args.output}: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        if args.output:
            print(f"[DRY-RUN] Would write to: {args.output}")
            print(f"---")
        print(output_text)

    sys.exit(0)


if __name__ == "__main__":
    main()
