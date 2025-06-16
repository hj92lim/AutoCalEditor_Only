#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Simple AutoCalEditor Build Script
Direct PyInstaller execution without intermediate scripts
경로 문제 완전 해결 버전
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
    """프로젝트 루트 디렉토리로 이동 (경로 문제 해결)"""
    current_dir = Path.cwd()
    
    # main.py가 있는 디렉토리를 찾을 때까지 상위로 이동
    search_dir = current_dir
    for _ in range(5):  # 최대 5단계까지 상위 검색
        if (search_dir / 'main.py').exists():
            if search_dir != current_dir:
                logging.info(f"프로젝트 루트로 이동: {current_dir} -> {search_dir}")
                os.chdir(search_dir)
            return True
        search_dir = search_dir.parent
    
    # 현재 디렉토리에 main.py가 있는지 확인
    if (current_dir / 'main.py').exists():
        return True
    
    logging.error(f"main.py를 찾을 수 없습니다. 현재 위치: {current_dir}")
    return False

def clean_build():
    """이전 빌드 파일 정리"""
    cleanup_dirs = ['build', 'dist', '__pycache__']
    for dir_name in cleanup_dirs:
        if os.path.exists(dir_name):
            shutil.rmtree(dir_name)
            logging.info(f"정리 완료: {dir_name}")

def find_cython_modules():
    """Cython 모듈 찾기 (경로 안전)"""
    cython_dir = Path("cython_extensions")
    modules = []
    
    if not cython_dir.exists():
        logging.warning(f"Cython 디렉토리 없음: {cython_dir.absolute()}")
        return modules
    
    if sys.platform == "win32":
        # Windows: .pyd files
        for pyd_file in cython_dir.glob("*.pyd"):
            modules.append(str(pyd_file))
        for pyd_file in cython_dir.glob("*.cp*.pyd"):
            modules.append(str(pyd_file))
    else:
        # Linux/Mac: .so files
        for so_file in cython_dir.glob("*.so"):
            modules.append(str(so_file))
    
    # 중복 제거
    modules = list(set(modules))
    return modules

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

def build_with_pyinstaller():
    """PyInstaller로 직접 빌드 (경로 안전)"""
    logging.info("PyInstaller 빌드 시작...")
    
    # 현재 작업 디렉토리 확인
    current_dir = os.getcwd()
    logging.info(f"빌드 디렉토리: {current_dir}")
    
    # 이전 빌드 정리
    clean_build()
    
    # Cython 모듈 찾기
    cython_modules = find_cython_modules()
    logging.info(f"Cython 모듈 {len(cython_modules)}개 발견")
    
    # PyInstaller 명령어 구성
    cmd = [
        sys.executable, '-m', 'PyInstaller',
        '--onefile',
        '--noconsole',
        '--name=AutoCalEditor',
        '--clean',
        'main.py'
    ]
    
    # Cython 모듈을 바이너리로 추가
    for module in cython_modules:
        cmd.extend(['--add-binary', f'{module};cython_extensions'])
    
    # 숨겨진 import 추가
    hidden_imports = [
        'PySide6.QtCore', 'PySide6.QtGui', 'PySide6.QtWidgets', 'PySide6.QtSql',
        'sqlite3', 'json', 'csv', 'logging', 'tempfile', 'shutil',
        'subprocess', 'threading', 'queue', 'datetime', 'pathlib',
        'win32com.client', 'pythoncom', 'numpy', 'openpyxl', 'xlwings',
        'cython_extensions.excel_processor_v2',
        'cython_extensions.code_generator_v2',
        'cython_extensions.data_processor',
        'cython_extensions.regex_optimizer',
        'core.info', 'core.constants',
        'data_manager.db_handler_v2', 'data_manager.db_manager',
        'excel_processor.excel_importer', 'excel_processor.excel_exporter',
        'ui.ui_components', 'ui.git_status_dialog',
        'core.data_parser', 'utils.git_manager',
        'code_generator.code_generator', 'code_generator.original_file_surrogate'
    ]
    
    for import_name in hidden_imports:
        cmd.extend(['--hidden-import', import_name])
    
    # Windows 콘솔창 숨김 옵션 추가
    if sys.platform == "win32":
        cmd.extend([
            '--add-data', 'utils/subprocess_helper.py;utils',
            '--exclude-module', 'tkinter',
            '--exclude-module', 'matplotlib'
        ])
    
    # 빌드 실행
    logging.info("PyInstaller 실행 중... (최대 15분 소요)")
    logging.info(f"명령어: {' '.join(cmd[:10])}... (총 {len(cmd)}개 인수)")
    
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
            'errors': 'replace'
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
            return False
            
    except subprocess.TimeoutExpired:
        logging.error("❌ 빌드 타임아웃 (15분)")
        return False
    except Exception as e:
        logging.error(f"❌ 빌드 오류: {e}")
        return False

def main():
    """메인 빌드 함수"""
    logging.info("=== Simple AutoCalEditor Build ===")
    
    # 1. 프로젝트 루트로 이동
    if not ensure_project_root():
        return False
    
    # 2. 의존성 확인
    if not check_dependencies():
        return False
    
    # 3. 빌드 실행
    if build_with_pyinstaller():
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
