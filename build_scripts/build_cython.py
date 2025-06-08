#!/usr/bin/env python3
"""
07_Python_DB_Refactoring Cython 빌드 스크립트
성능 최적화를 위한 Cython 확장 모듈 빌드
"""

import os
import sys
import subprocess
import shutil
import logging
from pathlib import Path

# 로깅 설정
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


def check_dependencies():
    """필수 의존성 확인 및 설치"""
    dependencies = ["setuptools", "wheel", "cython", "numpy"]

    for dep in dependencies:
        try:
            __import__(dep)
            logging.info(f"✓ {dep} 이미 설치됨")
        except ImportError:
            logging.info(f"⚠ {dep} 설치 중...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", dep])
            logging.info(f"✓ {dep} 설치 완료")


def clean_build_files():
    """이전 빌드 파일 정리"""
    patterns_to_remove = ["*.c", "*.so", "*.pyd", "build/", "*.egg-info/"]

    current_dir = Path(".")

    for pattern in patterns_to_remove:
        if pattern.endswith("/"):
            # 디렉토리 제거
            for path in current_dir.glob(pattern):
                if path.is_dir():
                    shutil.rmtree(path)
                    logging.info(f"🗑 디렉토리 제거: {path}")
        else:
            # 파일 제거
            for path in current_dir.glob(pattern):
                if path.is_file():
                    path.unlink()
                    logging.info(f"🗑 파일 제거: {path}")


def build_cython_extensions():
    """Cython 확장 모듈 빌드"""
    logging.info("🔨 Cython 확장 모듈 빌드 시작...")

    try:
        # 프로젝트 루트 디렉토리로 이동해서 빌드 실행
        original_cwd = os.getcwd()
        project_root = Path(__file__).parent.parent  # build_scripts의 부모 디렉토리
        os.chdir(project_root)

        logging.info(f"빌드 디렉토리: {project_root}")

        # setup.py build_ext --inplace 실행 (프로젝트 루트에서)
        result = subprocess.run(
            [sys.executable, "build_scripts/setup.py", "build_ext", "--inplace"],
            capture_output=True,
            text=True,
            check=True,
        )

        # 원래 디렉토리로 복귀
        os.chdir(original_cwd)

        logging.info("✓ Cython 빌드 성공")
        logging.info(f"빌드 출력:\n{result.stdout}")

        return True

    except subprocess.CalledProcessError as e:
        # 원래 디렉토리로 복귀
        if "original_cwd" in locals():
            os.chdir(original_cwd)
        logging.error(f"❌ Cython 빌드 실패: {e}")
        logging.error(f"오류 출력:\n{e.stderr}")
        return False
    except Exception as e:
        # 원래 디렉토리로 복귀
        if "original_cwd" in locals():
            os.chdir(original_cwd)
        logging.error(f"❌ 빌드 중 예상치 못한 오류: {e}")
        return False


def verify_build():
    """빌드 결과 검증"""
    # cython_extensions 폴더에서 파일 확인
    project_root = Path(__file__).parent.parent
    cython_dir = project_root / "cython_extensions"

    expected_files = [
        "excel_processor_v2.c",
        "code_generator_v2.c",
        "data_processor.c",
        "regex_optimizer.c",
    ]

    # 플랫폼별 확장자 확인 (실제 생성되는 파일명 패턴)
    if sys.platform == "win32":
        # Windows에서는 .cp311-win_amd64.pyd 형태로 생성됨
        import glob

        for module_name in [
            "excel_processor_v2",
            "code_generator_v2",
            "data_processor",
            "regex_optimizer",
        ]:
            pyd_files = list(cython_dir.glob(f"{module_name}.cp*.pyd"))
            if pyd_files:
                expected_files.extend([f.name for f in pyd_files])
            else:
                expected_files.append(f"{module_name}.pyd")  # 기본 형태도 확인
    else:
        # Linux/Mac에서는 .so 형태
        expected_files.extend(
            [
                "excel_processor_v2.so",
                "code_generator_v2.so",
                "data_processor.so",
                "regex_optimizer.so",
            ]
        )

    missing_files = []
    for file_name in expected_files:
        file_path = cython_dir / file_name
        if not file_path.exists():
            missing_files.append(file_name)

    if missing_files:
        logging.warning(f"⚠ 일부 파일이 생성되지 않음: {missing_files}")
        logging.info(f"확인 경로: {cython_dir}")
        return False
    else:
        logging.info("✓ 모든 빌드 파일 생성 완료")
        logging.info(f"빌드 파일 위치: {cython_dir}")
        return True


def test_imports():
    """빌드된 모듈 import 테스트"""
    # 프로젝트 루트를 Python 경로에 추가
    project_root = Path(__file__).parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    modules_to_test = [
        "cython_extensions.excel_processor_v2",
        "cython_extensions.code_generator_v2",
        "cython_extensions.data_processor",
        "cython_extensions.regex_optimizer",
    ]

    for module in modules_to_test:
        try:
            __import__(module)
            logging.info(f"✓ {module} import 성공")
        except ImportError as e:
            logging.error(f"❌ {module} import 실패: {e}")
            return False

    return True


def create_performance_settings():
    """성능 설정 파일 생성 - 모든 필요한 설정 포함"""
    settings_content = '''"""
07_Python_DB_Refactoring 성능 설정
Cython 최적화 모듈 사용 설정
"""

# Cython 모듈 사용 여부
USE_CYTHON_EXCEL = True
USE_CYTHON_CODE_GEN = True
USE_CYTHON_DATA_PROC = True
USE_CYTHON_CAL_LIST = True

# Float Suffix 기능 설정 (중요: 누락되면 import 에러 발생)
ENABLE_FLOAT_SUFFIX = True

# 성능 모니터링
ENABLE_PERFORMANCE_MONITORING = True

# 배치 처리 크기
EXCEL_BATCH_SIZE = 1000
CODE_GEN_BATCH_SIZE = 500
DB_BATCH_SIZE = 2000

# 캐시 설정
CELL_CACHE_MAX_SIZE = 100000
MEMORY_POOL_SIZE = 1000

def get_cython_status():
    """Cython 모듈 사용 가능 여부 확인"""
    status = {}

    try:
        import cython_extensions.excel_processor_v2
        status['excel_processor'] = True
    except ImportError:
        status['excel_processor'] = False

    try:
        import cython_extensions.code_generator_v2
        status['code_generator'] = True
    except ImportError:
        status['code_generator'] = False

    try:
        import cython_extensions.data_processor
        status['data_processor'] = True
    except ImportError:
        status['data_processor'] = False

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
        logging.warning("⚠ 일부 Cython 모듈을 사용할 수 없습니다. Python 폴백을 사용합니다.")
'''

    with open("performance_settings.py", "w", encoding="utf-8") as f:
        f.write(settings_content)

    logging.info("✓ performance_settings.py 생성 완료")


def main():
    """메인 빌드 프로세스"""
    logging.info("🚀 07_Python_DB_Refactoring Cython 빌드 시작")

    # 1. 의존성 확인
    check_dependencies()

    # 2. 이전 빌드 파일 정리
    clean_build_files()

    # 3. Cython 확장 모듈 빌드
    if not build_cython_extensions():
        logging.error("❌ 빌드 실패")
        sys.exit(1)

    # 4. 빌드 결과 검증
    if not verify_build():
        logging.warning("⚠ 빌드 검증에서 일부 문제 발견")

    # 5. import 테스트
    if not test_imports():
        logging.error("❌ 모듈 import 테스트 실패")
        sys.exit(1)

    # 6. 성능 설정 파일 생성
    create_performance_settings()

    logging.info("🎉 Cython 빌드 완료! 성능 최적화가 활성화되었습니다.")
    logging.info("📝 performance_settings.py에서 설정을 확인하세요.")


if __name__ == "__main__":
    main()
