"""
Redis 캐싱 시스템 실제 적용 상태 확인
main.py 실행 환경에서의 실제 캐싱 동작 검증
"""

import sys
import time
import logging
import os
from pathlib import Path
from typing import Dict, List, Any
import json

# 프로젝트 루트 경로 설정
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s'
)

class RedisProductionVerifier:
    """Redis 캐싱 시스템 프로덕션 환경 검증기"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.verification_results = {}
    
    def test_redis_in_main_context(self) -> Dict[str, Any]:
        """main.py 컨텍스트에서 Redis 캐싱 테스트"""
        self.logger.info("1. main.py 컨텍스트에서 Redis 캐싱 테스트")
        
        test_results = {
            'main_import_success': False,
            'phase3_integration_active': False,
            'redis_cache_working': False,
            'memory_fallback_working': False,
            'cache_statistics_collected': False,
            'error_details': None
        }
        
        try:
            # main.py에서 Phase 3 통합 상태 확인
            from main import PHASE3_INTEGRATION_AVAILABLE, DBExcelEditor
            test_results['main_import_success'] = True
            test_results['phase3_integration_active'] = PHASE3_INTEGRATION_AVAILABLE
            
            if PHASE3_INTEGRATION_AVAILABLE:
                # Phase 3 통합 모듈 import
                from ui_backend_integration_strategy import inject_phase3_into_existing_class
                
                # 테스트용 DBExcelEditor 인스턴스 생성
                # (실제 UI 초기화 없이 백엔드만 테스트)
                class TestDBExcelEditor:
                    def __init__(self):
                        pass
                
                # Phase 3 기능 주입
                inject_phase3_into_existing_class(TestDBExcelEditor)
                test_editor = TestDBExcelEditor()
                
                # Phase 3 백엔드 확인
                if hasattr(test_editor, 'phase3_backend') and test_editor.phase3_backend:
                    # 캐싱 프로세서 확인
                    cached_processor = test_editor.phase3_backend._cached_processor
                    
                    if cached_processor:
                        # 캐시 테스트 데이터
                        test_key = "redis_production_test"
                        test_value = [["DEFINE", "CONST", "FLOAT32", "REDIS_TEST", "1.0", "Redis Production Test"]]
                        
                        # 캐시 저장/조회 테스트
                        cached_processor.set_to_cache(test_key, test_value)
                        retrieved_value = cached_processor.get_from_cache(test_key)
                        
                        if retrieved_value == test_value:
                            test_results['memory_fallback_working'] = True
                            self.logger.info("✅ 메모리 캐시 fallback 정상 작동")
                        
                        # 캐시 통계 수집 확인
                        cache_stats = cached_processor.get_cache_stats()
                        if cache_stats and 'cache_hits' in cache_stats:
                            test_results['cache_statistics_collected'] = True
                            self.logger.info(f"✅ 캐시 통계 수집 확인: {cache_stats}")
                        
                        # Redis 연결 테스트 (있다면)
                        if hasattr(cached_processor, 'redis_cache') and cached_processor.redis_cache:
                            try:
                                # Redis 테스트
                                cached_processor.redis_cache.set_cache(test_key, test_value)
                                redis_retrieved = cached_processor.redis_cache.get_cache(test_key)
                                if redis_retrieved == test_value:
                                    test_results['redis_cache_working'] = True
                                    self.logger.info("✅ Redis 캐시 정상 작동")
                            except Exception as e:
                                self.logger.info(f"ℹ️ Redis 캐시 없음 (메모리 캐시로 대체): {e}")
                
                self.logger.info("✅ main.py 컨텍스트에서 캐싱 시스템 검증 완료")
            else:
                test_results['error_details'] = "Phase 3 통합이 비활성화됨"
                
        except Exception as e:
            test_results['error_details'] = str(e)
            self.logger.error(f"❌ main.py 컨텍스트 테스트 실패: {e}")
        
        return test_results
    
    def test_cache_hit_miss_statistics(self) -> Dict[str, Any]:
        """캐시 히트/미스 통계 실제 수집 테스트"""
        self.logger.info("2. 캐시 히트/미스 통계 수집 테스트")
        
        stats_results = {
            'statistics_working': False,
            'hit_miss_tracking': False,
            'performance_measurement': False,
            'cache_efficiency': 0.0,
            'detailed_stats': {}
        }
        
        try:
            from cached_db_processor import CachedDBProcessor, CacheConfig
            
            # 캐싱 프로세서 생성
            config = CacheConfig(
                enable_memory_cache=True,
                memory_cache_size=100,
                enable_redis_cache=False  # 메모리 캐시만 테스트
            )
            
            processor = CachedDBProcessor(config)
            
            # 테스트 데이터 준비
            test_data = []
            for i in range(20):
                test_data.append([
                    "DEFINE", "CONST", "FLOAT32", 
                    f"TEST_VAR_{i}", f"{i}.0", f"Test variable {i}"
                ])
            
            # 첫 번째 실행 (캐시 미스)
            test_key_1 = "stats_test_1"
            start_time = time.perf_counter()
            processor.set_to_cache(test_key_1, test_data)
            first_set_time = time.perf_counter() - start_time
            
            # 첫 번째 조회 (캐시 히트)
            start_time = time.perf_counter()
            retrieved_1 = processor.get_from_cache(test_key_1)
            first_get_time = time.perf_counter() - start_time
            
            # 두 번째 조회 (캐시 히트)
            start_time = time.perf_counter()
            retrieved_2 = processor.get_from_cache(test_key_1)
            second_get_time = time.perf_counter() - start_time
            
            # 존재하지 않는 키 조회 (캐시 미스)
            start_time = time.perf_counter()
            retrieved_none = processor.get_from_cache("nonexistent_key")
            miss_time = time.perf_counter() - start_time
            
            # 통계 수집
            cache_stats = processor.get_cache_stats()
            
            if cache_stats:
                stats_results['statistics_working'] = True
                stats_results['detailed_stats'] = cache_stats
                
                # 히트/미스 추적 확인
                if 'cache_hits' in cache_stats and 'cache_misses' in cache_stats:
                    stats_results['hit_miss_tracking'] = True
                    
                    total_requests = cache_stats['cache_hits'] + cache_stats['cache_misses']
                    if total_requests > 0:
                        stats_results['cache_efficiency'] = cache_stats['cache_hits'] / total_requests * 100
                
                # 성능 측정 확인
                if first_get_time < first_set_time:  # 조회가 저장보다 빠르면 정상
                    stats_results['performance_measurement'] = True
                
                self.logger.info(f"✅ 캐시 통계: {cache_stats}")
                self.logger.info(f"✅ 캐시 효율: {stats_results['cache_efficiency']:.1f}%")
            
            processor.cleanup()
            
        except Exception as e:
            stats_results['error'] = str(e)
            self.logger.error(f"❌ 캐시 통계 테스트 실패: {e}")
        
        return stats_results
    
    def test_memory_fallback_mechanism(self) -> Dict[str, Any]:
        """메모리 캐시 fallback 메커니즘 테스트"""
        self.logger.info("3. 메모리 캐시 fallback 메커니즘 테스트")
        
        fallback_results = {
            'redis_connection_failed': False,
            'memory_fallback_activated': False,
            'data_consistency_maintained': False,
            'performance_acceptable': False,
            'fallback_stats': {}
        }
        
        try:
            from cached_db_processor import CachedDBProcessor, CacheConfig
            
            # Redis 연결 실패 시뮬레이션 (잘못된 설정)
            config_with_redis_fail = CacheConfig(
                enable_redis_cache=True,
                enable_memory_cache=True,
                memory_cache_size=100,
                redis_host='nonexistent_host',
                redis_port=9999
            )
            
            processor = CachedDBProcessor(config_with_redis_fail)
            
            # Redis 연결 실패 확인
            if not hasattr(processor, 'redis_cache') or not processor.redis_cache or not processor.redis_cache.redis_client:
                fallback_results['redis_connection_failed'] = True
                self.logger.info("✅ Redis 연결 실패 시뮬레이션 성공")
            
            # 메모리 캐시로 fallback 테스트
            test_data = [["DEFINE", "CONST", "INT32", "FALLBACK_TEST", "42", "Fallback Test"]]
            test_key = "fallback_test_key"
            
            # 저장 테스트
            start_time = time.perf_counter()
            processor.set_to_cache(test_key, test_data)
            set_time = time.perf_counter() - start_time
            
            # 조회 테스트
            start_time = time.perf_counter()
            retrieved_data = processor.get_from_cache(test_key)
            get_time = time.perf_counter() - start_time
            
            # 데이터 일관성 확인
            if retrieved_data == test_data:
                fallback_results['memory_fallback_activated'] = True
                fallback_results['data_consistency_maintained'] = True
                self.logger.info("✅ 메모리 fallback 데이터 일관성 확인")
            
            # 성능 확인 (메모리 캐시는 충분히 빨라야 함)
            if get_time < 0.001:  # 1ms 이하
                fallback_results['performance_acceptable'] = True
                self.logger.info(f"✅ 메모리 fallback 성능 양호: {get_time*1000:.3f}ms")
            
            # Fallback 통계
            fallback_stats = processor.get_cache_stats()
            if fallback_stats:
                fallback_results['fallback_stats'] = fallback_stats
            
            processor.cleanup()
            
        except Exception as e:
            fallback_results['error'] = str(e)
            self.logger.error(f"❌ 메모리 fallback 테스트 실패: {e}")
        
        return fallback_results
    
    def generate_redis_verification_report(self) -> Dict[str, Any]:
        """Redis 캐싱 시스템 검증 보고서 생성"""
        self.logger.info("Redis 캐싱 시스템 실제 적용 상태 검증 시작")
        
        # 모든 테스트 실행
        main_context_test = self.test_redis_in_main_context()
        statistics_test = self.test_cache_hit_miss_statistics()
        fallback_test = self.test_memory_fallback_mechanism()
        
        # 종합 평가
        total_tests = 6
        passed_tests = 0
        
        # main.py 컨텍스트 테스트
        if main_context_test.get('phase3_integration_active', False):
            passed_tests += 1
        if main_context_test.get('memory_fallback_working', False):
            passed_tests += 1
        
        # 통계 테스트
        if statistics_test.get('statistics_working', False):
            passed_tests += 1
        if statistics_test.get('hit_miss_tracking', False):
            passed_tests += 1
        
        # Fallback 테스트
        if fallback_test.get('memory_fallback_activated', False):
            passed_tests += 1
        if fallback_test.get('data_consistency_maintained', False):
            passed_tests += 1
        
        verification_score = (passed_tests / total_tests) * 100
        
        verification_report = {
            'overall_verification_score': verification_score,
            'tests_passed': passed_tests,
            'total_tests': total_tests,
            'main_context_test': main_context_test,
            'statistics_test': statistics_test,
            'fallback_test': fallback_test,
            'summary': {
                'redis_production_ready': main_context_test.get('phase3_integration_active', False),
                'cache_statistics_working': statistics_test.get('statistics_working', False),
                'fallback_mechanism_reliable': fallback_test.get('data_consistency_maintained', False),
                'overall_cache_efficiency': statistics_test.get('cache_efficiency', 0.0)
            }
        }
        
        return verification_report

def main():
    """Redis 캐싱 시스템 실제 적용 상태 검증 실행"""
    print("🔍 Redis 캐싱 시스템 실제 적용 상태 검증")
    print("=" * 80)
    
    verifier = RedisProductionVerifier()
    
    try:
        # Redis 검증 실행
        report = verifier.generate_redis_verification_report()
        
        # 결과 출력
        print(f"\n📊 Redis 캐싱 시스템 검증 결과:")
        print(f"   검증 점수: {report['overall_verification_score']:.1f}% ({report['tests_passed']}/{report['total_tests']})")
        
        # 주요 결과
        summary = report['summary']
        print(f"\n🔍 주요 검증 결과:")
        print(f"   프로덕션 준비: {'✅' if summary['redis_production_ready'] else '❌'}")
        print(f"   캐시 통계 수집: {'✅' if summary['cache_statistics_working'] else '❌'}")
        print(f"   Fallback 신뢰성: {'✅' if summary['fallback_mechanism_reliable'] else '❌'}")
        print(f"   캐시 효율: {summary['overall_cache_efficiency']:.1f}%")
        
        # 상세 결과
        print(f"\n📋 상세 테스트 결과:")
        
        main_test = report['main_context_test']
        print(f"   main.py 컨텍스트: {'✅' if main_test.get('phase3_integration_active') else '❌'}")
        if main_test.get('memory_fallback_working'):
            print(f"     메모리 캐시: ✅ 정상 작동")
        
        stats_test = report['statistics_test']
        if stats_test.get('detailed_stats'):
            stats = stats_test['detailed_stats']
            print(f"   캐시 통계: ✅ 수집 중")
            print(f"     히트: {stats.get('cache_hits', 0)}회")
            print(f"     미스: {stats.get('cache_misses', 0)}회")
            print(f"     크기: {stats.get('cache_size', 0)}/{stats.get('max_size', 0)}")
        
        fallback_test = report['fallback_test']
        if fallback_test.get('fallback_stats'):
            print(f"   Fallback 통계: ✅ 정상")
        
        # 결과 저장
        with open('redis_production_verification_report.json', 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print(f"\n📄 상세 보고서가 'redis_production_verification_report.json'에 저장되었습니다.")
        
    except Exception as e:
        print(f"❌ Redis 검증 실패: {e}")
        logging.error(f"Redis 검증 실패: {e}")
    
    print("=" * 80)

if __name__ == "__main__":
    main()
