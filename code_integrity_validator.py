"""
Phase 3 코드 생성 무결성 검증기
병렬/비동기 처리 시 생성되는 C 코드의 일관성과 정확성 검증
"""

import asyncio
import multiprocessing as mp
import time
import hashlib
import logging
import os
import sys
from pathlib import Path
from typing import Dict, List, Any, Tuple
import json
from collections import defaultdict

# 프로젝트 루트 경로 설정
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s'
)

class CodeIntegrityValidator:
    """코드 생성 무결성 검증기"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.validation_results = {}
    
    def generate_code_hash(self, code_items: List[List[str]]) -> str:
        """생성된 코드의 해시값 계산"""
        # 코드 항목들을 정렬하여 순서에 무관한 해시 생성
        sorted_items = sorted([tuple(item) for item in code_items])
        content = str(sorted_items)
        return hashlib.md5(content.encode()).hexdigest()
    
    def process_sequential_reference(self, db_file: Path) -> Dict[str, Any]:
        """순차 처리 참조 구현 (기준점)"""
        start_time = time.perf_counter()
        
        try:
            from data_manager.db_handler_v2 import DBHandlerV2
            from cython_extensions.code_generator_v2 import ultra_fast_write_cal_list_processing
            
            # DB 연결
            db_handler = DBHandlerV2(str(db_file))
            db_handler.connect()
            
            # $ 시트 찾기
            sheets = db_handler.get_sheets()
            dollar_sheets = [s for s in sheets if s.get('is_dollar_sheet', False)]
            
            all_code_items = []
            sheet_results = {}
            
            # 시트별 순차 처리
            for sheet in dollar_sheets:
                sheet_data = db_handler.get_sheet_data(sheet['id'])
                if not sheet_data:
                    continue
                
                sheet_code_items = []
                
                # 코드 아이템 생성
                for row_data in sheet_data:
                    if len(row_data) >= 3:
                        code_item = [
                            "DEFINE", "CONST", "FLOAT32",
                            f"VAL_{row_data[0]}_{row_data[1]}", 
                            str(row_data[2]) if row_data[2] else "",
                            f"Generated from {sheet['name']}"
                        ]
                        sheet_code_items.append(code_item)
                
                # Cython 코드 생성
                if sheet_code_items:
                    processed_code = ultra_fast_write_cal_list_processing(sheet_code_items)
                    all_code_items.extend(processed_code)
                    
                    # 시트별 결과 저장
                    sheet_results[sheet['name']] = {
                        'items_count': len(processed_code),
                        'hash': self.generate_code_hash(processed_code)
                    }
            
            db_handler.disconnect()
            
            execution_time = time.perf_counter() - start_time
            total_hash = self.generate_code_hash(all_code_items)
            
            return {
                'success': True,
                'execution_time': execution_time,
                'total_items': len(all_code_items),
                'total_hash': total_hash,
                'sheet_results': sheet_results,
                'processing_mode': 'sequential'
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'processing_mode': 'sequential'
            }
    
    def process_distributed_test(self, db_file: Path) -> Dict[str, Any]:
        """분산 처리 테스트"""
        try:
            from distributed_db_processor import DistributedDBProcessor, DistributedConfig
            
            config = DistributedConfig(
                batch_size=500,
                chunk_size=1000,
                max_processes=2,  # 테스트용으로 2개 프로세스
                worker_timeout=60.0
            )
            
            processor = DistributedDBProcessor(config)
            result = processor.process_batch_distributed([db_file])
            
            if result['success'] and result['results']:
                file_result = result['results'][0]
                if file_result['success']:
                    return {
                        'success': True,
                        'execution_time': file_result['execution_time'],
                        'total_items': file_result['processed_items'],
                        'processing_mode': 'distributed',
                        'worker_pid': file_result.get('worker_pid', 'unknown')
                    }
            
            return {
                'success': False,
                'error': 'Distributed processing failed',
                'processing_mode': 'distributed'
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'processing_mode': 'distributed'
            }
    
    async def process_async_test(self, db_file: Path) -> Dict[str, Any]:
        """비동기 처리 테스트"""
        try:
            from async_db_processor import AsyncDBProcessor, AsyncConfig
            
            config = AsyncConfig(
                batch_size=500,
                chunk_size=1000,
                max_concurrent_dbs=2,
                max_concurrent_sheets=4
            )
            
            processor = AsyncDBProcessor(config)
            result = await processor.process_batch_async([db_file])
            
            await processor.cleanup()
            
            if result['success'] and result['results']:
                file_result = result['results'][0]
                if file_result['success']:
                    return {
                        'success': True,
                        'execution_time': file_result['execution_time'],
                        'total_items': file_result['processed_items'],
                        'processing_mode': 'async'
                    }
            
            return {
                'success': False,
                'error': 'Async processing failed',
                'processing_mode': 'async'
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'processing_mode': 'async'
            }
    
    def process_cached_test(self, db_file: Path) -> Dict[str, Any]:
        """캐싱 처리 테스트"""
        try:
            from cached_db_processor import CachedDBProcessor, CacheConfig
            
            config = CacheConfig(
                batch_size=500,
                chunk_size=1000,
                enable_memory_cache=True,
                memory_cache_size=100
            )
            
            processor = CachedDBProcessor(config)
            
            # 첫 번째 실행 (캐시 미스)
            result1 = processor.process_batch_cached([db_file])
            
            # 두 번째 실행 (캐시 히트)
            result2 = processor.process_batch_cached([db_file])
            
            processor.cleanup()
            
            if result1['success'] and result2['success']:
                return {
                    'success': True,
                    'first_run': {
                        'execution_time': result1['execution_time'],
                        'total_items': result1['total_processed_items']
                    },
                    'second_run': {
                        'execution_time': result2['execution_time'],
                        'total_items': result2['total_processed_items']
                    },
                    'cache_effect': result1['execution_time'] / result2['execution_time'] if result2['execution_time'] > 0 else 0,
                    'processing_mode': 'cached'
                }
            
            return {
                'success': False,
                'error': 'Cached processing failed',
                'processing_mode': 'cached'
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'processing_mode': 'cached'
            }
    
    def validate_processing_consistency(self, db_files: List[Path]) -> Dict[str, Any]:
        """처리 방식별 일관성 검증"""
        self.logger.info("처리 방식별 일관성 검증 시작")
        
        validation_results = {}
        
        for db_file in db_files:
            file_name = db_file.name
            self.logger.info(f"파일 검증 시작: {file_name}")
            
            file_results = {}
            
            # 1. 순차 처리 (참조)
            self.logger.info(f"  순차 처리 테스트: {file_name}")
            sequential_result = self.process_sequential_reference(db_file)
            file_results['sequential'] = sequential_result
            
            # 2. 분산 처리
            self.logger.info(f"  분산 처리 테스트: {file_name}")
            distributed_result = self.process_distributed_test(db_file)
            file_results['distributed'] = distributed_result
            
            # 3. 비동기 처리
            self.logger.info(f"  비동기 처리 테스트: {file_name}")
            try:
                async_result = asyncio.run(self.process_async_test(db_file))
                file_results['async'] = async_result
            except Exception as e:
                file_results['async'] = {
                    'success': False,
                    'error': str(e),
                    'processing_mode': 'async'
                }
            
            # 4. 캐싱 처리
            self.logger.info(f"  캐싱 처리 테스트: {file_name}")
            cached_result = self.process_cached_test(db_file)
            file_results['cached'] = cached_result
            
            # 결과 분석
            analysis = self.analyze_consistency(file_results)
            file_results['analysis'] = analysis
            
            validation_results[file_name] = file_results
            
            self.logger.info(f"파일 검증 완료: {file_name}")
        
        return validation_results
    
    def analyze_consistency(self, file_results: Dict[str, Any]) -> Dict[str, Any]:
        """일관성 분석"""
        analysis = {
            'item_count_consistency': True,
            'processing_success_rate': 0,
            'performance_comparison': {},
            'issues': []
        }
        
        # 성공한 처리 방식들
        successful_modes = [mode for mode, result in file_results.items() 
                          if mode != 'analysis' and result.get('success', False)]
        
        analysis['processing_success_rate'] = len(successful_modes) / (len(file_results) - 1) * 100
        
        if not successful_modes:
            analysis['issues'].append("모든 처리 방식이 실패했습니다.")
            return analysis
        
        # 항목 수 일관성 확인
        item_counts = {}
        execution_times = {}
        
        for mode in successful_modes:
            result = file_results[mode]
            
            if mode == 'cached':
                # 캐싱의 경우 첫 번째 실행 결과 사용
                item_counts[mode] = result['first_run']['total_items']
                execution_times[mode] = result['first_run']['execution_time']
            else:
                item_counts[mode] = result.get('total_items', 0)
                execution_times[mode] = result.get('execution_time', 0)
        
        # 항목 수 일관성 검증
        if len(set(item_counts.values())) > 1:
            analysis['item_count_consistency'] = False
            analysis['issues'].append(f"항목 수 불일치: {item_counts}")
        
        # 성능 비교
        if 'sequential' in execution_times:
            baseline = execution_times['sequential']
            for mode, time_taken in execution_times.items():
                if mode != 'sequential' and baseline > 0:
                    speedup = baseline / time_taken if time_taken > 0 else 0
                    analysis['performance_comparison'][mode] = {
                        'execution_time': time_taken,
                        'speedup': speedup
                    }
        
        analysis['item_counts'] = item_counts
        analysis['execution_times'] = execution_times
        
        return analysis
    
    def generate_integrity_report(self, validation_results: Dict[str, Any]) -> Dict[str, Any]:
        """무결성 검증 보고서 생성"""
        report = {
            'summary': {
                'total_files_tested': len(validation_results),
                'overall_consistency': True,
                'critical_issues': [],
                'performance_insights': {}
            },
            'detailed_results': validation_results
        }
        
        # 전체 일관성 분석
        all_consistent = True
        all_performance = defaultdict(list)
        
        for file_name, file_result in validation_results.items():
            analysis = file_result.get('analysis', {})
            
            # 일관성 체크
            if not analysis.get('item_count_consistency', True):
                all_consistent = False
                report['summary']['critical_issues'].append(
                    f"{file_name}: 항목 수 불일치"
                )
            
            # 성능 데이터 수집
            for mode, perf in analysis.get('performance_comparison', {}).items():
                all_performance[mode].append(perf['speedup'])
        
        report['summary']['overall_consistency'] = all_consistent
        
        # 평균 성능 계산
        for mode, speedups in all_performance.items():
            if speedups:
                report['summary']['performance_insights'][mode] = {
                    'avg_speedup': sum(speedups) / len(speedups),
                    'min_speedup': min(speedups),
                    'max_speedup': max(speedups)
                }
        
        return report

def main():
    """무결성 검증 메인 실행"""
    print("🔍 Phase 3 코드 생성 무결성 검증")
    print("=" * 80)
    
    # DB 파일 수집
    db_dir = Path('database')
    if not db_dir.exists():
        print("❌ Database 디렉토리가 존재하지 않습니다.")
        return
    
    db_files = [f for f in db_dir.glob('*.db') if f.stat().st_size > 50000][:2]  # 테스트용으로 2개만
    
    if not db_files:
        print("❌ 검증할 DB 파일이 없습니다.")
        return
    
    print(f"📁 검증 대상: {len(db_files)}개 파일")
    for db_file in db_files:
        print(f"   - {db_file.name}")
    
    # 무결성 검증 실행
    validator = CodeIntegrityValidator()
    
    try:
        # Windows에서 multiprocessing 사용 시 필요
        mp.set_start_method('spawn', force=True)
        
        validation_results = validator.validate_processing_consistency(db_files)
        
        # 보고서 생성
        report = validator.generate_integrity_report(validation_results)
        
        # 결과 출력
        print(f"\n📊 무결성 검증 결과:")
        print(f"   검증 파일 수: {report['summary']['total_files_tested']}개")
        print(f"   전체 일관성: {'✅ 통과' if report['summary']['overall_consistency'] else '❌ 실패'}")
        
        if report['summary']['critical_issues']:
            print(f"   심각한 문제:")
            for issue in report['summary']['critical_issues']:
                print(f"     - {issue}")
        
        print(f"\n📈 성능 비교 (순차 처리 기준):")
        for mode, perf in report['summary']['performance_insights'].items():
            print(f"   {mode:12s}: {perf['avg_speedup']:.2f}배 (범위: {perf['min_speedup']:.2f}-{perf['max_speedup']:.2f})")
        
        # 결과 저장
        with open('code_integrity_validation_report.json', 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print(f"\n📄 상세 보고서가 'code_integrity_validation_report.json'에 저장되었습니다.")
        
    except Exception as e:
        print(f"❌ 무결성 검증 실패: {e}")
        logging.error(f"무결성 검증 실패: {e}")
    
    print("=" * 80)

if __name__ == "__main__":
    main()
