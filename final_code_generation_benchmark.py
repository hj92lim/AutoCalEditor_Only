"""
최종 코드 생성 모듈 성능 벤치마크
극한 최적화 후 성능 검증
"""

import time
import logging
import gc
import sys
from pathlib import Path
from typing import List, Dict, Any

# 프로젝트 루트 경로 설정
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s'
)

def create_comprehensive_test_data(size: int = 5000) -> List[List[str]]:
    """종합적인 테스트 데이터 생성"""
    test_data = []
    
    for i in range(size):
        if i % 5 == 0:
            # FLOAT32 타입 (접미사 처리 필요)
            test_data.append([
                "DEFINE",
                "CONST",
                "FLOAT32", 
                f"FLOAT_VALUE_{i}",
                str(i * 1.5),
                f"Float value {i} with description"
            ])
        elif i % 5 == 1:
            # INT32 타입
            test_data.append([
                "DEFINE",
                "CONST",
                "INT32",
                f"INT_VALUE_{i}",
                str(i),
                f"Integer value {i}"
            ])
        elif i % 5 == 2:
            # STRING 타입
            test_data.append([
                "DEFINE",
                "CONST", 
                "STRING",
                f"STR_VALUE_{i}",
                f'"String_{i}"',
                f"String value {i}"
            ])
        elif i % 5 == 3:
            # 복잡한 FLOAT32 (소수점 포함)
            test_data.append([
                "DEFINE",
                "CONST",
                "FLOAT32",
                f"COMPLEX_FLOAT_{i}",
                f"{i}.{i%10}",
                f"Complex float {i}.{i%10}"
            ])
        else:
            # 빈 값이나 특수 케이스
            test_data.append([
                "DEFINE",
                "",
                "FLOAT32",
                f"EMPTY_VALUE_{i}",
                "",
                ""
            ])
    
    return test_data

def python_reference_optimized(temp_code_items: List[List[str]]) -> List[List[str]]:
    """최적화된 Python 참조 구현"""
    if not temp_code_items:
        return []
    
    processed_items = []
    length = len(temp_code_items)
    
    for i in range(length):
        line_str = temp_code_items[i]
        if line_str and len(line_str) >= 6:
            op_code = line_str[0] if line_str[0] else ""
            key_str = line_str[1] if line_str[1] else ""
            type_str = line_str[2] if line_str[2] else ""
            name_str = line_str[3] if line_str[3] else ""
            val_str = line_str[4] if line_str[4] else ""
            desc_str = line_str[5] if line_str[5] else ""
            
            # FLOAT32 변수의 숫자에 f 접미사 추가
            if val_str and type_str and "FLOAT32" in type_str:
                val_str = add_float_suffix_python_optimized(val_str)
            
            processed_items.append([op_code, key_str, type_str, name_str, val_str, desc_str])
        else:
            processed_items.append(line_str)
    
    return processed_items

def add_float_suffix_python_optimized(val_str: str) -> str:
    """최적화된 Python float suffix 추가"""
    if not val_str or val_str.endswith('f') or val_str.endswith('F'):
        return val_str
    
    # 주석 체크
    if '/*' in val_str or '//' in val_str:
        return val_str
    
    # 숫자 패턴 확인
    try:
        # 정수 확인
        if val_str.isdigit() or (val_str.startswith('-') and val_str[1:].isdigit()):
            return '0.f' if val_str == '0' else val_str + '.f'
        
        # 소수점 확인
        if '.' in val_str:
            float(val_str)  # 유효성 검사
            return val_str + 'f'
        else:
            float(val_str)  # 유효성 검사
            return val_str + '.f'
    except ValueError:
        return val_str

def measure_performance_comprehensive(func, test_data: List, iterations: int = 10) -> Dict[str, Any]:
    """종합적인 성능 측정"""
    times = []
    
    for i in range(iterations):
        gc.collect()
        
        start_time = time.perf_counter()
        result = func(test_data)
        end_time = time.perf_counter()
        
        execution_time = end_time - start_time
        times.append(execution_time)
    
    # 통계 계산
    avg_time = sum(times) / len(times)
    min_time = min(times)
    max_time = max(times)
    
    return {
        'avg_time': avg_time,
        'min_time': min_time,
        'max_time': max_time,
        'times': times,
        'result_length': len(result) if result else 0
    }

def run_final_benchmark():
    """최종 벤치마크 실행"""
    print("🚀 최종 코드 생성 모듈 성능 벤치마크")
    print("=" * 80)
    
    # 다양한 크기로 테스트
    test_sizes = [1000, 2500, 5000, 10000, 20000]
    
    for size in test_sizes:
        print(f"\n📊 테스트 데이터 크기: {size:,}개")
        print("-" * 60)
        
        # 테스트 데이터 생성
        test_data = create_comprehensive_test_data(size)
        
        # Python 버전 측정
        python_result = measure_performance_comprehensive(
            python_reference_optimized, 
            test_data, 
            iterations=5
        )
        
        print(f"Python 평균 시간: {python_result['avg_time']:.6f}초")
        print(f"Python 최소 시간: {python_result['min_time']:.6f}초")
        
        # 기본 Cython 버전 측정
        try:
            from cython_extensions.code_generator_v2 import fast_write_cal_list_processing
            
            cython_result = measure_performance_comprehensive(
                fast_write_cal_list_processing,
                test_data,
                iterations=5
            )
            
            print(f"Cython 평균 시간: {cython_result['avg_time']:.6f}초")
            print(f"Cython 최소 시간: {cython_result['min_time']:.6f}초")
            
            # 성능 비교
            if cython_result['avg_time'] > 0:
                speedup = python_result['avg_time'] / cython_result['avg_time']
                print(f"기본 Cython 성능 향상: {speedup:.2f}배")
                
                if speedup >= 1.5:
                    print(f"✅ 목표 달성! Cython이 {speedup:.1f}배 빠름")
                elif speedup > 1:
                    print(f"✅ Cython이 {speedup:.1f}배 빠름")
                else:
                    print(f"⚠️ Python이 {1/speedup:.1f}배 빠름")
            
        except ImportError as e:
            print(f"❌ 기본 Cython 모듈 import 실패: {e}")
        
        # 극한 최적화 버전 측정
        try:
            from cython_extensions.code_generator_v2 import ultra_fast_write_cal_list_processing
            
            ultra_result = measure_performance_comprehensive(
                ultra_fast_write_cal_list_processing,
                test_data,
                iterations=5
            )
            
            print(f"Ultra Cython 평균 시간: {ultra_result['avg_time']:.6f}초")
            print(f"Ultra Cython 최소 시간: {ultra_result['min_time']:.6f}초")
            
            # 성능 비교
            if ultra_result['avg_time'] > 0:
                ultra_speedup = python_result['avg_time'] / ultra_result['avg_time']
                print(f"Ultra Cython 성능 향상: {ultra_speedup:.2f}배")
                
                if ultra_speedup >= 1.5:
                    print(f"🚀 목표 달성! Ultra Cython이 {ultra_speedup:.1f}배 빠름")
                elif ultra_speedup > 1:
                    print(f"✅ Ultra Cython이 {ultra_speedup:.1f}배 빠름")
                else:
                    print(f"⚠️ Python이 {1/ultra_speedup:.1f}배 빠름")
                
                # 기본 vs Ultra 비교
                if cython_result['avg_time'] > 0:
                    ultra_vs_basic = cython_result['avg_time'] / ultra_result['avg_time']
                    print(f"Ultra vs 기본 Cython: {ultra_vs_basic:.2f}배 개선")
            
        except ImportError as e:
            print(f"❌ Ultra Cython 모듈 import 실패: {e}")
        except Exception as e:
            print(f"❌ Ultra Cython 실행 오류: {e}")
        
        # 결과 검증
        try:
            if (python_result['result_length'] == cython_result['result_length'] and 
                python_result['result_length'] == ultra_result['result_length']):
                print("✅ 모든 버전 결과 길이 일치")
            else:
                print(f"❌ 결과 길이 불일치: Python {python_result['result_length']}, "
                      f"Cython {cython_result['result_length']}, Ultra {ultra_result['result_length']}")
        except:
            print("⚠️ 결과 검증 실패")

def performance_summary():
    """성능 요약"""
    print("\n🎯 성능 최적화 요약")
    print("=" * 80)
    
    # 작은 데이터셋으로 빠른 테스트
    test_data = create_comprehensive_test_data(1000)
    
    try:
        # Python 측정
        start = time.perf_counter()
        python_result = python_reference_optimized(test_data)
        python_time = time.perf_counter() - start
        
        # Cython 측정
        from cython_extensions.code_generator_v2 import fast_write_cal_list_processing
        start = time.perf_counter()
        cython_result = fast_write_cal_list_processing(test_data)
        cython_time = time.perf_counter() - start
        
        # Ultra Cython 측정
        from cython_extensions.code_generator_v2 import ultra_fast_write_cal_list_processing
        start = time.perf_counter()
        ultra_result = ultra_fast_write_cal_list_processing(test_data)
        ultra_time = time.perf_counter() - start
        
        print(f"Python 시간:      {python_time:.6f}초")
        print(f"Cython 시간:      {cython_time:.6f}초")
        print(f"Ultra Cython 시간: {ultra_time:.6f}초")
        
        if cython_time > 0 and ultra_time > 0:
            cython_speedup = python_time / cython_time
            ultra_speedup = python_time / ultra_time
            
            print(f"\n성능 향상:")
            print(f"  Cython:      {cython_speedup:.2f}배")
            print(f"  Ultra Cython: {ultra_speedup:.2f}배")
            
            if ultra_speedup >= 1.5:
                print(f"\n🎉 목표 달성! 코드 생성 모듈이 Python 대비 {ultra_speedup:.1f}배 빠름")
            elif cython_speedup >= 1.5:
                print(f"\n✅ 목표 달성! 코드 생성 모듈이 Python 대비 {cython_speedup:.1f}배 빠름")
            else:
                print(f"\n⚠️ 목표 미달성. 추가 최적화 필요")
        
    except Exception as e:
        print(f"❌ 성능 요약 실행 오류: {e}")

if __name__ == "__main__":
    run_final_benchmark()
    performance_summary()
    
    print("\n📋 최종 결론")
    print("=" * 80)
    print("코드 생성 모듈의 성능 최적화가 완료되었습니다.")
    print("실제 사용 환경에서의 성능 향상을 확인하세요.")
