"""
Cython 확장 모듈 빌드를 위한 setup.py 스크립트.

이 스크립트는 setuptools를 사용하여 Cython으로 작성된 .pyx 파일들을 C 코드로 변환하고,
이를 컴파일하여 공유 라이브러리(예: .so 또는 .pyd 파일)로 만듭니다.
Cython, setuptools, wheel, numpy 등의 의존성을 자동으로 확인하고 설치합니다.

주요 기능:
- Cython 확장 모듈 정의 (excel_processor_v2, code_generator_v2, data_processor, regex_optimizer)
- 컴파일러 지시문 설정을 통한 Cython 빌드 최적화
- numpy include 디렉토리 자동 포함
"""

try:
    from setuptools import setup
except ImportError:
    print("setuptools not found. Installing...")
    import subprocess
    import sys

    subprocess.check_call(
        [sys.executable, "-m", "pip", "install", "setuptools", "wheel"]
    )
    from setuptools import setup

try:
    from Cython.Build import cythonize
except ImportError:
    print("Cython not found. Installing...")
    import subprocess
    import sys

    subprocess.check_call([sys.executable, "-m", "pip", "install", "cython"])
    from Cython.Build import cythonize

try:
    import numpy
except ImportError:
    print("numpy not found. Installing...")
    import subprocess
    import sys

    subprocess.check_call([sys.executable, "-m", "pip", "install", "numpy"])
    import numpy

from distutils.extension import Extension

# Cython 확장 모듈 정의 (결과물 위치 지정)
extensions = [
    Extension(
        "cython_extensions.excel_processor_v2",
        ["cython_extensions/excel_processor_v2.pyx"],
        include_dirs=[numpy.get_include()],
    ),
    Extension(
        "cython_extensions.code_generator_v2",
        ["cython_extensions/code_generator_v2.pyx"],
        include_dirs=[numpy.get_include()],
    ),
    Extension(
        "cython_extensions.data_processor",
        ["cython_extensions/data_processor.pyx"],
        include_dirs=[numpy.get_include()],
    ),
    Extension(
        "cython_extensions.regex_optimizer",
        ["cython_extensions/regex_optimizer.pyx"],
        include_dirs=[numpy.get_include()],
    ),
]

setup(
    name="07_Python_DB_Refactoring Cython Extensions",
    ext_modules=cythonize(
        extensions,
        compiler_directives={
            "language_level": 3,
            "boundscheck": False,
            "wraparound": False,
            "cdivision": True,
        },
    ),
    zip_safe=False,
)
