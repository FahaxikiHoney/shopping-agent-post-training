@echo off
setlocal
chcp 65001 >nul
set "REPO_ROOT=%~dp0..\.."
for %%I in ("%REPO_ROOT%") do set "REPO_ROOT=%%~fI"
if not defined MODEL_PATH set "MODEL_PATH=%REPO_ROOT%\models\Qwen3-0.6B"
cd /d "%REPO_ROOT%"
python scripts\run_module.py sft --model-path "%MODEL_PATH%"
exit /b %errorlevel%
