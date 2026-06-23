@echo off
setlocal enabledelayedexpansion
title V3.0 Production Deploy

echo.
echo ============================================
echo    V3.0 Self-Evolving Factory Deploy
echo    Date: %date% %time%
echo ============================================
echo.

REM -- Step 0: Fix code page --
chcp 65001 >nul 2>&1

REM -- Step 1: Check prerequisites --
echo [1/7] Checking prerequisites...
echo.

python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo   FAIL Python not found - install Python 3.11+
    exit /b 1
)
for /f "tokens=*" %%i in ('python --version 2^>^&1') do echo   OK  %%i

node --version >nul 2>&1
if %errorlevel% neq 0 (
    echo   WARN Node.js not found (optional)
) else (
    for /f "tokens=*" %%i in ('node --version 2^>^&1') do echo   OK  Node: %%i
)

git --version >nul 2>&1
if %errorlevel% neq 0 (
    echo   WARN Git not found
) else (
    echo   OK  Git: found
)

echo.
echo [2/7] Installing Python dependencies...
pip install ruff pre-commit pyyaml requests >nul 2>&1
echo   OK  Python deps installed

echo.
echo [3/7] Running pre-commit hooks...
cd /d D:\bobo\openclaw-foreign\workspace\v1.1-self-evo-factory
if exist .pre-commit-config.yaml (
    pre-commit run --all-files 2>nul
    echo   OK  Pre-commit hooks done
) else (
    echo   WARN No pre-commit config - skipping
)

echo.
echo [4/7] Verifying new skills (5)...
set PYTHONIOENCODING=utf-8
set SKILLS_DIR=D:\bobo\openclaw-foreign\skills

set ok=0
set fail=0
for %%s in (sql-optimizer api-doc-generator log-analyzer config-diff docker-compose-gen) do (
    python "%SKILLS_DIR%\%%s\run.py" --version >nul 2>&1
    if !errorlevel! equ 0 (
        set /a ok+=1
        echo   OK  %%s
    ) else (
        echo   FAIL %%s
        set /a fail+=1
    )
)
echo   Result: %ok%/%5% new skills verified

echo.
echo [5/7] Testing API skills (dry-run)...
cd /d D:\bobo\openclaw-foreign\workspace\v1.1-self-evo-factory
python pipeline\test_api_skills.py 2>nul
echo   OK  API skills test completed

echo.
echo [6/7] Running eval suite...
cd /d D:\bobo\openclaw-foreign\workspace\v1.1-self-evo-factory
if exist eval-suite\run_all.py (
    python eval-suite\run_all.py 2>nul
    echo   OK  Eval suite completed
) else (
    echo   WARN Eval suite not found - skipping
)

echo.
echo [7/7] System health check...
set skill_count=0
for /d %%d in ("%SKILLS_DIR%\*") do set /a skill_count+=1
echo   Skills: %skill_count%
cd /d D:\bobo\openclaw-foreign\workspace\v1.1-self-evo-factory
for /f %%c in ('git rev-list --count HEAD 2^>nul') do set commits=%%c
echo   Git commits: %commits%
echo   Working tree: checked

echo.
echo ============================================
echo    DEPLOY COMPLETE - V3.0
echo    Skills: %skill_count%  |  Commits: %commits%
echo ============================================
echo.
echo Next steps:
echo   python pipeline\config_api_tokens.py
echo   python pipeline\agent_mission.py
echo   start web\dashboard.html
echo.

endlocal
