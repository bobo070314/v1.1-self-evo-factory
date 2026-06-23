#!/usr/bin/env python3
"""
code-navigator — Symbol-level code navigation.
Finds functions, classes, interfaces, exports, imports, and supports fuzzy search.

Usage:
  python run.py --dir ./src --symbol MyComponent
  python run.py --dir ./src --list functions
  python run.py --dir ./src --list all --json
  python run.py --dir ./src --fuzzy "handleCl" --json
"""

import argparse
import ast
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path


# Regex patterns for non-Python files
PATTERNS = {
    "function": {
        ".ts": r'(?:export\s+)?(?:async\s+)?function\s+(\w+)',
        ".tsx": r'(?:export\s+)?(?:async\s+)?function\s+(\w+)',
        ".js": r'(?:export\s+)?(?:async\s+)?function\s+(\w+)',
        ".jsx": r'(?:export\s+)?(?:async\s+)?function\s+(\w+)',
        ".go": r'func\s+(\w+)',
        ".rs": r'fn\s+(\w+)',
        ".py": r'def\s+(\w+)',
    },
    "class": {
        ".ts": r'(?:export\s+)?class\s+(\w+)',
        ".tsx": r'(?:export\s+)?class\s+(\w+)',
        ".js": r'(?:export\s+)?class\s+(\w+)',
        ".jsx": r'(?:export\s+)?class\s+(\w+)',
        ".py": r'class\s+(\w+)',
    },
    "interface": {
        ".ts": r'(?:export\s+)?interface\s+(\w+)',
        ".tsx": r'(?:export\s+)?interface\s+(\w+)',
        ".go": r'type\s+(\w+)\s+interface',
    },
    "export": {
        ".ts": r'export\s+(?:const|let|var|function|class|interface|type|enum)\s+(\w+)',
        ".tsx": r'export\s+(?:const|let|var|function|class|interface|type|enum)\s+(\w+)',
        ".js": r'(?:export\s+(?:const|let|var|function|class)\s+(\w+)|module\.exports\s*=\s*(\w+))',
        ".jsx": r'(?:export\s+(?:const|let|var|function|class)\s+(\w+)|module\.exports\s*=\s*(\w+))',
        ".py": r'(?:^__all__\s*=\s*\[|^(\w+)\s*=.*#\s*export)',
    },
    "import": {
        ".ts": r'import\s+\{[^}]*\b(\w+)\b[^}]*\}\s+from',
        ".tsx": r'import\s+\{[^}]*\b(\w+)\b[^}]*\}\s+from',
        ".js": r'(?:import\s+\{[^}]*\b(\w+)\b[^}]*\}\s+from|require\([^)]*\))',
        ".jsx": r'(?:import\s+\{[^}]*\b(\w+)\b[^}]*\}\s+from|require\([^)]*\))',
        ".py": r'(?:from\s+\S+\s+import\s+(\w+)|import\s+(\w+))',
    },
}


def find_symbols_in_file(filepath: str, symbol_type: str = None) -> list:
    """Find symbols in a single file."""
    path = Path(filepath)
    if not path.exists():
        return []
    if path.suffix not in (".py", ".ts", ".tsx", ".js", ".jsx", ".go", ".rs"):
        return []

    results = []
    try:
        content = path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return []

    if path.suffix == ".py":
        return _find_python_symbols(filepath, content, symbol_type)

    types_to_check = [symbol_type] if symbol_type else list(PATTERNS.keys())
    for stype in types_to_check:
        patterns = PATTERNS.get(stype, {})
        for ext, pat in patterns.items():
            if ext != path.suffix:
                continue
            for match in re.finditer(pat, content, re.MULTILINE):
                line_no = content[:match.start()].count('\n') + 1
                # Get all capture groups, take first non-None
                name = None
                for g in match.groups():
                    if g is not None:
                        name = g
                        break
                if name:
                    results.append({
                        "file": str(path),
                        "line": line_no,
                        "type": stype,
                        "name": name,
                    })
    return results


def _find_python_symbols(filepath: str, content: str, symbol_type: str = None) -> list:
    """Find symbols in Python files using AST."""
    results = []
    try:
        tree = ast.parse(content)
    except SyntaxError:
        return results

    for node in ast.walk(tree):
        if symbol_type and symbol_type not in ("all", "function", "class", "import", "export"):
            continue

        if isinstance(node, ast.FunctionDef) and (not symbol_type or symbol_type in ("function", "all")):
            results.append({
                "file": filepath,
                "line": node.lineno,
                "type": "function",
                "name": node.name,
            })
        elif isinstance(node, ast.AsyncFunctionDef) and (not symbol_type or symbol_type in ("function", "all")):
            results.append({
                "file": filepath,
                "line": node.lineno,
                "type": "async_function",
                "name": node.name,
            })
        elif isinstance(node, ast.ClassDef) and (not symbol_type or symbol_type in ("class", "all")):
            results.append({
                "file": filepath,
                "line": node.lineno,
                "type": "class",
                "name": node.name,
            })
        elif isinstance(node, ast.Import) and (not symbol_type or symbol_type in ("import", "all")):
            for alias in node.names:
                results.append({
                    "file": filepath,
                    "line": node.lineno,
                    "type": "import",
                    "name": alias.asname or alias.name,
                })
        elif isinstance(node, ast.ImportFrom) and (not symbol_type or symbol_type in ("import", "all")):
            for alias in node.names:
                results.append({
                    "file": filepath,
                    "line": node.lineno,
                    "type": "import",
                    "name": alias.asname or alias.name,
                })

    return results


def scan_directory(directory: str, symbol_type: str = None) -> list:
    """Scan all supported files in a directory for symbols."""
    all_results = []
    root = Path(directory)
    for filepath in root.rglob("*"):
        if filepath.is_file() and filepath.suffix in (".py", ".ts", ".tsx", ".js", ".jsx", ".go", ".rs"):
            # Skip node_modules and __pycache__
            if "node_modules" in filepath.parts or "__pycache__" in filepath.parts:
                continue
            results = find_symbols_in_file(str(filepath), symbol_type)
            all_results.extend(results)
    return all_results


def fuzzy_search(results: list, query: str) -> list:
    """Fuzzy search results by name substring (case-insensitive)."""
    query_lower = query.lower()
    return [r for r in results if query_lower in r["name"].lower()]


def main():
    parser = argparse.ArgumentParser(
        description="code-navigator — Symbol-level code navigation",
    )
    parser.add_argument("--dir", default=os.getcwd(), help="Directory to scan (default: cwd)")
    parser.add_argument("--symbol", default=None, help="Find specific symbol by name (exact match)")
    parser.add_argument("--fuzzy", default=None, help="Fuzzy search for symbol by name (substring)")
    parser.add_argument("--list", default=None,
                        choices=["functions", "classes", "interfaces", "exports", "imports", "all"],
                        help="List symbols of a specific type")
    parser.add_argument("--file", default=None, help="Scan a single file instead of directory")
    parser.add_argument("--dry-run", action="store_true", default=True, help="Preview mode (default)")
    parser.add_argument("--no-dry-run", action="store_false", dest="dry_run", help="Not used for code-navigator")
    parser.add_argument("--json", action="store_true", help="Output as JSON")

    args = parser.parse_args()

    if args.file:
        # Single file mode
        symbol_type_map = {
            "functions": "function",
            "classes": "class",
            "interfaces": "interface",
            "exports": "export",
            "imports": "import",
            "all": None,
        }
        stype = symbol_type_map.get(args.list, None)
        results = find_symbols_in_file(args.file, stype)
    else:
        stype = None
        if args.list:
            stype_map = {
                "functions": "function",
                "classes": "class",
                "interfaces": "interface",
                "exports": "export",
                "imports": "import",
                "all": None,
            }
            stype = stype_map.get(args.list)
        results = scan_directory(args.dir, stype)

    # Exact symbol search
    if args.symbol:
        results = [r for r in results if r["name"] == args.symbol]

    # Fuzzy search
    if args.fuzzy:
        results = fuzzy_search(results, args.fuzzy)

    output = {
        "directory": args.dir if not args.file else args.file,
        "symbol_count": len(results),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "results": results,
    }

    if args.json:
        print(json.dumps(output, indent=2, ensure_ascii=False))
    else:
        print(f"code-navigator — Found {len(results)} symbols")
        if args.symbol:
            print(f"  Search: exact match for '{args.symbol}'")
        if args.fuzzy:
            print(f"  Search: fuzzy match for '{args.fuzzy}'")
        if args.list:
            print(f"  Filter: {args.list}")

        # Group by type for display
        by_type = {}
        for r in results:
            by_type.setdefault(r["type"], []).append(r)

        for stype, items in sorted(by_type.items()):
            print(f"\n  [{stype}] ({len(items)})")
            for item in items[:20]:  # Limit display
                rel_path = item["file"]
                print(f"    {item['name']} — {rel_path}:{item['line']}")
            if len(items) > 20:
                print(f"    ... and {len(items) - 20} more")

    sys.exit(0)


if __name__ == "__main__":
    main()
