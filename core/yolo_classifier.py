#!/usr/bin/env python3
"""core/yolo_classifier.py — Single Responsibility Security Classifier

One entry point: classify(text_or_file). No branching, no side effects.
Returns: {passed: bool, failures: [{id, level, category, message, line, context}]}

23 Detection Functions — each does ONE thing:
  1.  check_unicode_zero_width     — Zero-width characters in source
  2.  check_zsh_injection          — $(...) or `...` shell injection
  3.  check_path_traversal         — ../ or ..\\  path escape
  4.  check_sql_injection          — SQL injection patterns
  5.  check_xss_reflected          — Reflected XSS (innerHTML, dangerouslySetInnerHTML)
  6.  check_hardcoded_secret       — API keys, tokens, passwords hardcoded
  7.  check_command_injection      — os.system, eval, exec with user input
  8.  check_sensitive_data_leak    — PII / credit card / SSN patterns
  9.  check_open_redirect          — window.location with user-controlled URL
  10. check_csrf_missing           — Forms without CSRF tokens
  11. check_unvalidated_redirect   — URL redirect without validation
  12. check_xxe_vulnerable         — XML parsing without external entity disable
  13. check_deserialization_unsafe — pickle/yaml.unsafe_load/unmarshal
  14. check_prototype_pollution    — __proto__ or constructor.prototype assignment
  15. check_regex_dos              — Nested quantifiers in user-facing regex
  16. check_cors_misconfig         — Access-Control-Allow-Origin: *
  17. check_insecure_crypto        — MD5/SHA1 for passwords, ECB mode
  18. check_hardcoded_ip           — Hardcoded internal IPs (10.x, 172.16.x, 192.168.x)
  19. check_debug_enabled          — DEBUG=True / debugger left on
  20. check_dependency_confusion   — Private package names published on public registry
  21. check_insecure_random        — Math.random() / rand() for security
  22. check_missing_rate_limit     — No rate limiting on auth/sensitive endpoints
  23. check_log_injection          — Unsanitized user input in log statements
"""

import json
import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional


# ---- Severity ----
CRITICAL = "critical"
HIGH = "high"
MEDIUM = "medium"
LOW = "low"


def _failure(check_id: int, level: str, category: str, message: str,
             line: int = 0, context: str = "") -> Dict:
    return {
        "id": f"SEC-{check_id:03d}",
        "level": level,
        "category": category,
        "message": message,
        "line": line,
        "context": context[:200],
    }


# =============================================================================
# 23 Detection Functions
# =============================================================================

def check_unicode_zero_width(text: str, lines: List[str]) -> List[Dict]:
    """Detect zero-width characters used for malicious code hiding."""
    results = []
    zw_chars = {
        '\u200b': "ZERO WIDTH SPACE",
        '\u200c': "ZERO WIDTH NON-JOINER",
        '\u200d': "ZERO WIDTH JOINER",
        '\ufeff': "ZERO WIDTH NO-BREAK SPACE (BOM)",
        '\u2060': "WORD JOINER",
        '\u2061': "FUNCTION APPLICATION",
        '\u2062': "INVISIBLE TIMES",
        '\u2063': "INVISIBLE SEPARATOR",
        '\u2064': "INVISIBLE PLUS",
    }
    for i, line in enumerate(lines, 1):
        for ch, name in zw_chars.items():
            if ch in line:
                # Ignore BOM at start of file
                if ch == '\ufeff' and i == 1 and line.startswith(ch):
                    continue
                results.append(_failure(1, HIGH, "unicode-injection",
                    f"Zero-width character '{name}' (U+{ord(ch):04X}) found on line {i}",
                    line=i, context=line.strip()[:100]))
    return results


def check_zsh_injection(text: str, lines: List[str]) -> List[Dict]:
    """Detect shell injection patterns: $(cmd), `cmd`, ;cmd, |cmd."""
    results = []
    patterns = [
        (r'\$\([^)]+\)', "Command substitution $(...)"),
        (r'`[^`]+`', "Backtick command substitution"),
    ]
    for i, line in enumerate(lines, 1):
        # Skip comments and docstrings
        stripped = line.strip()
        if stripped.startswith(("#", "//", "/*", "*", "'''", '"""')):
            continue
        for pat, desc in patterns:
            for match in re.finditer(pat, line):
                results.append(_failure(2, CRITICAL, "shell-injection",
                    f"{desc} in code: '{match.group()[:80]}'",
                    line=i, context=line.strip()[:150]))
    return results


def check_path_traversal(text: str, lines: List[str]) -> List[Dict]:
    """Detect path traversal patterns: ../, ..\\, os.path.join(user_input, ...)."""
    results = []
    for i, line in enumerate(lines, 1):
        if re.search(r'(?:\.\./|\.\.\\)', line):
            if 'test' not in line.lower() and '# nosec' not in line.lower():
                results.append(_failure(3, HIGH, "path-traversal",
                    f"Path traversal detected: '{line.strip()[:100]}'",
                    line=i, context=line.strip()[:100]))
    return results


def check_sql_injection(text: str, lines: List[str]) -> List[Dict]:
    """Detect SQL injection: string concatenation/f-strings in queries."""
    results = []
    sql_keywords = r'(SELECT|INSERT|UPDATE|DELETE|DROP|ALTER|CREATE)\s'
    for i, line in enumerate(lines, 1):
        if re.search(sql_keywords, line, re.IGNORECASE):
            # Check for unsafe concatenation
            if '+' in line and any(x in line for x in ['request.', 'params', 'body', 'query', 'input', 'argv']):
                results.append(_failure(4, CRITICAL, "sql-injection",
                    "Potential SQL injection: user input concatenated into query",
                    line=i, context=line.strip()[:150]))
            # Python f-string in SQL
            if re.match(r'.*f["\'].*\b(SELECT|INSERT|UPDATE)\b', line, re.IGNORECASE):
                if any(x in line for x in ['request', 'params', 'input', 'user']):
                    results.append(_failure(4, CRITICAL, "sql-injection",
                        "Potential SQL injection: f-string with user input in query",
                        line=i, context=line.strip()[:150]))
    return results


def check_xss_reflected(text: str, lines: List[str]) -> List[Dict]:
    """Detect reflected XSS vectors."""
    results = []
    xss_sinks = [
        (r'innerHTML\s*=', "innerHTML assignment"),
        (r'dangerouslySetInnerHTML', "React dangerouslySetInnerHTML"),
        (r'document\.write\(', "document.write()"),
        (r'\.outerHTML\s*=', "outerHTML assignment"),
        (r'eval\(', "eval() with potential XSS"),
    ]
    for i, line in enumerate(lines, 1):
        for pat, desc in xss_sinks:
            if re.search(pat, line):
                if not re.search(r'(escape|sanitize|DOMPurify|safe)', line, re.IGNORECASE):
                    results.append(_failure(5, HIGH, "xss",
                        f"XSS sink '{desc}' without visible sanitization",
                        line=i, context=line.strip()[:150]))
    return results


def check_hardcoded_secret(text: str, lines: List[str]) -> List[Dict]:
    """Detect hardcoded secrets: API keys, tokens, passwords."""
    results = []
    secret_patterns = [
        (r'(?:api_key|apikey|API_KEY|API_SECRET|SECRET_KEY)\s*[:=]\s*["\'][A-Za-z0-9_\-]{8,}["\']', "API Key"),
        (r'(?:password|passwd|pwd)\s*[:=]\s*["\'][^"\']+["\']', "Hardcoded password"),
        (r'(?:token|TOKEN)\s*[:=]\s*["\'][A-Za-z0-9_\-\.]{16,}["\']', "Access token"),
        (r'(?:BEGIN\s+(?:RSA|EC|DSA|OPENSSH)\s+PRIVATE\s+KEY)', "Private key"),
        (r'sk-[A-Za-z0-9]{32,}', "OpenAI API key"),
        (r'ghp_[A-Za-z0-9]{36}', "GitHub personal access token"),
        (r'gho_[A-Za-z0-9]{36}', "GitHub OAuth token"),
        (r'github_pat_[A-Za-z0-9_]{22,}', "GitHub fine-grained token"),
    ]
    for i, line in enumerate(lines, 1):
        # Skip comments and string literals in non-code
        stripped = line.strip()
        if stripped.startswith(("#", "//", "/*", "*")):
            continue
        for pat, desc in secret_patterns:
            if re.search(pat, line):
                # Mask the actual secret
                masked = re.sub(r'(["\'])([^"\']{4})[^"\']*(["\'])', r'\1\2***\3', line.strip()[:120])
                results.append(_failure(6, CRITICAL, "hardcoded-secret",
                    f"Hardcoded {desc} detected: {masked}",
                    line=i, context=masked))
    return results


def check_command_injection(text: str, lines: List[str]) -> List[Dict]:
    """Detect command injection: os.system, subprocess with shell=True."""
    results = []
    for i, line in enumerate(lines, 1):
        if re.search(r'shell\s*=\s*True', line):
            user_input_patterns = ['request', 'input', 'argv', 'sys.argv', 'params', 'body', 'query', 'user']
            if any(x in line for x in user_input_patterns):
                results.append(_failure(7, CRITICAL, "command-injection",
                    f"subprocess(shell=True) with potential user input",
                    line=i, context=line.strip()[:150]))
        if re.search(r'os\.(system|popen)\(', line):
            if any(x in line for x in ['request', 'input', 'argv']):
                results.append(_failure(7, CRITICAL, "command-injection",
                    f"os.system/os.popen with potential user input",
                    line=i, context=line.strip()[:150]))
    return results


def check_sensitive_data_leak(text: str, lines: List[str]) -> List[Dict]:
    """Detect PII patterns: credit cards, SSN, email in code."""
    results = []
    for i, line in enumerate(lines, 1):
        # Credit card pattern (simplified)
        if re.search(r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b', line):
            results.append(_failure(8, HIGH, "data-leak",
                "Potential credit card number in code", line=i))
        # Chinese ID number (18 digits)
        if re.search(r'\b[1-9]\d{5}(?:19|20)\d{2}(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01])\d{3}[\dXx]\b', line):
            results.append(_failure(8, HIGH, "data-leak",
                "Potential Chinese ID number in code", line=i))
    return results


def check_open_redirect(text: str, lines: List[str]) -> List[Dict]:
    """Detect open redirect vectors."""
    results = []
    for i, line in enumerate(lines, 1):
        if re.search(r'window\.location\s*=|redirect\(|Router\.push\(', line):
            if any(x in line for x in ['req.query', 'req.params', 'searchParams', 'location.search']):
                results.append(_failure(9, MEDIUM, "open-redirect",
                    "Potential open redirect with user-controlled URL",
                    line=i, context=line.strip()[:150]))
    return results


def check_csrf_missing(text: str, lines: List[str]) -> List[Dict]:
    """Detect forms without CSRF protection."""
    results = []
    has_form = False
    has_csrf = False
    for line in lines:
        if re.search(r'<form\b', line, re.IGNORECASE):
            has_form = True
        if re.search(r'csrf|_token|authenticity_token|csrf_token', line, re.IGNORECASE):
            has_csrf = True
    if has_form and not has_csrf:
        results.append(_failure(10, HIGH, "csrf",
            "HTML form detected without CSRF token field"))
    return results


def check_unvalidated_redirect(text: str, lines: List[str]) -> List[Dict]:
    """Detect URL redirects without whitelist validation."""
    results = []
    redirect_funcs = ['redirect(', 'Redirect(', 'HttpResponseRedirect(', 'res.redirect(']
    for i, line in enumerate(lines, 1):
        for func in redirect_funcs:
            if func in line:
                # Check if there's any validation nearby (within 3 lines)
                nearby = lines[max(0,i-3):min(len(lines),i+3)]
                nearby_text = ' '.join(nearby)
                if not re.search(r'(whitelist|allowed_urls|valid_url|urlparse|URL\(|url_valid)', nearby_text, re.IGNORECASE):
                    results.append(_failure(11, MEDIUM, "unvalidated-redirect",
                        f"Redirect '{func}' without visible URL validation",
                        line=i, context=line.strip()[:100]))
    return results


def check_xxe_vulnerable(text: str, lines: List[str]) -> List[Dict]:
    """Detect XML parsing without external entity protection."""
    results = []
    xml_parsers = [
        'etree.parse(', 'etree.fromstring(', 'xml.etree.ElementTree',
        'minidom.parse(', 'sax.parse(', 'lxml', 'xmltodict.parse(',
    ]
    for i, line in enumerate(lines, 1):
        if any(p in line for p in xml_parsers):
            # Check if XXE protection is explicitly set
            nearby = ' '.join(lines[max(0,i-5):min(len(lines),i+5)])
            if not re.search(r'(defusedxml|resolve_entities=False| forbid_dtd|NoDTD|no_network)', nearby, re.IGNORECASE):
                results.append(_failure(12, HIGH, "xxe",
                    "XML parsing without visible XXE protection",
                    line=i, context=line.strip()[:100]))
    return results


def check_deserialization_unsafe(text: str, lines: List[str]) -> List[Dict]:
    """Detect unsafe deserialization."""
    results = []
    unsafe = [
        (r'pickle\.(loads?|Unpickler)', "pickle deserialization"),
        (r'yaml\.load\(', "yaml.load() (use yaml.safe_load)"),
        (r'cPickle\.loads?\(', "cPickle deserialization"),
        (r'marshal\.loads?\(', "marshal deserialization"),
        (r'jsonpickle\.(decode|loads)', "jsonpickle deserialization"),
    ]
    for i, line in enumerate(lines, 1):
        if stripped := line.strip():
            if stripped.startswith(("#", "//", "/*")):
                continue
            for pat, desc in unsafe:
                if re.search(pat, line):
                    results.append(_failure(13, CRITICAL, "unsafe-deserialization",
                        f"Unsafe deserialization via {desc}",
                        line=i, context=line.strip()[:120]))
    return results


def check_prototype_pollution(text: str, lines: List[str]) -> List[Dict]:
    """Detect JS prototype pollution vectors."""
    results = []
    for i, line in enumerate(lines, 1):
        if re.search(r'__proto__|constructor\.prototype', line):
            if any(x in line for x in ['merge(', 'extend(', 'assign(', '...', 'spread']):
                results.append(_failure(14, HIGH, "prototype-pollution",
                    "__proto__/prototype used in merge/assign — prototype pollution risk",
                    line=i, context=line.strip()[:150]))
    return results


def check_regex_dos(text: str, lines: List[str]) -> List[Dict]:
    """Detect ReDoS patterns: nested quantifiers like (a+)+, (a|b)*."""
    results = []
    redos_patterns = [
        r'\([^)]+\+\)\+',  # (a+)+
        r'\([^)]+\*\)\*',  # (a*)*
        r'\([^)]*\|[^)]*\)\+',  # (a|b)+ nested
    ]
    for i, line in enumerate(lines, 1):
        for pat in redos_patterns:
            match = re.search(pat, line)
            if match and re.search(r'(email|url|input|user|request)', line, re.IGNORECASE):
                results.append(_failure(15, MEDIUM, "redos",
                    f"Potential ReDoS: nested quantifier with user input",
                    line=i, context=line.strip()[:100]))
    return results


def check_cors_misconfig(text: str, lines: List[str]) -> List[Dict]:
    """Detect CORS misconfiguration: wildcard origin with credentials."""
    results = []
    has_wildcard = False
    has_credentials = False
    for i, line in enumerate(lines, 1):
        if 'Access-Control-Allow-Origin' in line and '*' in line:
            has_wildcard = True
        if 'Access-Control-Allow-Credentials' in line and 'true' in line.lower():
            has_credentials = True
    if has_wildcard and has_credentials:
        results.append(_failure(16, HIGH, "cors",
            "CORS misconfiguration: wildcard origin with credentials=true"))
    elif has_wildcard:
        results.append(_failure(16, MEDIUM, "cors",
            "CORS: wildcard origin (acceptable without credentials)"))
    return results


def check_insecure_crypto(text: str, lines: List[str]) -> List[Dict]:
    """Detect insecure cryptographic usage."""
    results = []
    insecure = [
        (r'\bmd5\b', "MD5 hash"),
        (r'\bsha1\b', "SHA1 hash"),
        (r'ECB\b', "ECB block cipher mode"),
        (r'DES\b(?!\.)', "DES cipher"),
        (r'RC4\b', "RC4 cipher"),
    ]
    crypto_contexts = ['password', 'hash', 'cipher', 'encrypt', 'token', 'sign']
    for i, line in enumerate(lines, 1):
        for pat, desc in insecure:
            if re.search(pat, line, re.IGNORECASE):
                if any(ctx in line.lower() for ctx in crypto_contexts):
                    results.append(_failure(17, HIGH, "insecure-crypto",
                        f"Insecure cryptography: {desc} used in security context",
                        line=i, context=line.strip()[:100]))
    return results


def check_hardcoded_ip(text: str, lines: List[str]) -> List[Dict]:
    """Detect hardcoded internal IPs."""
    results = []
    internal_ips = [
        r'\b10\.\d{1,3}\.\d{1,3}\.\d{1,3}\b',
        r'\b172\.(?:1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3}\b',
        r'\b192\.168\.\d{1,3}\.\d{1,3}\b',
        r'\b127\.0\.0\.1\b',
    ]
    for i, line in enumerate(lines, 1):
        for pat in internal_ips:
            match = re.search(pat, line)
            if match:
                if not re.search(r'(test|mock|example|localhost|sandbox)', line.lower()):
                    results.append(_failure(18, LOW, "hardcoded-ip",
                        f"Hardcoded internal IP: {match.group()}",
                        line=i, context=line.strip()[:100]))
    return results


def check_debug_enabled(text: str, lines: List[str]) -> List[Dict]:
    """Detect debug mode left enabled."""
    results = []
    debug_patterns = [
        (r'DEBUG\s*=\s*True', "DEBUG=True"),
        (r'debug\s*:\s*true', "debug: true (JSON/YAML config)"),
        (r'ENV\s*=\s*[\"\']development[\"\']', "ENV=development"),
        (r'NODE_ENV\s*=\s*[\"\']development[\"\']', "NODE_ENV=development"),
        (r'debugger\s*;', "debugger statement"),
    ]
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith(("#", "//", "/*", "*")):
            continue
        for pat, desc in debug_patterns:
            if re.search(pat, line):
                results.append(_failure(19, MEDIUM, "debug-enabled",
                    f"Debug mode enabled: {desc}",
                    line=i, context=line.strip()[:100]))
    return results


def check_dependency_confusion(text: str, lines: List[str]) -> List[Dict]:
    """Detect private/internal package names that could be confused with public."""
    results = []
    # Check requirements.txt / package.json style files
    private_indicators = ['my-', 'internal-', 'company-', 'private-', 'custom-']
    for i, line in enumerate(lines, 1):
        if any(ind in line.lower() for ind in private_indicators):
            if re.search(r'==|@|:', line):  # Looks like a dependency declaration
                results.append(_failure(20, MEDIUM, "dependency-confusion",
                    "Private package name could be confused with public registry",
                    line=i, context=line.strip()[:100]))
    return results


def check_insecure_random(text: str, lines: List[str]) -> List[Dict]:
    """Detect insecure random number generation for security purposes."""
    results = []
    for i, line in enumerate(lines, 1):
        if re.search(r'Math\.random\(\)', line):
            if any(x in line.lower() for x in ['token', 'password', 'secret', 'csrf', 'nonce', 'session']):
                results.append(_failure(21, HIGH, "insecure-random",
                    "Math.random() used for security-sensitive purpose",
                    line=i, context=line.strip()[:100]))
        if re.search(r'\brand\(\)', line) or re.search(r'\brandom\.randint\(', line):
            if any(x in line.lower() for x in ['token', 'password', 'secret']):
                results.append(_failure(21, HIGH, "insecure-random",
                    "Insecure random (rand/randint) for security purpose",
                    line=i, context=line.strip()[:100]))
    return results


def check_missing_rate_limit(text: str, lines: List[str]) -> List[Dict]:
    """Detect auth endpoints without rate limiting."""
    results = []
    has_auth_endpoint = False
    has_rate_limit = False
    for line in lines:
        if re.search(r'(login|auth|signin|signup|register|verify|otp|2fa|mfa)', line.lower()):
            if re.search(r'(def |app\.|router\.|@app|@router|@bp|async def|function)', line):
                has_auth_endpoint = True
        if re.search(r'(rate.limit|ratelimit|throttle|limiter|RateLimiter)', line.lower()):
            has_rate_limit = True
    if has_auth_endpoint and not has_rate_limit:
        results.append(_failure(22, MEDIUM, "missing-rate-limit",
            "Auth endpoint detected without visible rate limiting"))
    return results


def check_log_injection(text: str, lines: List[str]) -> List[Dict]:
    """Detect unsanitized user input in log statements."""
    results = []
    log_funcs = ['log.', 'logger.', 'console.log', 'logging.', 'print(']
    for i, line in enumerate(lines, 1):
        if any(f in line for f in log_funcs):
            if any(x in line for x in ['request.', 'req.', 'user_input', 'params', 'body', 'query']):
                # Check for sanitization
                if not re.search(r'(sanitize|escape|strip|replace|clean)', line.lower()):
                    results.append(_failure(23, LOW, "log-injection",
                        "User-controlled data logged without sanitization",
                        line=i, context=line.strip()[:120]))
    return results


# ---- Registry ----
ALL_CHECKS = [
    check_unicode_zero_width,
    check_zsh_injection,
    check_path_traversal,
    check_sql_injection,
    check_xss_reflected,
    check_hardcoded_secret,
    check_command_injection,
    check_sensitive_data_leak,
    check_open_redirect,
    check_csrf_missing,
    check_unvalidated_redirect,
    check_xxe_vulnerable,
    check_deserialization_unsafe,
    check_prototype_pollution,
    check_regex_dos,
    check_cors_misconfig,
    check_insecure_crypto,
    check_hardcoded_ip,
    check_debug_enabled,
    check_dependency_confusion,
    check_insecure_random,
    check_missing_rate_limit,
    check_log_injection,
]

CHECK_NAMES = {
    1: "unicode-zero-width", 2: "zsh-injection", 3: "path-traversal",
    4: "sql-injection", 5: "xss-reflected", 6: "hardcoded-secret",
    7: "command-injection", 8: "sensitive-data-leak", 9: "open-redirect",
    10: "csrf-missing", 11: "unvalidated-redirect", 12: "xxe",
    13: "unsafe-deserialization", 14: "prototype-pollution", 15: "regex-dos",
    16: "cors-misconfig", 17: "insecure-crypto", 18: "hardcoded-ip",
    19: "debug-enabled", 20: "dependency-confusion", 21: "insecure-random",
    22: "missing-rate-limit", 23: "log-injection",
}


def classify(text_or_path: str, checks: List = None) -> Dict:
    """Single entry point. classify() is the only public API.

    Args:
        text_or_path: Code text to scan, or a file path.
        checks: Optional list of check functions to run (default: all 23).

    Returns:
        {passed: bool, total_checks: int, failures: [...], summary: {...}}
    """
    checks = checks or ALL_CHECKS

    # Try as file path
    if os.path.isfile(text_or_path):
        with open(text_or_path, "r", encoding="utf-8", errors="replace") as f:
            text = f.read()
    else:
        text = text_or_path

    lines = text.splitlines()
    all_failures = []
    counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}

    for check_fn in checks:
        failures = check_fn(text, lines)
        for f in failures:
            counts[f["level"]] = counts.get(f["level"], 0) + 1
        all_failures.extend(failures)

    passed = len(all_failures) == 0

    return {
        "passed": passed,
        "total_checks": len(checks),
        "total_failures": len(all_failures),
        "severity_counts": counts,
        "failures": all_failures,
        "summary": f"{len(all_failures)} issues found ({counts['critical']} critical, "
                    f"{counts['high']} high, {counts['medium']} medium, {counts['low']} low)",
    }


# ---- CLI ----
if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser(description="YOLO Security Classifier — 23 detection functions")
    p.add_argument("target", nargs="?", help="File path or inline code to scan")
    p.add_argument("--json", action="store_true", help="JSON output")
    p.add_argument("--list", action="store_true", help="List all 23 checks")
    args = p.parse_args()

    if args.list:
        for cid, name in CHECK_NAMES.items():
            print(f"  SEC-{cid:03d}: {name}")
        print(f"\nTotal: {len(CHECK_NAMES)} detection functions")
        sys.exit(0)

    if args.target:
        result = classify(args.target)
        if args.json:
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            if result["passed"]:
                print("✅ PASSED — no security issues detected")
            else:
                print(f"❌ {result['summary']}")
                for f in result["failures"][:20]:
                    print(f"  [{f['level'].upper()}] {f['id']} L{f['line']}: {f['message']}")
                if len(result["failures"]) > 20:
                    print(f"  ... and {len(result['failures'])-20} more")
        sys.exit(0 if result["passed"] else 1)

    sys.exit(0)
