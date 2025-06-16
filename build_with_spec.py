#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AutoCalEditor Spec 파일 기반 빌드 스크립트
최적화된 spec 파일을 사용한 안전한 빌드
"""

import os
import sys
import logging
import subprocess
import shutil
from pathlib import Path

# Windows encoding fix
os.environ['PYTHONIOENCODING'] = 'utf-8'
os.environ['PYTHONUTF8'] = '1'

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def ensure_project_root():
    """프로젝트 루트 디렉토리로 이동"""
    current_dir = Path.cwd()
    
    # main.py가 있는 디렉토리를 찾을 때까지 상위로 이동
    search_dir = current_dir
    for _ in range(5):
        if (search_dir / 'main.py').exists():
            if search_dir != current_dir:
                logging.info(f"프로젝트 루트로 이동: {current_dir} -> {search_dir}")
                os.chdir(search_dir)
            return True
        search_dir = search_dir.parent
    
    logging.error(f"main.py를 찾을 수 없습니다. 현재 위치: {current_dir}")
    return False

def check_dependencies():
    """필수 의존성 확인"""
    required = {
        'PyInstaller': 'PyInstaller',
        'PySide6': 'PySide6',
        'numpy': 'numpy', 
        'openpyxl': 'openpyxl'
    }
    missing = []
    
    for display_name, import_name in required.items():
        try:
            module = __import__(import_name)
            version = getattr(module, '__version__', 'unknown')
            logging.info(f"✓ {display_name}: v{version}")
        except ImportError:
            logging.error(f"✗ {display_name}: 누락")
            missing.append(display_name)
    
    if missing:
        logging.error(f"누락된 패키지: {', '.join(missing)}")
        logging.error("설치 명령어: pip install " + " ".join(missing))
        return False
    return True

def clean_build():
    """이전 빌드 파일 정리"""
    cleanup_dirs = ['build', 'dist', '__pycache__']
    for dir_name in cleanup_dirs:
        if os.path.exists(dir_name):
            shutil.rmtree(dir_name)
            logging.info(f"정리 완료: {dir_name}")

def check_spec_file():
    """spec 파일 존재 확인"""
    spec_files = ['AutoCalEditor_optimized.spec', 'AutoCalEditor.spec']
    
    for spec_file in spec_files:
        if os.path.exists(spec_file):
            logging.info(f"spec 파일 발견: {spec_file}")
            return spec_file
    
    logging.error("spec 파일을 찾을 수 없습니다.")
    logging.error("다음 중 하나가 필요합니다:")
    for spec_file in spec_files:
        logging.error(f"  - {spec_file}")
    return None

def build_with_spec(spec_file):
    """spec 파일을 사용한 빌드"""
    logging.info(f"spec 파일로 빌드 시작: {spec_file}")
    
    # 이전 빌드 정리
    clean_build()
    
    # PyInstaller 명령어 구성
    cmd = [
        sys.executable, '-m', 'PyInstaller',
        '--clean',
        spec_file
    ]
    
    logging.info("PyInstaller 실행 중... (최대 15분 소요)")
    logging.info(f"명령어: {' '.join(cmd)}")
    
    try:
        # 환경변수 설정
        env = os.environ.copy()
        env['PYTHONIOENCODING'] = 'utf-8'
        env['PYTHONUTF8'] = '1'
        
        # Windows에서 콘솔창 숨김
        kwargs = {
            'env': env,
            'timeout': 900,  # 15분 타임아웃
            'text': True,
            'encoding': 'utf-8',
            'errors': 'replace',
            'capture_output': True
        }
        
        if sys.platform == "win32":
            kwargs['creationflags'] = subprocess.CREATE_NO_WINDOW
        
        result = subprocess.run(cmd, **kwargs)
        
        if result.returncode == 0:
            # 빌드 결과 확인
            exe_path = Path('dist/AutoCalEditor.exe')
            if exe_path.exists():
                size_mb = exe_path.stat().st_size / (1024 * 1024)
                logging.info(f"✅ 빌드 성공! 파일: {exe_path} ({size_mb:.1f} MB)")
                return True
            else:
                logging.error("❌ 실행 파일이 생성되지 않았습니다.")
                return False
        else:
            logging.error(f"❌ PyInstaller 빌드 실패 (코드: {result.returncode})")
            if result.stderr:
                logging.error(f"오류 출력: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        logging.error("❌ 빌드 타임아웃 (15분)")
        return False
    except Exception as e:
        logging.error(f"❌ 빌드 오류: {e}")
        return False

def main():
    """메인 빌드 함수"""
    logging.info("=== Spec 파일 기반 AutoCalEditor 빌드 ===")
    
    # 1. 프로젝트 루트로 이동
    if not ensure_project_root():
        return False
    
    # 2. 의존성 확인
    if not check_dependencies():
        return False
    
    # 3. spec 파일 확인
    spec_file = check_spec_file()
    if not spec_file:
        return False
    
    # 4. 빌드 실행
    if build_with_spec(spec_file):
        logging.info("🎉 빌드 완료!")
        logging.info("📁 결과: dist/AutoCalEditor.exe")
        logging.info("🚀 실행: ./dist/AutoCalEditor.exe")
        return True
    else:
        logging.error("💥 빌드 실패!")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
