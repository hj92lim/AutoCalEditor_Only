import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

from PySide6.QtCore import (
    Qt, QAbstractTableModel, QModelIndex, Signal,
    QItemSelectionModel, QItemSelection, QSize, QRect
)
from PySide6.QtGui import (
    QStandardItemModel, QStandardItem, QAction, QFontMetrics, QPalette,
    QKeySequence, QClipboard, QUndoStack, QUndoCommand, QShortcut, QFont
)
from PySide6.QtWidgets import (
    QTreeView, QTableView, QHeaderView, QAbstractItemView,
    QMenu, QInputDialog, QMessageBox, QFileDialog, QStyledItemDelegate,
    QStyle, QApplication
)

class FastItemDelegate(QStyledItemDelegate):
    """빠른 렌더링을 위한 아이템 델리게이트"""

    def __init__(self, parent=None):
        """FastItemDelegate 초기화"""
        super().__init__(parent)
        self.text_margin = 3
        self.size_cache = {}  # 크기 캐싱

    def paint(self, painter, option, index):
        """셀 렌더링 최적화"""
        # Draw background first, then set pen color based on selection
        if option.state & QStyle.State_Selected:
            painter.fillRect(option.rect, option.palette.highlight())
            painter.setPen(option.palette.color(QPalette.HighlightedText))
        else:
            painter.fillRect(option.rect, option.palette.base())
            painter.setPen(option.palette.color(QPalette.Text))

        # 텍스트 가져오기 및 처리
        text_value = index.data(Qt.DisplayRole)

        if text_value is None: # If data is explicitly None, nothing more to paint
            return

        text_to_draw = str(text_value) # Ensure it's a string for drawText

        # If the string representation is empty, no need to call drawText,
        # as the background has already been painted.
        if not text_to_draw:
            return

        # 텍스트 직접 렌더링
        text_rect = option.rect.adjusted(self.text_margin, 0, -self.text_margin, 0)
        painter.drawText(
            text_rect,
            Qt.AlignLeft | Qt.AlignVCenter,
            text_to_draw
        )

    def sizeHint(self, option, index):
        """셀 크기 계산 최적화 (캐싱)"""
        text = index.data(Qt.DisplayRole)
        if not text:
            return super().sizeHint(option, index)

        # 캐시된 크기가 있으면 사용
        cache_key = str(text)
        if cache_key in self.size_cache:
            return self.size_cache[cache_key]

        # 텍스트 크기 계산
        fm = QFontMetrics(option.font)
        text_width = fm.horizontalAdvance(text) + 2 * self.text_margin
        text_height = fm.height() + 2

        size = super().sizeHint(option, index)
        size.setWidth(max(size.width(), text_width))
        size.setHeight(max(size.height(), text_height))

        # 크기 캐싱 (캐시 크기 제한)
        if len(self.size_cache) > 10000:
            self.size_cache.clear()
        self.size_cache[cache_key] = size

        return size

class VirtualizedGridModel(QAbstractTableModel):
    """가상화된 그리드 모델 - 수십만 행도 빠르게 처리"""

    data_changed = Signal(int, int, str)  # row, col, value (UI 업데이트 외 추가 알림용)

    def __init__(self, db_handler):
        """
        VirtualizedGridModel 초기화

        Args:
            db_handler: DB 핸들러 객체
        """
        super().__init__()
        self.db = db_handler
        self.sheet_id = None

        # 메타데이터 캐싱
        self.row_count = 0
        self.col_count = 0

        # 데이터 캐싱 (행 단위로 캐싱)
        self.cache = {}  # {row: {col: value}}
        self.cache_size = 1000  # 최대 캐시 크기
        self.modified_cells = set()  # 수정된 셀 추적 (row, col)
        # 실행 취소 스택 추가
        self.undo_stack = QUndoStack(self)

    # 셀 변경 명령 클래스 추가
    class CellEditCommand(QUndoCommand):
        def __init__(self, model, index, old_value, new_value):
            super().__init__(f"셀 편집 ({index.row()},{index.column()})")
            self.model = model
            self.index = index
            self.old_value = old_value
            self.new_value = new_value

        def redo(self):
            # 셀 값 설정 - modified_cells에 추가하고 dataChanged 발생
            row, col = self.index.row(), self.index.column()
            if row not in self.model.cache:
                self.model.cache[row] = {}
            self.model.cache[row][col] = self.new_value
            self.model.modified_cells.add((row, col))

            # 즉시 DB에 저장 (실시간 저장)
            try:
                self.model.db.update_cells(self.model.sheet_id, [(row, col, self.new_value)])
                logging.debug(f"셀 즉시 저장: ({row}, {col}) = '{self.new_value}'")
            except Exception as save_error:
                logging.error(f"셀 즉시 저장 실패: {save_error}")

            self.model.dataChanged.emit(self.index, self.index, [Qt.EditRole])

            # 실시간 CSV 업데이트
            self.model.update_csv_immediately()

        def undo(self):
            # 이전 값으로 복원
            row, col = self.index.row(), self.index.column()
            if row not in self.model.cache:
                self.model.cache[row] = {}
            self.model.cache[row][col] = self.old_value
            self.model.modified_cells.add((row, col))

            # 즉시 DB에 저장 (실시간 저장)
            try:
                self.model.db.update_cells(self.model.sheet_id, [(row, col, self.old_value)])
                logging.debug(f"셀 실행 취소 저장: ({row}, {col}) = '{self.old_value}'")
            except Exception as save_error:
                logging.error(f"셀 실행 취소 저장 실패: {save_error}")

            self.model.dataChanged.emit(self.index, self.index, [Qt.EditRole])

            # 실시간 CSV 업데이트
            self.model.update_csv_immediately()

    def load_sheet(self, sheet_id):
        """
        시트 로드 - DB에서 메타데이터를 가져와 모델 초기화

        Args:
            sheet_id: 로드할 시트 ID
        """
        if self.sheet_id == sheet_id:
            logging.debug(f"Sheet {sheet_id} already loaded")
            return

        try:
            # 모델 변경 시작
            self.beginResetModel()

            # 시트 ID 설정
            self.sheet_id = sheet_id

            # 시트 메타데이터(행/열 개수) 가져오기
            metadata = self.db.get_sheet_metadata(sheet_id)

            # 모델 상태 업데이트
            self.row_count = metadata["max_row"] + 1  # 0부터 시작하므로 +1
            self.col_count = metadata["max_col"] + 1

            # 캐시 완전 초기화 (이전 데이터와 동기화 문제 방지)
            self.cache = {}
            self.modified_cells.clear()

            # 실행 취소 스택도 초기화
            self.undo_stack.clear()

            logging.info(f"Sheet {sheet_id} loaded successfully. Rows: {self.row_count}, Cols: {self.col_count} (캐시 초기화됨)")

        except Exception as e:
            logging.error(f"Error loading sheet metadata: {e}")
            # 오류 발생 시 빈 시트로 초기화
            self.sheet_id = sheet_id
            self.row_count = 100  # 기본값
            self.col_count = 50   # 기본값
            self.cache = {}
            self.modified_cells.clear()
            self.undo_stack.clear()
            raise  # 오류 재발생 (상위 호출자에게 알림)
        finally:
            # 모델 변경 완료
            self.endResetModel()

    def rowCount(self, parent=QModelIndex()):
        """모델의 행 개수 반환"""
        return self.row_count if not parent.isValid() else 0

    def columnCount(self, parent=QModelIndex()):
        """모델의 열 개수 반환"""
        return self.col_count if not parent.isValid() else 0

    def data(self, index, role=Qt.DisplayRole):
        """
        필요한 데이터만 로드 (가상화의 핵심)

        Args:
            index: 데이터가 필요한 셀의 QModelIndex
            role: 요청된 데이터 역할 (Qt.DisplayRole, Qt.EditRole 등)

        Returns:
            요청된 역할에 맞는 데이터 또는 None
        """
        if not index.isValid() or self.sheet_id is None:
            return None

        row, col = index.row(), index.column()

        if role == Qt.DisplayRole or role == Qt.EditRole:
            # 1. 수정된 데이터인지 확인 (캐시에 우선 반영됨)
            cached_value = self.get_from_cache(row, col)
            if cached_value is not None:
                return cached_value

            # 2. 캐시에 없으면 해당 행 전체를 DB에서 로드 (행 단위 캐싱)
            self.load_row_data(row)
            return self.get_from_cache(row, col) or "" # DB에도 없으면 빈 문자열

        return None

    def get_from_cache(self, row, col):
        """
        캐시에서 데이터 가져오기

        Args:
            row: 행 번호
            col: 열 번호

        Returns:
            캐시된 값 또는 None
        """
        row_data = self.cache.get(row)
        if row_data is not None:
            return row_data.get(col)
        return None

    def load_row_data(self, row):
        """
        행 단위로 데이터 로드 (DB 쿼리 최소화)

        Args:
            row: 로드할 행 번호
        """
        # 이미 캐시에 있거나 유효하지 않은 sheet_id면 로드하지 않음
        if row in self.cache or self.sheet_id is None:
            return

        # 캐시 크기 관리 (오래된 행 제거 - 수정되지 않은 행만)
        if len(self.cache) >= self.cache_size:
            rows_to_remove = []
            # 현재 행에서 멀리 떨어진, 수정되지 않은 행 찾기
            sorted_rows = sorted(self.cache.keys(), key=lambda r: abs(r - row))
            removed_count = 0
            for r in reversed(sorted_rows): # 가장 먼 행부터 확인
                is_modified = any((r, c) in self.modified_cells for c in self.cache[r])
                if not is_modified:
                    rows_to_remove.append(r)
                    removed_count += 1
                    if removed_count >= 100: # 최대 100개 제거
                        break

            for r in rows_to_remove:
                del self.cache[r]
            if rows_to_remove:
                logging.debug(f"Removed {len(rows_to_remove)} rows from cache.")

        # DB에서 행 데이터 로드
        try:
            logging.debug(f"Loading row {row} from DB for sheet {self.sheet_id}")
            row_data = self.db.get_row_data(self.sheet_id, row)
            self.cache[row] = row_data

            # UI 응답성 향상: 매 5행마다 이벤트 루프 처리
            if row % 5 == 0:
                QApplication.processEvents()

        except Exception as e:
            logging.error(f"Error loading row {row}: {e}")
            self.cache[row] = {}  # 빈 행으로 캐시

    def setData(self, index, value, role=Qt.EditRole):
        if not index.isValid() or role != Qt.EditRole or self.sheet_id is None:
            return False

        current_value = self.data(index, role)
        if str(value) == str(current_value or ""):
            return False

        # 실행 취소 명령 생성 및 스택에 추가
        command = self.CellEditCommand(self, index, current_value, value)
        self.undo_stack.push(command)
        # 여기서 실제 데이터 설정은 command의 redo()가 자동으로 처리
        return True

    def flags(self, index):
        """모든 셀 편집 가능하게 설정"""
        if not index.isValid():
            return Qt.NoItemFlags
        return Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsEditable

    def save_changes(self):
        """수정된 셀만 DB에 저장 (배치 처리)"""
        if not self.modified_cells or self.sheet_id is None:
            logging.info("No changes to save.")
            return

        logging.info(f"Saving {len(self.modified_cells)} modified cells for sheet {self.sheet_id}")
        cells_data = []
        for row, col in self.modified_cells:
            # 캐시에서 최신 값 가져오기
            value = self.get_from_cache(row, col)
            cells_data.append((row, col, value))

        try:
            # 수정된 셀만 DB에 업데이트
            self.db.update_cells(self.sheet_id, cells_data)
            self.modified_cells.clear()
            logging.info("Changes saved successfully.")
        except Exception as e:
            logging.error(f"Error saving changes: {e}")
            # 오류 발생 시 modified_cells를 유지하여 재시도 가능하게 할 수 있음
            raise # 오류를 상위로 전파

    def update_csv_immediately(self):
        """셀 수정 시 즉시 CSV 업데이트 (간단하고 확실한 방법)"""
        try:
            # 현재 시트 정보 확인
            if not self.sheet_id or not self.db:
                logging.debug("시트 ID 또는 DB가 없어서 CSV 업데이트 스킵")
                return

            # 메인 윈도우 찾기
            from PySide6.QtWidgets import QApplication
            app = QApplication.instance()
            if not app:
                return

            main_window = None
            for widget in app.topLevelWidgets():
                if hasattr(widget, 'git_manager'):
                    main_window = widget
                    break

            if not main_window:
                logging.debug("메인 윈도우를 찾을 수 없음")
                return

            # 현재 시트 정보 가져오기
            try:
                sheets = self.db.get_sheets()
                current_sheet = None
                for sheet in sheets:
                    if sheet['id'] == self.sheet_id:
                        current_sheet = sheet
                        break

                if not current_sheet:
                    logging.debug(f"시트 ID {self.sheet_id}를 찾을 수 없음")
                    return

                # DB와 시트 이름
                db_file_path = getattr(self.db, 'db_file_path', None) or getattr(self.db, 'db_file', None)
                if not db_file_path:
                    logging.debug("DB 파일 경로를 찾을 수 없음")
                    return

                db_name = Path(db_file_path).stem
                sheet_name = current_sheet['name']

                # CSV 파일 경로 (프로젝트 루트, .gitignore로 제외)
                csv_dir = Path("history") / db_name
                csv_dir.mkdir(parents=True, exist_ok=True)
                # $ 기호 제거하여 파일명 안전하게 만들기
                safe_sheet_name = sheet_name.replace('$', '')
                csv_file = csv_dir / f"{safe_sheet_name}.csv"

                # 시트 전체 데이터를 CSV로 저장
                import csv
                with open(csv_file, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)

                    # 시트 메타데이터
                    metadata = self.db.get_sheet_metadata(self.sheet_id)
                    max_row = metadata.get("max_row", 0)
                    max_col = metadata.get("max_col", 0)

                    # 모든 데이터 쓰기
                    for row in range(max_row + 1):
                        row_data = self.db.get_row_data(self.sheet_id, row)
                        csv_row = []
                        for col in range(max_col + 1):
                            value = row_data.get(col, "")
                            csv_row.append(str(value) if value is not None else "")
                        writer.writerow(csv_row)

                logging.info(f"✅ 실시간 CSV 업데이트: {csv_file}")

                # DB 파일도 저장 (변경사항 반영) - 모델의 save_changes 호출
                try:
                    if hasattr(self, 'save_changes') and callable(self.save_changes):
                        self.save_changes()
                        logging.debug("DB 변경사항 저장 완료")
                    else:
                        logging.debug("save_changes 메서드가 없거나 호출 불가")
                except Exception as save_error:
                    logging.error(f"DB 저장 중 오류: {save_error}")

                # Git 상태 즉시 업데이트
                if hasattr(main_window, 'update_git_status_display'):
                    main_window.update_git_status_display()

            except Exception as sheet_error:
                logging.error(f"시트 데이터 처리 중 오류: {sheet_error}")

        except Exception as e:
            logging.error(f"실시간 CSV 업데이트 실패: {e}")
            # 오류가 발생해도 셀 편집은 계속 진행

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.DisplayRole) -> Any:
        """행/열 헤더 데이터 반환"""
        if role != Qt.DisplayRole:
            return None

        if orientation == Qt.Horizontal:
            # 열 헤더 (A, B, ..., Z, AA, AB, ...)
            col_name = ""
            num = section
            while num >= 0:
                col_name = chr(65 + (num % 26)) + col_name
                num = num // 26 - 1
                if num < -1: # 무한 루프 방지
                    break
            # section 0부터 시작하므로 빈 문자열이 나올 수 없음
            return col_name

        elif orientation == Qt.Vertical:
            # 행 헤더 (1, 2, 3, ...)
            return str(section + 1)

        return None

    def insertRows(self, row, count, parent=QModelIndex()):
        """모델에 행 삽입 - 성능 최적화 버전"""
        if parent.isValid() or self.sheet_id is None or count <= 0:
            return False

        logging.debug(f"Model inserting {count} rows at {row}")

        # 뷰에 알림 시작 (삽입될 위치와 개수)
        self.beginInsertRows(parent, row, row + count - 1)
        try:
            # DB에서 행 이동 (삽입 위치 아래 행들을 count만큼 아래로)
            self.db.shift_rows(self.sheet_id, row, count)

            # 모델 내부 상태 업데이트
            self.row_count += count

            # 캐시 업데이트 최적화: 영향받는 행만 조정
            self._update_cache_after_row_insertion(row, count)
            logging.debug(f"Cache updated efficiently after row insertion.")

        except Exception as e:
            logging.error(f"Error inserting rows in DB: {e}")
            self.endInsertRows() # 실패해도 end 호출 필요
            return False
        finally:
            # 뷰에 알림 종료
            self.endInsertRows()

        logging.debug(f"Model rows inserted. New row count: {self.row_count}")
        return True

    def _update_cache_after_row_insertion(self, inserted_row, count):
        """행 삽입 후 캐시 효율적 업데이트"""
        if not self.cache:
            return

        # 삽입된 행 이후의 캐시된 행들을 아래로 이동
        new_cache = {}
        new_modified_cells = set()

        for cached_row, row_data in self.cache.items():
            if cached_row >= inserted_row:
                # 삽입 위치 이후의 행들은 count만큼 아래로 이동
                new_row = cached_row + count
                new_cache[new_row] = row_data
            else:
                # 삽입 위치 이전의 행들은 그대로 유지
                new_cache[cached_row] = row_data

        # 수정된 셀 정보도 업데이트
        for (mod_row, mod_col) in self.modified_cells:
            if mod_row >= inserted_row:
                new_modified_cells.add((mod_row + count, mod_col))
            else:
                new_modified_cells.add((mod_row, mod_col))

        self.cache = new_cache
        self.modified_cells = new_modified_cells

        logging.debug(f"Cache updated: {len(new_cache)} rows, {len(new_modified_cells)} modified cells")

    def removeRows(self, row, count, parent=QModelIndex()):
        """모델에서 행 삭제 - 성능 최적화 버전"""
        if parent.isValid() or self.sheet_id is None or count <= 0 or row + count > self.row_count:
            return False

        logging.debug(f"Model removing {count} rows at {row}")
        # 뷰에 알림 시작 (삭제될 위치와 개수)
        self.beginRemoveRows(parent, row, row + count - 1)
        try:
            # DB에서 행 삭제
            self.db.delete_rows_range(self.sheet_id, row, count)
            # 삭제된 행 아래의 행들을 위로 이동
            self.db.shift_rows(self.sheet_id, row + count, -count)

            # 모델 내부 상태 업데이트
            self.row_count -= count

            # 캐시 업데이트 최적화: 영향받는 행만 조정
            self._update_cache_after_row_removal(row, count)
            logging.debug(f"Cache updated efficiently after row removal.")

        except Exception as e:
            logging.error(f"Error removing rows in DB: {e}")
            self.endRemoveRows() # 실패해도 end 호출 필요
            return False
        finally:
            # 뷰에 알림 종료
            self.endRemoveRows()

        logging.debug(f"Model rows removed. New row count: {self.row_count}")
        return True

    def _update_cache_after_row_removal(self, removed_row, count):
        """행 삭제 후 캐시 효율적 업데이트"""
        if not self.cache:
            return

        # 삭제된 행들과 그 이후 행들의 캐시 업데이트
        new_cache = {}
        new_modified_cells = set()

        for cached_row, row_data in self.cache.items():
            if cached_row < removed_row:
                # 삭제 위치 이전의 행들은 그대로 유지
                new_cache[cached_row] = row_data
            elif cached_row >= removed_row + count:
                # 삭제된 행들 이후의 행들은 count만큼 위로 이동
                new_row = cached_row - count
                new_cache[new_row] = row_data
            # 삭제된 행들(removed_row <= cached_row < removed_row + count)은 캐시에서 제거

        # 수정된 셀 정보도 업데이트
        for (mod_row, mod_col) in self.modified_cells:
            if mod_row < removed_row:
                new_modified_cells.add((mod_row, mod_col))
            elif mod_row >= removed_row + count:
                new_modified_cells.add((mod_row - count, mod_col))
            # 삭제된 행의 수정 정보는 제거됨

        self.cache = new_cache
        self.modified_cells = new_modified_cells

        logging.debug(f"Row cache updated: {len(new_cache)} rows, {len(new_modified_cells)} modified cells")

    def insertColumns(self, column, count, parent=QModelIndex()):
        """모델에 열 삽입 - 성능 최적화 버전"""
        if parent.isValid() or self.sheet_id is None or count <= 0:
            return False

        logging.debug(f"Model inserting {count} columns at {column}")
        # 뷰에 알림 시작
        self.beginInsertColumns(parent, column, column + count - 1)
        try:
            # DB에서 열 이동
            self.db.shift_columns(self.sheet_id, column, count)

            # 모델 내부 상태 업데이트
            self.col_count += count

            # 캐시 업데이트 최적화: 영향받는 열만 조정
            self._update_cache_after_column_insertion(column, count)
            logging.debug(f"Cache updated efficiently after column insertion.")

        except Exception as e:
            logging.error(f"Error inserting columns in DB: {e}")
            self.endInsertColumns()
            return False
        finally:
            # 뷰에 알림 종료
            self.endInsertColumns()

        logging.debug(f"Model columns inserted. New column count: {self.col_count}")
        return True

    def _update_cache_after_column_insertion(self, inserted_col, count):
        """열 삽입 후 캐시 효율적 업데이트"""
        if not self.cache:
            return

        # 각 행의 캐시된 데이터에서 삽입된 열 이후의 데이터를 오른쪽으로 이동
        for row_num, row_data in self.cache.items():
            new_row_data = {}
            for col_num, value in row_data.items():
                if col_num >= inserted_col:
                    # 삽입 위치 이후의 열들은 count만큼 오른쪽으로 이동
                    new_row_data[col_num + count] = value
                else:
                    # 삽입 위치 이전의 열들은 그대로 유지
                    new_row_data[col_num] = value
            self.cache[row_num] = new_row_data

        # 수정된 셀 정보도 업데이트
        new_modified_cells = set()
        for (mod_row, mod_col) in self.modified_cells:
            if mod_col >= inserted_col:
                new_modified_cells.add((mod_row, mod_col + count))
            else:
                new_modified_cells.add((mod_row, mod_col))

        self.modified_cells = new_modified_cells

        logging.debug(f"Column cache updated: {len(self.cache)} rows, {len(new_modified_cells)} modified cells")

    def removeColumns(self, column, count, parent=QModelIndex()):
        """모델에서 열 삭제 - 성능 최적화 버전"""
        if parent.isValid() or self.sheet_id is None or count <= 0 or column + count > self.col_count:
            logging.error(f"열 삭제 검증 실패: column={column}, count={count}, valid_parent={not parent.isValid()}")
            return False

        logging.debug(f"Model removing {count} columns at {column}")
        # 뷰에 알림 시작
        self.beginRemoveColumns(parent, column, column + count - 1)
        try:
            # DB에서 열 삭제
            self.db.delete_columns_range(self.sheet_id, column, count)
            # 삭제된 열 오른쪽의 열들을 왼쪽으로 이동
            self.db.shift_columns(self.sheet_id, column + count, -count)

            # 모델 내부 상태 업데이트
            self.col_count -= count

            # 캐시 업데이트 최적화: 영향받는 열만 조정
            self._update_cache_after_column_removal(column, count)
            logging.debug(f"Cache updated efficiently after column removal.")

        except Exception as e:
            logging.error(f"Error removing columns in DB: {e}")
            self.endRemoveColumns() # 실패해도 end 호출 필요
            return False
        finally:
            # 뷰에 알림 종료
            self.endRemoveColumns()

        logging.debug(f"Model columns removed. New column count: {self.col_count}")
        return True

    def _update_cache_after_column_removal(self, removed_col, count):
        """열 삭제 후 캐시 효율적 업데이트"""
        if not self.cache:
            return

        # 각 행의 캐시된 데이터에서 삭제된 열들과 그 이후 열들의 캐시 업데이트
        for row_num, row_data in self.cache.items():
            new_row_data = {}
            for col_num, value in row_data.items():
                if col_num < removed_col:
                    # 삭제 위치 이전의 열들은 그대로 유지
                    new_row_data[col_num] = value
                elif col_num >= removed_col + count:
                    # 삭제된 열들 이후의 열들은 count만큼 왼쪽으로 이동
                    new_row_data[col_num - count] = value
                # 삭제된 열들(removed_col <= col_num < removed_col + count)은 캐시에서 제거
            self.cache[row_num] = new_row_data

        # 수정된 셀 정보도 업데이트
        new_modified_cells = set()
        for (mod_row, mod_col) in self.modified_cells:
            if mod_col < removed_col:
                new_modified_cells.add((mod_row, mod_col))
            elif mod_col >= removed_col + count:
                new_modified_cells.add((mod_row, mod_col - count))
            # 삭제된 열의 수정 정보는 제거됨

        self.modified_cells = new_modified_cells

        logging.debug(f"Column cache updated: {len(self.cache)} rows, {len(new_modified_cells)} modified cells")
class ExcelGridView(QTableView):
    """가상화된 Excel 스타일 그리드 뷰"""

    def __init__(self, parent=None):
        """ExcelGridView 초기화"""
        super().__init__(parent)

        # 컨텍스트 메뉴 설정
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)

        # 단축키 설정
        self.setupShortcuts()  # 이 줄이 추가되어야 합니다

        # 모델 연결 (set_db_handler에서 수행)
        self.db = None
        self.model = None

        # 성능 최적화 설정
        self.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.viewport().setAttribute(Qt.WA_OpaquePaintEvent, True)  # 더 빠른 페인팅
        self.setItemDelegate(FastItemDelegate(self))  # 빠른 렌더링 위한 델리게이트

        # 헤더 설정
        self.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.verticalHeader().setSectionResizeMode(QHeaderView.Interactive)
        # 헤더 클릭 시 행/열 전체 선택 기능 활성화
        self.horizontalHeader().setSectionsClickable(True)
        self.verticalHeader().setSectionsClickable(True)
        self.horizontalHeader().sectionClicked.connect(
            lambda index: self.selectColumn(index) if self.selectionMode() != QAbstractItemView.NoSelection else None
        )
        self.verticalHeader().sectionClicked.connect(
            lambda index: self.selectRow(index) if self.selectionMode() != QAbstractItemView.NoSelection else None
        )
        # 헤더 컨텍스트 메뉴
        self.horizontalHeader().setContextMenuPolicy(Qt.CustomContextMenu)
        self.horizontalHeader().customContextMenuRequested.connect(self.show_header_context_menu)
        self.verticalHeader().setContextMenuPolicy(Qt.CustomContextMenu)
        self.verticalHeader().customContextMenuRequested.connect(self.show_header_context_menu)

        # 선택 모드 설정
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)  # 여러 셀/행/열 선택 가능
        self.setSelectionBehavior(QAbstractItemView.SelectItems)    # 아이템 단위 선택

        # 편집 트리거 설정
        self.setEditTriggers(QAbstractItemView.DoubleClicked | QAbstractItemView.EditKeyPressed)

        # 컨텍스트 메뉴 설정
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)

        # 단축키 설정 (QShortcut 사용)
        self.setupShortcuts()

        # 모델 연결 (set_db_handler에서 수행)
        self.db = None
        self.model = None

        # 유틸리티 변수
        _is_deleting = False  # 삭제 작업 중 플래그
        self._font_size = 8  # 기본 폰트 크기
        self.setFont(QFont("맑은 고딕", self._font_size))

    def select_current_row(self):
        """선택된 모든 행 전체 선택"""
        # 현재 선택된 셀들을 확인
        selected_indexes = self.selectedIndexes()

        if not selected_indexes:
            # 선택된 셀이 없으면 현재 커서 위치의 행만 선택
            current_row = self.currentIndex().row()
            if current_row >= 0:
                self.selectRow(current_row)
                logging.debug(f"행 선택 단축키: 현재 행 {current_row} 선택됨")
            return

        # 선택된 인덱스에서 고유한 행 번호 추출
        selected_rows = set(index.row() for index in selected_indexes)
        if not selected_rows:
            return

        # 기존 선택 지우기
        self.selectionModel().clearSelection()

        # 각 행마다 전체 선택 적용
        for row in selected_rows:
            # QItemSelection 객체 생성
            row_selection = QItemSelection(
                self.model.index(row, 0),
                self.model.index(row, self.model.columnCount() - 1)
            )
            # 선택 모델에 추가 (병합)
            self.selectionModel().select(
                row_selection,
                QItemSelectionModel.Select | QItemSelectionModel.Rows
            )

        logging.debug(f"행 선택 단축키: {len(selected_rows)}개 행 전체 선택됨")

    def select_current_column(self):
        """선택된 모든 열 전체 선택"""
        # 현재 선택된 셀들을 확인
        selected_indexes = self.selectedIndexes()

        if not selected_indexes:
            # 선택된 셀이 없으면 현재 커서 위치의 열만 선택
            current_column = self.currentIndex().column()
            if current_column >= 0:
                self.selectColumn(current_column)
                logging.debug(f"열 선택 단축키: 현재 열 {current_column} 선택됨")
            return

        # 선택된
        selected_columns = set(index.column() for index in selected_indexes)
        if not selected_columns:
            return

        # 기존 선택 지우기
        self.selectionModel().clearSelection()

        # 각 열마다 전체 선택 적용
        for col in selected_columns:
            # QItemSelection 객체 생성
            col_selection = QItemSelection(
                self.model.index(0, col),
                self.model.index(self.model.rowCount() - 1, col)
            )
            # 선택 모델에 추가 (병합)
            self.selectionModel().select(
                col_selection,
                QItemSelectionModel.Select | QItemSelectionModel.Columns
            )

        logging.debug(f"열 선택 단축키: {len(selected_columns)}개 열 전체 선택됨")

    def handle_delete_columns(self):
        """단축키로 열 삭제 처리"""
        if self._is_deleting:
            return

        self._is_deleting = True
        try:
            logging.debug("열 삭제 단축키 (Ctrl+D) 감지됨")

            # 열이 선택되었는지 확인
            if self.is_full_column_selected():
                self.delete_selected_columns()
            else:
                # 현재 선택된 셀의 열만 삭제
                current_index = self.currentIndex()
                if current_index.isValid():
                    col = current_index.column()
                    col_name = self.model.headerData(col, Qt.Horizontal, Qt.DisplayRole)

                    reply = QMessageBox.question(
                        self, '열 삭제 확인',
                        f"'{col_name}' 열을 삭제하시겠습니까?",
                        QMessageBox.Yes | QMessageBox.No, QMessageBox.No
                    )

                    if reply == QMessageBox.Yes:
                        logging.debug(f"열 {col} 삭제 시도")
                        self.model.removeColumns(col, 1)
        finally:
            self._is_deleting = False

    def handle_delete_rows(self):
        """단축키로 행 삭제 처리"""
        if self._is_deleting:
            return

        self._is_deleting = True
        try:
            logging.debug("행 삭제 단축키 (Ctrl+R) 감지됨")

            # 행이 선택되었는지 확인
            if self.is_full_row_selected():
                self.delete_selected_rows()
            else:
                # 현재 선택된 셀의 행만 삭제
                current_index = self.currentIndex()
                if current_index.isValid():
                    row = current_index.row()
                    row_name = str(row + 1)  # 1부터 시작하는 행 번호

                    reply = QMessageBox.question(
                        self, '행 삭제 확인',
                        f"{row_name}행을 삭제하시겠습니까?",
                        QMessageBox.Yes | QMessageBox.No, QMessageBox.No
                    )

                    if reply == QMessageBox.Yes:
                        logging.debug(f"행 {row} 삭제 시도")
                        self.model.removeRows(row, 1)
        finally:
            self._is_deleting = False

    def handle_delete_columns(self):
        """단축키로 열 삭제 처리"""
        logging.debug("열 삭제 단축키 감지됨")

        # 열이 선택되었는지 확인
        if self.is_full_column_selected():
            self.delete_selected_columns()
        else:
            # 현재 선택된 셀의 열만 삭제
            current_index = self.currentIndex()
            if current_index.isValid():
                col = current_index.column()
                col_name = self.model.headerData(col, Qt.Horizontal, Qt.DisplayRole)

                reply = QMessageBox.question(
                    self, '열 삭제 확인',
                    f"'{col_name}' 열을 삭제하시겠습니까?",
                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No
                )

                if reply == QMessageBox.Yes:
                    logging.debug(f"열 {col} 삭제 시도")
                    self.model.removeColumns(col, 1)

    def set_db_handler(self, db_handler):
        """
        DB 핸들러 설정 및 모델 생성/연결

        Args:
            db_handler: DB 핸들러 객체
        """
        self.db = db_handler
        self.model = VirtualizedGridModel(self.db)
        self.setModel(self.model)
        logging.info("VirtualizedGridModel set for ExcelGridView.")
        # 모델의 data_changed 시그널은 필요시 연결 (예: 실시간 협업)
        # self.model.data_changed.connect(self.on_data_changed)

    def load_sheet(self, sheet_id):
        """
        시트 로드 - 모델에 위임

        Args:
            sheet_id: 로드할 시트 ID
        """
        if not self.model:
            logging.warning("Cannot load sheet: Model not set.")
            return
        try:
            self.model.load_sheet(sheet_id)
            # 로드 후 첫 번째 셀 선택 (선택사항)
            self.clearSelection()
            self.setCurrentIndex(self.model.index(0, 0))

            # 뷰포트를 강제로 다시 그리도록 요청하여 검은 화면 버그 수정
            self.viewport().update()

            logging.info(f"Sheet {sheet_id} loaded and view updated.")
        except Exception as e:
            logging.error(f"Error loading sheet {sheet_id} in view: {e}")
            QMessageBox.critical(self, "오류", f"시트 로드 중 오류 발생: {str(e)}")

    def save_changes(self):
        """변경 사항 저장 - 모델에 위임"""
        if self.model:
            try:
                self.model.save_changes()
            except Exception as e:
                logging.error(f"Error saving changes via view: {e}")
                QMessageBox.critical(self, "오류", f"변경 사항 저장 중 오류 발생: {str(e)}")
                # 오류 발생 시 사용자에게 알림
        else:
            logging.warning("Cannot save changes: Model not set.")

    def keyPressEvent(self, event):
        """키보드 이벤트 처리 (단축키)"""
        logging.debug(f"키 이벤트 감지: key={event.key()}, modifiers={event.modifiers()}, text='{event.text()}'")

        if not self.model:
            super().keyPressEvent(event)
            return

        # 키 이벤트 디버깅을 위한 정보 로깅
        modifiers = event.modifiers()
        key = event.key()
        logging.debug(f"Key event - key: {key}, modifiers: {modifiers}, text: '{event.text()}'")

        selection_model = self.selectionModel()

        # Shift + Space: 행 전체 선택 - 수정된 버전
        if event.key() == Qt.Key_Space and event.modifiers() == Qt.ShiftModifier:
            logging.debug(f"Shift+Space detected")

            # 이미 선택된 셀들의 인덱스 가져오기
            selected_indexes = selection_model.selectedIndexes()

            if selected_indexes:
                # 선택된 모든 행의 집합 구하기 (중복 제거)
                selected_rows = set(idx.row() for idx in selected_indexes)
                logging.debug(f"Selected rows: {selected_rows}")

                # 새 선택 객체 생성 전에 기존 선택 지우기
                selection_model.clearSelection()

                # 각 행에 대해 행 전체 선택
                for row in selected_rows:
                    start_index = self.model.index(row, 0)
                    end_index = self.model.index(row, self.model.columnCount() - 1)

                    if start_index.isValid() and end_index.isValid():
                        # 행 단위 QItemSelection 생성
                        item_selection = QItemSelection(start_index, end_index)
                        # SelectionFlags에 QItemSelectionModel.Rows와 Select 설정
                        selection_model.select(item_selection,
                                            QItemSelectionModel.Select | QItemSelectionModel.Rows)

                logging.debug(f"Multiple rows selected: {len(selected_rows)}")
                event.accept()
                return
            else:
                # 선택된 셀이 없는 경우 현재 커서 위치의 행만 선택 (기존 동작)
                current_row = self.currentIndex().row()
                if current_row >= 0:
                    selection_model.clearSelection()
                    start_index = self.model.index(current_row, 0)
                    end_index = self.model.index(current_row, self.model.columnCount() - 1)
                    if start_index.isValid() and end_index.isValid():
                        item_selection = QItemSelection(start_index, end_index)
                        selection_model.select(item_selection,
                                            QItemSelectionModel.Select | QItemSelectionModel.Rows)
                        logging.debug(f"Current row selected: {current_row}")
                    event.accept()
                    return

        # Ctrl + Space: 열 전체 선택 - 개선된 버전
        elif event.key() == Qt.Key_Space and event.modifiers() == Qt.ControlModifier:
            logging.debug("Ctrl+Space detected - 열 전체 선택")

            if not self.model or self.model.rowCount() == 0:
                logging.debug("모델이 없거나 행이 없음")
                event.accept()
                return

            # 현재 선택된 셀들의 열 번호 가져오기
            selected_indexes = selection_model.selectedIndexes()

            if selected_indexes:
                # 선택된 모든 열의 집합 구하기
                selected_cols = sorted(set(idx.column() for idx in selected_indexes))
                logging.debug(f"확장할 열들: {selected_cols}")
            else:
                # 선택된 셀이 없으면 현재 커서 위치의 열 선택
                current_col = self.currentIndex().column()
                if current_col >= 0:
                    selected_cols = [current_col]
                    logging.debug(f"현재 커서 열 선택: {current_col}")
                else:
                    logging.debug("유효한 열을 찾을 수 없음")
                    event.accept()
                    return

            # 기존 선택 지우기
            selection_model.clearSelection()

            # 각 열에 대해 전체 행 선택
            for col in selected_cols:
                if col >= 0 and col < self.model.columnCount():
                    # 열의 첫 번째 행부터 마지막 행까지 선택
                    top_index = self.model.index(0, col)
                    bottom_index = self.model.index(self.model.rowCount() - 1, col)

                    if top_index.isValid() and bottom_index.isValid():
                        # QItemSelection으로 열 전체 선택
                        column_selection = QItemSelection(top_index, bottom_index)
                        selection_model.select(column_selection, QItemSelectionModel.Select)
                        logging.debug(f"열 {col} 전체 선택 완료")

            logging.debug(f"총 {len(selected_cols)}개 열 전체 선택 완료")
            event.accept()
            return

        # Ctrl + + (더하기): 행/열 삽입
        elif (event.key() == Qt.Key_Plus and event.modifiers() == Qt.ControlModifier) or \
            (event.key() == Qt.Key_Equal and event.modifiers() == Qt.ControlModifier):  # + 키는 = 키와 같을 수 있음
            logging.debug(f"Ctrl++ detected, row_selected={self.is_full_row_selected()}, col_selected={self.is_full_column_selected()}")
            if self.is_full_row_selected():
                self.insert_selected_rows()
                event.accept()
                return
            elif self.is_full_column_selected():
                self.insert_selected_columns()
                event.accept()
                return
            # 선택 모드 기반 처리
            elif self.selectionBehavior() == QAbstractItemView.SelectRows and selection_model.hasSelection():
                self.insert_selected_rows()
                event.accept()
                return
            elif self.selectionBehavior() == QAbstractItemView.SelectColumns and selection_model.hasSelection():
                self.insert_selected_columns()
                event.accept()
                return

        # Ctrl + - (빼기): 행/열 삭제 - 행 우선 처리로 수정
        elif (event.key() == Qt.Key_Minus and event.modifiers() == Qt.ControlModifier) or \
            (event.key() == Qt.Key_Minus and event.modifiers() == (Qt.ControlModifier | Qt.KeypadModifier)):
            logging.debug("===== Ctrl+- 키 감지됨 =====")
            logging.debug(f"selection_model.hasSelection(): {selection_model.hasSelection()}")
            logging.debug(f"is_full_row_selected(): {self.is_full_row_selected()}")
            logging.debug(f"is_full_column_selected(): {self.is_full_column_selected()}")

            # 먼저 행 삭제 시도 (행 선택이 우선)
            if self.is_full_row_selected():
                selected_rows = self.get_selected_rows_range()
                if selected_rows:
                    start_row, count = selected_rows
                    reply = QMessageBox.question(
                        self, '행 삭제 확인', f'{count}개의 행을 삭제하시겠습니까?',
                        QMessageBox.Yes | QMessageBox.No, QMessageBox.No
                    )
                    if reply == QMessageBox.Yes:
                        success = self.model.removeRows(start_row, count)
                        logging.debug(f"행 삭제 결과: {'성공' if success else '실패'}")
                    event.accept()
                    return

            # 그 다음 열 삭제 시도 (열 선택인 경우)
            elif self.is_full_column_selected():
                selected_cols = self.get_selected_columns_range()
                if selected_cols:
                    start_col, count = selected_cols
                    reply = QMessageBox.question(
                        self, '열 삭제 확인', f'{count}개의 열을 삭제하시겠습니까?',
                        QMessageBox.Yes | QMessageBox.No, QMessageBox.No
                    )
                    if reply == QMessageBox.Yes:
                        success = self.model.removeColumns(start_col, count)
                        logging.debug(f"열 삭제 결과: {'성공' if success else '실패'}")
                    event.accept()
                    return

            logging.debug("선택된 행이나 열을 찾을 수 없음")

        # Delete 키: 선택한 셀 내용 삭제
        elif event.key() == Qt.Key_Delete:
            self.clear_selection()
            event.accept()
            return

        # 복사 (Ctrl+C 또는 Cmd+C)
        elif event.matches(QKeySequence.Copy):
            self.copy_selection()
            event.accept()
            return

        # 붙여넣기 (Ctrl+V 또는 Cmd+V)
        elif event.matches(QKeySequence.Paste):
            self.paste_to_selection()
            event.accept()
            return

        # 다른 키 이벤트는 기본 처리
        super().keyPressEvent(event)

    def force_delete_current_column(self):
        """현재 선택된 열을 강제로 삭제 (Ctrl+- 문제 해결용)"""
        if not self.model:
            return

        current_col = self.currentIndex().column()
        if current_col >= 0:
            reply = QMessageBox.question(
                self, '열 삭제 확인', f'현재 열({current_col+1})을 삭제하시겠습니까?',
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                logging.debug(f"강제 열 삭제 시도: {current_col}")
                self.model.removeColumns(current_col, 1)
                logging.debug("열 삭제 완료")
        else:
            QMessageBox.warning(self, "삭제 불가", "선택된 열이 없습니다.")

    def show_header_context_menu(self, position):
        """헤더 우클릭 시 컨텍스트 메뉴 표시 (행/열 삽입/삭제)"""
        header = self.sender() # QHeaderView
        if not isinstance(header, QHeaderView) or not self.model:
            return

        logical_index = header.logicalIndexAt(position)
        if logical_index < 0:
            return

        menu = QMenu(self)
        insert_action = None
        delete_action = None

        if header.orientation() == Qt.Vertical: # 행 헤더
            insert_action = menu.addAction("위에 행 삽입")
            delete_action = menu.addAction(f"{logical_index + 1}행 삭제")
        else: # 열 헤더
            col_name = self.model.headerData(logical_index, Qt.Horizontal, Qt.DisplayRole)
            insert_action = menu.addAction("왼쪽에 열 삽입")
            delete_action = menu.addAction(f"{col_name}열 삭제")

        action = menu.exec(header.mapToGlobal(position))

        if action == insert_action:
            if header.orientation() == Qt.Vertical:
                self.model.insertRows(logical_index, 1)
            else:
                self.model.insertColumns(logical_index, 1)
        elif action == delete_action:
            if header.orientation() == Qt.Vertical:
                self.model.removeRows(logical_index, 1)
            else:
                self.model.removeColumns(logical_index, 1)

    def show_context_menu(self, position):
        """셀 영역 우클릭 시 컨텍스트 메뉴 표시 (복사/붙여넣기/지우기)"""
        menu = QMenu(self)
        copy_action = menu.addAction("복사")
        paste_action = menu.addAction("붙여넣기")
        menu.addSeparator()
        clear_action = menu.addAction("내용 지우기")

        action = menu.exec(self.viewport().mapToGlobal(position))

        if action == copy_action:
            self.copy_selection()
        elif action == paste_action:
            self.paste_to_selection()
        elif action == clear_action:
            self.clear_selection()

    def is_full_row_selected(self) -> bool:
        """현재 선택 영역이 하나 이상의 행 전체인지 확인"""
        selection_model = self.selectionModel()
        if not selection_model or not selection_model.hasSelection():
            return False
        selected_ranges = selection_model.selection()
        # 모든 선택 범위가 행 전체를 포함하는지 확인
        for sel_range in selected_ranges:
            if sel_range.left() != 0 or sel_range.right() != self.model.columnCount() - 1:
                return False
        return True

    def is_full_column_selected(self) -> bool:
        """현재 선택 영역이 하나 이상의 열 전체인지 확인 - 개선된 버전"""
        logging.debug("is_full_column_selected 호출됨")

        # 1. 기본 검증
        if not self.model or not self.selectionModel():
            logging.debug("모델 또는 선택 모델 없음")
            return False

        selection_model = self.selectionModel()
        if not selection_model.hasSelection():
            logging.debug("선택 없음")
            return False

        # 2. 선택된 인덱스 가져오기
        selected_indexes = self.selectedIndexes()
        if not selected_indexes:
            logging.debug("선택된 인덱스 없음")
            return False

        # 3. 각 열별로 선택된 행 수 계산
        columns = {}
        for idx in selected_indexes:
            col = idx.column()
            row = idx.row()
            if col not in columns:
                columns[col] = set()
            columns[col].add(row)

        # 4. 모든 행이 선택된 열이 있는지 확인
        row_count = self.model.rowCount()
        if row_count == 0:
            logging.debug("행 수가 0")
            return False

        full_columns = []
        for col, rows in columns.items():
            if len(rows) == row_count:
                # 연속된 행인지 확인 (0부터 row_count-1까지)
                expected_rows = set(range(row_count))
                if rows == expected_rows:
                    full_columns.append(col)
                    logging.debug(f"열 {col}의 모든 행({len(rows)})이 선택됨")

        if full_columns:
            logging.debug(f"전체 선택된 열들: {full_columns}")
            return True
        else:
            logging.debug("어떤 열의 모든 행도 선택되지 않음")
            return False

    def get_selected_rows_range(self) -> Optional[Tuple[int, int]]:
        """선택된 행들의 시작 행과 개수를 반환 (연속된 행만 가정)"""
        selection_model = self.selectionModel()
        if not self.is_full_row_selected() or not selection_model:
             return None

        selected_rows = set()
        for sel_range in selection_model.selection():
            for r in range(sel_range.top(), sel_range.bottom() + 1):
                selected_rows.add(r)

        if not selected_rows:
            return None

        min_row = min(selected_rows)
        max_row = max(selected_rows)
        count = max_row - min_row + 1

        # 실제로 모든 행이 선택되었는지 확인 (비연속 선택 제외)
        if len(selected_rows) != count:
            logging.warning("Non-contiguous row selection detected for insertion/deletion.")
            # 비연속 선택 시 첫 번째 행만 처리하거나, 오류 처리 가능
            # 여기서는 첫 번째 행만 기준으로 함
            return min_row, 1 # 또는 None 반환

        return min_row, count

    def get_selected_columns_range(self) -> Optional[Tuple[int, int]]:
        """선택된 열들의 시작 열과 개수를 반환 - 전체 열 선택만 고려"""
        logging.debug("get_selected_columns_range 호출됨")

        # 전체 열이 선택되었는지 먼저 확인
        if not self.is_full_column_selected():
            logging.debug("전체 열이 선택되지 않음")
            return None

        # 선택된 인덱스 가져오기
        selected_indexes = self.selectedIndexes()
        if not selected_indexes:
            logging.debug("선택된 인덱스 없음")
            return None

        # 전체 행이 선택된 열들만 찾기
        columns = {}
        for idx in selected_indexes:
            col = idx.column()
            row = idx.row()
            if col not in columns:
                columns[col] = set()
            columns[col].add(row)

        row_count = self.model.rowCount()
        full_columns = []
        for col, rows in columns.items():
            if len(rows) == row_count:
                expected_rows = set(range(row_count))
                if rows == expected_rows:
                    full_columns.append(col)

        if not full_columns:
            logging.debug("전체 선택된 열 없음")
            return None

        # 연속된 열인지 확인
        full_columns.sort()
        min_col = min(full_columns)
        max_col = max(full_columns)
        expected_count = max_col - min_col + 1

        if len(full_columns) != expected_count:
            logging.debug(f"비연속 열 선택: 열 {min_col}부터 1개만 처리")
            return min_col, 1

        logging.debug(f"전체 열 선택 범위: {min_col}부터 {len(full_columns)}개")
        return min_col, len(full_columns)

    def insert_selected_rows(self):
        """선택된 행 위에 같은 개수의 행 삽입"""
        if not self.model: return
        rows_range = self.get_selected_rows_range()
        if rows_range:
            start_row, count = rows_range
            self.model.insertRows(start_row, count)

    def delete_selected_rows(self):
        """선택된 행 삭제"""
        if not self.model: return
        rows_range = self.get_selected_rows_range()
        if rows_range:
            start_row, count = rows_range
            reply = QMessageBox.question(
                self, '행 삭제 확인', f'{count}개의 행을 삭제하시겠습니까?',
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self.model.removeRows(start_row, count)

    def insert_selected_columns(self):
        """선택된 열 왼쪽에 같은 개수의 열 삽입"""
        if not self.model: return
        cols_range = self.get_selected_columns_range()
        if cols_range:
            start_col, count = cols_range
            self.model.insertColumns(start_col, count)
            logging.debug(f"Inserting {count} columns at column {start_col}")

    def delete_selected_columns(self):
        """선택된 열 삭제 - 완전 재구현"""
        logging.debug("delete_selected_columns 호출됨")

        if not self.model or not self.selectionModel():
            logging.debug("모델 또는 선택 모델 없음")
            return

        # 직접 선택된 열 범위 계산
        cols_range = self.get_selected_columns_range()
        if not cols_range:
            logging.debug("선택된 열 범위 없음")
            return

        start_col, count = cols_range
        logging.debug(f"삭제할 열: {start_col}부터 {count}개")

        # 사용자 확인
        reply = QMessageBox.question(
            self, '열 삭제 확인', f'{count}개의 열을 삭제하시겠습니까?',
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            logging.debug("사용자가 열 삭제 확인함")
            # 직접 모델의 removeColumns 호출
            success = self.model.removeColumns(start_col, count)
            logging.debug(f"열 삭제 결과: {'성공' if success else '실패'}")

    def copy_selection(self):
        """선택한 셀 복사 (내부 버퍼 및 시스템 클립보드)"""
        selected_indexes = self.selectedIndexes()
        if not selected_indexes or not self.model:
            return

        # 선택한 셀의 행/열 범위 계산
        min_row = min(idx.row() for idx in selected_indexes)
        max_row = max(idx.row() for idx in selected_indexes)
        min_col = min(idx.column() for idx in selected_indexes)
        max_col = max(idx.column() for idx in selected_indexes)

        # 복사할 데이터 구성 (2D 리스트)
        copied_data = []
        clipboard_text = ""
        for r in range(min_row, max_row + 1):
            row_data = []
            row_text_parts = []
            for c in range(min_col, max_col + 1):
                model_index = self.model.index(r, c)
                # 모델에서 직접 데이터 가져오기 (표시된 값)
                value = self.model.data(model_index, Qt.DisplayRole) or ""
                row_data.append(value)
                row_text_parts.append(value.replace('\n', ' ').replace('\t', ' ')) # 클립보드용 텍스트 처리
            copied_data.append(row_data)
            clipboard_text += "\t".join(row_text_parts) + "\n"

        # 내부 버퍼에 저장 (파이썬 객체)
        QApplication.instance().clipboard_data = copied_data
        # 시스템 클립보드에 저장 (텍스트)
        QApplication.clipboard().setText(clipboard_text.strip())
        logging.info(f"Copied {len(copied_data)}x{len(copied_data[0]) if copied_data else 0} cells.")

    def paste_to_selection(self):
        """복사한 데이터 붙여넣기"""
        clipboard = QApplication.instance()
        if not hasattr(clipboard, 'clipboard_data') or not clipboard.clipboard_data or not self.model:
            logging.warning("No data in internal clipboard to paste.")
            # 시스템 클립보드에서 텍스트 가져오기 시도
            try:
                system_clipboard_text = QApplication.clipboard().text()
                if system_clipboard_text:
                    # 탭으로 구분된 텍스트를 2D 배열로 변환
                    lines = system_clipboard_text.split('\n')
                    clipboard_data = []
                    for line in lines:
                        if line.strip():  # 빈 줄 무시
                            clipboard_data.append(line.split('\t'))
                    if clipboard_data:
                        clipboard.clipboard_data = clipboard_data
                    else:
                        return
                else:
                    return
            except Exception as e:
                logging.error(f"클립보드 데이터 처리 오류: {e}")
                return

        copied_data = clipboard.clipboard_data
        rows_to_paste = len(copied_data)
        cols_to_paste = len(copied_data[0]) if rows_to_paste > 0 else 0

        if rows_to_paste == 0 or cols_to_paste == 0:
            return

        # 붙여넣기 시작 위치 결정 (선택 영역의 가장 왼쪽 위 셀)
        selected_indexes = self.selectedIndexes()
        if not selected_indexes:
            start_row = 0
            start_col = 0
        else:
            start_row = min(idx.row() for idx in selected_indexes)
            start_col = min(idx.column() for idx in selected_indexes)

        logging.info(f"Pasting {rows_to_paste}x{cols_to_paste} cells starting at ({start_row}, {start_col})")

        changed_indexes = []

        try:
            for r_offset in range(rows_to_paste):
                target_row = start_row + r_offset
                # 모델의 행 범위를 벗어나면 중단
                if target_row >= self.model.rowCount():
                    break

                for c_offset in range(cols_to_paste):
                    target_col = start_col + c_offset
                    # 모델의 열 범위를 벗어나면 다음 행으로
                    if target_col >= self.model.columnCount():
                        break

                    value_to_paste = copied_data[r_offset][c_offset]
                    target_index = self.model.index(target_row, target_col)
                    if target_index.isValid():
                        # setData 호출 (내부적으로 dataChanged 시그널 발생)
                        if self.model.setData(target_index, value_to_paste):
                            changed_indexes.append(target_index)

            # 변경된 영역에 대한 dataChanged 시그널을 명시적으로 보내는 것이 더 좋음
            if changed_indexes:
                min_row = min(idx.row() for idx in changed_indexes)
                max_row = max(idx.row() for idx in changed_indexes)
                min_col = min(idx.column() for idx in changed_indexes)
                max_col = max(idx.column() for idx in changed_indexes)
                top_left = self.model.index(min_row, min_col)
                bottom_right = self.model.index(max_row, max_col)
                self.model.dataChanged.emit(top_left, bottom_right, [Qt.EditRole])
                logging.info(f"Paste completed. Emitted dataChanged for range ({min_row},{min_col}) to ({max_row},{max_col})")

        except Exception as e:
            logging.error(f"Error during paste operation: {e}")
            QMessageBox.critical(self, "붙여넣기 오류", f"데이터 붙여넣기 중 오류 발생: {str(e)}")

    def clear_selection(self):
        """선택한 셀 내용 삭제"""
        selected_indexes = self.selectedIndexes()
        if not selected_indexes or not self.model:
            return

        logging.info(f"Clearing contents of {len(selected_indexes)} selected cells.")

        changed_indexes = []
        try:
            for index in selected_indexes:
                if self.model.setData(index, ""): # 빈 문자열로 설정
                     changed_indexes.append(index)

            # 변경된 영역에 대한 dataChanged 시그널
            if changed_indexes:
                 min_row = min(idx.row() for idx in changed_indexes)
                 max_row = max(idx.row() for idx in changed_indexes)
                 min_col = min(idx.column() for idx in changed_indexes)
                 max_col = max(idx.column() for idx in changed_indexes)
                 top_left = self.model.index(min_row, min_col)
                 bottom_right = self.model.index(max_row, max_col)
                 self.model.dataChanged.emit(top_left, bottom_right, [Qt.EditRole])
                 logging.info(f"Clear contents completed. Emitted dataChanged.")

        except Exception as e:
            logging.error(f"Error clearing cell contents: {e}")

    def clear_view(self):
        """그리드뷰 초기화 (모델 리셋)"""
        if self.model:
            self.model.beginResetModel()
            self.model.sheet_id = None
            self.model.row_count = 0
            self.model.col_count = 0
            self.model.cache = {}
            self.model.modified_cells = set()
            self.model.endResetModel()
            logging.info("Grid view cleared.")

    def on_selection_changed(self, selected, deselected):
        """선택 변경 시 호출되는 메서드"""
        # 디버깅용 로깅 (선택사항)
        selection_model = self.selectionModel()
        if selection_model and selection_model.hasSelection():
            # 선택 정보 로깅 (선택사항)
            logging.debug("Selection changed")
            logging.debug(f"is_full_row_selected: {self.is_full_row_selected()}")
            logging.debug(f"is_full_column_selected: {self.is_full_column_selected()}")
# ExcelGridView 클래스에 다음 메서드 추가

    def setupShortcuts(self):
        """단축키 설정"""
        from PySide6.QtGui import QShortcut

        # 열 삭제 단축키 (Ctrl+D)
        self.delete_column_shortcut = QShortcut(QKeySequence("Ctrl+D"), self)
        self.delete_column_shortcut.activated.connect(self.handle_delete_columns)
        self.delete_column_shortcut.setContext(Qt.WidgetShortcut)

        # 행 삭제 단축키 (Ctrl+R)
        self.delete_row_shortcut = QShortcut(QKeySequence("Ctrl+R"), self)
        self.delete_row_shortcut.activated.connect(self.handle_delete_rows)
        self.delete_row_shortcut.setContext(Qt.WidgetShortcut)

    def handle_delete_columns(self):
        """단축키로 열 삭제 처리"""
        logging.debug("열 삭제 단축키 (Ctrl+D) 감지됨")

        # 열이 선택되었는지 확인
        if self.is_full_column_selected():
            self.delete_selected_columns()
        else:
            # 현재 선택된 셀의 열만 삭제
            current_index = self.currentIndex()
            if current_index.isValid():
                col = current_index.column()
                col_name = self.model.headerData(col, Qt.Horizontal, Qt.DisplayRole) if self.model else str(col+1)

                reply = QMessageBox.question(
                    self, '열 삭제 확인',
                    f"'{col_name}' 열을 삭제하시겠습니까?",
                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No
                )

                if reply == QMessageBox.Yes and self.model:
                    logging.debug(f"열 {col} 삭제 시도")
                    self.model.removeColumns(col, 1)

    def handle_delete_rows(self):
        """단축키로 행 삭제 처리"""
        logging.debug("행 삭제 단축키 (Ctrl+R) 감지됨")

        # 행이 선택되었는지 확인
        if self.is_full_row_selected():
            self.delete_selected_rows()
        else:
            # 현재 선택된 셀의 행만 삭제
            current_index = self.currentIndex()
            if current_index.isValid():
                row = current_index.row()
                row_name = str(row + 1)  # 1부터 시작하는 행 번호

                reply = QMessageBox.question(
                    self, '행 삭제 확인',
                    f"{row_name}행을 삭제하시겠습니까?",
                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No
                )

                if reply == QMessageBox.Yes and self.model:
                    logging.debug(f"행 {row} 삭제 시도")
                    self.model.removeRows(row, 1)

    def setModel(self, model):
        """모델 연결 시 셀 크기 자동 조정"""
        super().setModel(model)
        self.model = model
        self.adjustCellSizes()  # 모델(시트) 연결 시 셀 크기 조정

    def load_sheet(self, sheet_id):
        """시트 로드(예시, 실제 구현에 맞게 조정)"""
        if hasattr(self.model, "load_sheet"):
            self.model.load_sheet(sheet_id)
            self.adjustCellSizes()  # 시트 데이터 로드 후 셀 크기 조정

    def wheelEvent(self, event):
        if event.modifiers() & Qt.ControlModifier:
            delta = event.angleDelta().y()
            if delta > 0:
                self._font_size = min(self._font_size + 1, 30)
            else:
                self._font_size = max(self._font_size - 1, 2)
            self.setFont(QFont("맑은 고딕", self._font_size))
            self.adjustCellSizes()
            event.accept()
        else:
            super().wheelEvent(event)

    def adjustCellSizes(self):
        """폰트 크기에 맞춰 행 높이/열 너비 자동 조정"""
        fm = QFontMetrics(self.font())
        row_height = fm.height() + 6
        col_width = fm.horizontalAdvance("가나다ABCabc1234567890") // 2 + 16

        if self.model is not None:
            for row in range(self.model.rowCount()):
                self.setRowHeight(row, row_height)
            for col in range(self.model.columnCount()):
                self.setColumnWidth(col, col_width)

class TreeViewModel(QStandardItemModel):
    """트리 뷰 모델 클래스"""

    # 이름 변경 완료 시그널 (DB 업데이트용)
    file_renamed = Signal(int, str)  # file_id, new_name
    sheet_renamed = Signal(int, str)  # sheet_id, new_name

    def __init__(self, parent=None):
        """TreeViewModel 초기화"""
        super().__init__(parent)
        self.setHorizontalHeaderLabels(["이름"])
        self.files = [] # 파일 정보 캐시 {id: int, name: str}
        self.sheets_by_file = {} # {file_id: [{id: int, name: str, is_dollar_sheet: bool, order: int}]}

    def update_files(self, files: List[Dict[str, Any]]):
        """
        파일 목록 업데이트

        Args:
            files: 파일 정보 딕셔너리 리스트
        """
        self.files = files
        self.clear()
        self.setHorizontalHeaderLabels(["이름"])

        root_item = self.invisibleRootItem()
        for file_info in files:
            # 파일 항목 생성
            file_item = QStandardItem(file_info['name'])
            file_item.setData(file_info['id'], Qt.UserRole)  # ID 저장
            file_item.setData("file", Qt.UserRole + 1)  # 항목 유형 저장
            file_item.setEditable(True) # 이름 수정 가능하도록 설정

            # 모델에 파일 항목 추가
            root_item.appendRow(file_item)

            # 파일에 속한 시트가 이미 로드되어 있으면 추가
            if file_info['id'] in self.sheets_by_file:
                self._add_sheet_items(file_item, self.sheets_by_file[file_info['id']])

    def update_sheets(self, file_id: int, sheets: List[Dict[str, Any]]):
        """
        특정 파일의 시트 목록 업데이트
        Args:
            file_id: 파일 ID
            sheets: 시트 정보 딕셔너리 리스트
        """
        # 시트 정보 저장
        self.sheets_by_file[file_id] = sheets

        # 파일 항목 찾기
        for row in range(self.rowCount()):
            # QModelIndex 대신 QStandardItem 직접 사용
            item = self.item(row, 0)
            if item and item.data(Qt.UserRole) == file_id:
                # 기존 시트 항목 제거
                item.removeRows(0, item.rowCount())

                # 시트 항목 추가
                for sheet in sheets:
                    # 시트 항목 생성
                    sheet_item = QStandardItem(sheet['name'])
                    sheet_item.setData(sheet['id'], Qt.UserRole)  # ID 저장
                    sheet_item.setData("sheet", Qt.UserRole + 1)  # 항목 유형 저장
                    sheet_item.setData(sheet.get('is_dollar_sheet', False), Qt.UserRole + 2)

                    # 파일 항목에 시트 항목 추가
                    item.appendRow(sheet_item)

                break

    def _add_sheet_items(self, file_item: QStandardItem, sheets: List[Dict[str, Any]]):
        """파일 아이템 아래에 시트 아이템들을 추가하는 도우미 메서드"""
        for sheet_info in sheets:
            # 시트 항목 생성
            sheet_item = QStandardItem(sheet_info['name'])
            sheet_item.setData(sheet_info['id'], Qt.UserRole)  # ID 저장
            sheet_item.setData("sheet", Qt.UserRole + 1)  # 항목 유형 저장
            sheet_item.setData(sheet_info.get('is_dollar_sheet', False), Qt.UserRole + 2) # 달러 시트 여부
            sheet_item.setEditable(True) # 이름 수정 가능하도록 설정

            # 파일 항목에 시트 항목 추가
            file_item.appendRow(sheet_item)

    def get_sheets(self, file_id: int) -> List[Dict[str, Any]]:
        """
        특정 파일의 시트 목록 반환 (캐시된 정보)

        Args:
            file_id: 파일 ID

        Returns:
            시트 정보 딕셔너리 리스트
        """
        return self.sheets_by_file.get(file_id, [])

    def flags(self, index: QModelIndex) -> Qt.ItemFlags:
        """항목의 플래그를 반환 - 편집 가능하도록 설정"""
        if not index.isValid():
            return Qt.NoItemFlags

        # 기본 플래그에 ItemIsEditable 추가
        default_flags = super().flags(index)
        return default_flags | Qt.ItemIsEditable

    def setData(self, index: QModelIndex, value: Any, role: int = Qt.EditRole) -> bool:
        """
        항목 데이터 설정 (이름 수정 처리 및 시그널 발생)

        Args:
            index: 항목 인덱스
            value: 새 값
            role: 데이터 역할

        Returns:
            성공 여부
        """
        if not index.isValid() or role != Qt.EditRole:
            return False

        item = self.itemFromIndex(index)
        if not item:
            return False

        old_value = item.text()
        new_value = str(value).strip() # 공백 제거

        # 값이 변경되지 않았거나 빈 값이면 처리 안 함
        if new_value == old_value or not new_value:
            return False

        # 기본 데이터 설정 (QStandardItemModel이 처리)
        result = super().setData(index, new_value, role)

        if result:
            # 항목 정보 가져오기
            item_type = index.data(Qt.UserRole + 1)
            item_id = index.data(Qt.UserRole)

            # 이름 변경 시그널 발생
            try:
                if item_type == "file":
                    logging.info(f"File rename detected via model: ID={item_id}, New Name='{new_value}'")
                    self.file_renamed.emit(item_id, new_value)
                elif item_type == "sheet":
                    logging.info(f"Sheet rename detected via model: ID={item_id}, New Name='{new_value}'")
                    self.sheet_renamed.emit(item_id, new_value)
            except Exception as e:
                 logging.error(f"Error emitting rename signal: {e}")
                 return False # 실패로 처리

        return result


class TreeView(QTreeView):
    """파일 및 시트 트리 뷰 클래스"""

    # 시트 선택 시 시그널
    sheet_selected = Signal(int, str)  # sheet_id, sheet_name
    # 삭제 시그널
    delete_file = Signal(int)  # file_id
    delete_sheet = Signal(int)  # sheet_id
    # 시트 추가 시그널
    add_sheet = Signal(int)  # file_id

    def __init__(self, parent=None):
        """TreeView 초기화"""
        super().__init__(parent)
        self.model = TreeViewModel(self) # TreeViewModel 사용
        self.setModel(self.model)
        self.setup_ui()

    def setup_ui(self):
        """UI 설정"""
        self.setHeaderHidden(True)  # 헤더 숨김 (보통 트리뷰는 숨김)
        self.setExpandsOnDoubleClick(True)  # 더블 클릭으로 확장/축소

        # 컨텍스트 메뉴 설정
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)

        # 선택 모드 설정
        self.setSelectionMode(QAbstractItemView.SingleSelection) # 단일 항목 선택
        self.setSelectionBehavior(QAbstractItemView.SelectRows)  # 행 단위 선택

        # 드래그 앤 드롭 비활성화
        self.setDragEnabled(False)
        self.setAcceptDrops(False)
        self.setDragDropMode(QAbstractItemView.NoDragDrop)

        # 선택 변경 시그널 연결
        self.selectionModel().selectionChanged.connect(self.on_selection_changed)

        # 편집 트리거 설정 - F2 키 또는 더블클릭 후 약간의 딜레이
        self.setEditTriggers(QAbstractItemView.EditKeyPressed | QAbstractItemView.SelectedClicked)

    def mouseDoubleClickEvent(self, event):
        """더블 클릭 이벤트 처리 - 확장/축소만 실행, 편집 방지"""
        index = self.indexAt(event.pos())
        if index.isValid():
            # 기본 확장/축소 토글만 수행
            if self.isExpanded(index):
                self.collapse(index)
            else:
                self.expand(index)
            event.accept() # 이벤트 처리 완료, 편집 트리거 방지
        else:
            super().mouseDoubleClickEvent(event)

    def show_context_menu(self, position):
        """
        컨텍스트 메뉴 표시

        Args:
            position: 메뉴를 표시할 마우스 위치 (로컬 좌표)
        """
        index = self.indexAt(position)
        if not index.isValid():
            return

        # 선택된 항목 정보 가져오기
        item_type = index.data(Qt.UserRole + 1)
        item_id = index.data(Qt.UserRole)
        item_name = index.data(Qt.DisplayRole)

        menu = QMenu(self)

        if item_type == "file":
            # 파일 메뉴 항목
            rename_action = menu.addAction(f"'{item_name}' 이름 수정")
            delete_action = menu.addAction("파일 삭제")
            menu.addSeparator()
            add_sheet_action = menu.addAction("시트 추가")

            action = menu.exec(self.viewport().mapToGlobal(position))

            if action == rename_action:
                self.edit(index) # 인라인 편집 시작
            elif action == delete_action:
                self.delete_file.emit(item_id)
            elif action == add_sheet_action:
                self.add_sheet.emit(item_id)

        elif item_type == "sheet":
            # 시트 메뉴 항목
            rename_action = menu.addAction(f"'{item_name}' 이름 수정")
            delete_action = menu.addAction("시트 삭제")

            action = menu.exec(self.viewport().mapToGlobal(position))

            if action == rename_action:
                self.edit(index) # 인라인 편집 시작
            elif action == delete_action:
                self.delete_sheet.emit(item_id)

    def on_selection_changed(self, selected: QItemSelection, deselected: QItemSelection):
        """
        항목 선택 변경 처리 - 시트 선택 시그널 발생

        Args:
            selected: 새로 선택된 항목
            deselected: 선택 해제된 항목
        """
        selected_indexes = selected.indexes()
        if not selected_indexes:
            # 선택이 해제되었거나 빈 공간 클릭 시
            return

        # 첫 번째 선택된 항목 기준 (SingleSelection 모드이므로 하나만 존재)
        index = selected_indexes[0]
        item_type = index.data(Qt.UserRole + 1)

        if item_type == "sheet":
            sheet_id = index.data(Qt.UserRole)
            sheet_name = index.data(Qt.DisplayRole)
            logging.debug(f"Sheet selected via TreeView: ID={sheet_id}, Name='{sheet_name}'")
            self.sheet_selected.emit(sheet_id, sheet_name)

    def update_files(self, files):
        """
        파일 목록 업데이트 - 모델에 위임

        Args:
            files: 파일 목록
        """
        if isinstance(self.model, TreeViewModel):
            self.model.update_files(files)
        else:
            logging.error("Cannot update files: Model is not TreeViewModel")

    def update_sheets(self, file_id, sheets):
        """
        시트 목록 업데이트 - 모델에 위임

        Args:
            file_id: 파일 ID
            sheets: 시트 목록
        """
        if isinstance(self.model, TreeViewModel):
            self.model.update_sheets(file_id, sheets)
        else:
            logging.error("Cannot update sheets: Model is not TreeViewModel")

    def update_sheets_v2(self, sheets: List[Dict[str, Any]]):
        """
        V2 구조: 시트 목록을 DB별로 그룹화하여 업데이트

        Args:
            sheets: 모든 시트 목록 (source_file 정보 포함)
        """
        if not isinstance(self.model, TreeViewModel):
            logging.error("Cannot update sheets V2: Model is not TreeViewModel")
            return

        # source_file별로 시트 그룹화
        sheets_by_source = {}
        for sheet in sheets:
            source_file = sheet.get('source_file', 'Unknown')
            if source_file not in sheets_by_source:
                sheets_by_source[source_file] = []
            sheets_by_source[source_file].append(sheet)

        # 가상 파일 목록 생성
        virtual_files = []
        for i, (source_file, file_sheets) in enumerate(sheets_by_source.items(), 1):
            virtual_files.append({
                'id': i,
                'name': source_file,
                'created_at': None
            })

        # 모델 업데이트
        self.model.update_files(virtual_files)

        # 각 가상 파일에 시트 추가
        for i, (source_file, file_sheets) in enumerate(sheets_by_source.items(), 1):
            # 시트에 가상 file_id 추가
            for sheet in file_sheets:
                sheet['file_id'] = i
            self.model.update_sheets(i, file_sheets)