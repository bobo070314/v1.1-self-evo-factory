@echo off
REM ============================================
REM V2.14 Deploy Script — Self-Evolving Factory
REM One-click deploy + test + validate
REM ============================================

set PROJECT_ROOT=D:\bobo\openclaw-foreign\workspace\v1.1-self-evo-factory
cd /d "%PROJECT_ROOT%"

echo.
echo ========================================
echo  V2.14 — Self-Evolving Factory Deploy
echo ========================================
echo.

REM Step 1: Install dependencies
echo [1/4] Installing Python dependencies...
python -m pip install --upgrade pip ruff pre-commit --quiet
echo.

REM Step 2: Skill validation (148 skills)
echo [2/4] Validating 148 skills (--version)...
python -c "import subprocess,json,sys;from pathlib import Path;B=Path(r'D:/bobo/openclaw-foreign/skills');t=0;p=0;[((t:=t+1,p:=p+1) if subprocess.run([sys.executable,str(d/'run.py'),'--version'],capture_output=True,timeout=10).returncode==0 else (t:=t+1,None)) for d in sorted(B.iterdir()) if d.is_dir() and not d.name.startswith('.') and d.name!='qclaw-shared' and (d/'run.py').exists()];print(f'Skills: {p}/{t}')
echo.

REM Step 3: Deep skill tests
echo [3/4] Running deep skill tests...
python eval-suite\test_deep_skills.py
set DEEP_RESULT=%ERRORLEVEL%
echo.

REM Step 4: API skill validation
echo [4/4] Validating API skills...
python pipeline\validate_apis.py
set API_RESULT=%ERRORLEVEL%
echo.

echo ========================================
set /a FINAL=%DEEP_RESULT%+%API_RESULT%
if %FINAL%==0 (
    echo  ALL CHECKS PASSED ^- System ready!
) else (
    echo  WARNING: Some checks failed. See above.
)
echo ========================================

pause
