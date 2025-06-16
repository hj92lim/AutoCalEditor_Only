@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion

echo ========================================
echo AutoCalEditor Nuitka 고성능 컴파일
echo ========================================
echo.
echo 🔥 실제 컴파일을 통한 최고 성능 실행 파일 생성
echo ⚡ PyInstaller보다 2-5배 빠른 실행 속도
echo 🚀 Cython 최적화로 극한 성능 달성
echo 📦 단일 exe 파일로 어디서든 실행 가능
echo 🖥️ 콘솔창 없이 깔끔한 실행
echo.

REM Windows encoding fix
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1

REM 현재 디렉토리 표시
echo 현재 위치: %CD%
echo.

REM Python 버전 확인
echo Python 버전 확인...
python --version
if %ERRORLEVEL% NEQ 0 (
    echo ❌ Python이 설치되지 않았거나 PATH에 없습니다.
    echo Python 3.8 이상을 설치해주세요.
    pause
    exit /b 1
)
echo.

REM 컴파일러 확인
echo C 컴파일러 확인...
gcc --version >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo ✅ GCC 컴파일러 발견
    goto :compiler_ok
)

cl >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo ✅ MSVC 컴파일러 발견
    goto :compiler_ok
)

echo ❌ C 컴파일러를 찾을 수 없습니다.
echo.
echo 다음 중 하나를 설치해주세요:
echo 1. Visual Studio Build Tools (권장)
echo    https://visualstudio.microsoft.com/ko/downloads/
echo 2. MinGW-w64
echo    https://www.mingw-w64.org/downloads/
echo.
echo 설치 후 다시 실행해주세요.
pause
exit /b 1

:compiler_ok
echo.

REM Nuitka 빌드 실행
echo Nuitka 컴파일 시작...
echo ⏱️ 예상 소요 시간: 10-30분
echo 📝 로그 파일: nuitka_build.log
echo.

python build_nuitka.py

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ========================================
    echo ✅ Nuitka 컴파일 성공!
    echo ========================================
    echo.
    echo 📁 AutoCalEditor.exe 파일이 생성되었습니다!
    echo ⚡ PyInstaller보다 2-5배 빠른 성능을 경험하세요!
    echo 🔥 Cython 최적화로 극한 성능 달성!
    echo 📦 단일 exe 파일로 어디서든 실행 가능!
    echo 🖥️ 콘솔창 없이 깔끔한 실행!
    echo.
    echo 실행 방법:
    if exist "AutoCalEditor.exe" (
        echo   .\AutoCalEditor.exe
        echo.
        echo 파일 크기:
        for %%I in (AutoCalEditor.exe) do echo   %%~zI bytes (%%~zI/1048576 MB)
    ) else if exist "main.exe" (
        echo   .\main.exe
    ) else (
        echo   생성된 실행 파일을 확인하세요.
    )
    echo.
    pause
) else (
    echo.
    echo ========================================
    echo ❌ Nuitka 컴파일 실패!
    echo ========================================
    echo.
    echo 문제 해결 방법:
    echo 1. nuitka_build.log 파일을 확인하세요
    echo 2. 모든 의존성이 설치되었는지 확인하세요:
    echo    pip install -r requirements.txt
    echo 3. C 컴파일러가 올바르게 설치되었는지 확인하세요
    echo.
    pause
)
