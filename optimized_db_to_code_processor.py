"""
최적화된 DB → C 코드 변환 프로세서
모든 성능 개선 기법을 적용한 최종 솔루션
"""

import time
import gc
import logging
import os
import sys
from pathlib import Path
from typing import Dict, List, Any, Tuple, Optional
import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

# 프로젝트 루트 경로 설정
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s'
)

@dataclass
class ProcessingConfig:
    """처리 설정"""
    batch_size: int = 500
    chunk_size: int = 1000
    max_workers: int = 4
    gc_interval: int = 4
    enable_connection_pooling: bool = True
    enable_parallel_processing: bool = True
    enable_memory_optimization: bool = True

class ConnectionPool:
    """DB 연결 풀"""
    
    def __init__(self, max_connections: int = 10):
        self.max_connections = max_connections
        self.connections = {}
        self.lock = threading.Lock()
    
    def get_connection(self, db_path: str):
        """연결 가져오기"""
        with self.lock:
            if db_path not in self.connections:
                from data_manager.db_handler_v2 import DBHandlerV2
                db_handler = DBHandlerV2(db_path)
                db_handler.connect()
                self.connections[db_path] = db_handler
            return self.connections[db_path]
    
    def close_all(self):
        """모든 연결 해제"""
        with self.lock:
            for db_handler in self.connections.values():
                try:
                    db_handler.disconnect()
                except:
                    pass
            self.connections.clear()

class OptimizedDBToCodeProcessor:
    """최적화된 DB → C 코드 변환 프로세서"""
    
    def __init__(self, config: ProcessingConfig = None):
        self.config = config or ProcessingConfig()
        self.connection_pool = ConnectionPool() if self.config.enable_connection_pooling else None
        self.stats = {
            'total_files_processed': 0,
            'total_items_processed': 0,
            'total_execution_time': 0,
            'memory_usage_peak': 0
        }
    
    def process_single_db_optimized(self, db_file: Path) -> Dict[str, Any]:
        """최적화된 단일 DB 처리"""
        start_time = time.perf_counter()
        
        try:
            # 연결 풀 사용 또는 직접 연결
            if self.connection_pool:
                db_handler = self.connection_pool.get_connection(str(db_file))
            else:
                from data_manager.db_handler_v2 import DBHandlerV2
                db_handler = DBHandlerV2(str(db_file))
                db_handler.connect()
            
            # $ 시트 찾기
            sheets = db_handler.get_sheets()
            dollar_sheets = [s for s in sheets if s.get('is_dollar_sheet', False)]
            
            total_processed_items = 0
            
            # Ultra 최적화된 Cython 모듈 사용
            from cython_extensions.code_generator_v2 import ultra_fast_write_cal_list_processing
            
            # 메모리 효율적인 배치 처리
            for sheet_idx, sheet in enumerate(dollar_sheets):
                sheet_data = db_handler.get_sheet_data(sheet['id'])
                if not sheet_data:
                    continue
                
                # 청크 단위로 처리
                for chunk_start in range(0, len(sheet_data), self.config.chunk_size):
                    chunk_end = min(chunk_start + self.config.chunk_size, len(sheet_data))
                    chunk_data = sheet_data[chunk_start:chunk_end]
                    
                    # 배치 단위로 코드 생성
                    for batch_start in range(0, len(chunk_data), self.config.batch_size):
                        batch_end = min(batch_start + self.config.batch_size, len(chunk_data))
                        batch_data = chunk_data[batch_start:batch_end]
                        
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
                        if code_items:
                            processed_code = ultra_fast_write_cal_list_processing(code_items)
                            total_processed_items += len(processed_code)
                        
                        # 배치 간 메모리 정리
                        del code_items
                        if 'processed_code' in locals():
                            del processed_code
                        
                        # 주기적 가비지 컬렉션
                        if (batch_start // self.config.batch_size) % self.config.gc_interval == 0:
                            gc.collect()
            
            # 연결 풀을 사용하지 않는 경우에만 연결 해제
            if not self.connection_pool:
                db_handler.disconnect()
            
            execution_time = time.perf_counter() - start_time
            
            return {
                'success': True,
                'file_name': db_file.name,
                'execution_time': execution_time,
                'processed_items': total_processed_items,
                'sheets_processed': len(dollar_sheets)
            }
            
        except Exception as e:
            execution_time = time.perf_counter() - start_time
            return {
                'success': False,
                'file_name': db_file.name,
                'execution_time': execution_time,
                'error': str(e)
            }
    
    def process_batch_sequential(self, db_files: List[Path]) -> Dict[str, Any]:
        """순차 일괄 처리"""
        start_time = time.perf_counter()
        
        results = []
        total_processed_items = 0
        
        for db_file in db_files:
            result = self.process_single_db_optimized(db_file)
            results.append(result)
            
            if result['success']:
                total_processed_items += result['processed_items']
        
        execution_time = time.perf_counter() - start_time
        
        return {
            'method': 'sequential',
            'execution_time': execution_time,
            'total_processed_items': total_processed_items,
            'files_processed': len([r for r in results if r['success']]),
            'results': results
        }
    
    def process_batch_parallel(self, db_files: List[Path]) -> Dict[str, Any]:
        """병렬 일괄 처리"""
        start_time = time.perf_counter()
        
        with ThreadPoolExecutor(max_workers=self.config.max_workers) as executor:
            results = list(executor.map(self.process_single_db_optimized, db_files))
        
        execution_time = time.perf_counter() - start_time
        
        total_processed_items = sum(r.get('processed_items', 0) for r in results if r['success'])
        
        return {
            'method': 'parallel',
            'execution_time': execution_time,
            'total_processed_items': total_processed_items,
            'files_processed': len([r for r in results if r['success']]),
            'max_workers': self.config.max_workers,
            'results': results
        }
    
    def process_batch_optimized(self, db_files: List[Path]) -> Dict[str, Any]:
        """최적화된 일괄 처리 (자동 선택)"""
        if self.config.enable_parallel_processing and len(db_files) > 1:
            return self.process_batch_parallel(db_files)
        else:
            return self.process_batch_sequential(db_files)
    
    def benchmark_processing_methods(self, db_files: List[Path]) -> Dict[str, Any]:
        """처리 방법별 벤치마크"""
        print("\n🏁 처리 방법별 성능 벤치마크")
        print("=" * 60)
        
        benchmark_results = {}
        
        # 1. 기존 방식 (참조용)
        print("🔄 기존 방식 측정")
        original_result = self.measure_original_processing(db_files)
        benchmark_results['original'] = original_result
        
        # 2. 순차 최적화 처리
        print("🔄 순차 최적화 처리 측정")
        self.config.enable_parallel_processing = False
        sequential_result = self.process_batch_optimized(db_files)
        benchmark_results['sequential_optimized'] = sequential_result
        
        # 3. 병렬 최적화 처리
        print("🔄 병렬 최적화 처리 측정")
        self.config.enable_parallel_processing = True
        parallel_result = self.process_batch_optimized(db_files)
        benchmark_results['parallel_optimized'] = parallel_result
        
        # 성능 비교
        print(f"\n📊 성능 비교 결과:")
        
        if original_result['success']:
            original_time = original_result['execution_time']
            sequential_time = sequential_result['execution_time']
            parallel_time = parallel_result['execution_time']
            
            sequential_speedup = original_time / sequential_time if sequential_time > 0 else 0
            parallel_speedup = original_time / parallel_time if parallel_time > 0 else 0
            
            print(f"   기존 방식:      {original_time:.3f}초")
            print(f"   순차 최적화:    {sequential_time:.3f}초 ({sequential_speedup:.2f}배 빠름)")
            print(f"   병렬 최적화:    {parallel_time:.3f}초 ({parallel_speedup:.2f}배 빠름)")
            
            # 목표 달성 여부 확인
            target_improvement = 0.5  # 50% 단축 목표
            sequential_improvement = (original_time - sequential_time) / original_time
            parallel_improvement = (original_time - parallel_time) / original_time
            
            print(f"\n🎯 성능 개선 목표 달성 여부:")
            print(f"   목표: {target_improvement*100:.0f}% 단축")
            print(f"   순차 최적화: {sequential_improvement*100:.1f}% 단축 {'✅' if sequential_improvement >= target_improvement else '❌'}")
            print(f"   병렬 최적화: {parallel_improvement*100:.1f}% 단축 {'✅' if parallel_improvement >= target_improvement else '❌'}")
        
        return benchmark_results
    
    def measure_original_processing(self, db_files: List[Path]) -> Dict[str, Any]:
        """기존 방식 성능 측정 (참조용)"""
        start_time = time.perf_counter()
        
        try:
            from data_manager.db_handler_v2 import DBHandlerV2
            from cython_extensions.code_generator_v2 import fast_write_cal_list_processing
            
            total_processed_items = 0
            
            for db_file in db_files:
                # 매번 새로운 연결
                db_handler = DBHandlerV2(str(db_file))
                db_handler.connect()
                
                sheets = db_handler.get_sheets()
                dollar_sheets = [s for s in sheets if s.get('is_dollar_sheet', False)]
                
                for sheet in dollar_sheets:
                    sheet_data = db_handler.get_sheet_data(sheet['id'])
                    if sheet_data:
                        # 전체 데이터를 한 번에 처리
                        code_items = []
                        for row_data in sheet_data:
                            if len(row_data) >= 3:
                                code_items.append([
                                    "DEFINE", "CONST", "FLOAT32",
                                    f"VAL_{row_data[0]}_{row_data[1]}", 
                                    str(row_data[2]) if row_data[2] else "",
                                    f"Generated from {sheet['name']}"
                                ])
                        
                        # 기본 Cython 코드 생성
                        processed_code = fast_write_cal_list_processing(code_items)
                        total_processed_items += len(processed_code)
                
                db_handler.disconnect()
            
            execution_time = time.perf_counter() - start_time
            
            return {
                'success': True,
                'execution_time': execution_time,
                'total_processed_items': total_processed_items,
                'method': 'original'
            }
            
        except Exception as e:
            execution_time = time.perf_counter() - start_time
            return {
                'success': False,
                'execution_time': execution_time,
                'error': str(e),
                'method': 'original'
            }
    
    def cleanup(self):
        """리소스 정리"""
        if self.connection_pool:
            self.connection_pool.close_all()
        gc.collect()

def main():
    """메인 실행 함수"""
    print("🚀 최적화된 DB → C 코드 변환 프로세서")
    print("=" * 80)
    
    # DB 파일 수집
    db_dir = Path('database')
    if not db_dir.exists():
        print("❌ Database 디렉토리가 존재하지 않습니다.")
        return
    
    db_files = [f for f in db_dir.glob('*.db') if f.stat().st_size > 50000]  # 50KB 이상
    db_files = sorted(db_files, key=lambda x: x.stat().st_size, reverse=True)[:5]  # 큰 파일 5개
    
    if not db_files:
        print("❌ 분석할 DB 파일이 없습니다.")
        return
    
    print(f"📁 처리 대상 DB 파일: {len(db_files)}개")
    for db_file in db_files:
        size_mb = db_file.stat().st_size / 1024 / 1024
        print(f"   - {db_file.name} ({size_mb:.1f}MB)")
    
    # 최적화된 프로세서 생성
    config = ProcessingConfig(
        batch_size=500,
        chunk_size=1000,
        max_workers=4,
        gc_interval=4,
        enable_connection_pooling=True,
        enable_parallel_processing=True,
        enable_memory_optimization=True
    )
    
    processor = OptimizedDBToCodeProcessor(config)
    
    try:
        # 벤치마크 실행
        benchmark_results = processor.benchmark_processing_methods(db_files)
        
        # 결과 저장
        import json
        with open('optimized_db_processing_results.json', 'w', encoding='utf-8') as f:
            json.dump(benchmark_results, f, indent=2, ensure_ascii=False)
        
        print(f"\n📄 최적화 결과가 'optimized_db_processing_results.json'에 저장되었습니다.")
        
    finally:
        processor.cleanup()
    
    print("=" * 80)

if __name__ == "__main__":
    main()
