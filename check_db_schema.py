"""
실제 DB 스키마 확인
"""

import sqlite3
from pathlib import Path

def check_db_schema():
    """DB 스키마 확인"""
    db_dir = Path('database')
    db_files = list(db_dir.glob('*.db'))
    
    if not db_files:
        print("DB 파일이 없습니다.")
        return
    
    db_file = db_files[0]
    print(f"DB 파일: {db_file.name}")
    
    conn = sqlite3.connect(str(db_file))
    cursor = conn.cursor()
    
    # 테이블 목록 확인
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    print(f"테이블 목록: {tables}")
    
    # cells 테이블 스키마 확인
    cursor.execute("PRAGMA table_info(cells);")
    columns = cursor.fetchall()
    print(f"cells 테이블 컬럼: {columns}")
    
    # 샘플 데이터 확인
    cursor.execute("SELECT * FROM cells LIMIT 5;")
    sample_data = cursor.fetchall()
    print(f"샘플 데이터: {sample_data}")
    
    conn.close()

if __name__ == "__main__":
    check_db_schema()
