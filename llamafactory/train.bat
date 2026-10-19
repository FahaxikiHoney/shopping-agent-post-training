@echo off
setlocal
chcp 65001 >nul
for %%I in ("%~dp0..") do set "REPO_ROOT=%%~fI"
if not defined MODEL_PATH set "MODEL_PATH=%REPO_ROOT%\models\Qwen3-0.6B"
cd /d "%REPO_ROOT%"
python scripts\run_module.py sft --model-path "%MODEL_PATH%"
exit /b %errorlevel%
