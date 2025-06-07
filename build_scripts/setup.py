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

# Cython 확장 모듈 정의 (결과물 위치 지정)
extensions = [
    Extension(
        "cython_extensions.excel_processor_v2",
        ["cython_extensions/excel_processor_v2.pyx"],
        include_dirs=[numpy.get_include()]
    ),
    Extension(
        "cython_extensions.code_generator_v2",
        ["cython_extensions/code_generator_v2.pyx"],
        include_dirs=[numpy.get_include()]
    ),
    Extension(
        "cython_extensions.data_processor",
        ["cython_extensions/data_processor.pyx"],
        include_dirs=[numpy.get_include()]
    ),
    Extension(
        "cython_extensions.regex_optimizer",
        ["cython_extensions/regex_optimizer.pyx"],
        include_dirs=[numpy.get_include()]
    )
]

setup(
    name="07_Python_DB_Refactoring Cython Extensions",
    ext_modules=cythonize(extensions, compiler_directives={
        'language_level': 3,
        'boundscheck': False,
        'wraparound': False,
        'cdivision': True
    }),
    zip_safe=False
)
