try:
    from setuptools import setup
except ImportError:
    print("setuptools not found. Installing...")
    import subprocess
    import sys
    subprocess.check_call([sys.executable, "-m", "pip", "install", "setuptools", "wheel"])
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
import platform

# 컴파일러 최적화 플래그 설정
extra_compile_args = []
extra_link_args = []

if platform.system() == "Windows":
    # Windows MSVC 컴파일러 최적화 (안전한 버전)
    extra_compile_args = [
        "/O2",          # 최대 속도 최적화
        "/Ot",          # 속도 우선 최적화
        "/Oy",          # 프레임 포인터 생략
        "/GL",          # 전체 프로그램 최적화
        # "/arch:AVX2", # AVX2 제거 (호환성 문제)
    ]
    extra_link_args = [
        "/LTCG",        # Link Time Code Generation
    ]
else:
    # Linux/macOS GCC 컴파일러 최적화
    extra_compile_args = [
        "-O3",          # 최대 최적화
        "-march=native", # 현재 CPU에 최적화
        "-mtune=native",
        "-ffast-math",  # 빠른 수학 연산
        "-funroll-loops", # 루프 언롤링
    ]

# Cython 확장 모듈 정의 (성능 최적화 적용)
extensions = [
    Extension(
        "cython_extensions.excel_processor_v2",
        ["cython_extensions/excel_processor_v2.pyx"],
        include_dirs=[numpy.get_include()],
        extra_compile_args=extra_compile_args,
        extra_link_args=extra_link_args
    ),
    Extension(
        "cython_extensions.code_generator_v2",
        ["cython_extensions/code_generator_v2.pyx"],
        include_dirs=[numpy.get_include()],
        extra_compile_args=extra_compile_args,
        extra_link_args=extra_link_args
    ),
    Extension(
        "cython_extensions.data_processor",
        ["cython_extensions/data_processor.pyx"],
        include_dirs=[numpy.get_include()],
        extra_compile_args=extra_compile_args,
        extra_link_args=extra_link_args
    ),
    Extension(
        "cython_extensions.regex_optimizer",
        ["cython_extensions/regex_optimizer.pyx"],
        include_dirs=[numpy.get_include()],
        extra_compile_args=extra_compile_args,
        extra_link_args=extra_link_args
    )
]

setup(
    name="07_Python_DB_Refactoring Cython Extensions",
    ext_modules=cythonize(extensions, compiler_directives={
        'language_level': 3,
        'boundscheck': False,
        'wraparound': False,
        'cdivision': True,
        'initializedcheck': False,  # 초기화 검사 비활성화
        'overflowcheck': False,     # 오버플로우 검사 비활성화
        'nonecheck': False,         # None 검사 비활성화
        'embedsignature': False,    # 시그니처 임베딩 비활성화
        'optimize.use_switch': True, # switch 문 최적화
        'optimize.unpack_method_calls': True, # 메서드 호출 최적화
    }),
    zip_safe=False
)
