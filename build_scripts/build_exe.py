#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AutoCalEditor PyInstaller Build Script
Includes Cython modules, supports --onefile --noconsole
"""

import os
import sys
import shutil
import subprocess
import logging
from pathlib import Path
import glob

# Windows encoding fix: environment variables
os.environ['PYTHONIOENCODING'] = 'utf-8'
os.environ['PYTHONUTF8'] = '1'

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('build.log', encoding='utf-8')
    ]
)

def find_cython_modules():
    """Find compiled Cython modules"""
    cython_dir = Path("cython_extensions")
    modules = []

    if sys.platform == "win32":
        # Windows: .pyd files
        for pyd_file in cython_dir.glob("*.pyd"):
            modules.append(str(pyd_file))
        # Include cp311-win_amd64.pyd format
        for pyd_file in cython_dir.glob("*.cp*.pyd"):
            modules.append(str(pyd_file))
    else:
        # Linux/Mac: .so files
        for so_file in cython_dir.glob("*.so"):
            modules.append(str(so_file))

    logging.info(f"Found Cython modules: {modules}")
    return modules

def get_hidden_imports():
    """Hidden import list"""
    return [
        # PySide6 related
        'PySide6.QtCore',
        'PySide6.QtGui',
        'PySide6.QtWidgets',
        'PySide6.QtSql',

        # Standard library
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

        # Third-party libraries
        'win32com.client',
        'win32com.gen_py',
        'pythoncom',
        'pywintypes',
        'numpy',
        'openpyxl',
        'xlwings',

        # Cython extension modules
        'cython_extensions.excel_processor_v2',
        'cython_extensions.code_generator_v2',
        'cython_extensions.data_processor',
        'cython_extensions.regex_optimizer',

        # Project modules
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
    """Data files list"""
    data_files = []

    # Cython modules
    cython_modules = find_cython_modules()
    for module in cython_modules:
        data_files.append((module, 'cython_extensions'))

    # Other necessary files
    if os.path.exists('README.md'):
        data_files.append(('README.md', '.'))

    if os.path.exists('requirements.txt'):
        data_files.append(('requirements.txt', '.'))

    # Config files (if any)
    config_files = ['config.ini', 'settings.json']
    for config_file in config_files:
        if os.path.exists(config_file):
            data_files.append((config_file, '.'))

    return data_files

def create_spec_file():
    """Generate PyInstaller spec file"""
    spec_content = f'''# -*- mode: python ; coding: utf-8 -*-

import sys
import os
from pathlib import Path

# Project root path - fix for __file__ not defined error
project_root = Path(os.getcwd())

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

    logging.info("Spec file generation completed: AutoCalEditor.spec")

def build_executable():
    """Build executable file"""
    try:
        logging.info("PyInstaller build started...")

        # 1. Clean previous build results
        cleanup_dirs = ['build', 'dist', '__pycache__']
        for dir_name in cleanup_dirs:
            if os.path.exists(dir_name):
                shutil.rmtree(dir_name)
                logging.info(f"Previous build directory cleaned: {dir_name}")

        # 2. Generate spec file
        create_spec_file()

        # 3. Run PyInstaller
        cmd = [
            sys.executable, '-m', 'PyInstaller',
            '--clean',  # Clean cache
            'AutoCalEditor.spec'
        ]

        logging.info(f"Execution command: {' '.join(cmd)}")

        # Windows encoding fix: environment variables
        env = os.environ.copy()
        env['PYTHONIOENCODING'] = 'utf-8'

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',
            env=env
        )

        if result.returncode == 0:
            logging.info("PyInstaller build successful!")
            logging.info(f"Build output:\\n{result.stdout}")

            # Check build result
            exe_path = Path('dist/AutoCalEditor.exe')
            if exe_path.exists():
                size_mb = exe_path.stat().st_size / (1024 * 1024)
                logging.info(f"Executable file created: {exe_path} ({size_mb:.1f} MB)")
                return True
            else:
                logging.error("Executable file was not created.")
                return False
        else:
            logging.error("PyInstaller build failed!")
            logging.error(f"Error output:\\n{result.stderr}")
            return False

    except Exception as e:
        logging.error(f"Exception occurred during build: {e}")
        return False

def check_pyinstaller():
    """Check if PyInstaller is available"""
    try:
        import PyInstaller  # Correct import name (capital P and I)
        logging.info(f"PyInstaller available: {PyInstaller.__version__}")
        return True
    except ImportError:
        logging.error("PyInstaller not found. Install with: pip install pyinstaller")
        return False

def main():
    """Main build function"""
    logging.info("AutoCalEditor build started")

    # Check current directory
    if not os.path.exists('main.py'):
        logging.error("main.py file not found. Please run from project root.")
        return False

    # Check PyInstaller availability
    if not check_pyinstaller():
        return False

    # Check Cython modules
    cython_modules = find_cython_modules()
    if not cython_modules:
        logging.warning("Cython modules not found. Please run Cython build first.")
        logging.info("Cython build command: python build_scripts/build_cython.py")

    # Execute build
    if build_executable():
        logging.info("Build completed! Check dist/AutoCalEditor.exe file.")
        return True
    else:
        logging.error("Build failed!")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
