import sqlite3
from typing import Dict, List, Any, Tuple, Optional
import os
import logging
import gc

# 중앙 집중식 상수 관리 모듈 import
from core.constants import DatabaseConstants, PerformanceConstants, ExcelConstants

# Cython 최적화 모듈 import (성능 향상)
try:
    from cython_extensions.data_processor import (
        fast_db_batch_processing,
        fast_sheet_data_loading,
        fast_data_filtering
    )
    USE_CYTHON_DB = True
    logging.info("✓ Cython DB 최적화 모듈 로드 성공")
except ImportError as e:
    USE_CYTHON_DB = False
    logging.warning(f"⚠ Cython DB 모듈 로드 실패, Python 폴백 사용: {e}")


class DBHandlerV2:
    """단순화된 SQLite DB 연결 및 쿼리 처리 클래스 (2계층: DB → 시트)"""

    def __init__(self, db_file: str = None):
        """
        DBHandlerV2 초기화

        Args:
            db_file: 데이터베이스 파일 경로 (None인 경우 연결하지 않음)
        """
        self.db_file = db_file
        self.db_file_path = db_file  # Git 관련 코드 호환성을 위한 별칭
        self.conn = None
        self.cursor = None

        # DB 파일이 지정된 경우에만 연결 시도
        if db_file is not None:
            self.connect()
            self.init_tables()

    def connect(self) -> None:
        """DB 연결 설정 - 성능 최적화"""
        try:
            self.conn = sqlite3.connect(self.db_file, check_same_thread=False)
            self.conn.row_factory = sqlite3.Row  # 결과를 딕셔너리 형태로 가져오기 위해
            self.cursor = self.conn.cursor()

            # SQLite 성능 최적화 설정 (constants에서 관리)
            for pragma in DatabaseConstants.PRAGMA_SETTINGS:
                try:
                    self.cursor.execute(pragma)
                except sqlite3.Error as e:
                    logging.warning(f"PRAGMA 설정 실패: {pragma} - {e}")

            logging.info(f"SQLite DB '{self.db_file}' 연결 성공 (V2, 성능 최적화 적용)")
        except sqlite3.Error as e:
            logging.error(f"SQLite 연결 오류: {e}")
            raise

    def disconnect(self) -> None:
        """DB 연결 종료"""
        if self.conn:
            self.conn.close()
            logging.info("SQLite DB 연결 종료 (V2)")

    def init_tables(self) -> None:
        """필요한 테이블 생성 (단순화된 구조)"""
        try:
            # 시트 테이블 (files 테이블 제거, 시트가 최상위)
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS sheets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    is_dollar_sheet BOOLEAN NOT NULL DEFAULT 0,
                    sheet_order INTEGER NOT NULL DEFAULT 0,
                    source_file TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # 셀 데이터 테이블 (변경 없음)
            self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS cells (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sheet_id INTEGER NOT NULL,
                row INTEGER NOT NULL,
                col INTEGER NOT NULL,
                value TEXT,
                FOREIGN KEY (sheet_id) REFERENCES sheets (id) ON DELETE CASCADE,
                UNIQUE(sheet_id, row, col)
            )
            ''')

            # 성능 최적화를 위한 인덱스 생성 (constants에서 관리)
            for index_sql in DatabaseConstants.PERFORMANCE_INDEXES:
                try:
                    self.cursor.execute(index_sql)
                except sqlite3.Error as e:
                    logging.warning(f"인덱스 생성 실패: {index_sql} - {e}")

            self.conn.commit()
            logging.info("테이블 초기화 완료 (V2, 성능 최적화 인덱스 포함)")
        except sqlite3.Error as e:
            logging.error(f"테이블 초기화 오류: {e}")
            self.conn.rollback()
            raise

    def create_sheet_v2(self, sheet_name: str, is_dollar_sheet: bool = False,
                       sheet_order: int = 0, source_file: str = None,
                       replace_if_exists: bool = True) -> int:
        """
        시트 생성 (중복 처리 로직 포함)

        Args:
            sheet_name: 시트 이름
            is_dollar_sheet: $ 마크 포함 여부
            sheet_order: 시트 순서
            source_file: 원본 파일명 (선택사항)
            replace_if_exists: 기존 시트가 있을 경우 교체 여부 (기본값: True)

        Returns:
            생성된 시트 ID
        """
        try:
            # 기존 시트 존재 여부 확인
            existing_sheet = self.get_sheet_by_name(sheet_name)

            if existing_sheet:
                if replace_if_exists:
                    # 기존 시트 삭제 후 재생성
                    logging.info(f"기존 시트 '{sheet_name}' 발견, 교체 진행")
                    self.delete_sheet(existing_sheet['id'])
                else:
                    # 기존 시트 ID 반환
                    logging.info(f"기존 시트 '{sheet_name}' 사용 (ID: {existing_sheet['id']})")
                    return existing_sheet['id']

            # 새 시트 생성
            self.cursor.execute(
                '''INSERT INTO sheets (name, is_dollar_sheet, sheet_order, source_file)
                   VALUES (?, ?, ?, ?)''',
                (sheet_name, 1 if is_dollar_sheet else 0, sheet_order, source_file)
            )
            self.conn.commit()
            sheet_id = self.cursor.lastrowid
            logging.info(f"새 시트 '{sheet_name}' 생성 완료 (ID: {sheet_id})")
            return sheet_id

        except sqlite3.IntegrityError as e:
            if "UNIQUE constraint failed: sheets.name" in str(e):
                # UNIQUE constraint 오류 처리
                logging.error(f"시트명 중복 오류: '{sheet_name}' - 기존 시트가 존재합니다")
                if replace_if_exists:
                    # 재시도: 기존 시트 강제 삭제 후 재생성
                    try:
                        existing_sheet = self.get_sheet_by_name(sheet_name)
                        if existing_sheet:
                            logging.info(f"UNIQUE constraint 오류 복구: 기존 시트 '{sheet_name}' 삭제 후 재생성")
                            self.delete_sheet(existing_sheet['id'])
                            return self.create_sheet_v2(sheet_name, is_dollar_sheet, sheet_order, source_file, False)
                    except Exception as retry_error:
                        logging.error(f"시트 재생성 실패: {retry_error}")
                        raise
                raise
            else:
                logging.error(f"시트 생성 중 무결성 오류: {e}")
                self.conn.rollback()
                raise
        except Exception as e:
            logging.error(f"시트 생성 오류: {e}")
            self.conn.rollback()
            raise

    def get_sheets(self) -> List[Dict[str, Any]]:
        """
        모든 시트 목록 조회

        Returns:
            시트 목록
        """
        try:
            self.cursor.execute(
                '''SELECT id, name, is_dollar_sheet, sheet_order, source_file
                   FROM sheets ORDER BY sheet_order, id'''
            )
            sheets = []
            for row in self.cursor.fetchall():
                sheets.append({
                    'id': row[0],
                    'name': row[1],
                    'is_dollar_sheet': bool(row[2]),
                    'order': row[3],
                    'source_file': row[4]
                })
            return sheets
        except Exception as e:
            logging.error(f"시트 목록 조회 오류: {e}")
            raise

    def get_sheet_by_id(self, sheet_id: int) -> Optional[Dict[str, Any]]:
        """특정 시트 정보 조회"""
        try:
            self.cursor.execute(
                '''SELECT id, name, is_dollar_sheet, sheet_order, source_file
                   FROM sheets WHERE id = ?''', (sheet_id,)
            )
            row = self.cursor.fetchone()
            if row:
                return {
                    'id': row[0],
                    'name': row[1],
                    'is_dollar_sheet': bool(row[2]),
                    'order': row[3],
                    'source_file': row[4]
                }
            return None
        except Exception as e:
            logging.error(f"시트 조회 오류: {e}")
            raise

    def get_sheet_by_name(self, sheet_name: str) -> Optional[Dict[str, Any]]:
        """
        시트명으로 시트 정보 조회

        Args:
            sheet_name: 조회할 시트 이름

        Returns:
            시트 정보 딕셔너리 (없으면 None)
        """
        try:
            self.cursor.execute(
                '''SELECT id, name, is_dollar_sheet, sheet_order, source_file
                   FROM sheets WHERE name = ?''', (sheet_name,)
            )
            row = self.cursor.fetchone()
            if row:
                return {
                    'id': row[0],
                    'name': row[1],
                    'is_dollar_sheet': bool(row[2]),
                    'order': row[3],
                    'source_file': row[4]
                }
            return None
        except Exception as e:
            logging.error(f"시트명 조회 오류 ('{sheet_name}'): {e}")
            return None

    def rename_sheet(self, sheet_id: int, new_name: str, is_dollar_sheet: bool = None):
        """
        시트 이름 변경

        Args:
            sheet_id: 시트 ID
            new_name: 새 시트 이름
            is_dollar_sheet: 달러 시트 여부 (None이면 변경하지 않음)
        """
        try:
            if is_dollar_sheet is None:
                # 이름만 변경
                query = "UPDATE sheets SET name = ? WHERE id = ?"
                self.cursor.execute(query, (new_name, sheet_id))
            else:
                # 이름과 달러 시트 여부 모두 변경
                query = "UPDATE sheets SET name = ?, is_dollar_sheet = ? WHERE id = ?"
                self.cursor.execute(query, (new_name, is_dollar_sheet, sheet_id))

            self.conn.commit()
        except Exception as e:
            logging.error(f"시트 이름 변경 오류: {e}")
            self.conn.rollback()
            raise

    def delete_sheet(self, sheet_id: int):
        """시트 삭제 (연관된 셀 데이터도 함께 삭제)"""
        try:
            self.cursor.execute("DELETE FROM sheets WHERE id = ?", (sheet_id,))
            self.conn.commit()
        except Exception as e:
            logging.error(f"시트 삭제 오류: {e}")
            self.conn.rollback()
            raise

    def delete_sheets_by_source_file(self, source_file: str) -> int:
        """
        특정 source_file의 모든 시트 삭제

        Args:
            source_file: 원본 파일명

        Returns:
            삭제된 시트 개수
        """
        try:
            # 삭제할 시트 목록 조회
            self.cursor.execute(
                "SELECT id, name FROM sheets WHERE source_file = ?",
                (source_file,)
            )
            sheets_to_delete = self.cursor.fetchall()

            if not sheets_to_delete:
                logging.info(f"삭제할 시트가 없습니다 (source_file: '{source_file}')")
                return 0

            # 시트들 삭제 (CASCADE로 연관된 셀 데이터도 자동 삭제)
            self.cursor.execute("DELETE FROM sheets WHERE source_file = ?", (source_file,))
            deleted_count = self.cursor.rowcount
            self.conn.commit()

            logging.info(f"source_file '{source_file}'의 {deleted_count}개 시트 삭제 완료")
            for sheet in sheets_to_delete:
                logging.debug(f"  - 삭제된 시트: '{sheet[1]}' (ID: {sheet[0]})")

            return deleted_count

        except Exception as e:
            logging.error(f"source_file 시트 삭제 오류 ('{source_file}'): {e}")
            self.conn.rollback()
            raise

    def delete_sheets_by_source_file_in_transaction(self, source_file: str) -> int:
        """
        특정 source_file의 모든 시트 삭제 (기존 트랜잭션 내에서 실행)

        Args:
            source_file: 원본 파일명

        Returns:
            삭제된 시트 개수
        """
        try:
            # 삭제할 시트 목록 조회
            self.cursor.execute(
                "SELECT id, name FROM sheets WHERE source_file = ?",
                (source_file,)
            )
            sheets_to_delete = self.cursor.fetchall()

            if not sheets_to_delete:
                logging.info(f"삭제할 시트가 없습니다 (source_file: '{source_file}')")
                return 0

            # 시트들 삭제 (CASCADE로 연관된 셀 데이터도 자동 삭제)
            # 🔧 기존 트랜잭션 내에서 실행하므로 별도 트랜잭션 관리 안함
            self.cursor.execute("DELETE FROM sheets WHERE source_file = ?", (source_file,))
            deleted_count = self.cursor.rowcount

            logging.info(f"source_file '{source_file}'의 {deleted_count}개 시트 삭제 완료 (트랜잭션 내)")
            for sheet in sheets_to_delete:
                logging.debug(f"  - 삭제된 시트: '{sheet[1]}' (ID: {sheet[0]})")

            return deleted_count

        except Exception as e:
            logging.error(f"source_file 시트 삭제 오류 (트랜잭션 내, '{source_file}'): {e}")
            raise  # 상위 트랜잭션에서 롤백 처리

    # 셀 관련 메서드들은 기존과 동일
    def set_cell_value(self, sheet_id: int, row: int, col: int, value: str) -> None:
        """셀 값 설정"""
        try:
            self.cursor.execute(
                """
                INSERT INTO cells (sheet_id, row, col, value)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(sheet_id, row, col)
                DO UPDATE SET value = ?
                """,
                (sheet_id, row, col, value, value)
            )
            self.conn.commit()
        except sqlite3.Error as e:
            logging.error(f"셀 값 설정 오류: {e}")
            self.conn.rollback()
            raise

    def get_cell_value(self, sheet_id: int, row: int, col: int) -> str:
        """셀 값 가져오기"""
        try:
            self.cursor.execute(
                "SELECT value FROM cells WHERE sheet_id = ? AND row = ? AND col = ?",
                (sheet_id, row, col)
            )
            result = self.cursor.fetchone()
            return result['value'] if result and result['value'] is not None else ""
        except sqlite3.Error as e:
            logging.error(f"셀 값 가져오기 오류: {e}")
            return ""

    def get_sheet_data(self, sheet_id: int) -> List[List[str]]:
        """시트의 모든 데이터를 2차원 배열 형태로 가져오기 - 성능 최적화"""
        import gc

        try:
            # 1. 시트 크기 먼저 확인 (단일 쿼리로 최적화)
            self.cursor.execute("""
                SELECT MAX(row) as max_row, MAX(col) as max_col, COUNT(*) as cell_count
                FROM cells WHERE sheet_id = ? AND value IS NOT NULL AND value != ''
            """, (sheet_id,))

            result = self.cursor.fetchone()
            if not result or result['max_row'] is None:
                return []

            max_row, max_col, cell_count = result['max_row'], result['max_col'], result['cell_count']
            # 로깅 제거로 성능 향상

            # 2. 희소 행렬로 초기화 (메모리 효율적)
            sheet_data = [["" for _ in range(max_col + 1)] for _ in range(max_row + 1)]

            # 3. 배치 단위로 데이터 로드 (메모리 사용량 제어)
            batch_size = DatabaseConstants.BATCH_SIZE_LARGE
            offset = 0

            while True:
                # 배치 단위로 셀 데이터 가져오기 (빈 값 제외)
                self.cursor.execute("""
                    SELECT row, col, value FROM cells
                    WHERE sheet_id = ? AND value IS NOT NULL AND value != ''
                    ORDER BY row, col
                    LIMIT ? OFFSET ?
                """, (sheet_id, batch_size, offset))

                batch = self.cursor.fetchall()
                if not batch:
                    break

                # 배치 데이터 처리 - Cython 최적화 활성화
                try:
                    from cython_extensions.data_processor import fast_sheet_data_loading
                    # 배치를 Cython으로 빠르게 처리
                    batch_dict = [{'row': cell['row'], 'col': cell['col'], 'value': cell['value']} for cell in batch]
                    temp_sheet = fast_sheet_data_loading(batch_dict, max_row, max_col)
                    # 결과를 기존 sheet_data에 병합
                    for i in range(len(temp_sheet)):
                        for j in range(len(temp_sheet[i])):
                            if temp_sheet[i][j] is not None:
                                sheet_data[i][j] = temp_sheet[i][j]
                except ImportError:
                    # Python 폴백
                    for cell in batch:
                        sheet_data[cell['row']][cell['col']] = cell['value']

                offset += batch_size

                # 대용량 데이터 처리 시 주기적 가비지 컬렉션 (로깅 제거)
                if offset % DatabaseConstants.GC_INTERVAL_CELLS == 0:
                    gc.collect()

            logging.info(f"시트 {sheet_id} 데이터 로드 완료: {max_row+1}x{max_col+1}, {cell_count}개 셀")
            return sheet_data

        except sqlite3.Error as e:
            logging.error(f"시트 데이터 가져오기 오류: {e}")
            raise

    def get_sheet_metadata(self, sheet_id: int) -> Dict[str, Any]:
        """시트 메타데이터 가져오기 (행/열 수)"""
        try:
            # 시트 정보 조회
            self.cursor.execute(
                "SELECT MAX(row) as max_row, MAX(col) as max_col FROM cells WHERE sheet_id = ?",
                (sheet_id,)
            )
            result = self.cursor.fetchone()

            max_row = result['max_row'] if result and result['max_row'] is not None else 0
            max_col = result['max_col'] if result and result['max_col'] is not None else 0

            # 최소값 설정 (constants에서 관리)
            max_row = max(max_row, ExcelConstants.DEFAULT_ROWS)
            max_col = max(max_col, ExcelConstants.DEFAULT_COLS)

            return {"max_row": max_row, "max_col": max_col}

        except Exception as e:
            logging.error(f"시트 메타데이터 조회 오류: {e}")
            return {
                "max_row": ExcelConstants.DEFAULT_ROWS,
                "max_col": ExcelConstants.DEFAULT_COLS
            }  # 오류 시 기본값

    def get_sheets(self) -> List[Dict[str, Any]]:
        """
        모든 시트 목록 조회 (V2 순수 방식)

        Returns:
            시트 목록
        """
        try:
            self.cursor.execute(
                '''SELECT id, name, is_dollar_sheet, sheet_order, source_file
                   FROM sheets ORDER BY sheet_order, id'''
            )
            sheets = []
            for row in self.cursor.fetchall():
                sheets.append({
                    'id': row[0],
                    'name': row[1],
                    'is_dollar_sheet': bool(row[2]),
                    'order': row[3],
                    'source_file': row[4]
                })
            return sheets

        except Exception as e:
            logging.error(f"시트 목록 조회 오류: {e}")
            return []

    def get_files(self) -> List[Dict[str, Any]]:
        """
        파일 목록 조회 (V2에서는 DB 파일 자체가 하나의 파일)

        Returns:
            파일 목록 (단일 DB 파일 정보)
        """
        try:
            if not self.db_file:
                return []

            # DB 파일 자체를 하나의 파일로 처리
            import os
            from pathlib import Path

            file_path = Path(self.db_file)
            return [{
                'id': 1,  # 단일 파일이므로 ID는 1
                'name': file_path.stem,  # 확장자 제외한 파일명
                'path': str(file_path),
                'size': os.path.getsize(self.db_file) if os.path.exists(self.db_file) else 0
            }]

        except Exception as e:
            logging.error(f"파일 목록 조회 오류: {e}")
            return []

    def batch_insert_cells(self, sheet_id: int, cells_data: List[Tuple[int, int, str]]) -> None:
        """
        다수의 셀 데이터를 일괄 삽입 (성능 최적화 및 안정성 강화)

        Args:
            sheet_id: 시트 ID
            cells_data: (row, col, value) 튜플의 리스트
        """
        if not cells_data:
            logging.warning(f"시트 {sheet_id}: 삽입할 셀 데이터가 없습니다.")
            return

        try:
            # 트랜잭션 시작
            self.conn.execute("BEGIN TRANSACTION")

            # 기존 시트 데이터 삭제
            delete_result = self.cursor.execute("DELETE FROM cells WHERE sheet_id = ?", (sheet_id,))
            deleted_count = delete_result.rowcount
            # 로깅 제거로 성능 향상

            # 새 데이터 준비 (빈 값 제외) - Cython 최적화 활성화
            try:
                # Cython 최적화 버전 사용 (성능 향상)
                from cython_extensions.data_processor import fast_db_batch_processing
                processed_cells = fast_db_batch_processing(cells_data)
                data = [(sheet_id, row, col, value) for row, col, value in processed_cells]
                # DB 배치 처리 Cython 최적화 사용 (로그 제거)
            except ImportError:
                # Python 폴백
                data = []
                for row, col, value in cells_data:
                    if value is not None and str(value).strip():  # 빈 문자열과 None 제외
                        data.append((sheet_id, row, col, str(value)))
                # DB 배치 처리 Python 폴백 사용 (로그 제거)

            # 새 데이터 일괄 삽입
            if data:
                self.cursor.executemany(
                    "INSERT INTO cells (sheet_id, row, col, value) VALUES (?, ?, ?, ?)",
                    data
                )
                logging.info(f"시트 {sheet_id}: {len(data)}개 셀 일괄 삽입 완료 (원본 데이터: {len(cells_data)}개)")
            else:
                logging.warning(f"시트 {sheet_id}: 유효한 데이터가 없어 삽입하지 않음")

            # 트랜잭션 커밋
            self.conn.commit()

        except sqlite3.Error as e:
            logging.error(f"시트 {sheet_id} 셀 일괄 삽입 오류: {e}")
            self.conn.rollback()
            raise
        except Exception as e:
            logging.error(f"시트 {sheet_id} 셀 일괄 삽입 중 예상치 못한 오류: {e}")
            self.conn.rollback()
            raise

    def batch_insert_cells_in_transaction(self, sheet_id: int, cells_data: List[Tuple[int, int, str]]) -> None:
        """
        다수의 셀 데이터를 일괄 삽입 (기존 트랜잭션 내에서 실행)

        Args:
            sheet_id: 시트 ID
            cells_data: (row, col, value) 튜플의 리스트
        """
        if not cells_data:
            logging.warning(f"시트 {sheet_id}: 삽입할 셀 데이터가 없습니다.")
            return

        try:
            # 🔧 기존 트랜잭션 내에서 실행하므로 별도 트랜잭션 관리 안함

            # 기존 시트 데이터 삭제
            delete_result = self.cursor.execute("DELETE FROM cells WHERE sheet_id = ?", (sheet_id,))
            deleted_count = delete_result.rowcount

            # 새 데이터 준비 (빈 값 제외) - Cython 최적화 활성화
            try:
                # Cython 최적화 버전 사용 (성능 향상)
                from cython_extensions.data_processor import fast_db_batch_processing
                processed_cells = fast_db_batch_processing(cells_data)
                data = [(sheet_id, row, col, value) for row, col, value in processed_cells]
            except ImportError:
                # Python 폴백
                data = []
                for row, col, value in cells_data:
                    if value is not None and str(value).strip():  # 빈 문자열과 None 제외
                        data.append((sheet_id, row, col, str(value)))

            # 새 데이터 일괄 삽입
            if data:
                self.cursor.executemany(
                    "INSERT INTO cells (sheet_id, row, col, value) VALUES (?, ?, ?, ?)",
                    data
                )
                logging.info(f"시트 {sheet_id}: {len(data)}개 셀 일괄 삽입 완료 (트랜잭션 내, 원본: {len(cells_data)}개)")
            else:
                logging.warning(f"시트 {sheet_id}: 유효한 데이터가 없어 삽입하지 않음")

        except sqlite3.Error as e:
            logging.error(f"시트 {sheet_id} 셀 일괄 삽입 오류 (트랜잭션 내): {e}")
            raise  # 상위 트랜잭션에서 롤백 처리
        except Exception as e:
            logging.error(f"시트 {sheet_id} 셀 일괄 삽입 중 예상치 못한 오류 (트랜잭션 내): {e}")
            raise  # 상위 트랜잭션에서 롤백 처리

    def clear_sheet(self, sheet_id: int) -> None:
        """
        시트 내용 모두 지우기

        Args:
            sheet_id: 시트 ID
        """
        try:
            self.cursor.execute("DELETE FROM cells WHERE sheet_id = ?", (sheet_id,))
            self.conn.commit()
        except sqlite3.Error as e:
            logging.error(f"시트 내용 지우기 오류: {e}")
            self.conn.rollback()
            raise

    def update_cells(self, sheet_id: int, cells_data: List[Tuple[int, int, str]]):
        """
        수정된 셀만 업데이트 (성능 최적화)

        Args:
            sheet_id: 시트 ID
            cells_data: (행, 열, 값) 튜플의 리스트
        """
        if not cells_data:
            return

        try:
            # 트랜잭션 시작
            self.conn.execute("BEGIN TRANSACTION")

            for row, col, value in cells_data:
                if value:  # 값이 있는 경우 - 저장/업데이트
                    self.cursor.execute(
                        """
                        INSERT INTO cells (sheet_id, row, col, value)
                        VALUES (?, ?, ?, ?)
                        ON CONFLICT(sheet_id, row, col)
                        DO UPDATE SET value = ?
                        """,
                        (sheet_id, row, col, value, value)
                    )
                else:  # 값이 비어있는 경우 - 삭제 (희소 행렬 유지)
                    self.cursor.execute(
                        "DELETE FROM cells WHERE sheet_id = ? AND row = ? AND col = ?",
                        (sheet_id, row, col)
                    )

            # 트랜잭션 커밋
            self.conn.commit()

        except Exception as e:
            # 오류 발생 시 롤백
            self.conn.rollback()
            logging.error(f"셀 업데이트 오류: {e}")
            raise

    def get_row_data(self, sheet_id: int, row: int) -> Dict[int, str]:
        """
        특정 행의 데이터만 가져오기 (가상화 핵심)

        Args:
            sheet_id: 시트 ID
            row: 행 번호

        Returns:
            {열 번호: 값} 형태의 딕셔너리
        """
        try:
            self.cursor.execute(
                "SELECT col, value FROM cells WHERE sheet_id = ? AND row = ? ORDER BY col",
                (sheet_id, row)
            )

            # 희소 행렬 방식으로 반환 (비어있는 셀은 딕셔너리에 포함되지 않음)
            result = self.cursor.fetchall()
            return {row['col']: row['value'] for row in result}

        except Exception as e:
            logging.error(f"행 데이터 조회 오류 (sheet_id={sheet_id}, row={row}): {e}")
            return {}

    def get_batch_rows(self, sheet_id: int, start_row: int, end_row: int) -> Dict[int, Dict[int, str]]:
        """
        🚀 성능 최적화: 여러 행의 데이터를 한 번에 가져오기 (벡터화)

        Args:
            sheet_id: 시트 ID
            start_row: 시작 행 번호
            end_row: 끝 행 번호 (포함)

        Returns:
            {행 번호: {열 번호: 값}} 형태의 중첩 딕셔너리
        """
        try:
            # 배치로 여러 행 데이터 한 번에 조회 (단일 쿼리로 성능 향상)
            self.cursor.execute(
                "SELECT row, col, value FROM cells WHERE sheet_id = ? AND row BETWEEN ? AND ? ORDER BY row, col",
                (sheet_id, start_row, end_row)
            )

            # 결과를 중첩 딕셔너리로 구성
            batch_data = {}
            for cell in self.cursor.fetchall():
                row_num = cell['row']
                col_num = cell['col']
                value = cell['value']

                if row_num not in batch_data:
                    batch_data[row_num] = {}
                batch_data[row_num][col_num] = value

            # 로깅 제거로 성능 향상
            return batch_data

        except Exception as e:
            logging.error(f"배치 행 데이터 조회 오류 (sheet_id={sheet_id}, rows={start_row}-{end_row}): {e}")
            return {}

    def delete_rows_range(self, sheet_id: int, start_row: int, count: int) -> None:
        """
        지정된 범위의 행들을 삭제

        Args:
            sheet_id: 시트 ID
            start_row: 삭제 시작 행 번호
            count: 삭제할 행 개수
        """
        try:
            # 트랜잭션 시작
            self.conn.execute("BEGIN TRANSACTION")

            # 지정된 범위의 행들 삭제
            end_row = start_row + count - 1
            self.cursor.execute(
                "DELETE FROM cells WHERE sheet_id = ? AND row >= ? AND row <= ?",
                (sheet_id, start_row, end_row)
            )

            deleted_count = self.cursor.rowcount
            logging.debug(f"시트 {sheet_id}: 행 {start_row}~{end_row} 삭제 완료 ({deleted_count}개 셀)")

            # 트랜잭션 커밋
            self.conn.commit()

        except sqlite3.Error as e:
            logging.error(f"행 삭제 오류 (sheet_id={sheet_id}, start_row={start_row}, count={count}): {e}")
            self.conn.rollback()
            raise
        except Exception as e:
            logging.error(f"행 삭제 중 예상치 못한 오류: {e}")
            self.conn.rollback()
            raise

    def delete_columns_range(self, sheet_id: int, start_col: int, count: int) -> None:
        """
        지정된 범위의 열들을 삭제

        Args:
            sheet_id: 시트 ID
            start_col: 삭제 시작 열 번호
            count: 삭제할 열 개수
        """
        try:
            # 트랜잭션 시작
            self.conn.execute("BEGIN TRANSACTION")

            # 지정된 범위의 열들 삭제
            end_col = start_col + count - 1
            self.cursor.execute(
                "DELETE FROM cells WHERE sheet_id = ? AND col >= ? AND col <= ?",
                (sheet_id, start_col, end_col)
            )

            deleted_count = self.cursor.rowcount
            logging.debug(f"시트 {sheet_id}: 열 {start_col}~{end_col} 삭제 완료 ({deleted_count}개 셀)")

            # 트랜잭션 커밋
            self.conn.commit()

        except sqlite3.Error as e:
            logging.error(f"열 삭제 오류 (sheet_id={sheet_id}, start_col={start_col}, count={count}): {e}")
            self.conn.rollback()
            raise
        except Exception as e:
            logging.error(f"열 삭제 중 예상치 못한 오류: {e}")
            self.conn.rollback()
            raise

    def shift_rows(self, sheet_id: int, start_row: int, shift_amount: int) -> None:
        """
        지정된 행부터 모든 행을 위/아래로 이동 - 안전성 강화

        Args:
            sheet_id: 시트 ID
            start_row: 이동 시작 행 번호
            shift_amount: 이동할 행 수 (양수: 아래로, 음수: 위로)
        """
        try:
            # 트랜잭션 시작
            self.conn.execute("BEGIN TRANSACTION")

            if shift_amount == 0:
                # 이동할 필요 없음
                self.conn.commit()
                return

            # 이동 전 영향받는 셀 수 확인
            self.cursor.execute("""
                SELECT COUNT(*) FROM cells
                WHERE sheet_id = ? AND row >= ?
            """, (sheet_id, start_row))
            cells_to_move = self.cursor.fetchone()[0]

            logging.debug(f"시트 {sheet_id}: 행 {start_row}부터 {shift_amount}만큼 이동 예정 ({cells_to_move}개 셀)")

            if shift_amount > 0:
                # 아래로 이동 (행 삽입 시): 간단한 방법 사용
                # 큰 행 번호부터 역순으로 처리하여 충돌 방지
                self.cursor.execute("""
                    SELECT DISTINCT row FROM cells
                    WHERE sheet_id = ? AND row >= ?
                    ORDER BY row DESC
                """, (sheet_id, start_row))

                rows_to_move = [row[0] for row in self.cursor.fetchall()]

                # 큰 행 번호부터 역순으로 이동
                for row in rows_to_move:
                    self.cursor.execute("""
                        UPDATE cells
                        SET row = row + ?
                        WHERE sheet_id = ? AND row = ?
                    """, (shift_amount, sheet_id, row))

            elif shift_amount < 0:
                # 위로 이동 (행 삭제 시): 직접 이동 (음수 이동이므로 충돌 없음)
                self.cursor.execute("""
                    UPDATE cells
                    SET row = row + ?
                    WHERE sheet_id = ? AND row >= ?
                """, (shift_amount, sheet_id, start_row))

            affected_count = self.cursor.rowcount
            logging.debug(f"시트 {sheet_id}: 행 이동 완료 ({affected_count}개 셀 이동)")

            # 트랜잭션 커밋
            self.conn.commit()

        except sqlite3.Error as e:
            logging.error(f"행 이동 오류 (sheet_id={sheet_id}, start_row={start_row}, shift={shift_amount}): {e}")
            self.conn.rollback()
            raise
        except Exception as e:
            logging.error(f"행 이동 중 예상치 못한 오류: {e}")
            self.conn.rollback()
            raise

    def shift_columns(self, sheet_id: int, start_col: int, shift_amount: int) -> None:
        """
        지정된 열부터 모든 열을 좌/우로 이동 - 안전성 강화

        Args:
            sheet_id: 시트 ID
            start_col: 이동 시작 열 번호
            shift_amount: 이동할 열 수 (양수: 오른쪽으로, 음수: 왼쪽으로)
        """
        try:
            # 트랜잭션 시작
            self.conn.execute("BEGIN TRANSACTION")

            if shift_amount == 0:
                # 이동할 필요 없음
                self.conn.commit()
                return

            # 이동 전 영향받는 셀 수 확인
            self.cursor.execute("""
                SELECT COUNT(*) FROM cells
                WHERE sheet_id = ? AND col >= ?
            """, (sheet_id, start_col))
            cells_to_move = self.cursor.fetchone()[0]

            logging.debug(f"시트 {sheet_id}: 열 {start_col}부터 {shift_amount}만큼 이동 예정 ({cells_to_move}개 셀)")

            if shift_amount > 0:
                # 오른쪽으로 이동 (열 삽입 시): 간단한 방법 사용
                # 큰 열 번호부터 역순으로 처리하여 충돌 방지
                self.cursor.execute("""
                    SELECT DISTINCT col FROM cells
                    WHERE sheet_id = ? AND col >= ?
                    ORDER BY col DESC
                """, (sheet_id, start_col))

                cols_to_move = [col[0] for col in self.cursor.fetchall()]

                # 큰 열 번호부터 역순으로 이동
                for col in cols_to_move:
                    self.cursor.execute("""
                        UPDATE cells
                        SET col = col + ?
                        WHERE sheet_id = ? AND col = ?
                    """, (shift_amount, sheet_id, col))

            elif shift_amount < 0:
                # 왼쪽으로 이동 (열 삭제 시): 직접 이동 (음수 이동이므로 충돌 없음)
                self.cursor.execute("""
                    UPDATE cells
                    SET col = col + ?
                    WHERE sheet_id = ? AND col >= ?
                """, (shift_amount, sheet_id, start_col))

            affected_count = self.cursor.rowcount
            logging.debug(f"시트 {sheet_id}: 열 이동 완료 ({affected_count}개 셀 이동)")

            # 트랜잭션 커밋
            self.conn.commit()

        except sqlite3.Error as e:
            logging.error(f"열 이동 오류 (sheet_id={sheet_id}, start_col={start_col}, shift={shift_amount}): {e}")
            self.conn.rollback()
            raise
        except Exception as e:
            logging.error(f"열 이동 중 예상치 못한 오류: {e}")
            self.conn.rollback()
            raise

    def update_sheet_order(self, sheet_id: int, new_order: int):
        """
        시트 순서 업데이트

        Args:
            sheet_id: 시트 ID
            new_order: 새 순서 값
        """
        try:
            self.cursor.execute(
                "UPDATE sheets SET sheet_order = ? WHERE id = ?",
                (new_order, sheet_id)
            )
            self.conn.commit()
        except Exception as e:
            self.conn.rollback()
            logging.error(f"시트 순서 업데이트 오류: {e}")
            raise
