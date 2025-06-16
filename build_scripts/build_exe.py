#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🚀 AutoCalEditor PyInstaller 빌드 스크립트
Cython 모듈 포함, --onefile --noconsole 지원
"""

import os
import sys
import shutil
import subprocess
import logging
from pathlib import Path
import glob

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('build.log', encoding='utf-8')
    ]
)

def find_cython_modules():
    """Cython 컴파일된 모듈 찾기"""
    cython_dir = Path("cython_extensions")
    modules = []
    
    if sys.platform == "win32":
        # Windows: .pyd 파일들
        for pyd_file in cython_dir.glob("*.pyd"):
            modules.append(str(pyd_file))
        # cp311-win_amd64.pyd 형태도 포함
        for pyd_file in cython_dir.glob("*.cp*.pyd"):
            modules.append(str(pyd_file))
    else:
        # Linux/Mac: .so 파일들
        for so_file in cython_dir.glob("*.so"):
            modules.append(str(so_file))
    
    logging.info(f"발견된 Cython 모듈: {modules}")
    return modules

def get_hidden_imports():
    """숨겨진 import 목록"""
    return [
        # PySide6 관련
        'PySide6.QtCore',
        'PySide6.QtGui', 
        'PySide6.QtWidgets',
        'PySide6.QtSql',
        
        # 표준 라이브러리
        'sqlite3',
        'json',
        'csv',
        'logging',
        'tempfile',
        'shutil',
        'subprocess',
        'threading',
        'queue',
        'datetime',
        'pathlib',
        'glob',
        'traceback',
        'gc',
        'platform',
        'uuid',
        'hashlib',
        
        # 서드파티 라이브러리
        'win32com.client',
        'win32com.gen_py',
        'pythoncom',
        'pywintypes',
        'numpy',
        'openpyxl',
        'xlwings',
        
        # Cython 확장 모듈
        'cython_extensions.excel_processor_v2',
        'cython_extensions.code_generator_v2', 
        'cython_extensions.data_processor',
        'cython_extensions.regex_optimizer',
        
        # 프로젝트 모듈
        'core.info',
        'core.constants',
        'data_manager.db_handler_v2',
        'data_manager.db_manager',
        'excel_processor.excel_importer',
        'excel_processor.excel_exporter',
        'ui.ui_components',
        'ui.git_status_dialog',
        'core.data_parser',
        'utils.git_manager',
        'code_generator.code_generator',
        'code_generator.original_file_surrogate',
    ]

def get_data_files():
    """데이터 파일 목록"""
    data_files = []
    
    # Cython 모듈들
    cython_modules = find_cython_modules()
    for module in cython_modules:
        data_files.append((module, 'cython_extensions'))
    
    # 기타 필요한 파일들
    if os.path.exists('README.md'):
        data_files.append(('README.md', '.'))
    
    if os.path.exists('requirements.txt'):
        data_files.append(('requirements.txt', '.'))
        
    # 설정 파일들 (있다면)
    config_files = ['config.ini', 'settings.json']
    for config_file in config_files:
        if os.path.exists(config_file):
            data_files.append((config_file, '.'))
    
    return data_files

def create_spec_file():
    """PyInstaller spec 파일 생성"""
    spec_content = f'''# -*- mode: python ; coding: utf-8 -*-

import sys
from pathlib import Path

# 프로젝트 루트 경로
project_root = Path(__file__).parent

block_cipher = None

# 숨겨진 import 목록
hidden_imports = {get_hidden_imports()}

# 데이터 파일 목록
datas = {get_data_files()}

# 바이너리 파일 (Cython 모듈 포함)
binaries = []

# Cython 모듈들을 바이너리로 추가
cython_modules = {find_cython_modules()}
for module_path in cython_modules:
    binaries.append((module_path, 'cython_extensions'))

a = Analysis(
    ['main.py'],
    pathex=[str(project_root)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes=[
        # 불필요한 모듈 제외
        'tkinter',
        'matplotlib',
        'IPython',
        'jupyter',
        'notebook',
        'pandas',  # 사용하지 않는다면
        'scipy',   # 사용하지 않는다면
        'PIL',     # 사용하지 않는다면
        'cv2',     # 사용하지 않는다면
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# 중복 제거
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='AutoCalEditor',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # --noconsole
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='icon.ico' if Path('icon.ico').exists() else None,
)
'''
    
    with open('AutoCalEditor.spec', 'w', encoding='utf-8') as f:
        f.write(spec_content)
    
    logging.info("✓ spec 파일 생성 완료: AutoCalEditor.spec")

def build_executable():
    """실행 파일 빌드"""
    try:
        logging.info("🔨 PyInstaller 빌드 시작...")
        
        # 1. 이전 빌드 결과 정리
        cleanup_dirs = ['build', 'dist', '__pycache__']
        for dir_name in cleanup_dirs:
            if os.path.exists(dir_name):
                shutil.rmtree(dir_name)
                logging.info(f"✓ 이전 빌드 디렉토리 정리: {dir_name}")
        
        # 2. spec 파일 생성
        create_spec_file()
        
        # 3. PyInstaller 실행
        cmd = [
            sys.executable, '-m', 'PyInstaller',
            '--clean',  # 캐시 정리
            'AutoCalEditor.spec'
        ]
        
        logging.info(f"실행 명령어: {' '.join(cmd)}")
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace'
        )
        
        if result.returncode == 0:
            logging.info("✅ PyInstaller 빌드 성공!")
            logging.info(f"빌드 출력:\\n{result.stdout}")
            
            # 빌드 결과 확인
            exe_path = Path('dist/AutoCalEditor.exe')
            if exe_path.exists():
                size_mb = exe_path.stat().st_size / (1024 * 1024)
                logging.info(f"✓ 실행 파일 생성: {exe_path} ({size_mb:.1f} MB)")
                return True
            else:
                logging.error("❌ 실행 파일이 생성되지 않았습니다.")
                return False
        else:
            logging.error("❌ PyInstaller 빌드 실패!")
            logging.error(f"오류 출력:\\n{result.stderr}")
            return False
            
    except Exception as e:
        logging.error(f"❌ 빌드 중 예외 발생: {e}")
        return False

def main():
    """메인 빌드 함수"""
    logging.info("🚀 AutoCalEditor 빌드 시작")
    
    # 현재 디렉토리 확인
    if not os.path.exists('main.py'):
        logging.error("❌ main.py 파일을 찾을 수 없습니다. 프로젝트 루트에서 실행하세요.")
        return False
    
    # Cython 모듈 확인
    cython_modules = find_cython_modules()
    if not cython_modules:
        logging.warning("⚠️ Cython 모듈을 찾을 수 없습니다. 먼저 Cython 빌드를 실행하세요.")
        logging.info("Cython 빌드 명령어: python build_scripts/build_cython.py")
    
    # 빌드 실행
    if build_executable():
        logging.info("🎉 빌드 완료! dist/AutoCalEditor.exe 파일을 확인하세요.")
        return True
    else:
        logging.error("💥 빌드 실패!")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
