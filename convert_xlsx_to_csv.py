import os
import pandas as pd
from pathlib import Path

def convert_xlsx_to_csv():
    """
    Excel 폴더의 모든 xlsx 파일을 각각의 시트별로 CSV로 변환
    각 xlsx 파일명과 동일한 폴더를 만들고 그 안에 시트별 CSV 파일 저장
    """
    excel_folder = Path("excel")
    
    if not excel_folder.exists():
        print("excel 폴더가 존재하지 않습니다.")
        return
    
    # excel 폴더의 모든 xlsx 파일 찾기
    xlsx_files = list(excel_folder.glob("*.xlsx"))
    
    if not xlsx_files:
        print("excel 폴더에 xlsx 파일이 없습니다.")
        return
    
    print(f"발견된 xlsx 파일: {len(xlsx_files)}개")
    
    for xlsx_file in xlsx_files:
        print(f"\n처리 중: {xlsx_file.name}")
        
        # 파일명에서 확장자 제거하여 폴더명 생성
        folder_name = xlsx_file.stem
        output_folder = excel_folder / folder_name
        
        # 출력 폴더 생성
        output_folder.mkdir(exist_ok=True)
        print(f"폴더 생성: {output_folder}")
        
        try:
            # Excel 파일의 모든 시트 읽기
            excel_file = pd.ExcelFile(xlsx_file)
            sheet_names = excel_file.sheet_names
            
            print(f"시트 개수: {len(sheet_names)}")
            
            for sheet_name in sheet_names:
                print(f"  처리 중 시트: {sheet_name}")
                
                # 시트 읽기
                df = pd.read_excel(xlsx_file, sheet_name=sheet_name)
                
                # 시트명을 파일명으로 사용 (특수문자 제거)
                safe_sheet_name = "".join(c for c in sheet_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
                csv_filename = f"{safe_sheet_name}.csv"
                csv_path = output_folder / csv_filename
                
                # CSV로 저장
                df.to_csv(csv_path, index=False, encoding='utf-8-sig')
                print(f"    저장됨: {csv_path}")
                
        except Exception as e:
            print(f"오류 발생 ({xlsx_file.name}): {str(e)}")
            continue
    
    print("\n변환 완료!")

if __name__ == "__main__":
    convert_xlsx_to_csv()
