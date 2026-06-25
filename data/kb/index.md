# 猫抓离线知识库

## 项目概况
猫抓（OpenClaw international）是本地 AI 工作伙伴。
- 技术栈：React, Next.js, Tailwind CSS
- 本地 LLM：Ollama + qwen3.5:2b Q8_0
- GPU：NVIDIA GTX 1060 3GB CUDA 6.1
- Ollama 端口：127.0.0.1:11634
- Git：git@github.com:bobo070314/v1.1-self-evo-factory.git

## 启动命令
- Ollama 启动：D:\bobo\projects\v1.1-self-evo-factory\scripts\start_ollama.ps1（管理员 PowerShell）
- 保活守护：python D:\bobo\projects\v1.1-self-evo-factory\scripts\ollama_keepalive.py
- 本地推理：python D:\bobo\projects\v1.1-self-evo-factory\core\local_llm.py "你的问题"

## 常见问题
Ollama 连接失败 -> 管理员 PowerShell 跑 start_ollama.ps1
推理超时 -> GTX 1060 3GB 推理需要 30-90 秒，耐心等待
中文乱码 -> 设置 PYTHONIOENCODING=utf-8 或使用 run_llm_safe.py
