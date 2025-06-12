"""
코드 생성 모듈 성능 프로파일링 및 병목 지점 분석
"""

import time
import cProfile
import pstats
import io
import logging
from typing import List, Dict, Any
import sys
from pathlib import Path

# 프로젝트 루트 경로 설정
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s'
)

def create_large_test_data(size: int = 10000) -> List[List[str]]:
    """대용량 테스트 데이터 생성"""
    test_data = []
    for i in range(size):
        test_data.append([
            "DEFINE",
            "CONST", 
            "FLOAT32",
            f"TEST_VALUE_{i}",
            str(i * 1.5),
            f"Test value {i} description"
        ])
    return test_data

def python_reference_implementation(temp_code_items: List[List[str]]) -> List[List[str]]:
    """Python 참조 구현 (최적화된 버전)"""
    if not temp_code_items:
        return []
    
    processed_items = []
    
    for line_str in temp_code_items:
        if line_str and len(line_str) >= 6:
            op_code = line_str[0] if line_str[0] else ""
            key_str = line_str[1] if line_str[1] else ""
            type_str = line_str[2] if line_str[2] else ""
            name_str = line_str[3] if line_str[3] else ""
            val_str = line_str[4] if line_str[4] else ""
            desc_str = line_str[5] if line_str[5] else ""
            
            # FLOAT32 변수의 숫자에 f 접미사 추가
            if val_str and type_str and "FLOAT32" in type_str:
                val_str = add_float_suffix_python(val_str, type_str)
            
            processed_items.append([op_code, key_str, type_str, name_str, val_str, desc_str])
        else:
            processed_items.append(line_str)
    
    return processed_items

def add_float_suffix_python(val_str: str, type_str: str) -> str:
    """Python 버전 float suffix 추가"""
    if "float" not in type_str.lower():
        return val_str
    
    if not val_str or val_str.endswith('f') or val_str.endswith('F'):
        return val_str
    
    if '/*' in val_str or '//' in val_str:
        return val_str
    
    # 간단한 숫자 패턴 확인
    try:
        # 정수인지 확인
        if val_str.isdigit() or (val_str.startswith('-') and val_str[1:].isdigit()):
            if val_str == '0':
                return '0.f'
            else:
                return val_str + '.f'
        
        # 소수점 숫자인지 확인
        float(val_str)
        if '.' in val_str:
            return val_str + 'f'
        else:
            return val_str + '.f'
    except ValueError:
        return val_str

def profile_function(func, *args, **kwargs):
    """함수 프로파일링"""
    pr = cProfile.Profile()
    pr.enable()
    
    start_time = time.perf_counter()
    result = func(*args, **kwargs)
    end_time = time.perf_counter()
    
    pr.disable()
    
    # 프로파일링 결과 분석
    s = io.StringIO()
    ps = pstats.Stats(pr, stream=s).sort_stats('cumulative')
    ps.print_stats(20)  # 상위 20개 함수
    
    return {
        'result': result,
        'execution_time': end_time - start_time,
        'profile_stats': s.getvalue()
    }

def detailed_performance_analysis():
    """상세 성능 분석"""
    print("🔍 코드 생성 모듈 상세 성능 분석")
    print("=" * 80)
    
    # 다양한 크기의 테스트 데이터로 성능 측정
    test_sizes = [100, 1000, 5000, 10000]
    
    for size in test_sizes:
        print(f"\n📊 테스트 데이터 크기: {size:,}개")
        print("-" * 40)
        
        test_data = create_large_test_data(size)
        
        # Python 버전 프로파일링
        python_result = profile_function(python_reference_implementation, test_data)
        python_time = python_result['execution_time']
        
        print(f"Python 실행 시간: {python_time:.6f}초")
        
        # Cython 버전 프로파일링
        try:
            from cython_extensions.code_generator_v2 import fast_write_cal_list_processing
            cython_result = profile_function(fast_write_cal_list_processing, test_data)
            cython_time = cython_result['execution_time']
            
            print(f"Cython 실행 시간: {cython_time:.6f}초")
            
            if cython_time > 0:
                speedup = python_time / cython_time
                print(f"성능 비율: {speedup:.2f}배 ({'빠름' if speedup > 1 else '느림'})")
            
            # 결과 검증
            if len(python_result['result']) == len(cython_result['result']):
                print("✅ 결과 일치성: 정상")
            else:
                print("❌ 결과 일치성: 불일치")
                
        except ImportError as e:
            print(f"❌ Cython 모듈 import 실패: {e}")
        
        # 메모리 사용량 분석
        import psutil
        process = psutil.Process()
        memory_info = process.memory_info()
        print(f"메모리 사용량: {memory_info.rss / 1024 / 1024:.1f}MB")

def micro_benchmark_analysis():
    """마이크로 벤치마크 분석"""
    print("\n🔬 마이크로 벤치마크 분석")
    print("=" * 80)
    
    # 개별 연산 성능 측정
    test_data = create_large_test_data(1000)
    
    operations = {
        "리스트 생성": lambda: [],
        "리스트 미리 할당": lambda: [None] * len(test_data),
        "문자열 비교": lambda: "FLOAT32" in "FLOAT32",
        "문자열 접미사 확인": lambda: "123.45".endswith('f'),
        "타입 캐스팅": lambda: str("test"),
        "리스트 인덱싱": lambda: test_data[0][0] if test_data else None,
    }
    
    for op_name, op_func in operations.items():
        times = []
        for _ in range(10000):
            start = time.perf_counter()
            op_func()
            end = time.perf_counter()
            times.append(end - start)
        
        avg_time = sum(times) / len(times)
        print(f"{op_name}: {avg_time * 1000000:.2f} μs")

def identify_bottlenecks():
    """병목 지점 식별"""
    print("\n🎯 병목 지점 식별")
    print("=" * 80)
    
    test_data = create_large_test_data(5000)
    
    # 단계별 시간 측정
    steps = {}
    
    # 1. 입력 검증
    start = time.perf_counter()
    if not test_data:
        return []
    steps['입력_검증'] = time.perf_counter() - start
    
    # 2. 리스트 초기화
    start = time.perf_counter()
    processed_items = []
    steps['리스트_초기화'] = time.perf_counter() - start
    
    # 3. 메인 루프
    start = time.perf_counter()
    for i, line_str in enumerate(test_data):
        if i >= 100:  # 샘플링
            break
        if line_str and len(line_str) >= 6:
            # 문자열 추출
            op_code = line_str[0] if line_str[0] else ""
            key_str = line_str[1] if line_str[1] else ""
            type_str = line_str[2] if line_str[2] else ""
            name_str = line_str[3] if line_str[3] else ""
            val_str = line_str[4] if line_str[4] else ""
            desc_str = line_str[5] if line_str[5] else ""
            
            # FLOAT32 처리
            if val_str and type_str and "FLOAT32" in type_str:
                val_str = add_float_suffix_python(val_str, type_str)
            
            processed_items.append([op_code, key_str, type_str, name_str, val_str, desc_str])
    
    steps['메인_루프'] = time.perf_counter() - start
    
    # 결과 출력
    total_time = sum(steps.values())
    for step_name, step_time in steps.items():
        percentage = (step_time / total_time * 100) if total_time > 0 else 0
        print(f"{step_name}: {step_time:.6f}초 ({percentage:.1f}%)")

if __name__ == "__main__":
    detailed_performance_analysis()
    micro_benchmark_analysis()
    identify_bottlenecks()
    
    print("\n📋 분석 완료")
    print("=" * 80)
    print("상세 프로파일링 결과를 바탕으로 최적화 방안을 수립하겠습니다.")
