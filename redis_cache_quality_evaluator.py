"""
Redis 캐싱 시스템 구현 품질 평가기
Redis 연결, 데이터 일관성, fallback 메커니즘 등 종합 검증
"""

import time
import logging
import os
import sys
import hashlib
import pickle
from pathlib import Path
from typing import Dict, List, Any, Optional
import json
import threading
from concurrent.futures import ThreadPoolExecutor

# 프로젝트 루트 경로 설정
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s'
)

class RedisCacheQualityEvaluator:
    """Redis 캐싱 시스템 품질 평가기"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.evaluation_results = {}
    
    def test_redis_connection(self) -> Dict[str, Any]:
        """Redis 연결 테스트"""
        self.logger.info("Redis 연결 테스트 시작")
        
        test_results = {
            'redis_available': False,
            'connection_successful': False,
            'basic_operations': False,
            'error_details': None
        }
        
        try:
            # Redis 모듈 import 테스트
            import redis
            test_results['redis_module_available'] = True
            
            # Redis 연결 테스트
            redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=False)
            redis_client.ping()
            test_results['connection_successful'] = True
            test_results['redis_available'] = True
            
            # 기본 작업 테스트
            test_key = 'cache_quality_test'
            test_value = {'test': 'data', 'timestamp': time.time()}
            
            # SET 테스트
            redis_client.set(test_key, pickle.dumps(test_value))
            
            # GET 테스트
            retrieved_data = redis_client.get(test_key)
            if retrieved_data:
                unpickled_data = pickle.loads(retrieved_data)
                if unpickled_data == test_value:
                    test_results['basic_operations'] = True
            
            # 정리
            redis_client.delete(test_key)
            
            self.logger.info("✅ Redis 연결 및 기본 작업 성공")
            
        except ImportError:
            test_results['error_details'] = "Redis 모듈이 설치되지 않음"
            self.logger.warning("⚠️ Redis 모듈이 설치되지 않았습니다.")
        except Exception as e:
            test_results['error_details'] = str(e)
            self.logger.warning(f"⚠️ Redis 연결 실패: {e}")
        
        return test_results
    
    def test_cache_fallback_mechanism(self) -> Dict[str, Any]:
        """캐시 fallback 메커니즘 테스트"""
        self.logger.info("캐시 fallback 메커니즘 테스트 시작")
        
        from cached_db_processor import CachedDBProcessor, CacheConfig
        
        # Redis 없이 메모리 캐시만 사용하는 설정
        config_memory_only = CacheConfig(
            enable_redis_cache=False,
            enable_memory_cache=True,
            memory_cache_size=100
        )
        
        # Redis + 메모리 캐시 사용하는 설정 (Redis 없어도 작동해야 함)
        config_redis_fallback = CacheConfig(
            enable_redis_cache=True,
            enable_memory_cache=True,
            memory_cache_size=100,
            redis_host='nonexistent_host',  # 의도적으로 잘못된 호스트
            redis_port=9999
        )
        
        fallback_results = {}
        
        # 1. 메모리 캐시만 사용
        try:
            processor_memory = CachedDBProcessor(config_memory_only)
            
            # 테스트 데이터
            test_key = "test_fallback_key"
            test_value = [["DEFINE", "CONST", "FLOAT32", "TEST", "1.0", "Test"]]
            
            # 캐시 저장/조회 테스트
            processor_memory.set_to_cache(test_key, test_value)
            retrieved_value = processor_memory.get_from_cache(test_key)
            
            fallback_results['memory_only'] = {
                'success': retrieved_value == test_value,
                'cache_working': retrieved_value is not None
            }
            
            processor_memory.cleanup()
            
        except Exception as e:
            fallback_results['memory_only'] = {
                'success': False,
                'error': str(e)
            }
        
        # 2. Redis fallback 테스트
        try:
            processor_fallback = CachedDBProcessor(config_redis_fallback)
            
            # Redis 연결 실패해도 메모리 캐시로 작동해야 함
            test_key = "test_redis_fallback_key"
            test_value = [["DEFINE", "CONST", "FLOAT32", "FALLBACK", "2.0", "Fallback"]]
            
            processor_fallback.set_to_cache(test_key, test_value)
            retrieved_value = processor_fallback.get_from_cache(test_key)
            
            fallback_results['redis_fallback'] = {
                'success': retrieved_value == test_value,
                'fallback_working': retrieved_value is not None,
                'redis_failed_gracefully': True
            }
            
            processor_fallback.cleanup()
            
        except Exception as e:
            fallback_results['redis_fallback'] = {
                'success': False,
                'error': str(e),
                'redis_failed_gracefully': False
            }
        
        self.logger.info("캐시 fallback 메커니즘 테스트 완료")
        return fallback_results
    
    def test_cache_key_generation(self) -> Dict[str, Any]:
        """캐시 키 생성 로직 테스트"""
        self.logger.info("캐시 키 생성 로직 테스트 시작")
        
        from cached_db_processor import CachedDBProcessor
        
        processor = CachedDBProcessor()
        
        # 테스트 파일 생성
        test_file = Path('test_cache_key.db')
        test_file.write_text("test content")
        
        try:
            # 동일한 파라미터로 키 생성
            key1 = processor.generate_cache_key(test_file, 1, 0, 100)
            key2 = processor.generate_cache_key(test_file, 1, 0, 100)
            
            # 다른 파라미터로 키 생성
            key3 = processor.generate_cache_key(test_file, 1, 0, 200)  # 다른 chunk_end
            key4 = processor.generate_cache_key(test_file, 2, 0, 100)  # 다른 sheet_id
            
            # 파일 수정 후 키 생성
            time.sleep(0.1)  # 수정 시간 차이 보장
            test_file.write_text("modified content")
            key5 = processor.generate_cache_key(test_file, 1, 0, 100)
            
            key_test_results = {
                'consistency': key1 == key2,
                'parameter_sensitivity': len(set([key1, key3, key4])) == 3,
                'modification_sensitivity': key1 != key5,
                'key_format_valid': all(len(key) == 32 for key in [key1, key2, key3, key4, key5])
            }
            
            self.logger.info("✅ 캐시 키 생성 로직 검증 완료")
            
        except Exception as e:
            key_test_results = {
                'success': False,
                'error': str(e)
            }
        finally:
            # 테스트 파일 정리
            if test_file.exists():
                test_file.unlink()
        
        return key_test_results
    
    def test_cache_data_consistency(self) -> Dict[str, Any]:
        """캐시 데이터 일관성 테스트"""
        self.logger.info("캐시 데이터 일관성 테스트 시작")
        
        from cached_db_processor import MemoryCache
        
        cache = MemoryCache(max_size=10)
        
        # 테스트 데이터
        test_data = {
            'key1': [["DEFINE", "CONST", "FLOAT32", "VAL1", "1.0", "Test1"]],
            'key2': [["DEFINE", "CONST", "INT32", "VAL2", "2", "Test2"]],
            'key3': [["DEFINE", "CONST", "STRING", "VAL3", '"test"', "Test3"]]
        }
        
        consistency_results = {
            'storage_retrieval': True,
            'lru_behavior': True,
            'data_integrity': True,
            'concurrent_access': True
        }
        
        try:
            # 1. 저장/조회 일관성
            for key, value in test_data.items():
                cache.set(key, value)
                retrieved = cache.get(key)
                if retrieved != value:
                    consistency_results['storage_retrieval'] = False
                    break
            
            # 2. LRU 동작 확인
            # 캐시 크기를 초과하는 데이터 저장
            for i in range(15):  # 캐시 크기(10)를 초과
                cache.set(f'lru_test_{i}', f'value_{i}')
            
            # 초기 키들이 제거되었는지 확인
            if cache.get('lru_test_0') is not None:  # 첫 번째 키는 제거되어야 함
                consistency_results['lru_behavior'] = False
            
            if cache.get('lru_test_14') is None:  # 마지막 키는 존재해야 함
                consistency_results['lru_behavior'] = False
            
            # 3. 데이터 무결성 확인
            complex_data = {
                'nested': {'list': [1, 2, 3], 'dict': {'a': 'b'}},
                'unicode': '한글 테스트',
                'special_chars': '!@#$%^&*()'
            }
            
            cache.set('complex_key', complex_data)
            retrieved_complex = cache.get('complex_key')
            if retrieved_complex != complex_data:
                consistency_results['data_integrity'] = False
            
            # 4. 동시 접근 테스트
            def concurrent_cache_operation(cache_obj, thread_id):
                for i in range(10):
                    key = f'thread_{thread_id}_key_{i}'
                    value = f'thread_{thread_id}_value_{i}'
                    cache_obj.set(key, value)
                    retrieved = cache_obj.get(key)
                    if retrieved != value:
                        return False
                return True
            
            with ThreadPoolExecutor(max_workers=3) as executor:
                futures = [executor.submit(concurrent_cache_operation, cache, i) for i in range(3)]
                concurrent_results = [future.result() for future in futures]
                
                if not all(concurrent_results):
                    consistency_results['concurrent_access'] = False
            
            # 캐시 통계 확인
            stats = cache.get_stats()
            consistency_results['cache_stats'] = stats
            
            self.logger.info("✅ 캐시 데이터 일관성 검증 완료")
            
        except Exception as e:
            consistency_results['success'] = False
            consistency_results['error'] = str(e)
        
        return consistency_results
    
    def test_cache_performance_impact(self) -> Dict[str, Any]:
        """캐시 성능 영향 테스트"""
        self.logger.info("캐시 성능 영향 테스트 시작")
        
        from cached_db_processor import CachedDBProcessor, CacheConfig
        
        # DB 파일 확인
        db_dir = Path('database')
        db_files = [f for f in db_dir.glob('*.db') if f.stat().st_size > 50000][:1]  # 1개 파일만
        
        if not db_files:
            return {'success': False, 'error': 'No DB files available for testing'}
        
        db_file = db_files[0]
        
        performance_results = {}
        
        try:
            # 1. 캐시 없이 처리
            config_no_cache = CacheConfig(
                enable_redis_cache=False,
                enable_memory_cache=False
            )
            
            processor_no_cache = CachedDBProcessor(config_no_cache)
            
            start_time = time.perf_counter()
            result_no_cache = processor_no_cache.process_batch_cached([db_file])
            no_cache_time = time.perf_counter() - start_time
            
            processor_no_cache.cleanup()
            
            # 2. 메모리 캐시 사용
            config_with_cache = CacheConfig(
                enable_redis_cache=False,
                enable_memory_cache=True,
                memory_cache_size=1000
            )
            
            processor_with_cache = CachedDBProcessor(config_with_cache)
            
            # 첫 번째 실행 (캐시 구축)
            start_time = time.perf_counter()
            result_first_run = processor_with_cache.process_batch_cached([db_file])
            first_run_time = time.perf_counter() - start_time
            
            # 두 번째 실행 (캐시 활용)
            start_time = time.perf_counter()
            result_second_run = processor_with_cache.process_batch_cached([db_file])
            second_run_time = time.perf_counter() - start_time
            
            # 캐시 통계
            cache_stats = processor_with_cache.get_cache_stats()
            
            processor_with_cache.cleanup()
            
            # 성능 분석
            performance_results = {
                'no_cache_time': no_cache_time,
                'first_run_time': first_run_time,
                'second_run_time': second_run_time,
                'cache_effect': first_run_time / second_run_time if second_run_time > 0 else 0,
                'cache_overhead': (first_run_time - no_cache_time) / no_cache_time * 100 if no_cache_time > 0 else 0,
                'cache_stats': cache_stats,
                'data_consistency': (
                    result_no_cache['total_processed_items'] == 
                    result_first_run['total_processed_items'] == 
                    result_second_run['total_processed_items']
                )
            }
            
            self.logger.info("✅ 캐시 성능 영향 테스트 완료")
            
        except Exception as e:
            performance_results = {
                'success': False,
                'error': str(e)
            }
        
        return performance_results
    
    def generate_quality_report(self) -> Dict[str, Any]:
        """캐시 시스템 품질 보고서 생성"""
        self.logger.info("Redis 캐시 시스템 품질 평가 시작")
        
        # 모든 테스트 실행
        redis_test = self.test_redis_connection()
        fallback_test = self.test_cache_fallback_mechanism()
        key_test = self.test_cache_key_generation()
        consistency_test = self.test_cache_data_consistency()
        performance_test = self.test_cache_performance_impact()
        
        # 종합 평가
        quality_score = 0
        max_score = 5
        
        # Redis 연결 (선택사항)
        if redis_test.get('redis_available', False):
            quality_score += 1
        
        # Fallback 메커니즘 (필수)
        if fallback_test.get('memory_only', {}).get('success', False):
            quality_score += 1
        
        # 키 생성 로직 (필수)
        if all(key_test.get(key, False) for key in ['consistency', 'parameter_sensitivity', 'modification_sensitivity']):
            quality_score += 1
        
        # 데이터 일관성 (필수)
        if all(consistency_test.get(key, False) for key in ['storage_retrieval', 'data_integrity']):
            quality_score += 1
        
        # 성능 효과 (필수)
        if performance_test.get('cache_effect', 0) > 1.5:  # 1.5배 이상 성능 향상
            quality_score += 1
        
        quality_report = {
            'overall_quality_score': quality_score,
            'max_possible_score': max_score,
            'quality_percentage': (quality_score / max_score) * 100,
            'redis_connection_test': redis_test,
            'fallback_mechanism_test': fallback_test,
            'cache_key_generation_test': key_test,
            'data_consistency_test': consistency_test,
            'performance_impact_test': performance_test,
            'recommendations': self.generate_recommendations(redis_test, fallback_test, key_test, consistency_test, performance_test)
        }
        
        return quality_report
    
    def generate_recommendations(self, redis_test, fallback_test, key_test, consistency_test, performance_test) -> List[str]:
        """개선 권장사항 생성"""
        recommendations = []
        
        if not redis_test.get('redis_available', False):
            recommendations.append("Redis 서버 설치 및 설정을 고려하여 더 나은 캐시 성능을 얻을 수 있습니다.")
        
        if not fallback_test.get('redis_fallback', {}).get('success', False):
            recommendations.append("Redis fallback 메커니즘을 개선하여 안정성을 높일 수 있습니다.")
        
        if performance_test.get('cache_effect', 0) < 2.0:
            recommendations.append("캐시 효과가 제한적입니다. 캐시 크기나 전략을 조정해보세요.")
        
        if consistency_test.get('concurrent_access', True) == False:
            recommendations.append("동시 접근 시 안정성을 개선할 필요가 있습니다.")
        
        if not recommendations:
            recommendations.append("캐시 시스템이 우수한 품질로 구현되었습니다.")
        
        return recommendations

def main():
    """Redis 캐시 품질 평가 메인 실행"""
    print("🔧 Redis 캐싱 시스템 구현 품질 평가")
    print("=" * 80)
    
    evaluator = RedisCacheQualityEvaluator()
    
    try:
        # 품질 평가 실행
        quality_report = evaluator.generate_quality_report()
        
        # 결과 출력
        print(f"\n📊 Redis 캐시 시스템 품질 평가 결과:")
        print(f"   품질 점수: {quality_report['quality_percentage']:.1f}% ({quality_report['overall_quality_score']}/{quality_report['max_possible_score']})")
        
        # 주요 테스트 결과
        print(f"\n🔍 주요 테스트 결과:")
        print(f"   Redis 연결: {'✅' if quality_report['redis_connection_test'].get('redis_available') else '⚠️ 미사용'}")
        print(f"   Fallback 메커니즘: {'✅' if quality_report['fallback_mechanism_test'].get('memory_only', {}).get('success') else '❌'}")
        print(f"   키 생성 로직: {'✅' if quality_report['cache_key_generation_test'].get('consistency') else '❌'}")
        print(f"   데이터 일관성: {'✅' if quality_report['data_consistency_test'].get('storage_retrieval') else '❌'}")
        
        # 성능 효과
        perf_test = quality_report['performance_impact_test']
        if 'cache_effect' in perf_test:
            print(f"   캐시 성능 효과: {perf_test['cache_effect']:.2f}배")
        
        # 권장사항
        print(f"\n💡 권장사항:")
        for rec in quality_report['recommendations']:
            print(f"   - {rec}")
        
        # 결과 저장
        with open('redis_cache_quality_report.json', 'w', encoding='utf-8') as f:
            json.dump(quality_report, f, indent=2, ensure_ascii=False)
        
        print(f"\n📄 상세 보고서가 'redis_cache_quality_report.json'에 저장되었습니다.")
        
    except Exception as e:
        print(f"❌ 품질 평가 실패: {e}")
        logging.error(f"품질 평가 실패: {e}")
    
    print("=" * 80)

if __name__ == "__main__":
    main()
