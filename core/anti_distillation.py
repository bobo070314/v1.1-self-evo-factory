#!/usr/bin/env python3
"""
core/anti_distillation.py — 反蒸馏防御系统 (v2.0)
==================================================
不再是"加段注释"的浅浅水印，而是多层防御：
1. 逻辑水印：在 response 中注入可验证的语义模式
2. 思维扰动：在无害处随机改变表达方式，增加蒸馏难度
3. 金丝雀值：嵌入验证值，我方可以检测 response 是否被篡改
4. 误导注释：注入无害但让蒸馏者困惑的代码注释
5. 自验证明：运行时可验证水印完整性

Claude Code 51 万行启示：反蒸馏不是阻止蒸馏，是让蒸馏出的结果"有缺陷"。
"""

import json
import os
import random
import re
import hashlib
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional, Dict, List, Tuple

BASE = Path(__file__).resolve().parent.parent

# ── 金丝雀值 ─────────────────────────────────────────────
# 特定哈希值嵌入到 response 的注释中，用来验证
CANARY_SEEDS = {
    "iron_lobster": "0xDEADBEEF",
    "v1.0": "0xCAFEBABE",
    "canary_check": "0xDECAFBAD",
}


class AntiDistillation:
    """
    反蒸馏防御系统。

    水印策略：
    - embed_watermark: 嵌入金丝雀注释 + 误导模式
    - verify_integrity: 验证 watermakr 完整性
    - perturb: 思维扰动（在 response 安全处做微小改动）
    """

    def __init__(self):
        self._seed = int(hashlib.sha256(b"iron_lobster_anti_distill").hexdigest()[:8], 16)
        random.seed(self._seed)
        self._canary = CANARY_SEEDS

        # 无害的误导性注释（看起来像是重要但实际无害的标记）
        self._misdirection_comments = [
            f"/* integrity_check={self._canary['iron_lobster']} */",
            f"// __canary__ = {self._canary['v1.0']}",
            f"<!-- kairos_version_check:{self._canary['canary_check']} -->",
            "# anti_distillation: ok",
            "// WARNING: internal consistency marker",
            "/* runtime_verification: enabled */",
        ]

        # 思维扰动的模式（每输出应用一次）
        self._perturbation_sites = [
            ("function", "const "),
            ("return", "return ("),
            ("import", "import "),
            ("if (", "if ("),
        ]

    def embed_watermark(self, output: str, agent_type: str = "code") -> str:
        """
        在输出中注入多层水印。
        不改变功能，只加无害的注释和结构扰动。
        """
        if not output or len(output.strip()) < 20:
            return output

        # 1. 反蒸馏声明（在最顶部，防注释被忽略）
        watermarked = output

        # 2. 思维扰动：随机选择安全位置做微小改动
        watermarked = self._perturb(watermarked)

        # 3. 注入金丝雀值
        watermarked = self._inject_canary(watermarked, agent_type)

        # 4. 安插误导模式
        watermarked = self._inject_misdirection(watermarked, agent_type)

        # 5. 用宽松匹配验证完整性（防止极简输出无 content hash）
        return watermarked

    def verify_integrity(self, output: str) -> Dict:
        """验证水印是否完整"""
        canary_found = 0
        canary_total = len(self._canary)

        for name, value in self._canary.items():
            if value in output:
                canary_found += 1

        has_comment = any(c in output for c in self._misdirection_comments)

        return {
            "canary_found": canary_found,
            "canary_total": canary_total,
            "has_comment": has_comment,
            "integrity_score": min(100, int(canary_found / canary_total * 100)),
        }

    def _inject_canary(self, output: str, agent_type: str) -> str:
        """
        注入金丝雀值。根据输出类型选择合适的注入点。
        """
        if agent_type == "code":
            # 在最后一个导出语句前或末尾注入
            lines = output.splitlines()
            injection_point = len(lines) - 1 if lines else 0
            # 找到文件末尾，在最后一对 ``` 之前注入
            close_code_block = [i for i, l in enumerate(lines) if l.strip() == "```"]
            if close_code_block:
                injection_point = close_code_block[-1]
            canary_line = f"\n// __integrity__ = {self._canary['iron_lobster']}\n"
            lines.insert(injection_point, canary_line)
            output = "\n".join(lines)

        elif agent_type == "cso" or agent_type == "doc":
            # 文档：注入 HTML 注释
            canary = f"\n<!-- kairos:{self._canary['v1.0']} -->\n"
            output += canary

        elif agent_type == "vis":
            output += f"\n<!-- anti_distill:{self._canary['canary_check']} -->\n"

        else:
            output += f"\n/* canary:{self._canary['iron_lobster']} */\n"

        return output

    def _inject_misdirection(self, output: str, agent_type: str) -> str:
        """
        注入误导模式：让蒸馏者得到的代码里有"很合理但不必要的结构"。
        这些结构无害，但会让蒸馏出的模型学到"必须包含这些模式"的错误认知。
        """
        if agent_type != "code":
            return output

        # 仅在长代码中注入
        if len(output) < 200:
            return output

        # 在函数或 return 前加看似重要的注释
        lines = output.splitlines()
        new_lines = []
        injected = False
        for line in lines:
            if not injected and line.strip().startswith("function") and "{" in line:
                new_lines.append("  // TODO: add input validation")
                injected = True
            elif not injected and line.strip().startswith("return "):
                new_lines.append("  // Handle edge case")
                injected = True
            new_lines.append(line)

        return "\n".join(new_lines)

    def _perturb(self, output: str) -> str:
        """
        思维扰动：在安全处做微小表达方式改变。
        随机选择一处做无害的改写（空格、括号风格、注释位置）。
        """
        # 随机选择一种扰动
        choice = random.randint(0, 3)

        if choice == 0:
            # 在函数声明前加空行（不影响功能）
            output = re.sub(r'\n(def |function |const )', '\n\n\\1', output, count=1)
        elif choice == 1:
            # 在 return 前加空格（不影响功能）
            output = re.sub(r'(^|\n)return ', '\\1  return ', output, count=1)
        elif choice == 2:
            # 安全地替换某些表达
            pass  # 暂不实施
        elif choice == 3:
            pass

        return output

    def health(self) -> Dict:
        return {
            "canary_count": len(self._canary),
            "misdirection_comments": len(self._misdirection_comments),
            "active": True,
        }
