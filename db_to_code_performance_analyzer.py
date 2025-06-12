"""
DB → C 코드 변환 성능 문제 분석기
일괄 처리 vs 개별 처리 성능 비교 및 병목 지점 식별
"""

import time
import psutil
import gc
import logging
import os
import sys
from pathlib import Path
from typing import Dict, List, Any, Tuple
import json
import traceback
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
import threading

# 프로젝트 루트 경로 설정
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s'
)

class DBToCodePerformanceAnalyzer:
    """DB → C 코드 변환 성능 분석기"""
    
    def __init__(self):
        self.process = psutil.Process()
        self.analysis_results = {}
        self.db_files = []
        
    def discover_db_files(self) -> List[Path]:
        """DB 파일 발견 및 분석"""
        print("🔍 DB 파일 발견 및 분석")
        print("=" * 60)
        
        db_dir = Path('database')
        if not db_dir.exists():
            print("❌ Database 디렉토리가 존재하지 않습니다.")
            return []
        
        db_files = list(db_dir.glob('*.db'))
        print(f"📁 발견된 DB 파일: {len(db_files)}개")
        
        # DB 파일 상세 정보 분석
        for i, db_file in enumerate(db_files):
            file_size = db_file.stat().st_size
            print(f"   {i+1}. {db_file.name} ({file_size:,} bytes)")
            
            # DB 내용 간단 분석
            try:
                from data_manager.db_handler_v2 import DBHandlerV2
                db_handler = DBHandlerV2(str(db_file))
                db_handler.connect()
                
                sheets = db_handler.get_sheets()
                dollar_sheets = [s for s in sheets if s.get('is_dollar_sheet', False)]
                
                total_cells = 0
                for sheet in dollar_sheets:
                    sheet_data = db_handler.get_sheet_data(sheet['id'])
                    if sheet_data:
                        total_cells += len(sheet_data)
                
                print(f"      시트: {len(sheets)}개 ($ 시트: {len(dollar_sheets)}개)")
                print(f"      셀 데이터: {total_cells:,}개")
                
                db_handler.disconnect()
                
            except Exception as e:
                print(f"      ❌ 분석 실패: {e}")
        
        self.db_files = db_files[:5]  # 최대 5개 파일
        return self.db_files
    
    def measure_memory_and_cpu(self) -> Dict[str, float]:
        """메모리 및 CPU 사용량 측정"""
        memory_info = self.process.memory_info()
        cpu_percent = self.process.cpu_percent()
        
        return {
            'rss_mb': memory_info.rss / 1024 / 1024,
            'vms_mb': memory_info.vms / 1024 / 1024,
            'cpu_percent': cpu_percent
        }
    
    def convert_single_db_to_code(self, db_file: Path) -> Dict[str, Any]:
        """단일 DB 파일을 C 코드로 변환"""
        print(f"\n🔄 단일 변환: {db_file.name}")
        
        start_memory = self.measure_memory_and_cpu()
        start_time = time.perf_counter()
        
        try:
            from data_manager.db_handler_v2 import DBHandlerV2
            from cython_extensions.code_generator_v2 import fast_write_cal_list_processing
            
            # DB 연결
            db_handler = DBHandlerV2(str(db_file))
            db_handler.connect()
            
            # $ 시트 찾기
            sheets = db_handler.get_sheets()
            dollar_sheets = [s for s in sheets if s.get('is_dollar_sheet', False)]
            
            total_processed_items = 0
            step_times = {}
            
            # 단계별 시간 측정
            step_start = time.perf_counter()
            
            for sheet in dollar_sheets:
                sheet_data = db_handler.get_sheet_data(sheet['id'])
                if sheet_data:
                    # 코드 아이템 생성
                    code_items = []
                    for row_data in sheet_data:
                        if len(row_data) >= 3:
                            code_items.append([
                                "DEFINE", "CONST", "FLOAT32",
                                f"VAL_{row_data[0]}_{row_data[1]}", 
                                str(row_data[2]) if row_data[2] else "",
                                f"Generated from {sheet['name']}"
                            ])
                    
                    # Cython 코드 생성
                    processed_code = fast_write_cal_list_processing(code_items)
                    total_processed_items += len(processed_code)
            
            step_times['code_generation'] = time.perf_counter() - step_start
            
            # DB 연결 해제
            db_handler.disconnect()
            
            end_time = time.perf_counter()
            end_memory = self.measure_memory_and_cpu()
            
            execution_time = end_time - start_time
            memory_delta = end_memory['rss_mb'] - start_memory['rss_mb']
            
            result = {
                'success': True,
                'execution_time': execution_time,
                'processed_items': total_processed_items,
                'memory_delta_mb': memory_delta,
                'start_memory_mb': start_memory['rss_mb'],
                'end_memory_mb': end_memory['rss_mb'],
                'step_times': step_times,
                'file_name': db_file.name
            }
            
            print(f"   ✅ 완료: {execution_time:.3f}초, {total_processed_items:,}개 항목")
            print(f"   📊 메모리: {start_memory['rss_mb']:.1f}MB → {end_memory['rss_mb']:.1f}MB (+{memory_delta:.1f}MB)")
            
            return result
            
        except Exception as e:
            print(f"   ❌ 실패: {e}")
            return {
                'success': False,
                'error': str(e),
                'file_name': db_file.name
            }
    
    def convert_batch_db_to_code(self, db_files: List[Path]) -> Dict[str, Any]:
        """일괄 DB 파일을 C 코드로 변환"""
        print(f"\n🔄 일괄 변환: {len(db_files)}개 파일")
        
        start_memory = self.measure_memory_and_cpu()
        start_time = time.perf_counter()
        
        try:
            from data_manager.db_handler_v2 import DBHandlerV2
            from cython_extensions.code_generator_v2 import fast_write_cal_list_processing
            
            total_processed_items = 0
            file_results = []
            step_times = {}
            
            for i, db_file in enumerate(db_files):
                file_start_time = time.perf_counter()
                file_start_memory = self.measure_memory_and_cpu()
                
                print(f"   📁 처리 중 ({i+1}/{len(db_files)}): {db_file.name}")
                
                # DB 연결
                db_handler = DBHandlerV2(str(db_file))
                db_handler.connect()
                
                # $ 시트 찾기
                sheets = db_handler.get_sheets()
                dollar_sheets = [s for s in sheets if s.get('is_dollar_sheet', False)]
                
                file_processed_items = 0
                
                for sheet in dollar_sheets:
                    sheet_data = db_handler.get_sheet_data(sheet['id'])
                    if sheet_data:
                        # 코드 아이템 생성
                        code_items = []
                        for row_data in sheet_data:
                            if len(row_data) >= 3:
                                code_items.append([
                                    "DEFINE", "CONST", "FLOAT32",
                                    f"VAL_{row_data[0]}_{row_data[1]}", 
                                    str(row_data[2]) if row_data[2] else "",
                                    f"Generated from {sheet['name']}"
                                ])
                        
                        # Cython 코드 생성
                        processed_code = fast_write_cal_list_processing(code_items)
                        file_processed_items += len(processed_code)
                
                # DB 연결 해제
                db_handler.disconnect()
                
                file_end_time = time.perf_counter()
                file_end_memory = self.measure_memory_and_cpu()
                
                file_execution_time = file_end_time - file_start_time
                file_memory_delta = file_end_memory['rss_mb'] - file_start_memory['rss_mb']
                
                file_results.append({
                    'file_name': db_file.name,
                    'execution_time': file_execution_time,
                    'processed_items': file_processed_items,
                    'memory_delta_mb': file_memory_delta
                })
                
                total_processed_items += file_processed_items
                
                print(f"      ✅ {file_execution_time:.3f}초, {file_processed_items:,}개 항목, 메모리 +{file_memory_delta:.1f}MB")
                
                # 중간 가비지 컬렉션
                gc.collect()
            
            end_time = time.perf_counter()
            end_memory = self.measure_memory_and_cpu()
            
            execution_time = end_time - start_time
            memory_delta = end_memory['rss_mb'] - start_memory['rss_mb']
            
            result = {
                'success': True,
                'execution_time': execution_time,
                'processed_items': total_processed_items,
                'memory_delta_mb': memory_delta,
                'start_memory_mb': start_memory['rss_mb'],
                'end_memory_mb': end_memory['rss_mb'],
                'file_results': file_results,
                'files_count': len(db_files)
            }
            
            print(f"\n   ✅ 일괄 변환 완료: {execution_time:.3f}초")
            print(f"   📊 총 처리: {total_processed_items:,}개 항목")
            print(f"   📊 메모리: {start_memory['rss_mb']:.1f}MB → {end_memory['rss_mb']:.1f}MB (+{memory_delta:.1f}MB)")
            
            return result
            
        except Exception as e:
            print(f"   ❌ 일괄 변환 실패: {e}")
            return {
                'success': False,
                'error': str(e),
                'files_count': len(db_files)
            }
    
    def compare_performance(self) -> Dict[str, Any]:
        """개별 vs 일괄 처리 성능 비교"""
        print("\n📊 개별 vs 일괄 처리 성능 비교")
        print("=" * 60)
        
        if not self.db_files:
            print("❌ 분석할 DB 파일이 없습니다.")
            return {}
        
        # 개별 처리 성능 측정
        print("\n🔄 개별 처리 성능 측정")
        individual_results = []
        individual_total_time = 0
        
        for db_file in self.db_files:
            gc.collect()  # 각 파일 처리 전 가비지 컬렉션
            result = self.convert_single_db_to_code(db_file)
            if result['success']:
                individual_results.append(result)
                individual_total_time += result['execution_time']
        
        # 일괄 처리 성능 측정
        print("\n🔄 일괄 처리 성능 측정")
        gc.collect()  # 일괄 처리 전 가비지 컬렉션
        batch_result = self.convert_batch_db_to_code(self.db_files)
        
        # 성능 비교 분석
        comparison = {
            'individual_results': individual_results,
            'batch_result': batch_result,
            'performance_comparison': {}
        }
        
        if individual_results and batch_result['success']:
            individual_avg_time = individual_total_time / len(individual_results)
            batch_total_time = batch_result['execution_time']
            
            individual_total_items = sum(r['processed_items'] for r in individual_results)
            batch_total_items = batch_result['processed_items']
            
            individual_total_memory = sum(r['memory_delta_mb'] for r in individual_results)
            batch_total_memory = batch_result['memory_delta_mb']
            
            # 성능 비교 지표
            time_efficiency = individual_total_time / batch_total_time if batch_total_time > 0 else 0
            memory_efficiency = individual_total_memory / batch_total_memory if batch_total_memory > 0 else 0
            
            comparison['performance_comparison'] = {
                'individual_total_time': individual_total_time,
                'individual_avg_time': individual_avg_time,
                'batch_total_time': batch_total_time,
                'time_efficiency_ratio': time_efficiency,
                'individual_total_items': individual_total_items,
                'batch_total_items': batch_total_items,
                'individual_total_memory_mb': individual_total_memory,
                'batch_total_memory_mb': batch_total_memory,
                'memory_efficiency_ratio': memory_efficiency
            }
            
            print(f"\n📈 성능 비교 결과:")
            print(f"   개별 처리 총 시간: {individual_total_time:.3f}초")
            print(f"   일괄 처리 총 시간: {batch_total_time:.3f}초")
            print(f"   시간 효율성: {time_efficiency:.2f}배 ({'일괄이 빠름' if time_efficiency > 1 else '개별이 빠름'})")
            print(f"   메모리 효율성: {memory_efficiency:.2f}배")
            
            if time_efficiency < 1:
                performance_loss = (1 - time_efficiency) * 100
                print(f"   ⚠️ 일괄 처리 성능 저하: {performance_loss:.1f}%")
            else:
                performance_gain = (time_efficiency - 1) * 100
                print(f"   ✅ 일괄 처리 성능 향상: {performance_gain:.1f}%")
        
        return comparison

if __name__ == "__main__":
    print("🔍 DB → C 코드 변환 성능 문제 분석")
    print("=" * 80)
    
    analyzer = DBToCodePerformanceAnalyzer()
    
    # DB 파일 발견
    db_files = analyzer.discover_db_files()
    
    if not db_files:
        print("❌ 분석할 DB 파일이 없습니다.")
        sys.exit(1)
    
    # 성능 비교 실행
    comparison_results = analyzer.compare_performance()
    
    # 결과 저장
    with open('db_to_code_performance_analysis.json', 'w', encoding='utf-8') as f:
        json.dump(comparison_results, f, indent=2, ensure_ascii=False)
    
    print(f"\n📄 상세 분석 결과가 'db_to_code_performance_analysis.json'에 저장되었습니다.")
    print("=" * 80)
