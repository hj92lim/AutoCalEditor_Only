"""
UI 시스템과 Phase 3 백엔드 최적화 통합 전략
기존 GUI를 유지하면서 백엔드 성능을 향상시키는 방안
"""

import sys
import time
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

# 프로젝트 루트 경로 설정
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

@dataclass
class IntegrationConfig:
    """통합 설정"""
    enable_async_processing: bool = True
    enable_distributed_processing: bool = True
    enable_caching: bool = True
    auto_optimization: bool = True
    ui_progress_updates: bool = True
    background_processing: bool = True

class Phase3BackendIntegrator:
    """Phase 3 백엔드 최적화를 UI 시스템에 통합하는 클래스"""
    
    def __init__(self, config: IntegrationConfig = None):
        self.config = config or IntegrationConfig()
        self.logger = logging.getLogger(__name__)
        
        # Phase 3 프로세서들 초기화
        self._async_processor = None
        self._distributed_processor = None
        self._cached_processor = None
        
    def initialize_processors(self):
        """Phase 3 프로세서들 초기화"""
        try:
            if self.config.enable_async_processing:
                from async_db_processor import AsyncDBProcessor, AsyncConfig
                async_config = AsyncConfig(
                    batch_size=500,
                    chunk_size=1000,
                    max_concurrent_dbs=8,
                    max_concurrent_sheets=16
                )
                self._async_processor = AsyncDBProcessor(async_config)
                self.logger.info("✅ 비동기 프로세서 초기화 완료")
            
            if self.config.enable_distributed_processing:
                from distributed_db_processor import DistributedDBProcessor, DistributedConfig
                distributed_config = DistributedConfig(
                    batch_size=500,
                    chunk_size=1000,
                    max_processes=4,
                    worker_timeout=300.0,
                    memory_limit_mb=512
                )
                self._distributed_processor = DistributedDBProcessor(distributed_config)
                self.logger.info("✅ 분산 프로세서 초기화 완료")
            
            if self.config.enable_caching:
                from cached_db_processor import CachedDBProcessor, CacheConfig
                cache_config = CacheConfig(
                    batch_size=500,
                    chunk_size=500,
                    enable_memory_cache=True,
                    memory_cache_size=5000,
                    enable_redis_cache=False  # UI 환경에서는 메모리 캐시만 사용
                )
                self._cached_processor = CachedDBProcessor(cache_config)
                self.logger.info("✅ 캐싱 프로세서 초기화 완료")
                
        except Exception as e:
            self.logger.error(f"Phase 3 프로세서 초기화 실패: {e}")
            raise
    
    def choose_optimal_processor(self, db_files: List[Path]) -> str:
        """상황별 최적 프로세서 선택 (UI 환경 고려)"""
        if not db_files:
            return "none"
        
        file_count = len(db_files)
        total_size = sum(f.stat().st_size for f in db_files if f.exists())
        avg_size = total_size / file_count if file_count > 0 else 0
        
        # UI 환경에서는 안정성을 우선시
        if file_count >= 4 and avg_size > 500000:  # 500KB 이상의 큰 파일들
            if self.config.enable_async_processing and self._async_processor:
                return "async"
            elif self.config.enable_distributed_processing and self._distributed_processor:
                return "distributed"
        elif file_count >= 2:
            if self.config.enable_caching and self._cached_processor:
                return "cached"
        
        return "sequential"  # 기본 처리
    
    async def process_db_files_optimized(self, db_files: List[Path], 
                                       progress_callback=None) -> Dict[str, Any]:
        """최적화된 DB 파일 처리 (UI 진행률 콜백 지원)"""
        if not db_files:
            return {'success': False, 'error': 'No DB files provided'}
        
        # 최적 프로세서 선택
        processor_type = self.choose_optimal_processor(db_files)
        
        if progress_callback:
            progress_callback(0, f"처리 모드 선택: {processor_type}")
        
        try:
            if processor_type == "async" and self._async_processor:
                result = await self._async_processor.process_batch_async(db_files)
                result['processor_type'] = 'async'
                
            elif processor_type == "distributed" and self._distributed_processor:
                if progress_callback:
                    progress_callback(10, "분산 처리 시작...")
                result = self._distributed_processor.process_batch_distributed(db_files)
                result['processor_type'] = 'distributed'
                
            elif processor_type == "cached" and self._cached_processor:
                if progress_callback:
                    progress_callback(10, "캐시 처리 시작...")
                result = self._cached_processor.process_batch_cached(db_files)
                result['processor_type'] = 'cached'
                
            else:
                # 기본 순차 처리
                if progress_callback:
                    progress_callback(10, "순차 처리 시작...")
                result = await self._process_sequential(db_files, progress_callback)
                result['processor_type'] = 'sequential'
            
            if progress_callback:
                progress_callback(100, "처리 완료")
            
            return result
            
        except Exception as e:
            self.logger.error(f"DB 파일 처리 실패: {e}")
            return {
                'success': False,
                'error': str(e),
                'processor_type': processor_type
            }
    
    async def _process_sequential(self, db_files: List[Path], 
                                progress_callback=None) -> Dict[str, Any]:
        """기본 순차 처리 (UI 진행률 지원)"""
        from production_ready_db_processor import ProductionDBProcessor, ProductionConfig
        
        config = ProductionConfig(
            batch_size=500,
            chunk_size=1000,
            enable_parallel_processing=False
        )
        
        processor = ProductionDBProcessor(config)
        
        try:
            # 진행률 업데이트를 위한 래퍼
            if progress_callback:
                total_files = len(db_files)
                for i, db_file in enumerate(db_files):
                    progress = 20 + (i * 60 // total_files)
                    progress_callback(progress, f"처리 중: {db_file.name}")
            
            result = processor.process_batch_production(db_files)
            return result
            
        finally:
            processor.cleanup()
    
    def cleanup(self):
        """리소스 정리"""
        try:
            if self._async_processor:
                # 비동기 프로세서는 별도 정리 필요
                import asyncio
                if asyncio.get_event_loop().is_running():
                    asyncio.create_task(self._async_processor.cleanup())
                else:
                    asyncio.run(self._async_processor.cleanup())
            
            if self._cached_processor:
                self._cached_processor.cleanup()
                
            # 분산 프로세서는 자동 정리됨
            
            self.logger.info("Phase 3 백엔드 통합 리소스 정리 완료")
            
        except Exception as e:
            self.logger.error(f"리소스 정리 실패: {e}")

class UIProgressHandler:
    """UI 진행률 처리 헬퍼 클래스"""
    
    def __init__(self, progress_bar=None, status_label=None):
        self.progress_bar = progress_bar
        self.status_label = status_label
    
    def update_progress(self, percentage: int, message: str = ""):
        """진행률 업데이트"""
        if self.progress_bar:
            self.progress_bar.setValue(percentage)
        
        if self.status_label and message:
            self.status_label.setText(message)
    
    def __call__(self, percentage: int, message: str = ""):
        """콜백으로 사용할 수 있도록 호출 가능하게 만듦"""
        self.update_progress(percentage, message)

# UI 통합을 위한 헬퍼 함수들
def integrate_phase3_to_ui_method(ui_class, method_name: str):
    """
    기존 UI 클래스의 메서드에 Phase 3 최적화를 통합하는 데코레이터
    
    사용 예:
    @integrate_phase3_to_ui_method(DBExcelEditor, 'process_excel_files')
    def optimized_process_excel_files(self, files):
        # Phase 3 최적화가 적용된 처리
        pass
    """
    def decorator(optimized_func):
        # 원본 메서드 백업
        original_method = getattr(ui_class, method_name, None)
        if original_method:
            setattr(ui_class, f'_original_{method_name}', original_method)
        
        # 최적화된 메서드로 교체
        setattr(ui_class, method_name, optimized_func)
        
        return optimized_func
    
    return decorator

def create_background_processor():
    """백그라운드 처리용 Phase 3 통합 프로세서 생성"""
    config = IntegrationConfig(
        enable_async_processing=True,
        enable_distributed_processing=True,
        enable_caching=True,
        auto_optimization=True,
        ui_progress_updates=True,
        background_processing=True
    )

    integrator = Phase3BackendIntegrator(config)
    integrator.initialize_processors()

    return integrator

def inject_phase3_into_existing_class(target_class):
    """기존 클래스에 Phase 3 기능을 주입하는 함수"""

    # Phase 3 초기화 메서드 추가
    def init_phase3_backend(self):
        """Phase 3 백엔드 초기화"""
        try:
            self.phase3_backend = create_background_processor()
            self.phase3_enabled = True
            logging.info("✅ Phase 3 백엔드 초기화 완료")
        except Exception as e:
            self.phase3_backend = None
            self.phase3_enabled = False
            logging.warning(f"⚠️ Phase 3 백엔드 초기화 실패: {e}")

    # Phase 3 처리 메서드 추가
    async def process_with_phase3_optimization(self, db_files):
        """Phase 3 최적화된 처리"""
        if not hasattr(self, 'phase3_backend') or not self.phase3_backend:
            return None

        try:
            result = await self.phase3_backend.process_db_files_optimized(db_files)
            return result
        except Exception as e:
            logging.error(f"Phase 3 처리 실패: {e}")
            return None

    # 기존 메서드 확장을 위한 헬퍼 메서드
    def enhance_existing_method(self, method_name, enhancement_func):
        """기존 메서드를 Phase 3 최적화로 확장"""
        if hasattr(self, method_name):
            original_method = getattr(self, method_name)

            def enhanced_method(*args, **kwargs):
                # 기존 메서드 실행
                original_result = original_method(*args, **kwargs)

                # Phase 3 최적화 적용
                if hasattr(self, 'phase3_enabled') and self.phase3_enabled:
                    try:
                        enhanced_result = enhancement_func(self, original_result, *args, **kwargs)
                        return enhanced_result if enhanced_result is not None else original_result
                    except Exception as e:
                        logging.warning(f"Phase 3 확장 실패, 기존 결과 반환: {e}")
                        return original_result

                return original_result

            setattr(self, method_name, enhanced_method)

    # 기존 클래스에 메서드 추가
    target_class.init_phase3_backend = init_phase3_backend
    target_class.process_with_phase3_optimization = process_with_phase3_optimization

    # 기존 __init__ 메서드 확장
    original_init = target_class.__init__

    def enhanced_init(self, *args, **kwargs):
        # 기존 초기화 실행
        original_init(self, *args, **kwargs)

        # Phase 3 백엔드 초기화 추가
        try:
            self.init_phase3_backend()
        except Exception as e:
            logging.warning(f"Phase 3 백엔드 초기화 건너뛰기: {e}")

    target_class.__init__ = enhanced_init

    return target_class

# 사용 예시
def example_ui_integration():
    """UI 통합 사용 예시"""
    
    # 1. 백그라운드 프로세서 생성
    backend_processor = create_background_processor()
    
    # 2. UI 진행률 핸들러 생성 (실제 UI 위젯과 연결)
    # progress_handler = UIProgressHandler(progress_bar, status_label)
    
    # 3. DB 파일 처리 (비동기)
    # result = await backend_processor.process_db_files_optimized(
    #     db_files, progress_callback=progress_handler
    # )
    
    # 4. 결과 처리
    # if result['success']:
    #     print(f"처리 완료: {result['processor_type']} 모드")
    # else:
    #     print(f"처리 실패: {result['error']}")
    
    # 5. 정리
    # backend_processor.cleanup()
    
    pass

if __name__ == "__main__":
    # 통합 전략 테스트
    print("🔧 UI-백엔드 통합 전략 모듈")
    print("   Phase 3 최적화를 기존 UI에 통합하는 방안 제공")
    
    # 설정 예시
    config = IntegrationConfig(
        enable_async_processing=True,
        enable_distributed_processing=True,
        enable_caching=True,
        auto_optimization=True
    )
    
    print(f"   설정: {config}")
    print("   사용법: create_background_processor() 함수 활용")
