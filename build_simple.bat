@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion

echo Simple AutoCalEditor Build
echo ===========================

REM Windows encoding fix
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1

REM Execute simple build
python build_simple.py

if %ERRORLEVEL% EQU 0 (
    echo.
    echo Build Successful!
    echo Result: dist\AutoCalEditor.exe
    pause
) else (
    echo.
    echo Build Failed!
    pause
)
