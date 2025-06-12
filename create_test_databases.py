"""
테스트용 DB 파일들 생성
Excel 파일들을 DB로 변환하여 성능 분석용 데이터 준비
"""

import os
import sys
import time
import logging
from pathlib import Path

# 프로젝트 루트 경로 설정
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s'
)

def create_test_databases():
    """Excel 파일들을 DB로 변환하여 테스트 DB 생성"""
    print("🔄 테스트용 DB 파일 생성")
    print("=" * 60)
    
    # Excel 파일 확인
    excel_dir = Path('excel')
    if not excel_dir.exists():
        print("❌ Excel 디렉토리가 존재하지 않습니다.")
        return []
    
    excel_files = list(excel_dir.glob('*.xlsx'))
    if not excel_files:
        print("❌ Excel 파일이 없습니다.")
        return []
    
    print(f"📁 발견된 Excel 파일: {len(excel_files)}개")
    
    # Database 디렉토리 생성
    db_dir = Path('database')
    db_dir.mkdir(exist_ok=True)
    
    created_dbs = []
    
    try:
        from excel_processor.excel_importer import ExcelImporter
        from data_manager.db_handler_v2 import DBHandlerV2
        
        for i, excel_file in enumerate(excel_files):
            print(f"\n📊 변환 중 ({i+1}/{len(excel_files)}): {excel_file.name}")
            
            # DB 파일명 생성
            db_name = excel_file.stem + '.db'
            db_path = db_dir / db_name
            
            # 기존 DB 파일 삭제
            if db_path.exists():
                os.remove(db_path)
            
            try:
                # DB 생성 및 초기화
                db_handler = DBHandlerV2(str(db_path))
                db_handler.connect()
                db_handler.init_tables()
                
                # Excel import
                importer = ExcelImporter(db_handler)
                result = importer.import_excel(str(excel_file))
                
                # 생성된 데이터 확인
                sheets = db_handler.get_sheets()
                dollar_sheets = [s for s in sheets if s.get('is_dollar_sheet', False)]
                
                total_cells = 0
                for sheet in dollar_sheets:
                    sheet_data = db_handler.get_sheet_data(sheet['id'])
                    if sheet_data:
                        total_cells += len(sheet_data)
                
                db_handler.disconnect()
                
                file_size = db_path.stat().st_size
                
                print(f"   ✅ 생성 완료: {db_name}")
                print(f"      파일 크기: {file_size:,} bytes")
                print(f"      시트: {len(sheets)}개 ($ 시트: {len(dollar_sheets)}개)")
                print(f"      셀 데이터: {total_cells:,}개")
                
                created_dbs.append({
                    'file_path': db_path,
                    'file_name': db_name,
                    'file_size': file_size,
                    'sheets_count': len(sheets),
                    'dollar_sheets_count': len(dollar_sheets),
                    'cells_count': total_cells
                })
                
            except Exception as e:
                print(f"   ❌ 변환 실패: {e}")
                if db_path.exists():
                    os.remove(db_path)
    
    except ImportError as e:
        print(f"❌ 모듈 import 실패: {e}")
        return []
    
    print(f"\n✅ 총 {len(created_dbs)}개 DB 파일 생성 완료")
    return created_dbs

def create_large_test_database():
    """대용량 테스트용 DB 생성"""
    print("\n🔄 대용량 테스트 DB 생성")
    print("=" * 60)
    
    try:
        from data_manager.db_handler_v2 import DBHandlerV2
        
        # 대용량 테스트 DB 생성
        large_db_path = Path('database') / 'large_test.db'
        if large_db_path.exists():
            os.remove(large_db_path)
        
        db_handler = DBHandlerV2(str(large_db_path))
        db_handler.connect()
        db_handler.init_tables()
        
        # 대용량 시트 생성
        sheet_id = db_handler.create_sheet_v2("$(LargeTest)Sheet", is_dollar_sheet=True, source_file="large_test.xlsx")
        
        # 대량 데이터 생성 (10,000개 셀)
        large_data = []
        for i in range(10000):
            large_data.append((i % 100, i % 50, f"LARGE_VALUE_{i}"))
        
        # 배치 insert
        db_handler.batch_insert_cells(sheet_id, large_data)
        
        db_handler.disconnect()
        
        file_size = large_db_path.stat().st_size
        print(f"✅ 대용량 테스트 DB 생성 완료")
        print(f"   파일 크기: {file_size:,} bytes")
        print(f"   데이터: {len(large_data):,}개 셀")
        
        return {
            'file_path': large_db_path,
            'file_name': 'large_test.db',
            'file_size': file_size,
            'cells_count': len(large_data)
        }
        
    except Exception as e:
        print(f"❌ 대용량 테스트 DB 생성 실패: {e}")
        return None

def create_synthetic_databases(count: int = 3):
    """합성 테스트 DB 파일들 생성"""
    print(f"\n🔄 합성 테스트 DB {count}개 생성")
    print("=" * 60)
    
    try:
        from data_manager.db_handler_v2 import DBHandlerV2
        
        synthetic_dbs = []
        
        for i in range(count):
            db_name = f'synthetic_test_{i+1}.db'
            db_path = Path('database') / db_name
            
            if db_path.exists():
                os.remove(db_path)
            
            db_handler = DBHandlerV2(str(db_path))
            db_handler.connect()
            db_handler.init_tables()
            
            # 다양한 크기의 시트 생성
            sheets_data = []
            
            # 작은 시트
            small_sheet_id = db_handler.create_sheet_v2(f"$(Small)Sheet_{i}", is_dollar_sheet=True, source_file=f"synthetic_{i}.xlsx")
            small_data = [(j % 10, j % 5, f"SMALL_{j}") for j in range(100)]
            db_handler.batch_insert_cells(small_sheet_id, small_data)
            sheets_data.extend(small_data)
            
            # 중간 시트
            medium_sheet_id = db_handler.create_sheet_v2(f"$(Medium)Sheet_{i}", is_dollar_sheet=True, source_file=f"synthetic_{i}.xlsx")
            medium_data = [(j % 20, j % 10, f"MEDIUM_{j}") for j in range(1000)]
            db_handler.batch_insert_cells(medium_sheet_id, medium_data)
            sheets_data.extend(medium_data)
            
            # 큰 시트 (일부 DB에만)
            if i % 2 == 0:
                large_sheet_id = db_handler.create_sheet_v2(f"$(Large)Sheet_{i}", is_dollar_sheet=True, source_file=f"synthetic_{i}.xlsx")
                large_data = [(j % 50, j % 25, f"LARGE_{j}") for j in range(5000)]
                db_handler.batch_insert_cells(large_sheet_id, large_data)
                sheets_data.extend(large_data)
            
            db_handler.disconnect()
            
            file_size = db_path.stat().st_size
            
            print(f"   ✅ {db_name} 생성 완료")
            print(f"      파일 크기: {file_size:,} bytes")
            print(f"      데이터: {len(sheets_data):,}개 셀")
            
            synthetic_dbs.append({
                'file_path': db_path,
                'file_name': db_name,
                'file_size': file_size,
                'cells_count': len(sheets_data)
            })
        
        return synthetic_dbs
        
    except Exception as e:
        print(f"❌ 합성 테스트 DB 생성 실패: {e}")
        return []

if __name__ == "__main__":
    print("🔄 테스트용 DB 파일들 생성")
    print("=" * 80)
    
    all_created_dbs = []
    
    # 1. Excel 파일들을 DB로 변환
    excel_dbs = create_test_databases()
    all_created_dbs.extend(excel_dbs)
    
    # 2. 대용량 테스트 DB 생성
    large_db = create_large_test_database()
    if large_db:
        all_created_dbs.append(large_db)
    
    # 3. 합성 테스트 DB들 생성
    synthetic_dbs = create_synthetic_databases(3)
    all_created_dbs.extend(synthetic_dbs)
    
    print(f"\n📊 생성된 DB 파일 요약")
    print("=" * 60)
    
    total_size = 0
    total_cells = 0
    
    for db_info in all_created_dbs:
        print(f"📁 {db_info['file_name']}")
        print(f"   크기: {db_info['file_size']:,} bytes")
        print(f"   셀: {db_info.get('cells_count', 0):,}개")
        
        total_size += db_info['file_size']
        total_cells += db_info.get('cells_count', 0)
    
    print(f"\n✅ 총 {len(all_created_dbs)}개 DB 파일 생성")
    print(f"📊 총 크기: {total_size:,} bytes")
    print(f"📊 총 데이터: {total_cells:,}개 셀")
    print("=" * 80)
