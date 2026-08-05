#!/usr/bin/env python3
"""test_self_healing.py — Diagnosis→Fix→Verify self-healing loop demo.

Proves the pipeline: yaml-linter finds error -> Agnes LLM fixes it ->
yaml-linter verifies (exit 0 = evolved).

Usage:
  python test_self_healing.py              # run the demo on the demo poison file
  python test_self_healing.py <file>       # self-heal an arbitrary yaml/json file
"""

import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts.agnes_client import call_llm  # zero-cost agnes LLM client

PROJECT = Path(__file__).resolve().parent.parent
LINTER = PROJECT / "skills" / "yaml-linter" / "run.py"
DEMO_FILE = PROJECT / "skills" / "broken-config-demo" / "_meta.json"


def diagnose(target):
    """Run yaml-linter --json; return (rc, parsed_json)."""
    r = subprocess.run([sys.executable, str(LINTER), str(target), "--json"],
                       capture_output=True, text=True, timeout=30)
    try:
        data = json.loads(r.stdout)
    except json.JSONDecodeError:
        data = {"summary": {"error": 0, "warning": 0}, "files": []}
    return r.returncode, data


def ask_llm_to_fix(original, evidence):
    """Send original + linter evidence to Agnes; return fixed content."""
    prompt = (
        "你是配置文件修复专家。下面是我的 YAML/JSON 配置文件，linter 报了语法错误。\n"
        "请修复它并返回**修复后的完整文件内容**，保持原有结构和语义不变，只是修掉错误。\n"
        "只输出修复后的文件内容，不要任何解释，不要用代码块包裹。\n\n"
        "===== 原文件内容 =====\n"
        f"{original}\n"
        "===== Linter 诊断（JSON） =====\n"
        f"{json.dumps(evidence, ensure_ascii=False)}\n"
    )
    return call_llm(prompt, max_tokens=1024)


def self_heal(target, verbose=True):
    print(f"\n{'='*60}\n自愈目标: {target}\n{'='*60}")

    original = Path(target).read_text(encoding="utf-8")
    print(f"[1] 读取原始文件 ({len(original)}B)")

    rc, diag = diagnose(target)
    n_err = diag.get("summary", {}).get("error", 0)
    print(f"[2] yaml-linter 诊断: rc={rc}, errors={n_err}")
    if rc == 0 and n_err == 0:
        print("    ✅ 文件已健康，无需修复")
        return True
    if verbose and diag.get("files"):
        for d in diag["files"][0].get("diagnostics", [])[:3]:
            print(f"    - [Line {d['line']}, Col {d['column']}] {d['status'].upper()}: {d['reason']}")

    print("[3] 求助 Agnes LLM 修复...")
    try:
        fixed = ask_llm_to_fix(original, diag)
    except Exception as e:
        print(f"    ❌ LLM 调用失败: {e}")
        return False
    if not fixed or len(fixed) < 5:
        print("    ❌ LLM 返回内容异常，放弃")
        return False

    # 应用修复（原子写回）
    print("[4] 应用修复...")
    Path(target).write_text(fixed.rstrip("\n") + "\n", encoding="utf-8")

    # 二次验证
    rc2, diag2 = self_heal_verify(target)
    n_err2 = diag2.get("summary", {}).get("error", 0)

    if rc2 == 0 and n_err2 == 0:
        print("[5] ✅ 二次验证通过 — 进化成功！")
        print(f"    修复后内容:\n{fixed.rstrip()}\n")
        return True
    else:
        print(f"[5] ❌ 二次验证仍失败 (rc={rc2}, errors={n_err2})，回滚到原始内容")
        Path(target).write_text(original, encoding="utf-8")
        return False


def self_heal_verify(target):
    return diagnose(target)


if __name__ == "__main__":
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else DEMO_FILE
    ok = self_heal(target)
    print(f"\n>>> 自愈闭环 {'成功 💚' if ok else '失败 ❤️'}")
    sys.exit(0 if ok else 1)
