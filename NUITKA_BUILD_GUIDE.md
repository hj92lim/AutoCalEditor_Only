# 🚀 AutoCalEditor Nuitka 고성능 빌드 가이드 (Windows 최적화)

## 📋 개요

Nuitka는 Python 코드를 실제 C++로 컴파일하여 **PyInstaller보다 2-5배 빠른 실행 속도**를 제공하는 Python 컴파일러입니다.
**Cython 모듈과 통합**되어 극한의 성능을 달성합니다.

## ⚡ 성능 비교 (Cython 통합)

| 빌드 방식 | 시작 시간 | 실행 속도 | 파일 크기 | 빌드 시간 | 콘솔 숨김 |
|-----------|-----------|-----------|-----------|-----------|-----------|
| **Nuitka + Cython** | 0.1-0.3초 | ⭐⭐⭐⭐⭐ | 25-40MB | 15-30분 | ✅ |
| PyInstaller | 2-10초 | ⭐⭐⭐ | 80-120MB | 2-5분 | ✅ |

## 🎯 Windows 전용 최적화 특징

- ✅ **콘솔창 완전 숨김** (`--windows-disable-console`)
- ✅ **단일 exe 파일** 생성 (`--onefile`)
- ✅ **Cython 모듈 자동 통합**
- ✅ **Windows COM 지원** (Excel 연동)
- ✅ **어디서든 실행 가능** (Python 설치 불필요)

## 🛠️ 시스템 요구사항

### Windows
- Python 3.8 이상
- Visual Studio Build Tools 또는 MinGW-w64
- 최소 4GB RAM (빌드 시)

### Linux
- Python 3.8 이상
- GCC 컴파일러: `sudo apt install gcc`
- 최소 4GB RAM (빌드 시)

### macOS
- Python 3.8 이상
- Xcode Command Line Tools: `xcode-select --install`
- 최소 4GB RAM (빌드 시)

## 🚀 빌드 방법 (Windows 전용)

### 방법 1: 원클릭 빌드 (가장 쉬움) ⭐

```cmd
# Git에서 최신 코드 가져오기
git pull

# Windows 전용 최적화 빌드 실행
build_nuitka.bat
```

### 방법 2: Windows 전용 스크립트

```cmd
# 모든 의존성 자동 설치 + Cython 빌드 + Nuitka 컴파일
python build_nuitka_windows.py
```

### 방법 3: 수동 단계별 빌드

```cmd
# 1. 의존성 설치
pip install -r requirements_nuitka.txt

# 2. Cython 모듈 빌드
python build_scripts/build_cython.py

# 3. Nuitka 컴파일
python build_nuitka.py
```

### 방법 4: 통합 빌드 시스템

```cmd
# 빌드 옵션 선택 메뉴 (Nuitka 옵션 선택)
python build_all_options.py
```

## 📁 빌드 결과

성공적으로 빌드되면 **`AutoCalEditor.exe`** 파일이 생성됩니다:

- ✅ **단일 exe 파일** - 다른 파일 없이 독립 실행
- ✅ **콘솔창 숨김** - 깔끔한 GUI 실행
- ✅ **Cython 최적화** - 극한 성능 달성
- ✅ **어디서든 실행** - Python 설치 불필요
- ✅ **Windows COM 지원** - Excel 완벽 연동

## 🔧 문제 해결

### 1. 컴파일러 오류

**Windows - Visual Studio Build Tools 설치**
```cmd
# 다운로드: https://visualstudio.microsoft.com/ko/downloads/
# "C++ 빌드 도구" 워크로드 선택
```

**Linux - GCC 설치**
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install gcc python3-dev

# CentOS/RHEL
sudo yum install gcc python3-devel
```

**macOS - Xcode 설치**
```bash
xcode-select --install
```

### 2. 메모리 부족 오류

```bash
# 빌드 시 병렬 작업 수 줄이기
python -m nuitka --jobs=2 main.py
```

### 3. 의존성 오류

```bash
# 모든 의존성 재설치
pip install --upgrade -r requirements_nuitka.txt
```

### 4. PySide6 관련 오류

```bash
# PySide6 재설치
pip uninstall PySide6
pip install PySide6>=6.5.0
```

## 📊 빌드 최적화 옵션

### 크기 최적화
```python
# build_nuitka.py에서 다음 옵션 추가
'--nofollow-import-to=tkinter',
'--nofollow-import-to=matplotlib',
'--nofollow-import-to=pandas',
```

### 속도 최적화
```python
# build_nuitka.py에서 다음 옵션 추가
'--lto=yes',  # Link Time Optimization
'--jobs=4',   # 병렬 컴파일
```

## 🔍 로그 확인

빌드 과정의 상세 로그는 `nuitka_build.log` 파일에서 확인할 수 있습니다.

```bash
# 실시간 로그 확인 (Linux/Mac)
tail -f nuitka_build.log

# Windows에서 로그 확인
type nuitka_build.log
```

## 💡 팁과 권장사항

### 1. 첫 빌드 시간
- 첫 번째 빌드는 20-30분 소요
- 이후 빌드는 5-10분으로 단축

### 2. 빌드 환경
- SSD 사용 권장 (빌드 속도 향상)
- 최소 8GB RAM 권장
- 안티바이러스 실시간 검사 일시 해제

### 3. 배포 시 주의사항
- 생성된 실행 파일은 독립적으로 실행 가능
- Python 설치 불필요
- 같은 OS 아키텍처에서만 실행 가능

## 🆚 PyInstaller와 비교

| 특징 | Nuitka | PyInstaller |
|------|--------|-------------|
| 실행 속도 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| 시작 시간 | ⭐⭐⭐⭐⭐ | ⭐⭐ |
| 파일 크기 | ⭐⭐⭐⭐ | ⭐⭐ |
| 빌드 시간 | ⭐⭐ | ⭐⭐⭐⭐⭐ |
| 안정성 | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |

## 📞 지원

문제가 발생하면 다음을 확인하세요:

1. `nuitka_build.log` 파일
2. Python 및 컴파일러 버전
3. 사용 가능한 메모리 및 디스크 공간
4. 안티바이러스 소프트웨어 간섭

---

**🎯 결론**: 성능이 중요한 프로덕션 환경에서는 Nuitka를, 빠른 테스트가 필요한 개발 환경에서는 PyInstaller를 사용하세요!
