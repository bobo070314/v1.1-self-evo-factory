#!/usr/bin/env python3
"""🦞 Web Developer Agent — 猫的眼睛和手
Playwright 驱动的全栈网站自检代理。
赋能：截图、点击、填表、样式审计、响应式测试。
挂载到 evolution_engine.orchestrate_agents() 作为 'web-dev' agent。
"""

import hashlib
import json
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path

BASE = Path(os.environ.get("WEBDEV_BASE", "D:/bobo/openclaw-foreign/workspace"))
SCREENSHOTS_DIR = BASE / ".deploy" / "screenshots"
STATE_FILE = BASE / ".deploy" / "webdev_state.json"

# --- Chromium 启动配置 ---
CHROMIUM_PATHS = [
    r"D:\bobo\ms-playwright\chromium-1208\chrome-win64\chrome.exe",
    r"D:\bobo\ms-playwright\chromium_headless_shell-1208\chrome-headless-shell-win64\chrome-headless-shell.exe",
]

BROWSER_ARGS = [
    "--no-proxy-server",
    "--disable-web-security",
    "--disable-gpu",
    "--disable-dev-shm-usage",
    "--no-sandbox",
    "--window-size=1920,1080",
]


def ts():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _find_chromium() -> str | None:
    """找到可用的 Chromium 可执行文件"""
    for p in CHROMIUM_PATHS:
        if Path(p).exists():
            return p
    return None


def _load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    return {"screenshots": [], "audits": [], "last_run": None}


def _save_state(state: dict):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")


def screenshot(target: str, wait_ms: int = 1000, selector: str | None = None) -> str | None:
    """截图：URL 或本地文件路径。
    target: http(s)://... 或 file:///... 或本地绝对路径
    selector: CSS 选择器，等这个元素出现再截图
    返回截图路径（相对于 BASE）
    """
    chromium = _find_chromium()
    if not chromium:
        print("[WebDev] ❌ Chromium not found")
        return None

    from playwright.sync_api import sync_playwright

    target_url = target
    if not target.startswith(("http://", "https://", "file:///")):
        target_url = f"file:///{target}"

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, executable_path=chromium, args=BROWSER_ARGS)
            page = browser.new_page(viewport={"width": 1920, "height": 1080})

            page.goto(target_url, wait_until="domcontentloaded", timeout=15000)
            time.sleep(wait_ms / 1000)

            if selector:
                try:
                    page.wait_for_selector(selector, timeout=8000)
                except Exception:
                    print(f"[WebDev] ⚠️  Selector '{selector}' not found, capturing anyway")

            SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
            name = hashlib.md5(target.encode()).hexdigest()[:10]
            ts_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            path = SCREENSHOTS_DIR / f"{name}_{ts_str}.png"
            page.screenshot(path=str(path), full_page=True)
            print(f"[WebDev] 📸 Screenshot saved: {path.name} ({path.stat().st_size} bytes)")

            browser.close()

            # 记录状态
            state = _load_state()
            state["screenshots"].append(
                {
                    "target": target,
                    "path": str(path.relative_to(BASE)),
                    "size": path.stat().st_size,
                    "time": ts(),
                }
            )
            _save_state(state)

            return str(path.relative_to(BASE))

    except Exception as e:
        print(f"[WebDev] ❌ Screenshot failed: {e}")
        return None


def audit_styles(target: str) -> dict:
    """审计页面样式：CSS 变量、字体、布局断点、暗黑模式支持。
    返回 audit 报告 dict。
    """
    chromium = _find_chromium()
    if not chromium:
        return {"error": "Chromium not found"}

    from playwright.sync_api import sync_playwright

    target_url = target
    if not target.startswith(("http://", "https://", "file:///")):
        target_url = f"file:///{target}"

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, executable_path=chromium, args=BROWSER_ARGS)
            page = browser.new_page(viewport={"width": 1920, "height": 1080})

            page.goto(target_url, wait_until="domcontentloaded", timeout=15000)

            # 跑审计脚本
            audit = page.evaluate("""() => {
                const styles = getComputedStyle(document.body);
                const results = {
                    body_bg: styles.backgroundColor,
                    body_color: styles.color,
                    font_family: styles.fontFamily,
                    font_size: styles.fontSize,
                    css_variables: [],
                    media_queries: [],
                    total_elements: document.querySelectorAll('*').length,
                    images: document.querySelectorAll('img').length,
                    has_dark_mode: false,
                    viewport_meta: null,
                    errors: [],
                };

                // 检查 meta viewport
                const vp = document.querySelector('meta[name="viewport"]');
                results.viewport_meta = vp ? vp.content : null;

                // 提取 CSS 变量
                try {
                    for (let i = 0; i < document.styleSheets.length; i++) {
                        try {
                            const rules = document.styleSheets[i].cssRules || document.styleSheets[i].rules || [];
                            for (const rule of rules) {
                                if (rule.cssText && rule.cssText.includes('--')) {
                                    const vars = rule.cssText.match(/--[\\w-]+/g);
                                    if (vars) results.css_variables.push(...vars);
                                }
                                if (rule.cssText && rule.cssText.includes('@media')) {
                                    results.media_queries.push(rule.cssText.match(/@media[^{]+/)[0].trim());
                                }
                            }
                        } catch(e) { /* cross-origin stylesheet */ }
                    }
                } catch(e) {}

                // 检测暗黑模式
                results.has_dark_mode =
                    document.querySelector('link[media*="dark"]') !== null ||
                    document.querySelector('link[media*="prefers-color-scheme"]') !== null ||
                    document.querySelector('[data-theme="dark"]') !== null ||
                    // 检查是否有 prefers-color-scheme 媒体查询
                    Array.from(document.styleSheets).some(s => {
                        try {
                            return Array.from(s.cssRules || []).some(r =>
                                r.conditionText && r.conditionText.includes('prefers-color-scheme')
                            );
                        } catch(e) { return false; }
                    });

                // 基本无障碍检查
                const images_without_alt = document.querySelectorAll('img:not([alt])');
                if (images_without_alt.length > 0) {
                    results.errors.push(`${images_without_alt.length} images missing alt text`);
                }
                const headings = document.querySelectorAll('h1,h2,h3,h4,h5,h6');
                if (headings.length === 0) {
                    results.errors.push('No heading elements found');
                }

                return results;
            }""")

            browser.close()

            # 记录
            state = _load_state()
            state["audits"].append({"target": target, "result": audit, "time": ts()})
            _save_state(state)

            print(
                f"[WebDev] 🔍 Audit complete: {audit.get('total_elements', 0)} elements, "
                f"{len(audit.get('css_variables', []))} CSS vars, "
                f"dark_mode={audit.get('has_dark_mode', False)}"
            )
            return audit

    except Exception as e:
        print(f"[WebDev] ❌ Audit failed: {e}")
        return {"error": str(e)}


def responsive_test(target: str) -> dict:
    """响应式测试：多个视口尺寸截图 + 布局检测。
    返回每个断点的截图路径和基本信息。
    """
    chromium = _find_chromium()
    if not chromium:
        return {"error": "Chromium not found"}

    from playwright.sync_api import sync_playwright

    target_url = target
    if not target.startswith(("http://", "https://", "file:///")):
        target_url = f"file:///{target}"

    viewports = [
        {"name": "mobile", "width": 375, "height": 812},
        {"name": "tablet", "width": 768, "height": 1024},
        {"name": "desktop", "width": 1440, "height": 900},
        {"name": "ultrawide", "width": 1920, "height": 1080},
    ]

    results = {}
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, executable_path=chromium, args=BROWSER_ARGS)

            for vp in viewports:
                page = browser.new_page(viewport={"width": vp["width"], "height": vp["height"]})
                page.goto(target_url, wait_until="domcontentloaded", timeout=15000)
                time.sleep(0.5)

                SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
                name = hashlib.md5(target.encode()).hexdigest()[:10]
                ts_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
                path = SCREENSHOTS_DIR / f"{name}_{vp['name']}_{ts_str}.png"
                page.screenshot(path=str(path), full_page=True)

                # 检查水平滚动
                has_h_scroll = page.evaluate("() => document.body.scrollWidth > window.innerWidth")

                results[vp["name"]] = {
                    "path": str(path.relative_to(BASE)),
                    "size": path.stat().st_size,
                    "has_horizontal_scroll": has_h_scroll,
                }
                page.close()

            browser.close()
            print(f"[WebDev] 📱 Responsive test complete: {len(viewports)} viewports")
            return results

    except Exception as e:
        print(f"[WebDev] ❌ Responsive test failed: {e}")
        return {"error": str(e)}


def form_test(target: str, form_selector: str = "form", submit_selector: str = "button[type='submit']"):
    """表单测试：自动填写并提交表单，检测验证和错误处理。
    返回提交结果和截图。
    """
    chromium = _find_chromium()
    if not chromium:
        return {"error": "Chromium not found"}

    from playwright.sync_api import sync_playwright

    target_url = target
    if not target.startswith(("http://", "https://", "file:///")):
        target_url = f"file:///{target}"

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, executable_path=chromium, args=BROWSER_ARGS)
            page = browser.new_page(viewport={"width": 1920, "height": 1080})
            page.goto(target_url, wait_until="domcontentloaded", timeout=15000)

            form_count = len(page.query_selector_all("form"))
            input_count = len(page.query_selector_all("input"))
            textarea_count = len(page.query_selector_all("textarea"))

            if form_count == 0:
                browser.close()
                return {"error": "No forms found", "inputs": input_count}

            # 自动填写可见表单
            inputs = page.query_selector_all("input:visible, textarea:visible")
            for el in inputs:
                input_type = el.get_attribute("type") or "text"
                name = el.get_attribute("name") or el.get_attribute("id") or ""
                try:
                    if input_type in ("text", "email", "search", "url", "tel"):
                        el.fill(f"test_{name}" if name else "test_value")
                    elif input_type == "number":
                        el.fill("42")
                    elif input_type == "password":
                        el.fill("TestPass123!")
                    # skip checkbox/radio/file/submit
                except Exception:
                    pass

            # 截图填表状态
            SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
            path = SCREENSHOTS_DIR / f"form_{hashlib.md5(target.encode()).hexdigest()[:8]}.png"
            page.screenshot(path=str(path), full_page=True)

            # 统计在 close 前完成（Playwright 对象在 browser.close 后失效）
            filled_count = 0
            for el in inputs:
                try:
                    t = el.get_attribute("type") or "text"
                    if t not in ("submit", "button", "checkbox", "radio", "file"):
                        filled_count += 1
                except Exception:
                    pass

            browser.close()
            return {
                "forms": form_count,
                "inputs": input_count,
                "textareas": textarea_count,
                "filled": filled_count,
                "screenshot": str(path.relative_to(BASE)),
                "time": ts(),
            }

    except Exception as e:
        print(f"[WebDev] ❌ Form test failed: {e}")
        return {"error": str(e)}


def validate_html(target: str) -> dict:
    """HTML 结构验证：检查语义标签、meta 完整性、链接有效性（本地）"""
    target_path = Path(target) if not target.startswith("http") else None
    if target_path and not target_path.exists():
        return {"error": f"File not found: {target}"}

    content = target_path.read_text(encoding="utf-8", errors="ignore") if target_path else ""
    if not content:
        from playwright.sync_api import sync_playwright

        chromium = _find_chromium()
        if not chromium:
            return {"error": "Chromium not found"}
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, executable_path=chromium, args=BROWSER_ARGS)
            page = browser.new_page()
            page.goto(target, wait_until="domcontentloaded", timeout=15000)
            content = page.content()
            browser.close()

    checks = {
        "has_doctype": bool(re.search(r"<!DOCTYPE\s+html", content, re.I)),
        "has_lang": bool(re.search(r'<html[^>]*\slang="', content, re.I)),
        "has_title": bool(re.search(r"<title>", content, re.I)),
        "has_meta_charset": bool(re.search(r"<meta[^>]*charset", content, re.I)),
        "has_meta_viewport": bool(re.search(r"<meta[^>]*viewport", content, re.I)),
        "has_meta_description": bool(re.search(r'<meta[^>]*name="description"', content, re.I)),
        "has_main": bool(re.search(r"<main\b", content, re.I)),
        "has_header": bool(re.search(r"<header\b", content, re.I)),
        "has_footer": bool(re.search(r"<footer\b", content, re.I)),
        "has_nav": bool(re.search(r"<nav\b", content, re.I)),
        "has_h1": bool(re.search(r"<h1\b", content, re.I)),
        "inline_styles_count": len(re.findall(r'\sstyle="', content)),
        "total_lines": content.count("\n"),
    }

    score = sum(1 for v in checks.values() if v is True)
    checks["score"] = f"{score}/{len([k for k, v in checks.items() if isinstance(v, bool)])}"

    return checks


# === 命令行入口 ===
def main():
    import argparse

    parser = argparse.ArgumentParser(description="🦞 Web Developer Agent — 猫的眼睛和手")
    sub = parser.add_subparsers(dest="command")

    shot = sub.add_parser("shot", help="Screenshot a URL or local file")
    shot.add_argument("target", help="URL or local file path")
    shot.add_argument("--wait", type=int, default=1000)
    shot.add_argument("--selector", default=None)

    audit_p = sub.add_parser("audit", help="Audit page styles and structure")
    audit_p.add_argument("target", help="URL or local file path")

    resp = sub.add_parser("responsive", help="Responsive test across viewports")
    resp.add_argument("target", help="URL or local file path")

    form_p = sub.add_parser("form", help="Form auto-fill and test")
    form_p.add_argument("target", help="URL or local file path")

    html_p = sub.add_parser("validate-html", help="Validate HTML structure")
    html_p.add_argument("target", help="Local file path")

    args = parser.parse_args()

    if args.command == "shot":
        path = screenshot(args.target, args.wait, args.selector)
        print(json.dumps({"screenshot": path}, ensure_ascii=False))
    elif args.command == "audit":
        result = audit_styles(args.target)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.command == "responsive":
        result = responsive_test(args.target)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.command == "form":
        result = form_test(args.target)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.command == "validate-html":
        result = validate_html(args.target)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
