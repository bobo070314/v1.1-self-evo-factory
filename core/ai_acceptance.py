#!/usr/bin/env python3
"""
core/ai_acceptance.py — AI 驱动的深度验收 (v1.0)
==============================================
不再是字符串硬检查 12345678，而是用 LLM 做多维语义审查。

设计：
- 快速字符串检查（前置过滤，继承 old acceptance）
- LLM 语义审查（深度检查逻辑/安全/风格/完整性）
- 审查结果结构化输出（等级 + 原因 + 修复建议）
- 支持 code/vis/cso 三类 agent 不同审查标准
- 审查结果可用于自进化引擎的评分输入

Claude Code 51 万行启示：验收不是 check() 一个函数，是多层叠起来的质量体系。
"""

import json
import os
import re
import sys
from pathlib import Path
from typing import Optional, Dict, List, Any, Tuple

BASE = Path(__file__).resolve().parent.parent


# ── 快速字符串检查 (前置过滤) ─────────────────────────────

class FastGate:
    """快速、确定性的前置检查。快且准，不调用 LLM。"""

    FAIL = "fail"
    WARN = "warn"
    PASS = "pass"

    @staticmethod
    def check_all(output: str, agent_type: str) -> Dict:
        """综合检查，返回 {passed, messages, score_penalty}"""
        failures = []
        warnings = []
        total_penalty = 0

        if agent_type == "cso":
            f, w, p = FastGate._check_cso(output)
            failures.extend(f)
            warnings.extend(w)
            total_penalty += p
        elif agent_type == "vis":
            f, w, p = FastGate._check_vis(output)
            failures.extend(f)
            warnings.extend(w)
            total_penalty += p
        elif agent_type == "code":
            f, w, p = FastGate._check_code(output)
            failures.extend(f)
            warnings.extend(w)
            total_penalty += p
        else:
            f, w, p = FastGate._check_generic(output)
            failures.extend(f)
            warnings.extend(w)
            total_penalty += p

        return {
            "passed": len(failures) == 0,
            "verdict": "PASS" if len(failures) == 0 else "FAIL",
            "failures": failures,
            "warnings": warnings,
            "score_penalty": total_penalty,
        }

    @staticmethod
    def _check_cso(output: str) -> Tuple[List[str], List[str], int]:
        failures, warnings, penalty = [], [], 0
        required = {"用户画像": ["用户画像", "persona"], "竞争分析": ["竞争分析", "competitive", "竞品"],
                    "功能边界": ["功能边界", "scope", "out of scope"]}
        for section, keywords in required.items():
            if not any(kw in output for kw in keywords):
                failures.append(f"缺少必需章节: {section}")
                penalty += 15
        if len(output) < 200:
            failures.append("输出太短 (<200字符)")
            penalty += 10
        vague = ["可以考虑", "将来", "maybe", "TODO"]
        for word in vague:
            if word in output:
                warnings.append(f"模糊词: {word}")
                penalty += 2
        return failures, warnings, penalty

    @staticmethod
    def _check_vis(output: str) -> Tuple[List[str], List[str], int]:
        failures, warnings, penalty = [], [], 0
        # 间距检测
        if re.search(r"gap-[234]", output) and not re.search(r"gap-[6789]", output):
            failures.append("禁用 gap-2/3/4，需 gap-6+")
            penalty += 15
        # transition-all 禁止
        if "transition-all" in output:
            failures.append("禁用 transition-all")
            penalty += 10
        # 响应式
        if "sm:" not in output and "md:" not in output and "lg:" not in output:
            warnings.append("缺少响应式断点")
            penalty += 5
        # focus 环
        if re.search(r"<(button|input|a)", output) and "focus:" not in output:
            failures.append("交互元素缺少 focus:ring")
            penalty += 15
        return failures, warnings, penalty

    @staticmethod
    def _check_code(output: str) -> Tuple[List[str], List[str], int]:
        failures, warnings, penalty = [], [], 0
        dangerous = [
            (r"rm\s+-rf\s+/", "rm -rf /"),
            (r"os\.remove\(['\"]/", "os.remove /"),
            (r"subprocess\(.*shell=True.*[,\)]", "subprocess shell=True"),
            (r"eval\([^)]*\)", "eval()"),
            (r"exec\([^)]*\)", "exec()"),
        ]
        for pat, msg in dangerous:
            if re.search(pat, output):
                failures.append(f"危险代码: {msg}")
                penalty += 20
        if "TODO" in output:
            warnings.append("包含 TODO")
            penalty += 2
        if output.count("{") != output.count("}"):
            failures.append("花括号不匹配")
            penalty += 10
        return failures, warnings, penalty

    @staticmethod
    def _check_generic(output: str) -> Tuple[List[str], List[str], int]:
        failures, warnings, penalty = [], [], 0
        if not output or len(output.strip()) < 10:
            failures.append("输出为空或过短")
            penalty += 30
        if "TODO" in output:
            warnings.append("包含 TODO")
            penalty += 2
        if len(output) > 200:
            if output[:50] in output[100:]:
                failures.append("疑似橡皮图章")
                penalty += 20
        return failures, warnings, penalty


# ── LLM 语义审查 ─────────────────────────────────────────────

class DeepAcceptance:
    """用 LLM 做深度语义审查，弥补字符串检查的盲区。"""

    @staticmethod
    def build_review_prompt(output: str, agent_type: str, fast_result: Dict) -> str:
        """构建审查 prompt"""
        fast_msg = ""
        if fast_result.get("failures"):
            fast_msg = "快速检测发现的问题:\n" + "\n".join(f"- {f}" for f in fast_result["failures"])
        if fast_result.get("warnings"):
            if fast_msg:
                fast_msg += "\n"
            fast_msg += "警告:\n" + "\n".join(f"- {w}" for w in fast_result["warnings"])

        dimensions = {
            "code": "安全性、逻辑正确性、代码质量、风格一致性、性能影响",
            "cso": "完整性、逻辑连贯性、数据支撑、结构合理性",
            "vis": "布局合理性、可访问性、响应式适配、色彩使用",
        }

        return (
            f"你是一名资深代码/文档审查员。请审查以下{agent_type.upper()}输出。\n\n"
            f"检查维度: {dimensions.get(agent_type, '质量、安全、完整性')}\n\n"
        )

    @staticmethod
    def parse_review(text: str) -> Dict:
        """解析 LLM 返回的审查结果"""
        score = 70
        issues = []
        # 尝试从文本中提取评分
        score_match = re.search(r"评分[：:]\s*(\d+)(?:\s*分?)?", text)
        if score_match:
            score = min(100, max(0, int(score_match.group(1))))
        # 提取问题
        issue_lines = re.findall(r"(?:问题|缺陷|建议)[：:]\s*(.+)$", text, re.MULTILINE)
        for line in issue_lines:
            issues.append({"msg": line.strip(), "severity": detect_severity(line)})
        # 从[]或-列表中提取
        list_items = re.findall(r"(?:^|\n)\s*(?:-|\d+[.)])\s*(.+)$", text, re.MULTILINE)
        for item in list_items:
            if any(w in item.lower() for w in ["问题", "缺陷", "错误", "修复", "改进", "不安全", "风险"]):
                issues.append({"msg": item.strip(), "severity": detect_severity(item)})

        return {"score": score, "issues": issues, "raw": text[:200]}

    def review(self, output: str, agent_type: str, fast_result: Optional[Dict] = None,
               cloud_fn=None) -> Dict:
        """完整审查：快速检查 + LLM 深度检查"""
        # 快速检查
        fast = fast_result or FastGate.check_all(output, agent_type)

        # 如果快速检查已经严重失败，直接返回（不浪费 LLM）
        if not fast["passed"] and fast["score_penalty"] >= 50:
            return {**fast, "llm_review": None, "final_score": max(0, 70 - fast["score_penalty"])}

        # LLM 审查
        llm_result = None
        if cloud_fn:
            try:
                prompt = DeepAcceptance.build_review_prompt(output, agent_type, fast)
                raw = cloud_fn(prompt)
                if raw:
                    llm_result = DeepAcceptance.parse_review(raw)
            except Exception:
                pass

        # 综合评分
        base_score = llm_result["score"] if llm_result else 70
        final_score = max(0, base_score - fast["score_penalty"])

        return {
            "passed": final_score >= 60,
            "verdict": "PASS" if final_score >= 60 else "FAIL",
            "fast_check": fast,
            "llm_review": llm_result,
            "final_score": final_score,
            "issues": (llm_result.get("issues", []) if llm_result else []) + [
                {"msg": f, "severity": "high", "source": "fast_check"}
                for f in fast.get("failures", [])
            ],
        }


def detect_severity(text: str) -> str:
    text_lower = text.lower()
    if any(w in text_lower for w in ["critical", "严重", "高危", "致命", "安全"]):
        return "critical"
    if any(w in text_lower for w in ["high", "高", "dangerous", "危险"]):
        return "high"
    if any(w in text_lower for w in ["medium", "中", "warning", "建议"]):
        return "medium"
    return "low"


# ── 统一入口 ─────────────────────────────────────────────

class AIAcceptanceGate:
    """整合快速检查 + LLM 深度审查的统一入口"""

    def __init__(self, cloud_fn=None):
        self._fast = FastGate()
        self._deep = DeepAcceptance()
        self._cloud = cloud_fn

    def check(self, output: str, agent_type: str = "code") -> Dict:
        return self._deep.review(output, agent_type, fast_result=None, cloud_fn=self._cloud)

    def health(self) -> Dict:
        return {
            "fast_check_agents": ["cso", "vis", "code", "generic"],
            "llm_available": self._cloud is not None,
        }
