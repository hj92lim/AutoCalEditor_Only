#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AutoCalEditor Complete Build Script
Cython Compilation -> PyInstaller Build -> Result Verification
"""

import os
import sys
import logging
import subprocess
from pathlib import Path

# Windows encoding fix: environment variables
os.environ['PYTHONIOENCODING'] = 'utf-8'
os.environ['PYTHONUTF8'] = '1'

# Logging setup (UTF-8 encoding forced)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
    ]
)

def run_cython_build():
    """Build Cython modules"""
    logging.info("Step 1: Building Cython modules")

    try:
        # Windows encoding fix: UTF-8 forced setting
        result = subprocess.run([
            sys.executable, 'build_scripts/build_cython.py'
        ], capture_output=True, text=True, encoding='utf-8', errors='replace', check=True)

        logging.info("Cython build successful")
        if result.stdout:
            logging.debug(f"Cython build output: {result.stdout}")
        return True

    except subprocess.CalledProcessError as e:
        logging.error(f"Cython build failed: {e}")
        if e.stderr:
            logging.error(f"Error output: {e.stderr}")
        if e.stdout:
            logging.error(f"Standard output: {e.stdout}")
        return False
    except Exception as e:
        logging.error(f"Exception during Cython build: {e}")
        return False

def run_pyinstaller_build():
    """Build PyInstaller executable"""
    logging.info("Step 2: Building PyInstaller executable")

    try:
        # Windows encoding fix: UTF-8 forced setting
        result = subprocess.run([
            sys.executable, 'build_scripts/build_exe.py'
        ], capture_output=True, text=True, encoding='utf-8', errors='replace', check=True)

        logging.info("PyInstaller build successful")
        if result.stdout:
            logging.debug(f"PyInstaller build output: {result.stdout}")
        return True

    except subprocess.CalledProcessError as e:
        logging.error(f"PyInstaller build failed: {e}")
        if e.stderr:
            logging.error(f"Error output: {e.stderr}")
        if e.stdout:
            logging.error(f"Standard output: {e.stdout}")
        return False
    except Exception as e:
        logging.error(f"Exception during PyInstaller build: {e}")
        return False

def verify_build_result():
    """Verify build result"""
    logging.info("Step 3: Verifying build result")

    exe_path = Path('dist/AutoCalEditor.exe')
    if exe_path.exists():
        size_mb = exe_path.stat().st_size / (1024 * 1024)
        logging.info(f"Executable file created successfully: {exe_path}")
        logging.info(f"File size: {size_mb:.1f} MB")

        # Executable file test (optional)
        logging.info("Testing executable file...")
        try:
            # Windows encoding fix: UTF-8 forced setting
            test_result = subprocess.run([
                str(exe_path), '--help'
            ], capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=10)

            if test_result.returncode == 0:
                logging.info("Executable file test successful")
            else:
                logging.warning("Executable file test failed (may be normal)")

        except subprocess.TimeoutExpired:
            logging.info("Executable file test timeout (normal for GUI app)")
        except Exception as e:
            logging.warning(f"Error during executable file test: {e}")

        return True
    else:
        logging.error("Executable file was not created.")
        return False

def main():
    """Main build process"""
    logging.info("AutoCalEditor complete build started")
    logging.info("=" * 50)

    # Check project root
    if not os.path.exists('main.py'):
        logging.error("main.py not found. Please run from project root.")
        return False

    # Step 1: Cython build
    if not run_cython_build():
        logging.error("Build stopped due to Cython build failure")
        return False

    # Step 2: PyInstaller build
    if not run_pyinstaller_build():
        logging.error("Build stopped due to PyInstaller build failure")
        return False

    # Step 3: Result verification
    if not verify_build_result():
        logging.error("Build result verification failed")
        return False

    logging.info("=" * 50)
    logging.info("Complete build finished!")
    logging.info("Result file: dist/AutoCalEditor.exe")
    logging.info("Run command: ./dist/AutoCalEditor.exe")

    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
