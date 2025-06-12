"""
Phase 3: 통합 DB → C 코드 변환 프로세서
비동기 + 분산 + 캐싱을 모두 통합한 최고 성능 프로세서
"""

import asyncio
import multiprocessing as mp
import time
import gc
import logging
import os
import sys
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
class Phase3Config:
    """Phase 3 통합 설정"""
    # 기본 설정
    batch_size: int = 500
    chunk_size: int = 1000
    gc_interval: int = 4
    
    # 비동기 설정
    enable_async: bool = True
    max_concurrent_dbs: int = 8
    max_concurrent_sheets: int = 16
    
    # 분산 처리 설정
    enable_distributed: bool = True
    max_processes: int = None  # None이면 CPU 코어 수
    worker_timeout: float = 300.0
    
    # 캐싱 설정
    enable_caching: bool = True
    enable_redis_cache: bool = False  # Redis 없이도 작동
    enable_memory_cache: bool = True
    memory_cache_size: int = 1000
    
    # 하이브리드 모드 설정
    hybrid_threshold: int = 2  # 파일 수가 이 값 이상이면 분산 처리
    async_threshold: int = 4   # 시트 수가 이 값 이상이면 비동기 처리

class Phase3IntegratedProcessor:
    """Phase 3 통합 프로세서"""
    
    def __init__(self, config: Phase3Config = None):
        self.config = config or Phase3Config()
        
        # CPU 코어 수 자동 설정
        if self.config.max_processes is None:
            self.config.max_processes = min(mp.cpu_count(), 8)
        
        self.logger = logging.getLogger(__name__)
        
        # 캐시 초기화
        self.memory_cache = None
        if self.config.enable_caching and self.config.enable_memory_cache:
            from cached_db_processor import MemoryCache
            self.memory_cache = MemoryCache(self.config.memory_cache_size)
        
        self.stats = {
            'total_files_processed': 0,
            'total_items_processed': 0,
            'total_execution_time': 0,
            'processing_modes_used': [],
            'cache_hits': 0,
            'cache_misses': 0
        }
    
    def choose_processing_mode(self, db_files: List[Path]) -> str:
        """최적의 처리 모드 선택"""
        file_count = len(db_files)
        
        # 파일 크기 분석
        total_size = sum(f.stat().st_size for f in db_files)
        avg_size = total_size / file_count if file_count > 0 else 0
        
        # 처리 모드 결정 로직
        if file_count >= self.config.hybrid_threshold and self.config.enable_distributed:
            if avg_size > 500000:  # 500KB 이상의 큰 파일들
                return "distributed_async"  # 분산 + 비동기
            else:
                return "distributed"  # 분산 처리
        elif file_count >= 2 and self.config.enable_async:
            return "async"  # 비동기 처리
        else:
            return "sequential"  # 순차 처리
    
    async def process_with_async_cache(self, db_files: List[Path]) -> Dict[str, Any]:
        """비동기 + 캐싱 처리"""
        from async_db_processor import AsyncDBProcessor, AsyncConfig
        
        async_config = AsyncConfig(
            batch_size=self.config.batch_size,
            chunk_size=self.config.chunk_size,
            max_concurrent_dbs=self.config.max_concurrent_dbs,
            max_concurrent_sheets=self.config.max_concurrent_sheets
        )
        
        processor = AsyncDBProcessor(async_config)
        
        try:
            result = await processor.process_batch_async(db_files)
            result['processing_mode'] = 'async_cached'
            return result
        finally:
            await processor.cleanup()
    
    def process_with_distributed_cache(self, db_files: List[Path]) -> Dict[str, Any]:
        """분산 + 캐싱 처리"""
        from distributed_db_processor import DistributedDBProcessor, DistributedConfig
        
        dist_config = DistributedConfig(
            batch_size=self.config.batch_size,
            chunk_size=self.config.chunk_size,
            max_processes=self.config.max_processes,
            worker_timeout=self.config.worker_timeout
        )
        
        processor = DistributedDBProcessor(dist_config)
        result = processor.process_batch_distributed(db_files)
        result['processing_mode'] = 'distributed_cached'
        return result
    
    def process_with_sequential_cache(self, db_files: List[Path]) -> Dict[str, Any]:
        """순차 + 캐싱 처리"""
        from cached_db_processor import CachedDBProcessor, CacheConfig
        
        cache_config = CacheConfig(
            batch_size=self.config.batch_size,
            chunk_size=self.config.chunk_size,
            enable_memory_cache=self.config.enable_memory_cache,
            memory_cache_size=self.config.memory_cache_size
        )
        
        processor = CachedDBProcessor(cache_config)
        
        try:
            result = processor.process_batch_cached(db_files)
            result['processing_mode'] = 'sequential_cached'
            return result
        finally:
            processor.cleanup()
    
    async def process_hybrid_mode(self, db_files: List[Path]) -> Dict[str, Any]:
        """하이브리드 모드: 분산 + 비동기 + 캐싱"""
        self.logger.info("하이브리드 모드 실행: 분산 + 비동기 + 캐싱")
        
        # 파일들을 크기별로 그룹화
        small_files = [f for f in db_files if f.stat().st_size < 200000]  # 200KB 미만
        large_files = [f for f in db_files if f.stat().st_size >= 200000]  # 200KB 이상
        
        results = []
        total_start_time = time.perf_counter()
        
        # 큰 파일들은 분산 처리
        if large_files:
            self.logger.info(f"큰 파일 {len(large_files)}개를 분산 처리")
            dist_result = self.process_with_distributed_cache(large_files)
            results.extend(dist_result['results'])
        
        # 작은 파일들은 비동기 처리
        if small_files:
            self.logger.info(f"작은 파일 {len(small_files)}개를 비동기 처리")
            async_result = await self.process_with_async_cache(small_files)
            results.extend(async_result['results'])
        
        total_execution_time = time.perf_counter() - total_start_time
        
        # 결과 통합
        successful_results = [r for r in results if r['success']]
        total_processed_items = sum(r.get('processed_items', 0) for r in successful_results)
        
        return {
            'success': True,
            'execution_time': total_execution_time,
            'total_processed_items': total_processed_items,
            'files_processed': len(successful_results),
            'files_failed': len(results) - len(successful_results),
            'results': results,
            'processing_mode': 'hybrid',
            'large_files_count': len(large_files),
            'small_files_count': len(small_files)
        }
    
    async def process_batch_phase3(self, db_files: List[Path]) -> Dict[str, Any]:
        """Phase 3 통합 일괄 처리"""
        start_time = time.perf_counter()
        
        # 최적 처리 모드 선택
        processing_mode = self.choose_processing_mode(db_files)
        self.logger.info(f"선택된 처리 모드: {processing_mode}")
        
        self.stats['processing_modes_used'].append(processing_mode)
        
        # 처리 모드에 따른 실행
        if processing_mode == "distributed_async":
            result = await self.process_hybrid_mode(db_files)
        elif processing_mode == "distributed":
            result = self.process_with_distributed_cache(db_files)
        elif processing_mode == "async":
            result = await self.process_with_async_cache(db_files)
        else:  # sequential
            result = self.process_with_sequential_cache(db_files)
        
        # 통계 업데이트
        if result['success']:
            self.stats['total_files_processed'] += result['files_processed']
            self.stats['total_items_processed'] += result['total_processed_items']
            self.stats['total_execution_time'] += result['execution_time']
        
        return result
    
    def benchmark_all_modes(self, db_files: List[Path]) -> Dict[str, Any]:
        """모든 처리 모드 벤치마크"""
        self.logger.info("모든 Phase 3 처리 모드 벤치마크 시작")
        
        benchmark_results = {}
        
        # 1. 순차 + 캐싱
        try:
            self.logger.info("1. 순차 + 캐싱 모드 테스트")
            sequential_result = self.process_with_sequential_cache(db_files)
            benchmark_results['sequential_cached'] = sequential_result
        except Exception as e:
            self.logger.error(f"순차 + 캐싱 모드 실패: {e}")
            benchmark_results['sequential_cached'] = {'success': False, 'error': str(e)}
        
        # 2. 분산 + 캐싱
        try:
            self.logger.info("2. 분산 + 캐싱 모드 테스트")
            distributed_result = self.process_with_distributed_cache(db_files)
            benchmark_results['distributed_cached'] = distributed_result
        except Exception as e:
            self.logger.error(f"분산 + 캐싱 모드 실패: {e}")
            benchmark_results['distributed_cached'] = {'success': False, 'error': str(e)}
        
        # 3. 비동기 + 캐싱
        try:
            self.logger.info("3. 비동기 + 캐싱 모드 테스트")
            async_result = asyncio.run(self.process_with_async_cache(db_files))
            benchmark_results['async_cached'] = async_result
        except Exception as e:
            self.logger.error(f"비동기 + 캐싱 모드 실패: {e}")
            benchmark_results['async_cached'] = {'success': False, 'error': str(e)}
        
        # 4. 하이브리드 모드
        try:
            self.logger.info("4. 하이브리드 모드 테스트")
            hybrid_result = asyncio.run(self.process_hybrid_mode(db_files))
            benchmark_results['hybrid'] = hybrid_result
        except Exception as e:
            self.logger.error(f"하이브리드 모드 실패: {e}")
            benchmark_results['hybrid'] = {'success': False, 'error': str(e)}
        
        return benchmark_results
    
    def get_stats(self) -> Dict[str, Any]:
        """통계 반환"""
        stats = dict(self.stats)
        
        # 시스템 정보 추가
        stats['system_info'] = {
            'cpu_count': mp.cpu_count(),
            'max_processes': self.config.max_processes,
            'async_enabled': self.config.enable_async,
            'distributed_enabled': self.config.enable_distributed,
            'caching_enabled': self.config.enable_caching
        }
        
        return stats

async def main():
    """Phase 3 통합 메인 실행 함수"""
    print("🚀 Phase 3: 통합 DB → C 코드 변환 프로세서")
    print("   (비동기 + 분산 + 캐싱 통합)")
    print("=" * 80)
    
    # 설정
    config = Phase3Config(
        batch_size=500,
        chunk_size=1000,
        gc_interval=4,
        enable_async=True,
        enable_distributed=True,
        enable_caching=True,
        max_concurrent_dbs=8,
        max_concurrent_sheets=16,
        hybrid_threshold=2,
        async_threshold=4
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
    
    # Phase 3 통합 프로세서 생성
    processor = Phase3IntegratedProcessor(config)
    
    try:
        # 모든 모드 벤치마크
        benchmark_results = processor.benchmark_all_modes(db_files)
        
        # 결과 분석 및 출력
        print(f"\n📊 Phase 3 모든 모드 벤치마크 결과:")
        print("=" * 60)
        
        mode_times = {}
        baseline_time = None
        
        for mode, result in benchmark_results.items():
            if result.get('success', False):
                exec_time = result['execution_time']
                items = result['total_processed_items']
                mode_times[mode] = exec_time
                
                if mode == 'sequential_cached':
                    baseline_time = exec_time
                
                print(f"{mode:20s}: {exec_time:.3f}초 ({items:,}개 항목)")
            else:
                print(f"{mode:20s}: 실패 - {result.get('error', 'Unknown error')}")
        
        # 성능 비교
        if baseline_time and mode_times:
            print(f"\n📈 성능 비교 (순차 캐싱 기준):")
            print("-" * 40)
            
            for mode, exec_time in mode_times.items():
                if mode != 'sequential_cached':
                    speedup = baseline_time / exec_time if exec_time > 0 else 0
                    improvement = (1 - exec_time / baseline_time) * 100 if baseline_time > 0 else 0
                    print(f"{mode:20s}: {speedup:.2f}배 빠름 ({improvement:+.1f}%)")
        
        # 최고 성능 모드 식별
        if mode_times:
            best_mode = min(mode_times.keys(), key=lambda k: mode_times[k])
            best_time = mode_times[best_mode]
            print(f"\n🏆 최고 성능 모드: {best_mode} ({best_time:.3f}초)")
        
        # 통계 정보
        stats = processor.get_stats()
        print(f"\n🖥️ 시스템 정보:")
        print(f"   CPU 코어: {stats['system_info']['cpu_count']}개")
        print(f"   비동기 처리: {'✅' if stats['system_info']['async_enabled'] else '❌'}")
        print(f"   분산 처리: {'✅' if stats['system_info']['distributed_enabled'] else '❌'}")
        print(f"   캐싱 시스템: {'✅' if stats['system_info']['caching_enabled'] else '❌'}")
        
        # 결과 저장
        with open('phase3_integrated_results.json', 'w', encoding='utf-8') as f:
            json.dump({
                'benchmark_results': benchmark_results,
                'stats': stats,
                'config': config.__dict__
            }, f, indent=2, ensure_ascii=False)
        
        print(f"\n📄 결과가 'phase3_integrated_results.json'에 저장되었습니다.")
        
    except Exception as e:
        print(f"❌ Phase 3 통합 처리 실패: {e}")
        logging.error(f"Phase 3 통합 처리 실패: {e}")
    
    print("=" * 80)

if __name__ == "__main__":
    # Windows에서 multiprocessing 사용 시 필요
    mp.set_start_method('spawn', force=True)
    
    # 필요한 모듈 설치 확인
    missing_modules = []
    
    try:
        import aiosqlite
    except ImportError:
        missing_modules.append("aiosqlite")
    
    if missing_modules:
        print(f"❌ 필요한 모듈이 설치되지 않았습니다: {', '.join(missing_modules)}")
        print("설치 명령:")
        for module in missing_modules:
            print(f"  pip install {module}")
        sys.exit(1)
    
    asyncio.run(main())
