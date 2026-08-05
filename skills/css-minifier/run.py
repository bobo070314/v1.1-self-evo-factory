#!/usr/bin/env python3
"""CSS Minifier - Compress and minify CSS code."""

import argparse
import re
import sys
import json

VERSION = "1.0.0"


def minify_css(css: str) -> str:
    """Minify CSS by removing comments, unnecessary whitespace, and redundant semicolons."""
    if not css or not css.strip():
        return ""

    result = []
    i = 0
    length = len(css)
    in_string = None  # None, '"', or "'"
    in_comment = False
    prev_char = None
    after_block_start = False
    after_property_value = False
    after_comma = False
    in_url = False

    while i < length:
        char = css[i]

        # Handle string literals
        if in_string:
            result.append(char)
            if char == '\\' and i + 1 < length:
                i += 1
                if i < length:
                    result.append(css[i])
            elif char == in_string:
                in_string = None
            i += 1
            continue

        if char in ('"', "'"):
            in_string = char
            result.append(char)
            i += 1
            continue

        # Handle comments
        if not in_comment and char == '/' and i + 1 < length and css[i + 1] == '*':
            in_comment = True
            i += 2
            continue

        if in_comment:
            if char == '*' and i + 1 < length and css[i + 1] == '/':
                in_comment = False
                i += 2
                continue
            i += 1
            continue

        # Skip whitespace outside strings and comments
        if char in (' ', '\t', '\n', '\r'):
            # Collapse whitespace
            if result and result[-1] not in (' ', '\t', '\n', '\r', '{', '}', ':', ',', ';', '('):
                result.append(' ')
            i += 1
            continue

        # Handle special cases for colons and semicolons
        if char == ':' and not in_url:
            # Check if we're in a URL context
            if result and result[-1] == 'u' and len(result) >= 4:
                suffix = ''.join(result[-4:]).lower()
                if suffix == 'url':
                    in_url = True
            result.append(char)
            i += 1
            continue

        if char == ')':
            in_url = False
            result.append(char)
            i += 1
            continue

        if char == ';':
            result.append(char)
            i += 1
            continue

        if char == '{':
            # Remove any trailing space before {
            if result and result[-1] == ' ':
                result.pop()
            result.append(char)
            i += 1
            continue

        if char == '}':
            result.append(char)
            i += 1
            continue

        # Regular character
        result.append(char)
        i += 1

    # Post-processing: remove redundant semicolons
    output = ''.join(result)
    output = remove_redundant_semicolons(output)

    # Remove trailing whitespace
    output = output.rstrip()

    return output


def remove_redundant_semicolons(css: str) -> str:
    """Remove redundant semicolons after closing braces and at the end."""
    # Remove semicolons before closing braces
    css = re.sub(r';\s*\}', '}', css)
    # Remove trailing semicolons
    css = css.rstrip(';').rstrip()
    return css


def process_file(filepath: str) -> str:
    """Read and minify a CSS file."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
    except FileNotFoundError:
        print(f"Error: File not found: {filepath}", file=sys.stderr)
        sys.exit(1)
    except UnicodeDecodeError:
        try:
            with open(filepath, 'r', encoding='latin-1') as f:
                content = f.read()
        except Exception as e:
            print(f"Error reading file: {e}", file=sys.stderr)
            sys.exit(1)
    except Exception as e:
        print(f"Error reading file: {e}", file=sys.stderr)
        sys.exit(1)

    return minify_css(content)


def process_stdin() -> str:
    """Read CSS from stdin and minify it."""
    try:
        content = sys.stdin.read()
    except Exception as e:
        print(f"Error reading stdin: {e}", file=sys.stderr)
        sys.exit(1)
    return minify_css(content)


def main():
    parser = argparse.ArgumentParser(
        description='Compress and minify CSS code.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''Examples:
  echo "body { color: red; }" | python run.py
  python run.py input.css
  python run.py --json input.css
  python run.py --dry-run input.css
'''
    )
    parser.add_argument('--version', action='version', version=VERSION)
    parser.add_argument('--json', action='store_true', help='Output as JSON')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be done without modifying files')
    parser.add_argument('input', nargs='?', help='Input CSS file (reads from stdin if not provided)')

    args = parser.parse_args()

    if args.input:
        result = process_file(args.input)
    else:
        result = process_stdin()

    if args.json:
        output = {
            "version": VERSION,
            "input": args.input,
            "minified": result,
            "original_size": len(args.input if args.input else sys.stdin.read()) if not args.dry_run else 0,
            "minified_size": len(result)
        }
        print(json.dumps(output, indent=2))
    else:
        if args.dry_run:
            if args.input:
                print(f"Would minify: {args.input}")
                print(f"Original size: {len(process_file(args.input))} bytes")
                print(f"Minified size: {len(result)} bytes")
                print(f"Savings: {100 * (1 - len(result) / max(len(process_file(args.input)), 1)):.1f}%")
            else:
                print("Would minify from stdin")
                print(f"Minified size: {len(result)} bytes")
        else:
            print(result)


if __name__ == '__main__':
    main()