"""
Cython 성능 분석 및 개선 방안 보고서 생성
"""

import os
import sys
import logging
import json
from pathlib import Path
from typing import Dict, List, Any

# 프로젝트 루트 경로 설정
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s'
)

def analyze_cython_compilation():
    """Cython 컴파일 상태 분석"""
    print("🔍 Cython 컴파일 상태 분석")
    print("="*60)
    
    cython_dir = Path('cython_extensions')
    if not cython_dir.exists():
        print("❌ cython_extensions 디렉토리가 존재하지 않습니다.")
        return {}
    
    # 예상되는 파일들
    expected_files = {
        'excel_processor_v2': {
            'pyx': 'excel_processor_v2.pyx',
            'c': 'excel_processor_v2.c', 
            'pyd': 'excel_processor_v2.cp311-win_amd64.pyd'
        },
        'data_processor': {
            'pyx': 'data_processor.pyx',
            'c': 'data_processor.c',
            'pyd': 'data_processor.cp311-win_amd64.pyd'
        },
        'code_generator_v2': {
            'pyx': 'code_generator_v2.pyx',
            'c': 'code_generator_v2.c',
            'pyd': 'code_generator_v2.cp311-win_amd64.pyd'
        },
        'regex_optimizer': {
            'pyx': 'regex_optimizer.pyx',
            'c': 'regex_optimizer.c',
            'pyd': 'regex_optimizer.cp311-win_amd64.pyd'
        }
    }
    
    compilation_status = {}
    
    for module, files in expected_files.items():
        status = {
            'source_exists': False,
            'c_compiled': False,
            'pyd_compiled': False,
            'importable': False,
            'file_sizes': {}
        }
        
        # 소스 파일 확인
        pyx_path = cython_dir / files['pyx']
        if pyx_path.exists():
            status['source_exists'] = True
            status['file_sizes']['pyx'] = pyx_path.stat().st_size
        
        # C 파일 확인
        c_path = cython_dir / files['c']
        if c_path.exists():
            status['c_compiled'] = True
            status['file_sizes']['c'] = c_path.stat().st_size
        
        # PYD 파일 확인
        pyd_path = cython_dir / files['pyd']
        if pyd_path.exists():
            status['pyd_compiled'] = True
            status['file_sizes']['pyd'] = pyd_path.stat().st_size
        
        # Import 테스트
        try:
            __import__(f'cython_extensions.{module}')
            status['importable'] = True
        except ImportError:
            status['importable'] = False
        
        compilation_status[module] = status
        
        # 상태 출력
        print(f"\n📦 {module}")
        print(f"   소스 파일: {'✅' if status['source_exists'] else '❌'}")
        print(f"   C 컴파일: {'✅' if status['c_compiled'] else '❌'}")
        print(f"   PYD 컴파일: {'✅' if status['pyd_compiled'] else '❌'}")
        print(f"   Import 가능: {'✅' if status['importable'] else '❌'}")
        
        if status['file_sizes']:
            print(f"   파일 크기:")
            for file_type, size in status['file_sizes'].items():
                print(f"     {file_type.upper()}: {size:,} bytes")
    
    return compilation_status

def analyze_performance_bottlenecks():
    """성능 병목 지점 분석"""
    print("\n🚀 성능 병목 지점 분석")
    print("="*60)
    
    # 벤치마크 결과 로드
    benchmark_file = Path('benchmark_results.json')
    if benchmark_file.exists():
        with open(benchmark_file, 'r', encoding='utf-8') as f:
            results = json.load(f)
        
        print("📊 벤치마크 결과 분석:")
        
        summary = results.get('summary', {})
        print(f"   총 테스트: {summary.get('total_tests', 0)}개")
        print(f"   성공한 테스트: {summary.get('successful_tests', 0)}개")
        print(f"   평균 성능 향상: {summary.get('average_speedup', 0):.2f}배")
        
        detailed_results = results.get('detailed_results', [])
        for result in detailed_results:
            test_name = result.get('test_name', 'Unknown')
            speedup = result.get('speedup', 0)
            python_time = result.get('python_time', 0)
            cython_time = result.get('cython_time', 0)
            
            print(f"\n   🔬 {test_name}")
            print(f"      Python: {python_time:.4f}초")
            print(f"      Cython: {cython_time:.4f}초")
            print(f"      성능 향상: {speedup:.2f}배")
            
            if speedup < 1.0:
                print(f"      ⚠️ 성능 저하 발생!")
            elif speedup < 1.5:
                print(f"      📈 미미한 성능 향상")
            else:
                print(f"      🚀 효과적인 성능 향상")
    else:
        print("❌ 벤치마크 결과 파일을 찾을 수 없습니다.")

def analyze_code_quality():
    """Cython 코드 품질 분석"""
    print("\n📝 Cython 코드 품질 분석")
    print("="*60)
    
    cython_dir = Path('cython_extensions')
    pyx_files = list(cython_dir.glob('*.pyx'))
    
    for pyx_file in pyx_files:
        print(f"\n📄 {pyx_file.name}")
        
        with open(pyx_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        lines = content.split('\n')
        total_lines = len(lines)
        
        # 최적화 지시문 확인
        optimization_directives = [
            'boundscheck=False',
            'wraparound=False', 
            'cdivision=True',
            'language_level=3'
        ]
        
        found_directives = []
        for directive in optimization_directives:
            if directive in content:
                found_directives.append(directive)
        
        # 타입 선언 확인
        type_declarations = content.count('cdef ')
        function_count = content.count('def ')
        cdef_function_count = content.count('cdef ') - content.count('cdef class')
        
        print(f"   총 라인 수: {total_lines}")
        print(f"   최적화 지시문: {len(found_directives)}/{len(optimization_directives)}")
        for directive in found_directives:
            print(f"     ✅ {directive}")
        for directive in optimization_directives:
            if directive not in found_directives:
                print(f"     ❌ {directive}")
        
        print(f"   함수 수: {function_count}")
        print(f"   타입 선언 수: {type_declarations}")
        
        # 성능 개선 제안
        suggestions = []
        if len(found_directives) < len(optimization_directives):
            suggestions.append("누락된 최적화 지시문 추가")
        if type_declarations < function_count * 2:
            suggestions.append("더 많은 타입 선언 추가")
        if 'import re' in content:
            suggestions.append("정규식 사용을 C 수준 문자열 처리로 대체")
        
        if suggestions:
            print(f"   💡 개선 제안:")
            for suggestion in suggestions:
                print(f"     • {suggestion}")

def generate_improvement_recommendations():
    """개선 방안 제시"""
    print("\n🎯 성능 개선 방안")
    print("="*60)
    
    recommendations = [
        {
            "category": "컴파일 최적화",
            "items": [
                "컴파일러 최적화 플래그 추가 (-O3, -march=native)",
                "Link Time Optimization (LTO) 활성화",
                "Profile-Guided Optimization (PGO) 적용 고려"
            ]
        },
        {
            "category": "코드 최적화", 
            "items": [
                "더 많은 cdef 타입 선언 추가",
                "Python 객체 사용 최소화",
                "메모리 뷰(memoryview) 활용",
                "정규식 대신 C 수준 문자열 처리 사용"
            ]
        },
        {
            "category": "아키텍처 개선",
            "items": [
                "Python-Cython 간 데이터 전달 최소화",
                "배치 처리 크기 최적화",
                "메모리 풀링 구현",
                "병렬 처리 도입 (OpenMP)"
            ]
        },
        {
            "category": "프로파일링 및 측정",
            "items": [
                "cProfile을 이용한 상세 프로파일링",
                "line_profiler로 라인별 성능 측정",
                "메모리 사용량 프로파일링",
                "실제 워크로드 기반 벤치마크"
            ]
        }
    ]
    
    for rec in recommendations:
        print(f"\n📋 {rec['category']}")
        for item in rec['items']:
            print(f"   • {item}")

def main():
    """메인 분석 실행"""
    print("🔬 Cython 성능 분석 및 개선 방안 보고서")
    print("="*80)
    
    # 1. 컴파일 상태 분석
    compilation_status = analyze_cython_compilation()
    
    # 2. 성능 병목 분석
    analyze_performance_bottlenecks()
    
    # 3. 코드 품질 분석
    analyze_code_quality()
    
    # 4. 개선 방안 제시
    generate_improvement_recommendations()
    
    # 5. 종합 결론
    print("\n🏁 종합 결론")
    print("="*60)
    
    # 컴파일 성공률 계산
    total_modules = len(compilation_status)
    successful_compiles = sum(1 for status in compilation_status.values() 
                            if status['pyd_compiled'] and status['importable'])
    
    compile_success_rate = (successful_compiles / total_modules * 100) if total_modules > 0 else 0
    
    print(f"📊 Cython 모듈 컴파일 성공률: {compile_success_rate:.1f}% ({successful_compiles}/{total_modules})")
    
    if compile_success_rate >= 100:
        print("✅ 모든 Cython 모듈이 성공적으로 컴파일되었습니다.")
    elif compile_success_rate >= 75:
        print("⚠️ 대부분의 Cython 모듈이 컴파일되었지만 일부 문제가 있습니다.")
    else:
        print("❌ Cython 컴파일에 심각한 문제가 있습니다.")
    
    # 벤치마크 결과 기반 결론
    benchmark_file = Path('benchmark_results.json')
    if benchmark_file.exists():
        with open(benchmark_file, 'r', encoding='utf-8') as f:
            results = json.load(f)
        
        avg_speedup = results.get('summary', {}).get('average_speedup', 0)
        
        if avg_speedup >= 2.0:
            print("🚀 Cython 최적화가 매우 효과적입니다!")
        elif avg_speedup >= 1.5:
            print("✅ Cython 최적화가 효과적으로 작동하고 있습니다.")
        elif avg_speedup >= 1.0:
            print("📈 Cython 최적화가 일부 효과를 보이고 있습니다.")
        else:
            print("⚠️ Cython 최적화 효과가 미미하거나 역효과가 발생하고 있습니다.")
    
    print("\n📄 상세한 분석 결과는 로그 파일을 참조하세요.")

if __name__ == "__main__":
    main()
