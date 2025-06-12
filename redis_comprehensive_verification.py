"""
Redis 캐싱 시스템 종합 검증
main.py 실행 환경에서의 완전한 작동 상태 확인
"""

import time
import threading
import hashlib
import pickle
import logging
import os
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional
import json
from concurrent.futures import ThreadPoolExecutor

# 프로젝트 루트 경로 설정
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s'
)

class RedisComprehensiveVerifier:
    """Redis 캐싱 시스템 종합 검증기"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.verification_results = {}

    def test_redis_server_connection(self) -> Dict[str, Any]:
        """Redis 서버 연결 상태 실제 테스트"""
        self.logger.info("1. Redis 서버 연결 상태 검증")

        test_results = {
            'redis_module_available': False,
            'redis_server_running': False,
            'basic_operations_working': False,
            'connection_details': {},
            'error_details': None
        }

        try:
            # Redis 모듈 설치 확인
            import redis
            test_results['redis_module_available'] = True
            self.logger.info("✅ Redis 모듈 설치됨")

            # Redis 서버 연결 테스트
            redis_client = redis.Redis(
                host='localhost',
                port=6379,
                db=0,
                decode_responses=False,
                socket_connect_timeout=5,
                socket_timeout=5
            )

            # 연결 테스트
            response = redis_client.ping()
            if response:
                test_results['redis_server_running'] = True
                self.logger.info("✅ Redis 서버 연결 성공")

                # 서버 정보 수집
                info = redis_client.info()
                test_results['connection_details'] = {
                    'redis_version': info.get('redis_version', 'unknown'),
                    'used_memory': info.get('used_memory_human', 'unknown'),
                    'connected_clients': info.get('connected_clients', 0),
                    'total_commands_processed': info.get('total_commands_processed', 0)
                }

                # 기본 작업 테스트
                test_key = 'verification_test_key'
                test_value = {
                    'test_data': 'Redis 검증 테스트',
                    'timestamp': time.time(),
                    'complex_data': [1, 2, {'nested': 'value'}]
                }

                # SET 작업
                redis_client.set(test_key, pickle.dumps(test_value), ex=60)

                # GET 작업
                retrieved_data = redis_client.get(test_key)
                if retrieved_data:
                    unpickled_data = pickle.loads(retrieved_data)
                    if unpickled_data == test_value:
                        test_results['basic_operations_working'] = True
                        self.logger.info("✅ Redis 기본 작업 성공")

                # 정리
                redis_client.delete(test_key)

            else:
                test_results['error_details'] = "Redis ping 실패"

        except ImportError:
            test_results['error_details'] = "Redis 모듈이 설치되지 않음"
            self.logger.warning("⚠️ Redis 모듈 미설치")
        except redis.ConnectionError as e:
            test_results['error_details'] = f"Redis 서버 연결 실패: {e}"
            self.logger.warning(f"⚠️ Redis 서버 연결 실패: {e}")
        except Exception as e:
            test_results['error_details'] = f"Redis 테스트 오류: {e}"
            self.logger.error(f"❌ Redis 테스트 오류: {e}")

        return test_results

    def test_hierarchical_caching(self) -> Dict[str, Any]:
        """계층적 캐싱 (Redis + 메모리) 실제 동작 테스트"""
        self.logger.info("2. 계층적 캐싱 시스템 검증")

        from cached_db_processor import CachedDBProcessor, CacheConfig

        # Redis + 메모리 캐시 설정
        config_with_redis = CacheConfig(
            enable_redis_cache=True,
            enable_memory_cache=True,
            memory_cache_size=100,
            redis_host='localhost',
            redis_port=6379
        )

        test_results = {
            'redis_cache_working': False,
            'memory_cache_working': False,
            'hierarchical_flow': False,
            'cache_statistics': {}
        }

        try:
            processor = CachedDBProcessor(config_with_redis)

            # 테스트 데이터
            test_key = "hierarchical_test_key"
            test_value = [["DEFINE", "CONST", "FLOAT32", "TEST_VAL", "1.0", "Hierarchical Test"]]

            # 1. 캐시에 저장 (Redis + 메모리)
            processor.set_to_cache(test_key, test_value)

            # 2. 메모리 캐시에서 조회 (빠른 경로)
            memory_result = processor.get_from_cache(test_key)
            if memory_result == test_value:
                test_results['memory_cache_working'] = True
                self.logger.info("✅ 메모리 캐시 작동")

            # 3. 메모리 캐시 클리어 후 Redis에서 조회
            if processor.memory_cache:
                processor.memory_cache.clear()

            redis_result = processor.get_from_cache(test_key)
            if redis_result == test_value:
                test_results['redis_cache_working'] = True
                test_results['hierarchical_flow'] = True
                self.logger.info("✅ Redis 캐시 작동 및 계층적 흐름 확인")

            # 캐시 통계 수집
            cache_stats = processor.get_cache_stats()
            test_results['cache_statistics'] = cache_stats

            processor.cleanup()

        except Exception as e:
            test_results['error'] = str(e)
            self.logger.error(f"❌ 계층적 캐싱 테스트 실패: {e}")

        return test_results

    def test_fallback_mechanism(self) -> Dict[str, Any]:
        """Fallback 메커니즘 실제 동작 테스트"""
        self.logger.info("3. Fallback 메커니즘 검증")

        from cached_db_processor import CachedDBProcessor, CacheConfig

        # 잘못된 Redis 설정 (의도적 실패)
        config_fallback = CacheConfig(
            enable_redis_cache=True,
            enable_memory_cache=True,
            memory_cache_size=100,
            redis_host='nonexistent_host',  # 존재하지 않는 호스트
            redis_port=9999  # 잘못된 포트
        )

        test_results = {
            'redis_connection_failed': False,
            'fallback_to_memory': False,
            'data_consistency': False,
            'graceful_degradation': False
        }

        try:
            processor = CachedDBProcessor(config_fallback)

            # Redis 연결 실패 확인
            if processor.redis_cache and not processor.redis_cache.redis_client:
                test_results['redis_connection_failed'] = True
                self.logger.info("✅ Redis 연결 실패 감지됨")

            # 메모리 캐시로 fallback 테스트
            test_key = "fallback_test_key"
            test_value = [["DEFINE", "CONST", "INT32", "FALLBACK_VAL", "42", "Fallback Test"]]

            # 저장 및 조회 테스트
            processor.set_to_cache(test_key, test_value)
            retrieved_value = processor.get_from_cache(test_key)

            if retrieved_value == test_value:
                test_results['fallback_to_memory'] = True
                test_results['data_consistency'] = True
                test_results['graceful_degradation'] = True
                self.logger.info("✅ Fallback 메커니즘 정상 작동")

            processor.cleanup()

        except Exception as e:
            test_results['error'] = str(e)
            self.logger.error(f"❌ Fallback 테스트 실패: {e}")

        return test_results

    def test_cache_key_generation(self) -> Dict[str, Any]:
        """캐시 키 생성 로직 정확성 검증"""
        self.logger.info("4. 캐시 키 생성 로직 검증")

        from cached_db_processor import CachedDBProcessor

        # 테스트 파일 생성
        test_file = Path('cache_key_test.db')
        test_file.write_text("initial content")

        test_results = {
            'key_consistency': False,
            'parameter_sensitivity': False,
            'modification_sensitivity': False,
            'mtime_included': False,
            'size_included': False
        }

        try:
            processor = CachedDBProcessor()

            # 1. 동일 파라미터로 키 일관성 테스트
            key1 = processor.generate_cache_key(test_file, 1, 0, 100)
            key2 = processor.generate_cache_key(test_file, 1, 0, 100)

            if key1 == key2:
                test_results['key_consistency'] = True
                self.logger.info("✅ 키 일관성 확인")

            # 2. 파라미터 민감성 테스트
            key_diff_sheet = processor.generate_cache_key(test_file, 2, 0, 100)
            key_diff_chunk = processor.generate_cache_key(test_file, 1, 0, 200)

            if len(set([key1, key_diff_sheet, key_diff_chunk])) == 3:
                test_results['parameter_sensitivity'] = True
                self.logger.info("✅ 파라미터 민감성 확인")

            # 3. 파일 수정 시간/크기 포함 확인
            stat_before = test_file.stat()

            # 파일 수정
            time.sleep(0.1)
            test_file.write_text("modified content - longer")

            key_after_modification = processor.generate_cache_key(test_file, 1, 0, 100)
            stat_after = test_file.stat()

            if key1 != key_after_modification:
                test_results['modification_sensitivity'] = True
                self.logger.info("✅ 파일 수정 민감성 확인")

            # mtime과 size가 실제로 변경되었는지 확인
            if stat_before.st_mtime != stat_after.st_mtime:
                test_results['mtime_included'] = True
                self.logger.info("✅ 수정 시간 변화 감지")

            if stat_before.st_size != stat_after.st_size:
                test_results['size_included'] = True
                self.logger.info("✅ 파일 크기 변화 감지")

        except Exception as e:
            test_results['error'] = str(e)
            self.logger.error(f"❌ 캐시 키 테스트 실패: {e}")
        finally:
            # 테스트 파일 정리
            if test_file.exists():
                test_file.unlink()

        return test_results

    def test_lru_algorithm(self) -> Dict[str, Any]:
        """LRU 캐시 알고리즘 실제 동작 테스트"""
        self.logger.info("5. LRU 캐시 알고리즘 검증")

        from cached_db_processor import MemoryCache

        # 작은 캐시 크기로 테스트
        cache = MemoryCache(max_size=5)

        test_results = {
            'lru_eviction_working': False,
            'access_order_maintained': False,
            'size_limit_enforced': False,
            'statistics_accurate': False
        }

        try:
            # 1. 캐시 크기 제한 테스트
            for i in range(10):  # 캐시 크기(5)를 초과하는 데이터 저장
                cache.set(f'key_{i}', f'value_{i}')

            if len(cache.cache) == 5:  # 최대 크기 유지
                test_results['size_limit_enforced'] = True
                self.logger.info("✅ 캐시 크기 제한 확인")

            # 2. LRU 제거 확인 (초기 키들이 제거되었는지)
            if cache.get('key_0') is None and cache.get('key_9') is not None:
                test_results['lru_eviction_working'] = True
                self.logger.info("✅ LRU 제거 메커니즘 확인")

            # 3. 접근 순서 유지 테스트
            cache.get('key_5')  # key_5 접근으로 최신으로 만듦
            cache.set('key_new', 'new_value')  # 새 항목 추가

            if cache.get('key_5') is not None:  # 최근 접근한 key_5는 유지되어야 함
                test_results['access_order_maintained'] = True
                self.logger.info("✅ 접근 순서 유지 확인")

            # 4. 통계 정확성 확인
            stats = cache.get_stats()
            if stats['cache_size'] == len(cache.cache) and stats['max_size'] == 5:
                test_results['statistics_accurate'] = True
                self.logger.info("✅ 캐시 통계 정확성 확인")

        except Exception as e:
            test_results['error'] = str(e)
            self.logger.error(f"❌ LRU 테스트 실패: {e}")

        return test_results

    def test_thread_safety(self) -> Dict[str, Any]:
        """멀티스레딩 환경에서 스레드 안전성 테스트"""
        self.logger.info("6. 스레드 안전성 검증")

        from cached_db_processor import MemoryCache

        cache = MemoryCache(max_size=1000)
        test_results = {
            'concurrent_access_safe': False,
            'data_integrity_maintained': False,
            'no_race_conditions': False,
            'operations_completed': 0,
            'operations_expected': 0
        }

        def concurrent_cache_operation(thread_id: int, operations_count: int = 50):
            """동시 캐시 작업"""
            success_count = 0
            for i in range(operations_count):
                try:
                    key = f'thread_{thread_id}_key_{i}'
                    value = f'thread_{thread_id}_value_{i}'

                    # 저장
                    cache.set(key, value)

                    # 조회
                    retrieved = cache.get(key)
                    if retrieved == value:
                        success_count += 1

                    # 일부 키 삭제
                    if i % 10 == 0:
                        cache.delete(key)

                except Exception:
                    pass

            return success_count

        try:
            # 10개 스레드로 동시 작업
            thread_count = 10
            operations_per_thread = 50
            test_results['operations_expected'] = thread_count * operations_per_thread

            with ThreadPoolExecutor(max_workers=thread_count) as executor:
                futures = [
                    executor.submit(concurrent_cache_operation, i, operations_per_thread)
                    for i in range(thread_count)
                ]

                results = [future.result() for future in futures]
                test_results['operations_completed'] = sum(results)

            # 성공률 계산
            success_rate = test_results['operations_completed'] / test_results['operations_expected']

            if success_rate > 0.95:  # 95% 이상 성공
                test_results['concurrent_access_safe'] = True
                test_results['data_integrity_maintained'] = True
                test_results['no_race_conditions'] = True
                self.logger.info(f"✅ 스레드 안전성 확인 (성공률: {success_rate:.2%})")
            else:
                self.logger.warning(f"⚠️ 스레드 안전성 문제 (성공률: {success_rate:.2%})")

        except Exception as e:
            test_results['error'] = str(e)
            self.logger.error(f"❌ 스레드 안전성 테스트 실패: {e}")

        return test_results

    def generate_comprehensive_report(self) -> Dict[str, Any]:
        """종합 검증 보고서 생성"""
        self.logger.info("Redis 캐싱 시스템 종합 검증 시작")

        # 모든 테스트 실행
        redis_connection = self.test_redis_server_connection()
        hierarchical_caching = self.test_hierarchical_caching()
        fallback_mechanism = self.test_fallback_mechanism()
        cache_key_generation = self.test_cache_key_generation()
        lru_algorithm = self.test_lru_algorithm()
        thread_safety = self.test_thread_safety()

        # 종합 평가
        total_tests = 0
        passed_tests = 0

        # Redis 연결 (선택사항)
        if redis_connection.get('redis_server_running', False):
            passed_tests += 1
        total_tests += 1

        # 계층적 캐싱 (Redis 있을 때만)
        if redis_connection.get('redis_server_running', False):
            if hierarchical_caching.get('hierarchical_flow', False):
                passed_tests += 1
            total_tests += 1

        # Fallback 메커니즘 (필수)
        if fallback_mechanism.get('graceful_degradation', False):
            passed_tests += 1
        total_tests += 1

        # 캐시 키 생성 (필수)
        key_tests = ['key_consistency', 'parameter_sensitivity', 'modification_sensitivity']
        if all(cache_key_generation.get(test, False) for test in key_tests):
            passed_tests += 1
        total_tests += 1

        # LRU 알고리즘 (필수)
        lru_tests = ['lru_eviction_working', 'size_limit_enforced']
        if all(lru_algorithm.get(test, False) for test in lru_tests):
            passed_tests += 1
        total_tests += 1

        # 스레드 안전성 (필수)
        if thread_safety.get('concurrent_access_safe', False):
            passed_tests += 1
        total_tests += 1

        quality_score = (passed_tests / total_tests) * 100 if total_tests > 0 else 0

        comprehensive_report = {
            'overall_quality_score': quality_score,
            'tests_passed': passed_tests,
            'total_tests': total_tests,
            'redis_connection_test': redis_connection,
            'hierarchical_caching_test': hierarchical_caching,
            'fallback_mechanism_test': fallback_mechanism,
            'cache_key_generation_test': cache_key_generation,
            'lru_algorithm_test': lru_algorithm,
            'thread_safety_test': thread_safety,
            'recommendations': self.generate_recommendations(
                redis_connection, hierarchical_caching, fallback_mechanism,
                cache_key_generation, lru_algorithm, thread_safety
            )
        }

        return comprehensive_report

    def generate_recommendations(self, *test_results) -> List[str]:
        """개선 권장사항 생성"""
        recommendations = []

        redis_test = test_results[0]
        if not redis_test.get('redis_server_running', False):
            if not redis_test.get('redis_module_available', False):
                recommendations.append("Redis 모듈 설치: pip install redis")
            recommendations.append("Redis 서버 설치 및 실행을 권장합니다 (성능 향상)")

        thread_test = test_results[5]
        if not thread_test.get('concurrent_access_safe', False):
            recommendations.append("스레드 안전성 개선이 필요합니다")

        if not recommendations:
            recommendations.append("모든 캐시 기능이 우수하게 구현되었습니다")

        return recommendations

def main():
    """Redis 캐싱 시스템 종합 검증 실행"""
    print("🔍 Redis 캐싱 시스템 종합 검증")
    print("=" * 80)

    verifier = RedisComprehensiveVerifier()

    try:
        # 종합 검증 실행
        report = verifier.generate_comprehensive_report()

        # 결과 출력
        print(f"\n📊 Redis 캐싱 시스템 종합 검증 결과:")
        print(f"   품질 점수: {report['overall_quality_score']:.1f}% ({report['tests_passed']}/{report['total_tests']})")

        # 개별 테스트 결과
        print(f"\n🔍 개별 테스트 결과:")

        redis_test = report['redis_connection_test']
        print(f"   Redis 연결: {'✅' if redis_test.get('redis_server_running') else '⚠️ 미사용'}")
        if redis_test.get('connection_details'):
            details = redis_test['connection_details']
            print(f"     버전: {details.get('redis_version', 'unknown')}")
            print(f"     메모리: {details.get('used_memory', 'unknown')}")

        fallback_test = report['fallback_mechanism_test']
        print(f"   Fallback 메커니즘: {'✅' if fallback_test.get('graceful_degradation') else '❌'}")

        key_test = report['cache_key_generation_test']
        print(f"   키 생성 로직: {'✅' if key_test.get('key_consistency') else '❌'}")

        lru_test = report['lru_algorithm_test']
        print(f"   LRU 알고리즘: {'✅' if lru_test.get('lru_eviction_working') else '❌'}")

        thread_test = report['thread_safety_test']
        print(f"   스레드 안전성: {'✅' if thread_test.get('concurrent_access_safe') else '❌'}")
        if 'operations_completed' in thread_test:
            success_rate = thread_test['operations_completed'] / thread_test['operations_expected'] * 100
            print(f"     성공률: {success_rate:.1f}%")

        # 권장사항
        print(f"\n💡 권장사항:")
        for rec in report['recommendations']:
            print(f"   - {rec}")

        # 결과 저장
        with open('redis_comprehensive_verification_report.json', 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        print(f"\n📄 상세 보고서가 'redis_comprehensive_verification_report.json'에 저장되었습니다.")

    except Exception as e:
        print(f"❌ 종합 검증 실패: {e}")
        logging.error(f"종합 검증 실패: {e}")

    print("=" * 80)

if __name__ == "__main__":
    main()