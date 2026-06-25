<#
.SYNOPSIS
 猫抓 Ollama 启动脚本 — Windows 兼容版
.DESCRIPTION
 1. 规避 WinNAT 端口保留 (11406-11505)
 2. 强制使用 PowerShell 环境变量语法
 3. 绑定 GTX 1060 可用的端口
#>

# --- 核心配置 ---
$env:OLLAMA_HOST = "127.0.0.1:11634"
$env:OLLAMA_MODELS = "D:\bobo\Guanjia\ollama-runtime\models"
$env:OLLAMA_NO_CLOUD = "1"
$env:OLLAMA_NOPRUNE = "1"
$OLAMA_EXE = "D:\bobo\Guanjia\ollama-runtime\ollama.exe"

# --- 启动 ---
Write-Host "🦞 正在启动 Ollama 服务..." -ForegroundColor Green
Write-Host "  监听地址: $env:OLLAMA_HOST"
Write-Host "  模型目录: $env:OLLAMA_MODELS"
Write-Host "  端口选择: 11634 (绕过 WinNAT 11406-11505 保留段)"

Start-Process -FilePath $OLAMA_EXE -ArgumentList "serve" -NoNewWindow -Wait
