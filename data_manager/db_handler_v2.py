import sqlite3
from typing import Dict, List, Any, Tuple, Optional
import os
import logging
import gc

# Cython 최적화 모듈 import (성능 향상)
try:
    from cython_extensions.data_processor import (
        fast_db_batch_processing,
        fast_sheet_data_loading,
        # fast_data_filtering, # Vulture: unused
    )

    USE_CYTHON_DB = True
    logging.info("✓ Cython DB 최적화 모듈 로드 성공")
except ImportError as e:
    USE_CYTHON_DB = False
    logging.warning(f"⚠ Cython DB 모듈 로드 실패, Python 폴백 사용: {e}")


class DBHandlerV2:
    """
    SQLite 데이터베이스 연결 및 쿼리 처리를 위한 단순화된 클래스 (2계층: DB → 시트).

    이 클래스는 SQLite 데이터베이스 파일과의 연결을 관리하고,
    시트 및 셀 데이터의 생성, 조회, 수정, 삭제 작업을 수행하는 메소드들을 제공합니다.
    성능 최적화를 위해 PRAGMA 설정을 적용하고, Cython 확장 모듈 사용을 시도합니다.

    Attributes:
        db_file (str): 데이터베이스 파일의 경로.
        conn (Optional[sqlite3.Connection]): SQLite 데이터베이스 연결 객체.
        cursor (Optional[sqlite3.Cursor]): 데이터베이스 커서 객체.
    """

    def __init__(self, db_file: Optional[str] = None):
        """
        DBHandlerV2 객체를 초기화합니다.

        db_file 경로가 제공되면 데이터베이스 연결을 시도하고 기본 테이블을 초기화합니다.

        Args:
            db_file (Optional[str]): 데이터베이스 파일 경로. None인 경우 연결을 설정하지 않습니다.
        """
        self.db_file: Optional[str] = db_file
        self.db_file_path: Optional[str] = db_file  # Git 관련 코드 호환성을 위한 별칭
        self.conn: Optional[sqlite3.Connection] = None
        self.cursor: Optional[sqlite3.Cursor] = None

        if db_file is not None:
            self.connect()
            self.init_tables()

    def connect(self) -> None:
        """
        데이터베이스 파일을 열고 연결(connection) 및 커서(cursor) 객체를 설정합니다.

        SQLite 성능 최적화를 위한 여러 PRAGMA 설정을 시도합니다.
        연결 실패 시 sqlite3.Error를 발생시킬 수 있습니다.

        Raises:
            sqlite3.Error: 데이터베이스 연결 과정에서 오류 발생 시.
        """
        try:
            if self.db_file is None:
                logging.error("DB 파일이 지정되지 않아 연결할 수 없습니다.")
                raise sqlite3.Error("DB 파일 경로가 None입니다.")

            self.conn = sqlite3.connect(self.db_file, check_same_thread=False)
            self.conn.row_factory = sqlite3.Row
            self.cursor = self.conn.cursor()

            performance_pragmas = [
                "PRAGMA journal_mode = WAL",
                "PRAGMA synchronous = NORMAL",
                "PRAGMA cache_size = 100000",
                "PRAGMA temp_store = MEMORY",
                "PRAGMA mmap_size = 268435456",
                "PRAGMA optimize",
            ]

            for pragma in performance_pragmas:
                try:
                    self.cursor.execute(pragma)
                except sqlite3.Error as e:
                    logging.warning(f"PRAGMA 설정 실패: {pragma} - {e}")

            logging.info(f"SQLite DB '{self.db_file}' 연결 성공 (V2, 성능 최적화 적용)")
        except sqlite3.Error as e:
            logging.error(f"SQLite 연결 오류 ({self.db_file}): {e}")
            raise

    def disconnect(self) -> None:
        """데이터베이스 연결을 종료합니다."""
        if self.conn:
            self.conn.close()
            self.conn = None
            self.cursor = None
            logging.info(f"SQLite DB 연결 종료 (V2): {self.db_file}")

    def init_tables(self) -> None:
        """
        데이터베이스에 필요한 기본 테이블들('sheets', 'cells')을 생성합니다.

        테이블이 이미 존재하면 생성하지 않습니다. 성능 향상을 위한 인덱스도 함께 생성합니다.
        테이블 또는 인덱스 생성 실패 시 sqlite3.Error를 발생시킬 수 있습니다.

        Raises:
            sqlite3.Error: 테이블 또는 인덱스 생성 과정에서 오류 발생 시.
        """
        if not self.cursor or not self.conn:
            logging.error("DB 연결이 없습니다. 테이블을 초기화할 수 없습니다.")
            return

        try:
            self.cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS sheets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    is_dollar_sheet BOOLEAN NOT NULL DEFAULT 0,
                    sheet_order INTEGER NOT NULL DEFAULT 0,
                    source_file TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
            )
            self.cursor.execute(
                """
            CREATE TABLE IF NOT EXISTS cells (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sheet_id INTEGER NOT NULL,
                row INTEGER NOT NULL,
                col INTEGER NOT NULL,
                value TEXT,
                FOREIGN KEY (sheet_id) REFERENCES sheets (id) ON DELETE CASCADE,
                UNIQUE(sheet_id, row, col)
            )
            """
            )
            performance_indexes = [
                "CREATE INDEX IF NOT EXISTS idx_cells_sheet_row ON cells(sheet_id, row)",
                "CREATE INDEX IF NOT EXISTS idx_cells_sheet_row_col ON cells(sheet_id, row, col)",
                "CREATE INDEX IF NOT EXISTS idx_sheets_name ON sheets(name)",
                "CREATE INDEX IF NOT EXISTS idx_sheets_dollar ON sheets(is_dollar_sheet)",
            ]
            for index_sql in performance_indexes:
                try:
                    self.cursor.execute(index_sql)
                except sqlite3.Error as e:
                    logging.warning(f"인덱스 생성 실패: {index_sql} - {e}")
            self.conn.commit()
            logging.info("테이블 초기화 완료 (V2, 성능 최적화 인덱스 포함)")
        except sqlite3.Error as e:
            logging.error(f"테이블 초기화 오류: {e}")
            if self.conn: self.conn.rollback()
            raise

    def create_sheet_v2(
        self,
        sheet_name: str,
        is_dollar_sheet: bool = False,
        sheet_order: int = 0,
        source_file: Optional[str] = None,
        replace_if_exists: bool = True,
    ) -> int:
        """
        새로운 시트를 데이터베이스에 생성합니다.

        Args:
            sheet_name (str): 생성할 시트의 이름.
            is_dollar_sheet (bool): '$' 문자로 시작하는 특수 시트인지 여부. 기본값은 False.
            sheet_order (int): 시트의 정렬 순서. 기본값은 0.
            source_file (Optional[str]): 이 시트의 원본이 된 파일 경로 (선택 사항).
            replace_if_exists (bool): 동일한 이름의 시트가 이미 존재할 경우,
                                      기존 시트를 삭제하고 새로 생성할지 여부. 기본값은 True.

        Returns:
            int: 생성되거나 기존에 존재하던 시트의 ID.

        Raises:
            sqlite3.Error: 시트 생성 또는 기존 시트 처리 중 DB 오류 발생 시.
        """
        if not self.cursor or not self.conn:
            logging.error("DB 연결이 없습니다. 시트를 생성할 수 없습니다.")
            raise sqlite3.Error("데이터베이스에 연결되지 않았습니다.")

        try:
            existing_sheet = self.get_sheet_by_name(sheet_name)
            if existing_sheet:
                if replace_if_exists:
                    logging.info(f"기존 시트 '{sheet_name}' 발견, 교체 진행 (ID: {existing_sheet['id']})")
                    self.delete_sheet(existing_sheet["id"])
                else:
                    logging.info(f"기존 시트 '{sheet_name}' 사용 (ID: {existing_sheet['id']})")
                    return existing_sheet["id"]

            self.cursor.execute(
                "INSERT INTO sheets (name, is_dollar_sheet, sheet_order, source_file) VALUES (?, ?, ?, ?)",
                (sheet_name, 1 if is_dollar_sheet else 0, sheet_order, source_file),
            )
            self.conn.commit()
            sheet_id = self.cursor.lastrowid
            logging.info(f"새 시트 '{sheet_name}' 생성 완료 (ID: {sheet_id})")
            return sheet_id
        except sqlite3.IntegrityError as e:
            if "UNIQUE constraint failed: sheets.name" in str(e) and not replace_if_exists:
                logging.warning(f"시트명 중복: '{sheet_name}'. replace_if_exists=False이므로 기존 시트 ID를 반환 시도합니다.")
                # 이 경우, 기존 시트 ID를 다시 조회하여 반환하거나, 오류를 그대로 전달할 수 있습니다.
                # 여기서는 오류를 발생시켜 호출자가 처리하도록 합니다.
                raise
            logging.error(f"시트 생성 중 무결성 오류 ('{sheet_name}'): {e}")
            if self.conn: self.conn.rollback()
            raise
        except sqlite3.Error as e:
            logging.error(f"시트 생성 오류 ('{sheet_name}'): {e}")
            if self.conn: self.conn.rollback()
            raise

    def get_sheets(self) -> List[Dict[str, Any]]:
        """
        데이터베이스에 저장된 모든 시트의 목록을 조회합니다.

        Returns:
            List[Dict[str, Any]]: 각 시트의 정보를 담은 딕셔너리 리스트.
                                 각 딕셔너리는 'id', 'name', 'is_dollar_sheet', 'order', 'source_file' 키를 가집니다.
                                 오류 발생 시 빈 리스트를 반환할 수 있습니다.
        """
        if not self.cursor:
            logging.error("DB 연결이 없습니다. 시트 목록을 조회할 수 없습니다.")
            return []
        try:
            self.cursor.execute(
                "SELECT id, name, is_dollar_sheet, sheet_order, source_file FROM sheets ORDER BY sheet_order, id"
            )
            return [dict(row) for row in self.cursor.fetchall()]
        except sqlite3.Error as e:
            logging.error(f"시트 목록 조회 오류: {e}")
            return [] # 오류 발생 시 빈 리스트 반환

    def get_sheet_by_id(self, sheet_id: int) -> Optional[Dict[str, Any]]:
        """
        주어진 ID를 가진 시트의 정보를 조회합니다.

        Args:
            sheet_id (int): 조회할 시트의 ID.

        Returns:
            Optional[Dict[str, Any]]: 시트 정보를 담은 딕셔너리. 해당 ID의 시트가 없으면 None을 반환합니다.
        """
        if not self.cursor:
            logging.error("DB 연결이 없습니다. 시트 정보를 조회할 수 없습니다.")
            return None
        try:
            self.cursor.execute(
                "SELECT id, name, is_dollar_sheet, sheet_order, source_file FROM sheets WHERE id = ?", (sheet_id,)
            )
            row = self.cursor.fetchone()
            return dict(row) if row else None
        except sqlite3.Error as e:
            logging.error(f"ID로 시트 조회 오류 (ID: {sheet_id}): {e}")
            return None

    def get_sheet_by_name(self, sheet_name: str) -> Optional[Dict[str, Any]]:
        """
        주어진 이름을 가진 시트의 정보를 조회합니다.

        Args:
            sheet_name (str): 조회할 시트의 이름.

        Returns:
            Optional[Dict[str, Any]]: 시트 정보를 담은 딕셔너리. 해당 이름의 시트가 없으면 None을 반환합니다.
        """
        if not self.cursor:
            logging.error("DB 연결이 없습니다. 시트 정보를 조회할 수 없습니다.")
            return None
        try:
            self.cursor.execute(
                "SELECT id, name, is_dollar_sheet, sheet_order, source_file FROM sheets WHERE name = ?", (sheet_name,)
            )
            row = self.cursor.fetchone()
            return dict(row) if row else None
        except sqlite3.Error as e:
            logging.error(f"이름으로 시트 조회 오류 ('{sheet_name}'): {e}")
            return None

    def rename_sheet(self, sheet_id: int, new_name: str, is_dollar_sheet: Optional[bool] = None) -> None:
        """
        지정된 ID를 가진 시트의 이름 및 '$' 시트 여부를 변경합니다.

        Args:
            sheet_id (int): 변경할 시트의 ID.
            new_name (str): 새로운 시트 이름.
            is_dollar_sheet (Optional[bool]): 새로운 '$' 시트 여부. None이면 변경하지 않습니다.

        Raises:
            sqlite3.Error: 업데이트 중 DB 오류 발생 시.
        """
        if not self.cursor or not self.conn:
            logging.error("DB 연결이 없습니다. 시트 이름을 변경할 수 없습니다.")
            raise sqlite3.Error("데이터베이스에 연결되지 않았습니다.")
        try:
            if is_dollar_sheet is None:
                self.cursor.execute("UPDATE sheets SET name = ? WHERE id = ?", (new_name, sheet_id))
            else:
                self.cursor.execute(
                    "UPDATE sheets SET name = ?, is_dollar_sheet = ? WHERE id = ?",
                    (new_name, 1 if is_dollar_sheet else 0, sheet_id),
                )
            self.conn.commit()
            logging.info(f"시트 ID {sheet_id}의 이름이 '{new_name}'(으)로 변경되었습니다.")
        except sqlite3.Error as e:
            logging.error(f"시트 이름 변경 오류 (ID: {sheet_id}): {e}")
            if self.conn: self.conn.rollback()
            raise

    def delete_sheet(self, sheet_id: int) -> None:
        """
        지정된 ID의 시트를 데이터베이스에서 삭제합니다.

        FOREIGN KEY 설정에 따라 연관된 셀 데이터('cells' 테이블)도 함께 삭제됩니다.

        Args:
            sheet_id (int): 삭제할 시트의 ID.

        Raises:
            sqlite3.Error: 삭제 중 DB 오류 발생 시.
        """
        if not self.cursor or not self.conn:
            logging.error("DB 연결이 없습니다. 시트를 삭제할 수 없습니다.")
            raise sqlite3.Error("데이터베이스에 연결되지 않았습니다.")
        try:
            self.cursor.execute("DELETE FROM sheets WHERE id = ?", (sheet_id,))
            self.conn.commit()
            logging.info(f"시트 ID {sheet_id}가 성공적으로 삭제되었습니다.")
        except sqlite3.Error as e:
            logging.error(f"시트 삭제 오류 (ID: {sheet_id}): {e}")
            if self.conn: self.conn.rollback()
            raise

    def delete_sheets_by_source_file(self, source_file: str) -> int:
        """
        특정 원본 파일(`source_file`)과 연관된 모든 시트를 삭제합니다.

        Args:
            source_file (str): 삭제할 시트들의 원본 파일명.

        Returns:
            int: 삭제된 시트의 개수.

        Raises:
            sqlite3.Error: 삭제 중 DB 오류 발생 시.
        """
        if not self.cursor or not self.conn:
            logging.error("DB 연결이 없습니다. 원본 파일로 시트를 삭제할 수 없습니다.")
            raise sqlite3.Error("데이터베이스에 연결되지 않았습니다.")
        try:
            self.cursor.execute("SELECT id, name FROM sheets WHERE source_file = ?", (source_file,))
            sheets_to_delete = self.cursor.fetchall()
            if not sheets_to_delete:
                logging.info(f"삭제할 시트가 없습니다 (source_file: '{source_file}')")
                return 0

            self.cursor.execute("DELETE FROM sheets WHERE source_file = ?", (source_file,))
            deleted_count = self.cursor.rowcount
            self.conn.commit()
            logging.info(f"source_file '{source_file}'의 {deleted_count}개 시트 삭제 완료.")
            for sheet in sheets_to_delete:
                logging.debug(f"  - 삭제된 시트: '{sheet['name']}' (ID: {sheet['id']})")
            return deleted_count
        except sqlite3.Error as e:
            logging.error(f"원본 파일로 시트 삭제 오류 ('{source_file}'): {e}")
            if self.conn: self.conn.rollback()
            raise

    def set_cell_value(self, sheet_id: int, row: int, col: int, value: str) -> None:
        """
        지정된 시트의 특정 셀에 값을 설정(삽입 또는 업데이트)합니다.

        Args:
            sheet_id (int): 값을 설정할 시트의 ID.
            row (int): 셀의 행 번호.
            col (int): 셀의 열 번호.
            value (str): 셀에 저장할 값.

        Raises:
            sqlite3.Error: 값 설정 중 DB 오류 발생 시.
        """
        if not self.cursor or not self.conn:
            logging.error("DB 연결이 없습니다. 셀 값을 설정할 수 없습니다.")
            raise sqlite3.Error("데이터베이스에 연결되지 않았습니다.")
        try:
            self.cursor.execute(
                "INSERT INTO cells (sheet_id, row, col, value) VALUES (?, ?, ?, ?) ON CONFLICT(sheet_id, row, col) DO UPDATE SET value = excluded.value",
                (sheet_id, row, col, value),
            )
            self.conn.commit()
        except sqlite3.Error as e:
            logging.error(f"셀 값 설정 오류 (sheet_id={sheet_id}, row={row}, col={col}): {e}")
            if self.conn: self.conn.rollback()
            raise

    def get_cell_value(self, sheet_id: int, row: int, col: int) -> str:
        """
        지정된 시트의 특정 셀 값을 조회합니다.

        Args:
            sheet_id (int): 값을 조회할 시트의 ID.
            row (int): 셀의 행 번호.
            col (int): 셀의 열 번호.

        Returns:
            str: 조회된 셀 값. 셀이 없거나 값이 None이면 빈 문자열을 반환합니다.
        """
        if not self.cursor:
            logging.error("DB 연결이 없습니다. 셀 값을 조회할 수 없습니다.")
            return ""
        try:
            self.cursor.execute(
                "SELECT value FROM cells WHERE sheet_id = ? AND row = ? AND col = ?",
                (sheet_id, row, col),
            )
            result = self.cursor.fetchone()
            return result["value"] if result and result["value"] is not None else ""
        except sqlite3.Error as e:
            logging.error(f"셀 값 조회 오류 (sheet_id={sheet_id}, row={row}, col={col}): {e}")
            return ""

    def get_sheet_data(self, sheet_id: int) -> List[List[str]]:
        """
        특정 시트의 모든 셀 데이터를 2차원 리스트 형태로 가져옵니다.

        성능 최적화를 위해 시트의 최대 행/열 크기를 먼저 조회한 후,
        배치 단위로 셀 데이터를 로드하여 메모리에 재구성합니다.
        Cython 확장 모듈(`fast_sheet_data_loading`)이 사용 가능하면 이를 활용합니다.

        Args:
            sheet_id (int): 데이터를 가져올 시트의 ID.

        Returns:
            List[List[str]]: 시트 데이터를 나타내는 2차원 문자열 리스트.
                             오류 발생 또는 데이터 부재 시 빈 리스트를 반환할 수 있습니다.
        Raises:
            sqlite3.Error: 데이터 조회 중 DB 오류 발생 시.
        """
        if not self.cursor:
            logging.error("DB 연결이 없습니다. 시트 데이터를 가져올 수 없습니다.")
            return []

        gc.collect() # 명시적 가비지 컬렉션 호출
        try:
            self.cursor.execute(
                "SELECT MAX(row) as max_row, MAX(col) as max_col, COUNT(*) as cell_count FROM cells WHERE sheet_id = ? AND value IS NOT NULL AND value != ''",
                (sheet_id,),
            )
            result = self.cursor.fetchone()
            if not result or result["max_row"] is None: return []

            max_row, max_col, cell_count = result["max_row"], result["max_col"], result["cell_count"]
            logging.debug(f"시트 {sheet_id}: {max_row+1}x{max_col+1} 크기, {cell_count}개 셀")

            sheet_data = [["" for _ in range(max_col + 1)] for _ in range(max_row + 1)]
            batch_size = 50000
            offset = 0

            while True:
                self.cursor.execute(
                    "SELECT row, col, value FROM cells WHERE sheet_id = ? AND value IS NOT NULL AND value != '' ORDER BY row, col LIMIT ? OFFSET ?",
                    (sheet_id, batch_size, offset),
                )
                batch = self.cursor.fetchall()
                if not batch: break

                if USE_CYTHON_DB and 'fast_sheet_data_loading' in globals():
                    batch_dict = [{"row": cell["row"], "col": cell["col"], "value": cell["value"]} for cell in batch]
                    fast_sheet_data_loading(batch_dict, sheet_data) # sheet_data를 직접 수정
                else:
                    for cell in batch: sheet_data[cell["row"]][cell["col"]] = cell["value"]

                offset += len(batch)
                if offset % (batch_size * 4) == 0:
                    gc.collect()
                    logging.debug(f"시트 {sheet_id}: {offset}개 셀 처리 완료, 메모리 정리")

            logging.info(f"시트 {sheet_id} 데이터 로드 완료: {max_row+1}x{max_col+1}, {cell_count}개 셀")
            return sheet_data
        except sqlite3.Error as e:
            logging.error(f"시트 데이터 가져오기 오류 (ID: {sheet_id}): {e}")
            raise

    def get_sheet_metadata(self, sheet_id: int) -> Dict[str, Any]:
        """
        시트의 메타데이터(최대 행/열 수)를 가져옵니다.

        실제 데이터가 있는 최대 행/열을 기준으로 하되, 최소 100행 50열을 보장합니다.

        Args:
            sheet_id (int): 메타데이터를 조회할 시트의 ID.

        Returns:
            Dict[str, Any]: 'max_row'와 'max_col' 키를 포함하는 딕셔너리.
                            오류 발생 시 기본값으로 {'max_row': 100, 'max_col': 50}을 반환합니다.
        """
        if not self.cursor:
            logging.error("DB 연결이 없습니다. 시트 메타데이터를 조회할 수 없습니다.")
            return {"max_row": 100, "max_col": 50}
        try:
            self.cursor.execute("SELECT MAX(row) as max_row, MAX(col) as max_col FROM cells WHERE sheet_id = ?", (sheet_id,))
            result = self.cursor.fetchone()
            max_row = result["max_row"] if result and result["max_row"] is not None else 0
            max_col = result["max_col"] if result and result["max_col"] is not None else 0
            return {"max_row": max(max_row, 100), "max_col": max(max_col, 50)}
        except sqlite3.Error as e:
            logging.error(f"시트 메타데이터 조회 오류 (ID: {sheet_id}): {e}")
            return {"max_row": 100, "max_col": 50}

    # get_files 메서드는 DBHandlerV2의 역할 범위를 벗어날 수 있으므로,
    # DBManager 등 상위 관리 클래스에서 파일 시스템 정보를 직접 다루는 것이 적절할 수 있습니다.
    # 여기서는 DB 파일 자체에 대한 정보만 반환하도록 유지합니다.
    def get_files(self) -> List[Dict[str, Any]]:
        """
        현재 연결된 DB 파일에 대한 정보를 반환합니다. (V2에서는 단일 DB 파일만 관리)

        Returns:
            List[Dict[str, Any]]: DB 파일 정보를 담은 딕셔너리를 포함하는 리스트.
                                 DB 파일이 지정되지 않았거나 오류 발생 시 빈 리스트 반환.
        """
        if not self.db_file:
            return []
        try:
            file_path = Path(self.db_file)
            return [{
                "id": 1, "name": file_path.stem, "path": str(file_path),
                "size": os.path.getsize(self.db_file) if os.path.exists(self.db_file) else 0,
            }]
        except Exception as e:
            logging.error(f"DB 파일 정보 조회 오류: {e}")
            return []

    def batch_insert_cells(self, sheet_id: int, cells_data: List[Tuple[int, int, str]]) -> None:
        """
        지정된 시트에 다수의 셀 데이터를 일괄 삽입/업데이트합니다.

        기존 시트의 모든 셀 데이터를 삭제한 후, 제공된 `cells_data`를 삽입합니다.
        Cython 최적화 함수(`fast_db_batch_processing`)가 사용 가능하면 이를 활용합니다.
        빈 값(None 또는 공백 문자열)은 데이터베이스에 저장되지 않습니다.

        Args:
            sheet_id (int): 데이터를 삽입할 시트의 ID.
            cells_data (List[Tuple[int, int, str]]): (행, 열, 값) 형태의 튜플 리스트.

        Raises:
            sqlite3.Error: 데이터베이스 작업 중 오류 발생 시.
        """
        if not self.cursor or not self.conn:
            logging.error("DB 연결이 없습니다. 셀 데이터를 일괄 삽입할 수 없습니다.")
            raise sqlite3.Error("데이터베이스에 연결되지 않았습니다.")
        if not cells_data:
            logging.info(f"시트 {sheet_id}: 삽입할 셀 데이터가 없습니다. 기존 데이터만 삭제됩니다 (있는 경우).")
            # 기존 데이터 삭제는 아래 로직에서 처리됨

        try:
            self.conn.execute("BEGIN TRANSACTION")
            delete_result = self.cursor.execute("DELETE FROM cells WHERE sheet_id = ?", (sheet_id,))
            logging.debug(f"시트 {sheet_id}: 기존 {delete_result.rowcount}개 셀 삭제")

            data_to_insert = []
            if USE_CYTHON_DB and 'fast_db_batch_processing' in globals():
                # fast_db_batch_processing는 (row, col, value) 튜플 리스트를 반환해야 함
                processed_cells = fast_db_batch_processing(cells_data)
                data_to_insert = [(sheet_id, r, c, v) for r, c, v in processed_cells if v is not None and str(v).strip()]
            else:
                for row, col, value in cells_data:
                    if value is not None and str(value).strip():
                        data_to_insert.append((sheet_id, row, col, str(value)))

            if data_to_insert:
                self.cursor.executemany("INSERT INTO cells (sheet_id, row, col, value) VALUES (?, ?, ?, ?)", data_to_insert)
                logging.info(f"시트 {sheet_id}: {len(data_to_insert)}개 셀 일괄 삽입 완료 (원본: {len(cells_data)}개).")
            else:
                logging.info(f"시트 {sheet_id}: 유효한 데이터가 없어 삽입하지 않음.")

            self.conn.commit()
        except sqlite3.Error as e:
            logging.error(f"시트 {sheet_id} 셀 일괄 삽입 오류: {e}")
            if self.conn: self.conn.rollback()
            raise

    def clear_sheet(self, sheet_id: int) -> None:
        """
        지정된 시트의 모든 셀 데이터를 삭제합니다.

        Args:
            sheet_id (int): 내용을 삭제할 시트의 ID.

        Raises:
            sqlite3.Error: 삭제 중 DB 오류 발생 시.
        """
        if not self.cursor or not self.conn:
            logging.error("DB 연결이 없습니다. 시트 내용을 삭제할 수 없습니다.")
            raise sqlite3.Error("데이터베이스에 연결되지 않았습니다.")
        try:
            self.cursor.execute("DELETE FROM cells WHERE sheet_id = ?", (sheet_id,))
            self.conn.commit()
            logging.info(f"시트 ID {sheet_id}의 내용이 모두 삭제되었습니다.")
        except sqlite3.Error as e:
            logging.error(f"시트 내용 삭제 오류 (ID: {sheet_id}): {e}")
            if self.conn: self.conn.rollback()
            raise

    def update_cells(self, sheet_id: int, cells_data: List[Tuple[int, int, str]]) -> None:
        """
        지정된 시트의 특정 셀들을 업데이트하거나 삽입/삭제합니다.

        `cells_data` 리스트에 포함된 각 (행, 열, 값) 튜플에 대해,
        값이 존재하면 해당 셀을 삽입하거나 업데이트하고, 값이 비어있으면 해당 셀을 삭제합니다.
        모든 작업은 단일 트랜잭션 내에서 수행됩니다.

        Args:
            sheet_id (int): 업데이트할 시트의 ID.
            cells_data (List[Tuple[int, int, str]]): 변경할 셀 정보 튜플들의 리스트.

        Raises:
            sqlite3.Error: DB 작업 중 오류 발생 시.
        """
        if not self.cursor or not self.conn:
            logging.error("DB 연결이 없습니다. 셀을 업데이트할 수 없습니다.")
            raise sqlite3.Error("데이터베이스에 연결되지 않았습니다.")
        if not cells_data: return

        try:
            self.conn.execute("BEGIN TRANSACTION")
            for row, col, value in cells_data:
                if value:  # 값이 있는 경우 - 저장/업데이트
                    self.cursor.execute(
                        "INSERT INTO cells (sheet_id, row, col, value) VALUES (?, ?, ?, ?) ON CONFLICT(sheet_id, row, col) DO UPDATE SET value = excluded.value",
                        (sheet_id, row, col, value),
                    )
                else:  # 값이 비어있는 경우 - 삭제
                    self.cursor.execute("DELETE FROM cells WHERE sheet_id = ? AND row = ? AND col = ?", (sheet_id, row, col))
            self.conn.commit()
        except sqlite3.Error as e:
            logging.error(f"셀 업데이트 오류 (ID: {sheet_id}): {e}")
            if self.conn: self.conn.rollback()
            raise

    def get_row_data(self, sheet_id: int, row: int) -> Dict[int, str]:
        """
        특정 시트의 지정된 한 행의 데이터를 가져옵니다.

        희소 행렬(sparse matrix) 방식으로, 값이 있는 셀만 {열_번호: 값} 형태의 딕셔너리로 반환합니다.

        Args:
            sheet_id (int): 데이터를 가져올 시트의 ID.
            row (int): 가져올 행 번호.

        Returns:
            Dict[int, str]: 해당 행의 데이터를 {열_번호: 값} 형태로 담은 딕셔너리.
                            오류 발생 또는 데이터 부재 시 빈 딕셔너리를 반환합니다.
        """
        if not self.cursor:
            logging.error("DB 연결이 없습니다. 행 데이터를 조회할 수 없습니다.")
            return {}
        try:
            self.cursor.execute("SELECT col, value FROM cells WHERE sheet_id = ? AND row = ? ORDER BY col", (sheet_id, row))
            return {db_row["col"]: db_row["value"] for db_row in self.cursor.fetchall()}
        except sqlite3.Error as e:
            logging.error(f"행 데이터 조회 오류 (sheet_id={sheet_id}, row={row}): {e}")
            return {}

    def delete_rows_range(self, sheet_id: int, start_row: int, count: int) -> None:
        """
        지정된 시트에서 특정 범위의 행들을 삭제합니다.

        Args:
            sheet_id (int): 행을 삭제할 시트의 ID.
            start_row (int): 삭제를 시작할 행 번호.
            count (int): 삭제할 행의 개수.

        Raises:
            sqlite3.Error: DB 작업 중 오류 발생 시.
        """
        if not self.cursor or not self.conn:
            logging.error("DB 연결이 없습니다. 행 범위를 삭제할 수 없습니다.")
            raise sqlite3.Error("데이터베이스에 연결되지 않았습니다.")
        try:
            self.conn.execute("BEGIN TRANSACTION")
            end_row = start_row + count - 1
            self.cursor.execute("DELETE FROM cells WHERE sheet_id = ? AND row >= ? AND row <= ?", (sheet_id, start_row, end_row))
            deleted_count = self.cursor.rowcount
            logging.debug(f"시트 {sheet_id}: 행 {start_row}~{end_row} 삭제 완료 ({deleted_count}개 셀)")
            self.conn.commit()
        except sqlite3.Error as e:
            logging.error(f"행 범위 삭제 오류 (sheet_id={sheet_id}, start_row={start_row}, count={count}): {e}")
            if self.conn: self.conn.rollback()
            raise

    def delete_columns_range(self, sheet_id: int, start_col: int, count: int) -> None:
        """
        지정된 시트에서 특정 범위의 열들을 삭제합니다.

        Args:
            sheet_id (int): 열을 삭제할 시트의 ID.
            start_col (int): 삭제를 시작할 열 번호.
            count (int): 삭제할 열의 개수.

        Raises:
            sqlite3.Error: DB 작업 중 오류 발생 시.
        """
        if not self.cursor or not self.conn:
            logging.error("DB 연결이 없습니다. 열 범위를 삭제할 수 없습니다.")
            raise sqlite3.Error("데이터베이스에 연결되지 않았습니다.")
        try:
            self.conn.execute("BEGIN TRANSACTION")
            end_col = start_col + count - 1
            self.cursor.execute("DELETE FROM cells WHERE sheet_id = ? AND col >= ? AND col <= ?", (sheet_id, start_col, end_col))
            deleted_count = self.cursor.rowcount
            logging.debug(f"시트 {sheet_id}: 열 {start_col}~{end_col} 삭제 완료 ({deleted_count}개 셀)")
            self.conn.commit()
        except sqlite3.Error as e:
            logging.error(f"열 범위 삭제 오류 (sheet_id={sheet_id}, start_col={start_col}, count={count}): {e}")
            if self.conn: self.conn.rollback()
            raise

    def shift_rows(self, sheet_id: int, start_row: int, shift_amount: int) -> None:
        """
        지정된 시트의 특정 행부터 그 아래 모든 행들의 행 번호를 `shift_amount`만큼 변경합니다.

        `shift_amount`가 양수이면 행들이 아래로 이동(행 번호 증가), 음수이면 위로 이동(행 번호 감소)합니다.
        행 번호 충돌을 방지하기 위해 이동 방향에 따라 업데이트 순서를 조정합니다.

        Args:
            sheet_id (int): 작업 대상 시트의 ID.
            start_row (int): 이동을 시작할 기준 행 번호. 이 행부터 아래 모든 행이 대상이 됩니다.
            shift_amount (int): 행 번호를 변경할 값. 양수는 아래로, 음수는 위로 이동.

        Raises:
            sqlite3.Error: DB 작업 중 오류 발생 시.
        """
        if not self.cursor or not self.conn:
            logging.error("DB 연결이 없습니다. 행을 이동할 수 없습니다.")
            raise sqlite3.Error("데이터베이스에 연결되지 않았습니다.")
        if shift_amount == 0: return

        try:
            self.conn.execute("BEGIN TRANSACTION")
            if shift_amount > 0: # 아래로 이동 (행 번호 증가)
                self.cursor.execute("SELECT DISTINCT row FROM cells WHERE sheet_id = ? AND row >= ? ORDER BY row DESC", (sheet_id, start_row))
                rows_to_move = [row[0] for row in self.cursor.fetchall()]
                for r_idx in rows_to_move:
                    self.cursor.execute("UPDATE cells SET row = row + ? WHERE sheet_id = ? AND row = ?", (shift_amount, sheet_id, r_idx))
            else: # 위로 이동 (행 번호 감소)
                self.cursor.execute("UPDATE cells SET row = row + ? WHERE sheet_id = ? AND row >= ?", (shift_amount, sheet_id, start_row))

            logging.debug(f"시트 {sheet_id}: 행 {start_row}부터 {shift_amount}만큼 이동 완료 ({self.cursor.rowcount}개 셀 영향)")
            self.conn.commit()
        except sqlite3.Error as e:
            logging.error(f"행 이동 오류 (sheet_id={sheet_id}, start_row={start_row}, shift={shift_amount}): {e}")
            if self.conn: self.conn.rollback()
            raise

    def shift_columns(self, sheet_id: int, start_col: int, shift_amount: int) -> None:
        """
        지정된 시트의 특정 열부터 그 오른쪽 모든 열들의 열 번호를 `shift_amount`만큼 변경합니다.

        `shift_amount`가 양수이면 열들이 오른쪽으로 이동(열 번호 증가), 음수이면 왼쪽으로 이동(열 번호 감소)합니다.
        열 번호 충돌을 방지하기 위해 이동 방향에 따라 업데이트 순서를 조정합니다.

        Args:
            sheet_id (int): 작업 대상 시트의 ID.
            start_col (int): 이동을 시작할 기준 열 번호. 이 열부터 오른쪽 모든 열이 대상이 됩니다.
            shift_amount (int): 열 번호를 변경할 값. 양수는 오른쪽으로, 음수는 왼쪽으로 이동.

        Raises:
            sqlite3.Error: DB 작업 중 오류 발생 시.
        """
        if not self.cursor or not self.conn:
            logging.error("DB 연결이 없습니다. 열을 이동할 수 없습니다.")
            raise sqlite3.Error("데이터베이스에 연결되지 않았습니다.")
        if shift_amount == 0: return

        try:
            self.conn.execute("BEGIN TRANSACTION")
            if shift_amount > 0: # 오른쪽으로 이동 (열 번호 증가)
                self.cursor.execute("SELECT DISTINCT col FROM cells WHERE sheet_id = ? AND col >= ? ORDER BY col DESC", (sheet_id, start_col))
                cols_to_move = [row[0] for row in self.cursor.fetchall()]
                for c_idx in cols_to_move:
                    self.cursor.execute("UPDATE cells SET col = col + ? WHERE sheet_id = ? AND col = ?", (shift_amount, sheet_id, c_idx))
            else: # 왼쪽으로 이동 (열 번호 감소)
                self.cursor.execute("UPDATE cells SET col = col + ? WHERE sheet_id = ? AND col >= ?", (shift_amount, sheet_id, start_col))

            logging.debug(f"시트 {sheet_id}: 열 {start_col}부터 {shift_amount}만큼 이동 완료 ({self.cursor.rowcount}개 셀 영향)")
            self.conn.commit()
        except sqlite3.Error as e:
            logging.error(f"열 이동 오류 (sheet_id={sheet_id}, start_col={start_col}, shift={shift_amount}): {e}")
            if self.conn: self.conn.rollback()
            raise

    def update_sheet_order(self, sheet_id: int, new_order: int) -> None:
        """
        지정된 시트의 정렬 순서(`sheet_order`)를 업데이트합니다.

        Args:
            sheet_id (int): 순서를 업데이트할 시트의 ID.
            new_order (int): 새로운 정렬 순서 값.

        Raises:
            sqlite3.Error: 업데이트 중 DB 오류 발생 시.
        """
        if not self.cursor or not self.conn:
            logging.error("DB 연결이 없습니다. 시트 순서를 업데이트할 수 없습니다.")
            raise sqlite3.Error("데이터베이스에 연결되지 않았습니다.")
        try:
            self.cursor.execute("UPDATE sheets SET sheet_order = ? WHERE id = ?", (new_order, sheet_id))
            self.conn.commit()
            logging.info(f"시트 ID {sheet_id}의 순서가 {new_order}(으)로 업데이트되었습니다.")
        except sqlite3.Error as e:
            logging.error(f"시트 순서 업데이트 오류 (ID: {sheet_id}): {e}")
            if self.conn: self.conn.rollback()
            raise

# Path 클래스를 import 목록에 추가 (get_files 메서드에서 사용)
from pathlib import Path
