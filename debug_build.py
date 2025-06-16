#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Debug Build Script for AutoCalEditor
Diagnose build issues step by step
"""

import os
import sys
import logging
import subprocess
from pathlib import Path

# Windows encoding fix
os.environ['PYTHONIOENCODING'] = 'utf-8'
os.environ['PYTHONUTF8'] = '1'

# Logging setup
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def check_environment():
    """Check build environment"""
    logging.info("=== Environment Check ===")
    
    # Python version
    logging.info(f"Python version: {sys.version}")
    
    # Current directory
    logging.info(f"Current directory: {os.getcwd()}")
    
    # Check main.py
    if os.path.exists('main.py'):
        logging.info("main.py: Found")
    else:
        logging.error("main.py: NOT FOUND")
        return False
    
    # Check required modules
    required_modules = ['PySide6', 'numpy', 'openpyxl']
    for module in required_modules:
        try:
            __import__(module)
            logging.info(f"{module}: Available")
        except ImportError:
            logging.error(f"{module}: NOT AVAILABLE")
    
    # Check Cython modules
    cython_dir = Path("cython_extensions")
    if cython_dir.exists():
        pyd_files = list(cython_dir.glob("*.pyd")) + list(cython_dir.glob("*.cp*.pyd"))
        logging.info(f"Cython modules: {len(pyd_files)} found")
        for pyd in pyd_files:
            logging.info(f"  - {pyd.name}")
    else:
        logging.warning("cython_extensions directory not found")
    
    return True

def test_pyinstaller():
    """Test PyInstaller availability"""
    logging.info("=== PyInstaller Test ===")
    
    try:
        result = subprocess.run([
            sys.executable, '-m', 'PyInstaller', '--version'
        ], capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            logging.info(f"PyInstaller version: {result.stdout.strip()}")
            return True
        else:
            logging.error("PyInstaller not working")
            return False
            
    except subprocess.TimeoutExpired:
        logging.error("PyInstaller version check timeout")
        return False
    except Exception as e:
        logging.error(f"PyInstaller test failed: {e}")
        return False

def test_simple_build():
    """Test simple PyInstaller build"""
    logging.info("=== Simple Build Test ===")
    
    try:
        # Create minimal test script
        test_script = "test_build.py"
        with open(test_script, 'w') as f:
            f.write("""
import sys
print("Hello from test build!")
sys.exit(0)
""")
        
        # Try to build it
        cmd = [
            sys.executable, '-m', 'PyInstaller',
            '--onefile',
            '--clean',
            '--distpath=test_dist',
            '--workpath=test_build',
            test_script
        ]
        
        logging.info("Testing simple PyInstaller build...")
        result = subprocess.run(cmd, capture_output=True, text=True, 
                              timeout=120, encoding='utf-8', errors='replace')
        
        # Cleanup
        import shutil
        if os.path.exists(test_script):
            os.remove(test_script)
        if os.path.exists('test_dist'):
            shutil.rmtree('test_dist')
        if os.path.exists('test_build'):
            shutil.rmtree('test_build')
        if os.path.exists('test_build.spec'):
            os.remove('test_build.spec')
        
        if result.returncode == 0:
            logging.info("Simple build test: PASSED")
            return True
        else:
            logging.error("Simple build test: FAILED")
            logging.error(f"Error: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        logging.error("Simple build test: TIMEOUT")
        return False
    except Exception as e:
        logging.error(f"Simple build test error: {e}")
        return False

def main():
    """Main debug function"""
    logging.info("AutoCalEditor Build Debug Started")
    logging.info("=" * 50)
    
    # Step 1: Environment check
    if not check_environment():
        logging.error("Environment check failed")
        return False
    
    # Step 2: PyInstaller test
    if not test_pyinstaller():
        logging.error("PyInstaller test failed")
        return False
    
    # Step 3: Simple build test
    if not test_simple_build():
        logging.error("Simple build test failed")
        return False
    
    logging.info("=" * 50)
    logging.info("All tests passed! Environment is ready for build.")
    logging.info("Try running: python build_simple.py")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
