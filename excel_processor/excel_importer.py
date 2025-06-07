import xlwings as xw
import logging
from data_manager.db_handler_v2 import DBHandlerV2
import os

# Cython 최적화 모듈 import (성능 향상)
try:
    from cython_extensions.excel_processor_v2 import (
        fast_process_excel_data,
        process_cell_value_fast,
        fast_batch_cell_processing
    )
    USE_CYTHON_EXCEL = True
    logging.info("✓ Cython Excel 최적화 모듈 로드 성공")
except ImportError as e:
    USE_CYTHON_EXCEL = False
    logging.warning(f"⚠ Cython Excel 모듈 로드 실패, Python 폴백 사용: {e}")

class ExcelImporter:
    """Excel 파일 가져오기 클래스"""

    def __init__(self, db_handler: DBHandlerV2):
        """
        ExcelImporter 초기화 (V2 전용)

        Args:
            db_handler: V2 DB 핸들러 객체
        """
        self.db = db_handler

    def import_excel(self, excel_path: str, db_file_path: str = None) -> int:
        """
        Excel 파일을 DB로 가져오기 (안정성 강화)

        Args:
            excel_path: Excel 파일 경로
            db_file_path: 사용자 지정 DB 파일 경로 (지정된 경우)

        Returns:
            생성된 파일 ID
        """
        logging.info(f"Excel 파일 가져오기 시작: {excel_path}")

        app = None
        wb = None

        try:
            # Excel 파일 열기 (안전한 방식)
            app = xw.App(visible=False, add_book=False)
            app.display_alerts = False  # 경고 메시지 비활성화

            logging.info(f"Excel 애플리케이션 시작 완료")

            wb = app.books.open(excel_path)
            logging.info(f"Excel 파일 열기 완료: {excel_path}")

            # 파일명 추출 (V2에서는 source_file로 사용)
            if db_file_path:
                # 사용자가 지정한 DB 파일명 사용
                source_file_name = os.path.basename(db_file_path)
            else:
                # 기본: 확장자를 제거한 엑셀 파일명에 .db 추가
                excel_name_without_ext = os.path.splitext(os.path.basename(excel_path))[0]
                source_file_name = f"{excel_name_without_ext}.db"

            # V2 방식: source_file 이름만 저장 (실제 파일 ID는 사용하지 않음)
            source_file = source_file_name

            # 모든 시트 확인
            total_sheets = len(wb.sheets)
            dollar_sheets_count = 0

            logging.info(f"Excel 파일 총 시트 개수: {total_sheets}")

            for sheet_idx, sheet in enumerate(wb.sheets):
                sheet_name = sheet.name
                logging.info(f"시트 {sheet_idx + 1}/{total_sheets}: '{sheet_name}' 확인 중...")

                # "$" 포함 시트만 처리
                if "$" in sheet_name:
                    dollar_sheets_count += 1
                    logging.info(f"$ 시트 발견 [{dollar_sheets_count}]: '{sheet_name}' 가져오기 시작")

                    try:
                        # V2 방식으로 시트 생성
                        sheet_id = self.db.create_sheet_v2(
                            sheet_name,
                            is_dollar_sheet=True,
                            sheet_order=sheet_idx,
                            source_file=source_file_name
                        )
                        logging.info(f"시트 '{sheet_name}' DB 생성 완료 (ID: {sheet_id})")

                        # 시트 데이터 읽기 (상세 로깅 및 안전성 강화)
                        used_range = sheet.used_range
                        if used_range:
                            logging.info(f"시트 '{sheet_name}' used_range 감지: {used_range.address}")

                            # 데이터 읽기 시도 (안전한 방식)
                            try:
                                # 강제로 계산 업데이트 (데이터 정확성 보장)
                                sheet.api.Calculate()

                                data = used_range.value
                                logging.info(f"시트 '{sheet_name}' 데이터 읽기 완료, 타입: {type(data)}")

                                if data is None:
                                    logging.warning(f"시트 '{sheet_name}' 데이터가 None입니다.")
                                    continue

                                # 데이터 처리 - Cython 최적화 적용
                                if USE_CYTHON_EXCEL:
                                    # Cython 최적화 버전 사용 (C 수준 성능)
                                    cells_data = fast_process_excel_data(data)
                                    logging.info(f"시트 '{sheet_name}' Cython 최적화 데이터 처리: {len(cells_data)}개 셀")
                                else:
                                    # 기존 Python 버전 (폴백)
                                    cells_data = []
                                    if isinstance(data, list):
                                        logging.info(f"시트 '{sheet_name}' 리스트 데이터 처리: {len(data)}행")
                                        for i, row_data in enumerate(data):
                                            if isinstance(row_data, list):
                                                for j, cell_value in enumerate(row_data):
                                                    if cell_value is not None:
                                                        value = self.process_cell_value(cell_value)
                                                        cells_data.append((i, j, value))
                                            elif row_data is not None:  # 단일 행인 경우
                                                value = str(row_data) if not isinstance(row_data, str) else row_data
                                                cells_data.append((0, i, value))
                                    else:  # 단일 셀인 경우
                                        logging.info(f"시트 '{sheet_name}' 단일 셀 데이터: {data}")
                                        cells_data = [(0, 0, str(data) if data is not None else "")]

                                # 배치 처리 최적화
                                if USE_CYTHON_EXCEL and cells_data:
                                    cells_data = fast_batch_cell_processing(cells_data)

                                # DB에 셀 데이터 일괄 저장
                                if cells_data:
                                    self.db.batch_insert_cells(sheet_id, cells_data)
                                    logging.info(f"시트 '{sheet_name}' 데이터 저장 완료: {len(cells_data)}개 셀")
                                else:
                                    logging.warning(f"시트 '{sheet_name}' 저장할 데이터가 없습니다.")

                            except Exception as data_error:
                                logging.error(f"시트 '{sheet_name}' 데이터 읽기 오류: {data_error}")
                                continue

                        else:
                            logging.warning(f"시트 '{sheet_name}' used_range가 None입니다. (빈 시트)")

                    except Exception as sheet_error:
                        logging.error(f"시트 '{sheet_name}' 처리 중 오류: {sheet_error}")
                        continue

                else:
                    logging.debug(f"시트 '{sheet_name}' $ 없음, 건너뛰기")

            logging.info(f"Excel 가져오기 완료: 총 {total_sheets}개 시트 중 {dollar_sheets_count}개 $ 시트 처리")

            # Excel 파일 안전하게 닫기
            try:
                if wb:
                    wb.close()
                    logging.info("Excel 워크북 닫기 완료")
            except Exception as wb_close_error:
                logging.warning(f"Excel 워크북 닫기 중 오류: {wb_close_error}")

            try:
                if app:
                    app.quit()
                    logging.info("Excel 애플리케이션 종료 완료")
            except Exception as app_quit_error:
                logging.warning(f"Excel 애플리케이션 종료 중 오류: {app_quit_error}")

            logging.info(f"Excel 파일 가져오기 완료: {source_file_name}")
            return 1  # V2에서는 실제 파일 ID 대신 성공 표시

        except Exception as e:
            logging.error(f"Excel 파일 가져오기 오류: {e}")
            import traceback
            logging.error(f"상세 오류: {traceback.format_exc()}")

            # 오류 발생 시 리소스 정리
            try:
                if wb:
                    wb.close()
            except:
                pass

            try:
                if app:
                    app.quit()
            except:
                pass

            raise

    # 기존 코드 위치에 새 메서드 추가
    def process_cell_value(self, cell_value):
        """셀 값을 처리하여 적절한 형태로 변환 (Cython 최적화 지원)"""
        if USE_CYTHON_EXCEL:
            # Cython 최적화 버전 사용 (C 수준 성능)
            return process_cell_value_fast(cell_value)
        else:
            # 기존 Python 버전 (폴백)
            if cell_value is None:
                return ""

            # 숫자인 경우 정수 확인 및 처리
            if isinstance(cell_value, (int, float)):
                # 정수로 표현 가능한 값인지 확인
                if cell_value == int(cell_value):
                    return str(int(cell_value))  # 정수로 변환 후 문자열화
                return str(cell_value)           # 그대로 문자열화

            # 문자열이면 그대로 반환, 아니면 문자열로 변환
            return cell_value if isinstance(cell_value, str) else str(cell_value)