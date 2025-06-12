"""
Phase 3: 캐싱 기반 DB → C 코드 변환 프로세서
Redis 캐싱을 이용한 중간 결과 캐싱 구현
"""

import time
import gc
import logging
import os
import sys
import hashlib
import pickle
from pathlib import Path
from typing import Dict, List, Any, Optional
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
class CacheConfig:
    """캐싱 설정"""
    batch_size: int = 500
    chunk_size: int = 500  # 더 작은 청크로 캐시 효율성 향상
    gc_interval: int = 4
    enable_redis_cache: bool = True
    redis_host: str = 'localhost'
    redis_port: int = 6379
    redis_db: int = 0
    cache_ttl: int = 3600  # 1시간
    enable_memory_cache: bool = True
    memory_cache_size: int = 5000  # 5배 확대
    cache_compression: bool = True
    enable_sheet_level_cache: bool = True  # 시트 단위 캐싱 추가

class MemoryCache:
    """메모리 기반 캐시 (Redis 대안)"""
    
    def __init__(self, max_size: int = 1000):
        self.cache = {}
        self.access_order = []
        self.max_size = max_size
        self.hits = 0
        self.misses = 0
        self.logger = logging.getLogger(__name__)
    
    def get(self, key: str) -> Optional[Any]:
        """캐시에서 값 가져오기"""
        if key in self.cache:
            # LRU 업데이트
            self.access_order.remove(key)
            self.access_order.append(key)
            self.hits += 1
            return self.cache[key]
        else:
            self.misses += 1
            return None
    
    def set(self, key: str, value: Any):
        """캐시에 값 저장"""
        if key in self.cache:
            # 기존 키 업데이트
            self.access_order.remove(key)
        elif len(self.cache) >= self.max_size:
            # LRU 제거
            oldest_key = self.access_order.pop(0)
            del self.cache[oldest_key]
        
        self.cache[key] = value
        self.access_order.append(key)
    
    def delete(self, key: str):
        """캐시에서 값 삭제"""
        if key in self.cache:
            del self.cache[key]
            self.access_order.remove(key)
    
    def clear(self):
        """캐시 전체 삭제"""
        self.cache.clear()
        self.access_order.clear()
        self.hits = 0
        self.misses = 0
    
    def get_stats(self) -> Dict[str, Any]:
        """캐시 통계"""
        total_requests = self.hits + self.misses
        hit_rate = (self.hits / total_requests * 100) if total_requests > 0 else 0
        
        return {
            'hits': self.hits,
            'misses': self.misses,
            'hit_rate': hit_rate,
            'cache_size': len(self.cache),
            'max_size': self.max_size
        }

class RedisCache:
    """Redis 기반 캐시"""
    
    def __init__(self, host: str = 'localhost', port: int = 6379, db: int = 0, ttl: int = 3600):
        self.host = host
        self.port = port
        self.db = db
        self.ttl = ttl
        self.redis_client = None
        self.logger = logging.getLogger(__name__)
        
        try:
            import redis
            self.redis_client = redis.Redis(host=host, port=port, db=db, decode_responses=False)
            # 연결 테스트
            self.redis_client.ping()
            self.logger.info(f"Redis 연결 성공: {host}:{port}/{db}")
        except ImportError:
            self.logger.warning("Redis 모듈이 설치되지 않았습니다. 메모리 캐시를 사용합니다.")
        except Exception as e:
            self.logger.warning(f"Redis 연결 실패: {e}. 메모리 캐시를 사용합니다.")
            self.redis_client = None
    
    def get(self, key: str) -> Optional[Any]:
        """Redis에서 값 가져오기"""
        if not self.redis_client:
            return None
        
        try:
            data = self.redis_client.get(key)
            if data:
                return pickle.loads(data)
            return None
        except Exception as e:
            self.logger.error(f"Redis GET 실패: {e}")
            return None
    
    def set(self, key: str, value: Any):
        """Redis에 값 저장"""
        if not self.redis_client:
            return
        
        try:
            data = pickle.dumps(value)
            self.redis_client.setex(key, self.ttl, data)
        except Exception as e:
            self.logger.error(f"Redis SET 실패: {e}")
    
    def delete(self, key: str):
        """Redis에서 값 삭제"""
        if not self.redis_client:
            return
        
        try:
            self.redis_client.delete(key)
        except Exception as e:
            self.logger.error(f"Redis DELETE 실패: {e}")
    
    def clear(self):
        """Redis 캐시 전체 삭제"""
        if not self.redis_client:
            return
        
        try:
            self.redis_client.flushdb()
        except Exception as e:
            self.logger.error(f"Redis CLEAR 실패: {e}")

class CachedDBProcessor:
    """캐싱 기반 DB → C 코드 변환 프로세서"""
    
    def __init__(self, config: CacheConfig = None):
        self.config = config or CacheConfig()
        self.logger = logging.getLogger(__name__)
        
        # 캐시 초기화
        self.redis_cache = None
        self.memory_cache = None
        
        if self.config.enable_redis_cache:
            self.redis_cache = RedisCache(
                host=self.config.redis_host,
                port=self.config.redis_port,
                db=self.config.redis_db,
                ttl=self.config.cache_ttl
            )
        
        if self.config.enable_memory_cache:
            self.memory_cache = MemoryCache(self.config.memory_cache_size)
        
        self.stats = {
            'total_files_processed': 0,
            'total_items_processed': 0,
            'total_execution_time': 0,
            'cache_hits': 0,
            'cache_misses': 0
        }
    
    def generate_cache_key(self, db_file: Path, sheet_id: int, chunk_start: int, chunk_end: int) -> str:
        """캐시 키 생성"""
        # 파일 수정 시간과 크기를 포함하여 캐시 무효화
        stat = db_file.stat()
        key_data = f"{db_file.name}:{sheet_id}:{chunk_start}:{chunk_end}:{stat.st_mtime}:{stat.st_size}"
        return hashlib.md5(key_data.encode()).hexdigest()

    def generate_sheet_cache_key(self, db_file: Path, sheet_id: int) -> str:
        """시트 단위 캐시 키 생성"""
        stat = db_file.stat()
        key_data = f"SHEET:{db_file.name}:{sheet_id}:{stat.st_mtime}:{stat.st_size}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def get_from_cache(self, key: str) -> Optional[Any]:
        """캐시에서 값 가져오기 (Redis -> Memory 순서)"""
        # Redis 캐시 확인
        if self.redis_cache:
            value = self.redis_cache.get(key)
            if value is not None:
                # 메모리 캐시에도 저장
                if self.memory_cache:
                    self.memory_cache.set(key, value)
                self.stats['cache_hits'] += 1
                return value
        
        # 메모리 캐시 확인
        if self.memory_cache:
            value = self.memory_cache.get(key)
            if value is not None:
                self.stats['cache_hits'] += 1
                return value
        
        self.stats['cache_misses'] += 1
        return None
    
    def set_to_cache(self, key: str, value: Any):
        """캐시에 값 저장 (Redis + Memory)"""
        if self.redis_cache:
            self.redis_cache.set(key, value)
        
        if self.memory_cache:
            self.memory_cache.set(key, value)
    
    def process_sheet_chunk_cached(self, db_handler, sheet: Dict[str, Any], 
                                 chunk_start: int, chunk_end: int, db_file: Path) -> int:
        """캐시를 활용한 시트 청크 처리"""
        # 캐시 키 생성
        cache_key = self.generate_cache_key(db_file, sheet['id'], chunk_start, chunk_end)
        
        # 캐시에서 확인
        cached_result = self.get_from_cache(cache_key)
        if cached_result is not None:
            self.logger.debug(f"캐시 히트: {sheet['name']} chunk {chunk_start}-{chunk_end}")
            return cached_result
        
        # 캐시 미스 - 실제 처리
        self.logger.debug(f"캐시 미스: {sheet['name']} chunk {chunk_start}-{chunk_end}")
        
        # 시트 데이터 조회
        sheet_data = db_handler.get_sheet_data(sheet['id'])
        if not sheet_data:
            result = 0
            self.set_to_cache(cache_key, result)
            return result
        
        # 청크 데이터 추출
        chunk_data = sheet_data[chunk_start:chunk_end]
        
        # Ultra 최적화된 Cython 모듈 사용
        from cython_extensions.code_generator_v2 import ultra_fast_write_cal_list_processing
        
        total_processed_items = 0
        
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
        
        # 결과를 캐시에 저장
        self.set_to_cache(cache_key, total_processed_items)
        
        return total_processed_items
    
    def process_single_db_cached(self, db_file: Path) -> Dict[str, Any]:
        """캐시를 활용한 단일 DB 처리"""
        start_time = time.perf_counter()
        file_name = db_file.name
        
        try:
            self.logger.info(f"캐시 기반 DB 처리 시작: {file_name}")
            
            # DB 연결
            from data_manager.db_handler_v2 import DBHandlerV2
            db_handler = DBHandlerV2(str(db_file))
            db_handler.connect()
            
            # $ 시트 찾기
            sheets = db_handler.get_sheets()
            dollar_sheets = [s for s in sheets if s.get('is_dollar_sheet', False)]
            
            if not dollar_sheets:
                self.logger.warning(f"$ 시트가 없음: {file_name}")
                db_handler.disconnect()
                return {
                    'success': True,
                    'file_name': file_name,
                    'execution_time': time.perf_counter() - start_time,
                    'processed_items': 0,
                    'warning': 'No dollar sheets found'
                }
            
            total_processed_items = 0
            
            # 시트별 처리
            for sheet in dollar_sheets:
                sheet_data = db_handler.get_sheet_data(sheet['id'])
                if not sheet_data:
                    continue
                
                self.logger.debug(f"캐시 기반 시트 처리: {sheet['name']} ({len(sheet_data)}개 셀)")
                
                # 청크 단위로 캐시 활용 처리
                for chunk_start in range(0, len(sheet_data), self.config.chunk_size):
                    chunk_end = min(chunk_start + self.config.chunk_size, len(sheet_data))
                    
                    chunk_result = self.process_sheet_chunk_cached(
                        db_handler, sheet, chunk_start, chunk_end, db_file
                    )
                    total_processed_items += chunk_result
            
            # DB 연결 해제
            db_handler.disconnect()
            
            execution_time = time.perf_counter() - start_time
            
            self.logger.info(f"캐시 기반 DB 처리 완료: {file_name} ({execution_time:.3f}초, {total_processed_items:,}개 항목)")
            
            return {
                'success': True,
                'file_name': file_name,
                'execution_time': execution_time,
                'processed_items': total_processed_items,
                'sheets_processed': len(dollar_sheets)
            }
            
        except Exception as e:
            execution_time = time.perf_counter() - start_time
            error_msg = f"캐시 기반 DB 처리 실패: {file_name} - {str(e)}"
            self.logger.error(error_msg)
            
            return {
                'success': False,
                'file_name': file_name,
                'execution_time': execution_time,
                'error': str(e)
            }
    
    def process_batch_cached(self, db_files: List[Path]) -> Dict[str, Any]:
        """캐시를 활용한 일괄 처리"""
        start_time = time.perf_counter()
        
        self.logger.info(f"캐시 기반 일괄 처리 시작: {len(db_files)}개 파일")
        
        results = []
        for db_file in db_files:
            result = self.process_single_db_cached(db_file)
            results.append(result)
        
        execution_time = time.perf_counter() - start_time
        
        # 통계 계산
        successful_results = [r for r in results if r['success']]
        total_processed_items = sum(r.get('processed_items', 0) for r in successful_results)
        
        # 통계 업데이트
        self.stats['total_files_processed'] += len(successful_results)
        self.stats['total_items_processed'] += total_processed_items
        self.stats['total_execution_time'] += execution_time
        
        self.logger.info(f"캐시 기반 일괄 처리 완료: {execution_time:.3f}초, {total_processed_items:,}개 항목")
        
        return {
            'success': True,
            'execution_time': execution_time,
            'total_processed_items': total_processed_items,
            'files_processed': len(successful_results),
            'files_failed': len(results) - len(successful_results),
            'results': results,
            'processing_mode': 'cached'
        }
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """캐시 통계 반환"""
        cache_stats = {}
        
        if self.memory_cache:
            cache_stats['memory_cache'] = self.memory_cache.get_stats()
        
        if self.redis_cache and self.redis_cache.redis_client:
            try:
                info = self.redis_cache.redis_client.info()
                cache_stats['redis_cache'] = {
                    'connected_clients': info.get('connected_clients', 0),
                    'used_memory': info.get('used_memory', 0),
                    'keyspace_hits': info.get('keyspace_hits', 0),
                    'keyspace_misses': info.get('keyspace_misses', 0)
                }
            except:
                cache_stats['redis_cache'] = {'status': 'unavailable'}
        
        cache_stats['total_hits'] = self.stats['cache_hits']
        cache_stats['total_misses'] = self.stats['cache_misses']
        
        total_requests = self.stats['cache_hits'] + self.stats['cache_misses']
        if total_requests > 0:
            cache_stats['hit_rate'] = (self.stats['cache_hits'] / total_requests) * 100
        else:
            cache_stats['hit_rate'] = 0
        
        return cache_stats
    
    def cleanup(self):
        """리소스 정리"""
        self.logger.info("캐시 리소스 정리 시작")
        
        if self.memory_cache:
            self.memory_cache.clear()
        
        gc.collect()
        self.logger.info("캐시 리소스 정리 완료")

def main():
    """캐시 기반 메인 실행 함수"""
    print("🚀 Phase 3: 캐싱 기반 DB → C 코드 변환 프로세서")
    print("=" * 80)
    
    # 설정
    config = CacheConfig(
        batch_size=500,
        chunk_size=1000,
        gc_interval=4,
        enable_redis_cache=True,
        enable_memory_cache=True,
        memory_cache_size=1000,
        cache_ttl=3600
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
    
    # 캐시 기반 프로세서 생성 및 실행
    processor = CachedDBProcessor(config)
    
    try:
        # 첫 번째 실행 (캐시 미스)
        print("\n🔄 첫 번째 실행 (캐시 구축)")
        result1 = processor.process_batch_cached(db_files)
        
        # 두 번째 실행 (캐시 히트)
        print("\n🔄 두 번째 실행 (캐시 활용)")
        result2 = processor.process_batch_cached(db_files)
        
        # 결과 비교
        print(f"\n📊 캐시 효과 비교:")
        print(f"   첫 번째 실행: {result1['execution_time']:.3f}초")
        print(f"   두 번째 실행: {result2['execution_time']:.3f}초")
        
        if result1['execution_time'] > 0:
            speedup = result1['execution_time'] / result2['execution_time']
            improvement = (1 - result2['execution_time'] / result1['execution_time']) * 100
            print(f"   캐시 효과: {speedup:.2f}배 빠름 ({improvement:.1f}% 개선)")
        
        # 캐시 통계
        cache_stats = processor.get_cache_stats()
        print(f"\n📈 캐시 통계:")
        print(f"   캐시 히트율: {cache_stats['hit_rate']:.1f}%")
        print(f"   총 히트: {cache_stats['total_hits']:,}회")
        print(f"   총 미스: {cache_stats['total_misses']:,}회")
        
        if 'memory_cache' in cache_stats:
            mem_stats = cache_stats['memory_cache']
            print(f"   메모리 캐시: {mem_stats['cache_size']}/{mem_stats['max_size']} 항목")
        
        # 결과 저장
        with open('cached_processing_results.json', 'w', encoding='utf-8') as f:
            json.dump({
                'first_run': result1,
                'second_run': result2,
                'cache_stats': cache_stats,
                'config': config.__dict__
            }, f, indent=2, ensure_ascii=False)
        
        print(f"\n📄 결과가 'cached_processing_results.json'에 저장되었습니다.")
        
    except Exception as e:
        print(f"❌ 캐시 기반 처리 실패: {e}")
        logging.error(f"캐시 기반 처리 실패: {e}")
    
    finally:
        processor.cleanup()
    
    print("=" * 80)

if __name__ == "__main__":
    main()
