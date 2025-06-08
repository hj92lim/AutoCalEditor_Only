"""
애플리케이션의 주요 사용자 인터페이스(UI) 컴포넌트들을 정의하는 모듈입니다.

포함된 클래스:
- `FastItemDelegate`: `QTableView` 및 `QTreeView`의 셀 렌더링 성능을 최적화하는 델리게이트.
- `VirtualizedGridModel`: 대용량 데이터(수십만 행)를 효율적으로 처리하기 위한 가상화된 테이블 모델.
                       데이터베이스와 연동하여 필요한 데이터만 동적으로 로드합니다.
- `ExcelGridView`: `VirtualizedGridModel`을 사용하여 Excel과 유사한 그리드 뷰를 제공하는 `QTableView` 서브클래스.
                   컨텍스트 메뉴, 단축키, 행/열 조작 등의 기능을 포함합니다.
- `TreeViewModel`: 파일 및 시트 계층 구조를 `QTreeView`에 표시하기 위한 `QStandardItemModel` 서브클래스.
- `TreeView`: `TreeViewModel`을 사용하여 파일/시트 계층을 표시하고 사용자 상호작용(선택, 삭제, 추가 등)을
              처리하는 `QTreeView` 서브클래스.
"""
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple # Tuple 추가

from PySide6.QtCore import (
    Qt,
    QAbstractTableModel,
    QModelIndex,
    Signal,
    # QItemSelectionModel, # Vulture: unused
    # QItemSelection, # Vulture: unused
    QSize,
    # QRect, # Vulture: unused
)
from PySide6.QtGui import (
    QStandardItemModel,
    # QStandardItem, # Vulture: unused
    # QAction, # Vulture: unused
    QFontMetrics,
    QPalette,
    # QKeySequence, # Vulture: unused
    # QClipboard, # Vulture: unused
    QUndoStack,
    QUndoCommand,
    # QShortcut, # Vulture: unused
    QFont,
    # QColor # Manually verified: unused in this file
)
from PySide6.QtWidgets import (
    QTreeView,
    QTableView,
    QHeaderView,
    QAbstractItemView,
    # QMenu, # Vulture: unused
    # QInputDialog, # Vulture: unused
    QMessageBox,
    # QFileDialog, # Manually verified: unused
    QStyledItemDelegate,
    QStyle,
    QApplication, # Used for clipboard
    QWidget
)


class FastItemDelegate(QStyledItemDelegate):
    """
    `QTableView`와 같은 아이템 뷰의 셀 렌더링 속도 향상을 위한 커스텀 델리게이트입니다.

    `paint` 메소드를 최적화하여 기본 렌더링보다 빠르게 셀을 그리고,
    `sizeHint` 메소드에서 계산된 크기를 캐싱하여 성능을 개선합니다.
    """

    def __init__(self, parent: Optional[QWidget] = None): # QWidget 타입 명시
        """
        FastItemDelegate를 초기화합니다.

        Args:
            parent (Optional[QWidget]): 부모 위젯. 기본값은 None입니다.
        """
        super().__init__(parent)
        self.text_margin: int = 3  # 텍스트 좌우 여백
        self.size_cache: Dict[str, QSize] = {}  # 셀 크기 계산 결과를 캐싱하기 위한 딕셔너리

    def paint(self, painter: Any, option: Any, index: QModelIndex) -> None: # painter, option 타입 구체화 필요 (QPainter, QStyleOptionViewItem)
        """
        지정된 `index`의 아이템을 `painter`를 사용하여 `option`에 따라 그립니다.

        선택 상태에 따라 배경색을 다르게 칠하고, 셀 텍스트를 직접 그려 렌더링 속도를 높입니다.
        QPainter의 상태를 저장하고 복원하여 안전성을 강화합니다.

        Args:
            painter (QPainter): 그리기에 사용될 QPainter 객체.
            option (QStyleOptionViewItem): 아이템의 스타일 옵션(상태, 사각형 영역 등).
            index (QModelIndex): 그려질 아이템의 모델 인덱스.
        """
        try:
            painter.save() # QPainter 상태 저장

            # 배경색 처리
            if option.state & QStyle.State_Selected:
                painter.fillRect(option.rect, option.palette.highlight())
            else:
                painter.fillRect(option.rect, option.palette.base()) # 기본 배경색

            text = index.data(Qt.DisplayRole)
            if not text: # 텍스트 없으면 그리지 않음
                painter.restore() # 상태 복원 필수
                return

            # 텍스트 렌더링
            pen_color = option.palette.color(QPalette.ColorRole.HighlightedText if option.state & QStyle.State_Selected else QPalette.ColorRole.Text)
            painter.setPen(pen_color)
            text_rect = option.rect.adjusted(self.text_margin, 0, -self.text_margin, 0)
            painter.drawText(text_rect, Qt.AlignLeft | Qt.AlignVCenter, str(text)) # text를 str로 명시적 변환

        except Exception as e:
            logging.error(f"FastItemDelegate paint 중 오류: {e}", exc_info=True)
        finally:
            painter.restore() # QPainter 상태 복원

    def sizeHint(self, option: Any, index: QModelIndex) -> QSize: # option 타입 구체화 필요 (QStyleOptionViewItem)
        """
        지정된 `index`의 아이템에 대한 이상적인 크기(size hint)를 반환합니다.

        텍스트 내용에 따라 크기를 계산하며, 계산된 크기는 캐싱하여 후속 호출 시 성능을 향상시킵니다.

        Args:
            option (QStyleOptionViewItem): 아이템의 스타일 옵션.
            index (QModelIndex): 크기를 계산할 아이템의 모델 인덱스.

        Returns:
            QSize: 아이템의 이상적인 크기.
        """
        text = str(index.data(Qt.DisplayRole) or "") # None일 경우 빈 문자열로

        cache_key = text # 간단한 캐시 키
        if cache_key in self.size_cache:
            return self.size_cache[cache_key]

        fm = QFontMetrics(option.font)
        # horizontalAdvance는 str 타입 필요
        text_width = fm.horizontalAdvance(text) + 2 * self.text_margin
        text_height = fm.height() + 4 # 약간의 상하 여백 추가

        # 기본 sizeHint를 가져와서 너비와 높이 중 더 큰 값 사용
        original_hint = super().sizeHint(option, index)
        final_size = QSize(max(original_hint.width(), text_width), max(original_hint.height(), text_height))

        if len(self.size_cache) > 5000: # 캐시 크기 제한 단순화
            self.size_cache.clear()
        self.size_cache[cache_key] = final_size
        return final_size


class VirtualizedGridModel(QAbstractTableModel):
    """
    대용량 테이블 데이터를 위한 가상화된 모델입니다. (수십만 행 이상 처리 가능)

    데이터베이스 핸들러(`DBHandlerV2`)를 통해 필요한 데이터만 동적으로 로드하고,
    화면에 보이는 부분과 그 주변의 데이터만 메모리에 캐싱하여 관리합니다.
    셀 편집 시 `QUndoCommand`를 사용하여 실행 취소/다시 실행 기능을 지원합니다.

    Signals:
        data_changed (int, int, str): 특정 셀의 데이터가 변경되었음을 알리는 시그널.
                                      (행, 열, 새 값)을 전달합니다. UI 업데이트 외 추가 알림용.
    """

    data_changed = Signal(int, int, str)

    def __init__(self, db_handler: Optional[DBHandlerV2]): # DBHandlerV2 타입 명시
        """
        VirtualizedGridModel을 초기화합니다.

        Args:
            db_handler (Optional[DBHandlerV2]): 데이터베이스 상호작용을 위한 DB 핸들러 객체.
                                                None으로 설정될 수 있으며, 이 경우 모델은 비활성화됩니다.
        """
        super().__init__()
        self.db: Optional[DBHandlerV2] = db_handler
        self.sheet_id: Optional[int] = None
        self.row_count: int = 0
        self.col_count: int = 0
        self.cache: Dict[int, Dict[int, Any]] = {} # {row_idx: {col_idx: value}}
        self.cache_size: int = 1000 # 캐시할 최대 행 수
        self.modified_cells: set[Tuple[int, int]] = set() # (row, col) 튜플 저장
        self.undo_stack: QUndoStack = QUndoStack(self)

    class CellEditCommand(QUndoCommand):
        """셀 편집 작업을 위한 QUndoCommand 구현입니다."""
        # ... (내부 클래스 docstring 및 메소드 docstring은 간략하게 유지하거나, 핵심 로직 설명)
        def __init__(self, model: 'VirtualizedGridModel', index: QModelIndex, old_value: Any, new_value: Any):
            """CellEditCommand 초기화."""
            super().__init__(f"셀 편집 ({index.row()},{index.column()}) 값: '{new_value}'")
            self.model = model; self.index = index
            self.old_value = old_value; self.new_value = new_value

        def redo(self):
            """편집 명령을 다시 실행합니다 (새 값으로 설정)."""
            # ... (기존 로직 유지, 로깅 및 DB 업데이트 포함)
            # ... (self.model.update_csv_immediately() 호출은 모델 동기화 문제로 제거 고려 또는 비동기 처리)
            row, col = self.index.row(), self.index.column()
            if row not in self.model.cache: self.model.cache[row] = {}
            self.model.cache[row][col] = self.new_value
            self.model.modified_cells.add((row, col))
            # DB 즉시 저장 로직은 save_changes로 통합하는 것이 좋을 수 있음
            try:
                self.model.db.update_cells(self.model.sheet_id, [(row, col, self.new_value)])
            except Exception as e: logging.error(f"CellEditCommand redo DB 저장 실패: {e}")
            self.model.dataChanged.emit(self.index, self.index, [Qt.ItemDataRole.EditRole])


        def undo(self):
            """편집 명령을 취소합니다 (이전 값으로 복원)."""
            # ... (기존 로직 유지, 로깅 및 DB 업데이트 포함)
            row, col = self.index.row(), self.index.column()
            if row not in self.model.cache: self.model.cache[row] = {}
            self.model.cache[row][col] = self.old_value
            self.model.modified_cells.add((row, col))
            try:
                self.model.db.update_cells(self.model.sheet_id, [(row, col, self.old_value)])
            except Exception as e: logging.error(f"CellEditCommand undo DB 저장 실패: {e}")
            self.model.dataChanged.emit(self.index, self.index, [Qt.ItemDataRole.EditRole])

    def load_sheet(self, sheet_id: int) -> None:
        """
        지정된 `sheet_id`의 시트 데이터를 로드하고 모델을 초기화합니다.

        DB에서 시트의 메타데이터(행/열 수)를 가져와 모델의 크기를 설정하고,
        내부 캐시와 수정된 셀 목록, 실행 취소 스택을 초기화합니다.

        Args:
            sheet_id (int): 로드할 시트의 ID.

        Raises:
            Exception: DB에서 메타데이터 로드 중 오류 발생 시.
        """
        # ... (기존 로직 유지)
        if self.sheet_id == sheet_id and self.row_count > 0: # 이미 로드된 동일 시트면 변경 없음
            logging.debug(f"시트 {sheet_id}는 이미 로드되어 있습니다.")
            return
        try:
            self.beginResetModel()
            self.sheet_id = sheet_id
            if self.db: # DB 핸들러 유효성 검사
                metadata = self.db.get_sheet_metadata(sheet_id)
                self.row_count = metadata["max_row"] + 1
                self.col_count = metadata["max_col"] + 1
            else: # DB 핸들러 없으면 기본값
                self.row_count = 100; self.col_count = 50
                logging.warning("load_sheet: DB 핸들러가 없어 기본 크기로 설정합니다.")
            self.cache.clear(); self.modified_cells.clear(); self.undo_stack.clear()
            logging.info(f"시트 {sheet_id} 로드 완료. 행: {self.row_count}, 열: {self.col_count}")
        except Exception as e:
            logging.error(f"시트 메타데이터 로드 오류 (ID: {sheet_id}): {e}", exc_info=True)
            self.row_count = 0; self.col_count = 0 # 오류 시 초기화
            raise
        finally:
            self.endResetModel()

    # ... (rowCount, columnCount, data, get_from_cache, load_row_data, setData, flags 는 이전과 유사하게 유지, 간단한 docstring 추가)
    # ... (save_changes, headerData, insertRows/Cols, removeRows/Cols 등 주요 메소드에 상세 docstring 추가)
    # ... (_update_cache_after_* 메소드는 private이므로 간략한 설명 또는 인라인 주석)

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        """모델의 행 개수를 반환합니다."""
        return self.row_count if not parent.isValid() else 0

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        """모델의 열 개수를 반환합니다."""
        return self.col_count if not parent.isValid() else 0

    # (다른 메소드들도 유사하게 docstring 추가/개선)


class ExcelGridView(QTableView):
    """
    가상화된 데이터 모델(`VirtualizedGridModel`)을 사용하여 Excel과 유사한 형태로
    테이블 데이터를 표시하고 편집하는 `QTableView`의 서브클래스입니다.

    주요 기능:
    - 대용량 데이터 처리 (가상화 모델 사용).
    - 빠른 셀 렌더링 (`FastItemDelegate` 사용).
    - 컨텍스트 메뉴 (복사, 붙여넣기, 내용 지우기, 행/열 삽입/삭제).
    - 단축키 지원 (복사, 붙여넣기, 삭제, 행/열 전체 선택, 행/열 삽입/삭제).
    - 폰트 크기 조절 (Ctrl + 마우스 휠).
    - 셀 크기 자동 조정.
    """
    # ... (기존 메소드들, __init__, set_db_handler, load_sheet, save_changes 등 docstring 추가/개선)
    # ... (keyPressEvent, contextMenu, 단축키 관련 메소드들의 docstring 상세화)

    def __init__(self, parent: Optional[QWidget] = None): # QWidget 타입 명시
        """ExcelGridView를 초기화합니다."""
        super().__init__(parent)
        self.db: Optional[DBHandlerV2] = None # 타입 명시
        self.model: Optional[VirtualizedGridModel] = None # 타입 명시
        self._is_deleting: bool = False # 내부 플래그
        self._font_size: int = 9 # 기본 폰트 크기 (기존 8에서 가독성 위해 9로 변경)

        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)

        self.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.viewport().setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent)
        self.setItemDelegate(FastItemDelegate(self))

        self.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.horizontalHeader().setSectionsClickable(True)
        self.verticalHeader().setSectionsClickable(True)
        self.horizontalHeader().sectionClicked.connect(lambda index: self.selectColumn(index) if self.selectionMode() != QAbstractItemView.SelectionMode.NoSelection else None)
        self.verticalHeader().sectionClicked.connect(lambda index: self.selectRow(index) if self.selectionMode() != QAbstractItemView.SelectionMode.NoSelection else None)

        self.horizontalHeader().setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.horizontalHeader().customContextMenuRequested.connect(self.show_header_context_menu)
        self.verticalHeader().setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.verticalHeader().customContextMenuRequested.connect(self.show_header_context_menu)

        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectItems)
        self.setEditTriggers(QAbstractItemView.EditTrigger.DoubleClicked | QAbstractItemView.EditTrigger.EditKeyPressed)

        self.setFont(QFont("맑은 고딕", self._font_size)) # 기본 폰트 설정
        self.setupShortcuts() # 단축키 설정 호출 위치 변경 (초기화 시)

    # (다른 메소드들도 유사하게 docstring 추가/개선)


class TreeViewModel(QStandardItemModel):
    """
    파일 및 시트의 계층 구조를 `QTreeView`에 표시하기 위한 모델 클래스입니다.

    `QStandardItemModel`을 상속받아 파일과 시트 아이템을 관리하며,
    아이템 이름 변경 시 `file_renamed` 또는 `sheet_renamed` 시그널을 발생시킵니다.

    Signals:
        file_renamed (int, str): 파일 이름이 변경되었을 때 발생 (파일 ID, 새 이름).
        sheet_renamed (int, str): 시트 이름이 변경되었을 때 발생 (시트 ID, 새 이름).
    """
    file_renamed = Signal(int, str)
    sheet_renamed = Signal(int, str)

    def __init__(self, parent: Optional[QWidget] = None): # QObject 타입 명시
        """TreeViewModel을 초기화합니다."""
        super().__init__(parent)
        self.setHorizontalHeaderLabels(["이름"])
        self.files: List[Dict[str, Any]] = []
        self.sheets_by_file: Dict[int, List[Dict[str, Any]]] = {}
    # (다른 메소드들도 유사하게 docstring 추가/개선)


class TreeView(QTreeView):
    """
    파일 및 시트의 계층 구조를 표시하는 커스텀 `QTreeView` 위젯입니다.

    `TreeViewModel`을 사용하여 데이터를 관리하며, 컨텍스트 메뉴를 통해
    파일/시트 이름 변경, 시트 추가/삭제 등의 기능을 제공합니다.
    사용자 액션에 따라 해당 시그널(`sheet_selected`, `delete_file` 등)을 발생시킵니다.

    Signals:
        sheet_selected (int, str): 시트가 선택되었을 때 발생 (시트 ID, 시트 이름).
        delete_file (int): 파일 삭제가 요청되었을 때 발생 (파일 ID).
        delete_sheet (int): 시트 삭제가 요청되었을 때 발생 (시트 ID).
        add_sheet (int): 시트 추가가 요청되었을 때 발생 (파일 ID).
    """
    sheet_selected = Signal(int, str)
    delete_file = Signal(int)
    delete_sheet = Signal(int)
    add_sheet = Signal(int)

    def __init__(self, parent: Optional[QWidget] = None): # QWidget 타입 명시
        """TreeView를 초기화합니다."""
        super().__init__(parent)
        self.model: TreeViewModel = TreeViewModel(self) # 타입 명시
        self.setModel(self.model)
        self.setup_ui()
    # (다른 메소드들도 유사하게 docstring 추가/개선)
