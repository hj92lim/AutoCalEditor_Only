import xlwings as xw
import logging
from data_manager.db_handler_v2 import DBHandlerV2
import os

class ExcelExporter:
    """Excel 파일 내보내기 클래스"""

    def __init__(self, db_handler: DBHandlerV2):
        """
        ExcelExporter 초기화 (V2 전용)

        Args:
            db_handler: V2 DB 핸들러 객체
        """
        self.db = db_handler

    def export_excel(self, file_id: int, output_path: str) -> None:
        """
        DB 데이터를 Excel 파일로 내보내기

        Args:
            file_id: 파일 ID
            output_path: 출력 파일 경로
        """
        logging.info(f"Excel 파일 내보내기: ID {file_id}")

        try:
            # Excel 애플리케이션 시작
            app = xw.App(visible=False)
            wb = app.books.add()

            # 기본 Sheet1 삭제
            for sheet in wb.sheets:
                sheet.delete()

            # 파일 정보 가져오기
            files = self.db.get_files()
            file_name = next((f['name'] for f in files if f['id'] == file_id), None)

            if not file_name:
                raise ValueError(f"ID {file_id}에 해당하는 파일을 찾을 수 없습니다.")

            # 시트 목록 가져오기
            sheets = self.db.get_sheets(file_id)

            for sheet_info in sheets:
                sheet_id = sheet_info['id']
                sheet_name = sheet_info['name']

                # 새 시트 추가
                sheet = wb.sheets.add(sheet_name)

                # 시트 데이터 가져오기
                sheet_data = self.db.get_sheet_data(sheet_id)

                # 데이터가 있는 경우 Excel에 쓰기
                if sheet_data:
                    # 최대 행/열 수 계산
                    max_row = len(sheet_data)
                    max_col = max(len(row) for row in sheet_data) if max_row > 0 else 0

                    # 전체 범위 설정
                    if max_row > 0 and max_col > 0:
                        range_addr = f"A1:{chr(65 + max_col - 1)}{max_row}"
                        sheet.range(range_addr).value = sheet_data

            # 파일 저장
            wb.save(output_path)
            wb.close()
            app.quit()

            logging.info(f"Excel 파일 내보내기 완료: {output_path}")

        except Exception as e:
            logging.error(f"Excel 파일 내보내기 오류: {e}")
            if 'app' in locals():
                try:
                    app.quit()
                except:
                    pass
            raise