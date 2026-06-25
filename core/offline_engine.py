# -*- coding: utf-8 -*-
"""
离线规则引擎（宪法即代码）
纯本地规则匹配，不需要 LLM，不需要网络。
用于三级回退的 Level 3：Ollama 挂了 + 没有 API Key 时。
"""
import re
from typing import Optional, Tuple

# ── 规则表 ──
RULES = [
    # (正则, 响应模板)
    (r"(你好|hi|hello|在吗|hey)", "猫抓离线引擎就绪。无网络、无模型，纯规则响应。'自学'和'建站'相关的问题我可以帮上忙。"),
    (r"(你是谁|你的身份)", "我是猫抓，你的本地 AI 工作伙伴。当前处于纯离线规则模式。"),
    (r"(天气|temperature|weather)", "离线模式无法获取实时天气。请联网或启动本地 Ollama。"),
    (r"(时间|date|time|几点|日期)", "离线模式无法获取实时时间。Windows 系统时钟显示在任务栏右下角。"),
    (r"(代码|code|bug|error|修复|fix|写|编程|react|next|js|python|node)", "离线规则引擎无法分析和生成代码。请启动 Ollama 或联网使用完整版。"),
    (r"(搜索|search|google|百度|查一下)", "离线模式不支持网络搜索。请启动联网通道。"),
    (r"(翻译|translate|英文|中文|翻译成)", "离线模式不支持翻译。请启动 Ollama 或联网。"),
    (r"(帮助|help|能做什么|你会什么)", "猫抓离线模式支持：greeting / 身份说明 / 基础问答。代码/搜索/翻译需要联网或本地 LLM。"),
    (r"(谢谢|thank|感谢)", "不客气！需要时切换到在线或本地 LLM 模式。"),
    (r"(再见|bye|see you|晚安)", "再见！猫抓随时待命。"),
]

_FALLBACK = "猫抓离线中。暂无网络和本地 LLM。如需完整能力，请：\n① 启动 Ollama（python scripts/start_ollama.ps1）\n② 或配置 DEEPSEEK_API_KEY"

def match(prompt: str) -> Tuple[str, Optional[str]]:
    """返回 (响应, 匹配规则) 或 (回退, None)"""
    for pattern, response in RULES:
        if re.search(pattern, prompt, re.IGNORECASE):
            return response, pattern
    return _FALLBACK, None

# CLI
if __name__ == "__main__":
    import sys
    prompt = sys.argv[1] if len(sys.argv) > 1 else "你好"
    resp, rule = match(prompt)
    print(f"[offline:{rule or 'fallback'}] {resp}")
