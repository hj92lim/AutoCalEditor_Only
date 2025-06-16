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
        # Windows encoding fix: UTF-8 forced setting with timeout
        result = subprocess.run([
            sys.executable, 'build_scripts/build_cython.py'
        ], capture_output=True, text=True, encoding='utf-8', errors='replace',
        timeout=300, check=True)  # 5 minute timeout

        logging.info("Cython build successful")
        if result.stdout:
            logging.debug(f"Cython build output: {result.stdout}")
        return True

    except subprocess.TimeoutExpired:
        logging.error("Cython build timeout (5 minutes)")
        return False
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
    """Build PyInstaller executable with timeout and better error handling"""
    logging.info("Step 2: Building PyInstaller executable")

    try:
        # Use simple subprocess.run with timeout instead of Popen
        env = os.environ.copy()
        env['PYTHONIOENCODING'] = 'utf-8'

        result = subprocess.run([
            sys.executable, 'build_scripts/build_exe.py'
        ], capture_output=True, text=True, encoding='utf-8', errors='replace',
        env=env, timeout=600)  # 10 minute timeout

        if result.returncode == 0:
            logging.info("PyInstaller build successful")
            if result.stdout:
                logging.info(f"Build output: {result.stdout}")
            return True
        else:
            logging.error(f"PyInstaller build failed with return code: {result.returncode}")
            if result.stderr:
                logging.error(f"Error output: {result.stderr}")
            if result.stdout:
                logging.error(f"Standard output: {result.stdout}")
            return False

    except subprocess.TimeoutExpired:
        logging.error("PyInstaller build timeout (10 minutes)")
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

def check_dependencies():
    """Check required dependencies before build"""
    logging.info("Checking build dependencies...")

    # Correct import names for each package
    required_modules = {
        'PyInstaller': ('PyInstaller', 'pip install pyinstaller'),  # Package: pyinstaller, Import: PyInstaller
        'PySide6': ('PySide6', 'pip install PySide6'),
        'numpy': ('numpy', 'pip install numpy'),
        'openpyxl': ('openpyxl', 'pip install openpyxl')
    }

    missing = []
    for display_name, (import_name, install_cmd) in required_modules.items():
        try:
            module = __import__(import_name)
            # Try to get version if available
            version = getattr(module, '__version__', 'unknown')
            logging.info(f"✓ {display_name}: Available (v{version})")
        except ImportError as e:
            logging.error(f"✗ {display_name}: Missing - {e}")
            missing.append((display_name, install_cmd))

    if missing:
        logging.error("Missing required dependencies:")
        for module, cmd in missing:
            logging.error(f"  {module}: {cmd}")
        return False

    logging.info("All dependencies available")
    return True

def main():
    """Main build process"""
    logging.info("AutoCalEditor complete build started")
    logging.info("=" * 50)

    # Check project root
    if not os.path.exists('main.py'):
        logging.error("main.py not found. Please run from project root.")
        return False

    # Check dependencies first
    if not check_dependencies():
        logging.error("Dependency check failed. Please install missing packages.")
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
