#!/bin/bash

echo "========================================"
echo "AutoCalEditor Nuitka 고성능 컴파일"
echo "========================================"
echo ""
echo "🔥 실제 컴파일을 통한 최고 성능 실행 파일 생성"
echo "⚡ PyInstaller보다 훨씬 빠른 실행 속도"
echo "📦 더 작은 파일 크기"
echo ""

# 환경변수 설정
export PYTHONIOENCODING=utf-8
export PYTHONUTF8=1

# 현재 디렉토리 표시
echo "현재 위치: $(pwd)"
echo ""

# Python 버전 확인
echo "Python 버전 확인..."
if ! python3 --version; then
    echo "❌ Python3이 설치되지 않았습니다."
    echo "Python 3.8 이상을 설치해주세요:"
    echo "  Ubuntu/Debian: sudo apt install python3 python3-pip"
    echo "  CentOS/RHEL: sudo yum install python3 python3-pip"
    echo "  macOS: brew install python3"
    exit 1
fi
echo ""

# 컴파일러 확인
echo "C 컴파일러 확인..."
if command -v gcc &> /dev/null; then
    echo "✅ GCC 컴파일러 발견"
    gcc --version | head -1
elif command -v clang &> /dev/null; then
    echo "✅ Clang 컴파일러 발견"
    clang --version | head -1
else
    echo "❌ C 컴파일러를 찾을 수 없습니다."
    echo ""
    echo "다음 명령어로 설치해주세요:"
    echo "  Ubuntu/Debian: sudo apt install gcc"
    echo "  CentOS/RHEL: sudo yum install gcc"
    echo "  macOS: xcode-select --install"
    echo ""
    exit 1
fi
echo ""

# Nuitka 빌드 실행
echo "Nuitka 컴파일 시작..."
echo "⏱️ 예상 소요 시간: 10-30분"
echo "📝 로그 파일: nuitka_build.log"
echo ""

# Python 실행 (python3 사용)
if python3 build_nuitka.py; then
    echo ""
    echo "========================================"
    echo "✅ Nuitka 컴파일 성공!"
    echo "========================================"
    echo ""
    echo "📁 실행 파일이 생성되었습니다."
    echo "⚡ PyInstaller보다 훨씬 빠른 성능을 경험하세요!"
    echo ""
    echo "실행 방법:"
    if [ -f "AutoCalEditor" ]; then
        echo "  ./AutoCalEditor"
        chmod +x AutoCalEditor
    elif [ -f "main" ]; then
        echo "  ./main"
        chmod +x main
    else
        echo "  생성된 실행 파일을 확인하세요."
    fi
    echo ""
else
    echo ""
    echo "========================================"
    echo "❌ Nuitka 컴파일 실패!"
    echo "========================================"
    echo ""
    echo "문제 해결 방법:"
    echo "1. nuitka_build.log 파일을 확인하세요"
    echo "2. 모든 의존성이 설치되었는지 확인하세요:"
    echo "   pip3 install -r requirements.txt"
    echo "3. C 컴파일러가 올바르게 설치되었는지 확인하세요"
    echo ""
    exit 1
fi
