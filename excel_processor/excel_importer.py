"""
Excel 파일에서 데이터를 읽어와 데이터베이스에 저장하는 기능을 제공하는 모듈입니다.

`ExcelImporter` 클래스를 사용하여 `xlwings` 라이브러리를 통해 Excel 파일을 열고,
특정 규칙(예: '$' 포함 시트)에 따라 시트 데이터를 추출하여 `DBHandlerV2`를 통해
데이터베이스에 일괄 저장합니다. Cython 최적화 모듈을 활용하여 성능을 개선할 수 있습니다.
"""
import xlwings as xw
import logging
from data_manager.db_handler_v2 import DBHandlerV2
import os

# Cython 최적화 모듈 import (성능 향상)
try:
    from cython_extensions.excel_processor_v2 import (
        fast_process_excel_data,
        process_cell_value_fast,
        fast_batch_cell_processing,
    )

    USE_CYTHON_EXCEL = True
    logging.info("✓ Cython Excel 최적화 모듈 로드 성공")
except ImportError as e:
    USE_CYTHON_EXCEL = False
    logging.warning(f"⚠ Cython Excel 모듈 로드 실패, Python 폴백 사용: {e}")


class ExcelImporter:
    """
    Excel 파일의 데이터를 데이터베이스로 가져오는(import) 클래스입니다.

    `xlwings`를 사용하여 Excel 파일을 처리하고, `DBHandlerV2`를 통해 데이터를 저장합니다.
    '$' 문자가 포함된 시트만 대상으로 처리하며, Cython을 이용한 성능 최적화를 지원합니다.
    """

    def __init__(self, db_handler: DBHandlerV2):
        """
        ExcelImporter 객체를 초기화합니다. (DBHandlerV2 전용)

        Args:
            db_handler (DBHandlerV2): 데이터베이스 작업을 위한 `DBHandlerV2` 인스턴스.
                                     이 핸들러를 통해 시트 생성 및 셀 데이터 저장이 이루어집니다.
        """
        self.db: DBHandlerV2 = db_handler

    def import_excel(self, excel_path: str, db_file_path: Optional[str] = None) -> int:
        """
        지정된 Excel 파일에서 데이터를 읽어 데이터베이스로 가져옵니다.

        'Sheet$'와 같이 이름에 '$'가 포함된 시트들만 처리 대상으로 합니다.
        각 시트의 사용된 범위(used_range)의 데이터를 읽어 `DBHandlerV2.batch_insert_cells`를
        통해 일괄적으로 데이터베이스에 저장합니다. 기존에 동일한 `source_file`로
        저장된 시트가 있다면, 해당 시트들은 먼저 삭제된 후 새로운 데이터로 대체됩니다.

        Args:
            excel_path (str): 가져올 Excel 파일의 전체 경로.
            db_file_path (Optional[str]): 데이터베이스 파일의 경로. 제공되면 이 경로의 파일명을
                                          `source_file`로 사용하며, 그렇지 않으면 Excel 파일명에서
                                          파생된 이름을 사용합니다. (DBHandlerV2는 단일 DB를 다루므로,
                                          이 인자는 주로 `source_file` 메타데이터 설정에 사용됩니다.)

        Returns:
            int: 성공 시 1을 반환합니다. (V2에서는 구체적인 파일 ID 대신 성공 여부 표시)

        Raises:
            FileNotFoundError: `excel_path`에 해당하는 파일이 존재하지 않을 경우 (xlwings에서 발생 가능).
            Exception: Excel 파일 열기, 시트 처리, 데이터베이스 작업 중 발생하는 모든 예외.
                       (예: `xlwings` 오류, `sqlite3.Error` 등)
        """
        logging.info(f"Excel 파일 가져오기 시작: {excel_path}")
        if not os.path.exists(excel_path):
            logging.error(f"지정된 Excel 파일을 찾을 수 없습니다: {excel_path}")
            raise FileNotFoundError(f"지정된 Excel 파일을 찾을 수 없습니다: {excel_path}")

        app = None
        wb = None

        try:
            app = xw.App(visible=False, add_book=False)
            app.display_alerts = False
            logging.info("Excel 애플리케이션 시작 완료.")

            wb = app.books.open(excel_path)
            logging.info(f"Excel 파일 열기 완료: {excel_path}")

            if db_file_path:
                source_file_name = os.path.basename(db_file_path)
            else:
                excel_name_without_ext = os.path.splitext(os.path.basename(excel_path))[0]
                source_file_name = f"{excel_name_without_ext}.db" # DB 파일명으로 사용될 source_file

            try:
                deleted_count = self.db.delete_sheets_by_source_file(source_file_name)
                if deleted_count > 0:
                    logging.info(f"기존 '{source_file_name}' 출처 시트 {deleted_count}개 정리 완료.")
            except Exception as cleanup_error:
                logging.warning(f"기존 시트 정리 중 오류 (계속 진행): {cleanup_error}", exc_info=True)

            total_sheets = len(wb.sheets)
            dollar_sheets_processed_count = 0
            logging.info(f"Excel 파일 총 시트 개수: {total_sheets}")

            for sheet_idx, sheet in enumerate(wb.sheets):
                sheet_name = sheet.name
                logging.info(f"시트 {sheet_idx + 1}/{total_sheets}: '{sheet_name}' 확인 중...")

                if "$" in sheet_name:
                    dollar_sheets_processed_count += 1
                    logging.info(f"'$' 포함 시트 [{dollar_sheets_processed_count}]: '{sheet_name}' 가져오기 시작.")

                    try:
                        sheet_id = self.db.create_sheet_v2(
                            sheet_name,
                            is_dollar_sheet=True,
                            sheet_order=sheet_idx,
                            source_file=source_file_name, # 통일된 source_file_name 사용
                            replace_if_exists=True, # delete_sheets_by_source_file 이후이므로 사실상 새로 생성
                        )
                        logging.info(f"시트 '{sheet_name}' DB에 생성/매핑 완료 (ID: {sheet_id}).")

                        used_range = sheet.used_range
                        if used_range and used_range.rows.count > 0 and used_range.columns.count > 0 : # used_range가 실제로 영역을 가지는지 확인
                            logging.info(f"시트 '{sheet_name}' 사용된 범위(used_range): {used_range.address}")
                            sheet.api.Calculate() # 데이터 정확성 확보
                            raw_data = used_range.options(empty='').value # 빈 셀은 빈 문자열로 읽기

                            if raw_data is None:
                                logging.warning(f"시트 '{sheet_name}' 데이터가 None입니다. 건너뜁니다.")
                                continue

                            cells_data = []
                            if USE_CYTHON_EXCEL and 'fast_process_excel_data' in globals():
                                cells_data = fast_process_excel_data(raw_data)
                                logging.info(f"시트 '{sheet_name}' Cython 데이터 처리: {len(cells_data)}개 셀.")
                            else: # Python fallback
                                if isinstance(raw_data, list): # 여러 행 데이터
                                    for r_idx, row_content in enumerate(raw_data):
                                        if isinstance(row_content, list): # 각 행이 리스트(여러 열)인지 확인
                                            for c_idx, cell_val in enumerate(row_content):
                                                processed_val = self.process_cell_value(cell_val)
                                                if processed_val: # 빈 값은 저장하지 않음 (DB 핸들러에서 처리할 수도 있음)
                                                    cells_data.append((r_idx, c_idx, processed_val))
                                        elif row_content is not None: # 단일 열 데이터 (리스트의 요소가 값이 됨)
                                            processed_val = self.process_cell_value(row_content)
                                            if processed_val: cells_data.append((r_idx, 0, processed_val))
                                elif raw_data is not None: # 단일 셀 데이터
                                    processed_val = self.process_cell_value(raw_data)
                                    if processed_val: cells_data.append((0, 0, processed_val))
                                logging.info(f"시트 '{sheet_name}' Python 데이터 처리: {len(cells_data)}개 셀.")

                            if USE_CYTHON_EXCEL and cells_data and 'fast_batch_cell_processing' in globals():
                                cells_data = fast_batch_cell_processing(cells_data) # 추가 최적화

                            if cells_data:
                                self.db.batch_insert_cells(sheet_id, cells_data)
                                logging.info(f"시트 '{sheet_name}' 데이터 저장 완료: {len(cells_data)}개 셀.")
                            else:
                                logging.info(f"시트 '{sheet_name}'에 저장할 유효 데이터가 없습니다.")
                        else:
                            logging.info(f"시트 '{sheet_name}'에 사용된 범위가 없거나 비어있습니다.")
                    except Exception as sheet_proc_error:
                        logging.error(f"시트 '{sheet_name}' 처리 중 오류: {sheet_proc_error}", exc_info=True)
                        continue # 다음 시트로 계속
                else:
                    logging.debug(f"시트 '{sheet_name}' 이름에 '$'가 없어 건너뜁니다.")

            logging.info(f"Excel 가져오기 완료: 총 {total_sheets}개 시트 중 {dollar_sheets_processed_count}개 '$' 시트 처리됨.")
            return 1 # 성공 표시
        except FileNotFoundError: # excel_path 자체가 없을 때
            raise # 그대로 전달
        except Exception as e:
            logging.error(f"Excel 파일 가져오기 중 심각한 오류 발생: {excel_path}, 오류: {e}", exc_info=True)
            raise # 원본 예외를 다시 발생시켜 호출 측에서 상세 내용을 알 수 있도록 함
        finally:
            if wb:
                try: wb.close()
                except Exception as wb_e: logging.warning(f"Excel 워크북 닫기 중 오류: {wb_e}", exc_info=True)
            if app:
                try: app.quit()
                except Exception as app_e: logging.warning(f"Excel 애플리케이션 종료 중 오류: {app_e}", exc_info=True)
            gc.collect() # 작업 후 가비지 컬렉션

    def process_cell_value(self, cell_value: Any) -> str:
        """
        셀 값을 적절한 문자열 형태로 변환합니다. Cython 최적화 함수 사용을 시도합니다.

        None은 빈 문자열로, 숫자는 정수형태 우선 변환 후 문자열로, 그 외는 직접 문자열로 변환합니다.

        Args:
            cell_value (Any): 처리할 셀 값.

        Returns:
            str: 변환된 문자열 값.
        """
        if USE_CYTHON_EXCEL and 'process_cell_value_fast' in globals():
            try:
                return process_cell_value_fast(cell_value)
            except Exception as cy_e: # Cython 함수에서 예외 발생 시 Python 폴백
                logging.debug(f"Cython process_cell_value_fast 오류, Python 폴백: {cy_e}")

        # Python 폴백 로직
        if cell_value is None: return ""
        if isinstance(cell_value, (int, float)):
            if cell_value == int(cell_value): return str(int(cell_value))
            return str(cell_value)
        return str(cell_value) if not isinstance(cell_value, str) else cell_value
