"""
Phase 3: 분산 DB → C 코드 변환 프로세서
multiprocessing을 이용한 분산 처리 구현
"""

import multiprocessing as mp
import time
import gc
import logging
import os
import sys
from pathlib import Path
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass
import json
import queue
import psutil

# 프로젝트 루트 경로 설정
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s'
)

@dataclass
class DistributedConfig:
    """분산 처리 설정"""
    batch_size: int = 500
    chunk_size: int = 1000
    gc_interval: int = 4
    max_processes: int = None  # None이면 CPU 코어 수
    max_queue_size: int = 100
    worker_timeout: float = 300.0  # 5분
    enable_shared_memory: bool = True
    memory_limit_mb: int = 512  # 프로세스당 메모리 제한

def process_single_db_worker(args: Tuple[str, DistributedConfig]) -> Dict[str, Any]:
    """워커 프로세스에서 실행되는 단일 DB 처리 함수"""
    db_path, config = args
    
    # 워커 프로세스 초기화
    worker_logger = logging.getLogger(f"worker_{os.getpid()}")
    start_time = time.perf_counter()
    file_name = Path(db_path).name
    
    try:
        worker_logger.info(f"워커 {os.getpid()}: DB 처리 시작 - {file_name}")
        
        # 프로세스별 메모리 모니터링
        process = psutil.Process()
        start_memory = process.memory_info().rss / 1024 / 1024
        
        # 프로젝트 경로 재설정 (워커 프로세스에서)
        sys.path.insert(0, str(Path(__file__).parent))
        
        # DB 연결
        from data_manager.db_handler_v2 import DBHandlerV2
        db_handler = DBHandlerV2(db_path)
        db_handler.connect()
        
        # $ 시트 찾기
        sheets = db_handler.get_sheets()
        dollar_sheets = [s for s in sheets if s.get('is_dollar_sheet', False)]
        
        if not dollar_sheets:
            worker_logger.warning(f"워커 {os.getpid()}: $ 시트가 없음 - {file_name}")
            db_handler.disconnect()
            return {
                'success': True,
                'file_name': file_name,
                'execution_time': time.perf_counter() - start_time,
                'processed_items': 0,
                'worker_pid': os.getpid(),
                'warning': 'No dollar sheets found'
            }
        
        # Ultra 최적화된 Cython 모듈 사용
        from cython_extensions.code_generator_v2 import ultra_fast_write_cal_list_processing
        
        total_processed_items = 0
        
        # 메모리 효율적인 배치 처리
        for sheet_idx, sheet in enumerate(dollar_sheets):
            sheet_data = db_handler.get_sheet_data(sheet['id'])
            if not sheet_data:
                continue
            
            worker_logger.debug(f"워커 {os.getpid()}: 시트 처리 - {sheet['name']} ({len(sheet_data)}개 셀)")
            
            # 청크 단위로 처리
            for chunk_start in range(0, len(sheet_data), config.chunk_size):
                chunk_end = min(chunk_start + config.chunk_size, len(sheet_data))
                chunk_data = sheet_data[chunk_start:chunk_end]
                
                # 배치 단위로 코드 생성
                batch_count = 0
                for batch_start in range(0, len(chunk_data), config.batch_size):
                    batch_end = min(batch_start + config.batch_size, len(chunk_data))
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
                    if batch_count % config.gc_interval == 0:
                        gc.collect()
                    
                    # 메모리 사용량 체크
                    if batch_count % 20 == 0:
                        current_memory = process.memory_info().rss / 1024 / 1024
                        if current_memory > config.memory_limit_mb:
                            worker_logger.warning(f"워커 {os.getpid()}: 메모리 제한 초과 {current_memory:.1f}MB")
                            gc.collect()
        
        # DB 연결 해제
        db_handler.disconnect()
        
        execution_time = time.perf_counter() - start_time
        end_memory = process.memory_info().rss / 1024 / 1024
        memory_delta = end_memory - start_memory
        
        worker_logger.info(f"워커 {os.getpid()}: DB 처리 완료 - {file_name} ({execution_time:.3f}초, {total_processed_items:,}개 항목, 메모리 +{memory_delta:.1f}MB)")
        
        return {
            'success': True,
            'file_name': file_name,
            'execution_time': execution_time,
            'processed_items': total_processed_items,
            'sheets_processed': len(dollar_sheets),
            'worker_pid': os.getpid(),
            'memory_delta_mb': memory_delta
        }
        
    except Exception as e:
        execution_time = time.perf_counter() - start_time
        error_msg = f"워커 {os.getpid()}: DB 처리 실패 - {file_name} - {str(e)}"
        worker_logger.error(error_msg)
        
        return {
            'success': False,
            'file_name': file_name,
            'execution_time': execution_time,
            'error': str(e),
            'worker_pid': os.getpid()
        }

class DistributedDBProcessor:
    """분산 DB → C 코드 변환 프로세서"""
    
    def __init__(self, config: DistributedConfig = None):
        self.config = config or DistributedConfig()
        
        # CPU 코어 수 자동 설정
        if self.config.max_processes is None:
            self.config.max_processes = min(mp.cpu_count(), 8)  # 최대 8개 프로세스
        
        self.logger = logging.getLogger(__name__)
        self.stats = {
            'total_files_processed': 0,
            'total_items_processed': 0,
            'total_execution_time': 0,
            'worker_stats': {}
        }
    
    def process_batch_distributed(self, db_files: List[Path]) -> Dict[str, Any]:
        """분산 일괄 처리"""
        start_time = time.perf_counter()
        
        self.logger.info(f"분산 처리 시작: {len(db_files)}개 파일, {self.config.max_processes}개 프로세스")
        
        # 작업 인수 준비
        work_args = [(str(db_file), self.config) for db_file in db_files]
        
        try:
            # 프로세스 풀 생성 및 실행
            with mp.Pool(processes=self.config.max_processes) as pool:
                # 비동기 실행으로 진행 상황 모니터링 가능
                async_results = []
                
                # 작업 제출
                for args in work_args:
                    async_result = pool.apply_async(process_single_db_worker, (args,))
                    async_results.append(async_result)
                
                # 결과 수집 (타임아웃 적용)
                results = []
                for i, async_result in enumerate(async_results):
                    try:
                        result = async_result.get(timeout=self.config.worker_timeout)
                        results.append(result)
                        
                        if result['success']:
                            self.logger.info(f"작업 완료 ({i+1}/{len(async_results)}): {result['file_name']}")
                        else:
                            self.logger.error(f"작업 실패 ({i+1}/{len(async_results)}): {result['file_name']}")
                            
                    except mp.TimeoutError:
                        self.logger.error(f"작업 타임아웃 ({i+1}/{len(async_results)}): {work_args[i][0]}")
                        results.append({
                            'success': False,
                            'file_name': Path(work_args[i][0]).name,
                            'error': 'Worker timeout',
                            'execution_time': self.config.worker_timeout
                        })
                    except Exception as e:
                        self.logger.error(f"작업 예외 ({i+1}/{len(async_results)}): {e}")
                        results.append({
                            'success': False,
                            'file_name': Path(work_args[i][0]).name,
                            'error': str(e),
                            'execution_time': 0
                        })
            
            execution_time = time.perf_counter() - start_time
            
            # 통계 계산
            successful_results = [r for r in results if r['success']]
            total_processed_items = sum(r.get('processed_items', 0) for r in successful_results)
            
            # 워커별 통계
            worker_stats = {}
            for result in successful_results:
                worker_pid = result.get('worker_pid', 'unknown')
                if worker_pid not in worker_stats:
                    worker_stats[worker_pid] = {
                        'files_processed': 0,
                        'items_processed': 0,
                        'total_time': 0,
                        'memory_usage': 0
                    }
                
                worker_stats[worker_pid]['files_processed'] += 1
                worker_stats[worker_pid]['items_processed'] += result.get('processed_items', 0)
                worker_stats[worker_pid]['total_time'] += result.get('execution_time', 0)
                worker_stats[worker_pid]['memory_usage'] += result.get('memory_delta_mb', 0)
            
            self.stats['worker_stats'] = worker_stats
            
            # 통계 업데이트
            self.stats['total_files_processed'] += len(successful_results)
            self.stats['total_items_processed'] += total_processed_items
            self.stats['total_execution_time'] += execution_time
            
            self.logger.info(f"분산 처리 완료: {execution_time:.3f}초, {total_processed_items:,}개 항목")
            
            return {
                'success': True,
                'execution_time': execution_time,
                'total_processed_items': total_processed_items,
                'files_processed': len(successful_results),
                'files_failed': len(results) - len(successful_results),
                'results': results,
                'processing_mode': 'distributed',
                'processes_used': self.config.max_processes,
                'worker_stats': worker_stats
            }
            
        except Exception as e:
            execution_time = time.perf_counter() - start_time
            self.logger.error(f"분산 처리 실패: {e}")
            
            return {
                'success': False,
                'execution_time': execution_time,
                'error': str(e),
                'processing_mode': 'distributed'
            }
    
    def get_stats(self) -> Dict[str, Any]:
        """처리 통계 반환"""
        stats = dict(self.stats)
        
        # 시스템 정보 추가
        stats['system_info'] = {
            'cpu_count': mp.cpu_count(),
            'processes_used': self.config.max_processes,
            'memory_limit_per_process': self.config.memory_limit_mb
        }
        
        return stats

def main():
    """분산 처리 메인 실행 함수"""
    print("🚀 Phase 3: 분산 DB → C 코드 변환 프로세서")
    print("=" * 80)
    
    # 설정
    config = DistributedConfig(
        batch_size=500,
        chunk_size=1000,
        gc_interval=4,
        max_processes=None,  # CPU 코어 수 자동 설정
        worker_timeout=300.0,
        memory_limit_mb=512
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
    print(f"🖥️ 사용 가능 CPU: {mp.cpu_count()}개 코어")
    print(f"⚙️ 사용할 프로세스: {config.max_processes or mp.cpu_count()}개")
    
    # 분산 프로세서 생성 및 실행
    processor = DistributedDBProcessor(config)
    
    try:
        # 분산 일괄 처리 실행
        result = processor.process_batch_distributed(db_files)
        
        # 결과 출력
        print(f"\n📊 분산 처리 결과:")
        print(f"   실행 시간: {result['execution_time']:.3f}초")
        print(f"   처리 항목: {result['total_processed_items']:,}개")
        print(f"   성공 파일: {result['files_processed']}개")
        print(f"   실패 파일: {result['files_failed']}개")
        print(f"   처리 모드: {result['processing_mode']}")
        print(f"   사용 프로세스: {result['processes_used']}개")
        
        # 처리 속도 계산
        if result['execution_time'] > 0:
            items_per_second = result['total_processed_items'] / result['execution_time']
            print(f"   처리 속도: {items_per_second:,.0f} 항목/초")
        
        # 워커별 통계
        if 'worker_stats' in result:
            print(f"\n📈 워커별 통계:")
            for worker_pid, stats in result['worker_stats'].items():
                print(f"   워커 {worker_pid}: {stats['files_processed']}개 파일, {stats['items_processed']:,}개 항목")
        
        # 통계 정보
        stats = processor.get_stats()
        print(f"\n🖥️ 시스템 정보:")
        print(f"   CPU 코어: {stats['system_info']['cpu_count']}개")
        print(f"   사용 프로세스: {stats['system_info']['processes_used']}개")
        print(f"   프로세스당 메모리 제한: {stats['system_info']['memory_limit_per_process']}MB")
        
        # 결과 저장
        with open('distributed_processing_results.json', 'w', encoding='utf-8') as f:
            json.dump({
                'result': result,
                'stats': stats,
                'config': config.__dict__
            }, f, indent=2, ensure_ascii=False)
        
        print(f"\n📄 결과가 'distributed_processing_results.json'에 저장되었습니다.")
        
    except Exception as e:
        print(f"❌ 분산 처리 실패: {e}")
        logging.error(f"분산 처리 실패: {e}")
    
    print("=" * 80)

if __name__ == "__main__":
    # Windows에서 multiprocessing 사용 시 필요
    mp.set_start_method('spawn', force=True)
    main()
