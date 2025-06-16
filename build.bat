@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion

echo AutoCalEditor Build Started
echo ================================

REM Windows encoding fix: environment variables
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1

REM Execute Python
python build_all.py

if %ERRORLEVEL% EQU 0 (
    echo.
    echo Build Successful!
    echo Result file: dist\AutoCalEditor.exe
    pause
) else (
    echo.
    echo Build Failed!
    echo Please check the logs.
    pause
)
