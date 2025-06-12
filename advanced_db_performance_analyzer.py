"""
고급 DB → C 코드 변환 성능 분석기
실제 사용자 시나리오와 대용량 데이터 처리 성능 분석
"""

import time
import psutil
import gc
import logging
import os
import sys
import threading
from pathlib import Path
from typing import Dict, List, Any, Tuple
import json
import traceback
from concurrent.futures import ThreadPoolExecutor
import multiprocessing

# 프로젝트 루트 경로 설정
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s'
)

class AdvancedDBPerformanceAnalyzer:
    """고급 DB 성능 분석기"""
    
    def __init__(self):
        self.process = psutil.Process()
        self.analysis_results = {}
        
    def create_large_test_databases(self, count: int = 5, size_multiplier: int = 1000) -> List[Path]:
        """대용량 테스트 DB 파일들 생성"""
        print(f"🔄 대용량 테스트 DB {count}개 생성 (크기 배수: {size_multiplier})")
        print("=" * 60)
        
        try:
            from data_manager.db_handler_v2 import DBHandlerV2
            
            large_dbs = []
            
            for i in range(count):
                db_name = f'large_performance_test_{i+1}.db'
                db_path = Path('database') / db_name
                
                if db_path.exists():
                    os.remove(db_path)
                
                db_handler = DBHandlerV2(str(db_path))
                db_handler.connect()
                db_handler.init_tables()
                
                # 다양한 크기의 시트 생성
                total_cells = 0
                
                # 작은 시트들
                for j in range(3):
                    sheet_id = db_handler.create_sheet_v2(f"$(Small)Sheet_{i}_{j}", is_dollar_sheet=True, source_file=f"large_test_{i}.xlsx")
                    small_data = [(k % 20, k % 10, f"SMALL_{i}_{j}_{k}") for k in range(100 * size_multiplier)]
                    
                    # 중복 방지를 위해 고유한 row, col 생성
                    unique_data = []
                    for idx, (row, col, value) in enumerate(small_data):
                        unique_row = row + (j * 100)
                        unique_data.append((unique_row, col, value))
                    
                    db_handler.batch_insert_cells(sheet_id, unique_data)
                    total_cells += len(unique_data)
                
                # 중간 시트들
                for j in range(2):
                    sheet_id = db_handler.create_sheet_v2(f"$(Medium)Sheet_{i}_{j}", is_dollar_sheet=True, source_file=f"large_test_{i}.xlsx")
                    medium_data = [(k % 50, k % 20, f"MEDIUM_{i}_{j}_{k}") for k in range(500 * size_multiplier)]
                    
                    # 중복 방지
                    unique_data = []
                    for idx, (row, col, value) in enumerate(medium_data):
                        unique_row = row + (j * 200) + 1000  # 다른 시트와 겹치지 않도록
                        unique_data.append((unique_row, col, value))
                    
                    db_handler.batch_insert_cells(sheet_id, unique_data)
                    total_cells += len(unique_data)
                
                # 큰 시트 (일부에만)
                if i % 2 == 0:
                    sheet_id = db_handler.create_sheet_v2(f"$(Large)Sheet_{i}", is_dollar_sheet=True, source_file=f"large_test_{i}.xlsx")
                    large_data = [(k % 100, k % 30, f"LARGE_{i}_{k}") for k in range(1000 * size_multiplier)]
                    
                    # 중복 방지
                    unique_data = []
                    for idx, (row, col, value) in enumerate(large_data):
                        unique_row = row + 2000  # 다른 시트와 겹치지 않도록
                        unique_data.append((unique_row, col, value))
                    
                    db_handler.batch_insert_cells(sheet_id, unique_data)
                    total_cells += len(unique_data)
                
                db_handler.disconnect()
                
                file_size = db_path.stat().st_size
                
                print(f"   ✅ {db_name} 생성 완료")
                print(f"      파일 크기: {file_size:,} bytes")
                print(f"      데이터: {total_cells:,}개 셀")
                
                large_dbs.append(db_path)
            
            return large_dbs
            
        except Exception as e:
            print(f"❌ 대용량 테스트 DB 생성 실패: {e}")
            print(traceback.format_exc())
            return []
    
    def measure_system_resources(self) -> Dict[str, float]:
        """시스템 리소스 측정"""
        memory_info = self.process.memory_info()
        cpu_percent = self.process.cpu_percent(interval=0.1)
        
        # 시스템 전체 메모리 정보
        system_memory = psutil.virtual_memory()
        
        return {
            'process_rss_mb': memory_info.rss / 1024 / 1024,
            'process_vms_mb': memory_info.vms / 1024 / 1024,
            'process_cpu_percent': cpu_percent,
            'system_memory_percent': system_memory.percent,
            'system_available_mb': system_memory.available / 1024 / 1024
        }
    
    def stress_test_batch_processing(self, db_files: List[Path], iterations: int = 3) -> Dict[str, Any]:
        """스트레스 테스트: 반복적인 일괄 처리"""
        print(f"\n🔥 스트레스 테스트: {len(db_files)}개 DB 파일 x {iterations}회 반복")
        print("=" * 60)
        
        try:
            from data_manager.db_handler_v2 import DBHandlerV2
            from cython_extensions.code_generator_v2 import fast_write_cal_list_processing
            
            iteration_results = []
            
            for iteration in range(iterations):
                print(f"\n🔄 반복 {iteration + 1}/{iterations}")
                
                start_resources = self.measure_system_resources()
                start_time = time.perf_counter()
                
                total_processed_items = 0
                
                for i, db_file in enumerate(db_files):
                    file_start_time = time.perf_counter()
                    
                    # DB 연결
                    db_handler = DBHandlerV2(str(db_file))
                    db_handler.connect()
                    
                    # $ 시트 찾기
                    sheets = db_handler.get_sheets()
                    dollar_sheets = [s for s in sheets if s.get('is_dollar_sheet', False)]
                    
                    file_processed_items = 0
                    
                    for sheet in dollar_sheets:
                        sheet_data = db_handler.get_sheet_data(sheet['id'])
                        if sheet_data:
                            # 코드 아이템 생성
                            code_items = []
                            for row_data in sheet_data:
                                if len(row_data) >= 3:
                                    code_items.append([
                                        "DEFINE", "CONST", "FLOAT32",
                                        f"VAL_{row_data[0]}_{row_data[1]}", 
                                        str(row_data[2]) if row_data[2] else "",
                                        f"Generated from {sheet['name']}"
                                    ])
                            
                            # Cython 코드 생성
                            processed_code = fast_write_cal_list_processing(code_items)
                            file_processed_items += len(processed_code)
                    
                    # DB 연결 해제
                    db_handler.disconnect()
                    
                    file_end_time = time.perf_counter()
                    file_time = file_end_time - file_start_time
                    
                    total_processed_items += file_processed_items
                    
                    print(f"      📁 {db_file.name}: {file_time:.3f}초, {file_processed_items:,}개 항목")
                    
                    # 중간 리소스 체크
                    if i % 2 == 0:  # 2개 파일마다 체크
                        mid_resources = self.measure_system_resources()
                        memory_growth = mid_resources['process_rss_mb'] - start_resources['process_rss_mb']
                        if memory_growth > 100:  # 100MB 이상 증가시 경고
                            print(f"      ⚠️ 메모리 증가: +{memory_growth:.1f}MB")
                
                end_time = time.perf_counter()
                end_resources = self.measure_system_resources()
                
                iteration_time = end_time - start_time
                memory_delta = end_resources['process_rss_mb'] - start_resources['process_rss_mb']
                
                iteration_results.append({
                    'iteration': iteration + 1,
                    'execution_time': iteration_time,
                    'processed_items': total_processed_items,
                    'memory_delta_mb': memory_delta,
                    'start_memory_mb': start_resources['process_rss_mb'],
                    'end_memory_mb': end_resources['process_rss_mb'],
                    'cpu_usage': end_resources['process_cpu_percent']
                })
                
                print(f"   ✅ 반복 {iteration + 1} 완료: {iteration_time:.3f}초")
                print(f"      처리 항목: {total_processed_items:,}개")
                print(f"      메모리 변화: {start_resources['process_rss_mb']:.1f}MB → {end_resources['process_rss_mb']:.1f}MB (+{memory_delta:.1f}MB)")
                
                # 반복 간 가비지 컬렉션
                gc.collect()
                time.sleep(0.5)  # 시스템 안정화
            
            # 성능 저하 분석
            if len(iteration_results) > 1:
                first_time = iteration_results[0]['execution_time']
                last_time = iteration_results[-1]['execution_time']
                performance_degradation = (last_time - first_time) / first_time * 100
                
                print(f"\n📊 성능 저하 분석:")
                print(f"   첫 번째 반복: {first_time:.3f}초")
                print(f"   마지막 반복: {last_time:.3f}초")
                print(f"   성능 변화: {performance_degradation:+.1f}%")
                
                if performance_degradation > 20:
                    print(f"   ⚠️ 심각한 성능 저하 감지!")
                elif performance_degradation > 10:
                    print(f"   ⚠️ 성능 저하 감지")
                else:
                    print(f"   ✅ 안정적인 성능 유지")
            
            return {
                'success': True,
                'iteration_results': iteration_results,
                'total_iterations': iterations,
                'files_count': len(db_files)
            }
            
        except Exception as e:
            print(f"❌ 스트레스 테스트 실패: {e}")
            print(traceback.format_exc())
            return {
                'success': False,
                'error': str(e)
            }
    
    def parallel_processing_test(self, db_files: List[Path]) -> Dict[str, Any]:
        """병렬 처리 성능 테스트"""
        print(f"\n🔀 병렬 처리 성능 테스트: {len(db_files)}개 파일")
        print("=" * 60)
        
        def process_single_db(db_file: Path) -> Dict[str, Any]:
            """단일 DB 파일 처리 (병렬 실행용)"""
            try:
                from data_manager.db_handler_v2 import DBHandlerV2
                from cython_extensions.code_generator_v2 import fast_write_cal_list_processing
                
                start_time = time.perf_counter()
                
                # DB 연결
                db_handler = DBHandlerV2(str(db_file))
                db_handler.connect()
                
                # $ 시트 찾기
                sheets = db_handler.get_sheets()
                dollar_sheets = [s for s in sheets if s.get('is_dollar_sheet', False)]
                
                total_processed_items = 0
                
                for sheet in dollar_sheets:
                    sheet_data = db_handler.get_sheet_data(sheet['id'])
                    if sheet_data:
                        # 코드 아이템 생성
                        code_items = []
                        for row_data in sheet_data:
                            if len(row_data) >= 3:
                                code_items.append([
                                    "DEFINE", "CONST", "FLOAT32",
                                    f"VAL_{row_data[0]}_{row_data[1]}", 
                                    str(row_data[2]) if row_data[2] else "",
                                    f"Generated from {sheet['name']}"
                                ])
                        
                        # Cython 코드 생성
                        processed_code = fast_write_cal_list_processing(code_items)
                        total_processed_items += len(processed_code)
                
                # DB 연결 해제
                db_handler.disconnect()
                
                end_time = time.perf_counter()
                
                return {
                    'success': True,
                    'file_name': db_file.name,
                    'execution_time': end_time - start_time,
                    'processed_items': total_processed_items
                }
                
            except Exception as e:
                return {
                    'success': False,
                    'file_name': db_file.name,
                    'error': str(e)
                }
        
        # 순차 처리 측정
        print("🔄 순차 처리 측정")
        sequential_start = time.perf_counter()
        sequential_results = []
        
        for db_file in db_files:
            result = process_single_db(db_file)
            sequential_results.append(result)
            if result['success']:
                print(f"   ✅ {result['file_name']}: {result['execution_time']:.3f}초")
        
        sequential_time = time.perf_counter() - sequential_start
        
        # 병렬 처리 측정
        print("\n🔀 병렬 처리 측정")
        parallel_start = time.perf_counter()
        
        max_workers = min(len(db_files), multiprocessing.cpu_count())
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            parallel_results = list(executor.map(process_single_db, db_files))
        
        parallel_time = time.perf_counter() - parallel_start
        
        for result in parallel_results:
            if result['success']:
                print(f"   ✅ {result['file_name']}: {result['execution_time']:.3f}초")
        
        # 성능 비교
        speedup = sequential_time / parallel_time if parallel_time > 0 else 0
        
        print(f"\n📊 병렬 처리 성능 비교:")
        print(f"   순차 처리: {sequential_time:.3f}초")
        print(f"   병렬 처리: {parallel_time:.3f}초")
        print(f"   성능 향상: {speedup:.2f}배")
        print(f"   사용 워커: {max_workers}개")
        
        return {
            'sequential_time': sequential_time,
            'parallel_time': parallel_time,
            'speedup': speedup,
            'max_workers': max_workers,
            'sequential_results': sequential_results,
            'parallel_results': parallel_results
        }

if __name__ == "__main__":
    print("🔍 고급 DB → C 코드 변환 성능 분석")
    print("=" * 80)
    
    analyzer = AdvancedDBPerformanceAnalyzer()
    
    # 1. 대용량 테스트 DB 생성
    large_dbs = analyzer.create_large_test_databases(count=5, size_multiplier=2)
    
    if not large_dbs:
        print("❌ 대용량 테스트 DB 생성 실패")
        sys.exit(1)
    
    # 2. 스트레스 테스트 실행
    stress_results = analyzer.stress_test_batch_processing(large_dbs, iterations=3)
    
    # 3. 병렬 처리 테스트 실행
    parallel_results = analyzer.parallel_processing_test(large_dbs)
    
    # 결과 저장
    final_results = {
        'stress_test': stress_results,
        'parallel_test': parallel_results,
        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
    }
    
    with open('advanced_db_performance_analysis.json', 'w', encoding='utf-8') as f:
        json.dump(final_results, f, indent=2, ensure_ascii=False)
    
    print(f"\n📄 고급 분석 결과가 'advanced_db_performance_analysis.json'에 저장되었습니다.")
    print("=" * 80)
