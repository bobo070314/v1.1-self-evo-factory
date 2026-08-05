#!/usr/bin/env python3
"""
core/self_evolve.py — 自我迭代闭环引擎 (v2.0)
===========================================
双引擎：
- SelfEvolver: 评分→修复→重执行→回滚（生成物质量把关）
- SelfHealer:  泛化自愈协议 Scan→Diagnose→Fix(LLM)→Verify
  （只要有 verifier/linter，就能自动修——本质：证据驱动的手术）

CLI:
  python core/self_evolve.py --path <file>            # 体检+自愈
  python core/self_evolve.py --path <file> --no-llm   # 只体检
  python core/self_evolve.py --tree <dir> --ext yaml  # 批量自愈

设计思想：
- 评分系统：0-100 分，多层维度（语法、风格、安全、逻辑、完整性）
- 修复策略：针对不同类型的缺陷有不同的修复模式
- 回滚保护：修复后质量下降时自动回滚到上一个版本
- 历史追踪：记录每次迭代的变更，形成进化日志
- 策略选择：根据缺陷类型自动选择最优修复策略

Claude Code 51 万行启示：真正的闭环不是 retry(3)，而是完整的进化子系统。
"""

import json
import os
import re
import sys
import time
import copy
import traceback
import subprocess
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional, Dict, List, Tuple, Any

TZ = timezone(timedelta(hours=8))
BASE = Path(__file__).resolve().parent.parent
EVO_LOG_DIR = BASE / "data" / "evolution"
EVO_LOG_DIR.mkdir(parents=True, exist_ok=True)


# ── 质量评分器 ─────────────────────────────────────────────

class QualityScorer:
    """多层质量评分。不是二值化 pass/fail，而是 0-100 分多维评分。"""

    # 各维度权重
    WEIGHTS = {
        "syntax": 0.20,
        "security": 0.25,
        "style": 0.10,
        "completeness": 0.20,
        "logic": 0.15,
        "performance": 0.10,
    }

    @classmethod
    def score(cls, output: str, agent_type: str = "code") -> Dict:
        """返回分数和详细原因"""
        scores = {}

        # 语法分
        syntax_score = cls._score_syntax(output)
        scores["syntax"] = syntax_score

        # 安全分
        security_score = cls._score_security(output)
        scores["security"] = security_score

        # 风格分
        style_score = cls._score_style(output, agent_type)
        scores["style"] = style_score

        # 完整性分
        completeness_score = cls._score_completeness(output, agent_type)
        scores["completeness"] = completeness_score

        # 逻辑分
        logic_score = cls._score_logic(output, agent_type)
        scores["logic"] = logic_score

        # 性能分（代码特定的额外维度）
        performance_score = cls._score_performance(output, agent_type)
        scores["performance"] = performance_score

        # 加权总分
        total = sum(scores.get(k, 0) * cls.WEIGHTS.get(k, 0) for k in cls.WEIGHTS)
        total = round(total, 1)

        # 缺陷分类
        issues = cls._classify_issues(output, agent_type)

        return {
            "total": min(100, max(0, total)),
            "detail": scores,
            "issues": issues,
            "sources": ["quality_scorer"],
        }

    @staticmethod
    def _score_syntax(output: str) -> float:
        """语法检查：代码/JSON 等是否有明显的语法错误"""
        if not output or len(output.strip()) < 5:
            return 10.0
        score = 100.0
        # 检查代码裁剪（截断)
        if output.strip().endswith("...") or output.strip().endswith("```"):
            score -= 30
        # 检查括号不匹配
        if output.count("{") != output.count("}"):
            score -= 20
        if output.count("(") != output.count(")"):
            score -= 15
        if output.count("[") != output.count("]"):
            score -= 10
        # 检查 JSON 格式错误
        if "{" in output and "}" in output:
            try:
                json.loads(output)
            except (json.JSONDecodeError, ValueError):
                pass  # 纯 JSON 才有问题
        # JavaScript/Python 常见的语法问题
        if "=> {" in output and "}" not in output.split("=> {")[-1]:
            score -= 10
        return max(0, score)

    # SQL 注入检测正则：字符串拼接 SELECT/INSERT/UPDATE/DELETE + 变量
    _SQLI_PATTERNS = [
        r"(SELECT|INSERT\s+INTO|UPDATE|DELETE\s+FROM)\b[^'\"`]*\b(AND|OR|WHERE)\b[^'\"`]*\"\s*\+",
        r"f['\"][^'\"]*(SELECT|INSERT|UPDATE|DELETE)[^'\"]*\{[^'\"]*\}['\"]",
        r"(query|sql|cmd)\s*=\s*['\"][^'\"]*(SELECT|INSERT|UPDATE|DELETE)[^'\"]*['\"]\s*\+",
    ]

    @staticmethod
    def _score_security(output: str) -> float:
        """安全检测"""
        score = 100.0
        dangerous = [
            (r"rm\s+-rf\s+/\s+", -50),
            (r"('|\")?\s*(SELECT\s+[^;\n\"']*FROM\s+[\w.]+)[^\n]*\+\s*[A-Za-z_][\w.]*", -35),  # SQL 字符串拼接注入
            (r"f['\"][^'\"]*(SELECT|INSERT|UPDATE|DELETE)[^'\"]*\{[^'\"]*\}['\"]", -35),  # f-string SQL 注入
            (r"os\.system\([^)]*input", -40),
            (r"subprocess\(.*shell=True", -35),
            (r"exec\([^)]*\)", -30),
            (r"eval\([^)]*\)", -30),
            (r"pickle\.loads\([^)]*\)", -20),
            (r"innerHTML\s*=", -15),
            (r"dangerouslySetInnerHTML", -15),
            (r"document\.write\([^)]*\)", -15),
            (r"//\s*TODO\s*:\s*security", -10),
            (r"password\s*=\s*['\"][^'\"]{1,10}['\"]", -20),
            (r"api_key\s*=\s*['\"][^'\"]{10,}['\"]", -20),
            (r"secret\s*=\s*['\"][^'\"]{5,}['\"]", -20),
            (r"token\s*=\s*['\"][^'\"]{10,}['\"]", -15),
        ]
        for pattern, penalty in dangerous:
            if re.search(pattern, output, re.IGNORECASE):
                score += penalty
        return max(0, score)

    @staticmethod
    def _score_style(output: str, agent_type: str) -> float:
        """风格质量"""
        score = 70.0  # 基础分，能加能减
        # 加分：好的代码风格
        if "type" in output or "interface" in output:
            score += 5
        if "useEffect" in output or "useState" in output:
            score += 3
        if "try:" in output or "try {" in output:
            score += 5
        if "//" in output or "/*" in output:
            score += 3
        if "ErrorBoundary" in output or "error" in output.lower():
            score += 3
        # 减分：不好的风格
        if "var " in output:
            score -= 10
        if "any" in output and "as any" in output:
            score -= 5
        if "console.log(" in output:
            score -= 5
        # 代码/文档比率
        code_lines = sum(1 for l in output.splitlines() if l.strip() and not l.strip().startswith(("#", "//", "/*", "* ", "- ", "> ")))
        doc_lines = sum(1 for l in output.splitlines() if l.strip().startswith(("#", "//", "/*")))
        total = code_lines + doc_lines
        if total > 0 and code_lines / total < 0.3:
            score -= 10  # 注释过多，代码太少
        return min(100, max(0, score))

    @staticmethod
    def _score_completeness(output: str, agent_type: str) -> float:
        """完整性：输出是否包含核心部分"""
        score = 50.0  # 基础分
        if not output or len(output.strip()) < 20:
            return 0  # 空输出=0分

        if agent_type == "code":
            if "import" in output or "require(" in output:
                score += 15
            if "export" in output or "module.exports" in output:
                score += 10
            if "return" in output:
                score += 10
            if "function" in output or "const" in output or "=>" in output:
                score += 10
            if len(output) > 200:
                score += 5
            if len(output) > 1000:
                score += 5
        elif agent_type == "cso":
            sections = ["用户画像", "竞争分析", "功能边界", "技术架构", "路线图"]
            found = sum(1 for s in sections if s in output)
            score += found * 10
            if len(output) > 500:
                score += 10
        elif agent_type == "vis":
            if "<!DOCTYPE" in output or "<html" in output:
                score += 10
            if "class=" in output:
                score += 10
            if "tailwind" in output.lower():
                score += 10
            if "responsive" in output.lower() or "md:" in output or "lg:" in output:
                score += 10
        else:
            score += min(30, len(output) / 50)

        return min(100, max(0, score))

    @staticmethod
    def _score_logic(output: str, agent_type: str) -> float:
        """逻辑正确性启发式检查"""
        score = 80.0
        # 矛盾的逻辑
        if "return true" in output and "return false" not in output:
            pass
        if "error" in output.lower() and "catch" not in output.lower() and "try" not in output.lower():
            score -= 10
        # 循环安全
        if "while True" in output and "break" not in output:
            score -= 20
        if "while (" in output and "break" not in output:
            score -= 10
        # 空函数/空方法
        empty_funcs = re.findall(r"def \w+\(.*\):\s*\n\s*(?:pass|return|\.\.\.)", output)
        if empty_funcs:
            score -= len(empty_funcs) * 10
        # 条件判断缺少else
        if "if " in output and "else" not in output:
            score -= 5
        return max(0, score)

    @staticmethod
    def _score_performance(output: str, agent_type: str) -> float:
        """性能质量启发式"""
        score = 80.0
        # React 特定的性能问题
        if "useEffect" in output and "[]" not in output:
            score -= 15  # 无依赖数组的 useEffect
        if "useCallback" in output or "useMemo" in output:
            score += 10
        # 数据库 N+1 模式
        if "forEach" in output and "await" in output:
            score -= 10
        # 大对象内联
        if len(output) > 5000 and "export" in output:
            score -= 5
        return max(0, score)

    @staticmethod
    def _classify_issues(output: str, agent_type: str) -> List[Dict]:
        """将所有的扣分点分类为 issues"""
        issues = []
        # 截断
        if output.strip().endswith("..."):
            issues.append({"type": "syntax", "severity": "critical", "msg": "输出被截断"})
        # 括号
        if output.count("{") != output.count("}"):
            issues.append({"type": "syntax", "severity": "high", "msg": "花括号不匹配"})
        # 安全
        if re.search(r"eval\([^)]*\)", output):
            issues.append({"type": "security", "severity": "critical", "msg": "使用 eval(), 有代码注入风险"})
        if re.search(r"innerHTML\s*=", output):
            issues.append({"type": "security", "severity": "high", "msg": "使用 innerHTML, 有 XSS 风险"})
        if re.search(r"rm\s+-rf", output):
            issues.append({"type": "security", "severity": "critical", "msg": "使用 rm -rf, 危险操作"})
        if re.search(r"('|\")?\s*(SELECT\s+[^;\n\"']*FROM\s+[\w.]+)[^\n]*\+\s*[A-Za-z_][\w.]*", output, re.IGNORECASE):
            issues.append({"type": "security", "severity": "critical", "msg": "SQL 查询使用字符串拼接，存在 SQL 注入风险"})
        if re.search(r"f['\"][^'\"]*(SELECT|INSERT|UPDATE|DELETE)[^'\"]*\{[^'\"]*\}['\"]", output, re.IGNORECASE):
            issues.append({"type": "security", "severity": "high", "msg": "f-string 内嵌 SQL 变量，存在注入风险"})
        # 风格
        if "var " in output:
            issues.append({"type": "style", "severity": "low", "msg": "使用 var, 建议用 const/let"})
        if "TODO" in output:
            issues.append({"type": "completeness", "severity": "low", "msg": "包含 TODO 标记"})
        # 完整性
        if len(output.strip()) < 50:
            issues.append({"type": "completeness", "severity": "high", "msg": "输出过短，可能不完整"})
        return issues


# ── 修复策略引擎 ─────────────────────────────────────────────

class FixEngine:
    """针对不同缺陷类型的修复策略选择器。"""

    STRATEGIES = {
        "syntax": [
            "fix_brackets",
            "fix_truncation",
            "fix_json",
        ],
        "security": [
            "replace_dangerous_patterns",
            "add_sanitization",
            "rewrite_unsafe_api",
        ],
        "style": [
            "convert_var_to_const",
            "add_type_hints",
            "remove_debug_logs",
        ],
        "completeness": [
            "expand_truncated",
            "add_missing_sections",
            "fill_templates",
        ],
        "logic": [
            "add_error_handling",
            "add_null_checks",
            "add_break_conditions",
        ],
        "performance": [
            "optimize_loop",
            "add_memoization",
            "suggest_batching",
        ],
    }

    @staticmethod
    def select_strategies(issues: List[Dict]) -> List[str]:
        """根据缺陷选择修复策略"""
        strategies = set()
        for issue in issues:
            issue_type = issue.get("type", "")
            if issue_type in FixEngine.STRATEGIES:
                strategies.add(FixEngine.STRATEGIES[issue_type][0])
        return list(strategies) if strategies else ["general_review"]

    @staticmethod
    def generate_fix_prompt(original: str, issues: List[Dict], agent_type: str) -> str:
        """生成修复 prompt，告诉 LLM 要修什么"""
        issue_str = "\n".join(f"[{i.get('severity','info').upper()}] {i.get('msg','')}" for i in issues)
        strategies = FixEngine.select_strategies(issues)

        return (
            f"你是一名代码质量工程师。请修复以下输出中的问题。\n\n"
            f"原始输出（{agent_type}）:```\n{original}\n```\n\n"
            f"检测到的问题:\n{issue_str}\n\n"
            f"修复策略: {', '.join(strategies)}\n\n"
            f"规则:\n"
            f"1. 只修改有问题的部分，不要重写整个输出\n"
            f"2. 保持原有功能和风格一致\n"
            f"3. 修复后请完整输出修复版本\n"
            f"4. 不要添加太多新功能\n"
        )


# ── 进化日志 ─────────────────────────────────────────────

class EvolutionLog:
    """记录每次迭代的变更，支持回滚。"""

    def __init__(self):
        self.current_run = None
        self.history = self._load_history()

    def _load_history(self) -> Dict:
        path = EVO_LOG_DIR / "evolution_history.json"
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {"runs": [], "version": 1}

    def _save_history(self):
        path = EVO_LOG_DIR / "evolution_history.json"
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self.history, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def start_run(self, user_input: str, agent_type: str):
        self.current_run = {
            "id": str(int(time.time() * 1000)),
            "started_at": datetime.now(TZ).isoformat(),
            "user_input": user_input[:200],
            "agent_type": agent_type,
            "generations": [],
            "final_score": None,
            "retries": 0,
            "success": False,
            "rolled_back": False,
        }

    def log_generation(self, output: str, score: Dict, strategy: str = "initial"):
        if self.current_run is None:
            return
        self.current_run["generations"].append({
            "iteration": len(self.current_run["generations"]) + 1,
            "score": score["total"],
            "detail": score.get("detail", {}),
            "issues": score.get("issues", []),
            "strategy": strategy,
            "output_preview": output[:200],
            "timestamp": datetime.now(TZ).isoformat(),
        })

    def end_run(self, final_score: float, success: bool, rolled_back: bool = False):
        if self.current_run is None:
            return
        self.current_run["final_score"] = final_score
        self.current_run["success"] = success
        self.current_run["retries"] = len(self.current_run["generations"]) - 1
        self.current_run["rolled_back"] = rolled_back
        self.current_run["ended_at"] = datetime.now(TZ).isoformat()
        self.history["runs"].append(self.current_run)
        # 只保留最近 1000 条
        if len(self.history["runs"]) > 1000:
            self.history["runs"] = self.history["runs"][-1000:]
        self._save_history()
        self.current_run = None

    def get_stats(self) -> Dict:
        runs = self.history.get("runs", [])
        if not runs:
            return {"runs": 0}
        recent = [r for r in runs if r.get("retries", 0) > 0]
        return {
            "runs": len(runs),
            "avg_score": sum(r.get("final_score", 0) or 0 for r in runs) / len(runs),
            "retry_rate": f"{len(recent) / len(runs) * 100:.1f}%" if runs else "0%",
            "rollback_rate": f"{sum(1 for r in runs if r.get('rolled_back')) / len(runs) * 100:.1f}%",
            "total_generations": sum(len(r.get("generations", [])) for r in runs),
        }


# ── 闭环调度器 ─────────────────────────────────────────────

class SelfEvolver:
    """
    自我迭代闭环。

    流程：
    1. 初始生成 → 2. 评分 → 3. 如果分数 < 阈值：修复 → 4. 再评分
    → 5. 直到分数 >= 阈值或达到最大迭代 → 6. 如果最后分数还低于前一代：回滚
    """

    MIN_SCORE = 65      # 最小通过分数
    MAX_ITERATIONS = 5   # 最大迭代次数（太多次浪费 token）
    ROLLBACK_THRESHOLD = 5  # 回滚阈值：如果当前比上一个低超过多少分就回滚

    def __init__(self, llm_chat_fn=None, cloud_fn=None):
        self._llm_chat = llm_chat_fn
        self._cloud = cloud_fn
        self._scorer = QualityScorer()
        self._fix_engine = FixEngine()
        self._log = EvolutionLog()

    def evolve(self, initial_output: str, user_input: str, agent_type: str = "code",
               extra_context: Optional[Dict] = None) -> Tuple[str, Dict]:
        """
        迭代优化输出。
        返回 (优化后的输出, 迭代记录)
        """
        self._log.start_run(user_input, agent_type)

        current = initial_output
        best = current
        best_score = 0
        last_score = 0
        rolled_back = False

        # 初始评分
        score = self._scorer.score(current, agent_type)
        first_score = score["total"]
        self._log.log_generation(current, score, "initial")

        if score["total"] >= self.MIN_SCORE:
            self._log.end_run(score["total"], True)
            return current, {
                "iterations": 1, "final_score": score["total"], "rolled_back": False,
                "issues": score.get("issues", []),
            }

        print(f"  [evolve] 初始分 {score['total']:.1f}/{self.MIN_SCORE}，开始迭代...")

        for i in range(self.MAX_ITERATIONS):
            issues = score.get("issues", [])
            if not issues:
                break  # 没有问题了

            fix_prompt = self._fix_engine.generate_fix_prompt(current, issues, agent_type)
            fixed = self._try_execute_fix(fix_prompt, user_input, agent_type)

            if not fixed or fixed == current or len(fixed.strip()) < 10:
                print(f"  [evolve] 第{i+1}次修复无明显变化，停止")
                break

            current = fixed
            score = self._scorer.score(current, agent_type)
            self._log.log_generation(current, score, f"fix_{i+1}")

            print(f"  [evolve] 第{i+1}次修复后: {score['total']:.1f} 分 ({len(issues)} issues) ...>? 阈值 {self.MIN_SCORE}")

            if score["total"] >= self.MIN_SCORE:
                if score["total"] < last_score:
                    diff = last_score - score["total"]
                    if diff > self.ROLLBACK_THRESHOLD:
                        print(f"  [evolve] 修复导致分数下降 {diff:.1f} 分，回滚到上一版")
                        current = best
                        score["total"] = best_score
                        rolled_back = True
                        break
                break

            if score["total"] > best_score:
                best = current
                best_score = score["total"]

            last_score = score["total"]

        # 最终检查：是否需要回滚
        if not rolled_back and score["total"] < first_score - self.ROLLBACK_THRESHOLD:
            print(f"  [evolve] 最终版本比初版低，回滚到初版")
            current = initial_output
            score["total"] = first_score
            rolled_back = True

        final_score = score["total"]
        success = final_score >= self.MIN_SCORE

        self._log.end_run(final_score, success, rolled_back)

        return current, {
            "iterations": len(self._log.current_run["generations"]) if self._log.current_run else 1,
            "final_score": final_score,
            "rolled_back": rolled_back,
            "first_score": first_score,
            "issues": score.get("issues", []),
        }

    def _try_execute_fix(self, fix_prompt: str, user_input: str, agent_type: str) -> Optional[str]:
        """尝试用 cloud/local 执行修复"""
        # 优先 cloud
        if self._cloud:
            try:
                result = self._cloud(fix_prompt)
                if result and len(result.strip()) > 20:
                    return result
            except Exception:
                pass
        # 兜底 local
        if self._llm_chat:
            try:
                result, _ = self._llm_chat(fix_prompt)
                if result and len(result.strip()) > 20:
                    return result
            except Exception:
                pass
        return None

    def health(self) -> Dict:
        return {
            "min_score": self.MIN_SCORE,
            "max_iterations": self.MAX_ITERATIONS,
            "rollback_threshold": self.ROLLBACK_THRESHOLD,
            "stats": self._log.get_stats(),
            "llm_available": self._llm_chat is not None or self._cloud is not None,
        }


# ── 通用修复协议 SelfHealer ─────────────────────────────────
# 泛化“诊断→修复→验证”闭环：只要有 verifier (linter)，就能自愈。
# 证据驱动：先跑 verifier --json 拿到结构化报错，再把“证据+源码”喂给 LLM。

class SelfHealer:
    """Platform-grade self-healing: Scan → Diagnose → Fix(LLM) → Verify.

    按文件后缀映射到对应 verifier；体格检查不合格时自动启动自愈。
    这是把 demo (test_self_healing.py) 提炼为平台能力的内核。
    """

    # 后缀 → verifier 可执行脚本（相对项目根）
    VERIFIERS = {
        ".yaml": "skills/yaml-linter/run.py",
        ".yml": "skills/yaml-linter/run.py",
        ".json": "skills/yaml-linter/run.py",   # JSON 是 YAML 子集，可被 pyyaml 校验
        ".md": "skills/markdown-linter/run.py",
        ".markdown": "skills/markdown-linter/run.py",
        ".css": "skills/css-minifier/run.py",     # 压缩即校验：能健康处理=通过
        # .py 不映射 verifier，走 _COMPILE_EXTS 的 py_compile 分支
    }

    # 简单语言后缀直接 py_compile 校验（无需外部 linter）
    _COMPILE_EXTS = {".py"}

    def __init__(self, llm_fn=None, project_root=None):
        self.project_root = Path(project_root or BASE)
        self._llm_fn = llm_fn  # 可选注入；默认懒加载 agnes

    # ── verifier 解析 ────────────────────────────────────────
    def verifier_for(self, path: Path) -> Optional[Path]:
        suffix = path.suffix.lower()
        rel = self.VERIFIERS.get(suffix)
        if rel:
            p = self.project_root / rel
            return p if p.exists() else None
        return None

    # ── 诊断 ─────────────────────────────────────────────────
    def diagnose(self, path: Path):
        """运行对应 verifier --json。返回 (rc, data)。无 verifier 时尝试 py_compile。"""
        verifier = self.verifier_for(path)
        if verifier is None:
            if path.suffix.lower() in self._COMPILE_EXTS:
                return self._py_compile_check(path)
            return None, {"summary": {"error": 0}, "unverifiable": True}

        r = subprocess.run([sys.executable, str(verifier), str(path), "--json"],
                           capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60)
        try:
            data = json.loads(r.stdout) if r.stdout else {}
        except json.JSONDecodeError:
            data = {"summary": {"error": 0}, "raw": r.stdout}
        return r.returncode, data

    @staticmethod
    def _py_compile_check(path: Path):
        r = subprocess.run([sys.executable, "-m", "py_compile", str(path)],
                           capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60)
        ok = r.returncode == 0
        return (0 if ok else 1), {"summary": {"error": 0 if ok else 1},
                                   "diagnostic": None if ok else r.stderr[:300]}

    # ── 修复 ─────────────────────────────────────────────────
    def _llm(self, prompt: str) -> str:
        if self._llm_fn:
            return self._llm_fn(prompt)
        # 懒加载 agnes 客户端（确保项目根在 sys.path）
        root = str(self.project_root)
        if root not in sys.path:
            sys.path.insert(0, root)
        from scripts.agnes_client import call_llm
        return call_llm(prompt)

    @staticmethod
    def _build_fix_prompt(original: str, evidence) -> str:
        return (
            "你是通用配置文件修复专家。下面的文件被 verifier 报了错，请修复并返回完整内容。\n"
            "要求：保持语义和结构，只修掉错误；只输出修复后的文件内容，不加解释、不用代码块。\n\n"
            "===== 原内容 =====\n"
            f"{original}\n"
            "===== 诊断证据 (结构化) =====\n"
            f"{json.dumps(evidence, ensure_ascii=False)}"
        )

    # ── 主闭环 ───────────────────────────────────────────────
    def heal(self, path, verbose=True):
        """完整自愈闭环。返回 dict {success, action, evidence, fixed_content}。"""
        p = Path(path)
        if not p.exists():
            return {"success": False, "action": "skipped", "reason": "file missing"}

        original = p.read_text(encoding="utf-8", errors="replace")
        rc, diag = self.diagnose(p)
        n_err = diag.get("summary", {}).get("error", 0)
        if diag.get("unverifiable"):
            if verbose:
                print(f"[heal] {p.name}: 无 verifier，跳过")
            return {"success": True, "action": "unverifiable"}
        if rc == 0 and n_err == 0:
            if verbose:
                print(f"[heal] {p.name}: ✅ 体检合格，无需修复")
            return {"success": True, "action": "healthy"}

        if verbose:
            print(f"[heal] {p.name}: ❌ rc={rc}, errors={n_err}")
            for d in (diag.get("files", [{}])[0].get("diagnostics", []) if diag.get("files") else [] )[:5]:
                print(f"        [L{d.get('line')},C{d.get('column')}] {d.get('reason','')}")

        # 求助 LLM 修复
        try:
            fixed = self._llm(self._build_fix_prompt(original, diag))
        except Exception as e:
            print(f"        ❌ LLM 调用失败: {e}")
            return {"success": False, "action": "llm_error", "reason": str(e)}
        if not fixed or len(fixed) < 5:
            print("        ❌ LLM 返回异常")
            return {"success": False, "action": "llm_empty"}

        # 写回 + 二次验证
        p.write_text(fixed.rstrip("\n") + "\n", encoding="utf-8")
        rc2, diag2 = self.diagnose(p)
        n_err2 = diag2.get("summary", {}).get("error", 0)
        if rc2 == 0 and n_err2 == 0:
            if verbose:
                print(f"[heal] {p.name}: ✅ 修复后体检通过 — 进化成功")
            return {"success": True, "action": "healed", "fixed_content": fixed}
        else:
            p.write_text(original, encoding="utf-8")  # 回滚
            if verbose:
                print(f"[heal] {p.name}: ❌ 二次体检仍失败 (rc={rc2}, err={n_err2})，已回滚")
            return {"success": False, "action": "heal_failed"}

    def heal_tree(self, root, suffixes=None, verbose=True):
        """批量自愈一个目录树下所有可验证文件。"""
        root = Path(root)
        targets = []
        for ext in (suffixes or list(self.VERIFIERS.keys())):
            targets.extend(root.rglob("*" + ext))
        results = {"healed": [], "healthy": [], "failed": [], "skipped": []}
        for t in targets:
            r = self.heal(t, verbose=verbose)
            results[r.get("action", "skipped")].append(str(t))
        return results


# ── CLI ─────────────────────────────────────────────────────

def _main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(
        prog="self_evolve",
        description="Self-evolving engine: grade (SelfEvolver) + self-heal (SelfHealer).",
    )
    ap.add_argument("--path", help="体检/自愈单个文件路径", required=False)
    ap.add_argument("--tree", help="批量自愈一个目录", required=False)
    ap.add_argument("--ext", help="批量时限定后缀(逗号分隔)", default=None)
    ap.add_argument("--no-llm", action="store_true", help="只体检不自愈(不调 LLM)")
    ap.add_argument("--version", action="version", version="self_evolve 2.0.0")
    args = ap.parse_args(argv)

    healer = SelfHealer()

    if args.path:
        if args.no_llm:
            p = Path(args.path)
            rc, diag = healer.diagnose(p)
            n_err = diag.get("summary", {}).get("error", 0) if diag else 0
            print(f"{p.name}: rc={rc}, errors={n_err}")
            return 1 if n_err else 0
        r = healer.heal(args.path)
        return 0 if r.get("success") else 1

    if args.tree:
        exts = None
        if args.ext:
            exts = [e.strip() for e in args.ext.split(",") if e.strip()]
        results = healer.heal_tree(args.tree, suffixes=exts)
        print(json.dumps({k: len(v) for k, v in results.items()}, indent=2))
        return 1 if results.get("failed") else 0

    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(_main())

