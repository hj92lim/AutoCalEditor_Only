"""
데이터베이스의 내용을 Excel 파일로 내보내는 기능을 제공하는 모듈입니다.

`ExcelExporter` 클래스를 사용하여 `DBHandlerV2`를 통해 접근된 데이터베이스의
시트와 셀 데이터를 지정된 경로의 Excel 파일(.xlsx)로 저장합니다.
"""
import xlwings as xw
import logging
from data_manager.db_handler_v2 import DBHandlerV2
import os # os 모듈은 현재 코드에서 직접 사용되지 않으나, 경로 관련 작업에 잠재적으로 필요할 수 있습니다.


class ExcelExporter:
    """
    데이터베이스의 데이터를 Excel 파일 형식으로 내보내는 클래스입니다.

    `DBHandlerV2`를 통해 데이터베이스에 접근하여, 지정된 파일 ID에 해당하는
    모든 시트와 셀 데이터를 Excel 통합 문서로 구성하고 저장합니다.
    """

    def __init__(self, db_handler: DBHandlerV2):
        """
        ExcelExporter 객체를 초기화합니다. (DBHandlerV2 전용)

        Args:
            db_handler (DBHandlerV2): 데이터베이스 작업을 위한 `DBHandlerV2` 인스턴스.
                                     이 핸들러를 통해 시트 목록, 셀 데이터 등을 조회합니다.
        """
        self.db: DBHandlerV2 = db_handler

    def export_excel(self, file_id: int, output_path: str) -> None:
        """
        지정된 `file_id`에 해당하는 데이터베이스의 모든 시트 데이터를 Excel 파일로 내보냅니다.

        `file_id`는 `DBHandlerV2`에서 관리하는 파일 식별자일 것으로 예상되나,
        V2 핸들러는 단일 DB 파일을 직접 다루므로, 이 `file_id`의 구체적인 역할은
        `DBHandlerV2.get_files()` 및 `DBHandlerV2.get_sheets()` 메소드의 구현에 따라 달라집니다.
        (현재 `DBHandlerV2.get_files()`는 DB 파일 자체를 단일 파일로 반환하며,
         `get_sheets`는 `file_id` 인자를 받지 않는 것으로 보입니다. 이 부분은 확인이 필요합니다.)
        Excel 파일 생성에는 `xlwings` 라이브러리를 사용합니다.

        Args:
            file_id (int): 내보낼 데이터베이스 파일의 ID. (DBHandlerV2의 파일 관리 방식에 따라 해석됨)
            output_path (str): 생성될 Excel 파일의 전체 경로 (확장자 포함).

        Raises:
            ValueError: 제공된 `file_id`에 해당하는 파일을 찾을 수 없는 경우.
            Exception: Excel 파일 생성, 데이터 쓰기, 또는 `xlwings` 관련 작업 중 발생하는 모든 예외.
                       (구체적인 예외 타입은 `xlwings` 및 DB 핸들러에 따라 다를 수 있음)
        """
        logging.info(f"Excel 파일 내보내기 시작: 파일 ID {file_id} -> {output_path}")

        app = None # Ensure app is defined for finally block
        try:
            # 참고: DBHandlerV2는 단일 DB 파일을 다루므로, file_id의 역할이 모호할 수 있습니다.
            # get_files()가 단일 파일 정보를 반환하고, get_sheets()가 file_id를 사용하지 않는다면,
            # file_id 인자는 사실상 현재 구현에서 큰 의미가 없을 수 있습니다.
            # 여기서는 제공된 file_id로 파일을 찾는 로직을 유지합니다.
            files = self.db.get_files() # 현재는 DB 파일 자체 정보를 반환
            target_file_info = None
            # file_id가 1이 아니거나, get_files() 결과가 예상과 다를 경우를 대비한 로직
            if files and files[0].get("id") == file_id : # V2는 단일 DB 파일이므로 ID 1로 가정
                 target_file_info = files[0]

            if not target_file_info:
                raise ValueError(f"ID {file_id}에 해당하는 파일을 찾을 수 없습니다 (현재 DB: {self.db.db_file}).")

            logging.info(f"내보낼 대상 DB 파일 정보: {target_file_info.get('name', '이름 없음')}")

            app = xw.App(visible=False) # Excel 애플리케이션 시작
            wb = app.books.add()

            # 기본적으로 생성되는 'Sheet1' 등 초기 시트 삭제
            if wb.sheets.count > 0 and any(sheet.name == 'Sheet1' for sheet in wb.sheets): # xw 버전에 따라 기본 시트 이름 다를 수 있음
                for sheet_obj in list(wb.sheets): # list()로 복사본 순회
                    try:
                        sheet_obj.delete()
                    except Exception as sheet_del_e:
                        # 기본 시트 삭제 실패는 치명적이지 않을 수 있으므로 경고만 로깅
                        logging.warning(f"기본 시트 '{sheet_obj.name}' 삭제 중 오류: {sheet_del_e}")

            # DB에서 시트 목록 가져오기 (DBHandlerV2.get_sheets는 file_id를 받지 않음)
            sheets_info = self.db.get_sheets()

            if not sheets_info:
                logging.warning(f"DB에 내보낼 시트가 없습니다: {self.db.db_file}")
                # 빈 Excel 파일을 저장할지, 오류를 발생시킬지 결정. 현재는 빈 파일 저장.

            for sheet_detail in sheets_info: # Renamed sheet_info to sheet_detail
                sheet_id_db = sheet_detail["id"] # Renamed sheet_id to sheet_id_db
                sheet_name_db = sheet_detail["name"] # Renamed sheet_name to sheet_name_db

                new_sheet = wb.sheets.add(sheet_name_db) # 새 시트 추가
                logging.debug(f"시트 '{sheet_name_db}' (ID: {sheet_id_db}) 데이터 내보내기 중...")

                sheet_cell_data = self.db.get_sheet_data(sheet_id_db) # Renamed sheet_data

                if sheet_cell_data:
                    max_row = len(sheet_cell_data)
                    max_col = max(len(row_data) for row_data in sheet_cell_data) if max_row > 0 else 0 # Renamed row to row_data

                    if max_row > 0 and max_col > 0:
                        # xlwings는 0-based index가 아닌 Excel 스타일 주소(A1)를 사용
                        # 또한, 데이터는 리스트의 리스트 형태로 직접 할당 가능
                        new_sheet.range("A1").value = sheet_cell_data
                        logging.debug(f"'{sheet_name_db}' 시트에 {max_row}x{max_col} 데이터 쓰기 완료.")
                else:
                    logging.info(f"'{sheet_name_db}' 시트에 데이터가 없습니다.")

            if not wb.sheets: # 만약 모든 시트가 비어있거나 해서 추가된 시트가 없다면
                wb.sheets.add("Sheet1") # 기본 시트 하나는 있도록 보장
                logging.info("내보낼 데이터가 없어 빈 Sheet1을 포함한 Excel 파일을 생성합니다.")


            wb.save(output_path)
            logging.info(f"Excel 파일 내보내기 완료: {output_path}")

        except Exception as e:
            logging.error(f"Excel 파일 내보내기 중 오류 발생: {e}", exc_info=True)
            # app 객체가 생성되었고, wb 객체도 정상적으로 생성되었다면 wb.close() 시도
            if 'wb' in locals() and wb is not None:
                try:
                    wb.close()
                except Exception as wb_close_e:
                    logging.error(f"워크북 닫기 실패: {wb_close_e}", exc_info=True)
            raise # 원본 예외를 다시 발생시켜 호출 측에서 알 수 있도록 함
        finally:
            if app: # Excel 애플리케이션 종료
                try:
                    app.quit()
                except Exception as app_quit_e:
                    logging.error(f"Excel 애플리케이션 종료 실패: {app_quit_e}", exc_info=True)

# os 모듈 직접 사용하지 않아 주석 처리 또는 삭제 가능
# import os
