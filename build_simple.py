#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Simple AutoCalEditor Build Script
Direct PyInstaller execution without intermediate scripts
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

def clean_build():
    """Clean previous build files"""
    cleanup_dirs = ['build', 'dist', '__pycache__']
    for dir_name in cleanup_dirs:
        if os.path.exists(dir_name):
            shutil.rmtree(dir_name)
            logging.info(f"Cleaned: {dir_name}")

def find_cython_modules():
    """Find Cython modules"""
    cython_dir = Path("cython_extensions")
    modules = []
    
    if sys.platform == "win32":
        for pyd_file in cython_dir.glob("*.pyd"):
            modules.append(str(pyd_file))
        for pyd_file in cython_dir.glob("*.cp*.pyd"):
            modules.append(str(pyd_file))
    else:
        for so_file in cython_dir.glob("*.so"):
            modules.append(str(so_file))
    
    return modules

def build_with_pyinstaller():
    """Build directly with PyInstaller"""
    logging.info("Building with PyInstaller...")

    # Clean previous builds
    clean_build()

    # Find Cython modules
    cython_modules = find_cython_modules()
    logging.info(f"Found Cython modules: {len(cython_modules)}")

    # Build PyInstaller command
    cmd = [
        sys.executable, '-m', 'PyInstaller',
        '--onefile',
        '--noconsole',
        '--name=AutoCalEditor',
        '--clean',
        'main.py'
    ]

    # Add Cython modules as binary files
    for module in cython_modules:
        cmd.extend(['--add-binary', f'{module};cython_extensions'])

    # Add hidden imports
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
        'core.data_parser', 'utils.git_manager'
    ]

    for import_name in hidden_imports:
        cmd.extend(['--hidden-import', import_name])

    # Execute PyInstaller with timeout
    logging.info("Starting PyInstaller build...")
    logging.info("This may take several minutes...")

    try:
        # Set environment variables
        env = os.environ.copy()
        env['PYTHONIOENCODING'] = 'utf-8'

        result = subprocess.run(cmd, check=True, text=True,
                              encoding='utf-8', errors='replace',
                              env=env, timeout=900)  # 15 minute timeout

        # Check result
        exe_path = Path('dist/AutoCalEditor.exe')
        if exe_path.exists():
            size_mb = exe_path.stat().st_size / (1024 * 1024)
            logging.info(f"Build successful! File: {exe_path} ({size_mb:.1f} MB)")
            return True
        else:
            logging.error("Executable not found")
            return False

    except subprocess.TimeoutExpired:
        logging.error("Build timeout (15 minutes)")
        return False
    except subprocess.CalledProcessError as e:
        logging.error(f"PyInstaller failed: {e}")
        return False
    except Exception as e:
        logging.error(f"Build error: {e}")
        return False

def check_dependencies():
    """Check required dependencies"""
    # Correct import names: package name vs import name can be different
    required = {
        'PyInstaller': 'PyInstaller',  # pip install pyinstaller, import PyInstaller
        'PySide6': 'PySide6',
        'numpy': 'numpy',
        'openpyxl': 'openpyxl'
    }
    missing = []

    for display_name, import_name in required.items():
        try:
            __import__(import_name)
            logging.info(f"✓ {display_name}")
        except ImportError:
            logging.error(f"✗ {display_name}")
            missing.append(display_name)

    if missing:
        logging.error(f"Missing: {', '.join(missing)}")
        logging.error("Install with: pip install " + " ".join(missing))
        return False
    return True

def main():
    """Main build function"""
    logging.info("Simple AutoCalEditor build started")

    if not os.path.exists('main.py'):
        logging.error("main.py not found. Run from project root.")
        return False

    if not check_dependencies():
        return False
    
    if build_with_pyinstaller():
        logging.info("Build completed successfully!")
        logging.info("Run: ./dist/AutoCalEditor.exe")
        return True
    else:
        logging.error("Build failed!")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
