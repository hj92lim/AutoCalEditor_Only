"""
코드 생성 과정의 공통 기능 통합 관리 클래스
중복 코드 제거 및 Single Source of Truth 원칙 적용
"""

import time
import logging
import traceback
from typing import Optional, Callable, Any
from PySide6.QtWidgets import QApplication
from core.constants import PerformanceConstants


class ProgressManager:
    """진행률 관리 통합 클래스 - 중복 제거"""
    
    def __init__(self):
        self.last_update_time = 0
        self.update_interval = 0.1  # 100ms 간격으로 업데이트
    
    def update_progress(self, progress_callback: Optional[Callable], 
                       current: int, total: int, start_time: float, 
                       message: str = "", progress_weight: int = 100) -> None:
        """통합된 진행률 업데이트"""
        if not progress_callback:
            return
        
        # 업데이트 빈도 제한 (성능 최적화)
        now = time.time()
        if now - self.last_update_time < self.update_interval:
            return
        
        progress = int((current / total) * progress_weight) if total > 0 else 0
        elapsed = now - start_time
        
        if not message:
            message = f"처리 중: {current+1}/{total} - {elapsed:.1f}초 경과"
        
        try:
            progress_callback(progress, message)
            self.last_update_time = now
        except InterruptedError as e:
            logging.info(f"사용자가 작업을 취소했습니다: {str(e)}")
            raise


class ResourceMonitor:
    """리소스 모니터링 통합 클래스 - 중복 제거"""
    
    def __init__(self):
        self._memory_monitoring = self._setup_memory_monitoring()
        self._process = None
        self._last_memory_check = 0
        self._cached_memory = 0.0
        self.memory_check_interval = 1.0  # 1초 간격
    
    def _setup_memory_monitoring(self) -> bool:
        """메모리 모니터링 설정"""
        try:
            import psutil
            self._process = psutil.Process()
            return True
        except ImportError:
            logging.warning("psutil 모듈이 설치되지 않아 메모리 모니터링을 사용할 수 없습니다.")
            return False
    
    def get_memory_usage(self) -> float:
        """현재 메모리 사용량 반환 (MB) - 캐싱 적용"""
        if not self._memory_monitoring:
            return 0.0
        
        now = time.time()
        if now - self._last_memory_check < self.memory_check_interval:
            return self._cached_memory
        
        try:
            self._cached_memory = self._process.memory_info().rss / 1024 / 1024
            self._last_memory_check = now
            return self._cached_memory
        except Exception:
            return 0.0
    
    def check_memory_limit(self, limit_mb: int = 2048) -> None:
        """메모리 제한 체크"""
        current_memory = self.get_memory_usage()
        if current_memory > limit_mb:
            logging.warning(f"메모리 사용량 초과: {current_memory:.1f}MB")
            raise MemoryError(f"메모리 사용량이 {limit_mb}MB를 초과했습니다. 현재: {current_memory:.1f}MB")
    
    def check_timeout(self, start_time: float, timeout_seconds: int, 
                     context: str = "", current_progress: str = "") -> None:
        """타임아웃 체크"""
        elapsed_time = time.time() - start_time
        if elapsed_time > timeout_seconds:
            logging.warning(f"{context} 타임아웃: {elapsed_time:.1f}초 경과")
            raise TimeoutError(f"{context}이(가) {timeout_seconds}초를 초과했습니다. {current_progress}")


class UIManager:
    """UI 응답성 관리 통합 클래스 - 중복 제거"""
    
    def __init__(self):
        self.last_ui_update = 0
        self.ui_update_interval = 0.05  # 50ms 간격
    
    def process_events_if_needed(self) -> None:
        """필요한 경우에만 UI 이벤트 처리 - 성능 최적화"""
        now = time.time()
        if now - self.last_ui_update >= self.ui_update_interval:
            QApplication.processEvents()
            self.last_ui_update = now


class ExceptionHandler:
    """예외 처리 통합 클래스 - 중복 제거"""
    
    @staticmethod
    def handle_interrupted_error(e: InterruptedError, context: str) -> None:
        """InterruptedError 통합 처리"""
        logging.info(f"{context} 중 사용자가 취소함: {str(e)}")
        raise
    
    @staticmethod
    def handle_general_exception(e: Exception, context: str) -> None:
        """일반 예외 통합 처리"""
        error_msg = f"{context} 중 오류: {str(e)}"
        logging.error(error_msg)
        logging.error(traceback.format_exc())
        raise
    
    @staticmethod
    def log_completion(context: str, start_time: float, 
                      memory_monitor: Optional[ResourceMonitor] = None,
                      initial_memory: float = 0.0) -> None:
        """완료 로그 통합 처리"""
        elapsed_time = time.time() - start_time
        
        if memory_monitor and memory_monitor._memory_monitoring:
            final_memory = memory_monitor.get_memory_usage()
            memory_used = final_memory - initial_memory
            logging.info(f"{context} 완료 (소요시간: {elapsed_time:.1f}초, 메모리 사용량: {memory_used:.1f}MB)")
        else:
            logging.info(f"{context} 완료 (소요시간: {elapsed_time:.1f}초)")


class ProcessingPipeline:
    """코드 생성 파이프라인 통합 관리 클래스"""
    
    def __init__(self):
        self.progress_manager = ProgressManager()
        self.resource_monitor = ResourceMonitor()
        self.ui_manager = UIManager()
        self.exception_handler = ExceptionHandler()
    
    def execute_with_monitoring(self, 
                               func: Callable,
                               context: str,
                               progress_callback: Optional[Callable] = None,
                               timeout_seconds: int = PerformanceConstants.CODE_GENERATION_TIMEOUT,
                               memory_limit_mb: int = 2048,
                               *args, **kwargs) -> Any:
        """모니터링과 함께 함수 실행"""
        start_time = time.time()
        initial_memory = self.resource_monitor.get_memory_usage()
        
        logging.info(f"{context} 시작")
        
        try:
            # 리소스 체크
            self.resource_monitor.check_memory_limit(memory_limit_mb)
            self.resource_monitor.check_timeout(start_time, timeout_seconds, context)
            
            # UI 응답성 유지
            self.ui_manager.process_events_if_needed()
            
            # 실제 함수 실행
            result = func(*args, **kwargs)
            
            # 완료 로그
            self.exception_handler.log_completion(context, start_time, 
                                                self.resource_monitor, initial_memory)
            
            return result
            
        except InterruptedError as e:
            self.exception_handler.handle_interrupted_error(e, context)
        except Exception as e:
            self.exception_handler.handle_general_exception(e, context)
    
    def process_batch_with_progress(self,
                                   items: list,
                                   process_func: Callable,
                                   context: str,
                                   progress_callback: Optional[Callable] = None,
                                   batch_size: int = 100) -> list:
        """배치 처리와 진행률 관리 통합"""
        start_time = time.time()
        results = []
        
        for i, item in enumerate(items):
            # 진행률 업데이트
            self.progress_manager.update_progress(
                progress_callback, i, len(items), start_time, 
                f"{context}: {i+1}/{len(items)} 처리 중"
            )
            
            # 리소스 체크 (배치 단위로)
            if i % batch_size == 0:
                self.resource_monitor.check_memory_limit()
                self.resource_monitor.check_timeout(
                    start_time, PerformanceConstants.CODE_GENERATION_TIMEOUT,
                    context, f"{i}/{len(items)} 처리 완료"
                )
                self.ui_manager.process_events_if_needed()
            
            # 실제 처리
            try:
                result = process_func(item)
                results.append(result)
            except InterruptedError:
                raise
            except Exception as e:
                logging.error(f"{context} 항목 {i} 처리 중 오류: {e}")
                # 개별 항목 오류는 로그만 남기고 계속 진행
        
        return results


# 전역 인스턴스 (싱글톤 패턴)
_processing_pipeline = None

def get_processing_pipeline() -> ProcessingPipeline:
    """ProcessingPipeline 싱글톤 인스턴스 반환"""
    global _processing_pipeline
    if _processing_pipeline is None:
        _processing_pipeline = ProcessingPipeline()
    return _processing_pipeline
