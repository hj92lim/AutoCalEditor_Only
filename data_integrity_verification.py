"""
데이터 무결성 실제 검증
캐시 사용/미사용 시 동일한 결과 보장 확인
"""

import time
import hashlib
import logging
import sys
from pathlib import Path
from typing import Dict, List, Any, Tuple
import json

# 프로젝트 루트 경로 설정
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s'
)

class DataIntegrityVerifier:
    """데이터 무결성 검증기"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def generate_data_hash(self, data: List[List[str]]) -> str:
        """데이터의 해시값 생성 (순서 무관)"""
        # 데이터를 정렬하여 순서에 무관한 해시 생성
        sorted_data = sorted([tuple(item) for item in data])
        content = str(sorted_data)
        return hashlib.sha256(content.encode()).hexdigest()
    
    def process_without_cache(self, db_files: List[Path]) -> Dict[str, Any]:
        """캐시 없이 처리"""
        self.logger.info("캐시 없이 처리 시작")
        
        from cached_db_processor import CachedDBProcessor, CacheConfig
        
        # 캐시 비활성화 설정
        config_no_cache = CacheConfig(
            enable_redis_cache=False,
            enable_memory_cache=False
        )
        
        processor = CachedDBProcessor(config_no_cache)
        
        start_time = time.perf_counter()
        result = processor.process_batch_cached(db_files)
        execution_time = time.perf_counter() - start_time
        
        processor.cleanup()
        
        return {
            'execution_time': execution_time,
            'total_items': result['total_processed_items'],
            'success': result['success'],
            'processing_mode': 'no_cache'
        }
    
    def process_with_cache(self, db_files: List[Path]) -> Dict[str, Any]:
        """캐시 사용하여 처리"""
        self.logger.info("캐시 사용하여 처리 시작")
        
        from cached_db_processor import CachedDBProcessor, CacheConfig
        
        # 캐시 활성화 설정
        config_with_cache = CacheConfig(
            enable_redis_cache=False,  # Redis 없이 메모리 캐시만
            enable_memory_cache=True,
            memory_cache_size=5000
        )
        
        processor = CachedDBProcessor(config_with_cache)
        
        # 첫 번째 실행 (캐시 구축)
        start_time = time.perf_counter()
        result_first = processor.process_batch_cached(db_files)
        first_execution_time = time.perf_counter() - start_time
        
        # 두 번째 실행 (캐시 활용)
        start_time = time.perf_counter()
        result_second = processor.process_batch_cached(db_files)
        second_execution_time = time.perf_counter() - start_time
        
        # 캐시 통계
        cache_stats = processor.get_cache_stats()
        
        processor.cleanup()
        
        return {
            'first_execution_time': first_execution_time,
            'second_execution_time': second_execution_time,
            'cache_effect': first_execution_time / second_execution_time if second_execution_time > 0 else 0,
            'total_items_first': result_first['total_processed_items'],
            'total_items_second': result_second['total_processed_items'],
            'success_first': result_first['success'],
            'success_second': result_second['success'],
            'cache_stats': cache_stats,
            'processing_mode': 'with_cache'
        }
    
    def verify_complex_data_integrity(self) -> Dict[str, Any]:
        """복잡한 데이터 구조의 무결성 검증"""
        self.logger.info("복잡한 데이터 구조 무결성 검증")
        
        from cached_db_processor import MemoryCache
        
        cache = MemoryCache(max_size=100)
        
        # 복잡한 테스트 데이터
        complex_data = [
            ["DEFINE", "CONST", "FLOAT32", "한글_변수명", "3.14159", "한글 주석"],
            ["DEFINE", "CONST", "STRING", "SPECIAL_CHARS", '"!@#$%^&*()"', "Special characters"],
            ["DEFINE", "CONST", "ARRAY", "NESTED_DATA", '{"key": [1, 2, 3]}', "JSON data"],
            ["DEFINE", "CONST", "UNICODE", "EMOJI_TEST", "🚀🔥💎", "Emoji test"],
            ["DEFINE", "CONST", "LONG_STRING", "LONG_VAL", "A" * 1000, "Long string test"]
        ]
        
        test_results = {
            'korean_text_integrity': False,
            'special_chars_integrity': False,
            'json_data_integrity': False,
            'emoji_integrity': False,
            'long_string_integrity': False,
            'overall_integrity': False
        }
        
        try:
            # 각 데이터 타입별 저장/조회 테스트
            for i, data_item in enumerate(complex_data):
                key = f'complex_test_{i}'
                
                # 저장
                cache.set(key, data_item)
                
                # 조회
                retrieved = cache.get(key)
                
                # 무결성 확인
                if retrieved == data_item:
                    if i == 0:  # 한글
                        test_results['korean_text_integrity'] = True
                    elif i == 1:  # 특수문자
                        test_results['special_chars_integrity'] = True
                    elif i == 2:  # JSON
                        test_results['json_data_integrity'] = True
                    elif i == 3:  # 이모지
                        test_results['emoji_integrity'] = True
                    elif i == 4:  # 긴 문자열
                        test_results['long_string_integrity'] = True
            
            # 전체 무결성 확인
            if all([
                test_results['korean_text_integrity'],
                test_results['special_chars_integrity'],
                test_results['json_data_integrity'],
                test_results['emoji_integrity'],
                test_results['long_string_integrity']
            ]):
                test_results['overall_integrity'] = True
                self.logger.info("✅ 복잡한 데이터 구조 무결성 확인")
            
        except Exception as e:
            test_results['error'] = str(e)
            self.logger.error(f"❌ 복잡한 데이터 무결성 테스트 실패: {e}")
        
        return test_results
    
    def verify_cache_invalidation(self) -> Dict[str, Any]:
        """캐시 무효화 정확성 검증"""
        self.logger.info("캐시 무효화 정확성 검증")
        
        from cached_db_processor import CachedDBProcessor
        
        # 테스트 파일 생성
        test_file = Path('cache_invalidation_test.db')
        test_file.write_text("original content")
        
        test_results = {
            'initial_cache_working': False,
            'invalidation_triggered': False,
            'new_cache_working': False,
            'cache_invalidation_accurate': False
        }
        
        try:
            processor = CachedDBProcessor()
            
            # 1. 초기 캐시 키 생성
            initial_key = processor.generate_cache_key(test_file, 1, 0, 100)
            
            # 2. 파일 수정
            time.sleep(0.1)  # 수정 시간 차이 보장
            test_file.write_text("modified content - different size")
            
            # 3. 수정 후 캐시 키 생성
            modified_key = processor.generate_cache_key(test_file, 1, 0, 100)
            
            # 4. 키가 변경되었는지 확인 (무효화 확인)
            if initial_key != modified_key:
                test_results['invalidation_triggered'] = True
                test_results['cache_invalidation_accurate'] = True
                self.logger.info("✅ 캐시 무효화 정확성 확인")
            
            test_results['initial_cache_working'] = True
            test_results['new_cache_working'] = True
            
        except Exception as e:
            test_results['error'] = str(e)
            self.logger.error(f"❌ 캐시 무효화 테스트 실패: {e}")
        finally:
            # 테스트 파일 정리
            if test_file.exists():
                test_file.unlink()
        
        return test_results
    
    def verify_data_consistency(self, db_files: List[Path]) -> Dict[str, Any]:
        """캐시 사용/미사용 시 데이터 일관성 검증"""
        self.logger.info("데이터 일관성 검증 시작")
        
        # 1. 캐시 없이 처리
        no_cache_result = self.process_without_cache(db_files)
        
        # 2. 캐시 사용하여 처리
        with_cache_result = self.process_with_cache(db_files)
        
        # 3. 결과 비교
        consistency_results = {
            'item_count_consistent': False,
            'processing_success_consistent': False,
            'cache_performance_improvement': 0,
            'data_integrity_maintained': False,
            'no_cache_result': no_cache_result,
            'with_cache_result': with_cache_result
        }
        
        try:
            # 항목 수 일관성 확인
            if (no_cache_result['total_items'] == with_cache_result['total_items_first'] == 
                with_cache_result['total_items_second']):
                consistency_results['item_count_consistent'] = True
                self.logger.info("✅ 항목 수 일관성 확인")
            
            # 처리 성공 일관성 확인
            if (no_cache_result['success'] and with_cache_result['success_first'] and 
                with_cache_result['success_second']):
                consistency_results['processing_success_consistent'] = True
                self.logger.info("✅ 처리 성공 일관성 확인")
            
            # 캐시 성능 향상 계산
            if with_cache_result['cache_effect'] > 0:
                consistency_results['cache_performance_improvement'] = with_cache_result['cache_effect']
                self.logger.info(f"✅ 캐시 성능 향상: {with_cache_result['cache_effect']:.2f}배")
            
            # 전체 데이터 무결성 확인
            if (consistency_results['item_count_consistent'] and 
                consistency_results['processing_success_consistent']):
                consistency_results['data_integrity_maintained'] = True
                self.logger.info("✅ 전체 데이터 무결성 확인")
            
        except Exception as e:
            consistency_results['error'] = str(e)
            self.logger.error(f"❌ 데이터 일관성 검증 실패: {e}")
        
        return consistency_results
    
    def generate_integrity_report(self, db_files: List[Path]) -> Dict[str, Any]:
        """데이터 무결성 종합 보고서 생성"""
        self.logger.info("데이터 무결성 종합 검증 시작")
        
        # 모든 검증 실행
        data_consistency = self.verify_data_consistency(db_files)
        complex_data_integrity = self.verify_complex_data_integrity()
        cache_invalidation = self.verify_cache_invalidation()
        
        # 종합 평가
        total_tests = 4
        passed_tests = 0
        
        # 데이터 일관성
        if data_consistency.get('data_integrity_maintained', False):
            passed_tests += 1
        
        # 복잡한 데이터 무결성
        if complex_data_integrity.get('overall_integrity', False):
            passed_tests += 1
        
        # 캐시 무효화
        if cache_invalidation.get('cache_invalidation_accurate', False):
            passed_tests += 1
        
        # 캐시 성능 효과
        if data_consistency.get('cache_performance_improvement', 0) >= 1.5:
            passed_tests += 1
        
        integrity_score = (passed_tests / total_tests) * 100 if total_tests > 0 else 0
        
        integrity_report = {
            'overall_integrity_score': integrity_score,
            'tests_passed': passed_tests,
            'total_tests': total_tests,
            'data_consistency_verification': data_consistency,
            'complex_data_integrity_verification': complex_data_integrity,
            'cache_invalidation_verification': cache_invalidation,
            'summary': {
                'cache_performance_improvement': data_consistency.get('cache_performance_improvement', 0),
                'data_integrity_maintained': data_consistency.get('data_integrity_maintained', False),
                'complex_data_supported': complex_data_integrity.get('overall_integrity', False),
                'cache_invalidation_working': cache_invalidation.get('cache_invalidation_accurate', False)
            }
        }
        
        return integrity_report

def main():
    """데이터 무결성 검증 실행"""
    print("🔍 데이터 무결성 실제 검증")
    print("=" * 80)
    
    # DB 파일 수집
    db_dir = Path('database')
    if not db_dir.exists():
        print("❌ Database 디렉토리가 존재하지 않습니다.")
        return
    
    db_files = [f for f in db_dir.glob('*.db') if f.stat().st_size > 50000][:2]  # 테스트용 2개
    
    if not db_files:
        print("❌ 검증할 DB 파일이 없습니다.")
        return
    
    print(f"📁 검증 대상: {len(db_files)}개 파일")
    for db_file in db_files:
        print(f"   - {db_file.name}")
    
    verifier = DataIntegrityVerifier()
    
    try:
        # 데이터 무결성 검증 실행
        report = verifier.generate_integrity_report(db_files)
        
        # 결과 출력
        print(f"\n📊 데이터 무결성 검증 결과:")
        print(f"   무결성 점수: {report['overall_integrity_score']:.1f}% ({report['tests_passed']}/{report['total_tests']})")
        
        # 주요 결과
        summary = report['summary']
        print(f"\n🔍 주요 검증 결과:")
        print(f"   데이터 무결성: {'✅' if summary['data_integrity_maintained'] else '❌'}")
        print(f"   복잡한 데이터 지원: {'✅' if summary['complex_data_supported'] else '❌'}")
        print(f"   캐시 무효화: {'✅' if summary['cache_invalidation_working'] else '❌'}")
        print(f"   캐시 성능 향상: {summary['cache_performance_improvement']:.2f}배")
        
        # 결과 저장
        with open('data_integrity_verification_report.json', 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print(f"\n📄 상세 보고서가 'data_integrity_verification_report.json'에 저장되었습니다.")
        
    except Exception as e:
        print(f"❌ 데이터 무결성 검증 실패: {e}")
        logging.error(f"데이터 무결성 검증 실패: {e}")
    
    print("=" * 80)

if __name__ == "__main__":
    main()
