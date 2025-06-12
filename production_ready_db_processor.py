"""
프로덕션 준비된 DB → C 코드 변환 프로세서
Phase 1 + Phase 2 최적화를 실제 시스템에 적용
"""

import time
import gc
import logging
import os
import sys
import threading
from pathlib import Path
from typing import Dict, List, Any, Optional
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
import json

# 프로젝트 루트 경로 설정
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s'
)

@dataclass
class ProductionConfig:
    """프로덕션 설정"""
    # Phase 1 최적화
    batch_size: int = 500
    chunk_size: int = 1000
    gc_interval: int = 4
    
    # Phase 2 최적화
    enable_connection_pooling: bool = True
    enable_parallel_processing: bool = True
    max_workers: int = 4
    connection_pool_size: int = 10
    
    # 메모리 관리
    max_memory_mb: int = 1024  # 1GB 제한
    memory_check_interval: int = 10

class ProductionConnectionPool:
    """프로덕션용 DB 연결 풀"""
    
    def __init__(self, max_connections: int = 10):
        self.max_connections = max_connections
        self.connections = {}
        self.connection_usage = {}
        self.lock = threading.Lock()
        self.logger = logging.getLogger(__name__)
    
    def get_connection(self, db_path: str):
        """연결 가져오기 (스레드 안전)"""
        with self.lock:
            if db_path not in self.connections:
                try:
                    from data_manager.db_handler_v2 import DBHandlerV2
                    db_handler = DBHandlerV2(db_path)
                    db_handler.connect()
                    self.connections[db_path] = db_handler
                    self.connection_usage[db_path] = 0
                    self.logger.info(f"새 DB 연결 생성: {Path(db_path).name}")
                except Exception as e:
                    self.logger.error(f"DB 연결 실패 {db_path}: {e}")
                    raise
            
            self.connection_usage[db_path] += 1
            return self.connections[db_path]
    
    def release_connection(self, db_path: str):
        """연결 사용 완료 표시"""
        with self.lock:
            if db_path in self.connection_usage:
                self.connection_usage[db_path] -= 1
    
    def close_all(self):
        """모든 연결 해제"""
        with self.lock:
            for db_path, db_handler in self.connections.items():
                try:
                    db_handler.disconnect()
                    self.logger.info(f"DB 연결 해제: {Path(db_path).name}")
                except Exception as e:
                    self.logger.error(f"DB 연결 해제 실패 {db_path}: {e}")
            
            self.connections.clear()
            self.connection_usage.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """연결 풀 통계"""
        with self.lock:
            return {
                'total_connections': len(self.connections),
                'active_connections': sum(1 for usage in self.connection_usage.values() if usage > 0),
                'connection_usage': dict(self.connection_usage)
            }

class ProductionDBProcessor:
    """프로덕션용 DB → C 코드 변환 프로세서"""
    
    def __init__(self, config: ProductionConfig = None):
        self.config = config or ProductionConfig()
        self.connection_pool = ProductionConnectionPool(self.config.connection_pool_size) if self.config.enable_connection_pooling else None
        self.logger = logging.getLogger(__name__)
        self.stats = {
            'total_files_processed': 0,
            'total_items_processed': 0,
            'total_execution_time': 0,
            'memory_usage_peak': 0,
            'errors': []
        }
    
    def check_memory_usage(self) -> float:
        """메모리 사용량 체크"""
        import psutil
        process = psutil.Process()
        memory_mb = process.memory_info().rss / 1024 / 1024
        
        if memory_mb > self.config.max_memory_mb:
            self.logger.warning(f"메모리 사용량 초과: {memory_mb:.1f}MB > {self.config.max_memory_mb}MB")
            gc.collect()  # 강제 가비지 컬렉션
        
        return memory_mb
    
    def process_single_db_production(self, db_file: Path) -> Dict[str, Any]:
        """프로덕션용 단일 DB 처리"""
        start_time = time.perf_counter()
        file_name = db_file.name
        
        try:
            self.logger.info(f"DB 처리 시작: {file_name}")
            
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
            
            if not dollar_sheets:
                self.logger.warning(f"$ 시트가 없음: {file_name}")
                return {
                    'success': True,
                    'file_name': file_name,
                    'execution_time': time.perf_counter() - start_time,
                    'processed_items': 0,
                    'warning': 'No dollar sheets found'
                }
            
            total_processed_items = 0
            
            # Ultra 최적화된 Cython 모듈 사용
            from cython_extensions.code_generator_v2 import ultra_fast_write_cal_list_processing
            
            # 메모리 효율적인 배치 처리
            for sheet_idx, sheet in enumerate(dollar_sheets):
                sheet_data = db_handler.get_sheet_data(sheet['id'])
                if not sheet_data:
                    continue
                
                self.logger.debug(f"시트 처리: {sheet['name']} ({len(sheet_data)}개 셀)")
                
                # 청크 단위로 처리
                for chunk_start in range(0, len(sheet_data), self.config.chunk_size):
                    chunk_end = min(chunk_start + self.config.chunk_size, len(sheet_data))
                    chunk_data = sheet_data[chunk_start:chunk_end]
                    
                    # 배치 단위로 코드 생성
                    batch_count = 0
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
                        
                        batch_count += 1
                        
                        # 주기적 가비지 컬렉션
                        if batch_count % self.config.gc_interval == 0:
                            gc.collect()
                        
                        # 주기적 메모리 체크
                        if batch_count % self.config.memory_check_interval == 0:
                            self.check_memory_usage()
            
            # 연결 풀을 사용하지 않는 경우에만 연결 해제
            if not self.connection_pool:
                db_handler.disconnect()
            else:
                self.connection_pool.release_connection(str(db_file))
            
            execution_time = time.perf_counter() - start_time
            
            self.logger.info(f"DB 처리 완료: {file_name} ({execution_time:.3f}초, {total_processed_items:,}개 항목)")
            
            return {
                'success': True,
                'file_name': file_name,
                'execution_time': execution_time,
                'processed_items': total_processed_items,
                'sheets_processed': len(dollar_sheets)
            }
            
        except Exception as e:
            execution_time = time.perf_counter() - start_time
            error_msg = f"DB 처리 실패: {file_name} - {str(e)}"
            self.logger.error(error_msg)
            self.stats['errors'].append(error_msg)
            
            return {
                'success': False,
                'file_name': file_name,
                'execution_time': execution_time,
                'error': str(e)
            }
    
    def process_batch_production(self, db_files: List[Path]) -> Dict[str, Any]:
        """프로덕션용 일괄 처리"""
        start_time = time.perf_counter()
        
        self.logger.info(f"일괄 처리 시작: {len(db_files)}개 파일")
        
        if self.config.enable_parallel_processing and len(db_files) > 1:
            # 병렬 처리
            self.logger.info(f"병렬 처리 모드 (워커: {self.config.max_workers}개)")
            results = self._process_parallel(db_files)
        else:
            # 순차 처리
            self.logger.info("순차 처리 모드")
            results = self._process_sequential(db_files)
        
        execution_time = time.perf_counter() - start_time
        
        # 통계 업데이트
        successful_results = [r for r in results if r['success']]
        total_processed_items = sum(r.get('processed_items', 0) for r in successful_results)
        
        self.stats['total_files_processed'] += len(successful_results)
        self.stats['total_items_processed'] += total_processed_items
        self.stats['total_execution_time'] += execution_time
        
        self.logger.info(f"일괄 처리 완료: {execution_time:.3f}초, {total_processed_items:,}개 항목")
        
        return {
            'success': True,
            'execution_time': execution_time,
            'total_processed_items': total_processed_items,
            'files_processed': len(successful_results),
            'files_failed': len(results) - len(successful_results),
            'results': results,
            'processing_mode': 'parallel' if self.config.enable_parallel_processing and len(db_files) > 1 else 'sequential'
        }
    
    def _process_sequential(self, db_files: List[Path]) -> List[Dict[str, Any]]:
        """순차 처리"""
        results = []
        for db_file in db_files:
            result = self.process_single_db_production(db_file)
            results.append(result)
        return results
    
    def _process_parallel(self, db_files: List[Path]) -> List[Dict[str, Any]]:
        """병렬 처리"""
        with ThreadPoolExecutor(max_workers=self.config.max_workers) as executor:
            results = list(executor.map(self.process_single_db_production, db_files))
        return results
    
    def get_stats(self) -> Dict[str, Any]:
        """처리 통계 반환"""
        stats = dict(self.stats)
        
        if self.connection_pool:
            stats['connection_pool'] = self.connection_pool.get_stats()
        
        # 메모리 사용량
        stats['current_memory_mb'] = self.check_memory_usage()
        
        return stats
    
    def cleanup(self):
        """리소스 정리"""
        self.logger.info("리소스 정리 시작")
        
        if self.connection_pool:
            self.connection_pool.close_all()
        
        gc.collect()
        self.logger.info("리소스 정리 완료")

def main():
    """메인 실행 함수"""
    print("🚀 프로덕션 준비된 DB → C 코드 변환 프로세서")
    print("=" * 80)
    
    # 설정
    config = ProductionConfig(
        batch_size=500,
        chunk_size=1000,
        gc_interval=4,
        enable_connection_pooling=True,
        enable_parallel_processing=True,
        max_workers=4,
        connection_pool_size=10,
        max_memory_mb=1024
    )
    
    # DB 파일 수집
    db_dir = Path('database')
    if not db_dir.exists():
        print("❌ Database 디렉토리가 존재하지 않습니다.")
        return
    
    db_files = [f for f in db_dir.glob('*.db') if f.stat().st_size > 50000]
    
    if not db_files:
        print("❌ 처리할 DB 파일이 없습니다.")
        return
    
    print(f"📁 처리 대상: {len(db_files)}개 파일")
    
    # 프로세서 생성 및 실행
    processor = ProductionDBProcessor(config)
    
    try:
        # 일괄 처리 실행
        result = processor.process_batch_production(db_files)
        
        # 결과 출력
        print(f"\n📊 처리 결과:")
        print(f"   실행 시간: {result['execution_time']:.3f}초")
        print(f"   처리 항목: {result['total_processed_items']:,}개")
        print(f"   성공 파일: {result['files_processed']}개")
        print(f"   실패 파일: {result['files_failed']}개")
        print(f"   처리 모드: {result['processing_mode']}")
        
        # 통계 출력
        stats = processor.get_stats()
        print(f"\n📈 시스템 통계:")
        print(f"   메모리 사용량: {stats['current_memory_mb']:.1f}MB")
        if 'connection_pool' in stats:
            print(f"   연결 풀: {stats['connection_pool']['total_connections']}개 연결")
        
        # 결과 저장
        with open('production_processing_results.json', 'w', encoding='utf-8') as f:
            json.dump({
                'result': result,
                'stats': stats,
                'config': config.__dict__
            }, f, indent=2, ensure_ascii=False)
        
        print(f"\n📄 결과가 'production_processing_results.json'에 저장되었습니다.")
        
    except Exception as e:
        print(f"❌ 처리 실패: {e}")
        logging.error(f"프로덕션 처리 실패: {e}")
    
    finally:
        processor.cleanup()
    
    print("=" * 80)

if __name__ == "__main__":
    main()
