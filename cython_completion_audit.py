"""
Cython 최적화 작업 완료 상태 종합 점검
Excel → DB → C 코드 변환 프로세스의 모든 측면을 검증
"""

import os
import sys
import time
import logging
import importlib
import traceback
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

class CythonCompletionAuditor:
    """Cython 최적화 완료 상태 감사"""
    
    def __init__(self):
        self.audit_results = {}
        self.cython_modules = [
            'excel_processor_v2',
            'data_processor', 
            'code_generator_v2',
            'regex_optimizer'
        ]
    
    def check_cython_implementation_coverage(self) -> Dict[str, Any]:
        """Cython 구현 범위 확인"""
        print("📋 1. Cython 구현 범위 확인")
        print("=" * 60)
        
        coverage_results = {}
        
        for module_name in self.cython_modules:
            module_info = {
                'source_exists': False,
                'c_compiled': False,
                'pyd_compiled': False,
                'importable': False,
                'functions_count': 0,
                'file_sizes': {},
                'optimization_directives': []
            }
            
            # 소스 파일 확인
            pyx_path = Path(f'cython_extensions/{module_name}.pyx')
            if pyx_path.exists():
                module_info['source_exists'] = True
                module_info['file_sizes']['pyx'] = pyx_path.stat().st_size
                
                # 최적화 지시문 확인
                with open(pyx_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                directives = [
                    'boundscheck=False',
                    'wraparound=False',
                    'cdivision=True',
                    'initializedcheck=False',
                    'nonecheck=False'
                ]
                
                for directive in directives:
                    if directive in content:
                        module_info['optimization_directives'].append(directive)
                
                # 함수 개수 확인
                module_info['functions_count'] = content.count('def ') + content.count('cdef ')
            
            # C 파일 확인
            c_path = Path(f'cython_extensions/{module_name}.c')
            if c_path.exists():
                module_info['c_compiled'] = True
                module_info['file_sizes']['c'] = c_path.stat().st_size
            
            # PYD 파일 확인
            pyd_files = list(Path('cython_extensions').glob(f'{module_name}*.pyd'))
            if pyd_files:
                module_info['pyd_compiled'] = True
                module_info['file_sizes']['pyd'] = pyd_files[0].stat().st_size
            
            # Import 테스트
            try:
                module = importlib.import_module(f'cython_extensions.{module_name}')
                module_info['importable'] = True
                
                # 주요 함수들 확인
                if hasattr(module, 'fast_process_excel_data'):
                    module_info['excel_functions'] = True
                if hasattr(module, 'fast_db_batch_processing'):
                    module_info['data_functions'] = True
                if hasattr(module, 'fast_write_cal_list_processing'):
                    module_info['code_gen_functions'] = True
                if hasattr(module, 'ultra_fast_write_cal_list_processing'):
                    module_info['ultra_code_gen_functions'] = True
                    
            except ImportError as e:
                module_info['import_error'] = str(e)
            
            coverage_results[module_name] = module_info
            
            # 결과 출력
            print(f"\n📦 {module_name}")
            print(f"   소스 파일: {'✅' if module_info['source_exists'] else '❌'}")
            print(f"   C 컴파일: {'✅' if module_info['c_compiled'] else '❌'}")
            print(f"   PYD 컴파일: {'✅' if module_info['pyd_compiled'] else '❌'}")
            print(f"   Import 가능: {'✅' if module_info['importable'] else '❌'}")
            print(f"   함수 개수: {module_info['functions_count']}")
            print(f"   최적화 지시문: {len(module_info['optimization_directives'])}/5")
            
            if module_info['file_sizes']:
                print(f"   파일 크기:")
                for file_type, size in module_info['file_sizes'].items():
                    print(f"     {file_type.upper()}: {size:,} bytes")
        
        return coverage_results
    
    def check_build_compilation_status(self) -> Dict[str, Any]:
        """빌드 및 컴파일 상태 검증"""
        print("\n🔨 2. 빌드 및 컴파일 상태 검증")
        print("=" * 60)
        
        build_status = {
            'setup_py_exists': False,
            'build_script_exists': False,
            'optimization_flags': [],
            'compiler_warnings': [],
            'build_success': True
        }
        
        # setup.py 확인
        setup_path = Path('build_scripts/setup.py')
        if setup_path.exists():
            build_status['setup_py_exists'] = True
            
            with open(setup_path, 'r', encoding='utf-8') as f:
                setup_content = f.read()
            
            # 최적화 플래그 확인
            optimization_flags = ['/O2', '/Ot', '/Oy', '/GL', '/LTCG']
            for flag in optimization_flags:
                if flag in setup_content:
                    build_status['optimization_flags'].append(flag)
        
        # 빌드 스크립트 확인
        build_script_path = Path('build_scripts/build_cython.py')
        if build_script_path.exists():
            build_status['build_script_exists'] = True
        
        # 최근 빌드 로그 확인 (있다면)
        log_files = list(Path('.').glob('*build*.log'))
        if log_files:
            latest_log = max(log_files, key=lambda x: x.stat().st_mtime)
            try:
                with open(latest_log, 'r', encoding='utf-8') as f:
                    log_content = f.read()
                    
                # 경고 메시지 추출
                if 'warning' in log_content.lower():
                    build_status['compiler_warnings'] = ['컴파일러 경고 발견']
                    
            except Exception:
                pass
        
        print(f"setup.py 존재: {'✅' if build_status['setup_py_exists'] else '❌'}")
        print(f"빌드 스크립트 존재: {'✅' if build_status['build_script_exists'] else '❌'}")
        print(f"최적화 플래그: {len(build_status['optimization_flags'])}/5")
        for flag in build_status['optimization_flags']:
            print(f"  ✅ {flag}")
        
        return build_status
    
    def check_performance_test_results(self) -> Dict[str, Any]:
        """성능 테스트 결과 종합"""
        print("\n🚀 3. 성능 테스트 결과 종합")
        print("=" * 60)
        
        performance_results = {
            'benchmark_files_exist': False,
            'latest_results': {},
            'target_achievement': {}
        }
        
        # 벤치마크 결과 파일 확인
        result_files = [
            'benchmark_results.json',
            'real_world_benchmark_results.json',
            'final_benchmark_results.json'
        ]
        
        for result_file in result_files:
            if Path(result_file).exists():
                performance_results['benchmark_files_exist'] = True
                try:
                    with open(result_file, 'r', encoding='utf-8') as f:
                        results = json.load(f)
                        performance_results['latest_results'][result_file] = results
                except Exception as e:
                    print(f"⚠️ {result_file} 읽기 실패: {e}")
        
        # 간단한 성능 테스트 실행
        try:
            test_data = []
            for i in range(1000):
                test_data.append([
                    "DEFINE", "CONST", "FLOAT32", 
                    f"TEST_{i}", str(i * 1.5), f"Test {i}"
                ])
            
            # Python 버전 (참조)
            start_time = time.perf_counter()
            python_result = self.python_reference_processing(test_data)
            python_time = time.perf_counter() - start_time
            
            # Cython 버전들 테스트
            modules_performance = {}
            
            # Excel 처리
            try:
                from cython_extensions.excel_processor_v2 import fast_process_excel_data
                start_time = time.perf_counter()
                excel_result = fast_process_excel_data(test_data)
                excel_time = time.perf_counter() - start_time
                modules_performance['excel_processor'] = {
                    'time': excel_time,
                    'speedup': python_time / excel_time if excel_time > 0 else 0
                }
            except Exception as e:
                modules_performance['excel_processor'] = {'error': str(e)}
            
            # 코드 생성
            try:
                from cython_extensions.code_generator_v2 import fast_write_cal_list_processing
                start_time = time.perf_counter()
                code_result = fast_write_cal_list_processing(test_data)
                code_time = time.perf_counter() - start_time
                modules_performance['code_generator'] = {
                    'time': code_time,
                    'speedup': python_time / code_time if code_time > 0 else 0
                }
                
                # 목표 달성 여부 확인 (1.5배 이상)
                if code_time > 0:
                    speedup = python_time / code_time
                    performance_results['target_achievement']['code_generator'] = {
                        'target': 1.5,
                        'achieved': speedup,
                        'success': speedup >= 1.5
                    }
                    
            except Exception as e:
                modules_performance['code_generator'] = {'error': str(e)}
            
            performance_results['current_performance'] = modules_performance
            
        except Exception as e:
            print(f"⚠️ 성능 테스트 실행 실패: {e}")
        
        # 결과 출력
        if 'current_performance' in performance_results:
            for module, perf in performance_results['current_performance'].items():
                if 'speedup' in perf:
                    print(f"📈 {module}: {perf['speedup']:.2f}배 빠름")
                    if perf['speedup'] >= 1.5:
                        print(f"   ✅ 목표 달성 (1.5배 이상)")
                    else:
                        print(f"   ⚠️ 목표 미달성")
                else:
                    print(f"❌ {module}: 테스트 실패")
        
        return performance_results
    
    def python_reference_processing(self, data):
        """Python 참조 구현"""
        result = []
        for item in data:
            if item and len(item) >= 6:
                result.append([
                    item[0] or "", item[1] or "", item[2] or "",
                    item[3] or "", item[4] or "", item[5] or ""
                ])
        return result
    
    def check_functional_accuracy(self) -> Dict[str, Any]:
        """기능 정확성 검증"""
        print("\n✅ 4. 기능 정확성 검증")
        print("=" * 60)
        
        accuracy_results = {
            'output_consistency': {},
            'real_file_processing': {},
            'generated_code_quality': {}
        }
        
        # 출력 일치성 확인
        test_cases = [
            # 기본 케이스
            [["DEFINE", "CONST", "FLOAT32", "TEST_VAL", "123.45", "Test value"]],
            # 빈 값 케이스
            [["DEFINE", "", "INT32", "EMPTY", "", ""]],
            # 복잡한 케이스
            [["DEFINE", "CONST", "FLOAT32", "COMPLEX", "0.5", "Complex /* comment */ value"]]
        ]
        
        for i, test_case in enumerate(test_cases):
            try:
                # Python 결과
                python_result = self.python_reference_processing(test_case)
                
                # Cython 결과
                from cython_extensions.code_generator_v2 import fast_write_cal_list_processing
                cython_result = fast_write_cal_list_processing(test_case)
                
                # 일치성 확인
                is_consistent = (len(python_result) == len(cython_result))
                if is_consistent and python_result and cython_result:
                    is_consistent = (python_result[0] == cython_result[0])
                
                accuracy_results['output_consistency'][f'test_case_{i+1}'] = {
                    'consistent': is_consistent,
                    'python_length': len(python_result),
                    'cython_length': len(cython_result)
                }
                
                print(f"테스트 케이스 {i+1}: {'✅ 일치' if is_consistent else '❌ 불일치'}")
                
            except Exception as e:
                accuracy_results['output_consistency'][f'test_case_{i+1}'] = {
                    'error': str(e)
                }
                print(f"테스트 케이스 {i+1}: ❌ 오류 - {e}")
        
        # 실제 파일 처리 확인
        excel_dir = Path('excel')
        if excel_dir.exists():
            excel_files = list(excel_dir.glob('*.xlsx'))
            if excel_files:
                print(f"📁 Excel 파일 {len(excel_files)}개 발견")
                accuracy_results['real_file_processing']['excel_files_found'] = len(excel_files)
            else:
                print("📁 Excel 파일 없음")
        
        # 생성된 C 코드 확인
        output_dir = Path('generated_output')
        if output_dir.exists():
            c_files = list(output_dir.glob('**/*.c'))
            if c_files:
                print(f"📄 생성된 C 파일 {len(c_files)}개 발견")
                accuracy_results['generated_code_quality']['c_files_count'] = len(c_files)
                
                # 최근 생성된 파일 확인
                if c_files:
                    latest_c_file = max(c_files, key=lambda x: x.stat().st_mtime)
                    file_size = latest_c_file.stat().st_size
                    print(f"📄 최근 C 파일: {latest_c_file.name} ({file_size:,} bytes)")
                    accuracy_results['generated_code_quality']['latest_file'] = {
                        'name': latest_c_file.name,
                        'size': file_size
                    }
            else:
                print("📄 생성된 C 파일 없음")
        
        return accuracy_results
    
    def generate_completion_report(self) -> Dict[str, Any]:
        """완료 상태 종합 보고서 생성"""
        print("\n📊 5. 완료 상태 종합 보고서")
        print("=" * 60)
        
        # 모든 검사 실행
        coverage = self.check_cython_implementation_coverage()
        build_status = self.check_build_compilation_status()
        performance = self.check_performance_test_results()
        accuracy = self.check_functional_accuracy()
        
        # 종합 평가
        total_modules = len(self.cython_modules)
        compiled_modules = sum(1 for m in coverage.values() if m['pyd_compiled'] and m['importable'])
        
        completion_score = {
            'implementation_coverage': (compiled_modules / total_modules) * 100,
            'build_success': build_status['setup_py_exists'] and build_status['build_script_exists'],
            'performance_target_met': False,
            'functional_accuracy': True
        }
        
        # 성능 목표 달성 확인
        if 'target_achievement' in performance and 'code_generator' in performance['target_achievement']:
            completion_score['performance_target_met'] = performance['target_achievement']['code_generator']['success']
        
        # 기능 정확성 확인
        if 'output_consistency' in accuracy:
            consistency_results = [r.get('consistent', False) for r in accuracy['output_consistency'].values() if 'consistent' in r]
            if consistency_results:
                completion_score['functional_accuracy'] = all(consistency_results)
        
        # 최종 완료율 계산
        completion_percentage = (
            (completion_score['implementation_coverage'] / 100) * 0.3 +
            (1 if completion_score['build_success'] else 0) * 0.2 +
            (1 if completion_score['performance_target_met'] else 0) * 0.3 +
            (1 if completion_score['functional_accuracy'] else 0) * 0.2
        ) * 100
        
        print(f"\n🎯 Cython 최적화 완료율: {completion_percentage:.1f}%")
        print(f"📦 모듈 구현: {completion_score['implementation_coverage']:.1f}% ({compiled_modules}/{total_modules})")
        print(f"🔨 빌드 성공: {'✅' if completion_score['build_success'] else '❌'}")
        print(f"🚀 성능 목표: {'✅' if completion_score['performance_target_met'] else '❌'}")
        print(f"✅ 기능 정확성: {'✅' if completion_score['functional_accuracy'] else '❌'}")
        
        # 종합 결과 저장
        final_report = {
            'completion_percentage': completion_percentage,
            'completion_score': completion_score,
            'coverage_details': coverage,
            'build_details': build_status,
            'performance_details': performance,
            'accuracy_details': accuracy,
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
        }
        
        with open('cython_completion_audit_report.json', 'w', encoding='utf-8') as f:
            json.dump(final_report, f, indent=2, ensure_ascii=False)
        
        return final_report

if __name__ == "__main__":
    print("🔍 Cython 최적화 작업 완료 상태 종합 점검")
    print("=" * 80)
    
    auditor = CythonCompletionAuditor()
    final_report = auditor.generate_completion_report()
    
    print(f"\n📄 상세 보고서가 'cython_completion_audit_report.json'에 저장되었습니다.")
    print("=" * 80)
