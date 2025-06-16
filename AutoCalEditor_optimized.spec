# -*- mode: python ; coding: utf-8 -*-
"""
AutoCalEditor PyInstaller Spec File (최적화 버전)
콘솔창 숨김, 경로 문제 해결, 성능 최적화 적용
"""

import os
import sys
from pathlib import Path

# 프로젝트 루트 경로 설정
project_root = Path(os.getcwd())

block_cipher = None

# Cython 모듈 자동 탐지
def find_cython_binaries():
    """Cython 모듈을 자동으로 찾아서 binaries 목록 생성"""
    cython_dir = project_root / "cython_extensions"
    binaries = []
    
    if cython_dir.exists():
        if sys.platform == "win32":
            # Windows: .pyd 파일들
            for pyd_file in cython_dir.glob("*.pyd"):
                binaries.append((str(pyd_file), 'cython_extensions'))
            for pyd_file in cython_dir.glob("*.cp*.pyd"):
                binaries.append((str(pyd_file), 'cython_extensions'))
        else:
            # Linux/Mac: .so 파일들
            for so_file in cython_dir.glob("*.so"):
                binaries.append((str(so_file), 'cython_extensions'))
    
    # 중복 제거
    return list(set(binaries))

# 데이터 파일 자동 탐지
def find_data_files():
    """필요한 데이터 파일들 자동 탐지"""
    datas = []
    
    # subprocess_helper.py 추가 (콘솔창 숨김용)
    subprocess_helper = project_root / "utils" / "subprocess_helper.py"
    if subprocess_helper.exists():
        datas.append((str(subprocess_helper), 'utils'))
    
    # 설정 파일들 추가 (있다면)
    config_files = ['config.ini', 'settings.json', 'requirements.txt']
    for config_file in config_files:
        config_path = project_root / config_file
        if config_path.exists():
            datas.append((str(config_path), '.'))
    
    # 아이콘 파일 추가 (있다면)
    icon_files = ['icon.ico', 'app.ico', 'AutoCalEditor.ico']
    for icon_file in icon_files:
        icon_path = project_root / icon_file
        if icon_path.exists():
            datas.append((str(icon_path), '.'))
    
    return datas

# 숨겨진 import 목록 (최적화됨)
hidden_imports = [
    # PySide6 핵심 모듈
    'PySide6.QtCore',
    'PySide6.QtGui', 
    'PySide6.QtWidgets',
    'PySide6.QtSql',
    
    # Python 표준 라이브러리
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
    
    # Windows 전용 (조건부)
    'win32com.client',
    'win32com.gen_py',
    'pythoncom',
    'pywintypes',
    
    # 서드파티 라이브러리
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
    'utils.subprocess_helper',
    'code_generator.code_generator',
    'code_generator.original_file_surrogate',
]

# 제외할 모듈 (성능 최적화)
excludes = [
    'tkinter',
    'matplotlib',
    'IPython',
    'jupyter',
    'notebook',
    'pandas',  # 사용하지 않는다면
    'scipy',   # 사용하지 않는다면
    'PIL',     # 사용하지 않는다면
    'cv2',     # 사용하지 않는다면
    'pytest',
    'setuptools',
    'distutils',
]

a = Analysis(
    ['main.py'],
    pathex=[str(project_root)],
    binaries=find_cython_binaries(),
    datas=find_data_files(),
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# 중복 제거 및 최적화
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# 아이콘 파일 찾기
def find_icon():
    """아이콘 파일 자동 탐지"""
    icon_files = ['icon.ico', 'app.ico', 'AutoCalEditor.ico']
    for icon_file in icon_files:
        icon_path = project_root / icon_file
        if icon_path.exists():
            return str(icon_path)
    return None

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
    console=False,  # 콘솔창 완전 숨김
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=find_icon(),  # 아이콘 자동 탐지
    # Windows 전용 최적화 설정
    uac_admin=False,
    uac_uiaccess=False,
)
