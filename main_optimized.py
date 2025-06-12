"""
최적화된 AutoCalEditor 메인 실행 파일
DB → C 코드 변환 성능 최적화 적용
"""

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

def main():
    """메인 실행 함수"""
    print("🚀 AutoCalEditor - 성능 최적화 버전")
    print("=" * 80)
    
    try:
        # 기존 Excel → DB 변환
        print("\n📊 1단계: Excel → DB 변환")
        excel_to_db_time = process_excel_to_db()
        
        # 최적화된 DB → C 코드 변환
        print("\n⚙️ 2단계: DB → C 코드 변환 (최적화 적용)")
        db_to_code_time = process_db_to_code_optimized()
        
        total_time = excel_to_db_time + db_to_code_time
        
        print(f"\n✅ 전체 처리 완료")
        print(f"   Excel → DB: {excel_to_db_time:.3f}초")
        print(f"   DB → C 코드: {db_to_code_time:.3f}초")
        print(f"   총 시간: {total_time:.3f}초")
        
    except Exception as e:
        print(f"❌ 처리 실패: {e}")
        logging.error(f"메인 처리 실패: {e}")
        return 1
    
    return 0

def process_excel_to_db():
    """Excel → DB 변환 (기존 로직)"""
    start_time = time.perf_counter()
    
    try:
        from excel_processor.excel_importer import ExcelImporter
        from data_manager.db_handler_v2 import DBHandlerV2
        
        # Excel 파일 찾기
        excel_dir = Path('excel')
        if not excel_dir.exists():
            print("   ⚠️ Excel 디렉토리가 없습니다.")
            return 0
        
        excel_files = list(excel_dir.glob('*.xlsx'))
        if not excel_files:
            print("   ⚠️ Excel 파일이 없습니다.")
            return 0
        
        print(f"   📁 Excel 파일 {len(excel_files)}개 발견")
        
        # Database 디렉토리 생성
        db_dir = Path('database')
        db_dir.mkdir(exist_ok=True)
        
        for excel_file in excel_files:
            db_name = excel_file.stem + '.db'
            db_path = db_dir / db_name
            
            # 기존 DB 파일 삭제
            if db_path.exists():
                db_path.unlink()
            
            # DB 생성 및 Excel import
            db_handler = DBHandlerV2(str(db_path))
            db_handler.connect()
            db_handler.init_tables()
            
            importer = ExcelImporter(db_handler)
            result = importer.import_excel(str(excel_file))
            
            db_handler.disconnect()
            
            print(f"   ✅ {excel_file.name} → {db_name}")
        
        return time.perf_counter() - start_time
        
    except Exception as e:
        print(f"   ❌ Excel → DB 변환 실패: {e}")
        raise

def process_db_to_code_optimized():
    """최적화된 DB → C 코드 변환"""
    start_time = time.perf_counter()
    
    try:
        # 최적화된 프로세서 import
        from production_ready_db_processor import ProductionDBProcessor, ProductionConfig
        
        # DB 파일 수집
        db_dir = Path('database')
        if not db_dir.exists():
            print("   ⚠️ Database 디렉토리가 없습니다.")
            return 0
        
        db_files = list(db_dir.glob('*.db'))
        if not db_files:
            print("   ⚠️ DB 파일이 없습니다.")
            return 0
        
        print(f"   📁 DB 파일 {len(db_files)}개 발견")
        
        # 최적화 설정
        config = ProductionConfig(
            batch_size=500,
            chunk_size=1000,
            gc_interval=4,
            enable_connection_pooling=True,
            enable_parallel_processing=True,
            max_workers=4
        )
        
        # 최적화된 프로세서로 처리
        processor = ProductionDBProcessor(config)
        
        try:
            result = processor.process_batch_production(db_files)
            
            print(f"   ✅ 처리 완료: {result['total_processed_items']:,}개 항목")
            print(f"   📊 처리 모드: {result['processing_mode']}")
            print(f"   📈 성공률: {result['files_processed']}/{len(db_files)} 파일")
            
            # 생성된 C 코드 저장 (실제 구현 시 추가)
            output_dir = Path('generated_output')
            output_dir.mkdir(exist_ok=True)
            
            # 여기에 실제 C 코드 파일 생성 로직 추가
            # (기존 코드 생성 로직과 통합)
            
            return time.perf_counter() - start_time
            
        finally:
            processor.cleanup()
        
    except Exception as e:
        print(f"   ❌ DB → C 코드 변환 실패: {e}")
        raise

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
