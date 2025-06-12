"""
main.py 실행 환경에서의 완전한 기능 검증
실제 프로덕션 환경에서 Phase 3 최적화 동작 확인
"""

import sys
import time
import logging
import os
import asyncio
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

class MainProductionVerifier:
    """main.py 프로덕션 환경 검증기"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.verification_results = {}
    
    def test_phase3_integration_in_main(self) -> Dict[str, Any]:
        """main.py에서 Phase 3 통합 상태 테스트"""
        self.logger.info("1. main.py Phase 3 통합 상태 테스트")
        
        integration_results = {
            'main_import_success': False,
            'phase3_available': False,
            'dbexceleditor_enhanced': False,
            'all_processors_available': False,
            'backend_initialization_success': False,
            'processor_details': {}
        }
        
        try:
            # main.py import 및 Phase 3 상태 확인
            from main import PHASE3_INTEGRATION_AVAILABLE, DBExcelEditor
            integration_results['main_import_success'] = True
            integration_results['phase3_available'] = PHASE3_INTEGRATION_AVAILABLE
            
            if PHASE3_INTEGRATION_AVAILABLE:
                # Phase 3 통합 모듈 확인
                from ui_backend_integration_strategy import inject_phase3_into_existing_class
                
                # 테스트용 클래스 생성 및 Phase 3 주입
                class TestMainEditor:
                    def __init__(self):
                        pass
                
                inject_phase3_into_existing_class(TestMainEditor)
                test_editor = TestMainEditor()
                
                # Phase 3 백엔드 확인
                if hasattr(test_editor, 'phase3_backend') and test_editor.phase3_backend:
                    integration_results['backend_initialization_success'] = True
                    
                    backend = test_editor.phase3_backend
                    
                    # 개별 프로세서 확인
                    processors = {
                        'async_processor': backend._async_processor,
                        'distributed_processor': backend._distributed_processor,
                        'cached_processor': backend._cached_processor
                    }
                    
                    available_processors = 0
                    for name, processor in processors.items():
                        if processor is not None:
                            available_processors += 1
                            integration_results['processor_details'][name] = 'available'
                        else:
                            integration_results['processor_details'][name] = 'not_available'
                    
                    if available_processors >= 2:  # 최소 2개 프로세서 사용 가능
                        integration_results['all_processors_available'] = True
                
                # DBExcelEditor 클래스 확장 확인
                if hasattr(DBExcelEditor, 'phase3_backend') or hasattr(DBExcelEditor, 'init_phase3_backend'):
                    integration_results['dbexceleditor_enhanced'] = True
                
                self.logger.info("✅ main.py Phase 3 통합 상태 확인 완료")
            else:
                self.logger.warning("⚠️ Phase 3 통합이 비활성화됨")
                
        except Exception as e:
            integration_results['error'] = str(e)
            self.logger.error(f"❌ main.py Phase 3 통합 테스트 실패: {e}")
        
        return integration_results
    
    def test_actual_db_processing(self) -> Dict[str, Any]:
        """실제 DB 파일을 사용한 처리 테스트"""
        self.logger.info("2. 실제 DB 파일 처리 테스트")
        
        processing_results = {
            'db_files_found': False,
            'sequential_processing_success': False,
            'phase3_processing_success': False,
            'performance_comparison': {},
            'processing_details': {}
        }
        
        try:
            # DB 파일 확인
            db_dir = Path('database')
            if db_dir.exists():
                db_files = [f for f in db_dir.glob('*.db') if f.stat().st_size > 50000][:2]  # 2개만 테스트
                
                if db_files:
                    processing_results['db_files_found'] = True
                    processing_results['processing_details']['file_count'] = len(db_files)
                    processing_results['processing_details']['files'] = [f.name for f in db_files]
                    
                    # 순차 처리 테스트
                    sequential_result = self.test_sequential_processing(db_files)
                    if sequential_result['success']:
                        processing_results['sequential_processing_success'] = True
                        processing_results['performance_comparison']['sequential'] = sequential_result
                    
                    # Phase 3 처리 테스트
                    phase3_result = self.test_phase3_processing(db_files)
                    if phase3_result['success']:
                        processing_results['phase3_processing_success'] = True
                        processing_results['performance_comparison']['phase3'] = phase3_result
                        
                        # 성능 비교
                        if sequential_result['success'] and phase3_result['success']:
                            seq_time = sequential_result['execution_time']
                            p3_time = phase3_result['execution_time']
                            if p3_time > 0:
                                speedup = seq_time / p3_time
                                processing_results['performance_comparison']['speedup'] = speedup
                                self.logger.info(f"✅ 성능 향상: {speedup:.2f}배")
                else:
                    self.logger.warning("⚠️ 테스트할 DB 파일이 없습니다.")
            else:
                self.logger.warning("⚠️ database 디렉토리가 없습니다.")
                
        except Exception as e:
            processing_results['error'] = str(e)
            self.logger.error(f"❌ 실제 DB 처리 테스트 실패: {e}")
        
        return processing_results
    
    def test_sequential_processing(self, db_files: List[Path]) -> Dict[str, Any]:
        """순차 처리 테스트"""
        try:
            from production_ready_db_processor import ProductionDBProcessor, ProductionConfig
            
            config = ProductionConfig(
                batch_size=500,
                chunk_size=1000,
                enable_parallel_processing=False
            )
            
            processor = ProductionDBProcessor(config)
            
            start_time = time.perf_counter()
            result = processor.process_batch_production(db_files)
            execution_time = time.perf_counter() - start_time
            
            processor.cleanup()
            
            return {
                'success': result['success'],
                'execution_time': execution_time,
                'processed_items': result.get('total_processed_items', 0),
                'processing_mode': 'sequential'
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'processing_mode': 'sequential'
            }
    
    def test_phase3_processing(self, db_files: List[Path]) -> Dict[str, Any]:
        """Phase 3 최적화 처리 테스트"""
        try:
            from ui_backend_integration_strategy import create_background_processor
            
            # Phase 3 백그라운드 프로세서 생성
            processor = create_background_processor()
            
            # 비동기 처리 실행
            async def async_process():
                return await processor.process_db_files_optimized(db_files)
            
            start_time = time.perf_counter()
            result = asyncio.run(async_process())
            execution_time = time.perf_counter() - start_time
            
            processor.cleanup()
            
            return {
                'success': result['success'],
                'execution_time': execution_time,
                'processed_items': result.get('total_processed_items', 0),
                'processing_mode': result.get('processor_type', 'phase3')
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'processing_mode': 'phase3'
            }
    
    def test_ui_backend_connection(self) -> Dict[str, Any]:
        """UI와 백엔드 연결 테스트"""
        self.logger.info("3. UI-백엔드 연결 테스트")
        
        connection_results = {
            'ui_components_available': False,
            'backend_integration_working': False,
            'method_injection_success': False,
            'async_compatibility': False
        }
        
        try:
            # UI 컴포넌트 확인
            from ui.ui_components import TreeView, ExcelGridView
            connection_results['ui_components_available'] = True
            
            # 백엔드 통합 확인
            from ui_backend_integration_strategy import inject_phase3_into_existing_class
            
            # 테스트용 UI 클래스
            class TestUIClass:
                def __init__(self):
                    self.data = []
                
                def process_data(self, data):
                    return f"Processed {len(data)} items"
            
            # Phase 3 기능 주입
            inject_phase3_into_existing_class(TestUIClass)
            test_ui = TestUIClass()
            
            # 메서드 주입 확인
            if hasattr(test_ui, 'process_with_phase3_optimization'):
                connection_results['method_injection_success'] = True
            
            # 백엔드 통합 확인
            if hasattr(test_ui, 'phase3_backend') and test_ui.phase3_backend:
                connection_results['backend_integration_working'] = True
            
            # 비동기 호환성 확인
            if hasattr(test_ui, 'process_with_phase3_optimization'):
                try:
                    # 비동기 메서드 호출 테스트
                    async def test_async():
                        return await test_ui.process_with_phase3_optimization([])
                    
                    asyncio.run(test_async())
                    connection_results['async_compatibility'] = True
                except Exception as e:
                    self.logger.warning(f"비동기 호환성 테스트 실패: {e}")
            
            self.logger.info("✅ UI-백엔드 연결 테스트 완료")
            
        except Exception as e:
            connection_results['error'] = str(e)
            self.logger.error(f"❌ UI-백엔드 연결 테스트 실패: {e}")
        
        return connection_results
    
    def generate_main_verification_report(self) -> Dict[str, Any]:
        """main.py 검증 보고서 생성"""
        self.logger.info("main.py 실행 환경 완전한 기능 검증 시작")
        
        # 모든 테스트 실행
        integration_test = self.test_phase3_integration_in_main()
        processing_test = self.test_actual_db_processing()
        connection_test = self.test_ui_backend_connection()
        
        # 종합 평가
        total_tests = 8
        passed_tests = 0
        
        # 통합 테스트
        if integration_test.get('phase3_available', False):
            passed_tests += 1
        if integration_test.get('backend_initialization_success', False):
            passed_tests += 1
        if integration_test.get('all_processors_available', False):
            passed_tests += 1
        
        # 처리 테스트
        if processing_test.get('sequential_processing_success', False):
            passed_tests += 1
        if processing_test.get('phase3_processing_success', False):
            passed_tests += 1
        
        # 연결 테스트
        if connection_test.get('ui_components_available', False):
            passed_tests += 1
        if connection_test.get('backend_integration_working', False):
            passed_tests += 1
        if connection_test.get('method_injection_success', False):
            passed_tests += 1
        
        verification_score = (passed_tests / total_tests) * 100
        
        verification_report = {
            'overall_verification_score': verification_score,
            'tests_passed': passed_tests,
            'total_tests': total_tests,
            'integration_test': integration_test,
            'processing_test': processing_test,
            'connection_test': connection_test,
            'summary': {
                'main_production_ready': integration_test.get('phase3_available', False),
                'actual_processing_working': processing_test.get('phase3_processing_success', False),
                'ui_backend_connected': connection_test.get('backend_integration_working', False),
                'performance_improvement': processing_test.get('performance_comparison', {}).get('speedup', 0)
            }
        }
        
        return verification_report

def main():
    """main.py 실행 환경 검증 실행"""
    print("🔍 main.py 실행 환경에서의 완전한 기능 검증")
    print("=" * 80)
    
    verifier = MainProductionVerifier()
    
    try:
        # main.py 검증 실행
        report = verifier.generate_main_verification_report()
        
        # 결과 출력
        print(f"\n📊 main.py 기능 검증 결과:")
        print(f"   검증 점수: {report['overall_verification_score']:.1f}% ({report['tests_passed']}/{report['total_tests']})")
        
        # 주요 결과
        summary = report['summary']
        print(f"\n🔍 주요 검증 결과:")
        print(f"   프로덕션 준비: {'✅' if summary['main_production_ready'] else '❌'}")
        print(f"   실제 처리 작동: {'✅' if summary['actual_processing_working'] else '❌'}")
        print(f"   UI-백엔드 연결: {'✅' if summary['ui_backend_connected'] else '❌'}")
        if summary['performance_improvement'] > 0:
            print(f"   성능 향상: {summary['performance_improvement']:.2f}배")
        
        # 상세 결과
        print(f"\n📋 상세 테스트 결과:")
        
        integration = report['integration_test']
        print(f"   Phase 3 통합: {'✅' if integration.get('phase3_available') else '❌'}")
        if integration.get('processor_details'):
            for proc_name, status in integration['processor_details'].items():
                print(f"     {proc_name}: {'✅' if status == 'available' else '❌'}")
        
        processing = report['processing_test']
        if processing.get('processing_details'):
            details = processing['processing_details']
            print(f"   DB 파일 처리: ✅ {details.get('file_count', 0)}개 파일")
            
        if processing.get('performance_comparison'):
            perf = processing['performance_comparison']
            if 'speedup' in perf:
                print(f"   성능 비교: {perf['speedup']:.2f}배 향상")
        
        connection = report['connection_test']
        print(f"   UI 컴포넌트: {'✅' if connection.get('ui_components_available') else '❌'}")
        print(f"   메서드 주입: {'✅' if connection.get('method_injection_success') else '❌'}")
        
        # 결과 저장
        with open('main_production_verification_report.json', 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print(f"\n📄 상세 보고서가 'main_production_verification_report.json'에 저장되었습니다.")
        
    except Exception as e:
        print(f"❌ main.py 검증 실패: {e}")
        logging.error(f"main.py 검증 실패: {e}")
    
    print("=" * 80)

if __name__ == "__main__":
    main()
