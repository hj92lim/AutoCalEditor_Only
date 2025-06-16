@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion

echo 🚀 AutoCalEditor 빌드 시작
echo ================================

REM 🔧 Windows 인코딩 문제 해결: 환경변수 설정
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1

REM Python 실행
python build_all.py

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ✅ 빌드 성공!
    echo 📁 결과 파일: dist\AutoCalEditor.exe
    pause
) else (
    echo.
    echo ❌ 빌드 실패!
    echo 로그를 확인하세요.
    pause
)
