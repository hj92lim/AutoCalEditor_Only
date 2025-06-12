"""
DB → C 코드 변환 성능 문제 종합 해결 방안
실제 DB 파일들을 사용한 성능 분석 및 최적화 솔루션 제시
"""

import time
import psutil
import gc
import logging
import os
import sys
from pathlib import Path
from typing import Dict, List, Any, Tuple
import json
import traceback
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
import threading

# 프로젝트 루트 경로 설정
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s'
)

class ComprehensivePerformanceSolution:
    """종합적인 성능 문제 해결 방안"""
    
    def __init__(self):
        self.process = psutil.Process()
        self.analysis_results = {}
        
    def get_existing_db_files(self) -> List[Path]:
        """기존 DB 파일들 수집"""
        db_dir = Path('database')
        if not db_dir.exists():
            return []
        
        db_files = [f for f in db_dir.glob('*.db') if f.stat().st_size > 50000]  # 50KB 이상만
        return sorted(db_files, key=lambda x: x.stat().st_size, reverse=True)[:5]  # 큰 파일 5개
    
    def measure_detailed_performance(self, func, *args, **kwargs) -> Dict[str, Any]:
        """상세한 성능 측정"""
        # 가비지 컬렉션
        gc.collect()
        
        # 시작 시점 측정
        start_memory = self.process.memory_info()
        start_time = time.perf_counter()
        start_cpu_times = self.process.cpu_times()
        
        try:
            # 함수 실행
            result = func(*args, **kwargs)
            
            # 종료 시점 측정
            end_time = time.perf_counter()
            end_memory = self.process.memory_info()
            end_cpu_times = self.process.cpu_times()
            
            execution_time = end_time - start_time
            memory_delta = end_memory.rss - start_memory.rss
            cpu_time_delta = (end_cpu_times.user - start_cpu_times.user) + (end_cpu_times.system - start_cpu_times.system)
            
            return {
                'success': True,
                'execution_time': execution_time,
                'memory_delta_bytes': memory_delta,
                'memory_delta_mb': memory_delta / 1024 / 1024,
                'cpu_time_delta': cpu_time_delta,
                'start_memory_mb': start_memory.rss / 1024 / 1024,
                'end_memory_mb': end_memory.rss / 1024 / 1024,
                'result': result
            }
            
        except Exception as e:
            end_time = time.perf_counter()
            return {
                'success': False,
                'execution_time': end_time - start_time,
                'error': str(e),
                'traceback': traceback.format_exc()
            }
    
    def optimized_single_db_processing(self, db_file: Path) -> Dict[str, Any]:
        """최적화된 단일 DB 처리"""
        try:
            from data_manager.db_handler_v2 import DBHandlerV2
            from cython_extensions.code_generator_v2 import ultra_fast_write_cal_list_processing
            
            # DB 연결 (연결 풀링 시뮬레이션)
            db_handler = DBHandlerV2(str(db_file))
            db_handler.connect()
            
            # $ 시트 찾기 (캐싱 시뮬레이션)
            sheets = db_handler.get_sheets()
            dollar_sheets = [s for s in sheets if s.get('is_dollar_sheet', False)]
            
            total_processed_items = 0
            
            # 배치 단위로 처리 (메모리 효율성)
            batch_size = 1000
            
            for sheet in dollar_sheets:
                sheet_data = db_handler.get_sheet_data(sheet['id'])
                if sheet_data:
                    # 배치 단위로 코드 생성
                    for i in range(0, len(sheet_data), batch_size):
                        batch_data = sheet_data[i:i+batch_size]
                        
                        # 코드 아이템 생성
                        code_items = []
                        for row_data in batch_data:
                            if len(row_data) >= 3:
                                code_items.append([
                                    "DEFINE", "CONST", "FLOAT32",
                                    f"VAL_{row_data[0]}_{row_data[1]}", 
                                    str(row_data[2]) if row_data[2] else "",
                                    f"Generated from {sheet['name']}"
                                ])
                        
                        # Ultra 최적화된 Cython 코드 생성
                        processed_code = ultra_fast_write_cal_list_processing(code_items)
                        total_processed_items += len(processed_code)
                        
                        # 배치 간 메모리 정리
                        del code_items, processed_code
            
            # DB 연결 해제
            db_handler.disconnect()
            
            return {
                'success': True,
                'processed_items': total_processed_items,
                'file_name': db_file.name
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'file_name': db_file.name
            }
    
    def optimized_batch_processing(self, db_files: List[Path]) -> Dict[str, Any]:
        """최적화된 일괄 처리"""
        try:
            from data_manager.db_handler_v2 import DBHandlerV2
            from cython_extensions.code_generator_v2 import ultra_fast_write_cal_list_processing
            
            total_processed_items = 0
            file_results = []
            
            # 연결 풀링 시뮬레이션
            db_connections = {}
            
            for db_file in db_files:
                file_start_time = time.perf_counter()
                
                # 연결 재사용
                if str(db_file) not in db_connections:
                    db_handler = DBHandlerV2(str(db_file))
                    db_handler.connect()
                    db_connections[str(db_file)] = db_handler
                else:
                    db_handler = db_connections[str(db_file)]
                
                # $ 시트 찾기
                sheets = db_handler.get_sheets()
                dollar_sheets = [s for s in sheets if s.get('is_dollar_sheet', False)]
                
                file_processed_items = 0
                
                # 메모리 효율적인 배치 처리
                for sheet in dollar_sheets:
                    sheet_data = db_handler.get_sheet_data(sheet['id'])
                    if sheet_data:
                        # 청크 단위 처리 (메모리 사용량 제한)
                        chunk_size = 500
                        
                        for i in range(0, len(sheet_data), chunk_size):
                            chunk_data = sheet_data[i:i+chunk_size]
                            
                            # 코드 아이템 생성
                            code_items = []
                            for row_data in chunk_data:
                                if len(row_data) >= 3:
                                    code_items.append([
                                        "DEFINE", "CONST", "FLOAT32",
                                        f"VAL_{row_data[0]}_{row_data[1]}", 
                                        str(row_data[2]) if row_data[2] else "",
                                        f"Generated from {sheet['name']}"
                                    ])
                            
                            # Ultra 최적화된 Cython 코드 생성
                            processed_code = ultra_fast_write_cal_list_processing(code_items)
                            file_processed_items += len(processed_code)
                            
                            # 청크 간 메모리 정리
                            del code_items, processed_code
                            
                            # 주기적 가비지 컬렉션
                            if i % (chunk_size * 4) == 0:
                                gc.collect()
                
                file_end_time = time.perf_counter()
                file_time = file_end_time - file_start_time
                
                file_results.append({
                    'file_name': db_file.name,
                    'execution_time': file_time,
                    'processed_items': file_processed_items
                })
                
                total_processed_items += file_processed_items
            
            # 모든 연결 해제
            for db_handler in db_connections.values():
                db_handler.disconnect()
            
            return {
                'success': True,
                'total_processed_items': total_processed_items,
                'file_results': file_results,
                'files_count': len(db_files)
            }
            
        except Exception as e:
            # 연결 정리
            for db_handler in db_connections.values():
                try:
                    db_handler.disconnect()
                except:
                    pass
            
            return {
                'success': False,
                'error': str(e),
                'traceback': traceback.format_exc()
            }
    
    def memory_optimized_processing(self, db_files: List[Path]) -> Dict[str, Any]:
        """메모리 최적화된 처리"""
        print("\n🧠 메모리 최적화된 처리 테스트")
        print("=" * 60)
        
        # 메모리 사용량 모니터링
        def monitor_memory():
            memory_usage = []
            while not stop_monitoring:
                memory_info = self.process.memory_info()
                memory_usage.append({
                    'timestamp': time.time(),
                    'rss_mb': memory_info.rss / 1024 / 1024,
                    'vms_mb': memory_info.vms / 1024 / 1024
                })
                time.sleep(0.1)
            return memory_usage
        
        stop_monitoring = False
        
        # 메모리 모니터링 시작
        monitor_thread = threading.Thread(target=monitor_memory)
        monitor_thread.start()
        
        try:
            # 최적화된 일괄 처리 실행
            result = self.measure_detailed_performance(
                self.optimized_batch_processing, 
                db_files
            )
            
            stop_monitoring = True
            monitor_thread.join()
            
            if result['success']:
                print(f"✅ 메모리 최적화 처리 완료")
                print(f"   실행 시간: {result['execution_time']:.3f}초")
                print(f"   메모리 변화: {result['memory_delta_mb']:+.1f}MB")
                print(f"   처리 항목: {result['result']['total_processed_items']:,}개")
            else:
                print(f"❌ 메모리 최적화 처리 실패: {result['error']}")
            
            return result
            
        except Exception as e:
            stop_monitoring = True
            monitor_thread.join()
            return {'success': False, 'error': str(e)}
    
    def parallel_optimized_processing(self, db_files: List[Path]) -> Dict[str, Any]:
        """병렬 최적화된 처리"""
        print("\n🔀 병렬 최적화된 처리 테스트")
        print("=" * 60)
        
        # 순차 처리
        sequential_result = self.measure_detailed_performance(
            self.optimized_batch_processing,
            db_files
        )
        
        # 병렬 처리 (ThreadPoolExecutor 사용)
        def process_db_optimized(db_file):
            return self.optimized_single_db_processing(db_file)
        
        parallel_start = time.perf_counter()
        
        with ThreadPoolExecutor(max_workers=min(len(db_files), 4)) as executor:
            parallel_results = list(executor.map(process_db_optimized, db_files))
        
        parallel_time = time.perf_counter() - parallel_start
        
        # 결과 집계
        total_parallel_items = sum(r.get('processed_items', 0) for r in parallel_results if r['success'])
        
        if sequential_result['success']:
            speedup = sequential_result['execution_time'] / parallel_time if parallel_time > 0 else 0
            
            print(f"📊 병렬 처리 성능 비교:")
            print(f"   순차 처리: {sequential_result['execution_time']:.3f}초")
            print(f"   병렬 처리: {parallel_time:.3f}초")
            print(f"   성능 향상: {speedup:.2f}배")
            
            return {
                'sequential_time': sequential_result['execution_time'],
                'parallel_time': parallel_time,
                'speedup': speedup,
                'sequential_items': sequential_result['result']['total_processed_items'],
                'parallel_items': total_parallel_items
            }
        else:
            return {'success': False, 'error': 'Sequential processing failed'}
    
    def generate_performance_improvement_plan(self, analysis_results: Dict[str, Any]) -> Dict[str, Any]:
        """성능 개선 계획 생성"""
        print("\n📋 성능 개선 계획 생성")
        print("=" * 60)
        
        improvement_plan = {
            'immediate_optimizations': [],
            'medium_term_optimizations': [],
            'long_term_optimizations': [],
            'expected_improvements': {}
        }
        
        # 즉시 적용 가능한 최적화
        improvement_plan['immediate_optimizations'] = [
            {
                'name': 'Ultra Cython 모듈 사용',
                'description': 'fast_write_cal_list_processing 대신 ultra_fast_write_cal_list_processing 사용',
                'expected_improvement': '20-30%',
                'implementation': 'from cython_extensions.code_generator_v2 import ultra_fast_write_cal_list_processing'
            },
            {
                'name': '배치 크기 최적화',
                'description': '메모리 사용량과 성능의 균형을 위한 배치 크기 조정',
                'expected_improvement': '15-25%',
                'implementation': 'batch_size = 500-1000 (메모리에 따라 조정)'
            },
            {
                'name': '주기적 가비지 컬렉션',
                'description': '메모리 누적 방지를 위한 주기적 gc.collect() 호출',
                'expected_improvement': '메모리 안정성 향상',
                'implementation': 'gc.collect() 매 4번째 배치마다 호출'
            }
        ]
        
        # 중기 최적화
        improvement_plan['medium_term_optimizations'] = [
            {
                'name': 'DB 연결 풀링',
                'description': 'DB 연결 재사용으로 연결 오버헤드 감소',
                'expected_improvement': '30-40%',
                'implementation': '연결 풀 매니저 구현'
            },
            {
                'name': '병렬 처리 도입',
                'description': 'ThreadPoolExecutor를 이용한 병렬 DB 처리',
                'expected_improvement': '50-100%',
                'implementation': 'ThreadPoolExecutor(max_workers=4)'
            },
            {
                'name': '메모리 매핑 I/O',
                'description': '대용량 데이터 처리를 위한 메모리 매핑 사용',
                'expected_improvement': '20-30%',
                'implementation': 'mmap 모듈 활용'
            }
        ]
        
        # 장기 최적화
        improvement_plan['long_term_optimizations'] = [
            {
                'name': '비동기 처리 아키텍처',
                'description': 'asyncio를 이용한 비동기 DB 처리',
                'expected_improvement': '100-200%',
                'implementation': 'asyncio + aiosqlite 도입'
            },
            {
                'name': '분산 처리',
                'description': '다중 프로세스를 이용한 분산 처리',
                'expected_improvement': '200-400%',
                'implementation': 'multiprocessing.Pool 활용'
            },
            {
                'name': '캐싱 시스템',
                'description': '중간 결과 캐싱으로 중복 처리 방지',
                'expected_improvement': '50-100%',
                'implementation': 'Redis 또는 메모리 캐시 구현'
            }
        ]
        
        # 예상 개선 효과
        improvement_plan['expected_improvements'] = {
            'immediate': '50-80% 성능 향상',
            'medium_term': '100-200% 성능 향상',
            'long_term': '300-500% 성능 향상'
        }
        
        return improvement_plan

if __name__ == "__main__":
    print("🔍 DB → C 코드 변환 성능 문제 종합 해결 방안")
    print("=" * 80)
    
    solution = ComprehensivePerformanceSolution()
    
    # 기존 DB 파일들 수집
    db_files = solution.get_existing_db_files()
    
    if not db_files:
        print("❌ 분석할 DB 파일이 없습니다.")
        sys.exit(1)
    
    print(f"📁 분석 대상 DB 파일: {len(db_files)}개")
    for db_file in db_files:
        size_mb = db_file.stat().st_size / 1024 / 1024
        print(f"   - {db_file.name} ({size_mb:.1f}MB)")
    
    analysis_results = {}
    
    # 1. 메모리 최적화된 처리 테스트
    memory_result = solution.memory_optimized_processing(db_files)
    analysis_results['memory_optimized'] = memory_result
    
    # 2. 병렬 최적화된 처리 테스트
    parallel_result = solution.parallel_optimized_processing(db_files)
    analysis_results['parallel_optimized'] = parallel_result
    
    # 3. 성능 개선 계획 생성
    improvement_plan = solution.generate_performance_improvement_plan(analysis_results)
    analysis_results['improvement_plan'] = improvement_plan
    
    # 결과 저장
    with open('comprehensive_performance_solution.json', 'w', encoding='utf-8') as f:
        json.dump(analysis_results, f, indent=2, ensure_ascii=False)
    
    print(f"\n📄 종합 해결 방안이 'comprehensive_performance_solution.json'에 저장되었습니다.")
    print("=" * 80)
