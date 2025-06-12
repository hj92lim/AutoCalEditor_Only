"""
Cython vs Python 성능 벤치마크 스크립트
Excel → DB → C 코드 변환 과정의 성능 측정 및 비교
"""

import time
import logging
import traceback
import os
import sys
import gc
import psutil
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import sqlite3

# 프로젝트 루트 경로 설정
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s',
    handlers=[
        logging.FileHandler('performance_benchmark.log', mode='w', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

class PerformanceBenchmark:
    """성능 벤치마크 클래스"""
    
    def __init__(self):
        self.results = {}
        self.process = psutil.Process()
        
    def measure_memory_usage(self) -> Dict[str, float]:
        """메모리 사용량 측정"""
        memory_info = self.process.memory_info()
        return {
            'rss_mb': memory_info.rss / 1024 / 1024,  # 물리 메모리 (MB)
            'vms_mb': memory_info.vms / 1024 / 1024,  # 가상 메모리 (MB)
        }
    
    def benchmark_function(self, func_name: str, func, *args, **kwargs) -> Dict:
        """함수 성능 측정"""
        logging.info(f"🔍 벤치마크 시작: {func_name}")
        
        # 가비지 컬렉션 실행
        gc.collect()
        
        # 시작 시점 메모리 측정
        start_memory = self.measure_memory_usage()
        start_time = time.perf_counter()
        
        try:
            # 함수 실행
            result = func(*args, **kwargs)
            
            # 종료 시점 측정
            end_time = time.perf_counter()
            end_memory = self.measure_memory_usage()
            
            execution_time = end_time - start_time
            memory_delta = {
                'rss_mb': end_memory['rss_mb'] - start_memory['rss_mb'],
                'vms_mb': end_memory['vms_mb'] - start_memory['vms_mb']
            }
            
            benchmark_result = {
                'success': True,
                'execution_time': execution_time,
                'start_memory': start_memory,
                'end_memory': end_memory,
                'memory_delta': memory_delta,
                'result': result
            }
            
            logging.info(f"✅ {func_name} 완료: {execution_time:.3f}초, 메모리 증가: {memory_delta['rss_mb']:.1f}MB")
            
        except Exception as e:
            end_time = time.perf_counter()
            execution_time = end_time - start_time
            
            benchmark_result = {
                'success': False,
                'execution_time': execution_time,
                'error': str(e),
                'traceback': traceback.format_exc()
            }
            
            logging.error(f"❌ {func_name} 실패: {e} ({execution_time:.3f}초)")
        
        self.results[func_name] = benchmark_result
        return benchmark_result

    def compare_implementations(self, test_name: str, python_func, cython_func, *args, **kwargs) -> Dict:
        """Python vs Cython 구현 비교"""
        logging.info(f"🆚 구현 비교 시작: {test_name}")
        
        # Python 버전 측정
        python_result = self.benchmark_function(f"{test_name}_python", python_func, *args, **kwargs)
        
        # 메모리 정리
        gc.collect()
        time.sleep(0.1)
        
        # Cython 버전 측정
        cython_result = self.benchmark_function(f"{test_name}_cython", cython_func, *args, **kwargs)
        
        # 성능 비교 계산
        if python_result['success'] and cython_result['success']:
            speedup = python_result['execution_time'] / cython_result['execution_time']
            memory_improvement = python_result['memory_delta']['rss_mb'] - cython_result['memory_delta']['rss_mb']
            
            comparison = {
                'test_name': test_name,
                'python_time': python_result['execution_time'],
                'cython_time': cython_result['execution_time'],
                'speedup': speedup,
                'memory_improvement_mb': memory_improvement,
                'python_success': True,
                'cython_success': True
            }
            
            if speedup > 1:
                logging.info(f"🚀 {test_name}: Cython이 {speedup:.2f}배 빠름")
            else:
                logging.warning(f"⚠️ {test_name}: Python이 {1/speedup:.2f}배 빠름 (Cython 최적화 필요)")
                
        else:
            comparison = {
                'test_name': test_name,
                'python_success': python_result['success'],
                'cython_success': cython_result['success'],
                'python_error': python_result.get('error'),
                'cython_error': cython_result.get('error')
            }
            
            logging.error(f"❌ {test_name}: 비교 실패 (Python: {python_result['success']}, Cython: {cython_result['success']})")
        
        return comparison

def create_test_data() -> Tuple[List, List, Dict]:
    """테스트용 데이터 생성"""
    logging.info("📊 테스트 데이터 생성 중...")
    
    # Excel 데이터 시뮬레이션 (1000x100 크기)
    excel_data = []
    for i in range(1000):
        row = []
        for j in range(100):
            if j == 0:
                row.append(f"Item_{i}")
            elif j == 1:
                row.append("FLOAT32")
            elif j == 2:
                row.append(f"value_{i}")
            elif j == 3:
                row.append(str(i * 1.5))
            else:
                row.append(f"data_{i}_{j}")
        excel_data.append(row)
    
    # 셀 데이터 리스트
    cells_data = []
    for i, row in enumerate(excel_data):
        for j, value in enumerate(row):
            if value:
                cells_data.append((i, j, str(value)))
    
    # 시트 데이터
    sheet_data = {
        'id': 1,
        'name': 'TestSheet',
        'data': excel_data
    }
    
    logging.info(f"✅ 테스트 데이터 생성 완료: {len(excel_data)}행 x {len(excel_data[0])}열, {len(cells_data)}개 셀")
    
    return excel_data, cells_data, sheet_data

def test_excel_processing(benchmark: PerformanceBenchmark, excel_data: List, cells_data: List):
    """Excel 처리 성능 테스트"""
    logging.info("📈 Excel 처리 성능 테스트 시작")
    
    # Python 버전 함수
    def python_excel_processing(values):
        cells_data = []
        if values is None:
            return cells_data
        
        rows = len(values)
        for i in range(rows):
            row = values[i]
            if isinstance(row, list):
                cols = len(row)
                for j in range(cols):
                    val = row[j]
                    if val is not None:
                        value_str = str(val)
                        cells_data.append((i, j, value_str))
        return cells_data
    
    # Cython 버전 import 시도
    try:
        from cython_extensions.excel_processor_v2 import fast_process_excel_data
        cython_func = fast_process_excel_data
    except ImportError:
        logging.warning("Cython Excel 모듈을 찾을 수 없음, Python 버전만 테스트")
        cython_func = python_excel_processing
    
    # 성능 비교
    comparison = benchmark.compare_implementations(
        "excel_processing", 
        python_excel_processing, 
        cython_func, 
        excel_data
    )
    
    return comparison

def test_data_processing(benchmark: PerformanceBenchmark, cells_data: List):
    """데이터 처리 성능 테스트"""
    logging.info("🔧 데이터 처리 성능 테스트 시작")
    
    # Python 버전 함수
    def python_batch_processing(cells_data):
        processed_data = []
        for cell_tuple in cells_data:
            row, col, value = cell_tuple
            value_str = str(value) if value is not None else ""
            if value_str and value_str.strip():
                processed_data.append((row, col, value_str))
        return processed_data
    
    # Cython 버전 import 시도
    try:
        from cython_extensions.data_processor import fast_db_batch_processing
        cython_func = fast_db_batch_processing
    except ImportError:
        logging.warning("Cython 데이터 처리 모듈을 찾을 수 없음, Python 버전만 테스트")
        cython_func = python_batch_processing
    
    # 성능 비교
    comparison = benchmark.compare_implementations(
        "data_processing", 
        python_batch_processing, 
        cython_func, 
        cells_data
    )
    
    return comparison

if __name__ == "__main__":
    logging.info("🚀 Cython vs Python 성능 벤치마크 시작")
    
    # 벤치마크 객체 생성
    benchmark = PerformanceBenchmark()
    
    # 테스트 데이터 생성
    excel_data, cells_data, sheet_data = create_test_data()
    
    # 각종 성능 테스트 실행
    results = []
    
    # 1. Excel 처리 테스트
    excel_result = test_excel_processing(benchmark, excel_data, cells_data)
    results.append(excel_result)
    
    # 2. 데이터 처리 테스트
    data_result = test_data_processing(benchmark, cells_data)
    results.append(data_result)
    
    logging.info("📊 벤치마크 완료, 결과 분석 중...")

    # 결과 요약 출력
    print("\n" + "="*80)
    print("🎯 성능 벤치마크 결과 요약")
    print("="*80)

    total_speedup = 0
    successful_tests = 0

    for result in results:
        if result.get('python_success') and result.get('cython_success'):
            test_name = result['test_name']
            python_time = result['python_time']
            cython_time = result['cython_time']
            speedup = result['speedup']
            memory_improvement = result.get('memory_improvement_mb', 0)

            print(f"\n📈 {test_name.upper()}")
            print(f"   Python 시간:    {python_time:.4f}초")
            print(f"   Cython 시간:    {cython_time:.4f}초")
            print(f"   성능 향상:      {speedup:.2f}배")
            print(f"   메모리 개선:    {memory_improvement:.1f}MB")

            if speedup > 1:
                print(f"   ✅ Cython이 {speedup:.1f}배 빠름")
            else:
                print(f"   ⚠️ Python이 {1/speedup:.1f}배 빠름")

            total_speedup += speedup
            successful_tests += 1
        else:
            test_name = result['test_name']
            print(f"\n❌ {test_name.upper()}: 테스트 실패")
            if not result.get('python_success'):
                print(f"   Python 오류: {result.get('python_error', 'Unknown')}")
            if not result.get('cython_success'):
                print(f"   Cython 오류: {result.get('cython_error', 'Unknown')}")

    # 전체 요약
    print(f"\n{'='*80}")
    if successful_tests > 0:
        avg_speedup = total_speedup / successful_tests
        print(f"🏆 전체 평균 성능 향상: {avg_speedup:.2f}배")

        if avg_speedup > 1.5:
            print("🚀 Cython 최적화가 효과적으로 작동하고 있습니다!")
        elif avg_speedup > 1.0:
            print("✅ Cython 최적화가 일부 효과를 보이고 있습니다.")
        else:
            print("⚠️ Cython 최적화 효과가 미미하거나 역효과가 발생하고 있습니다.")
            print("   - 컴파일 최적화 옵션 검토 필요")
            print("   - Python-Cython 간 데이터 전달 오버헤드 확인 필요")
            print("   - 타입 선언 및 최적화 지시문 개선 필요")
    else:
        print("❌ 모든 테스트가 실패했습니다. Cython 설정을 확인해주세요.")

    print("="*80)

    # 상세 결과를 파일로 저장
    import json
    with open('benchmark_results.json', 'w', encoding='utf-8') as f:
        json.dump({
            'summary': {
                'total_tests': len(results),
                'successful_tests': successful_tests,
                'average_speedup': total_speedup / successful_tests if successful_tests > 0 else 0
            },
            'detailed_results': results,
            'all_benchmark_data': benchmark.results
        }, f, indent=2, ensure_ascii=False)

    logging.info("📄 상세 결과가 benchmark_results.json에 저장되었습니다.")

def test_code_generation(benchmark: PerformanceBenchmark, test_data: List):
    """코드 생성 성능 테스트"""
    logging.info("⚙️ 코드 생성 성능 테스트 시작")

    # 테스트용 코드 아이템 생성
    temp_code_items = []
    for i in range(1000):
        temp_code_items.append([
            "DEFINE",
            "CONST",
            "FLOAT32",
            f"TEST_VALUE_{i}",
            str(i * 1.5),
            f"Test value {i}"
        ])

    # Python 버전 함수
    def python_code_processing(temp_code_items):
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
                    if val_str.replace('.', '').replace('-', '').isdigit():
                        if '.' in val_str:
                            val_str = val_str + 'f'
                        else:
                            val_str = val_str + '.f'

                processed_items.append([op_code, key_str, type_str, name_str, val_str, desc_str])
        return processed_items

    # Cython 버전 import 시도
    try:
        from cython_extensions.code_generator_v2 import fast_write_cal_list_processing
        cython_func = fast_write_cal_list_processing
    except ImportError:
        logging.warning("Cython 코드 생성 모듈을 찾을 수 없음, Python 버전만 테스트")
        cython_func = python_code_processing

    # 성능 비교
    comparison = benchmark.compare_implementations(
        "code_generation",
        python_code_processing,
        cython_func,
        temp_code_items
    )

    return comparison

def analyze_cython_status():
    """Cython 모듈 상태 분석"""
    logging.info("🔍 Cython 모듈 상태 분석 시작")

    modules_to_check = [
        'cython_extensions.excel_processor_v2',
        'cython_extensions.data_processor',
        'cython_extensions.code_generator_v2',
        'cython_extensions.regex_optimizer'
    ]

    status = {}
    for module in modules_to_check:
        try:
            __import__(module)
            status[module] = {'available': True, 'error': None}
            logging.info(f"✅ {module}: 사용 가능")
        except ImportError as e:
            status[module] = {'available': False, 'error': str(e)}
            logging.warning(f"❌ {module}: 사용 불가 - {e}")

    # 컴파일된 파일 확인
    cython_dir = Path('cython_extensions')
    if cython_dir.exists():
        compiled_files = list(cython_dir.glob('*.pyd')) + list(cython_dir.glob('*.so'))
        logging.info(f"📁 컴파일된 파일: {[f.name for f in compiled_files]}")
    else:
        logging.warning("📁 cython_extensions 디렉토리를 찾을 수 없음")

    return status

def run_comprehensive_benchmark():
    """종합적인 벤치마크 실행"""
    logging.info("🚀 종합 성능 벤치마크 시작")

    # Cython 상태 분석
    cython_status = analyze_cython_status()

    # 벤치마크 객체 생성
    benchmark = PerformanceBenchmark()

    # 테스트 데이터 생성
    excel_data, cells_data, sheet_data = create_test_data()

    # 각종 성능 테스트 실행
    results = []

    try:
        # 1. Excel 처리 테스트
        excel_result = test_excel_processing(benchmark, excel_data, cells_data)
        results.append(excel_result)

        # 2. 데이터 처리 테스트
        data_result = test_data_processing(benchmark, cells_data)
        results.append(data_result)

        # 3. 코드 생성 테스트
        code_result = test_code_generation(benchmark, excel_data)
        results.append(code_result)

    except Exception as e:
        logging.error(f"벤치마크 실행 중 오류: {e}")
        logging.error(traceback.format_exc())

    return results, cython_status, benchmark

if __name__ == "__main__":
    # 종합 벤치마크 실행
    results, cython_status, benchmark = run_comprehensive_benchmark()
