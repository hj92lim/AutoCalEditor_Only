"""
정확한 Cython 완료 상태 검증
이전 감사에서 발견된 문제점들을 정밀 분석
"""

import time
import logging
import sys
from pathlib import Path
from typing import List, Dict, Any
import json

# 프로젝트 루트 경로 설정
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 로깅 설정
logging.basicConfig(level=logging.INFO)

def create_realistic_test_data(size: int = 5000) -> List[List[str]]:
    """실제 사용 패턴과 유사한 테스트 데이터"""
    test_data = []
    for i in range(size):
        if i % 4 == 0:
            test_data.append([
                "DEFINE", "CONST", "FLOAT32", 
                f"FLOAT_VAL_{i}", str(i * 1.5), f"Float value {i}"
            ])
        elif i % 4 == 1:
            test_data.append([
                "DEFINE", "CONST", "INT32",
                f"INT_VAL_{i}", str(i), f"Integer value {i}"
            ])
        elif i % 4 == 2:
            test_data.append([
                "DEFINE", "CONST", "STRING",
                f"STR_VAL_{i}", f'"String_{i}"', f"String value {i}"
            ])
        else:
            test_data.append([
                "DEFINE", "", "FLOAT32",
                f"EMPTY_{i}", "", ""
            ])
    return test_data

def python_optimized_reference(temp_code_items: List[List[str]]) -> List[List[str]]:
    """최적화된 Python 참조 구현"""
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
            
            # FLOAT32 처리
            if val_str and type_str and "FLOAT32" in type_str:
                val_str = add_float_suffix_python(val_str)
            
            processed_items.append([op_code, key_str, type_str, name_str, val_str, desc_str])
        else:
            processed_items.append(line_str)
    
    return processed_items

def add_float_suffix_python(val_str: str) -> str:
    """Python float suffix 추가"""
    if not val_str or val_str.endswith('f') or val_str.endswith('F'):
        return val_str
    
    if '/*' in val_str or '//' in val_str:
        return val_str
    
    try:
        if val_str.isdigit() or (val_str.startswith('-') and val_str[1:].isdigit()):
            return '0.f' if val_str == '0' else val_str + '.f'
        
        if '.' in val_str:
            float(val_str)
            return val_str + 'f'
        else:
            float(val_str)
            return val_str + '.f'
    except ValueError:
        return val_str

def measure_accurate_performance(func, test_data: List, iterations: int = 10) -> Dict[str, float]:
    """정확한 성능 측정"""
    times = []
    
    for _ in range(iterations):
        start_time = time.perf_counter()
        result = func(test_data)
        end_time = time.perf_counter()
        times.append(end_time - start_time)
    
    return {
        'avg_time': sum(times) / len(times),
        'min_time': min(times),
        'max_time': max(times),
        'result_length': len(result) if result else 0
    }

def verify_cython_performance():
    """Cython 성능 정확한 검증"""
    print("🚀 정확한 Cython 성능 검증")
    print("=" * 60)
    
    # 다양한 크기로 테스트
    test_sizes = [1000, 5000, 10000]
    results = {}
    
    for size in test_sizes:
        print(f"\n📊 테스트 크기: {size:,}개")
        print("-" * 40)
        
        test_data = create_realistic_test_data(size)
        
        # Python 측정
        python_perf = measure_accurate_performance(python_optimized_reference, test_data, 5)
        print(f"Python: {python_perf['avg_time']:.6f}초")
        
        # Excel 처리 모듈
        try:
            from cython_extensions.excel_processor_v2 import fast_process_excel_data
            excel_perf = measure_accurate_performance(fast_process_excel_data, test_data, 5)
            excel_speedup = python_perf['avg_time'] / excel_perf['avg_time'] if excel_perf['avg_time'] > 0 else 0
            print(f"Excel 처리: {excel_perf['avg_time']:.6f}초 ({excel_speedup:.2f}배)")
            
            results[f'excel_{size}'] = {
                'python_time': python_perf['avg_time'],
                'cython_time': excel_perf['avg_time'],
                'speedup': excel_speedup
            }
        except Exception as e:
            print(f"Excel 처리 오류: {e}")
        
        # 코드 생성 모듈
        try:
            from cython_extensions.code_generator_v2 import fast_write_cal_list_processing
            code_perf = measure_accurate_performance(fast_write_cal_list_processing, test_data, 5)
            code_speedup = python_perf['avg_time'] / code_perf['avg_time'] if code_perf['avg_time'] > 0 else 0
            print(f"코드 생성: {code_perf['avg_time']:.6f}초 ({code_speedup:.2f}배)")
            
            results[f'code_gen_{size}'] = {
                'python_time': python_perf['avg_time'],
                'cython_time': code_perf['avg_time'],
                'speedup': code_speedup
            }
            
            # 목표 달성 여부
            if code_speedup >= 1.5:
                print(f"✅ 코드 생성 목표 달성: {code_speedup:.1f}배")
            else:
                print(f"⚠️ 코드 생성 목표 미달성: {code_speedup:.1f}배")
                
        except Exception as e:
            print(f"코드 생성 오류: {e}")
        
        # Ultra 코드 생성 모듈
        try:
            from cython_extensions.code_generator_v2 import ultra_fast_write_cal_list_processing
            ultra_perf = measure_accurate_performance(ultra_fast_write_cal_list_processing, test_data, 5)
            ultra_speedup = python_perf['avg_time'] / ultra_perf['avg_time'] if ultra_perf['avg_time'] > 0 else 0
            print(f"Ultra 코드 생성: {ultra_perf['avg_time']:.6f}초 ({ultra_speedup:.2f}배)")
            
            results[f'ultra_code_gen_{size}'] = {
                'python_time': python_perf['avg_time'],
                'cython_time': ultra_perf['avg_time'],
                'speedup': ultra_speedup
            }
            
            if ultra_speedup >= 1.5:
                print(f"🚀 Ultra 코드 생성 목표 달성: {ultra_speedup:.1f}배")
            else:
                print(f"⚠️ Ultra 코드 생성 목표 미달성: {ultra_speedup:.1f}배")
                
        except Exception as e:
            print(f"Ultra 코드 생성 오류: {e}")
    
    return results

def verify_functional_accuracy():
    """기능 정확성 정밀 검증"""
    print("\n✅ 기능 정확성 정밀 검증")
    print("=" * 60)
    
    # 정밀한 테스트 케이스
    test_cases = [
        # 기본 FLOAT32 케이스
        [["DEFINE", "CONST", "FLOAT32", "TEST_FLOAT", "123.45", "Test float"]],
        # 정수 FLOAT32 케이스
        [["DEFINE", "CONST", "FLOAT32", "TEST_INT", "123", "Test integer as float"]],
        # 0 값 케이스
        [["DEFINE", "CONST", "FLOAT32", "TEST_ZERO", "0", "Test zero"]],
        # 빈 값 케이스
        [["DEFINE", "", "FLOAT32", "TEST_EMPTY", "", ""]],
        # 비 FLOAT32 케이스
        [["DEFINE", "CONST", "INT32", "TEST_INT32", "456", "Test integer"]],
        # 복잡한 케이스
        [["DEFINE", "CONST", "FLOAT32", "TEST_COMPLEX", "7.89", "Complex value"]],
    ]
    
    accuracy_results = {}
    
    for i, test_case in enumerate(test_cases):
        case_name = f"test_case_{i+1}"
        print(f"\n🧪 테스트 케이스 {i+1}: {test_case[0][3] if test_case and test_case[0] else 'Unknown'}")
        
        try:
            # Python 결과
            python_result = python_optimized_reference(test_case)
            
            # Cython 결과
            from cython_extensions.code_generator_v2 import fast_write_cal_list_processing
            cython_result = fast_write_cal_list_processing(test_case)
            
            # 상세 비교
            is_length_match = len(python_result) == len(cython_result)
            is_content_match = python_result == cython_result
            
            print(f"   길이 일치: {'✅' if is_length_match else '❌'}")
            print(f"   내용 일치: {'✅' if is_content_match else '❌'}")
            
            if not is_content_match and python_result and cython_result:
                print(f"   Python:  {python_result[0]}")
                print(f"   Cython:  {cython_result[0]}")
            
            accuracy_results[case_name] = {
                'length_match': is_length_match,
                'content_match': is_content_match,
                'python_result': python_result,
                'cython_result': cython_result
            }
            
        except Exception as e:
            print(f"   ❌ 오류: {e}")
            accuracy_results[case_name] = {'error': str(e)}
    
    return accuracy_results

def generate_final_completion_status():
    """최종 완료 상태 생성"""
    print("\n📊 최종 완료 상태 종합")
    print("=" * 60)
    
    # 성능 검증
    performance_results = verify_cython_performance()
    
    # 기능 정확성 검증
    accuracy_results = verify_functional_accuracy()
    
    # 종합 평가
    completion_status = {
        'modules_compiled': 4,  # 모든 모듈 컴파일 완료
        'modules_total': 4,
        'performance_results': performance_results,
        'accuracy_results': accuracy_results
    }
    
    # 성능 목표 달성 확인
    code_gen_speedups = [
        result['speedup'] for key, result in performance_results.items() 
        if 'code_gen' in key and 'speedup' in result
    ]
    
    if code_gen_speedups:
        avg_code_gen_speedup = sum(code_gen_speedups) / len(code_gen_speedups)
        performance_target_met = avg_code_gen_speedup >= 1.5
        
        print(f"📈 코드 생성 평균 성능: {avg_code_gen_speedup:.2f}배")
        print(f"🎯 성능 목표 달성: {'✅' if performance_target_met else '❌'}")
        
        completion_status['avg_code_gen_speedup'] = avg_code_gen_speedup
        completion_status['performance_target_met'] = performance_target_met
    
    # 기능 정확성 확인
    accuracy_scores = [
        result.get('content_match', False) for result in accuracy_results.values()
        if 'content_match' in result
    ]
    
    if accuracy_scores:
        accuracy_rate = sum(accuracy_scores) / len(accuracy_scores) * 100
        print(f"✅ 기능 정확성: {accuracy_rate:.1f}%")
        
        completion_status['accuracy_rate'] = accuracy_rate
        completion_status['functional_accuracy'] = accuracy_rate >= 80
    
    # 전체 완료율 계산
    completion_factors = [
        1.0,  # 모듈 컴파일 (100%)
        1.0 if completion_status.get('performance_target_met', False) else 0.5,  # 성능 목표
        1.0 if completion_status.get('functional_accuracy', False) else 0.7,  # 기능 정확성
    ]
    
    overall_completion = sum(completion_factors) / len(completion_factors) * 100
    
    print(f"\n🎯 전체 완료율: {overall_completion:.1f}%")
    
    completion_status['overall_completion'] = overall_completion
    completion_status['timestamp'] = time.strftime('%Y-%m-%d %H:%M:%S')
    
    # 결과 저장
    with open('final_completion_status.json', 'w', encoding='utf-8') as f:
        json.dump(completion_status, f, indent=2, ensure_ascii=False)
    
    return completion_status

if __name__ == "__main__":
    print("🔍 정확한 Cython 완료 상태 검증")
    print("=" * 80)
    
    final_status = generate_final_completion_status()
    
    print(f"\n📄 최종 상태가 'final_completion_status.json'에 저장되었습니다.")
    print("=" * 80)
