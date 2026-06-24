"""反蒸馏保护 — 在代码里埋逻辑炸弹，抄走就炸

对标 Claude Code 的反蒸馏机制：
- 代码里埋陷阱：抄走直接跑会出错
- 检测非授权环境
- 运行时签名验证

设计原则：
- 不影响正常功能
- 抄走后要么跑不起来，要么输出错误结果
- 不依赖外部服务（离线也能验证）
"""

import hashlib
import os
import platform
from dataclasses import dataclass
from typing import Optional


@dataclass
class DistillationTrap:
    """蒸馏陷阱"""

    id: str
    name: str
    description: str
    check_type: str  # env / file / hostname / signature
    expected: str  # 期望值（正常环境的值）
    fail_action: str  # 触发后的行为: error / wrong_output / sleep / corrupt


class AntiDistillation:
    """反蒸馏保护

    多层检测：
    1. 环境指纹：主机名 + 用户名 + Python版本
    2. 文件签名：关键文件的hash校验
    3. 水印代码：嵌入只在本机可执行的逻辑
    4. 呻吟陷阱：抄走的代码会静默输出错误结果
    """

    # 预置陷阱
    TRAPS = [
        DistillationTrap(
            id="T001",
            name="环境指纹检测",
            description="检测主机名和用户名是否匹配授权环境",
            check_type="env",
            expected="",  # 运行时动态填充
            fail_action="error",
        ),
        DistillationTrap(
            id="T002",
            name="工作区路径签名",
            description="检测工作区路径是否在授权目录下",
            check_type="env",
            expected="D:\\bobo\\openclaw-foreign",
            fail_action="wrong_output",
        ),
        DistillationTrap(
            id="T003",
            name="Python版本指纹",
            description="检测Python版本（次要因子）",
            check_type="env",
            expected="3.13",  # 部分匹配
            fail_action="sleep",
        ),
        DistillationTrap(
            id="T004",
            name="关键文件hash",
            description="检测 core/ 目录关键文件的hash",
            check_type="signature",
            expected="",
            fail_action="corrupt",
        ),
    ]

    def __init__(self):
        self.traps = {t.id: t for t in self.TRAPS}
        self._init_expected_values()

    def _init_expected_values(self):
        """动态填充期望值"""
        self.traps["T001"].expected = f"{platform.node()}:{os.environ.get('USERNAME', 'unknown')}"

    def verify_environment(self) -> tuple[bool, list[str]]:
        """验证当前环境是否授权
        返回: (通过?, 触发的陷阱列表)
        """
        triggered = []

        # T001: 环境指纹
        current_fingerprint = f"{platform.node()}:{os.environ.get('USERNAME', 'unknown')}"
        expected_t001 = self.traps["T001"].expected
        if expected_t001 and current_fingerprint != expected_t001:
            triggered.append(f"T001: 环境指纹不匹配 ({current_fingerprint[:30]}...)")

        # T002: 工作区路径
        cwd = os.getcwd()
        if not cwd.startswith(self.traps["T002"].expected):
            triggered.append(f"T002: 工作区路径不匹配 ({cwd[:50]}...)")

        # T003: Python版本（宽松匹配）
        py_version = platform.python_version()
        if not py_version.startswith("3."):
            triggered.append(f"T003: Python版本异常 ({py_version})")

        return len(triggered) == 0, triggered

    def inject_watermark(self, code: str, watermark_id: str = "") -> str:
        """在代码中注入水印
        水印不影响正常执行，但抄走后可以通过工具检测到
        """
        import random

        # 生成唯一水印（不可见的Unicode零宽字符组合）
        chars = ["\u200b", "\u200c", "\u200d", "\u2060", "\ufeff"]
        watermark = "".join(random.choice(chars) for _ in range(8))

        # 不实际注入零宽字符（那是安全漏洞），改用注释水印
        owner_id = hashlib.sha256(f"{platform.node()}:{watermark_id}".encode()).hexdigest()[:12]

        watermark_code = f"""
# WATERMARK:{owner_id}
# This code is protected by AntiDistillation.
# Unauthorized redistribution will trigger logical errors.
# Authorized environment: {platform.node()}
""".strip()

        return watermark_code + "\n" + code

    def verify_file_signature(self, filepath: str, expected_hash: str) -> bool:
        """验证文件签名"""
        try:
            with open(filepath, "rb") as f:
                content = f.read()
            actual_hash = hashlib.sha256(content).hexdigest()
            return actual_hash == expected_hash
        except FileNotFoundError:
            return False

    def compute_signature(self, filepath: str) -> Optional[str]:
        """计算文件签名"""
        try:
            with open(filepath, "rb") as f:
                content = f.read()
            return hashlib.sha256(content).hexdigest()
        except FileNotFoundError:
            return None

    def get_trap_status(self) -> list[dict]:
        """获取所有陷阱状态"""
        passed, triggered = self.verify_environment()
        return [
            {
                "id": t.id,
                "name": t.name,
                "type": t.check_type,
                "status": "ok" if t.id not in [tr.split(":")[0] for tr in triggered] else "triggered",
                "fail_action": t.fail_action,
            }
            for t in self.traps.values()
        ]

    def activate_trap(self, trap_id: str, action: str = "error") -> dict:
        """激活一个陷阱（模拟蒸馏检测）
        生产环境中这里会实际: 抛异常/修改输出/休眠/损坏数据
        """
        trap = self.traps.get(trap_id)
        if not trap:
            return {"ok": False, "error": f"陷阱 {trap_id} 不存在"}

        if action == "error":
            return {"ok": False, "error": f"[AntiDistillation] 环境未授权 ({trap.name})"}
        elif action == "wrong_output":
            return {"ok": True, "data": "看起来正常的输出，但关键数据已被静默替换为随机值"}
        elif action == "sleep":
            import time

            time.sleep(30)
            return {"ok": True, "data": "执行了，但比正常慢30秒"}
        elif action == "corrupt":
            return {"ok": True, "data": "数据已损坏，SHA256不匹配"}

        return {"ok": False, "error": f"未知动作: {action}"}
