#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AutoCalEditor Windows 전용 Nuitka 컴파일 스크립트
Cython 통합 + 콘솔 숨김 + 단일 exe 파일
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
        logging.FileHandler('nuitka_build_windows.log', mode='w', encoding='utf-8')
    ]
)

def check_windows():
    """Windows 환경 확인"""
    if sys.platform != 'win32':
        logging.error("❌ 이 스크립트는 Windows 전용입니다.")
        return False
    logging.info("✅ Windows 환경 확인")
    return True

def install_nuitka():
    """Nuitka 자동 설치"""
    logging.info("🔧 Nuitka 설치 중...")
    try:
        subprocess.run([sys.executable, '-m', 'pip', 'install', '-r', 'requirements_nuitka.txt'], 
                      check=True, timeout=300)
        logging.info("✅ Nuitka 및 의존성 설치 완료")
        return True
    except Exception as e:
        logging.error(f"❌ 설치 실패: {e}")
        return False

def build_cython_first():
    """Cython 모듈 우선 빌드"""
    logging.info("🔧 Cython 모듈 빌드 중...")
    try:
        result = subprocess.run([
            sys.executable, 'build_scripts/build_cython.py'
        ], capture_output=True, text=True, timeout=300)
        
        if result.returncode == 0:
            logging.info("✅ Cython 모듈 빌드 완료")
            return True
        else:
            logging.error(f"❌ Cython 빌드 실패: {result.stderr}")
            return False
    except Exception as e:
        logging.error(f"❌ Cython 빌드 오류: {e}")
        return False

def build_nuitka_optimized():
    """최적화된 Nuitka 빌드"""
    logging.info("🚀 Nuitka 최적화 컴파일 시작...")
    
    # 이전 빌드 정리
    cleanup_dirs = ['main.build', 'main.dist', 'AutoCalEditor.build', 'AutoCalEditor.dist']
    for dir_name in cleanup_dirs:
        if os.path.exists(dir_name):
            shutil.rmtree(dir_name)
            logging.info(f"정리: {dir_name}")
    
    # 기존 exe 파일 삭제
    if os.path.exists('AutoCalEditor.exe'):
        os.remove('AutoCalEditor.exe')
        logging.info("기존 AutoCalEditor.exe 삭제")
    
    # Nuitka 명령어 (Windows 최적화)
    cmd = [
        sys.executable, '-m', 'nuitka',
        '--standalone',
        '--onefile',
        '--output-filename=AutoCalEditor.exe',
        '--windows-disable-console',  # 콘솔 숨김
        '--assume-yes-for-downloads',
        '--remove-output',
        
        # 성능 최적화
        '--lto=yes',
        '--jobs=4',
        
        # 플러그인
        '--enable-plugin=pyside6',
        
        # Cython 모듈 포함
        '--include-module=cython_extensions.excel_processor_v2',
        '--include-module=cython_extensions.code_generator_v2',
        '--include-module=cython_extensions.data_processor',
        '--include-module=cython_extensions.regex_optimizer',
        
        # Windows COM 지원
        '--include-module=win32com.client',
        '--include-module=pythoncom',
        '--include-module=pywintypes',
        
        # 핵심 모듈
        '--include-module=numpy',
        '--include-module=openpyxl',
        '--include-module=xlwings',
        '--include-module=sqlite3',
        '--include-module=PySide6.QtCore',
        '--include-module=PySide6.QtGui',
        '--include-module=PySide6.QtWidgets',
        '--include-module=PySide6.QtSql',
        
        # 불필요한 모듈 제외
        '--nofollow-import-to=tkinter',
        '--nofollow-import-to=matplotlib',
        '--nofollow-import-to=pandas',
        '--nofollow-import-to=scipy',
        '--nofollow-import-to=IPython',
        '--nofollow-import-to=jupyter',
        
        'main.py'
    ]
    
    logging.info("컴파일 시작... (예상 시간: 15-30분)")
    start_time = time.time()
    
    try:
        result = subprocess.run(cmd, timeout=1800)  # 30분 타임아웃
        elapsed = time.time() - start_time
        
        if result.returncode == 0 and os.path.exists('AutoCalEditor.exe'):
            size_mb = os.path.getsize('AutoCalEditor.exe') / (1024 * 1024)
            logging.info(f"✅ 컴파일 성공!")
            logging.info(f"📁 파일: AutoCalEditor.exe ({size_mb:.1f} MB)")
            logging.info(f"⏱️ 소요 시간: {elapsed/60:.1f}분")
            return True
        else:
            logging.error("❌ 컴파일 실패")
            return False
            
    except subprocess.TimeoutExpired:
        logging.error("❌ 컴파일 타임아웃")
        return False
    except Exception as e:
        logging.error(f"❌ 컴파일 오류: {e}")
        return False

def main():
    """메인 함수"""
    print("=" * 60)
    print("AutoCalEditor Windows 전용 Nuitka 고성능 빌드")
    print("=" * 60)
    print("🎯 Windows 최적화 + Cython 가속 + 콘솔 숨김")
    print("📦 단일 exe 파일로 어디서든 실행 가능")
    print("⚡ PyInstaller보다 2-5배 빠른 성능")
    print()
    
    # 1. Windows 확인
    if not check_windows():
        return False
    
    # 2. 프로젝트 루트 확인
    if not os.path.exists('main.py'):
        logging.error("❌ main.py를 찾을 수 없습니다. 프로젝트 루트에서 실행하세요.")
        return False
    
    # 3. 의존성 설치
    if not install_nuitka():
        return False
    
    # 4. Cython 빌드
    if not build_cython_first():
        logging.warning("⚠️ Cython 빌드 실패, 기본 Python 코드로 진행")
    
    # 5. Nuitka 컴파일
    if build_nuitka_optimized():
        print()
        print("=" * 60)
        print("🎉 빌드 완료!")
        print("=" * 60)
        print("📁 파일: AutoCalEditor.exe")
        print("🚀 실행: .\\AutoCalEditor.exe")
        print("⚡ 극한 성능을 경험하세요!")
        print("📦 이 파일 하나로 어디서든 실행 가능합니다!")
        return True
    else:
        print()
        print("❌ 빌드 실패!")
        print("📝 nuitka_build_windows.log 파일을 확인하세요.")
        return False

if __name__ == "__main__":
    success = main()
    input("\n계속하려면 Enter를 누르세요...")
    sys.exit(0 if success else 1)
