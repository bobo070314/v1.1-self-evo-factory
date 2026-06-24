"""验收标准引擎 — "活的标准"，不是死宪法

Claude Code 的验收标准：
1. 每个任务有明确的 "可验证证据" 要求
2. 不接受 "我完成了" — 必须看到产出
3. 标准随任务类型动态调整
"""

from dataclasses import dataclass, field
from enum import Enum


class EvidenceType(str, Enum):
    """可验证的证据类型"""

    FILE_EXISTS = "file_exists"  # 文件存在
    EXIT_CODE = "exit_code"  # 命令退出码
    TEST_PASS = "test_pass"  # 测试通过
    LINT_CLEAN = "lint_clean"  # Lint无警告
    HTTP_STATUS = "http_status"  # HTTP状态码
    SIZE_NONZERO = "size_nonzero"  # 文件非空
    PATTERN_MATCH = "pattern_match"  # 内容匹配
    NO_SECURITY_ISSUE = "no_security_issue"  # 无安全问题
    DEPENDENCY_OK = "dependency_ok"  # 依赖完整


@dataclass
class Criterion:
    """单条验收标准"""

    id: str
    description: str  # 人类可读描述
    evidence_type: EvidenceType  # 证据类型
    required: bool = True  # 是否必须满足
    params: dict = field(default_factory=dict)  # 证据参数
    weight: float = 1.0  # 权重（非必须项的扣分系数）

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "description": self.description,
            "evidence_type": self.evidence_type.value,
            "required": self.required,
            "params": self.params,
            "weight": self.weight,
        }


class AcceptanceCriteria:
    """验收标准引擎

    预置了常见任务类型的验收标准模板，
    支持动态注册和自定义
    """

    # 标准模板库
    TEMPLATES = {
        "code_implementation": [
            Criterion("code_file", "代码文件存在", EvidenceType.FILE_EXISTS),
            Criterion("syntax", "代码语法正确（Python编译检查）", EvidenceType.EXIT_CODE, params={"expected": 0}),
            Criterion("tests", "测试用例全部通过", EvidenceType.TEST_PASS, weight=1.5),
            Criterion("no_vuln", "无安全漏洞", EvidenceType.NO_SECURITY_ISSUE),
            Criterion("lint", "Lint无新增警告", EvidenceType.LINT_CLEAN, required=False, weight=0.5),
        ],
        "bug_fix": [
            Criterion("fix_code", "修复代码存在", EvidenceType.FILE_EXISTS),
            Criterion("regression", "回归测试通过", EvidenceType.TEST_PASS, weight=2.0),
            Criterion("no_new_bug", "无新增lint警告", EvidenceType.LINT_CLEAN, required=False),
            Criterion("root_cause", "根因分析记录存在", EvidenceType.FILE_EXISTS, params={"pattern": "*.md"}),
        ],
        "deployment": [
            Criterion("build_ok", "构建成功", EvidenceType.EXIT_CODE, params={"expected": 0}, weight=1.5),
            Criterion("artifact", "构建产物存在", EvidenceType.FILE_EXISTS),
            Criterion("artifact_size", "构建产物非空", EvidenceType.SIZE_NONZERO),
            Criterion("health", "健康检查通过", EvidenceType.HTTP_STATUS, params={"expected": 200}),
            Criterion("deps_ok", "依赖完整", EvidenceType.DEPENDENCY_OK, required=False),
        ],
        "documentation": [
            Criterion("doc_exists", "文档文件存在", EvidenceType.FILE_EXISTS),
            Criterion("doc_size", "文档内容非空", EvidenceType.SIZE_NONZERO),
            Criterion("format", "格式正确（Markdown）", EvidenceType.PATTERN_MATCH, params={"pattern": r"^#"}),
        ],
        "security_audit": [
            Criterion("audit_report", "审计报告存在", EvidenceType.FILE_EXISTS),
            Criterion("vuln_list", "漏洞列表非空", EvidenceType.SIZE_NONZERO),
            Criterion(
                "severity",
                "严重性分级标记",
                EvidenceType.PATTERN_MATCH,
                params={"pattern": r"(CRITICAL|HIGH|MEDIUM|LOW)"},
            ),
            Criterion(
                "remediation",
                "修复建议存在",
                EvidenceType.PATTERN_MATCH,
                params={"pattern": r"(修复|fix|建议|recommend)"},
            ),
        ],
    }

    def __init__(self):
        self.custom_templates: dict[str, list[Criterion]] = {}

    def get_criteria(self, task_type: str) -> list[Criterion]:
        """获取指定任务类型的验收标准"""
        if task_type in self.custom_templates:
            return self.custom_templates[task_type]
        return self.TEMPLATES.get(task_type, self.TEMPLATES["code_implementation"])

    def register_template(self, name: str, criteria: list[Criterion]):
        """注册自定义验收标准"""
        self.custom_templates[name] = criteria

    def infer_type(self, task_description: str) -> str:
        """从任务描述推断任务类型"""
        desc = task_description.lower()

        if any(kw in desc for kw in ["修复", "bug", "fix", "修", "改错"]):
            return "bug_fix"
        elif any(kw in desc for kw in ["部署", "deploy", "build", "发布", "上线"]):
            return "deployment"
        elif any(kw in desc for kw in ["文档", "doc", "readme", "说明"]):
            return "documentation"
        elif any(kw in desc for kw in ["安全", "security", "审计", "audit", "漏洞"]):
            return "security_audit"
        else:
            return "code_implementation"

    def evaluate(self, task_type: str, evidence: dict) -> tuple[bool, float, list[str]]:
        """评估验收标准
        返回: (全部必要项通过?, 总分, 失败项列表)
        """
        criteria = self.get_criteria(task_type)
        passed = []
        failed = []
        total_score = 0.0
        max_score = sum(c.weight for c in criteria)

        for c in criteria:
            ev = evidence.get(c.evidence_type.value)
            if ev is None:
                if c.required:
                    failed.append(f"缺少证据: {c.description}")
                continue

            # 简单判断：有证据 → 通过
            # 生产环境应接入实际的检查器
            if self._check_evidence(c, ev):
                passed.append(c.description)
                total_score += c.weight
            elif c.required:
                failed.append(f"不满足: {c.description}")

        all_required_pass = len(failed) == 0
        score = total_score / max(max_score, 1)

        return all_required_pass, score, failed

    def _check_evidence(self, criterion: Criterion, evidence_value) -> bool:
        """检查单一证据"""
        if evidence_value is True:
            return True
        if isinstance(evidence_value, bool):
            return evidence_value
        if isinstance(evidence_value, str) and evidence_value.lower() in ("true", "yes", "ok", "pass"):
            return True
        return bool(evidence_value)

    def suggest_evidence_types(self, task_type: str) -> list[str]:
        """提示需要收集哪些类型的证据"""
        criteria = self.get_criteria(task_type)
        return [c.evidence_type.value for c in criteria if c.required]
