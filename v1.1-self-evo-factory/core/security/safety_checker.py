"""安全检测器 — 23道检测规则

对标 Claude Code：
1. Unicode 零宽字符注入
2. Zsh/PowerShell 骚操作
3. 路径穿越
4. 命令注入
5. SQL注入
6. 硬编码密钥检测
7. 权限提升
8. 文件系统破坏
9. 网络外泄
10. 进程劫持
...共23道

每道规则：pattern + severity + block/allow
"""

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class Severity(str, Enum):
    CRITICAL = "critical"  # 立即阻止
    HIGH = "high"  # 报警 + 阻止
    MEDIUM = "medium"  # 报警，可放行
    LOW = "low"  # 仅记录


class RuleAction(str, Enum):
    BLOCK = "block"  # 阻止执行
    WARN = "warn"  # 警告但放行
    ALLOW = "allow"  # 放行
    ASK = "ask"  # 询问用户


@dataclass
class SafetyRule:
    """单条安全规则"""

    id: str
    name: str
    description: str
    pattern: str  # 正则表达式
    severity: Severity
    action: RuleAction
    category: str  # 分类
    check_in: str = "command"  # 检测位置：command / file / network / all

    def matches(self, target: str) -> bool:
        """检查目标是否匹配此规则"""
        return bool(re.search(self.pattern, target, re.IGNORECASE | re.MULTILINE))


@dataclass
class SafetyResult:
    """安全检测结果"""

    passed: bool
    violations: list[dict] = field(default_factory=list)
    warnings: list[dict] = field(default_factory=list)
    blocked_by: Optional[str] = None


class SafetyChecker:
    """23道安全检测规则引擎

    每条规则有：
    - 正则匹配模式
    - 严重程度（critical/high/medium/low）
    - 动作（block/warn/allow/ask）
    """

    # ============ 23道检测规则 ============
    RULES = [
        # ---- 1-5: 注入类 ----
        SafetyRule(
            "S001",
            "Unicode零宽字符注入",
            "检测零宽空格/连接符隐藏恶意代码",
            r"[\u200b\u200c\u200d\u2060\uFEFF]",
            Severity.CRITICAL,
            RuleAction.BLOCK,
            "injection",
        ),
        SafetyRule(
            "S002",
            "SQL注入",
            "检测原始SQL拼接",
            r"(select|insert|update|delete|drop|alter|union).{0,50}(from|into|table|database)",
            Severity.CRITICAL,
            RuleAction.BLOCK,
            "injection",
        ),
        SafetyRule(
            "S003",
            "命令注入",
            "检测shell命令注入",
            r"[;&|`$][\s]*(rm\s+-rf|mkfs|dd\s+if|:\(\)\s*\{|wget\s+-O|curl\s+.*\|\s*(ba)?sh)",
            Severity.CRITICAL,
            RuleAction.BLOCK,
            "injection",
        ),
        SafetyRule(
            "S004",
            "XSS攻击",
            "检测脚本注入",
            r"<script|<img\s+onerror|javascript:|onload=|onerror=",
            Severity.HIGH,
            RuleAction.BLOCK,
            "injection",
        ),
        SafetyRule(
            "S005",
            "路径穿越",
            "检测目录穿越攻击",
            r"(\.\.\/|\.\.\\|/etc/passwd|/etc/shadow|C:\\Windows\\System32)",
            Severity.CRITICAL,
            RuleAction.BLOCK,
            "injection",
        ),
        # ---- 6-10: 文件系统破坏 ----
        SafetyRule(
            "S006",
            "递归删除",
            "检测rm -rf / del /f /s",
            r"(rm\s+.*-rf?\s*\S*\s*[\\/]|del\s+/[fsq]\s+/s|rd\s+/s\s+/q)",
            Severity.CRITICAL,
            RuleAction.BLOCK,
            "filesystem",
        ),
        SafetyRule(
            "S007",
            "格式化磁盘",
            "检测磁盘格式化命令",
            r"(mkfs\.|format\s+[a-z]:|diskpart|fdisk)",
            Severity.CRITICAL,
            RuleAction.BLOCK,
            "filesystem",
        ),
        SafetyRule(
            "S008",
            "修改系统文件",
            "检测操作系统文件修改",
            r"(chmod\s+777|chown\s+root|attrib\s+\+[shr])",
            Severity.HIGH,
            RuleAction.BLOCK,
            "filesystem",
        ),
        SafetyRule(
            "S009",
            "批量覆盖写入",
            "检测破坏性重定向",
            r"(sudo\s+|>\s*/dev/[hs]d|[^>]>\s*/etc/)",
            Severity.HIGH,
            RuleAction.BLOCK,
            "filesystem",
        ),
        SafetyRule(
            "S010",
            "符号链接劫持",
            "检测恶意软链接",
            r"ln\s+-sf?\s+/etc/|mklink\s+/[dh]",
            Severity.HIGH,
            RuleAction.BLOCK,
            "filesystem",
        ),
        # ---- 11-15: 权限与进程 ----
        SafetyRule(
            "S011",
            "sudo提权",
            "检测未授权sudo操作",
            r"sudo\s+(?!-v|-n|apt|yum|brew|npm|pip)",
            Severity.HIGH,
            RuleAction.ASK,
            "privilege",
        ),
        SafetyRule(
            "S012",
            "进程注入",
            "检测进程劫持",
            r"(ptrace|process\s+hacker|inject\s+.*\b(pid|process)\b)",
            Severity.CRITICAL,
            RuleAction.BLOCK,
            "privilege",
        ),
        SafetyRule(
            "S013",
            "注册表修改",
            "检测Windows注册表操作",
            r"(reg\s+(add|delete|import)|New-ItemProperty.*HKLM)",
            Severity.HIGH,
            RuleAction.ASK,
            "privilege",
        ),
        SafetyRule(
            "S014",
            "计划任务持久化",
            "检测定时任务植入",
            r"(schtasks\s+/create|at\s+\d|Register-ScheduledTask)",
            Severity.HIGH,
            RuleAction.BLOCK,
            "privilege",
        ),
        SafetyRule(
            "S015",
            "内核模块加载",
            "检测驱动/内核操作",
            r"(insmod|modprobe|sc\s+create|sc\s+start|driver\s+load)",
            Severity.CRITICAL,
            RuleAction.BLOCK,
            "privilege",
        ),
        # ---- 16-20: 数据泄漏 ----
        SafetyRule(
            "S016",
            "API密钥泄漏",
            "检测硬编码密钥/Token",
            r"(api[_-]?key|access[_-]?token|secret[_-]?key|password|credential)\s*[=:]\s*[\"']?[a-zA-Z0-9_\-\.]{20,}[\"']?",
            Severity.CRITICAL,
            RuleAction.BLOCK,
            "leakage",
            check_in="all",
        ),
        SafetyRule(
            "S017",
            "SSH密钥泄漏",
            "检测私钥泄漏",
            r"-----BEGIN\s+(RSA|EC|DSA|OPENSSH)\s+PRIVATE\s+KEY-----",
            Severity.CRITICAL,
            RuleAction.BLOCK,
            "leakage",
            check_in="all",
        ),
        SafetyRule(
            "S018",
            "环境变量泄漏",
            "检测env导出敏感信息",
            r"(export\s+|set\s+|setx\s+)\w*(token|key|secret|password|credential)",
            Severity.HIGH,
            RuleAction.BLOCK,
            "leakage",
        ),
        SafetyRule(
            "S019",
            "数据外泄",
            "检测数据发送到外部",
            r"(curl|wget|Invoke-WebRequest|nc\s+).*\b(https?://|\.com|\.net|\.io).*\b(data|dump|exfil)",
            Severity.CRITICAL,
            RuleAction.BLOCK,
            "leakage",
        ),
        SafetyRule(
            "S020",
            "剪贴板窃取",
            "检测剪贴板操作",
            r"(xclip|pbcopy|Get-Clipboard|clip\b)(?!.*\|.*out)",
            Severity.MEDIUM,
            RuleAction.WARN,
            "leakage",
        ),
        # ---- 21-23: 网络与隐蔽 ----
        SafetyRule(
            "S021",
            "反向Shell",
            "检测反向Shell连接",
            r"(nc\s+.*-e|bash\s+-i\s*>&|python\s+-c\s*.*socket|powershell.*-e\s+[A-Za-z0-9+/]{20,}|Invoke-ReverseShell)",
            Severity.CRITICAL,
            RuleAction.BLOCK,
            "network",
        ),
        SafetyRule(
            "S022",
            "DNS隧道",
            "检测DNS数据外泄",
            r"(dnscat|iodine|dns2tcp|dnsteal|nslookup.*\b(base64|hex|decode)\b)",
            Severity.CRITICAL,
            RuleAction.BLOCK,
            "network",
        ),
        SafetyRule(
            "S023",
            "代码混淆/编码执行",
            "检测base64编码的恶意命令",
            r"(eval\s*\(|exec\s*\(|base64\s+-d|FromBase64String.*iex|Invoke-Expression)",
            Severity.HIGH,
            RuleAction.BLOCK,
            "obfuscation",
        ),
    ]

    def __init__(self, enabled_rules: Optional[list[str]] = None):
        """enabled_rules: 启用的规则ID列表，None=全部启用"""
        self.rules = self.RULES
        if enabled_rules:
            enabled_set = set(enabled_rules)
            self.rules = [r for r in self.RULES if r.id in enabled_set]

    def check_command(self, command: str, context: dict = None) -> SafetyResult:
        """检测命令安全性"""
        return self._check(command, "command", context)

    def check_file_content(self, content: str, context: dict = None) -> SafetyResult:
        """检测文件内容安全性"""
        return self._check(content, "file", context)

    def check_network_request(self, url: str, context: dict = None) -> SafetyResult:
        """检测网络请求安全性"""
        return self._check(url, "network", context)

    def _check(self, target: str, check_type: str, context: dict = None) -> SafetyResult:
        violations = []
        warnings = []
        blocked_by = None

        for rule in self.rules:
            # 跳过不匹配检测位置的规则
            if rule.check_in not in (check_type, "all"):
                continue

            if rule.matches(target):
                detail = {
                    "rule_id": rule.id,
                    "name": rule.name,
                    "description": rule.description,
                    "severity": rule.severity.value,
                    "category": rule.category,
                    "action": rule.action.value,
                }

                if rule.action == RuleAction.BLOCK:
                    violations.append(detail)
                    if rule.severity == Severity.CRITICAL:
                        blocked_by = blocked_by or rule.id
                elif rule.action == RuleAction.WARN:
                    warnings.append(detail)
                elif rule.action == RuleAction.ASK:
                    violations.append(detail)  # ASK 当 BLOCK 处理（需要用户确认）

        passed = len(violations) == 0

        return SafetyResult(
            passed=passed,
            violations=violations,
            warnings=warnings,
            blocked_by=blocked_by,
        )

    def quick_scan(self, target: str) -> bool:
        """快速扫描（只检查 CRITICAL + HIGH）"""
        for rule in self.rules:
            if rule.severity in (Severity.CRITICAL, Severity.HIGH) and rule.action == RuleAction.BLOCK:
                if rule.matches(target):
                    return False
        return True

    def get_rules_summary(self) -> dict:
        """获取规则摘要"""
        by_category = {}
        by_severity = {}
        for r in self.rules:
            by_category[r.category] = by_category.get(r.category, 0) + 1
            by_severity[r.severity.value] = by_severity.get(r.severity.value, 0) + 1
        return {
            "total_rules": len(self.rules),
            "by_category": by_category,
            "by_severity": by_severity,
        }
