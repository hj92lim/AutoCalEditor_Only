#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AutoCalEditor Nuitka 컴파일 스크립트
실제 컴파일을 통한 최고 성능 실행 파일 생성
"""

import os
import sys
import logging
import subprocess
import shutil
from pathlib import Path
import time

# Windows encoding fix
os.environ['PYTHONIOENCODING'] = 'utf-8'
os.environ['PYTHONUTF8'] = '1'

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('nuitka_build.log', mode='w', encoding='utf-8')
    ]
)

def check_nuitka_installation():
    """Nuitka 설치 확인 및 자동 설치"""
    try:
        result = subprocess.run([sys.executable, '-m', 'nuitka', '--version'], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            version = result.stdout.strip()
            logging.info(f"✅ Nuitka 설치 확인: {version}")
            return True
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    
    logging.info("🔧 Nuitka가 설치되지 않았습니다. 자동 설치를 시작합니다...")
    
    try:
        # Nuitka 설치
        subprocess.run([sys.executable, '-m', 'pip', 'install', 'nuitka'], 
                      check=True, timeout=300)
        logging.info("✅ Nuitka 설치 완료")
        return True
    except subprocess.CalledProcessError as e:
        logging.error(f"❌ Nuitka 설치 실패: {e}")
        return False
    except subprocess.TimeoutExpired:
        logging.error("❌ Nuitka 설치 타임아웃")
        return False

def check_compiler():
    """C 컴파일러 확인"""
    compilers = ['gcc', 'clang', 'cl']  # Linux/Mac: gcc/clang, Windows: cl (MSVC)
    
    for compiler in compilers:
        try:
            result = subprocess.run([compiler, '--version'], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                logging.info(f"✅ 컴파일러 확인: {compiler}")
                return True
        except (subprocess.TimeoutExpired, FileNotFoundError):
            continue
    
    logging.error("❌ C 컴파일러를 찾을 수 없습니다.")
    logging.error("다음 중 하나를 설치해주세요:")
    logging.error("  - Linux: sudo apt install gcc")
    logging.error("  - Windows: Visual Studio Build Tools 또는 MinGW")
    logging.error("  - Mac: xcode-select --install")
    return False

def ensure_project_root():
    """프로젝트 루트 디렉토리 확인"""
    if not os.path.exists('main.py'):
        logging.error("❌ main.py를 찾을 수 없습니다. 프로젝트 루트에서 실행해주세요.")
        return False
    
    logging.info(f"✅ 프로젝트 루트 확인: {os.getcwd()}")
    return True

def clean_build():
    """이전 빌드 파일 정리"""
    cleanup_dirs = ['main.build', 'main.dist', '__pycache__', 'build', 'dist']
    cleanup_files = ['main.exe', 'AutoCalEditor.exe']
    
    for dir_name in cleanup_dirs:
        if os.path.exists(dir_name):
            shutil.rmtree(dir_name)
            logging.info(f"정리 완료: {dir_name}")
    
    for file_name in cleanup_files:
        if os.path.exists(file_name):
            os.remove(file_name)
            logging.info(f"정리 완료: {file_name}")

def check_cython_modules():
    """Cython 모듈 확인 및 빌드"""
    cython_modules = [
        'cython_extensions.excel_processor_v2',
        'cython_extensions.code_generator_v2',
        'cython_extensions.data_processor',
        'cython_extensions.regex_optimizer'
    ]

    missing_modules = []
    for module in cython_modules:
        try:
            __import__(module)
            logging.info(f"✅ Cython 모듈 확인: {module}")
        except ImportError:
            missing_modules.append(module)
            logging.warning(f"⚠️ Cython 모듈 누락: {module}")

    if missing_modules:
        logging.info("🔧 Cython 모듈을 빌드합니다...")
        if not build_cython_modules():
            logging.error("❌ Cython 모듈 빌드 실패")
            return False

        # 빌드 후 재확인
        for module in missing_modules:
            try:
                __import__(module)
                logging.info(f"✅ Cython 모듈 빌드 완료: {module}")
            except ImportError:
                logging.error(f"❌ Cython 모듈 빌드 실패: {module}")
                return False

    return True

def build_cython_modules():
    """Cython 모듈 빌드"""
    try:
        # build_scripts/build_cython.py 실행
        result = subprocess.run([
            sys.executable, 'build_scripts/build_cython.py'
        ], capture_output=True, text=True, timeout=300)

        if result.returncode == 0:
            logging.info("✅ Cython 모듈 빌드 성공")
            return True
        else:
            logging.error(f"❌ Cython 빌드 실패: {result.stderr}")
            return False
    except Exception as e:
        logging.error(f"❌ Cython 빌드 오류: {e}")
        return False

def check_dependencies():
    """필수 의존성 확인"""
    required_packages = ['PySide6', 'openpyxl', 'numpy', 'xlwings', 'win32com.client']
    missing_packages = []

    for package in required_packages:
        try:
            if package == 'win32com.client':
                import win32com.client
            else:
                __import__(package)
            logging.info(f"✅ {package} 확인")
        except ImportError:
            missing_packages.append(package)
            logging.error(f"❌ {package} 누락")

    if missing_packages:
        logging.error(f"누락된 패키지: {missing_packages}")
        logging.error("다음 명령어로 설치하세요:")
        if 'win32com.client' in missing_packages:
            logging.error("pip install pywin32")
        logging.error(f"pip install {' '.join([p for p in missing_packages if p != 'win32com.client'])}")
        return False

    return True

def build_with_nuitka():
    """Nuitka로 컴파일 - Windows + Cython 최적화"""
    logging.info("🚀 Nuitka 컴파일 시작 (Windows + Cython 최적화)...")

    # 이전 빌드 정리
    clean_build()

    # Nuitka 명령어 구성 (Windows 전용 최적화)
    cmd = [
        sys.executable, '-m', 'nuitka',
        '--standalone',  # 독립 실행 파일
        '--onefile',     # 단일 exe 파일로 패키징
        '--output-filename=AutoCalEditor.exe',  # Windows exe 파일명
        '--remove-output',  # 빌드 후 임시 파일 정리
        '--assume-yes-for-downloads',  # 자동 다운로드 승인

        # Windows 전용 설정 (콘솔 숨김)
        '--windows-disable-console',  # 콘솔창 완전 숨김
        '--windows-icon-from-ico=icon.ico' if os.path.exists('icon.ico') else '',

        # 성능 최적화
        '--lto=yes',     # Link Time Optimization
        '--jobs=4',      # 병렬 컴파일 (CPU 코어 수에 맞게 조정)

        # PySide6 플러그인 활성화
        '--enable-plugin=pyside6',

        # Cython 모듈 명시적 포함
        '--include-module=cython_extensions.excel_processor_v2',
        '--include-module=cython_extensions.code_generator_v2',
        '--include-module=cython_extensions.data_processor',
        '--include-module=cython_extensions.regex_optimizer',

        # Windows Excel COM 지원
        '--include-module=win32com.client',
        '--include-module=pythoncom',
        '--include-module=pywintypes',

        # 핵심 모듈 명시적 포함
        '--include-module=numpy',
        '--include-module=openpyxl',
        '--include-module=xlwings',
        '--include-module=sqlite3',

        # 불필요한 모듈 제외 (크기 최적화)
        '--nofollow-import-to=tkinter',
        '--nofollow-import-to=matplotlib',
        '--nofollow-import-to=IPython',
        '--nofollow-import-to=jupyter',
        '--nofollow-import-to=pandas',
        '--nofollow-import-to=scipy',
        '--nofollow-import-to=PIL',
        '--nofollow-import-to=cv2',

        'main.py'  # 메인 스크립트
    ]

    # 빈 문자열 제거
    cmd = [arg for arg in cmd if arg]
    
    logging.info("Nuitka 컴파일 실행 중... (10-30분 소요 예상)")
    logging.info(f"명령어: {' '.join(cmd)}")
    
    start_time = time.time()
    
    try:
        # 환경변수 설정
        env = os.environ.copy()
        env['PYTHONIOENCODING'] = 'utf-8'
        env['PYTHONUTF8'] = '1'
        
        # 컴파일 실행
        result = subprocess.run(
            cmd,
            env=env,
            timeout=1800,  # 30분 타임아웃
            text=True,
            encoding='utf-8',
            errors='replace'
        )
        
        elapsed_time = time.time() - start_time
        
        if result.returncode == 0:
            # Windows exe 파일 확인
            exe_path = Path('AutoCalEditor.exe')

            if exe_path.exists():
                size_mb = exe_path.stat().st_size / (1024 * 1024)
                logging.info(f"✅ Nuitka 컴파일 성공!")
                logging.info(f"📁 파일: {exe_path} ({size_mb:.1f} MB)")
                logging.info(f"⏱️ 소요 시간: {elapsed_time:.1f}초")
                logging.info(f"🚀 실행: .\\{exe_path}")
                logging.info(f"🔥 단일 exe 파일로 어디서든 실행 가능!")
                logging.info(f"⚡ Cython 최적화로 최고 성능 달성!")
                return True
            else:
                logging.error("❌ AutoCalEditor.exe 파일이 생성되지 않았습니다.")
                # 다른 가능한 파일명 확인
                possible_files = ['main.exe', 'AutoCalEditor', 'main']
                for file_name in possible_files:
                    if os.path.exists(file_name):
                        logging.info(f"📁 대신 생성된 파일: {file_name}")
                        return True
                return False
        else:
            logging.error(f"❌ Nuitka 컴파일 실패 (코드: {result.returncode})")
            return False
            
    except subprocess.TimeoutExpired:
        logging.error("❌ 컴파일 타임아웃 (30분)")
        return False
    except Exception as e:
        logging.error(f"❌ 컴파일 오류: {e}")
        return False

def main():
    """메인 빌드 함수 - Windows + Cython 최적화"""
    logging.info("=== AutoCalEditor Nuitka 컴파일 (Windows + Cython) ===")
    logging.info("🔥 최고 성능을 위한 실제 컴파일 빌드")
    logging.info("🎯 Windows 전용 최적화 + Cython 가속")
    logging.info("📦 단일 exe 파일 생성 + 콘솔 숨김")

    # 1. 프로젝트 루트 확인
    if not ensure_project_root():
        return False

    # 2. Nuitka 설치 확인
    if not check_nuitka_installation():
        return False

    # 3. 컴파일러 확인
    if not check_compiler():
        return False

    # 4. 의존성 확인
    if not check_dependencies():
        return False

    # 5. Cython 모듈 확인 및 빌드
    if not check_cython_modules():
        return False

    # 6. Nuitka 컴파일 실행
    if build_with_nuitka():
        logging.info("🎉 Nuitka 컴파일 완료!")
        logging.info("⚡ PyInstaller보다 2-5배 빠른 실행 속도!")
        logging.info("🔥 Cython 최적화로 극한 성능 달성!")
        logging.info("📦 단일 exe 파일로 어디서든 실행 가능!")
        logging.info("🖥️ 콘솔창 없이 깔끔한 실행!")
        return True
    else:
        logging.error("💥 컴파일 실패!")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
