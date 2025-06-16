#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🚀 AutoCalEditor 전체 빌드 스크립트
Cython 컴파일 → PyInstaller 빌드 → 결과 확인
"""

import os
import sys
import logging
import subprocess
from pathlib import Path

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def run_cython_build():
    """Cython 모듈 빌드"""
    logging.info("🔨 1단계: Cython 모듈 빌드")
    
    try:
        result = subprocess.run([
            sys.executable, 'build_scripts/build_cython.py'
        ], capture_output=True, text=True, check=True)
        
        logging.info("✅ Cython 빌드 성공")
        return True
        
    except subprocess.CalledProcessError as e:
        logging.error(f"❌ Cython 빌드 실패: {e}")
        logging.error(f"오류 출력: {e.stderr}")
        return False

def run_pyinstaller_build():
    """PyInstaller 실행 파일 빌드"""
    logging.info("🔨 2단계: PyInstaller 실행 파일 빌드")
    
    try:
        result = subprocess.run([
            sys.executable, 'build_scripts/build_exe.py'
        ], capture_output=True, text=True, check=True)
        
        logging.info("✅ PyInstaller 빌드 성공")
        return True
        
    except subprocess.CalledProcessError as e:
        logging.error(f"❌ PyInstaller 빌드 실패: {e}")
        logging.error(f"오류 출력: {e.stderr}")
        return False

def verify_build_result():
    """빌드 결과 확인"""
    logging.info("🔍 3단계: 빌드 결과 확인")
    
    exe_path = Path('dist/AutoCalEditor.exe')
    if exe_path.exists():
        size_mb = exe_path.stat().st_size / (1024 * 1024)
        logging.info(f"✅ 실행 파일 생성 완료: {exe_path}")
        logging.info(f"📦 파일 크기: {size_mb:.1f} MB")
        
        # 실행 파일 테스트 (선택사항)
        logging.info("🧪 실행 파일 테스트 중...")
        try:
            # --version 옵션이 있다면 테스트
            test_result = subprocess.run([
                str(exe_path), '--help'
            ], capture_output=True, text=True, timeout=10)
            
            if test_result.returncode == 0:
                logging.info("✅ 실행 파일 테스트 성공")
            else:
                logging.warning("⚠️ 실행 파일 테스트 실패 (정상일 수 있음)")
                
        except subprocess.TimeoutExpired:
            logging.info("⏰ 실행 파일 테스트 타임아웃 (GUI 앱이므로 정상)")
        except Exception as e:
            logging.warning(f"⚠️ 실행 파일 테스트 중 오류: {e}")
        
        return True
    else:
        logging.error("❌ 실행 파일이 생성되지 않았습니다.")
        return False

def main():
    """메인 빌드 프로세스"""
    logging.info("🚀 AutoCalEditor 전체 빌드 시작")
    logging.info("=" * 50)
    
    # 프로젝트 루트 확인
    if not os.path.exists('main.py'):
        logging.error("❌ main.py를 찾을 수 없습니다. 프로젝트 루트에서 실행하세요.")
        return False
    
    # 1단계: Cython 빌드
    if not run_cython_build():
        logging.error("💥 Cython 빌드 실패로 중단")
        return False
    
    # 2단계: PyInstaller 빌드  
    if not run_pyinstaller_build():
        logging.error("💥 PyInstaller 빌드 실패로 중단")
        return False
    
    # 3단계: 결과 확인
    if not verify_build_result():
        logging.error("💥 빌드 결과 확인 실패")
        return False
    
    logging.info("=" * 50)
    logging.info("🎉 전체 빌드 완료!")
    logging.info("📁 결과 파일: dist/AutoCalEditor.exe")
    logging.info("🚀 실행 방법: ./dist/AutoCalEditor.exe")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
