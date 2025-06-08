"""
07_Python_DB_Refactoring 성능 설정
Cython 최적화 모듈 사용 설정
"""

import configparser
import os

# --- Configuration Setup ---
config = configparser.ConfigParser()
# Construct the path to config.ini relative to this file's location (core/performance_settings.py)
# This assumes config.ini is in the project root, one level above 'core'
config_file_path = os.path.join(os.path.dirname(__file__), "..", "config.ini")
config.read(config_file_path, encoding="utf-8")

# --- Cython Settings ---
USE_CYTHON_EXCEL = config.getboolean("Cython", "USE_CYTHON_EXCEL", fallback=True)
USE_CYTHON_CODE_GEN = config.getboolean("Cython", "USE_CYTHON_CODE_GEN", fallback=True)
USE_CYTHON_DATA_PROC = config.getboolean(
    "Cython", "USE_CYTHON_DATA_PROC", fallback=True
)
USE_CYTHON_CAL_LIST = config.getboolean("Cython", "USE_CYTHON_CAL_LIST", fallback=True)

# --- Feature Enablement ---
ENABLE_FLOAT_SUFFIX = config.getboolean(
    "Features", "ENABLE_FLOAT_SUFFIX", fallback=True
)  # Float Suffix 기능 설정 (중요: 누락되면 import 에러 발생)
ENABLE_PERFORMANCE_MONITORING = config.getboolean(
    "Features", "ENABLE_PERFORMANCE_MONITORING", fallback=True
)  # 성능 모니터링

# --- Batch Size Settings ---
EXCEL_BATCH_SIZE = config.getint(
    "BatchSize", "EXCEL_BATCH_SIZE", fallback=1000
)  # 배치 처리 크기
CODE_GEN_BATCH_SIZE = config.getint("BatchSize", "CODE_GEN_BATCH_SIZE", fallback=500)
DB_BATCH_SIZE = config.getint("BatchSize", "DB_BATCH_SIZE", fallback=2000)

# --- Cache Settings ---
CELL_CACHE_MAX_SIZE = config.getint(
    "Cache", "CELL_CACHE_MAX_SIZE", fallback=100000
)  # 캐시 설정
MEMORY_POOL_SIZE = config.getint("Cache", "MEMORY_POOL_SIZE", fallback=1000)


def get_cython_status():
    """Cython 모듈 사용 가능 여부 확인"""
    status = {}

    try:
        import cython_extensions.excel_processor_v2

        status["excel_processor"] = True
    except ImportError:
        status["excel_processor"] = False

    try:
        import cython_extensions.code_generator_v2

        status["code_generator"] = True
    except ImportError:
        status["code_generator"] = False

    try:
        import cython_extensions.data_processor

        status["data_processor"] = True
    except ImportError:
        status["data_processor"] = False

    return status


def log_performance_status():
    """성능 최적화 상태 로깅"""
    import logging

    status = get_cython_status()

    logging.info("=== Cython 성능 최적화 상태 ===")
    for module, available in status.items():
        status_text = "✓ 사용 가능" if available else "❌ 사용 불가"
        logging.info(f"{module}: {status_text}")

    if all(status.values()):
        logging.info("🚀 모든 Cython 최적화 모듈이 활성화되었습니다!")
    else:
        logging.warning(
            "⚠ 일부 Cython 모듈을 사용할 수 없습니다. Python 폴백을 사용합니다."
        )
