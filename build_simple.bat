@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion

echo ========================================
echo Simple AutoCalEditor Build (경로 안전)
echo ========================================

REM Windows encoding fix
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1

REM 현재 디렉토리 표시
echo 현재 위치: %CD%

REM Execute simple build
echo 빌드 시작...
python build_simple.py

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ✅ 빌드 성공!
    echo 📁 결과: dist\AutoCalEditor.exe
    echo 🚀 실행: .\dist\AutoCalEditor.exe
    pause
) else (
    echo.
    echo ❌ 빌드 실패!
    echo 로그를 확인하세요.
    pause
)
