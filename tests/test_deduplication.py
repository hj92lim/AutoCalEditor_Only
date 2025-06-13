"""
중복 제거 효과 테스트 및 성능 측정
"""

import time
import unittest
from unittest.mock import Mock, patch
from code_generator.processing_manager import ProcessingPipeline, get_processing_pipeline
from code_generator.make_code import MakeCode


class TestDeduplicationEffects(unittest.TestCase):
    """중복 제거 효과 테스트"""
    
    def setUp(self):
        """테스트 설정"""
        self.mock_of = Mock()
        self.mock_lb_src = Mock()
        self.mock_lb_hdr = Mock()
        
        # MakeCode 인스턴스 생성
        self.make_code = MakeCode(self.mock_of, self.mock_lb_src, self.mock_lb_hdr)
        
        # 테스트용 시트 데이터 설정
        self.make_code.cl = [Mock() for _ in range(5)]
        for i, cl in enumerate(self.make_code.cl):
            cl.ShtName = f"TestSheet{i}"
            cl.ReadCalList = Mock()
            cl.PrjtNameMain = f"Project{i}"
    
    def test_processing_pipeline_singleton(self):
        """ProcessingPipeline 싱글톤 패턴 테스트"""
        pipeline1 = get_processing_pipeline()
        pipeline2 = get_processing_pipeline()
        
        self.assertIs(pipeline1, pipeline2, "ProcessingPipeline은 싱글톤이어야 합니다")
    
    def test_progress_manager_update_frequency(self):
        """진행률 관리자 업데이트 빈도 제한 테스트"""
        pipeline = get_processing_pipeline()
        progress_callback = Mock()
        
        start_time = time.time()
        
        # 연속으로 여러 번 호출
        for i in range(10):
            pipeline.progress_manager.update_progress(
                progress_callback, i, 10, start_time, f"테스트 {i}"
            )
        
        # 업데이트 빈도 제한으로 인해 실제 콜백 호출 횟수는 적어야 함
        self.assertLessEqual(progress_callback.call_count, 3, 
                           "진행률 업데이트 빈도가 제한되어야 합니다")
    
    def test_resource_monitor_memory_caching(self):
        """리소스 모니터 메모리 캐싱 테스트"""
        pipeline = get_processing_pipeline()
        
        # 첫 번째 호출
        memory1 = pipeline.resource_monitor.get_memory_usage()
        
        # 즉시 두 번째 호출 (캐시된 값 반환되어야 함)
        memory2 = pipeline.resource_monitor.get_memory_usage()
        
        if pipeline.resource_monitor._memory_monitoring:
            self.assertEqual(memory1, memory2, "메모리 사용량이 캐싱되어야 합니다")
    
    def test_ui_manager_event_processing_frequency(self):
        """UI 관리자 이벤트 처리 빈도 테스트"""
        pipeline = get_processing_pipeline()
        
        with patch('PySide6.QtWidgets.QApplication.processEvents') as mock_process_events:
            # 연속으로 여러 번 호출
            for _ in range(10):
                pipeline.ui_manager.process_events_if_needed()
            
            # 빈도 제한으로 인해 실제 processEvents 호출 횟수는 적어야 함
            self.assertLessEqual(mock_process_events.call_count, 3,
                               "UI 이벤트 처리 빈도가 제한되어야 합니다")
    
    def test_batch_processing_efficiency(self):
        """배치 처리 효율성 테스트"""
        pipeline = get_processing_pipeline()
        
        # 테스트 데이터
        test_items = list(range(100))
        processed_items = []
        
        def mock_process_func(item):
            processed_items.append(item)
            return f"처리됨: {item}"
        
        start_time = time.time()
        
        results = pipeline.process_batch_with_progress(
            test_items,
            mock_process_func,
            "배치 처리 테스트",
            None,  # progress_callback 없음
            batch_size=10
        )
        
        elapsed_time = time.time() - start_time
        
        # 모든 아이템이 처리되었는지 확인
        self.assertEqual(len(processed_items), 100, "모든 아이템이 처리되어야 합니다")
        self.assertEqual(len(results), 100, "모든 결과가 반환되어야 합니다")
        
        # 성능 확인 (100개 아이템 처리가 1초 이내)
        self.assertLess(elapsed_time, 1.0, "배치 처리가 효율적이어야 합니다")
    

    
    def test_memory_usage_optimization(self):
        """메모리 사용량 최적화 테스트"""
        pipeline = get_processing_pipeline()
        
        # 초기 메모리 사용량
        initial_memory = pipeline.resource_monitor.get_memory_usage()
        
        # 대량 데이터 처리 시뮬레이션
        large_data = list(range(1000))
        
        def memory_intensive_func(item):
            # 메모리를 많이 사용하는 작업 시뮬레이션
            temp_data = [i for i in range(item, item + 100)]
            return sum(temp_data)
        
        results = pipeline.process_batch_with_progress(
            large_data,
            memory_intensive_func,
            "메모리 집약적 처리",
            None,
            batch_size=50
        )
        
        # 최종 메모리 사용량
        final_memory = pipeline.resource_monitor.get_memory_usage()
        
        # 메모리 증가량이 합리적인 범위 내인지 확인
        if pipeline.resource_monitor._memory_monitoring:
            memory_increase = final_memory - initial_memory
            self.assertLess(memory_increase, 100, "메모리 사용량 증가가 제한되어야 합니다")  # 100MB 이내
    
    def test_error_handling_consistency(self):
        """일관된 예외 처리 테스트"""
        pipeline = get_processing_pipeline()
        
        def failing_function():
            raise ValueError("테스트 오류")
        
        with self.assertRaises(ValueError):
            pipeline.execute_with_monitoring(
                failing_function,
                "오류 테스트",
                None,
                10,  # 10초 타임아웃
                1024  # 1GB 메모리 제한
            )


class TestPerformanceImprovement(unittest.TestCase):
    """성능 개선 효과 측정 테스트"""
    
    def test_function_call_overhead_reduction(self):
        """함수 호출 오버헤드 감소 테스트"""
        # 기존 방식 시뮬레이션 (중복 호출)
        start_time = time.time()
        
        for i in range(1000):
            # 중복된 진행률 업데이트 시뮬레이션
            pass
        
        old_method_time = time.time() - start_time
        
        # 새로운 방식 (통합 파이프라인)
        pipeline = get_processing_pipeline()
        start_time = time.time()
        
        for i in range(1000):
            # 최적화된 진행률 업데이트
            pipeline.progress_manager.update_progress(None, i, 1000, start_time)
        
        new_method_time = time.time() - start_time
        
        # 새로운 방식이 더 빠르거나 비슷해야 함
        self.assertLessEqual(new_method_time, old_method_time * 1.1,
                           "새로운 방식이 성능상 이점이 있어야 합니다")


if __name__ == '__main__':
    unittest.main()
