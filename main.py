import sys
import os
import logging
import traceback
from typing import Dict, List, Optional, Any, Tuple
# test
# Qt 폰트 경고 메시지 숨기기 (간단한 해결책)
os.environ['QT_LOGGING_RULES'] = 'qt.qpa.fonts=false'

# 애플리케이션 정보는 core/info.py에서 중앙 관리

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QMessageBox, QFileDialog, QLabel, QSplitter,
    QStatusBar, QToolBar, QInputDialog, QLineEdit, QDialog,
    QTextEdit, QListWidget, QComboBox
)
# 수정 후
from PySide6.QtCore import Qt, QSize, Signal, Slot, QUrl, QSettings, QTimer
from PySide6.QtGui import QAction, QIcon, QDesktopServices, QFont, QKeySequence

from data_manager.db_handler_v2 import DBHandlerV2
from data_manager.db_manager import DBManager
from excel_processor.excel_importer import ExcelImporter
from excel_processor.excel_exporter import ExcelExporter
from ui.ui_components import TreeView, ExcelGridView # VirtualizedGridModel 사용하는 버전
from core.data_parser import DataParser
from utils.git_manager import GitManager, DBHistoryManager
from ui.git_status_dialog import GitStatusDialog
# from commit_dialog import CommitFileDialog  # 더 이상 사용하지 않음

# 기존 코드 가져오기 (안전한 import)
try:
    from core.info import Info, SShtInfo, EMkFile
    from code_generator.make_code import MakeCode
    from code_generator.cal_list import CalList
    logging.info("✓ 필수 모듈 로드 성공")
except ImportError as e:
    logging.error(f"기존 코드 모듈 import 실패: {e}. 경로를 확인하세요.")
    print(f"❌ 필수 모듈 로드 실패: {e}")
    print("📁 현재 작업 디렉토리:", os.getcwd())
    print("🔍 Python 경로:", sys.path[:3])  # 처음 3개만 표시
    sys.exit(1)

# 성능 최적화 모듈 (검증된 최적화만 사용)
try:
    from production_ready_db_processor import ProductionDBProcessor, ProductionConfig
    OPTIMIZED_PROCESSING_AVAILABLE = True
    logging.info("✓ 최적화된 DB 프로세서 로드 성공")
except ImportError as e:
    OPTIMIZED_PROCESSING_AVAILABLE = False
    logging.warning(f"최적화된 프로세서 로드 실패: {e} (기본 기능으로 작동)")
    print("⚠️ 최적화 기능을 사용할 수 없습니다. 기본 기능만 사용됩니다.")


# 단순화된 로깅 시스템 설정
def setup_logging():
    """단순화된 로깅 시스템 설정"""
    from pathlib import Path

    # logs 디렉토리 생성
    logs_dir = Path(__file__).parent / "logs"
    logs_dir.mkdir(exist_ok=True)

    # 로그 파일명
    log_filename = logs_dir / "app.log"

    # 기존 로깅 설정 제거
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)

    # 파일 핸들러 설정
    file_handler = logging.FileHandler(log_filename, mode='w', encoding='utf-8')
    file_handler.setLevel(logging.INFO)
    file_formatter = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(file_formatter)

    # 콘솔 핸들러 설정
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter('%(levelname)s: %(message)s')
    console_handler.setFormatter(console_formatter)

    # 루트 로거 설정
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

    logging.info("=== AutoCalEditor 시작 ===")
    return log_filename

# 로깅 시스템 초기화
log_file_path = setup_logging()

# 기본 import
import subprocess

# 코드 생성 관련 상수 (SSOT 원칙)
class CodeGenerationConstants:
    """코드 생성 관련 상수 정의"""

    # 시트 타입 정의
    FILEINFO_SHEET_TYPE = "FileInfo"
    CALLIST_SHEET_TYPES = ["CalList", "CalData", "Caldata", "COMMON"]
    PROJECT_SHEET_PREFIX = "_"
    UNDEFINED_SHEET_TYPE = "UNDEFINED"
    END_SHEET_TYPE = "END"

    # 그룹 관련
    DEFAULT_GROUP_NAME = "Default"

    # 파일 확장자
    C_SOURCE_EXT = ".c"
    C_HEADER_EXT = ".h"

    # FileInfo 시트에서 파일명 읽기 위치
    FILEINFO_FILENAME_ROW_PRIMARY = 9
    FILEINFO_FILENAME_COL_PRIMARY = 3
    FILEINFO_FILENAME_ROW_SECONDARY = 8
    FILEINFO_FILENAME_COL_SECONDARY = 2

    # 타임아웃 설정 (초)
    MULTI_DB_TIMEOUT = 3600  # 1시간
    GIT_COMMAND_TIMEOUT = 10  # Git 명령어 타임아웃

    # 진행률 범위
    PROGRESS_SHEET_CLASSIFICATION_START = 30
    PROGRESS_SHEET_CLASSIFICATION_END = 50
    PROGRESS_CODE_GENERATION_START = 50
    PROGRESS_CODE_GENERATION_END = 95

    # UI 업데이트 간격 (밀리초)
    GIT_STATUS_UPDATE_INTERVAL = 3000  # 3초마다 Git 상태 업데이트

class CodeGenerationHelper:
    """코드 생성 관련 공통 로직을 담당하는 헬퍼 클래스"""

    @staticmethod
    def classify_sheets_by_group(db_handler: 'DBHandlerV2') -> Dict[str, Dict[str, Any]]:
        """
        시트들을 그룹별로 분류하는 공통 로직

        Returns:
            Dict[str, Dict[str, Any]]: 그룹명 -> {FileInfoSht, CalListSht[]} 매핑
        """
        sheets = db_handler.get_sheets()
        dollar_sheets = [s for s in sheets if s.get('is_dollar_sheet', False)]

        if not dollar_sheets:
            return {}

        d_xls = {}
        logging.info(f"시트 그룹별 분류 시작: {len(dollar_sheets)}개 $ 시트")

        for sheet_info in dollar_sheets:
            sheet_name = sheet_info['name']
            logging.info(f"시트 분류 중: '{sheet_name}'")

            # 패턴 1: $(GroupName)SheetType
            if sheet_name.startswith("$(") and ")" in sheet_name:
                temp_name = sheet_name[1:]  # $ 제거
                temp_sht_name = temp_name.split(')')
                group_name = temp_sht_name[0].replace("(", "")
                sheet_type = temp_sht_name[1] if len(temp_sht_name) > 1 else ""

                logging.info(f"  → 그룹 패턴 - 그룹: '{group_name}', 타입: '{sheet_type}'")

                if group_name not in d_xls:
                    d_xls[group_name] = {"FileInfoSht": None, "CalListSht": []}

                CodeGenerationHelper._assign_sheet_to_group(
                    d_xls[group_name], sheet_info, sheet_type, group_name, db_handler
                )

            # 패턴 2: $SheetType (그룹명 없음)
            elif sheet_name.startswith("$") and not sheet_name.startswith("$("):
                sheet_type = sheet_name[1:].strip()  # $ 제거 및 공백 제거
                group_name = CodeGenerationConstants.DEFAULT_GROUP_NAME

                logging.info(f"  → 단순 패턴 - 그룹: '{group_name}', 타입: '{sheet_type}'")

                if group_name not in d_xls:
                    d_xls[group_name] = {"FileInfoSht": None, "CalListSht": []}

                CodeGenerationHelper._assign_sheet_to_group(
                    d_xls[group_name], sheet_info, sheet_type, group_name, db_handler
                )
            else:
                logging.warning(f"  → 인식되지 않는 시트 패턴: '{sheet_name}'")

        # 그룹별 분류 결과 로깅
        logging.info(f"그룹별 분류 결과: {len(d_xls)}개 그룹")
        for group_name, group_data in d_xls.items():
            fileinfo_count = 1 if group_data["FileInfoSht"] else 0
            callist_count = len(group_data["CalListSht"])
            logging.info(f"  그룹 '{group_name}': FileInfo {fileinfo_count}개, CalList {callist_count}개")

        return d_xls

    @staticmethod
    def _assign_sheet_to_group(group_data: Dict[str, Any], sheet_info: Dict[str, Any],
                              sheet_type: str, group_name: str, db_handler: 'DBHandlerV2'):
        """시트를 그룹에 할당하는 내부 메서드"""
        if sheet_type == CodeGenerationConstants.FILEINFO_SHEET_TYPE:
            # FileInfo 시트 데이터 로드
            fileinfo_sheet_data = db_handler.get_sheet_data(sheet_info['id'])
            fileinfo_sht_info = DataParser.prepare_sheet_for_existing_code(
                sheet_info['name'], fileinfo_sheet_data
            )
            group_data['FileInfoSht'] = fileinfo_sht_info
            logging.info(f"  → FileInfo 시트 등록: 그룹 '{group_name}'")
        elif (sheet_type in CodeGenerationConstants.CALLIST_SHEET_TYPES or
              sheet_type.startswith(CodeGenerationConstants.PROJECT_SHEET_PREFIX) or
              CodeGenerationConstants.UNDEFINED_SHEET_TYPE in sheet_type or
              sheet_type == CodeGenerationConstants.END_SHEET_TYPE):
            # CalList 시트 데이터 로드
            callist_sheet_data = db_handler.get_sheet_data(sheet_info['id'])
            callist_sht_info = DataParser.prepare_sheet_for_existing_code(
                sheet_info['name'], callist_sheet_data
            )
            group_data['CalListSht'].append(callist_sht_info)
            logging.info(f"  → CalList 시트 등록: 그룹 '{group_name}' 타입 '{sheet_type}'")
        else:
            # 알 수 없는 타입도 CalList로 처리 (C# 레거시 호환성)
            callist_sheet_data = db_handler.get_sheet_data(sheet_info['id'])
            callist_sht_info = DataParser.prepare_sheet_for_existing_code(
                sheet_info['name'], callist_sheet_data
            )
            group_data['CalListSht'].append(callist_sht_info)
            logging.info(f"  → 알 수 없는 타입을 CalList로 등록: 그룹 '{group_name}' 타입 '{sheet_type}'")

    @staticmethod
    def get_base_filename_from_fileinfo(fileinfo_sht: SShtInfo, group_name: str) -> str:
        """FileInfo 시트에서 기본 파일명을 추출"""
        base_name = group_name  # 기본값은 그룹명

        if fileinfo_sht and fileinfo_sht.Data:
            # 우선 순위: 9행 3열 → 8행 2열
            s_file = Info.ReadCell(
                fileinfo_sht.Data,
                CodeGenerationConstants.FILEINFO_FILENAME_ROW_PRIMARY,
                CodeGenerationConstants.FILEINFO_FILENAME_COL_PRIMARY
            )
            if s_file and s_file.endswith(CodeGenerationConstants.C_SOURCE_EXT):
                base_name = s_file[:-2]  # .c 확장자 제거
                logging.info(f"그룹 '{group_name}' 파일명 읽기 (9행 3열): {s_file} → {base_name}")
            else:
                # 대체 위치 시도
                s_file_alt = Info.ReadCell(
                    fileinfo_sht.Data,
                    CodeGenerationConstants.FILEINFO_FILENAME_ROW_SECONDARY,
                    CodeGenerationConstants.FILEINFO_FILENAME_COL_SECONDARY
                )
                if s_file_alt and s_file_alt.endswith(CodeGenerationConstants.C_SOURCE_EXT):
                    base_name = s_file_alt[:-2]
                    logging.info(f"그룹 '{group_name}' 파일명 읽기 (8행 2열 대체): {s_file_alt} → {base_name}")
                else:
                    logging.info(f"그룹 '{group_name}' 기본 파일명 사용: {base_name}")
        else:
            logging.info(f"그룹 '{group_name}' FileInfo 없음, 기본 파일명 사용: {base_name}")

        return base_name

    @staticmethod
    def initialize_global_state():
        """전역 상태 초기화"""
        if hasattr(Info, 'ErrList'):
            Info.ErrList = []
        if hasattr(Info, 'FileList'):
            Info.FileList = []
        if hasattr(Info, 'PrjtList'):
            Info.PrjtList = []
        if hasattr(Info, 'MkFileNum'):
            Info.MkFileNum = 0
        if hasattr(Info, 'ErrNameSize'):
            Info.ErrNameSize = 0

class OriginalFileSurrogate:
    """기존 코드(MakeCode 등)와의 호환성을 위한 원본 파일 데이터 대체 클래스"""

    def __init__(self, db_handler: 'DBHandlerV2'):
        """OriginalFileSurrogate 초기화"""
        self.db = db_handler
        self.FileInfoSht: Optional[SShtInfo] = None
        self.CalListSht: List[SShtInfo] = []

    def load_file_data(self, file_id: int):
        """
        DB에서 '$' 포함 시트 데이터를 로드하여 SShtInfo 객체로 변환 (V2 방식)

        Args:
            file_id: 더미 파일 ID (V2에서는 사용하지 않음)
        """
        logging.info(f"Loading data for original code compatibility (V2 mode)")
        # V2 방식: 모든 시트 직접 조회
        sheets = self.db.get_sheets()

        self.FileInfoSht = None
        self.CalListSht = []

        for sheet_info in sheets:
            sheet_id = sheet_info['id']
            sheet_name = sheet_info['name']
            is_dollar_sheet = sheet_info.get('is_dollar_sheet', False)

            # '$' 포함 시트만 처리
            if is_dollar_sheet:
                try:
                    # 시트 데이터 가져오기 (2D 리스트 형태)
                    sheet_data = self.db.get_sheet_data(sheet_id)

                    # SShtInfo 객체 생성 (DataParser 사용)
                    sht_info = DataParser.prepare_sheet_for_existing_code(sheet_name, sheet_data)

                    # FileInfo 시트와 CalList 시트 구분
                    if "FileInfo" in sheet_name:
                        if self.FileInfoSht is None:
                            self.FileInfoSht = sht_info
                            logging.info(f"FileInfo sheet loaded: {sheet_name}")
                        else:
                            logging.debug(f"Multiple FileInfo sheets found. Using the first one: {self.FileInfoSht.Name}")
                    else:
                        self.CalListSht.append(sht_info)
                        logging.info(f"CalList sheet added: {sheet_name}")

                except Exception as e:
                    logging.error(f"Error processing sheet ID {sheet_id} ('{sheet_name}') for compatibility: {e}")
                    # 오류 발생 시 해당 시트 건너뛰기 또는 다른 처리

        if not self.FileInfoSht:
            logging.warning(f"FileInfo sheet not found for File ID: {file_id}")
        if not self.CalListSht:
            logging.warning(f"No CalList ($) sheets found for File ID: {file_id}")


class DBExcelEditor(QMainWindow):
    """DB 기반 Excel 뷰어/에디터 메인 클래스 (성능 최적화 적용)"""

    def __init__(self):
        """DBExcelEditor 초기화"""
        super().__init__()

        # 설정 관리 객체 초기화
        self.settings = QSettings(Info.SETTINGS_ORG, Info.SETTINGS_APP)

        # 마지막 사용 디렉토리 경로 저장 변수 (설정에서 로드, 없으면 현재 실행 디렉토리)
        self.last_directory = self.settings.value(Info.LAST_DIRECTORY_KEY, os.getcwd())

        # 다중 DB 관리자 초기화
        self.db_manager = DBManager()

        # 기존 호환성을 위한 속성들 (현재 활성 DB 참조)
        self.db = None  # 현재 활성 DB 핸들러 (호환성 유지)
        self.importer = None
        self.exporter = None
        self.data_parser = None
        self.file_surrogate = None

        # 오류 상황에 대비한 기본 오류 처리 설정
        try:
            # DB 관련 객체들은 import_excel_file 메서드에서 초기화
            pass
        except Exception as e:
            logging.critical(f"UI 초기화 실패: {e}")
            QMessageBox.critical(self, "치명적 오류", f"애플리케이션 초기화 실패: {e}\n프로그램을 종료합니다.")
            sys.exit(1)

        # 현재 선택된 파일/시트 정보
        self.current_file_id: Optional[int] = None
        self.current_sheet_id: Optional[int] = None

        # 프로젝트 루트 디렉토리 설정
        self.project_root = os.getcwd()

        # 기존 코드 연동을 위한 객체 (필요 시점에 생성)
        self.original_surrogate: Optional[OriginalFileSurrogate] = None

        # UI 초기화 (Git 설정 전에 먼저 UI 생성)
        self.init_ui()

        # Git 설정 확인 및 강제 설정 다이얼로그
        self.git_manager = None
        self.history_manager = None
        self.git_config_needed = True

        # Git 설정 초기화 및 검증
        if not self.initialize_git_config():
            # Git 설정 실패 시 프로그램 종료
            logging.critical("Git 설정이 완료되지 않아 프로그램을 종료합니다.")
            QMessageBox.critical(self, "설정 필요",
                               "Git 설정이 필요합니다. 프로그램을 다시 시작해주세요.")
            sys.exit(1)

        # Git 상태 자동 업데이트 타이머
        self.git_status_timer = QTimer()
        self.git_status_timer.timeout.connect(self.update_git_status_display)
        self.git_status_timer.start(CodeGenerationConstants.GIT_STATUS_UPDATE_INTERVAL)

        # 애플리케이션 종료 시 DB 연결 해제 보장
        QApplication.instance().aboutToQuit.connect(self.cleanup)

    def initialize_git_config(self) -> bool:
        """
        Git 설정 초기화 및 검증
        설정이 없으면 강제로 설정 다이얼로그를 표시하고,
        설정 완료 후 Git pull → 데이터 로드 순서로 진행

        Returns:
            bool: 설정 성공 여부
        """
        try:
            # Git 관리자 초기화 (로컬 Git만 사용)
            self.git_manager = GitManager()
            self.history_manager = DBHistoryManager(self.git_manager)

            logging.info("Git 관리자 초기화 완료 (로컬 Git 전용)")

            # Git 관리자 초기화 완료 후 브랜치 목록 초기화
            if hasattr(self, 'branch_combo'):
                self.refresh_branches()

            return True

        except Exception as e:
            logging.error(f"Git 설정 초기화 실패: {e}")
            QMessageBox.critical(self, "Git 설정 오류",
                               f"Git 설정 초기화 중 오류가 발생했습니다:\n{str(e)}")
            return False





    def __del__(self):
        """객체 소멸 시 DB 연결 해제 (안전 장치)"""
        try:
            if hasattr(self, 'db_manager') and self.db_manager:
                self.db_manager.disconnect_all()
            if hasattr(self, 'db') and self.db:
                self.db.disconnect()
        except:
            pass  # 소멸자에서는 예외를 발생시키지 않음

    def update_current_db_references(self):
        """현재 활성 DB 참조를 업데이트 (기존 코드 호환성 유지)"""
        self.db = self.db_manager.get_current_db()

        if self.db:
            # 관련 객체들도 현재 DB로 업데이트
            self.importer = ExcelImporter(self.db)
            self.exporter = ExcelExporter(self.db)
            self.data_parser = DataParser()
            self.file_surrogate = OriginalFileSurrogate(self.db)

            # 그리드뷰에도 현재 DB 설정
            if hasattr(self, 'grid_view'):
                self.grid_view.set_db_handler(self.db)
        else:
            # DB가 없으면 모든 참조를 None으로 설정
            self.importer = None
            self.exporter = None
            self.data_parser = None
            self.file_surrogate = None

    def init_ui(self):
        """UI 초기화"""
        self.setWindowTitle(Info.APP_TITLE)
        self.setMinimumSize(1200, 800)

        # 중앙 위젯 및 레이아웃
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # 메인 레이아웃 (수평)
        main_layout = QHBoxLayout(central_widget)

        # 스플리터 생성 (트리뷰와 그리드뷰 분리)
        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)

        # --- 왼쪽 패널 (트리뷰) ---
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)

        # DB 선택 드롭다운 패널
        db_selection_panel = QWidget()
        db_selection_layout = QHBoxLayout(db_selection_panel)
        db_selection_layout.setContentsMargins(5, 5, 5, 5)

        # DB 선택 라벨
        db_label = QLabel("활성 DB:")
        db_selection_layout.addWidget(db_label)

        # DB 선택 드롭다운
        self.db_combo = QComboBox()
        self.db_combo.setMinimumWidth(200)
        self.db_combo.setToolTip("현재 열린 데이터베이스 목록에서 선택하세요")
        self.db_combo.currentIndexChanged.connect(self.on_db_selection_changed)  # 인덱스 변경으로 수정
        # 초기 상태 설정
        self.db_combo.addItem("DB가 열려있지 않음")
        self.db_combo.setEnabled(False)
        db_selection_layout.addWidget(self.db_combo)

        # DB 닫기 버튼
        self.close_db_button = QPushButton("DB 닫기")
        self.close_db_button.setToolTip("현재 선택된 데이터베이스를 닫습니다")
        self.close_db_button.clicked.connect(self.close_current_db)
        self.close_db_button.setEnabled(False)
        db_selection_layout.addWidget(self.close_db_button)

        db_selection_layout.addStretch()  # 오른쪽 여백
        left_layout.addWidget(db_selection_panel)

        # 트리뷰 생성 및 시그널 연결
        self.tree_view = TreeView()
        self.tree_view.sheet_selected.connect(self.on_sheet_selected)
        self.tree_view.delete_file.connect(self.on_delete_file)
        self.tree_view.delete_sheet.connect(self.on_delete_sheet)
        self.tree_view.add_sheet.connect(self.on_add_sheet)
        # TreeViewModel의 이름 변경 시그널을 메인 윈도우의 슬롯에 직접 연결
        self.tree_view.model.file_renamed.connect(self.on_file_renamed)
        self.tree_view.model.sheet_renamed.connect(self.on_sheet_renamed)
        left_layout.addWidget(self.tree_view)

        # --- 오른쪽 패널 (그리드뷰) ---
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)

        # Git 작업 패널 (통합)
        git_panel = QWidget()
        git_layout = QHBoxLayout(git_panel)
        git_layout.setContentsMargins(5, 5, 5, 5)

        # Git 상태 표시 레이블 (왼쪽에 배치)
        self.git_status_label = QLabel("Git 상태 확인 중...")
        self.git_status_label.setStyleSheet("""
            QLabel {
                padding: 3px 8px;
                border-radius: 3px;
                font-size: 11px;
                background-color: #e3f2fd;
                color: #1976d2;
            }
        """)
        git_layout.addWidget(self.git_status_label)

        # Git 상태 새로고침 버튼
        self.git_refresh_button = QPushButton("↻")
        self.git_refresh_button.setToolTip("Git 브랜치 정보 새로고침")
        self.git_refresh_button.setFixedSize(32, 32)
        self.git_refresh_button.clicked.connect(self.refresh_git_status)
        self.git_refresh_button.setStyleSheet("""
            QPushButton {
                padding: 4px;
                font-size: 14px;
                background-color: #f8f9fa;
                color: #495057;
                border: 1px solid #dee2e6;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #e9ecef;
                border-color: #adb5bd;
            }
            QPushButton:pressed {
                background-color: #dee2e6;
            }
        """)
        git_layout.addWidget(self.git_refresh_button)

        # 브랜치 전환 드롭다운
        branch_label = QLabel("브랜치 전환:")
        git_layout.addWidget(branch_label)

        self.branch_combo = QComboBox()
        self.branch_combo.setToolTip("브랜치를 선택하여 전환합니다")
        self.branch_combo.setMinimumWidth(150)
        self.branch_combo.currentTextChanged.connect(self.on_branch_changed)
        self.branch_combo.setStyleSheet("""
            QComboBox {
                padding: 4px 8px;
                font-size: 11px;
                border: 1px solid #ced4da;
                border-radius: 4px;
                background-color: white;
                color: #333;
            }
            QComboBox:hover {
                border-color: #80bdff;
            }
            QComboBox::drop-down {
                border: none;
                background-color: #f8f9fa;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 4px solid #666;
                margin-right: 8px;
            }
            QComboBox QAbstractItemView {
                background-color: white;
                border: 1px solid #ced4da;
                selection-background-color: #007bff;
                selection-color: white;
                color: #333;
            }
            QComboBox QAbstractItemView::item {
                padding: 6px 8px;
                border: none;
                color: #333;
            }
            QComboBox QAbstractItemView::item:selected {
                background-color: #007bff;
                color: white;
            }
            QComboBox QAbstractItemView::item:hover {
                background-color: #e3f2fd;
                color: #1976d2;
            }
        """)
        git_layout.addWidget(self.branch_combo)

        # Git 변경사항 확인 버튼
        self.git_status_button = QPushButton("변경사항 확인")
        self.git_status_button.setToolTip("Git 변경사항 확인 및 커밋/푸시 (DB 자동 닫기)")
        self.git_status_button.clicked.connect(self.show_git_status)
        self.git_status_button.setStyleSheet("""
            QPushButton {
                padding: 6px 12px;
                font-size: 11px;
                background-color: #17a2b8;
                color: white;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #138496;
            }
        """)
        git_layout.addWidget(self.git_status_button)

        git_layout.addStretch()  # 중간 공간 확보

        # 원격 기준 초기화 버튼 (우측 상단에 배치)
        self.reset_to_remote_button = QPushButton("원격 기준으로 초기화")
        self.reset_to_remote_button.setToolTip("원격 저장소 기준으로 로컬을 리셋합니다 (clean 명령어 제외)")
        self.reset_to_remote_button.clicked.connect(self.reset_to_remote)
        self.reset_to_remote_button.setStyleSheet("""
            QPushButton {
                padding: 6px 12px;
                font-size: 11px;
                background-color: #dc3545;
                color: white;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #c82333;
            }
        """)
        git_layout.addWidget(self.reset_to_remote_button)

        right_layout.addWidget(git_panel)

        # 현재 시트 표시 레이블
        self.sheet_label = QLabel("선택된 시트 없음")
        right_layout.addWidget(self.sheet_label)

        # 그리드뷰 생성 및 DB 핸들러 설정
        self.grid_view = ExcelGridView()
        self.grid_view.set_db_handler(self.db) # 모델 생성 및 연결 포함
        right_layout.addWidget(self.grid_view)

        # 스플리터에 패널 추가
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)

        # 스플리터 비율 설정 (1:3)
        splitter.setSizes([300, 900])

        # 상태바 생성
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.statusBar.showMessage("준비 완료")

        # 메뉴바 생성
        self.create_menu_bar()

        # 툴바 생성 제거 (중복 기능이므로 메뉴만 사용)
        # self.create_tool_bar()

        # 초기 브랜치 정보 업데이트
        self.update_branch_display()

        # 초기 Git 상태 설정
        self.update_git_status("Git 준비 완료", "success")

        # 초기 DB 로드 시도
        self.load_initial_databases()

    def on_db_selection_changed(self, index: int):
        """DB 선택 드롭다운에서 DB가 변경되었을 때 처리"""
        try:
            if index < 0 or not self.db_manager:
                return

            # 현재 선택된 항목의 실제 DB 이름 가져오기
            db_name = self.db_combo.itemData(index)
            if not db_name:
                return

            # 현재 선택된 DB와 같으면 무시
            if self.db_manager.current_db_name == db_name:
                return

            logging.info(f"DB 전환 요청: {self.db_manager.current_db_name} -> {db_name}")

            # DB 전환
            if self.db_manager.switch_database(db_name):
                # 현재 DB 참조 업데이트
                self.update_current_db_references()

                # 파일 목록 새로고침 (선택된 DB의 시트만 표시)
                self.load_files()

                # 상태바 업데이트
                db_count = self.db_manager.get_database_count()
                self.statusBar.showMessage(f"활성 DB '{db_name}' 전환 완료 (총 {db_count}개 DB 관리 중)")

                # 닫기 버튼 활성화
                self.close_db_button.setEnabled(True)

                logging.info(f"DB 전환 완료: {db_name}")
            else:
                logging.error(f"DB 전환 실패: {db_name}")
                QMessageBox.warning(self, "DB 전환 실패", f"'{db_name}' 데이터베이스로 전환할 수 없습니다.")

        except Exception as e:
            logging.error(f"DB 선택 변경 처리 중 오류: {e}")
            QMessageBox.critical(self, "오류", f"DB 전환 중 오류가 발생했습니다:\n{str(e)}")

    def close_current_db(self):
        """현재 선택된 DB 닫기"""
        try:
            if not self.db_manager or not self.db_manager.current_db_name:
                QMessageBox.information(self, "알림", "닫을 데이터베이스가 없습니다.")
                return

            current_db_name = self.db_manager.current_db_name

            # 확인 대화상자
            reply = QMessageBox.question(
                self, "DB 닫기 확인",
                f"'{current_db_name}' 데이터베이스를 닫으시겠습니까?\n\n"
                "저장되지 않은 변경사항이 있다면 먼저 저장해주세요.",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )

            if reply == QMessageBox.Yes:
                # DB 제거
                if self.db_manager.remove_database(current_db_name):
                    # 현재 DB 참조 업데이트 (새로운 활성 DB로)
                    self.update_current_db_references()

                    # 드롭다운 업데이트
                    self.update_db_combo()

                    # 파일 목록 새로고침
                    self.load_files()

                    remaining_count = self.db_manager.get_database_count()
                    if remaining_count > 0:
                        new_active = self.db_manager.current_db_name
                        self.statusBar.showMessage(f"DB '{current_db_name}' 닫기 완료. 현재 활성 DB: '{new_active}' (총 {remaining_count}개)")
                    else:
                        self.statusBar.showMessage("모든 데이터베이스가 닫혔습니다.")

                    logging.info(f"DB 닫기 완료: {current_db_name}")
                else:
                    QMessageBox.warning(self, "DB 닫기 실패", f"'{current_db_name}' 데이터베이스를 닫을 수 없습니다.")

        except Exception as e:
            logging.error(f"DB 닫기 중 오류: {e}")
            QMessageBox.critical(self, "오류", f"DB 닫기 중 오류가 발생했습니다:\n{str(e)}")

    def update_db_combo(self):
        """DB 선택 드롭다운 업데이트"""
        try:
            logging.info("🔄 DB 드롭다운 업데이트 시작")

            # 시그널 일시 차단 (무한 루프 방지)
            self.db_combo.blockSignals(True)

            # 기존 항목 제거
            self.db_combo.clear()

            if not self.db_manager or self.db_manager.get_database_count() == 0:
                self.db_combo.addItem("DB가 열려있지 않음")
                self.db_combo.setEnabled(False)
                self.close_db_button.setEnabled(False)
                logging.info("🔄 DB가 없어서 비활성화 상태로 설정")
                return

            # DB 목록 추가
            db_names = self.db_manager.get_database_names()
            logging.info(f"🔄 DB 목록 ({len(db_names)}개): {db_names}")

            for db_name in db_names:
                # DB 이름과 파일 경로 힌트 표시
                db_handler = self.db_manager.get_database(db_name)
                if db_handler and hasattr(db_handler, 'db_file'):
                    file_path = db_handler.db_file  # 올바른 속성 이름 사용
                    display_text = f"{db_name} ({os.path.basename(file_path)})"
                    self.db_combo.addItem(display_text, db_name)  # 실제 DB 이름을 데이터로 저장
                    logging.info(f"🔄 DB 추가: {display_text} -> {db_name}")
                else:
                    self.db_combo.addItem(db_name, db_name)
                    logging.info(f"🔄 DB 추가 (경로 없음): {db_name}")

            # 현재 활성 DB 선택
            current_db_name = self.db_manager.current_db_name
            if current_db_name:
                for i in range(self.db_combo.count()):
                    if self.db_combo.itemData(i) == current_db_name:
                        self.db_combo.setCurrentIndex(i)
                        logging.info(f"🔄 현재 활성 DB 선택: {current_db_name} (인덱스 {i})")
                        break
                else:
                    logging.warning(f"🔄 현재 활성 DB '{current_db_name}'를 드롭다운에서 찾을 수 없음")

            self.db_combo.setEnabled(True)
            self.close_db_button.setEnabled(True)

            logging.info(f"🔄 DB 드롭다운 업데이트 완료: {self.db_combo.count()}개 항목, 활성 DB: {current_db_name}")

        except Exception as e:
            logging.error(f"DB 드롭다운 업데이트 중 오류: {e}")
            import traceback
            logging.error(f"상세 오류: {traceback.format_exc()}")
        finally:
            # 시그널 차단 해제
            self.db_combo.blockSignals(False)

    def load_initial_databases(self):
        """초기 데이터베이스 로드"""
        try:
            logging.info("초기 데이터베이스 로드 시작")

            # 다중 DB 자동 로드 시도
            self.auto_load_multi_db()

            logging.info("초기 데이터베이스 로드 완료")

        except Exception as e:
            logging.error(f"초기 데이터베이스 로드 중 오류: {e}")
            self.statusBar.showMessage("초기 DB 로드 실패")

    @Slot(int)
    def on_delete_file(self, file_id: int):
        """파일 삭제 처리 (TreeView의 delete_file 시그널에 연결된 슬롯)"""
        file_name = ""
        try:
            # 삭제 전 파일 이름 확인 (사용자 확인 메시지에 사용)
            files = self.db.get_files()
            file_name = next((f['name'] for f in files if f['id'] == file_id), f"ID {file_id}")
        except Exception as e:
            logging.warning(f"파일 이름 조회 중 오류 (삭제 확인용): {e}")
            file_name = f"ID {file_id}"


        reply = QMessageBox.question(
            self, '파일 삭제 확인', f"'{file_name}' 파일을 정말 삭제하시겠습니까?\n파일에 포함된 모든 시트와 데이터가 영구적으로 삭제됩니다.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            try:
                logging.info(f"Deleting file: ID={file_id}, Name='{file_name}'")
                self.db.delete_file(file_id)
                self.statusBar.showMessage(f"파일 '{file_name}' 삭제 완료")

                # 파일 목록 새로고침
                self.load_files()

                # 현재 선택된 파일이 삭제된 경우 그리드뷰 초기화
                if self.current_file_id == file_id:
                    self.current_file_id = None
                    self.current_sheet_id = None
                    self.grid_view.clear_view()
                    self.sheet_label.setText("선택된 시트 없음")

            except Exception as e:
                error_msg = f"파일 삭제 중 오류 발생: {str(e)}"
                logging.error(f"{error_msg} (File ID: {file_id})")
                QMessageBox.critical(self, "파일 삭제 오류", error_msg)

    @Slot(int)
    def on_delete_sheet(self, sheet_id: int):
        """시트 삭제 처리 (TreeView의 delete_sheet 시그널에 연결된 슬롯)"""
        sheet_name = ""
        parent_file_id = None
        try:
            # 삭제 전 시트 이름 및 부모 파일 ID 확인
            for file_id, sheets in self.tree_view.model.sheets_by_file.items():
                 found_sheet = next((s for s in sheets if s['id'] == sheet_id), None)
                 if found_sheet:
                     sheet_name = found_sheet['name']
                     parent_file_id = file_id
                     break
            if not sheet_name:
                 sheet_name = f"ID {sheet_id}"
        except Exception as e:
            logging.warning(f"시트 정보 조회 중 오류 (삭제 확인용): {e}")
            sheet_name = f"ID {sheet_id}"

        reply = QMessageBox.question(
            self, '시트 삭제 확인', f"'{sheet_name}' 시트를 정말 삭제하시겠습니까?\n시트의 모든 데이터가 영구적으로 삭제됩니다.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            try:
                logging.info(f"Deleting sheet: ID={sheet_id}, Name='{sheet_name}'")
                self.db.delete_sheet(sheet_id)
                self.statusBar.showMessage(f"시트 '{sheet_name}' 삭제 완료")

                # 해당 파일의 시트 목록 새로고침
                if parent_file_id is not None:
                    self.load_sheets(parent_file_id)
                else:
                    # 부모 파일을 못 찾은 경우 전체 파일/시트 새로고침 (안전 조치)
                    self.load_files()


                # 현재 선택된 시트가 삭제된 경우 그리드뷰 초기화
                if self.current_sheet_id == sheet_id:
                    self.current_sheet_id = None
                    self.grid_view.clear_view()
                    self.sheet_label.setText("선택된 시트 없음")

            except Exception as e:
                error_msg = f"시트 삭제 중 오류 발생: {str(e)}"
                logging.error(f"{error_msg} (Sheet ID: {sheet_id})")
                QMessageBox.critical(self, "시트 삭제 오류", error_msg)

    # 컨텍스트 메뉴를 통한 이름 변경 슬롯은 제거 (인라인 편집 후 모델 시그널 사용)
    # def on_rename_sheet(self, sheet_id): ...

    def create_menu_bar(self):
        """메뉴바 생성"""
        menu_bar = self.menuBar()

        # --- 파일 메뉴 ---
        file_menu = menu_bar.addMenu("파일(&F)")

        # DB 생성 액션 추가
        create_db_action = QAction("DB 생성(&N)...", self)
        create_db_action.setShortcut(QKeySequence("Ctrl+N"))  # 표준 새 파일 단축키 사용
        create_db_action.setStatusTip("새로운 빈 데이터베이스를 생성합니다")
        create_db_action.triggered.connect(self.create_new_db)
        file_menu.addAction(create_db_action)

        # DB 파일 열기 액션 추가
        open_db_action = QAction("DB 파일 열기(&O)...", self)
        open_db_action.setShortcut(QKeySequence("Ctrl+O"))  # 표준 열기 단축키 사용
        open_db_action.setStatusTip("DB 파일을 열어 편집합니다 (다중 선택 지원)")
        open_db_action.triggered.connect(self.open_db_file)
        file_menu.addAction(open_db_action)

        file_menu.addSeparator()

        import_action = QAction(Info.EXCEL_TO_DB_MENU_TEXT, self)
        import_action.setShortcut(QKeySequence("Ctrl+I"))  # 단축키 변경 (기존 Open과 충돌하지 않도록)
        import_action.setStatusTip(Info.EXCEL_TO_DB_STATUS_TIP)
        import_action.triggered.connect(self.import_excel_file)
        file_menu.addAction(import_action)

        # Excel 내보내기 기능 임시 비활성화 (향후 재활성화를 위해 주석 처리)
        # export_action = QAction("Excel 내보내기(&E)...", self)
        # export_action.setShortcut(QKeySequence("Ctrl+Shift+E"))  # 충돌 없는 단축키 사용
        # export_action.setStatusTip("현재 선택된 파일을 Excel 파일로 내보냅니다.")
        # export_action.triggered.connect(self.export_to_excel)
        # file_menu.addAction(export_action)

        file_menu.addSeparator()

        # CSV 히스토리 생성 액션
        csv_history_action = QAction("CSV 히스토리 생성(&H)...", self)
        csv_history_action.setShortcut(QKeySequence("Ctrl+H"))
        csv_history_action.setStatusTip("열린 모든 DB의 시트를 CSV로 내보내기")
        csv_history_action.triggered.connect(self.generate_csv_history)
        file_menu.addAction(csv_history_action)

        file_menu.addSeparator()

        save_action = QAction("현재 시트 저장(&S)", self)
        save_action.setShortcut(QKeySequence.Save)  # 표준 단축키 사용
        save_action.setStatusTip("현재 편집 중인 시트의 변경 사항을 저장합니다.")
        save_action.triggered.connect(self.save_current_sheet)
        file_menu.addAction(save_action)

        file_menu.addSeparator()

        exit_action = QAction("종료(&X)", self)
        exit_action.setShortcut(QKeySequence.Quit)  # 표준 단축키 사용
        exit_action.setStatusTip("애플리케이션을 종료합니다.")
        exit_action.triggered.connect(self.close)  # QMainWindow의 close 슬롯 사용
        file_menu.addAction(exit_action)

        # --- 편집 메뉴 ---
        edit_menu = menu_bar.addMenu("편집(&E)")

        # 실행 취소/다시 실행
        undo_action = QAction("실행 취소(&U)", self)
        undo_action.setShortcut(QKeySequence.Undo)
        undo_action.triggered.connect(lambda: self.grid_view.model.undo_stack.undo() if self.grid_view.model else None)
        edit_menu.addAction(undo_action)

        redo_action = QAction("다시 실행(&R)", self)
        redo_action.setShortcut(QKeySequence.Redo)
        redo_action.triggered.connect(lambda: self.grid_view.model.undo_stack.redo() if self.grid_view.model else None)
        edit_menu.addAction(redo_action)

        edit_menu.addSeparator()

        # 복사/붙여넣기/삭제
        copy_action = QAction("복사(&C)", self)
        copy_action.setShortcut(QKeySequence.Copy)
        copy_action.triggered.connect(self.grid_view.copy_selection)
        edit_menu.addAction(copy_action)

        paste_action = QAction("붙여넣기(&P)", self)
        paste_action.setShortcut(QKeySequence.Paste)
        paste_action.triggered.connect(self.grid_view.paste_to_selection)
        edit_menu.addAction(paste_action)

        clear_action = QAction("내용 지우기(&L)", self)
        clear_action.setShortcut(QKeySequence.Delete)
        clear_action.triggered.connect(self.grid_view.clear_selection)
        edit_menu.addAction(clear_action)

        edit_menu.addSeparator()

        # --- 행/열 관리 하위 메뉴 ---
        row_col_menu = edit_menu.addMenu("행/열 관리(&M)")

        insert_row_action = QAction("행 삽입(&I)", self)
        insert_row_action.setShortcut(QKeySequence("Ctrl+I"))  # 충돌 없는 단축키
        insert_row_action.triggered.connect(self.grid_view.insert_selected_rows)
        row_col_menu.addAction(insert_row_action)

        delete_row_action = QAction("행 삭제(&R)", self)
        delete_row_action.setShortcut(QKeySequence("Ctrl+R"))  # 충돌 없는 단축키로 변경
        delete_row_action.setStatusTip("선택한 행을 삭제합니다")
        delete_row_action.triggered.connect(self.grid_view.handle_delete_rows)
        row_col_menu.addAction(delete_row_action)

        row_col_menu.addSeparator()

        # 열 관련 동작
        insert_col_action = QAction("열 삽입(&C)", self)
        insert_col_action.setShortcut(QKeySequence("Ctrl+Shift+I"))  # 충돌 없는 단축키
        insert_col_action.setStatusTip("선택한 열 앞에 새 열을 삽입합니다")
        insert_col_action.triggered.connect(self.grid_view.insert_selected_columns)
        row_col_menu.addAction(insert_col_action)

        delete_col_action = QAction("열 삭제(&D)", self)
        delete_col_action.setShortcut(QKeySequence("Ctrl+D"))  # 충돌 없는 단축키로 변경
        delete_col_action.setStatusTip("선택한 열을 삭제합니다")
        delete_col_action.triggered.connect(self.grid_view.handle_delete_columns)
        row_col_menu.addAction(delete_col_action)

        # 선택 관련 동작 추가
        edit_menu.addSeparator()
        select_menu = edit_menu.addMenu("선택(&S)")

        select_row_action = QAction("행 전체 선택(&R)", self)
        select_row_action.setShortcut(QKeySequence("Shift+Space"))
        select_row_action.setStatusTip("현재 커서가 있는 행 전체를 선택합니다")
        select_row_action.triggered.connect(self.grid_view.select_current_row)
        select_menu.addAction(select_row_action)

        select_col_action = QAction("열 전체 선택(&C)", self)
        select_col_action.setShortcut(QKeySequence("Ctrl+Space"))
        select_col_action.setStatusTip("현재 커서가 있는 열 전체를 선택합니다")
        select_col_action.triggered.connect(self.grid_view.select_current_column)
        select_menu.addAction(select_col_action)

        # --- 코드 메뉴 ---
        code_menu = menu_bar.addMenu("코드(&C)")
        generate_action = QAction("C 코드 생성(&G)...", self)
        generate_action.setShortcut(QKeySequence("Ctrl+G"))  # 단축키 추가
        generate_action.setStatusTip("현재 선택된 파일의 $ 시트들을 기반으로 C 코드를 생성합니다.")
        generate_action.triggered.connect(self.generate_code)
        code_menu.addAction(generate_action)



        # --- 도움말 메뉴 ---
        help_menu = menu_bar.addMenu("도움말(&H)")

        # 단축키 도움말 항목 추가
        shortcuts_action = QAction("단축키 목록(&K)", self)
        shortcuts_action.setStatusTip("사용 가능한 단축키 목록을 표시합니다")
        shortcuts_action.triggered.connect(self.show_shortcuts_help)
        help_menu.addAction(shortcuts_action)

        help_menu.addSeparator()

        about_action = QAction("정보(&A)", self)
        about_action.setStatusTip("프로그램 정보를 표시합니다.")
        about_action.triggered.connect(self.show_about_dialog)
        help_menu.addAction(about_action)

    def show_shortcuts_help(self):
            """단축키 도움말 대화상자 표시"""
            shortcut_text = """
        <h3>주요 단축키 목록</h3>
        <table border="0" cellspacing="5">
            <tr><th>동작</th><th>단축키</th></tr>
            <tr><td>파일 저장</td><td>Ctrl+S</td></tr>
            <tr><td>복사</td><td>Ctrl+C</td></tr>
            <tr><td>붙여넣기</td><td>Ctrl+V</td></tr>
            <tr><td>셀 내용 삭제</td><td>Delete</td></tr>
            <tr><td>행 선택</td><td>Shift+Space</td></tr>
            <tr><td>열 선택</td><td>Ctrl+Space</td></tr>
            <tr><td>행 삭제</td><td>Ctrl+R</td></tr>
            <tr><td>열 삭제</td><td>Ctrl+D</td></tr>
            <tr><td>행 삽입</td><td>Ctrl+I</td></tr>
            <tr><td>열 삽입</td><td>Ctrl+Shift+I</td></tr>
            <tr><td>실행 취소</td><td>Ctrl+Z</td></tr>
            <tr><td>다시 실행</td><td>Ctrl+Y</td></tr>
        </table>
            """
            QMessageBox.information(self, "단축키 도움말", shortcut_text)

    def show_about_dialog(self):
        """프로그램 정보 대화상자 표시"""
        # 현재 날짜 정보
        from datetime import datetime
        current_year = datetime.now().year

        about_text = f"""
        <div style="text-align: center; padding: 20px;">
            <h1 style="color: #2c3e50; font-size: 24pt; margin-bottom: 10px;">{Info.APP_NAME}</h1>
            <h3 style="color: #34495e; font-size: 14pt; margin-bottom: 20px;">버전 {Info.APP_VERSION}</h3>

            <div style="background-color: #f8f9fa; padding: 15px; border-radius: 8px; margin: 15px 0;">
                <p style="font-size: 11pt; color: #495057; margin: 5px 0; text-align: center;">
                    <strong>SQLite 기반 Cal 데이터 관리 및 C/H 코드 생성 도구</strong>
                </p>
            </div>

            <div style="text-align: left; margin: 20px 0;">
                <h4 style="color: #2c3e50; font-size: 12pt; margin-bottom: 10px;">주요 기능</h4>
                <ul style="font-size: 10pt; color: #495057; line-height: 1.6;">
                    <li>SQLite 데이터베이스 기반 Cal 데이터 관리</li>
                    <li>Excel → DB 변환 지원</li>
                    <li>실시간 데이터 편집 및 검증</li>
                    <li>자동 C/H 코드 생성 및 관리</li>
                    <li>Git 기반 버전 관리 통합</li>
                    <li>CSV 히스토리 관리</li>
                </ul>
            </div>

            <div style="text-align: left; margin: 20px 0;">
                <h4 style="color: #2c3e50; font-size: 12pt; margin-bottom: 10px;">기술 정보</h4>
                <p style="font-size: 10pt; color: #6c757d; line-height: 1.5;">
                    • 개발 언어: Python 3.x<br>
                    • UI 프레임워크: PySide6 (Qt6)<br>
                    • 데이터베이스: SQLite<br>
                    • 버전 관리: Git 통합<br>
                    • 플랫폼: Windows
                </p>
            </div>

            <hr style="border: none; border-top: 1px solid #dee2e6; margin: 20px 0;">

            <p style="font-size: 10pt; color: #6c757d; margin: 10px 0; text-align: center;">
                문의: 인버터설계2팀 임현재 연구원
            </p>
        </div>
        """

        # 커스텀 메시지박스 생성
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("프로그램 정보")
        msg_box.setText(about_text)
        msg_box.setTextFormat(Qt.RichText)
        msg_box.setStandardButtons(QMessageBox.Ok)
        msg_box.setMinimumSize(500, 400)
        msg_box.exec()

    def create_tool_bar(self):
        """툴바 생성"""
        tool_bar = QToolBar("메인 툴바")
        tool_bar.setIconSize(QSize(24, 24)) # 아이콘 크기 조정
        self.addToolBar(tool_bar)

        # 가져오기 액션
        import_action = QAction(QIcon.fromTheme("document-open"), "가져오기", self)
        import_action.setStatusTip("Excel 파일을 데이터베이스로 가져옵니다.")
        import_action.triggered.connect(self.import_excel_file)
        tool_bar.addAction(import_action)

        # 내보내기 액션
        export_action = QAction(QIcon.fromTheme("document-save-as"), "내보내기", self)
        export_action.setStatusTip("현재 파일을 Excel 파일로 내보냅니다.")
        export_action.triggered.connect(self.export_to_excel)
        tool_bar.addAction(export_action)

        tool_bar.addSeparator()

        # 저장 액션
        save_action = QAction(QIcon.fromTheme("document-save"), "저장", self)
        save_action.setStatusTip("현재 시트의 변경 사항을 저장합니다.")
        save_action.triggered.connect(self.save_current_sheet)
        tool_bar.addAction(save_action)

        tool_bar.addSeparator()

        # 코드 생성 액션
        generate_action = QAction(QIcon.fromTheme("utilities-terminal"), "코드 생성", self)
        generate_action.setStatusTip("현재 파일 기반으로 C 코드를 생성합니다.")
        generate_action.triggered.connect(self.generate_code)
        tool_bar.addAction(generate_action)

        tool_bar.addSeparator()

        # 복사/붙여넣기/지우기 (선택사항)
        copy_action = QAction(QIcon.fromTheme("edit-copy"), "복사", self)
        copy_action.triggered.connect(self.grid_view.copy_selection)
        tool_bar.addAction(copy_action)

        paste_action = QAction(QIcon.fromTheme("edit-paste"), "붙여넣기", self)
        paste_action.triggered.connect(self.grid_view.paste_to_selection)
        tool_bar.addAction(paste_action)

        clear_action = QAction(QIcon.fromTheme("edit-clear"), "지우기", self)
        clear_action.triggered.connect(self.grid_view.clear_selection)
        tool_bar.addAction(clear_action)


    def load_files(self):
        """DB에서 시트 목록 로드 및 트리뷰 업데이트 (V2: 다중 DB 지원)"""
        try:
            # 다중 DB 환경에서 모든 DB의 시트 정보 수집
            all_sheets = []
            db_count = self.db_manager.get_database_count()

            logging.info(f"🔄 load_files 시작 - DB 개수: {db_count}, 현재 활성 DB: {self.db_manager.current_db_name}")

            if db_count == 0:
                # DB가 없는 경우 빈 리스트로 초기화
                all_sheets = []
                logging.info("열린 DB가 없습니다. 시트 목록을 비웁니다.")
            else:
                # 모든 경우에 다중 DB 처리 방식 사용 (일관성 보장)
                all_sheets_info = self.db_manager.get_all_sheets_info()
                logging.info(f"🔄 다중 DB 시트 정보: {list(all_sheets_info.keys())}")

                # 현재 활성 DB의 시트만 표시 (UI 혼란 방지)
                current_db_name = self.db_manager.current_db_name
                if current_db_name and current_db_name in all_sheets_info:
                    all_sheets = all_sheets_info[current_db_name]
                    logging.info(f"🔄 현재 활성 DB '{current_db_name}'에서 {len(all_sheets)}개 시트 로드")

                    # 각 시트에 DB 정보 추가
                    for sheet in all_sheets:
                        sheet['db_name'] = current_db_name
                        sheet['db_source'] = f"[{current_db_name}]"
                else:
                    # 활성 DB가 없으면 빈 리스트
                    all_sheets = []
                    logging.warning(f"🔄 활성 DB가 없거나 찾을 수 없음: {current_db_name}")

                logging.info(f"🔄 총 {db_count}개 DB 중 활성 DB '{current_db_name}'의 {len(all_sheets)}개 시트 표시")

            # V2 구조에서는 시트를 source_file별로 그룹화하여 트리뷰에 표시
            self.tree_view.update_sheets_v2(all_sheets)

            # 상태바 메시지 업데이트
            if db_count > 1:
                current_db_name = self.db_manager.current_db_name
                self.statusBar.showMessage(f"활성 DB '{current_db_name}': {len(all_sheets)}개 시트 (총 {db_count}개 DB 관리 중)")
            elif db_count == 1:
                self.statusBar.showMessage(f"{len(all_sheets)}개 시트 로드 완료")
            else:
                self.statusBar.showMessage("DB가 열려있지 않음")

            # 활성 DB의 첫 번째 시트 자동 선택 (일관된 동작)
            if all_sheets:
                first_sheet = all_sheets[0]

                try:
                    self.current_sheet_id = first_sheet['id']
                    self.current_file_id = 1  # 가상 파일 ID (V1 호환)

                    # 그리드뷰에 시트 로드
                    self.grid_view.load_sheet(first_sheet['id'])
                    self.sheet_label.setText(f"현재 시트: {first_sheet['name']}")
                    logging.info(f"🔄 활성 DB의 첫 번째 시트 자동 선택 - {first_sheet['name']}")
                except Exception as e:
                    logging.warning(f"첫 시트 자동 선택 중 오류: {e}")
                    self.current_file_id = None
                    self.current_sheet_id = None
                    self.grid_view.clear_view()
                    self.sheet_label.setText("시트 선택 실패")
            else:
                # 시트가 하나도 없는 경우
                self.current_file_id = None
                self.current_sheet_id = None
                self.grid_view.clear_view()
                self.sheet_label.setText("선택된 시트 없음")

        except Exception as e:
            error_msg = f"시트 목록 로드 중 오류 발생: {str(e)}"
            logging.error(f"{error_msg}\n{traceback.format_exc()}")
            QMessageBox.critical(self, "시트 로드 오류", error_msg)
            self.statusBar.showMessage("시트 목록 로드 실패")

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

            # 여기에 다음 한 줄을 추가하세요 - 이것이 검은 화면 문제를 해결합니다
            self.viewport().update()

        except Exception as e:
            logging.error(f"Error loading sheet {sheet_id} in view: {e}")
            QMessageBox.critical(self, "오류", f"시트 로드 중 오류 발생: {str(e)}")


    @Slot(int, str)
    def on_sheet_selected(self, sheet_id: int, sheet_name: str):
        """
        시트 선택 이벤트 처리 (TreeView의 sheet_selected 시그널에 연결된 슬롯)

        Args:
            sheet_id: 선택된 시트 ID
            sheet_name: 선택된 시트 이름
        """
        if sheet_id < 0: # 시트 선택 해제 시 (예: 빈 공간 클릭)
            self.current_sheet_id = None
            # self.grid_view.clear_view() # 선택사항: 시트 선택 해제 시 그리드 비우기
            # self.sheet_label.setText("선택된 시트 없음")
            logging.debug("Sheet selection cleared.")
            return

        # 현재 파일 ID 찾기 (선택된 시트의 부모 파일)
        selected_index = self.tree_view.currentIndex()
        parent_index = selected_index.parent()
        if parent_index.isValid() and parent_index.data(Qt.UserRole + 1) == "file":
            self.current_file_id = parent_index.data(Qt.UserRole)
        else:
            # 부모를 못찾는 경우? 로깅하고 현재 파일 ID 유지 시도
            logging.warning(f"선택된 시트(ID:{sheet_id})의 부모 파일 노드를 찾을 수 없습니다.")
            # self.current_file_id = None # 또는 유지

        # 현재 시트 ID 업데이트
        self.current_sheet_id = sheet_id

        logging.info(f"Sheet selected: ID={sheet_id}, Name='{sheet_name}', File ID={self.current_file_id}")

        try:
            # 그리드뷰에 시트 로드 (모델이 DB에서 데이터 가져옴)
            self.grid_view.load_sheet(sheet_id)

            # 시트 레이블 업데이트
            self.sheet_label.setText(f"현재 시트: {sheet_name}")

            self.statusBar.showMessage(f"시트 '{sheet_name}' 로드 완료")
        except Exception as e:
            error_msg = f"시트 데이터 로드 중 오류 발생 (Sheet ID: {sheet_id}): {str(e)}"
            logging.error(error_msg)
            QMessageBox.critical(self, "시트 로드 오류", error_msg)
            self.grid_view.clear_view() # 오류 시 그리드뷰 비우기
            self.sheet_label.setText(f"시트 '{sheet_name}' 로드 실패")

    def setup_db_connection(self, db_file_path: str, operation_name: str = "초기화") -> bool:
        """
        DB 연결 및 관련 객체 초기화를 위한 공통 메서드

        Args:
            db_file_path: DB 파일 경로
            operation_name: 작업 이름(오류 메시지에 표시)

        Returns:
            성공 여부
        """
        try:
            logging.info(f"DB 연결 시도: {db_file_path}")
            self.statusBar.showMessage(f"DB {operation_name} 중...")
            QApplication.processEvents()  # 상태 메시지 업데이트 강제

            # DBManager를 통해 DB 추가
            db_name = self.db_manager.add_database(db_file_path)

            # 현재 활성 DB로 설정
            self.db_manager.switch_database(db_name)

            # 기존 코드 호환성을 위해 현재 DB 참조 업데이트
            self.update_current_db_references()

            # DB 구조 확인 및 테이블 존재 여부 확인
            if self.db:
                self.check_db_structure()

            # 파일 목록 새로고침 (새 파일 및 시트 포함)
            self.load_files()

            # DB 드롭다운 업데이트
            self.update_db_combo()

            # 성공적으로 DB 연결 시 설정에 저장
            self.save_last_db_file(db_file_path)

            return True

        except Exception as e:
            error_msg = f"DB {operation_name} 중 오류 발생: {str(e)}"
            logging.error(f"{error_msg}\n{traceback.format_exc()}")
            QMessageBox.critical(self, f"{operation_name} 오류", error_msg)
            self.statusBar.showMessage(f"DB {operation_name} 실패")
            return False

    def setup_new_db_connection(self, db_file_path: str, operation_name: str) -> bool:
        """
        새 DB 파일 생성 및 연결 (Excel 가져오기용)

        Args:
            db_file_path: 생성할 DB 파일 경로
            operation_name: 작업 이름(오류 메시지에 표시)

        Returns:
            성공 여부
        """
        try:
            logging.info(f"새 DB 생성 시도: {db_file_path}")
            self.statusBar.showMessage(f"새 DB {operation_name} 중...")
            QApplication.processEvents()  # 상태 메시지 업데이트 강제

            # DBManager를 통해 새 DB 생성 및 추가
            db_name = self.db_manager.create_and_add_database(db_file_path)

            # 현재 활성 DB로 설정
            self.db_manager.switch_database(db_name)

            # 기존 코드 호환성을 위해 현재 DB 참조 업데이트
            self.update_current_db_references()

            # DB 구조 확인 및 테이블 존재 여부 확인
            if self.db:
                self.check_db_structure()

            # 파일 목록 새로고침 (새 파일 및 시트 포함)
            self.load_files()

            # 성공적으로 DB 생성 시 설정에 저장
            self.save_last_db_file(db_file_path)

            return True

        except Exception as e:
            error_msg = f"새 DB {operation_name} 중 오류 발생: {str(e)}"
            logging.error(f"{error_msg}\n{traceback.format_exc()}")
            QMessageBox.critical(self, f"{operation_name} 오류", error_msg)
            self.statusBar.showMessage(f"새 DB {operation_name} 실패")
            return False

    def save_last_db_file(self, db_file_path: str):
        """마지막으로 열었던 DB 파일 경로를 설정에 저장"""
        try:
            self.settings.setValue("last_db_file", db_file_path)
            self.settings.setValue(Info.LAST_DIRECTORY_KEY, os.path.dirname(db_file_path))
            logging.info(f"마지막 DB 파일 경로 저장: {db_file_path}")
        except Exception as e:
            logging.warning(f"설정 저장 중 오류: {e}")

    def load_last_db_file(self):
        """마지막으로 열었던 DB 파일을 자동으로 로드 (안전한 처리)"""
        try:
            last_db_file = self.settings.value("last_db_file", "")
            if last_db_file:
                if os.path.exists(last_db_file):
                    logging.info(f"마지막 DB 파일 자동 로드 시도: {last_db_file}")
                    if self.setup_db_connection(last_db_file, "자동 로드"):
                        self.statusBar.showMessage(f"마지막 DB 파일 자동 로드 완료: {os.path.basename(last_db_file)}")
                        logging.info(f"마지막 DB 파일 자동 로드 성공: {last_db_file}")
                    else:
                        logging.warning(f"마지막 DB 파일 자동 로드 실패: {last_db_file}")
                        self.statusBar.showMessage("마지막 DB 파일 로드 실패")
                else:
                    # 파일이 존재하지 않는 경우 경고 메시지만 표시하고 계속 진행
                    logging.warning(f"마지막 DB 파일이 존재하지 않음: {last_db_file}")
                    self.statusBar.showMessage(f"마지막 DB 파일을 찾을 수 없음: {os.path.basename(last_db_file)}")

                    # 사용자에게 알림 (선택사항)
                    QMessageBox.information(
                        self, "DB 파일 없음",
                        f"마지막으로 사용한 DB 파일을 찾을 수 없습니다:\n{last_db_file}\n\n"
                        "새 Excel 파일을 가져오거나 다른 DB 파일을 열어주세요."
                    )

                    # 설정에서 존재하지 않는 파일 경로 제거
                    self.settings.remove("last_db_file")
            else:
                logging.info("저장된 마지막 DB 파일 없음")
                self.statusBar.showMessage("새 프로젝트를 시작하세요")
        except Exception as e:
            logging.warning(f"마지막 DB 파일 자동 로드 중 오류: {e}")
            self.statusBar.showMessage("DB 파일 자동 로드 중 오류 발생")

    def auto_load_multi_db(self):
        """단일 DB 로드"""
        try:
            logging.info("앱 시작 시 마지막 DB 파일 로드 시도")

            # 기존 단일 DB 로드 방식 사용
            self.load_last_db_file()

            # DB 드롭다운 업데이트
            self.update_db_combo()

        except Exception as e:
            logging.error(f"DB 자동 로드 중 오류: {e}")
            import traceback
            traceback.print_exc()

            # 오류 발생 시 상태 메시지 표시
            self.statusBar.showMessage("DB 자동 로드 실패")

    def select_database_for_code_generation(self) -> Optional['DBHandlerV2']:
        """
        코드 생성을 위한 데이터베이스 선택

        Returns:
            선택된 DBHandlerV2 또는 None (취소/오류)
        """
        db_count = self.db_manager.get_database_count()

        if db_count == 0:
            QMessageBox.warning(self, "코드 생성 경고", "열린 데이터베이스가 없습니다.\n먼저 DB 파일을 열어주세요.")
            return None
        elif db_count == 1:
            # 단일 DB면 자동 선택
            current_db = self.db_manager.get_current_db()
            db_name = self.db_manager.current_db_name
            logging.info(f"단일 DB 자동 선택: {db_name}")
            return current_db
        else:
            # 다중 DB면 사용자 선택
            return self.show_database_selection_dialog()

    def show_database_selection_dialog(self) -> Optional['DBHandlerV2']:
        """
        데이터베이스 선택 대화상자 표시 (단일 선택용 - 호환성 유지)

        Returns:
            선택된 DBHandlerV2 또는 None (취소)
        """
        selected_dbs = self.show_multiple_database_selection_dialog()
        if selected_dbs and len(selected_dbs) > 0:
            return selected_dbs[0]  # 첫 번째 선택된 DB 반환
        return None

    def show_multiple_database_selection_dialog(self) -> List['DBHandlerV2']:
        """
        다중 데이터베이스 선택 대화상자 표시 (체크박스 방식)

        Returns:
            선택된 DBHandlerV2 리스트
        """
        db_info_list = self.db_manager.get_database_info()
        if not db_info_list:
            return []

        # 커스텀 다중 선택 대화상자 생성
        from PySide6.QtWidgets import QDialog, QVBoxLayout, QCheckBox, QPushButton, QHBoxLayout, QLabel, QScrollArea, QWidget

        dialog = QDialog(self)
        dialog.setWindowTitle("코드 생성할 데이터베이스 선택")
        dialog.setMinimumSize(400, 300)

        layout = QVBoxLayout(dialog)

        # 안내 메시지
        info_label = QLabel("코드를 생성할 데이터베이스를 선택하세요 (다중 선택 가능):")
        info_label.setWordWrap(True)
        layout.addWidget(info_label)

        # 스크롤 영역 생성
        scroll_area = QScrollArea()
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)

        # 체크박스 리스트 생성
        checkboxes = []
        for info in db_info_list:
            checkbox = QCheckBox(f"{info['name']} ({info['path']})")
            checkbox.setChecked(False)  # 기본적으로 아무것도 선택하지 않음 (사용자 명시적 선택 유도)
            checkboxes.append((checkbox, info))
            scroll_layout.addWidget(checkbox)

        scroll_area.setWidget(scroll_widget)
        layout.addWidget(scroll_area)

        # 전체 선택/해제 버튼
        select_buttons_layout = QHBoxLayout()
        select_all_btn = QPushButton("전체 선택")
        select_none_btn = QPushButton("전체 해제")

        def select_all():
            for checkbox, _ in checkboxes:
                checkbox.setChecked(True)

        def select_none():
            for checkbox, _ in checkboxes:
                checkbox.setChecked(False)

        select_all_btn.clicked.connect(select_all)
        select_none_btn.clicked.connect(select_none)

        select_buttons_layout.addWidget(select_all_btn)
        select_buttons_layout.addWidget(select_none_btn)
        select_buttons_layout.addStretch()
        layout.addLayout(select_buttons_layout)

        # 확인/취소 버튼
        button_layout = QHBoxLayout()
        ok_button = QPushButton("확인")
        cancel_button = QPushButton("취소")

        ok_button.clicked.connect(dialog.accept)
        cancel_button.clicked.connect(dialog.reject)

        button_layout.addStretch()
        button_layout.addWidget(ok_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)

        # 대화상자 실행
        if dialog.exec() == QDialog.Accepted:
            selected_dbs = []
            for checkbox, info in checkboxes:
                if checkbox.isChecked():
                    db_handler = self.db_manager.get_database(info['name'])
                    if db_handler:
                        selected_dbs.append(db_handler)
            return selected_dbs

        return []

    def show_file_selection_dialog(self) -> Optional[int]:
        """
        파일 선택 대화상자 표시

        Returns:
            선택된 파일 ID 또는 None (취소)
        """
        if not self.db:
            return None

        files = self.db.get_files()
        if not files:
            return None

        # 파일 이름 목록 생성
        file_names = [f['name'] for f in files]

        from PySide6.QtWidgets import QInputDialog
        selected_name, ok = QInputDialog.getItem(
            self, "파일 선택",
            "코드를 생성할 파일을 선택하세요:",
            file_names, 0, False
        )

        if ok and selected_name:
            selected_file = next((f for f in files if f['name'] == selected_name), None)
            return selected_file['id'] if selected_file else None

        return None

    def check_db_structure(self):
        """
        DB 구조와 테이블 설정을 확인하는 유틸리티 메서드 (V2 구조 대응)
        """
        try:
            self.db.cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in self.db.cursor.fetchall()]
            logging.info(f"DB 테이블 목록: {tables}")

            # V2 구조 확인: files 테이블은 더 이상 사용하지 않음
            db_version = "V2" if 'files' not in tables else "V1"
            logging.info(f"DB 구조 버전: {db_version}")

            if db_version == "V1":
                # V1 구조: files 테이블 확인
                if 'files' in tables:
                    self.db.cursor.execute("SELECT COUNT(*) FROM files")
                    files_count = self.db.cursor.fetchone()[0]
                    logging.info(f"DB 파일 개수 (V1): {files_count}")

                    # 파일 정보 상세 확인
                    if files_count > 0:
                        self.db.cursor.execute("SELECT id, name FROM files")
                        file_rows = self.db.cursor.fetchall()
                        for row in file_rows:
                            logging.info(f"DB 파일 ID: {row[0]}, 이름: {row[1]}")
                else:
                    logging.warning("V1 구조이지만 'files' 테이블이 없습니다.")
            else:
                # V2 구조: files 테이블 없음이 정상
                logging.info("V2 구조 확인: files 테이블 없음 (정상)")

            # sheets 테이블 확인 (V1, V2 공통)
            if 'sheets' in tables:
                self.db.cursor.execute("SELECT COUNT(*) FROM sheets")
                sheets_count = self.db.cursor.fetchone()[0]
                logging.info(f"DB 시트 개수: {sheets_count}")

                # 시트 정보 상세 확인 (V2에서는 source_file 정보도 표시)
                if sheets_count > 0:
                    if db_version == "V2":
                        self.db.cursor.execute("SELECT id, name, is_dollar_sheet, source_file FROM sheets LIMIT 5")
                        sheet_rows = self.db.cursor.fetchall()
                        for row in sheet_rows:
                            logging.info(f"DB 시트 ID: {row[0]}, 이름: {row[1]}, $ 시트: {row[2]}, 원본 파일: {row[3]}")
                    else:
                        self.db.cursor.execute("SELECT id, name, is_dollar_sheet FROM sheets LIMIT 5")
                        sheet_rows = self.db.cursor.fetchall()
                        for row in sheet_rows:
                            logging.info(f"DB 시트 ID: {row[0]}, 이름: {row[1]}, $ 시트: {row[2]}")
            else:
                logging.warning("DB에 'sheets' 테이블이 없습니다.")

            # cells 테이블 확인 (V1, V2 공통)
            if 'cells' in tables:
                self.db.cursor.execute("SELECT COUNT(*) FROM cells")
                cells_count = self.db.cursor.fetchone()[0]
                logging.info(f"DB 셀 개수: {cells_count}")
            else:
                logging.warning("DB에 'cells' 테이블이 없습니다.")

        except Exception as e:
            logging.error(f"DB 구조 확인 중 오류: {e}")

    def create_new_db(self):
        """새로운 빈 데이터베이스 생성"""
        try:
            # 기본 DB 파일명 설정
            default_db_name = f"{Info.DEFAULT_DB_NAME}{Info.DB_EXTENSION}"

            # DB 파일 저장 대화상자
            db_file_path, _ = QFileDialog.getSaveFileName(
                self, "새 데이터베이스 생성",
                os.path.join(self.last_directory, default_db_name),
                Info.DB_FILE_FILTER
            )

            if not db_file_path:
                return  # 사용자가 취소

            # 확장자 확인 및 추가
            if not db_file_path.lower().endswith(Info.DB_EXTENSION):
                db_file_path += Info.DB_EXTENSION

            # 파일이 이미 존재하는 경우 확인
            if os.path.exists(db_file_path):
                reply = QMessageBox.question(
                    self, "파일 덮어쓰기 확인",
                    f"'{os.path.basename(db_file_path)}' 파일이 이미 존재합니다.\n덮어쓰시겠습니까?",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No
                )
                if reply == QMessageBox.No:
                    return

                # 기존 파일 삭제
                try:
                    os.remove(db_file_path)
                    logging.info(f"기존 DB 파일 삭제: {db_file_path}")
                except Exception as e:
                    QMessageBox.critical(self, "파일 삭제 오류", f"기존 파일을 삭제할 수 없습니다:\n{str(e)}")
                    return

            # 선택한 파일의 디렉토리 저장
            self.last_directory = os.path.dirname(db_file_path)
            self.settings.setValue(Info.LAST_DIRECTORY_KEY, self.last_directory)

            # 새 DB 생성 및 연결
            if self.setup_new_db_connection(db_file_path, "생성"):
                # DB 드롭다운 업데이트
                self.update_db_combo()

                db_name = os.path.splitext(os.path.basename(db_file_path))[0]
                self.statusBar.showMessage(f"새 데이터베이스 '{db_name}' 생성 완료")

                QMessageBox.information(
                    self, "DB 생성 완료",
                    f"새 데이터베이스가 성공적으로 생성되었습니다.\n\n"
                    f"파일: {os.path.basename(db_file_path)}\n"
                    f"위치: {os.path.dirname(db_file_path)}\n\n"
                    f"이제 Excel 파일을 가져오거나 직접 시트를 추가할 수 있습니다."
                )

                logging.info(f"새 DB 생성 완료: {db_file_path}")
            else:
                self.statusBar.showMessage("DB 생성 실패")

        except Exception as e:
            error_msg = f"새 데이터베이스 생성 중 오류 발생: {str(e)}"
            logging.error(f"{error_msg}\n{traceback.format_exc()}")
            QMessageBox.critical(self, "DB 생성 오류", error_msg)
            self.statusBar.showMessage("DB 생성 실패")

    def open_db_file(self):
        """DB 파일 열기 (다중 선택 자동 지원)"""
        try:
            # 다중 파일 선택 대화상자
            db_file_paths, _ = QFileDialog.getOpenFileNames(
                self, "DB 파일 선택 (다중 선택 가능)", self.last_directory, Info.DB_FILE_FILTER
            )

            if not db_file_paths:
                return  # 사용자가 취소

            # 선택한 파일의 디렉토리 저장
            self.last_directory = os.path.dirname(db_file_paths[0])
            self.settings.setValue(Info.LAST_DIRECTORY_KEY, self.last_directory)

            # 단일 파일 vs 다중 파일 자동 처리
            if len(db_file_paths) == 1:
                # 단일 파일 처리 (기존 DB 유지하고 추가)
                db_file_path = db_file_paths[0]
                try:
                    # DBManager를 통해 DB 추가 (기존 DB 유지)
                    db_name = self.db_manager.add_database(db_file_path, replace_existing=False)
                    logging.info(f"🔄 DB 추가 완료: {db_name}")

                    # 새로 추가된 DB를 현재 활성 DB로 전환
                    switch_success = self.db_manager.switch_database(db_name)
                    logging.info(f"🔄 DB 전환 시도: {db_name} -> 성공: {switch_success}")
                    logging.info(f"🔄 현재 활성 DB: {self.db_manager.current_db_name}")

                    # 현재 DB 참조 업데이트
                    self.update_current_db_references()
                    logging.info(f"🔄 DB 참조 업데이트 완료. self.db: {self.db}")

                    # 파일 목록 새로고침
                    self.load_files()

                    # DB 드롭다운 업데이트
                    self.update_db_combo()
                    logging.info(f"단일 DB 로드 후 드롭다운 업데이트 완료: {db_name}")

                    self.statusBar.showMessage(f"DB 파일 열기 완료: {os.path.basename(db_file_path)}")
                    QMessageBox.information(self, "열기 완료",
                                          f"'{os.path.basename(db_file_path)}' 데이터베이스를 성공적으로 열었습니다.\n"
                                          f"총 {self.db_manager.get_database_count()}개 DB가 관리 중입니다.")
                except Exception as e:
                    error_msg = f"DB 파일 열기 실패: {str(e)}"
                    logging.error(f"{error_msg}\n{traceback.format_exc()}")
                    QMessageBox.critical(self, "DB 열기 오류", error_msg)
            else:
                # 다중 파일 처리 (자동으로 모두 추가)
                self.process_multiple_db_files(db_file_paths)

        except Exception as e:
            error_msg = f"DB 파일 열기 중 오류 발생: {str(e)}"
            logging.error(f"{error_msg}\n{traceback.format_exc()}")
            QMessageBox.critical(self, "열기 오류", error_msg)
            self.statusBar.showMessage("DB 파일 열기 실패")

    def process_multiple_db_files(self, db_file_paths):
        """다중 DB 파일 처리 (단순화된 버전)"""
        try:
            # 진행률 대화상자 생성
            from PySide6.QtWidgets import QProgressDialog
            progress = QProgressDialog("DB 파일 열기 중...", "취소", 0, len(db_file_paths), self)
            progress.setWindowModality(Qt.WindowModal)
            progress.setMinimumDuration(0)
            progress.show()

            successful_opens = []
            failed_opens = []

            for i, db_file_path in enumerate(db_file_paths):
                if progress.wasCanceled():
                    break

                db_basename = os.path.basename(db_file_path)
                progress.setLabelText(f"열기 중: {db_basename}")
                progress.setValue(i)
                QApplication.processEvents()

                try:
                    logging.info(f"다중 DB 열기 [{i+1}/{len(db_file_paths)}]: {db_file_path}")

                    # DBManager를 통해 DB 추가 (자동으로 모두 추가)
                    db_name = self.db_manager.add_database(db_file_path, replace_existing=False)
                    successful_opens.append({
                        'db_file': db_basename,
                        'db_name': db_name
                    })
                    logging.info(f"다중 DB 열기 성공: {db_basename} -> {db_name}")

                except Exception as e:
                    error_msg = str(e)
                    failed_opens.append({
                        'db_file': db_basename,
                        'error': error_msg
                    })
                    logging.error(f"다중 DB 열기 실패 [{db_basename}]: {error_msg}")

            progress.setValue(len(db_file_paths))
            progress.close()

            # 성공한 경우 UI 업데이트
            if successful_opens:
                # 마지막으로 추가된 DB를 현재 활성 DB로 전환
                last_db_name = successful_opens[-1]['db_name']
                self.db_manager.switch_database(last_db_name)

                # 현재 DB 참조 업데이트
                self.update_current_db_references()

                # 파일 목록 새로고침
                self.load_files()

                # DB 드롭다운 업데이트 (버그 수정)
                self.update_db_combo()
                logging.info(f"다중 DB 로드 후 드롭다운 업데이트 완료: {len(successful_opens)}개 DB")

            # 간단한 결과 메시지
            if failed_opens:
                self.statusBar.showMessage(f"다중 DB 열기 완료: 성공 {len(successful_opens)}개, 실패 {len(failed_opens)}개")
                QMessageBox.information(self, "다중 DB 열기 완료",
                                      f"총 {len(db_file_paths)}개 파일 중 {len(successful_opens)}개 성공, {len(failed_opens)}개 실패")
            else:
                self.statusBar.showMessage(f"다중 DB 열기 완료: 모든 {len(successful_opens)}개 파일 성공")
                QMessageBox.information(self, "다중 DB 열기 완료",
                                      f"모든 {len(successful_opens)}개 DB 파일을 성공적으로 열었습니다.")

        except Exception as e:
            error_msg = f"다중 DB 파일 처리 중 오류 발생: {str(e)}"
            logging.error(f"{error_msg}\n{traceback.format_exc()}")
            QMessageBox.critical(self, "다중 처리 오류", error_msg)
            self.statusBar.showMessage("다중 DB 파일 처리 실패")

    def open_multiple_db_files(self):
        """여러 DB 파일을 동시에 열기"""
        try:
            # 여러 파일 선택 대화상자
            db_file_paths, _ = QFileDialog.getOpenFileNames(
                self, "여러 DB 파일 선택", self.last_directory, Info.DB_FILE_FILTER
            )

            if not db_file_paths:
                return  # 사용자가 취소

            # 선택한 파일의 디렉토리 저장
            if db_file_paths:
                self.last_directory = os.path.dirname(db_file_paths[0])
                self.settings.setValue(Info.LAST_DIRECTORY_KEY, self.last_directory)

            # 기존 DB 처리 방식 선택
            if self.db_manager.get_database_count() > 0:
                reply = QMessageBox.question(
                    self, "DB 열기 방식 선택",
                    f"현재 {self.db_manager.get_database_count()}개의 DB가 열려 있습니다.\n\n"
                    f"선택한 {len(db_file_paths)}개 DB 파일을 어떻게 처리하시겠습니까?",
                    QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,
                    QMessageBox.Yes
                )

                # 버튼 텍스트 커스터마이징
                reply_button = reply
                if reply == QMessageBox.Yes:
                    # 기존 DB 유지하고 추가
                    replace_existing = False
                elif reply == QMessageBox.No:
                    # 기존 DB 대체
                    replace_existing = True
                else:
                    return  # 취소
            else:
                replace_existing = False

            # 진행률 대화상자 생성
            from PySide6.QtWidgets import QProgressDialog
            progress = QProgressDialog("DB 파일 열기 중...", "취소", 0, len(db_file_paths), self)
            progress.setWindowModality(Qt.WindowModal)
            progress.setMinimumDuration(0)
            progress.show()

            # 첫 번째 파일은 replace_existing 설정 적용, 나머지는 추가 모드
            successful_opens = []
            failed_opens = []

            for i, db_file_path in enumerate(db_file_paths):
                if progress.wasCanceled():
                    break

                db_basename = os.path.basename(db_file_path)
                progress.setLabelText(f"열기 중: {db_basename}")
                progress.setValue(i)
                QApplication.processEvents()

                try:
                    # 첫 번째 파일만 replace_existing 적용
                    current_replace = replace_existing if i == 0 else False

                    logging.info(f"다중 DB 열기 [{i+1}/{len(db_file_paths)}]: {db_file_path}")

                    # DBManager를 통해 DB 추가
                    db_name = self.db_manager.add_database(db_file_path, current_replace)
                    successful_opens.append({
                        'db_file': db_basename,
                        'db_name': db_name
                    })
                    logging.info(f"다중 DB 열기 성공: {db_basename} -> {db_name}")

                except Exception as e:
                    error_msg = str(e)
                    failed_opens.append({
                        'db_file': db_basename,
                        'error': error_msg
                    })
                    logging.error(f"다중 DB 열기 실패 [{db_basename}]: {error_msg}")

            progress.setValue(len(db_file_paths))
            progress.close()

            # 성공한 경우 UI 업데이트
            if successful_opens:
                # 마지막으로 추가된 DB를 현재 활성 DB로 전환
                last_db_name = successful_opens[-1]['db_name']
                self.db_manager.switch_database(last_db_name)

                # 현재 DB 참조 업데이트
                self.update_current_db_references()

                # 파일 목록 새로고침
                self.load_files()

                # DB 드롭다운 업데이트
                self.update_db_combo()

            # 결과 표시
            self.show_multiple_db_open_result(successful_opens, failed_opens)

        except Exception as e:
            error_msg = f"다중 DB 파일 열기 중 오류 발생: {str(e)}"
            logging.error(f"{error_msg}\n{traceback.format_exc()}")
            QMessageBox.critical(self, "다중 열기 오류", error_msg)
            self.statusBar.showMessage("다중 DB 파일 열기 실패")

    def show_multiple_db_open_result(self, successful_opens, failed_opens):
        """다중 DB 열기 결과 표시"""
        result_dialog = QDialog(self)
        result_dialog.setWindowTitle("다중 DB 파일 열기 결과")
        result_dialog.setMinimumSize(500, 400)

        layout = QVBoxLayout(result_dialog)

        # 결과 요약
        summary_label = QLabel(f"총 {len(successful_opens + failed_opens)}개 DB 파일 처리 완료")
        summary_label.setFont(QFont("", 10, QFont.Bold))
        layout.addWidget(summary_label)

        # 성공한 파일들
        if successful_opens:
            success_label = QLabel(f"성공: {len(successful_opens)}개")
            success_label.setStyleSheet("color: green; font-weight: bold;")
            layout.addWidget(success_label)

            success_text = QTextEdit()
            success_text.setMaximumHeight(150)
            success_content = ""
            for item in successful_opens:
                success_content += f"• {item['db_file']} → DB 이름: {item['db_name']}\n"
            success_text.setPlainText(success_content)
            success_text.setReadOnly(True)
            layout.addWidget(success_text)

        # 실패한 파일들
        if failed_opens:
            fail_label = QLabel(f"실패: {len(failed_opens)}개")
            fail_label.setStyleSheet("color: red; font-weight: bold;")
            layout.addWidget(fail_label)

            fail_text = QTextEdit()
            fail_text.setMaximumHeight(150)
            fail_content = ""
            for item in failed_opens:
                fail_content += f"• {item['db_file']}: {item['error']}\n"
            fail_text.setPlainText(fail_content)
            fail_text.setReadOnly(True)
            layout.addWidget(fail_text)

        # 확인 버튼
        from PySide6.QtWidgets import QPushButton, QHBoxLayout
        button_layout = QHBoxLayout()
        ok_button = QPushButton("확인")
        ok_button.clicked.connect(result_dialog.accept)
        button_layout.addStretch()
        button_layout.addWidget(ok_button)
        layout.addLayout(button_layout)

        # 상태바 업데이트
        if failed_opens:
            self.statusBar.showMessage(f"다중 DB 열기 완료: 성공 {len(successful_opens)}개, 실패 {len(failed_opens)}개")
        else:
            self.statusBar.showMessage(f"다중 DB 열기 완료: 모든 {len(successful_opens)}개 파일 성공")

        result_dialog.exec()

    def import_excel_file(self):
        """Excel 파일을 DB로 변환 (다중 선택 자동 지원)"""
        try:
            # 다중 파일 선택 대화상자
            file_paths, _ = QFileDialog.getOpenFileNames(
                self, "Excel 파일 선택 (다중 선택 가능)", self.last_directory, "Excel 파일 (*.xlsx *.xls)"
            )

            if not file_paths:
                return # 사용자가 취소

            # 선택한 파일의 디렉토리 저장
            self.last_directory = os.path.dirname(file_paths[0])
            self.settings.setValue(Info.LAST_DIRECTORY_KEY, self.last_directory)

            # 단일 파일 vs 다중 파일 자동 처리
            if len(file_paths) == 1:
                # 단일 파일 처리
                self.process_single_excel_import(file_paths[0])
            else:
                # 다중 파일 처리 (단일 함수 반복 호출 방식)
                self.process_multiple_excel_files_simple(file_paths)

        except Exception as e:
            error_msg = f"Excel → DB 변환 중 오류 발생: {str(e)}"
            logging.error(f"{error_msg}\n{traceback.format_exc()}")
            QMessageBox.critical(self, "변환 오류", error_msg)
            self.statusBar.showMessage("Excel → DB 변환 실패")

    def process_single_excel_import(self, file_path):
        """단일 Excel 파일 가져오기 처리"""
        try:
            # 기본 DB 파일명 생성 (엑셀 파일명과 동일, 확장자는 .db)
            excel_basename = os.path.basename(file_path)
            excel_filename_only = os.path.splitext(excel_basename)[0]
            default_db_name = f"{excel_filename_only}.db"

            # DB 파일 저장 대화상자 (기본값: 엑셀 파일명과 동일한 DB명)
            db_file_path, _ = QFileDialog.getSaveFileName(
                self, "DB 파일 저장 위치 선택", os.path.join(self.last_directory, default_db_name),
                Info.DB_FILE_FILTER
            )

            if not db_file_path:
                return # 사용자가 취소

            # DB 파일 경로 저장 (다음번 사용을 위해)
            self.last_directory = os.path.dirname(db_file_path)
            self.settings.setValue(Info.LAST_DIRECTORY_KEY, self.last_directory)

            # Excel → DB 변환용 새 DB 생성 및 연결
            if not self.setup_new_db_connection(db_file_path, "변환"):
                return  # DB 생성 실패

            # Excel 파일을 DB로 변환 (사용자가 지정한 DB 파일명 전달)
            logging.info(f"Excel → DB 변환 시도: {file_path} -> {db_file_path}")
            self.statusBar.showMessage("Excel 파일을 DB로 변환 중...")
            QApplication.processEvents()  # 상태 메시지 업데이트 강제

            file_id = self.importer.import_excel(file_path, db_file_path)

            # 파일 목록 새로고침 (파일 변환 후 새 데이터 표시)
            self.load_files()

            # DB 드롭다운 업데이트
            self.update_db_combo()

            self.statusBar.showMessage(f"Excel → DB 변환 완료: {os.path.basename(file_path)} → {os.path.basename(db_file_path)}")
            QMessageBox.information(self, "변환 완료",
                                  f"'{os.path.basename(file_path)}' 파일을 '{os.path.basename(db_file_path)}' 데이터베이스로 성공적으로 변환했습니다.")

        except Exception as e:
            error_msg = f"Excel → DB 변환 중 오류 발생: {str(e)}"
            logging.error(f"{error_msg}\n{traceback.format_exc()}")
            QMessageBox.critical(self, "변환 오류", error_msg)
            self.statusBar.showMessage("Excel → DB 변환 실패")

    def process_multiple_excel_files_simple(self, file_paths):
        """다중 Excel 파일 처리 (단일 함수 반복 호출 방식 - 안정성 개선)"""
        try:
            # DB 저장 디렉토리 선택 대화상자
            save_directory = QFileDialog.getExistingDirectory(
                self, "DB 파일들을 저장할 디렉토리 선택", self.last_directory
            )

            if not save_directory:
                return  # 사용자가 취소

            # 진행률 대화상자 생성
            from PySide6.QtWidgets import QProgressDialog
            progress = QProgressDialog("다중 Excel 파일을 DB로 변환 중...", "취소", 0, len(file_paths), self)
            progress.setWindowTitle(Info.EXCEL_TO_DB_MULTI_PROGRESS_TITLE)
            progress.setWindowModality(Qt.WindowModal)
            progress.setMinimumDuration(0)
            progress.show()

            successful_imports = []
            failed_imports = []

            # 현재 DB 상태 백업 (복원용)
            original_db_state = {
                'db': self.db,
                'importer': self.importer,
                'exporter': self.exporter,
                'current_db_name': self.db_manager.current_db_name if hasattr(self.db_manager, 'current_db_name') else None
            }

            for i, file_path in enumerate(file_paths):
                if progress.wasCanceled():
                    break

                excel_basename = os.path.basename(file_path)
                progress.setLabelText(f"변환 중: {excel_basename}")
                progress.setValue(i)
                QApplication.processEvents()

                try:
                    logging.info(f"다중 Excel → DB 변환 [{i+1}/{len(file_paths)}]: {file_path}")

                    # 각 파일을 독립적으로 처리 (단일 파일 변환과 동일한 방식)
                    result = self.process_single_excel_import_isolated(file_path, save_directory)

                    if result:
                        successful_imports.append({
                            'excel_file': excel_basename,
                            'db_file': result['db_file'],
                            'db_path': result['db_path']
                        })
                        logging.info(f"다중 Excel → DB 변환 성공: {excel_basename}")
                    else:
                        failed_imports.append({
                            'excel_file': excel_basename,
                            'error': '변환 실패'
                        })

                except Exception as e:
                    error_msg = str(e)
                    failed_imports.append({
                        'excel_file': excel_basename,
                        'error': error_msg
                    })
                    logging.error(f"다중 Excel → DB 변환 실패 [{excel_basename}]: {error_msg}")
                    import traceback
                    logging.error(f"상세 오류: {traceback.format_exc()}")

            progress.setValue(len(file_paths))
            progress.close()

            # 원래 DB 상태 복원 (다중 처리 후 안정성 보장)
            try:
                if original_db_state['current_db_name']:
                    self.db_manager.switch_database(original_db_state['current_db_name'])
                self.update_current_db_references()
            except Exception as restore_error:
                logging.warning(f"원래 DB 상태 복원 중 오류: {restore_error}")

            # 성공한 DB들을 모두 DBManager에 추가
            if successful_imports:
                self.add_multiple_dbs_to_manager(successful_imports)

            # 파일 목록 새로고침
            self.load_files()

            # DB 드롭다운 업데이트 (중요: UI 동기화)
            self.update_db_combo()

            # 결과 메시지
            if failed_imports:
                self.statusBar.showMessage(f"다중 Excel → DB 변환 완료: 성공 {len(successful_imports)}개, 실패 {len(failed_imports)}개")
                QMessageBox.information(self, "다중 Excel → DB 변환 완료",
                                      f"총 {len(file_paths)}개 파일 중 {len(successful_imports)}개 성공, {len(failed_imports)}개 실패\n"
                                      f"저장 위치: {save_directory}")
            else:
                self.statusBar.showMessage(f"다중 Excel → DB 변환 완료: 모든 {len(successful_imports)}개 파일 성공")
                QMessageBox.information(self, "다중 Excel → DB 변환 완료",
                                      f"모든 {len(successful_imports)}개 Excel 파일을 성공적으로 DB로 변환했습니다.\n"
                                      f"저장 위치: {save_directory}")

        except Exception as e:
            error_msg = f"다중 Excel → DB 변환 중 오류 발생: {str(e)}"
            logging.error(f"{error_msg}\n{traceback.format_exc()}")
            QMessageBox.critical(self, "다중 변환 오류", error_msg)
            self.statusBar.showMessage("다중 Excel → DB 변환 실패")

    def process_single_excel_import_isolated(self, file_path, save_directory):
        """
        독립적인 단일 Excel 가져오기 (다중 처리용 - 안정성 강화)

        각 파일을 완전히 독립적으로 처리하여 데이터 손실 방지
        """
        db_handler = None
        importer = None

        try:
            # 기본 DB 파일명 생성 (엑셀 파일명과 동일, 확장자는 .db)
            excel_basename = os.path.basename(file_path)
            excel_filename_only = os.path.splitext(excel_basename)[0]
            default_db_name = f"{excel_filename_only}.db"

            # 자동으로 DB 파일 경로 생성 (사용자 선택 없이)
            db_file_path = os.path.join(save_directory, default_db_name)

            # 파일이 이미 존재하는 경우 고유한 이름 생성
            counter = 1
            original_db_path = db_file_path
            while os.path.exists(db_file_path):
                name_without_ext = os.path.splitext(original_db_path)[0]
                db_file_path = f"{name_without_ext}_{counter}.db"
                default_db_name = f"{excel_filename_only}_{counter}.db"
                counter += 1

            logging.info(f"독립적 Excel → DB 변환: {file_path} → {db_file_path}")

            # 새로운 독립적인 DB 핸들러 생성 (기존 연결과 분리)
            db_handler = DBHandlerV2(db_file_path)

            # 새로운 독립적인 Excel 변환 객체 생성
            importer = ExcelImporter(db_handler)

            # Excel 파일을 DB로 변환 (완전히 독립적으로 처리)
            logging.info(f"Excel → DB 변환 시작: {excel_basename}")
            file_id = importer.import_excel(file_path, db_file_path)

            # 변환 완료 후 연결 정리
            if db_handler:
                db_handler.disconnect()
                db_handler = None

            logging.info(f"독립적 Excel → DB 변환 완료: {excel_basename} → {default_db_name}")

            return {
                'db_file': default_db_name,
                'db_path': db_file_path,
                'file_id': file_id
            }

        except Exception as e:
            error_msg = f"독립적 Excel → DB 변환 중 오류 발생: {str(e)}"
            logging.error(f"{error_msg}\n{traceback.format_exc()}")

            # 오류 발생 시 리소스 정리
            if db_handler:
                try:
                    db_handler.disconnect()
                except:
                    pass

            return None

    def process_single_excel_import_auto(self, file_path, save_directory):
        """단일 Excel 가져오기 (자동 경로 생성 버전) - 기존 호환성 유지"""
        try:
            # 기본 DB 파일명 생성 (엑셀 파일명과 동일, 확장자는 .db)
            excel_basename = os.path.basename(file_path)
            excel_filename_only = os.path.splitext(excel_basename)[0]
            default_db_name = f"{excel_filename_only}.db"

            # 자동으로 DB 파일 경로 생성 (사용자 선택 없이)
            db_file_path = os.path.join(save_directory, default_db_name)

            logging.info(f"자동 Excel 가져오기: {file_path} → {db_file_path}")

            # Excel 가져오기용 새 DB 생성 및 연결 (단일 Excel 가져오기와 동일)
            if not self.setup_new_db_connection(db_file_path, "자동 가져오기"):
                return None  # DB 생성 실패

            # Excel 파일 가져오기 (단일 Excel 가져오기와 완전히 동일)
            self.statusBar.showMessage(f"Excel 파일 가져오는 중: {excel_basename}...")
            QApplication.processEvents()

            file_id = self.importer.import_excel(file_path, db_file_path)

            logging.info(f"자동 Excel 가져오기 완료: {excel_basename} → {default_db_name}")

            return {
                'db_file': default_db_name,
                'db_path': db_file_path,
                'file_id': file_id
            }

        except Exception as e:
            error_msg = f"자동 Excel 파일 가져오기 중 오류 발생: {str(e)}"
            logging.error(f"{error_msg}\n{traceback.format_exc()}")
            return None

    def process_multiple_excel_files(self, file_paths):
        """다중 Excel 파일 처리 (DB 저장 경로 선택 포함)"""
        try:
            # DB 저장 디렉토리 선택 대화상자
            save_directory = QFileDialog.getExistingDirectory(
                self, "DB 파일들을 저장할 디렉토리 선택", self.last_directory
            )

            if not save_directory:
                return  # 사용자가 취소

            # 선택한 디렉토리 저장
            self.last_directory = save_directory
            self.settings.setValue(Info.LAST_DIRECTORY_KEY, self.last_directory)

            # 진행률 대화상자 생성
            from PySide6.QtWidgets import QProgressDialog
            progress = QProgressDialog("Excel 파일을 DB로 변환 중...", "취소", 0, len(file_paths), self)
            progress.setWindowTitle(Info.EXCEL_TO_DB_MULTI_PROGRESS_TITLE)
            progress.setWindowModality(Qt.WindowModal)
            progress.setMinimumDuration(0)
            progress.show()

            successful_imports = []
            failed_imports = []

            for i, file_path in enumerate(file_paths):
                if progress.wasCanceled():
                    break

                excel_basename = os.path.basename(file_path)
                progress.setLabelText(f"처리 중: {excel_basename}")
                progress.setValue(i)
                QApplication.processEvents()

                try:
                    # 기본 DB 파일명 생성
                    excel_filename_only = os.path.splitext(excel_basename)[0]
                    db_filename = f"{excel_filename_only}.db"
                    db_file_path = os.path.join(save_directory, db_filename)

                    # 파일이 이미 존재하는 경우 고유한 이름 생성
                    counter = 1
                    original_db_path = db_file_path
                    while os.path.exists(db_file_path):
                        name_without_ext = os.path.splitext(original_db_path)[0]
                        db_file_path = f"{name_without_ext}_{counter}.db"
                        counter += 1

                    logging.info(f"다중 가져오기 [{i+1}/{len(file_paths)}]: {file_path} -> {db_file_path}")

                    # 새 DB 생성 및 Excel 가져오기
                    if self.setup_new_db_connection(db_file_path, "다중 가져오기"):
                        self.importer.import_excel(file_path, db_file_path)
                        successful_imports.append({
                            'excel_file': excel_basename,
                            'db_file': os.path.basename(db_file_path),
                            'db_path': db_file_path
                        })
                        logging.info(f"다중 가져오기 성공: {excel_basename}")
                    else:
                        failed_imports.append({
                            'excel_file': excel_basename,
                            'error': 'DB 생성 실패'
                        })

                except Exception as e:
                    error_msg = str(e)
                    failed_imports.append({
                        'excel_file': excel_basename,
                        'error': error_msg
                    })
                    logging.error(f"다중 가져오기 실패 [{excel_basename}]: {error_msg}")

            progress.setValue(len(file_paths))
            progress.close()

            # 성공한 DB들을 모두 DBManager에 추가
            if successful_imports:
                self.add_multiple_dbs_to_manager(successful_imports)

            # 파일 목록 새로고침
            self.load_files()

            # DB 드롭다운 업데이트 (중요: UI 동기화)
            self.update_db_combo()

            # 간단한 결과 메시지
            if failed_imports:
                self.statusBar.showMessage(f"다중 Excel → DB 변환 완료: 성공 {len(successful_imports)}개, 실패 {len(failed_imports)}개")
                QMessageBox.information(self, "다중 Excel → DB 변환 완료",
                                      f"총 {len(file_paths)}개 파일 중 {len(successful_imports)}개 성공, {len(failed_imports)}개 실패\n"
                                      f"저장 위치: {save_directory}")
            else:
                self.statusBar.showMessage(f"다중 Excel → DB 변환 완료: 모든 {len(successful_imports)}개 파일 성공")
                QMessageBox.information(self, "다중 Excel → DB 변환 완료",
                                      f"모든 {len(successful_imports)}개 Excel 파일을 성공적으로 DB로 변환했습니다.\n"
                                      f"저장 위치: {save_directory}")

        except Exception as e:
            error_msg = f"다중 Excel 파일 처리 중 오류 발생: {str(e)}"
            logging.error(f"{error_msg}\n{traceback.format_exc()}")
            QMessageBox.critical(self, "다중 처리 오류", error_msg)
            self.statusBar.showMessage("다중 Excel 파일 처리 실패")

    def add_multiple_dbs_to_manager(self, successful_imports):
        """성공적으로 가져온 DB들을 DBManager에 추가"""
        try:
            added_count = 0
            last_added_db_name = None

            for import_info in successful_imports:
                db_path = import_info['db_path']
                try:
                    # 이미 DBManager에 추가되었는지 확인
                    db_already_exists = False
                    for existing_name, existing_handler in self.db_manager.databases.items():
                        if existing_handler.db_file == db_path:
                            db_already_exists = True
                            logging.info(f"DB 이미 존재함: {existing_name} ({db_path})")
                            break

                    if not db_already_exists:
                        # DBManager에 추가 (기존 DB들과 함께 관리)
                        db_name = self.db_manager.add_database(db_path, replace_existing=False)
                        logging.info(f"DBManager에 추가됨: {db_name} ({db_path})")
                        added_count += 1
                        last_added_db_name = db_name  # 마지막 추가된 DB 기록

                except Exception as e:
                    logging.warning(f"DBManager 추가 실패: {db_path} - {e}")

            # 마지막으로 추가된 DB를 현재 활성 DB로 설정
            if last_added_db_name:
                self.db_manager.switch_database(last_added_db_name)
                logging.info(f"마지막 추가된 DB를 활성 DB로 설정: {last_added_db_name}")

            # 현재 DB 참조 업데이트
            self.update_current_db_references()

            # UI 새로고침 (모든 DB 표시)
            self.refresh_all_db_ui()

            logging.info(f"새로 추가된 DB: {added_count}개, 총 {self.db_manager.get_database_count()}개 DB가 관리 중")

        except Exception as e:
            logging.error(f"다중 DB 추가 중 오류: {e}")
            import traceback
            traceback.print_exc()

    def refresh_all_db_ui(self):
        """모든 DB를 UI에 표시하도록 새로고침"""
        try:
            # 파일 목록 새로고침 (모든 DB의 파일들 표시)
            self.load_files()

            # DB 드롭다운 업데이트 (중요: 이 부분이 누락되어 있었음)
            self.update_db_combo()

            # 상태바에 DB 개수 표시
            db_count = self.db_manager.get_database_count()
            if db_count > 1:
                self.statusBar.showMessage(f"다중 DB 관리 중: {db_count}개 데이터베이스")
            elif db_count == 1:
                current_db_name = self.db_manager.current_db_name
                self.statusBar.showMessage(f"현재 DB: {current_db_name}")
            else:
                self.statusBar.showMessage("DB가 열려있지 않음")

            logging.info(f"UI 새로고침 완료: {db_count}개 DB 표시")

        except Exception as e:
            logging.error(f"UI 새로고침 중 오류: {e}")
            import traceback
            traceback.print_exc()



    def show_multiple_import_result(self, successful_imports, failed_imports):
        """다중 Excel → DB 변환 결과 표시"""
        result_dialog = QDialog(self)
        result_dialog.setWindowTitle("다중 Excel → DB 변환 결과")
        result_dialog.setMinimumSize(500, 400)

        layout = QVBoxLayout(result_dialog)

        # 결과 요약
        summary_label = QLabel(f"총 {len(successful_imports + failed_imports)}개 파일 처리 완료")
        summary_label.setFont(QFont("", 10, QFont.Bold))
        layout.addWidget(summary_label)

        # 성공한 파일들
        if successful_imports:
            success_label = QLabel(f"성공: {len(successful_imports)}개")
            success_label.setStyleSheet("color: green; font-weight: bold;")
            layout.addWidget(success_label)

            success_text = QTextEdit()
            success_text.setMaximumHeight(150)
            success_content = ""
            for item in successful_imports:
                success_content += f"• {item['excel_file']} → {item['db_file']}\n"
            success_text.setPlainText(success_content)
            success_text.setReadOnly(True)
            layout.addWidget(success_text)

        # 실패한 파일들
        if failed_imports:
            fail_label = QLabel(f"실패: {len(failed_imports)}개")
            fail_label.setStyleSheet("color: red; font-weight: bold;")
            layout.addWidget(fail_label)

            fail_text = QTextEdit()
            fail_text.setMaximumHeight(150)
            fail_content = ""
            for item in failed_imports:
                fail_content += f"• {item['excel_file']}: {item['error']}\n"
            fail_text.setPlainText(fail_content)
            fail_text.setReadOnly(True)
            layout.addWidget(fail_text)

        # 확인 버튼
        from PySide6.QtWidgets import QPushButton, QHBoxLayout
        button_layout = QHBoxLayout()
        ok_button = QPushButton("확인")
        ok_button.clicked.connect(result_dialog.accept)
        button_layout.addStretch()
        button_layout.addWidget(ok_button)
        layout.addLayout(button_layout)

        # 상태바 업데이트
        if failed_imports:
            self.statusBar.showMessage(f"다중 변환 완료: 성공 {len(successful_imports)}개, 실패 {len(failed_imports)}개")
        else:
            self.statusBar.showMessage(f"다중 변환 완료: 모든 {len(successful_imports)}개 파일 성공")

        result_dialog.exec()

    def export_to_excel(self):
        """
        현재 선택된 파일을 Excel로 내보내기

        주의: 이 기능은 현재 임시로 비활성화되어 있습니다.
        메뉴에서 접근할 수 없지만 코드는 향후 재활성화를 위해 보존됩니다.
        """
        if self.current_file_id is None:
            QMessageBox.warning(self, "내보내기 경고", "내보낼 파일을 먼저 선택해주세요.")
            return

        # 현재 파일 이름 가져오기 (저장 대화상자 기본값으로 사용)
        current_file_name = "exported_excel" # 기본값
        try:
            files = self.db.get_files()
            current_file_name = next((f['name'] for f in files if f['id'] == self.current_file_id), current_file_name)
            # 확장자 제거
            current_file_name = os.path.splitext(current_file_name)[0]
        except Exception as e:
             logging.warning(f"현재 파일 이름 조회 중 오류 (내보내기용): {e}")


        try:
            # 파일 저장 대화상자
            default_path = f"{current_file_name}.xlsx"
            file_path, _ = QFileDialog.getSaveFileName(
                self, "Excel 파일로 저장", default_path, "Excel 파일 (*.xlsx)"
            )

            if not file_path:
                return # 사용자가 취소

            # 확장자 확인 및 추가 (.xlsx만 지원 가정)
            if not file_path.lower().endswith('.xlsx'):
                file_path += '.xlsx'

            logging.info(f"Attempting to export File ID {self.current_file_id} to: {file_path}")
            self.statusBar.showMessage("Excel 파일로 내보내는 중...")
            QApplication.processEvents()

            # Excel 파일로 내보내기 (exporter 사용)
            self.exporter.export_excel(self.current_file_id, file_path)

            self.statusBar.showMessage(f"Excel 파일 내보내기 완료: {file_path}")
            QMessageBox.information(self, "내보내기 완료", f"파일을 성공적으로 Excel 형식으로 저장했습니다.\n경로: {file_path}")

        except Exception as e:
            error_msg = f"Excel 파일 내보내기 중 오류 발생: {str(e)}"
            logging.error(f"{error_msg}\n{traceback.format_exc()}")
            QMessageBox.critical(self, "내보내기 오류", error_msg)
            self.statusBar.showMessage("Excel 파일 내보내기 실패")

    def save_current_sheet(self):
        """현재 그리드뷰의 변경 사항을 DB에 저장"""
        if self.current_sheet_id is None:
            # 시트가 선택되지 않았거나 로드되지 않은 상태
            # QMessageBox.warning(self, "저장 경고", "저장할 시트가 선택되지 않았습니다.")
            logging.debug("Save attempt ignored: No sheet selected.")
            return

        if not self.grid_view or not self.grid_view.model:
            QMessageBox.warning(self, "저장 오류", "그리드 뷰 또는 모델이 초기화되지 않았습니다.")
            return

        try:
            logging.info(f"Saving changes for Sheet ID: {self.current_sheet_id}")
            self.statusBar.showMessage("변경 사항 저장 중...")
            QApplication.processEvents()

            # 그리드뷰 모델의 save_changes 메서드 호출 (수정된 셀만 DB에 저장)
            self.grid_view.save_changes()

            self.statusBar.showMessage("변경 사항 저장 완료")
            logging.info(f"Changes saved successfully for Sheet ID: {self.current_sheet_id}")

        except Exception as e:
            error_msg = f"시트 저장 중 오류 발생: {str(e)}"
            logging.error(f"{error_msg} (Sheet ID: {self.current_sheet_id})\n{traceback.format_exc()}")
            QMessageBox.critical(self, "저장 오류", error_msg)
            self.statusBar.showMessage("변경 사항 저장 실패")

    def generate_code(self):
        """코드 생성 메서드 (다중 DB 지원 - 개선된 워크플로우)"""
        try:
            # 1. DB 선택 먼저 (다중 선택 지원)
            selected_dbs = self.select_databases_for_code_generation()
            if not selected_dbs:
                return  # 사용자가 취소하거나 DB가 없음

            # 2. 출력 디렉토리 선택 (한 번만)
            if len(selected_dbs) == 1:
                dialog_title = "코드 출력 디렉토리 선택"
            else:
                dialog_title = f"다중 DB 코드 출력 디렉토리 선택 ({len(selected_dbs)}개 DB)"

            output_dir = QFileDialog.getExistingDirectory(self, dialog_title, self.last_directory)
            if not output_dir:
                return  # 사용자가 취소

            # 출력 디렉토리 기억
            self.last_directory = output_dir
            self.settings.setValue(Info.LAST_DIRECTORY_KEY, output_dir)

            # 3. 코드 생성 실행 (통합 함수 사용)
            if len(selected_dbs) == 1:
                # 단일 DB 처리
                self.generate_code_for_single_db_unified(selected_dbs[0], output_dir)
            else:
                # 다중 DB 처리 (개선된 배치 처리)
                self.generate_code_for_multiple_dbs_unified(selected_dbs, output_dir)

        except Exception as e:
            error_msg = f"코드 생성 중 오류 발생: {str(e)}"
            logging.error(f"{error_msg}\n{traceback.format_exc()}")
            QMessageBox.critical(self, "코드 생성 오류", error_msg)
            self.statusBar.showMessage("코드 생성 중 심각한 오류 발생")

    def select_databases_for_code_generation(self) -> List['DBHandlerV2']:
        """코드 생성을 위한 데이터베이스들 선택"""
        db_count = self.db_manager.get_database_count()

        if db_count == 0:
            QMessageBox.warning(self, "코드 생성 경고", "열린 데이터베이스가 없습니다.\n먼저 DB 파일을 열어주세요.")
            return []
        elif db_count == 1:
            # 단일 DB면 자동 선택
            current_db = self.db_manager.get_current_db()
            db_name = self.db_manager.current_db_name
            logging.info(f"단일 DB 자동 선택: {db_name}")
            return [current_db] if current_db else []
        else:
            # 다중 DB면 사용자 선택 (체크박스 방식)
            return self.show_multiple_database_selection_dialog()

    def generate_code_for_single_db_unified(self, selected_db: 'DBHandlerV2', output_dir: str):
        """단일 DB에 대한 코드 생성 - 통합 함수 사용"""
        # 선택된 DB로 전환
        if self.db_manager.get_current_db() != selected_db:
            # 선택된 DB의 이름 찾기
            for db_name, db_handler in self.db_manager.databases.items():
                if db_handler == selected_db:
                    self.db_manager.switch_database(db_name)
                    self.update_current_db_references()
                    break

        try:
            # 진행률 대화상자 생성
            from PySide6.QtWidgets import QProgressDialog
            db_name = os.path.basename(selected_db.db_file)
            progress = QProgressDialog(f"코드 생성 중: {db_name}", "취소", 0, 100, self)
            progress.setWindowModality(Qt.WindowModal)
            progress.setMinimumDuration(0)
            progress.setAutoClose(False)
            progress.setAutoReset(False)
            progress.show()
            progress.setValue(0)

            # 초기 메시지 표시
            progress.setLabelText("코드 생성 준비 중...")
            QApplication.processEvents()

            # 1. 현재 편집 중인 시트 저장 확인
            if self.current_sheet_id is not None:
                progress.setValue(5)
                progress.setLabelText("변경 사항 저장 확인 중...")
                QApplication.processEvents()

                reply = QMessageBox.question(self, "저장 확인",
                                             "코드 생성 전에 현재 시트의 변경 사항을 저장하시겠습니까?",
                                             QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel,
                                             QMessageBox.Save)
                if reply == QMessageBox.Save:
                    self.save_current_sheet()
                elif reply == QMessageBox.Cancel:
                    progress.close()
                    return

            # 2. 출력 디렉토리 설정
            if not output_dir:
                progress.setValue(10)
                progress.setLabelText("출력 디렉토리 선택 중...")
                QApplication.processEvents()

                output_dir = QFileDialog.getExistingDirectory(self, "코드 저장 폴더 선택", "")
                if not output_dir:
                    progress.close()
                    return

            # DB명 폴더 생성 (다중 DB와 동일한 구조)
            db_output_dir = os.path.join(output_dir, os.path.splitext(db_name)[0])
            os.makedirs(db_output_dir, exist_ok=True)
            logging.info(f"단일 DB 출력 디렉토리 생성: {db_output_dir}")

            # 통합 코드 생성 함수 호출
            result_message, generated_files_info = self.generate_code_unified(
                selected_db, db_output_dir, progress, show_result=True, return_file_info=True
            )

            # 상태바 업데이트
            if "완료" in result_message:
                self.statusBar.showMessage(f"코드 생성 완료: {len(generated_files_info)}개 파일 생성")
            else:
                self.statusBar.showMessage("코드 생성 중 오류 발생")

            progress.close()

        except InterruptedError as e:
            logging.info(f"사용자가 코드 생성을 취소했습니다: {str(e)}")
            if 'progress' in locals():
                progress.close()
            QMessageBox.information(self, "코드 생성 취소", "코드 생성이 취소되었습니다.")
        except Exception as e:
            error_msg = f"코드 생성 과정 중 예기치 않은 오류 발생: {str(e)}"
            logging.critical(f"{error_msg}\n{traceback.format_exc()}")
            if 'progress' in locals():
                progress.close()
            QMessageBox.critical(self, "코드 생성 오류", error_msg)
            self.statusBar.showMessage("코드 생성 중 심각한 오류 발생")

    def generate_code_for_single_db(self, selected_db: 'DBHandlerV2', output_dir: str):
        """기존 호환성을 위한 래퍼 함수 - 통합 함수로 리다이렉트"""
        return self.generate_code_for_single_db_unified(selected_db, output_dir)

        # 이 부분은 이제 통합 함수에서 처리되므로 제거됨

    def generate_code_for_multiple_dbs_unified(self, selected_dbs: List['DBHandlerV2'], output_dir: str):
        """통합된 다중 DB 코드 생성 함수"""
        import time

        try:
            logging.info(f"=== 통합 다중 DB 코드 생성 시작: {len(selected_dbs)}개 DB ===")
            start_time = time.time()

            # 진행률 대화상자 생성
            from PySide6.QtWidgets import QProgressDialog
            progress = QProgressDialog(f"다중 DB 코드 생성 중... (0/{len(selected_dbs)})", "취소", 0, len(selected_dbs), self)
            progress.setWindowModality(Qt.WindowModal)
            progress.setMinimumDuration(0)
            progress.show()

            successful_generations = []
            failed_generations = []

            for i, db_handler in enumerate(selected_dbs):
                if progress.wasCanceled():
                    logging.info("사용자가 다중 DB 코드 생성을 취소했습니다.")
                    break

                db_name = os.path.basename(db_handler.db_file)
                progress.setLabelText(f"코드 생성 중: {db_name} ({i+1}/{len(selected_dbs)})")
                progress.setValue(i)
                QApplication.processEvents()

                # 타임아웃 체크
                elapsed_time = time.time() - start_time
                if elapsed_time > CodeGenerationConstants.MULTI_DB_TIMEOUT:
                    logging.warning(f"다중 DB 코드 생성 타임아웃: {elapsed_time:.1f}초 경과")
                    failed_generations.append({
                        'db_name': db_name,
                        'error': f'전체 처리 시간 초과 ({CodeGenerationConstants.MULTI_DB_TIMEOUT}초 제한)',
                        'output_dir': 'N/A'
                    })
                    break

                try:
                    # 각 DB별 출력 디렉토리 생성
                    db_output_dir = os.path.join(output_dir, os.path.splitext(db_name)[0])
                    os.makedirs(db_output_dir, exist_ok=True)

                    # $ 시트 확인
                    sheets = db_handler.get_sheets()
                    dollar_sheets = [s for s in sheets if s.get('is_dollar_sheet', False)]

                    if not dollar_sheets:
                        failed_generations.append({
                            'db_name': db_name,
                            'error': '코드 생성할 $ 시트가 없음',
                            'output_dir': db_output_dir
                        })
                        logging.warning(f"DB '{db_name}': $ 시트가 없어 코드 생성 건너뜀")
                        continue

                    logging.info(f"다중 DB 코드 생성 [{i+1}/{len(selected_dbs)}]: {db_name} ({len(dollar_sheets)}개 $ 시트)")

                    # 통합 코드 생성 함수 호출 (결과창 표시 안함)
                    result_message, generated_files_info = self.generate_code_unified(
                        db_handler, db_output_dir, progress_dialog=None,
                        show_result=False, return_file_info=True
                    )

                    logging.info(f"코드 생성 완료: 결과 메시지 길이 {len(result_message)}, 파일 정보 {len(generated_files_info)}개")

                    # 생성된 파일 정보 처리
                    generated_files = []
                    for file_info in generated_files_info:
                        src_file = file_info.get('src_file')
                        hdr_file = file_info.get('hdr_file')

                        if src_file:
                            src_path = file_info.get('src_path')
                            if src_path and os.path.exists(src_path):
                                generated_files.append({
                                    'name': src_file,
                                    'size': os.path.getsize(src_path),
                                    'type': 'C 소스'
                                })

                        if hdr_file:
                            hdr_path = file_info.get('hdr_path')
                            if hdr_path and os.path.exists(hdr_path):
                                generated_files.append({
                                    'name': hdr_file,
                                    'size': os.path.getsize(hdr_path),
                                    'type': 'C 헤더'
                                })

                    logging.info(f"최종 생성된 파일 목록: {len(generated_files)}개 - {[f['name'] for f in generated_files]}")

                    # 실제 파일 생성 여부로 성공/실패 판정
                    if generated_files:
                        successful_generations.append({
                            'db_name': db_name,
                            'output_dir': db_output_dir,
                            'result': result_message,
                            'generated_files': generated_files,
                            'file_count': len(generated_files)
                        })
                        logging.info(f"✅ 다중 DB 코드 생성 성공: {db_name} ({len(generated_files)}개 파일)")
                    else:
                        # 파일이 생성되지 않았으면 실패로 처리
                        failed_generations.append({
                            'db_name': db_name,
                            'error': f'파일 생성 실패: 생성된 파일이 없습니다.\n결과: {result_message}',
                            'output_dir': db_output_dir
                        })
                        logging.warning(f"⚠️ 다중 DB 코드 생성 실패: {db_name} (생성된 파일 없음)")

                except InterruptedError as e:
                    logging.info(f"DB '{db_name}' 코드 생성 취소: {str(e)}")
                    failed_generations.append({
                        'db_name': db_name,
                        'error': f'사용자 취소: {str(e)}',
                        'output_dir': db_output_dir if 'db_output_dir' in locals() else 'N/A'
                    })
                    break  # 취소 시 전체 중단
                except TimeoutError as e:
                    logging.warning(f"DB '{db_name}' 코드 생성 타임아웃: {str(e)}")
                    failed_generations.append({
                        'db_name': db_name,
                        'error': f'타임아웃: {str(e)}',
                        'output_dir': db_output_dir if 'db_output_dir' in locals() else 'N/A'
                    })
                except Exception as e:
                    error_msg = str(e)
                    failed_generations.append({
                        'db_name': db_name,
                        'error': error_msg,
                        'output_dir': db_output_dir if 'db_output_dir' in locals() else 'N/A'
                    })
                    logging.error(f"❌ 다중 DB 코드 생성 실패 [{db_name}]: {error_msg}")

            progress.setValue(len(selected_dbs))
            progress.close()

            # 배치 처리 완료 - 통합 결과 표시
            total_time = time.time() - start_time
            logging.info(f"다중 DB 코드 생성 완료 (총 소요시간: {total_time:.1f}초)")
            self.show_multiple_code_generation_result_improved(successful_generations, failed_generations, output_dir)

        except InterruptedError as e:
            logging.info(f"다중 DB 코드 생성 취소: {str(e)}")
            if 'progress' in locals():
                progress.close()
            QMessageBox.information(self, "다중 코드 생성 취소", "다중 DB 코드 생성이 취소되었습니다.")
        except MemoryError as e:
            logging.error(f"다중 DB 코드 생성 메모리 부족: {str(e)}")
            if 'progress' in locals():
                progress.close()
            QMessageBox.critical(self, "메모리 부족",
                               f"다중 DB 코드 생성 중 메모리 사용량이 한계를 초과했습니다.\n\n{str(e)}\n\n"
                               "더 적은 수의 DB를 선택하거나 시스템 메모리를 늘려주세요.")
        except Exception as e:
            error_msg = f"다중 DB 코드 생성 중 오류: {str(e)}"
            logging.error(f"{error_msg}\n{traceback.format_exc()}")
            if 'progress' in locals():
                progress.close()
            QMessageBox.critical(self, "다중 코드 생성 오류", error_msg)
        finally:
            # 진행률 대화상자가 열려있다면 닫기
            if 'progress' in locals() and progress.isVisible():
                progress.close()

    def generate_code_for_multiple_dbs_improved(self, selected_dbs: List['DBHandlerV2'], output_dir: str):
        """기존 호환성을 위한 래퍼 함수 - 통합 함수로 리다이렉트"""
        return self.generate_code_for_multiple_dbs_unified(selected_dbs, output_dir)

    def generate_code_unified(self, db_handler: 'DBHandlerV2', output_dir: str,
                             progress_dialog=None, show_result: bool = True,
                             return_file_info: bool = False) -> tuple[str, list]:
        """
        통합된 코드 생성 함수 - 모든 코드 생성 요구사항을 처리

        Args:
            db_handler: 데이터베이스 핸들러
            output_dir: 출력 디렉토리
            progress_dialog: 진행률 대화상자 (선택사항)
            show_result: 결과창 표시 여부
            return_file_info: 파일 정보 반환 여부

        Returns:
            tuple[str, list]: (결과 메시지, 생성된 파일 정보 리스트)
        """
        try:
            db_name = os.path.basename(db_handler.db_file)
            logging.info(f"=== 통합 코드 생성 시작: {db_name} ===")

            # 진행률 콜백 함수 정의
            def progress_callback(progress_val: int, message: str):
                if progress_dialog:
                    progress_dialog.setValue(progress_val)
                    progress_dialog.setLabelText(message)
                    QApplication.processEvents()

                    if progress_dialog.wasCanceled():
                        raise InterruptedError("사용자가 코드 생성을 취소했습니다.")

            if progress_dialog:
                progress_callback(10, "시트 분류 중...")

            # 1. 시트 그룹별 분류 (헬퍼 함수 사용)
            d_xls = CodeGenerationHelper.classify_sheets_by_group(db_handler)

            if not d_xls:
                return "코드 생성할 $ 시트가 없습니다.", []

            if progress_dialog:
                progress_callback(30, f"코드 생성 시작... ({len(d_xls)}개 그룹)")

            # 2. 각 그룹별 코드 생성
            result_message = f"코드 생성 결과 ({db_name}):\n\n"
            generated_files_info = []
            has_errors = False

            for group_idx, (group_name, group_data) in enumerate(d_xls.items()):
                # 진행률 업데이트
                if progress_dialog:
                    progress_val = 30 + int((group_idx / len(d_xls)) * 60)  # 30-90% 범위
                    progress_callback(progress_val, f"'{group_name}' 그룹 처리 중 ({group_idx+1}/{len(d_xls)})")

                # 그룹 검증
                if not group_data['FileInfoSht'] or not group_data['CalListSht']:
                    result_message += f"❌ 그룹 '{group_name}': FileInfo 또는 CalList 시트 누락\n\n"
                    has_errors = True
                    continue

                try:
                    # 전역 상태 초기화
                    CodeGenerationHelper.initialize_global_state()

                    # 임시 위젯 생성
                    from PySide6.QtWidgets import QListWidget
                    lb_src = QListWidget()
                    lb_hdr = QListWidget()

                    # 그룹별 서로게이트 객체 생성
                    group_surrogate = OriginalFileSurrogate(db_handler)
                    group_surrogate.FileInfoSht = group_data['FileInfoSht']
                    group_surrogate.CalListSht = group_data['CalListSht']

                    # MakeCode 객체 생성
                    make_code = MakeCode(group_surrogate, lb_src, lb_hdr)

                    # 시트 정보 검증
                    if make_code.ChkShtInfo():
                        error_msgs = "\n".join(Info.ErrList) if Info.ErrList else "알 수 없는 검증 오류"
                        result_message += f"❌ 그룹 '{group_name}' 정보 검증 오류:\n{error_msgs}\n\n"
                        has_errors = True
                        Info.ErrList = []
                        continue

                    # 파일명 결정
                    base_name = CodeGenerationHelper.get_base_filename_from_fileinfo(
                        group_data['FileInfoSht'], group_name
                    )
                    target_file_name = f"{base_name}{CodeGenerationConstants.C_SOURCE_EXT}"

                    # 코드 읽기 및 변환
                    make_code.ReadXlstoCode()
                    make_code.ConvXlstoCode(db_name, target_file_name)

                    # 변환 중 오류 확인
                    if Info.ErrList:
                        error_msgs = "\n".join(Info.ErrList)
                        result_message += f"❌ 그룹 '{group_name}' 코드 변환 중 오류:\n{error_msgs}\n\n"
                        has_errors = True
                        Info.ErrList = []
                        continue

                    # 파일 저장
                    src_filename = f"{base_name}{CodeGenerationConstants.C_SOURCE_EXT}"
                    hdr_filename = f"{base_name}{CodeGenerationConstants.C_HEADER_EXT}"

                    src_file_path = os.path.join(output_dir, src_filename)
                    hdr_file_path = os.path.join(output_dir, hdr_filename)

                    # 소스 파일 저장
                    with open(src_file_path, 'w', encoding='utf-8') as f_src:
                        for i in range(lb_src.count()):
                            f_src.write(lb_src.item(i).text() + '\n')

                    # 헤더 파일 저장
                    with open(hdr_file_path, 'w', encoding='utf-8') as f_hdr:
                        for i in range(lb_hdr.count()):
                            f_hdr.write(lb_hdr.item(i).text() + '\n')

                    # 성공 메시지 및 파일 정보 기록
                    result_message += f"✅ 그룹 '{group_name}' 코드 생성 완료:\n"
                    result_message += f"   - 소스 파일: {src_filename}\n"
                    result_message += f"   - 헤더 파일: {hdr_filename}\n\n"

                    if return_file_info:
                        generated_files_info.append({
                            "group": group_name,
                            "src_file": src_filename,
                            "hdr_file": hdr_filename,
                            "src_path": src_file_path,
                            "hdr_path": hdr_file_path
                        })

                    logging.info(f"코드 생성 성공: 그룹 '{group_name}' - {src_filename}, {hdr_filename}")

                except Exception as group_error:
                    error_msg = f"그룹 '{group_name}' 처리 중 예외 발생: {str(group_error)}"
                    result_message += f"❌ {error_msg}\n\n"
                    logging.error(f"{error_msg}\n{traceback.format_exc()}")
                    has_errors = True
                finally:
                    # 리소스 정리
                    if 'make_code' in locals() and hasattr(make_code, 'reset_for_new_file'):
                        make_code.reset_for_new_file()
                    if 'lb_src' in locals():
                        del lb_src
                    if 'lb_hdr' in locals():
                        del lb_hdr
                    if 'group_surrogate' in locals():
                        del group_surrogate
                    if 'make_code' in locals():
                        del make_code

            # 최종 결과 처리
            if progress_dialog:
                progress_callback(95, "결과 정리 중...")

            if has_errors:
                final_msg = f"코드 생성 완료 (일부 오류 발생): {len(d_xls)}개 그룹 중 일부에서 오류"
            else:
                final_msg = f"코드 생성 완료: 모든 {len(d_xls)}개 그룹 성공"

            result_message += final_msg
            logging.info(f"통합 코드 생성 완료: {final_msg}")

            if progress_dialog:
                progress_callback(100, f"완료 - {len(generated_files_info)}개 파일 생성됨")

            # 결과창 표시 (옵션)
            if show_result:
                self.show_code_generation_result(result_message, output_dir, generated_files_info)

            return result_message, generated_files_info

        except InterruptedError as e:
            logging.info(f"코드 생성 취소: {str(e)}")
            return f"코드 생성 취소: {str(e)}", []
        except Exception as e:
            error_msg = f"통합 코드 생성 중 오류: {str(e)}"
            logging.error(f"{error_msg}\n{traceback.format_exc()}")
            return f"코드 생성 실패: {error_msg}", []

    def generate_code_for_single_db_real(self, db_handler: 'DBHandlerV2', output_dir: str, progress_dialog=None) -> str:
        """기존 호환성을 위한 래퍼 함수 - 통합 함수로 리다이렉트"""
        result_message, _ = self.generate_code_unified(
            db_handler, output_dir, progress_dialog, show_result=False, return_file_info=False
        )
        return result_message

    def generate_code_for_single_db_copy(self, db_handler: 'DBHandlerV2', output_dir: str) -> str:
        """기존 호환성을 위한 래퍼 함수 - 통합 함수로 리다이렉트"""
        result_message, _ = self.generate_code_unified(
            db_handler, output_dir, progress_dialog=None, show_result=False, return_file_info=False
        )
        return result_message

        # 이 부분은 이제 통합 함수에서 처리되므로 제거됨

    def generate_code_for_single_db_copy_with_tracking(self, db_handler: 'DBHandlerV2', output_dir: str) -> tuple[str, list]:
        """기존 호환성을 위한 래퍼 함수 - 통합 함수로 리다이렉트 (파일 추적 포함)"""
        return self.generate_code_unified(
            db_handler, output_dir, progress_dialog=None, show_result=False, return_file_info=True
        )

        # 이 부분은 이제 통합 함수에서 처리되므로 제거됨

    def call_single_db_function_directly(self, db_handler: 'DBHandlerV2', output_dir: str) -> str:
        """단일 DB 함수를 직접 호출 (가장 간단한 방법)"""
        try:
            db_name = os.path.basename(db_handler.db_file)
            logging.info(f"=== 단일 DB 함수 직접 호출: {db_name} ===")

            # 현재 DB를 임시로 전환
            original_db = self.db_manager.get_current_db()
            original_db_name = self.db_manager.current_db_name

            # 대상 DB로 전환
            target_db_name = None
            for name, handler in self.db_manager.databases.items():
                if handler == db_handler:
                    target_db_name = name
                    break

            if not target_db_name:
                return "DB를 찾을 수 없습니다."

            # DB 전환
            self.db_manager.switch_database(target_db_name)
            self.update_current_db_references()

            # 단일 DB 코드 생성 함수 직접 호출 (출력 디렉토리 전달, 결과창 표시 안함)
            self.generate_code_for_single_db_silent(db_handler, output_dir)

            # 원래 DB로 복원
            if original_db_name:
                self.db_manager.switch_database(original_db_name)
                self.update_current_db_references()

            return f"DB '{db_name}' 코드 생성 완료"

        except Exception as e:
            error_msg = f"단일 DB 함수 직접 호출 중 오류: {str(e)}"
            logging.error(f"{error_msg}\n{traceback.format_exc()}")
            return f"코드 생성 실패: {error_msg}"

    def generate_code_for_single_db_silent(self, selected_db: 'DBHandlerV2', output_dir: str):
        """기존 호환성을 위한 래퍼 함수 - 통합 함수로 리다이렉트 (결과창 표시 안함)"""
        # 선택된 DB로 전환
        if self.db_manager.get_current_db() != selected_db:
            # 선택된 DB의 이름 찾기
            for db_name, db_handler in self.db_manager.databases.items():
                if db_handler == selected_db:
                    self.db_manager.switch_database(db_name)
                    self.update_current_db_references()
                    break

        # 통합 함수 호출 (결과창 표시 안함)
        result_message, _ = self.generate_code_unified(
            selected_db, output_dir, progress_dialog=None, show_result=False, return_file_info=False
        )

        logging.info(f"Silent code generation completed for DB: {os.path.basename(selected_db.db_file)}")
        return result_message

    def show_file_selection_dialog_for_db(self, db_handler: 'DBHandlerV2') -> Optional[int]:
        """특정 DB에 대한 파일 선택 대화상자 (V2 구조에서는 사용하지 않음)"""
        # V2 구조에서는 파일 개념이 없으므로 더미 값 반환
        # 실제로는 시트 기반으로 코드 생성이 이루어짐
        logging.info(f"V2 구조에서는 파일 선택이 필요하지 않음: {os.path.basename(db_handler.db_file)}")
        return 1  # 더미 파일 ID

    def show_multiple_code_generation_result_improved(self, successful_generations, failed_generations, output_dir):
        """개선된 다중 DB 코드 생성 결과 표시 (깔끔한 단일 DB 스타일)"""
        from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                                       QPushButton, QTextEdit)
        from PySide6.QtGui import QFont
        from PySide6.QtCore import Qt

        # 결과 대화상자 생성
        result_dialog = QDialog(self)
        result_dialog.setWindowTitle("다중 DB 코드 생성 결과")
        result_dialog.setMinimumSize(600, 500)
        result_dialog.setModal(True)

        main_layout = QVBoxLayout(result_dialog)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 20, 20, 20)

        # 제목 라벨
        title_label = QLabel("다중 DB 코드 생성 완료")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title_label)

        # 요약 정보
        total_dbs = len(successful_generations) + len(failed_generations)
        success_count = len(successful_generations)
        fail_count = len(failed_generations)

        summary_label = QLabel(f"총 {total_dbs}개 DB 처리 완료 (성공: {success_count}개, 실패: {fail_count}개)")
        summary_label.setAlignment(Qt.AlignCenter)
        summary_label.setStyleSheet("color: #666; font-size: 12px; margin: 10px;")
        main_layout.addWidget(summary_label)

        # 결과 텍스트 영역 (단일 DB 스타일과 동일)
        result_text = QTextEdit()
        result_text.setReadOnly(True)
        result_text.setFont(QFont("Consolas", 9))

        # 결과 텍스트 생성
        result_content = []

        # 성공한 DB들 (헤더 없이 바로 표시)
        if successful_generations:
            for gen_info in successful_generations:
                db_name = gen_info['db_name']
                generated_files = gen_info.get('generated_files', [])
                output_path = gen_info['output_dir']

                # DB명과 저장 위치를 함께 표시 (출처 정보 포함)
                result_content.append(f"📂 저장 위치: {os.path.basename(output_path)} (출처: {db_name})")

                if generated_files:
                    result_content.append("   생성된 파일:")
                    for file_info in generated_files:
                        file_name = file_info['name']
                        file_size = file_info['size']

                        # 파일 크기 포맷
                        if file_size < 1024:
                            size_str = f"{file_size} bytes"
                        elif file_size < 1024 * 1024:
                            size_str = f"{file_size / 1024:.1f} KB"
                        else:
                            size_str = f"{file_size / (1024 * 1024):.1f} MB"

                        file_icon = "📄" if file_name.endswith('.c') else "📋"
                        result_content.append(f"   {file_icon} {file_name} ({size_str})")
                else:
                    result_content.append("   생성된 파일 없음")

                result_content.append("")

        # 실패한 DB들 (헤더 없이 바로 표시)
        if failed_generations:
            # 성공한 DB와 실패한 DB 사이에 구분선 추가
            if successful_generations:
                result_content.append("=" * 50)
                result_content.append("")

            for fail_info in failed_generations:
                db_name = fail_info['db_name']
                error_msg = fail_info['error']
                output_path = fail_info.get('output_dir', 'N/A')

                # 실패한 DB 정보 표시
                if output_path != 'N/A':
                    result_content.append(f"❌ 실패: {os.path.basename(output_path)} (출처: {db_name})")
                else:
                    result_content.append(f"❌ 실패: {db_name}")
                result_content.append(f"   오류: {error_msg}")
                result_content.append("")

        result_text.setPlainText("\n".join(result_content))
        main_layout.addWidget(result_text)

        # 버튼 영역
        button_layout = QHBoxLayout()

        # 폴더 열기 버튼 (상위 디렉토리 열기)
        open_folder_btn = QPushButton("📂 출력 폴더 열기")
        open_folder_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        open_folder_btn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(output_dir)))
        button_layout.addWidget(open_folder_btn)

        button_layout.addStretch()

        # 확인 버튼
        ok_btn = QPushButton("확인")
        ok_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        ok_btn.clicked.connect(result_dialog.accept)
        button_layout.addWidget(ok_btn)

        main_layout.addLayout(button_layout)

        # 상태바 메시지 업데이트
        if fail_count == 0:
            self.statusBar.showMessage(f"다중 DB 코드 생성 완료: {success_count}개 성공")
        else:
            self.statusBar.showMessage(f"다중 DB 코드 생성 완료: {success_count}개 성공, {fail_count}개 실패")

        # 대화상자 표시
        result_dialog.exec()

    def show_multiple_code_generation_result(self, successful_generations, failed_generations, output_dir):
        """기존 호환성을 위한 래퍼 함수 - 개선된 함수로 리다이렉트"""
        return self.show_multiple_code_generation_result_improved(successful_generations, failed_generations, output_dir)

    def show_code_generation_result(self, result_message: str, output_dir: str, generated_files_info: List[Dict[str, str]]):
        """
        코드 생성 결과를 보여주는 상세 대화 상자

        Args:
            result_message: 생성 과정 및 결과를 담은 문자열
            output_dir: 코드가 저장된 디렉토리 경로
            generated_files_info: 생성된 파일 정보 리스트 (딕셔너리 형태)
        """
        # 커스텀 대화 상자 생성
        dialog = QDialog(self)
        dialog.setWindowTitle("코드 생성 결과")
        dialog.setMinimumSize(700, 500) # 최소 크기 설정
        dialog.setStyleSheet("""
            QDialog { background-color: #f8f9fa; }
            QLabel#TitleLabel { font-size: 16pt; font-weight: bold; color: #343a40; }
            QLabel#PathLabel { font-size: 10pt; color: #495057; }
            QPushButton#OpenDirButton {
                background-color: #007bff; color: white; border: none;
                padding: 5px 10px; border-radius: 4px; font-size: 9pt;
            }
            QPushButton#OpenDirButton:hover { background-color: #0056b3; }
            QPushButton#CloseButton {
                background-color: #6c757d; color: white; border: none;
                padding: 8px 16px; border-radius: 4px; font-size: 10pt;
            }
            QPushButton#CloseButton:hover { background-color: #5a6268; }
            QTextEdit {
                background-color: white; border: 1px solid #ced4da;
                border-radius: 4px; font-family: Consolas, monospace; /* 고정폭 폰트 */
                font-size: 9pt;
            }
        """)

        # 메인 레이아웃
        main_layout = QVBoxLayout(dialog)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        # 제목 레이블
        title_label = QLabel("코드 생성 결과")
        title_label.setObjectName("TitleLabel")
        title_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title_label)

        # 경로 정보 및 폴더 열기 버튼
        path_layout = QHBoxLayout()
        path_label = QLabel(f"<b>저장 위치:</b> <a href='file:///{output_dir}'>{output_dir}</a>")
        path_label.setObjectName("PathLabel")
        path_label.setTextInteractionFlags(Qt.TextBrowserInteraction) # 링크 클릭 가능
        path_label.setOpenExternalLinks(True) # 시스템 파일 탐색기로 열기
        path_layout.addWidget(path_label, 1) # Stretch factor 1

        open_dir_button = QPushButton(QIcon.fromTheme("folder"), "폴더 열기")
        open_dir_button.setObjectName("OpenDirButton")
        open_dir_button.setToolTip("생성된 코드가 있는 폴더를 엽니다.")
        open_dir_button.clicked.connect(lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(output_dir)))
        path_layout.addWidget(open_dir_button)

        main_layout.addLayout(path_layout)

        # 상세 결과 메시지 (스크롤 가능)
        results_text = QTextEdit()
        results_text.setReadOnly(True)
        results_text.setText(result_message)
        main_layout.addWidget(results_text, 1) # Stretch factor 1

        # 닫기 버튼
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch() # 버튼을 오른쪽으로 밀기
        close_button = QPushButton("닫기")
        close_button.setObjectName("CloseButton")
        close_button.clicked.connect(dialog.accept)
        buttons_layout.addWidget(close_button)
        main_layout.addLayout(buttons_layout)

        # 대화 상자 표시 (모달)
        dialog.exec()

    def closeEvent(self, event):
        """애플리케이션 종료 이벤트 처리"""
        logging.info("Close event triggered.")
        # 현재 작업 저장 여부 확인 (선택사항)
        # if self.grid_view and self.grid_view.model and self.grid_view.model.modified_cells:
        #     reply = QMessageBox.question(self, "종료 확인",
        #                                  "저장하지 않은 변경 사항이 있습니다. 저장하시겠습니까?",
        #                                  QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel,
        #                                  QMessageBox.Cancel)
        #     if reply == QMessageBox.Save:
        #         self.save_current_sheet()
        #     elif reply == QMessageBox.Cancel:
        #         event.ignore() # 종료 취소
        #         return

        # cleanup 메서드가 aboutToQuit 시그널에 연결되어 DB 연결 해제 등을 처리하므로
        # 여기서는 특별한 작업 없이 종료 허용
        event.accept()

    @Slot()
    def cleanup(self):
        """애플리케이션 종료 시 정리 작업 (다중 DB 상태 저장 및 DB 연결 해제)"""
        logging.info("=== 애플리케이션 정리 작업 시작 ===")

        try:
            # 1. 개별 DB 핸들러 연결 해제 (안전 조치)
            if hasattr(self, 'db') and self.db:
                try:
                    logging.info("개별 DB 핸들러 연결 해제 중...")
                    self.db.disconnect()
                    self.db = None
                    logging.info("개별 DB 핸들러 연결 해제 완료")
                except Exception as e:
                    logging.error(f"개별 DB 핸들러 해제 오류: {e}")

            # 2. DBManager를 통한 모든 DB 연결 해제
            if hasattr(self, 'db_manager') and self.db_manager:
                try:
                    db_count = self.db_manager.get_database_count()
                    logging.info(f"DBManager 정리 시작 - 현재 {db_count}개 DB 연결")



                    # 모든 DB 연결 해제
                    logging.info("모든 DB 연결 해제 중...")
                    self.db_manager.disconnect_all()

                    # 연결 해제 확인
                    remaining_count = self.db_manager.get_database_count()
                    if remaining_count == 0:
                        logging.info("✅ 모든 DB 연결이 성공적으로 해제되었습니다.")
                    else:
                        logging.warning(f"⚠️ {remaining_count}개 DB 연결이 남아있습니다.")

                    # DBManager 객체 정리
                    self.db_manager = None

                except Exception as e:
                    logging.error(f"DBManager 정리 중 오류: {e}")

            # 3. 기타 객체들 정리
            cleanup_objects = [
                ('importer', 'Excel 가져오기 객체'),
                ('exporter', 'Excel 내보내기 객체'),
                ('data_parser', '데이터 파서 객체'),
                ('file_surrogate', '파일 대체 객체'),
                ('original_surrogate', '원본 파일 대체 객체')
            ]

            for attr_name, description in cleanup_objects:
                if hasattr(self, attr_name):
                    try:
                        obj = getattr(self, attr_name)
                        if obj and hasattr(obj, 'disconnect'):
                            obj.disconnect()
                        setattr(self, attr_name, None)
                        logging.debug(f"{description} 정리 완료")
                    except Exception as e:
                        logging.error(f"{description} 정리 중 오류: {e}")

            # 4. 강제 가비지 컬렉션
            import gc
            gc.collect()
            logging.info("가비지 컬렉션 실행 완료")

        except Exception as e:
            logging.error(f"정리 작업 중 예상치 못한 오류: {e}")
            import traceback
            logging.error(traceback.format_exc())

        finally:
            logging.info("=== 애플리케이션 정리 작업 완료 ===")

            # 로그 핸들러도 정리 (선택사항)
            try:
                for handler in logging.getLogger().handlers[:]:
                    handler.close()
                    logging.getLogger().removeHandler(handler)
            except:
                pass  # 로그 정리 실패는 무시


    @Slot(int)
    def on_add_sheet(self, file_id: int):
        """
        새 시트 추가 처리 (TreeView의 add_sheet 시그널에 연결된 슬롯)

        Args:
            file_id: 시트를 추가할 파일 ID
        """
        try:
            # 현재 파일의 시트 목록 가져오기 (새 시트 이름 기본값 생성용)
            existing_sheets = self.db.get_sheets(file_id)
            default_sheet_name = f"Sheet{len(existing_sheets) + 1}"

            # 새 시트 이름 입력 대화상자
            sheet_name, ok = QInputDialog.getText(
                self, '새 시트 추가', '새 시트 이름을 입력하세요:',
                QLineEdit.Normal, default_sheet_name
            )

            if ok and sheet_name:
                sheet_name = sheet_name.strip()
                if not sheet_name:
                    QMessageBox.warning(self, "이름 오류", "시트 이름은 비워둘 수 없습니다.")
                    return

                # 중복 이름 확인 (선택사항)
                if any(s['name'] == sheet_name for s in existing_sheets):
                     QMessageBox.warning(self, "이름 중복", f"같은 파일 내에 '{sheet_name}' 시트가 이미 존재합니다.")
                     return

                # 달러 표시 포함 여부 확인
                is_dollar_sheet = "$" in sheet_name

                # 시트 순서 결정 (마지막 순서)
                sheet_order = len(existing_sheets)

                logging.info(f"Adding new sheet to File ID {file_id}: Name='{sheet_name}', IsDollar={is_dollar_sheet}, Order={sheet_order}")

                # DB에 새 시트 추가
                sheet_id = self.db.create_sheet(file_id, sheet_name, is_dollar_sheet, sheet_order)

                # 시트 목록 새로고침 (트리뷰 업데이트)
                self.load_sheets(file_id)

                # 새로 추가된 시트 선택 (선택사항)
                # self.select_item_in_tree(sheet_id=sheet_id) # 예시 함수

                self.statusBar.showMessage(f"시트 '{sheet_name}' 추가 완료")
            else:
                logging.debug("Add sheet cancelled by user.")

        except Exception as e:
            error_msg = f"시트 추가 중 오류 발생: {str(e)}"
            logging.error(f"{error_msg} (File ID: {file_id})\n{traceback.format_exc()}")
            QMessageBox.critical(self, "시트 추가 오류", error_msg)
            self.statusBar.showMessage("시트 추가 실패")

    @Slot(int, str)
    def on_file_renamed(self, file_id: int, new_name: str):
        """
        파일 이름 변경 처리 (TreeViewModel의 file_renamed 시그널에 연결된 슬롯)

        Args:
            file_id: 파일 ID
            new_name: 새 파일 이름
        """
        try:
            logging.info(f"Attempting to rename file ID {file_id} to '{new_name}' in DB.")
            # DB에 파일 이름 업데이트
            self.db.rename_file(file_id, new_name)

            # 상태바 메시지 업데이트
            self.statusBar.showMessage(f"파일 이름이 '{new_name}'으로 변경되었습니다.")
            logging.info(f"File ID {file_id} successfully renamed to '{new_name}'.")

            # 트리뷰는 모델 변경 시 자동으로 업데이트되므로 별도 조치 필요 없음
            # 만약 DB 업데이트 실패 시 롤백이 필요하다면 여기서 처리
            # self.load_files() # 오류 시 강제 새로고침 (최후의 수단)

        except Exception as e:
            error_msg = f"파일 이름 변경 중 DB 오류 발생: {str(e)}"
            logging.error(f"{error_msg} (File ID: {file_id}, New Name: '{new_name}')\n{traceback.format_exc()}")
            QMessageBox.critical(self, "파일 이름 변경 오류", f"{error_msg}\n\n파일 목록을 새로고침합니다.")
            # 오류 발생 시 파일 목록 강제 새로고침하여 UI 복원 시도
            self.load_files()
            self.statusBar.showMessage("파일 이름 변경 실패")


    @Slot(int, str)
    def on_sheet_renamed(self, sheet_id: int, new_name: str):
        """
        시트 이름 변경 처리 (TreeViewModel의 sheet_renamed 시그널에 연결된 슬롯)

        Args:
            sheet_id: 시트 ID
            new_name: 새 시트 이름
        """
        parent_file_id = None
        try:
            # 부모 파일 ID 찾기 (시트 목록 새로고침용)
            for file_id, sheets in self.tree_view.model.sheets_by_file.items():
                if any(s['id'] == sheet_id for s in sheets):
                    parent_file_id = file_id
                    break

            if parent_file_id is None:
                 logging.error(f"Cannot find parent file for sheet ID {sheet_id} during rename.")
                 # 오류 처리: 사용자에게 알리고 롤백 시도?
                 QMessageBox.critical(self, "이름 변경 오류", "시트의 부모 파일을 찾을 수 없어 이름을 변경할 수 없습니다.")
                 # 강제 새로고침
                 if self.current_file_id: self.load_sheets(self.current_file_id)
                 return

            # 달러 표시 포함 여부 결정 (새 이름 기준)
            is_dollar_sheet = "$" in new_name

            logging.info(f"Attempting to rename sheet ID {sheet_id} to '{new_name}' (IsDollar: {is_dollar_sheet}) in DB.")

            # DB에 시트 이름 및 달러 여부 업데이트
            self.db.rename_sheet(sheet_id, new_name, is_dollar_sheet)

            # 상태바 메시지 업데이트
            self.statusBar.showMessage(f"시트 이름이 '{new_name}'으로 변경되었습니다.")
            logging.info(f"Sheet ID {sheet_id} successfully renamed to '{new_name}'.")

            # 시트 목록 새로고침 (이름 변경 및 순서 변경 가능성 반영)
            self.load_sheets(parent_file_id)

            # 현재 선택된 시트가 이름 변경된 시트이면 레이블 업데이트
            if self.current_sheet_id == sheet_id:
                self.sheet_label.setText(f"현재 시트: {new_name}")

        except Exception as e:
            error_msg = f"시트 이름 변경 중 DB 오류 발생: {str(e)}"
            logging.error(f"{error_msg} (Sheet ID: {sheet_id}, New Name: '{new_name}')\n{traceback.format_exc()}")
            QMessageBox.critical(self, "시트 이름 변경 오류", f"{error_msg}\n\n시트 목록을 새로고침합니다.")
            # 오류 발생 시 시트 목록 강제 새로고침하여 UI 복원 시도
            if parent_file_id:
                self.load_sheets(parent_file_id)
            elif self.current_file_id: # 부모 ID 못 찾았으면 현재 파일 ID로 시도
                 self.load_sheets(self.current_file_id)
            self.statusBar.showMessage("시트 이름 변경 실패")

    def startup_routine(self):
        """앱 시작 시 Git pull 및 백업 루틴"""
        try:
            logging.info("앱 시작 루틴 시작...")

            # Git 상태 표시 업데이트
            self.update_git_status("🔄 Git pull 실행 중...", "info")
            QApplication.processEvents()

            # 현재 디렉토리의 모든 .db 파일 찾기
            db_files = [f for f in os.listdir('.') if f.endswith('.db')]

            # Git pull 및 백업 실행
            if self.history_manager.startup_routine(db_files):
                # Git pull 성공 후 기준점 저장
                self.update_git_status("💾 기준점 저장 중...", "info")
                QApplication.processEvents()

                # 현재 열린 DB 핸들러들 수집
                db_handlers = []
                if self.db_manager:
                    for db_name in self.db_manager.databases:
                        db_handler = self.db_manager.databases[db_name]
                        if db_handler:
                            db_handlers.append(db_handler)

                # 기준점 저장
                if db_handlers and self.history_manager.save_baseline_after_pull(db_handlers):
                    self.update_git_status("✅ Git pull, 백업 및 기준점 저장 완료", "success")
                    self.statusBar.showMessage("Git pull, 백업 및 기준점 저장 완료")
                    logging.info("앱 시작 루틴 완료 (기준점 저장 포함)")
                else:
                    self.update_git_status("⚠️ Git pull 완료, 기준점 저장 실패", "warning")
                    self.statusBar.showMessage("Git pull 완료, 기준점 저장 실패")
                    logging.warning("기준점 저장 실패")
            else:
                # Git pull 실패 시 상세한 오류 메시지 표시
                self.update_git_status("❌ Git pull 실패", "error")
                self.statusBar.showMessage("Git pull 실패 - Git 설정을 확인하세요")
                logging.warning("앱 시작 루틴 실패")

                # 사용자에게 해결 방법 안내
                QMessageBox.warning(self, "Git Pull 실패",
                                  "Git pull에 실패했습니다.\n\n"
                                  "가능한 원인:\n"
                                  "• 인증 정보 오류 (사용자 ID/API 토큰)\n"
                                  "• 저장소 URL 오류\n"
                                  "• 네트워크 연결 문제\n"
                                  "• 원격 저장소가 비어있음\n\n"
                                  "Git → Git 설정에서 설정을 확인해주세요.")

        except Exception as e:
            logging.error(f"앱 시작 루틴 중 오류: {e}")
            self.update_git_status("❌ Git 초기화 오류", "error")
            self.statusBar.showMessage("시작 루틴 오류 발생")

    def update_git_status(self, message: str, status_type: str = "info"):
        """Git 상태 레이블 업데이트"""
        if not hasattr(self, 'git_status_label'):
            return

        # 상태별 스타일 설정
        styles = {
            "info": {
                "background-color": "#e3f2fd",
                "color": "#1976d2"
            },
            "success": {
                "background-color": "#e8f5e8",
                "color": "#2e7d32"
            },
            "error": {
                "background-color": "#ffebee",
                "color": "#c62828"
            },
            "warning": {
                "background-color": "#fff3e0",
                "color": "#ef6c00"
            }
        }

        style = styles.get(status_type, styles["info"])

        self.git_status_label.setText(message)
        self.git_status_label.setStyleSheet(f"""
            QLabel {{
                padding: 3px 8px;
                border-radius: 3px;
                font-size: 11px;
                background-color: {style["background-color"]};
                color: {style["color"]};
            }}
        """)

    def get_current_branch(self) -> str:
        """현재 Git 브랜치 이름 가져오기"""
        try:
            # GitManager가 있으면 사용
            if hasattr(self, 'git_manager') and self.git_manager:
                return self.git_manager.get_current_branch()
            else:
                # GitManager가 없으면 직접 Git 명령어 실행
                logging.debug("GitManager가 없어서 직접 Git 명령어 실행")
                import subprocess
                import os

                # Git 실행 파일 경로 찾기 (GitManager와 동일한 로직)
                git_executable = self._find_git_executable_fallback()

                result = subprocess.run(
                    [git_executable, 'branch', '--show-current'],
                    cwd=os.getcwd(),
                    capture_output=True,
                    text=True,
                    encoding='utf-8',
                    errors='replace',
                    timeout=CodeGenerationConstants.GIT_COMMAND_TIMEOUT
                )
                if result.returncode == 0:
                    branch_name = result.stdout.strip()
                    return branch_name if branch_name else 'main'
                else:
                    logging.warning(f"Git 명령어 실행 실패: {result.stderr}")
                    return 'main'
        except Exception as e:
            logging.warning(f"브랜치 정보 가져오기 실패: {e}")
            return 'main'

    def _find_git_executable_fallback(self) -> str:
        """Git 실행 파일 경로 찾기 (GitManager 없을 때 사용)"""
        import platform
        import os
        import subprocess

        # Windows에서 일반적인 Git 설치 경로들
        if platform.system() == "Windows":
            possible_paths = [
                r"C:\Program Files\Git\bin\git.exe",
                r"C:\Program Files\Git\mingw64\bin\git.exe",
                r"C:\Program Files (x86)\Git\bin\git.exe",
                r"C:\Program Files (x86)\Git\mingw64\bin\git.exe",
            ]

            # 설치된 경로 확인
            for path in possible_paths:
                if os.path.exists(path):
                    return path

            # where 명령어로 찾기 시도
            try:
                result = subprocess.run(['where', 'git'],
                                      capture_output=True, text=True, check=True)
                git_path = result.stdout.strip().split('\n')[0]
                if os.path.exists(git_path):
                    return git_path
            except:
                pass

        # 기본값 (PATH에서 찾기)
        return "git"

    def update_branch_display(self):
        """브랜치 표시 업데이트 (Git 상태 레이블에 반영)"""
        try:
            current_branch = self.get_current_branch()

            # Git 상태 레이블에 브랜치 정보 표시
            if hasattr(self, 'git_status_label'):
                # 브랜치별 색상 구분
                if current_branch in ['main', 'master']:
                    status_type = "success"
                else:
                    status_type = "info"

                self.update_git_status(f"브랜치: {current_branch}", status_type)

            logging.debug(f"브랜치 표시 업데이트: {current_branch}")
        except Exception as e:
            logging.warning(f"브랜치 표시 업데이트 실패: {e}")
            if hasattr(self, 'git_status_label'):
                self.update_git_status("브랜치 확인 실패", "error")

    def refresh_git_status(self):
        """Git 브랜치 정보 및 상태 새로고침"""
        try:
            logging.info("Git 상태 수동 새로고침 시작")

            # 새로고침 버튼 일시 비활성화
            self.git_refresh_button.setEnabled(False)
            self.git_refresh_button.setText("⏳")

            # 상태바 메시지 표시
            self.statusBar.showMessage("Git 상태 새로고침 중...")
            QApplication.processEvents()

            # 브랜치 정보 업데이트
            self.update_branch_display()

            # 브랜치 목록 새로고침
            self.refresh_branches()

            # Git 상태 정보 업데이트
            if hasattr(self, 'git_status_label'):
                try:
                    if self.git_manager:
                        current_branch = self.get_current_branch()
                        self.update_git_status(f"브랜치: {current_branch}", "success")
                    else:
                        self.update_git_status("Git 관리자 없음", "warning")
                except Exception as git_error:
                    logging.warning(f"Git 상태 업데이트 실패: {git_error}")
                    self.update_git_status("Git 상태 확인 실패", "error")

            # 완료 메시지
            self.statusBar.showMessage("Git 상태 새로고침 완료")
            logging.info("Git 상태 새로고침 완료")

        except Exception as e:
            logging.error(f"Git 상태 새로고침 중 오류: {e}")
            self.statusBar.showMessage("Git 상태 새로고침 실패")
            if hasattr(self, 'git_status_label'):
                self.update_git_status("새로고침 실패", "error")

        finally:
            # 새로고침 버튼 복원
            self.git_refresh_button.setEnabled(True)
            self.git_refresh_button.setText("↻")

    def reset_to_remote(self):
        """원격 기준으로 로컬 초기화"""
        try:
            # 사용자 확인
            reply = QMessageBox.question(
                self, "원격 기준 초기화 확인",
                "원격 저장소 기준으로 로컬을 초기화하시겠습니까?\n\n"
                "주의: 로컬의 커밋되지 않은 변경사항이 모두 사라집니다!\n"
                "추적되지 않는 파일들은 유지됩니다.",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )

            if reply == QMessageBox.Yes:
                # 상태 업데이트
                self.update_git_status("원격 기준 초기화 중...", "warning")
                self.statusBar.showMessage("원격 기준으로 로컬 초기화 중...")
                QApplication.processEvents()

                # 원격 기준 초기화 실행
                if self.git_manager.reset_to_remote():
                    self.update_git_status("원격 기준 초기화 완료", "success")
                    self.statusBar.showMessage("원격 기준 초기화 완료")

                    # 브랜치 정보 새로고침
                    self.update_branch_display()
                    self.refresh_branches()

                    QMessageBox.information(self, "초기화 완료",
                                          "원격 저장소 기준으로 로컬이 성공적으로 초기화되었습니다.")
                else:
                    self.update_git_status("초기화 실패", "error")
                    self.statusBar.showMessage("원격 기준 초기화 실패")
                    QMessageBox.critical(self, "초기화 실패",
                                       "원격 기준 초기화 중 오류가 발생했습니다.\n로그를 확인해주세요.")

        except Exception as e:
            logging.error(f"원격 기준 초기화 중 오류: {e}")
            self.update_git_status("초기화 오류", "error")
            QMessageBox.critical(self, "초기화 오류",
                               f"원격 기준 초기화 중 오류가 발생했습니다:\n{str(e)}")

    def commit_and_push_changes(self):
        """레거시 함수 - Git 변경사항 확인 다이얼로그 사용 안내"""
        QMessageBox.information(self, "Git 작업 변경",
                              "Git 작업은 이제 '변경사항 확인' 버튼을 사용해주세요.\n"
                              "Git 변경사항을 확인하고 커밋/푸시할 수 있습니다.")



    def generate_csv_history(self):
        """CSV 히스토리 생성 (파일 메뉴에서 호출)"""
        try:
            # 기능 설명 및 확인 대화상자
            info_message = (
                "CSV 히스토리 생성 기능\n\n"
                "이 기능은 초기 CSV 히스토리 설정을 위해 현재 TreeView에 표시된 "
                "모든 데이터베이스의 시트를 CSV 파일로 내보내는 기능입니다.\n\n"
                "작업 내용:\n"
                "• 현재 열린 모든 데이터베이스의 시트를 개별 CSV 파일로 변환\n"
                "• 각 데이터베이스별로 별도의 history 디렉토리 생성\n"
                "• 시트명을 파일명으로 하는 CSV 파일 생성\n"
                "• 기존 CSV 파일이 있는 경우 덮어쓰기\n\n"
                "주의사항:\n"
                "일반적으로 파일 편집 시 CSV 히스토리가 자동으로 생성되므로, "
                "초기 세팅, 특별한 목적 등이 없다면 사용하실 필요가 없습니다.\n\n"
                "이 작업을 진행하시겠습니까?"
            )

            reply = QMessageBox.question(
                self, "CSV 히스토리 생성",
                info_message,
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )

            if reply != QMessageBox.Yes:
                return

            # 현재 열린 모든 DB 핸들러 수집
            db_handlers = []
            if self.db_manager:
                for db_name in self.db_manager.databases:
                    db_handler = self.db_manager.databases[db_name]
                    if db_handler:
                        db_handlers.append(db_handler)

            if not db_handlers:
                QMessageBox.information(self, "데이터베이스 없음",
                                      "CSV로 내보낼 데이터베이스가 없습니다.\n"
                                      "먼저 DB 파일을 열어주세요.")
                return

            # 대상 DB 목록 표시 및 최종 확인
            db_names = []
            total_sheets = 0

            for db in db_handlers:
                if hasattr(db, 'db_file_path'):
                    db_name = os.path.basename(db.db_file_path)
                elif hasattr(db, 'db_file'):
                    db_name = os.path.basename(db.db_file)
                else:
                    db_name = "알 수 없는 DB"

                db_names.append(db_name)

                # 시트 개수 계산
                try:
                    sheets = db.get_sheets()
                    total_sheets += len(sheets)
                except:
                    pass

            db_list = '\n'.join([f"• {name}" for name in db_names])

            final_confirm = QMessageBox.question(
                self, "CSV 히스토리 생성 확인",
                f"대상 데이터베이스 ({len(db_handlers)}개):\n\n{db_list}\n\n"
                f"총 예상 시트 수: 약 {total_sheets}개\n\n"
                f"모든 시트를 CSV 파일로 내보내시겠습니까?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes
            )

            if final_confirm != QMessageBox.Yes:
                return

            # 진행률 다이얼로그 표시
            from PySide6.QtWidgets import QProgressDialog
            progress = QProgressDialog("CSV 히스토리 생성 중...", "취소", 0, 100, self)
            progress.setWindowModality(Qt.WindowModal)
            progress.setMinimumDuration(0)
            progress.show()
            progress.setValue(10)
            QApplication.processEvents()

            # CSV 생성 실행
            progress.setLabelText("모든 DB의 시트를 CSV로 내보내는 중...")
            progress.setValue(50)
            QApplication.processEvents()

            if self.git_manager.export_all_db_history(db_handlers):
                progress.setValue(100)
                progress.setLabelText("CSV 생성 완료")
                QApplication.processEvents()

                # 성공 메시지
                self.statusBar.showMessage("CSV 히스토리 생성 완료")

                QMessageBox.information(self, "CSV 생성 완료",
                                      f"모든 DB의 시트가 CSV로 성공적으로 내보내졌습니다.\n\n"
                                      f"각 DB별 history 디렉토리를 확인해주세요.")
            else:
                progress.close()
                QMessageBox.critical(self, "CSV 생성 실패",
                                   "CSV 파일 생성 중 오류가 발생했습니다.\n"
                                   "로그를 확인해주세요.")

            progress.close()

        except Exception as e:
            logging.error(f"CSV 히스토리 생성 중 오류: {e}")
            QMessageBox.critical(self, "CSV 생성 오류",
                               f"CSV 히스토리 생성 중 오류가 발생했습니다:\n{str(e)}")



    def show_git_status(self):
        """Git 변경사항 확인 다이얼로그 표시 (DB 닫기 없이 바로 표시)"""
        try:
            if not self.git_manager:
                QMessageBox.warning(self, "Git 관리자 없음",
                                  "Git 관리자가 초기화되지 않았습니다.")
                return

            # Git 상태 다이얼로그 생성 및 표시 (DB 닫기 없이 바로)
            # DB 관리자 정보를 다이얼로그에 전달하여 커밋 시 DB 닫기 처리
            dialog = GitStatusDialog(self.git_manager, self, db_manager=self.db_manager)

            # 다이얼로그 실행
            result = dialog.exec()

            # 다이얼로그가 닫힌 후 처리
            if result == QDialog.DialogCode.Accepted:
                # 커밋/푸시가 완료된 경우
                QMessageBox.information(
                    self,
                    "작업 완료",
                    "Git 작업이 완료되었습니다.\n\n"
                    "필요한 경우 '파일 열기' 버튼으로 DB를 다시 열어주세요."
                )

                # DB 참조 업데이트 (DB가 닫혔을 수 있음)
                self.update_current_db_references()
                self.update_db_combo()
                self.load_files()
            else:
                # 다이얼로그만 닫은 경우
                logging.info("Git 상태 다이얼로그 닫힘 (커밋 없음)")

        except Exception as e:
            logging.error(f"Git 변경사항 확인 중 오류: {e}")
            QMessageBox.critical(self, "Git 변경사항 확인 오류",
                               f"Git 변경사항 확인 중 오류가 발생했습니다:\n{str(e)}")

    def refresh_branches(self):
        """브랜치 목록 새로고침"""
        try:
            if not self.git_manager:
                return

            # 시그널 일시 차단
            self.branch_combo.blockSignals(True)

            # 브랜치 목록 가져오기
            branches_info = self.git_manager.get_all_branches()

            # 콤보박스 초기화
            self.branch_combo.clear()

            # 현재 브랜치 표시
            current_branch = branches_info.get('current', 'main')

            # 로컬 브랜치 추가
            local_branches = branches_info.get('local', [])
            for branch in local_branches:
                if branch == current_branch:
                    self.branch_combo.addItem(f"[로컬] {branch} (현재)", f"local:{branch}")
                else:
                    self.branch_combo.addItem(f"[로컬] {branch}", f"local:{branch}")

            # 원격 브랜치 추가 (로컬에 없는 것만)
            remote_branches = branches_info.get('remote', [])
            for branch_info in remote_branches:
                # 새로운 형식 처리 (딕셔너리)
                if isinstance(branch_info, dict):
                    branch_name = branch_info['name']
                    display_name = branch_info['display']
                    full_name = branch_info['full_name']

                    if branch_name not in local_branches:
                        self.branch_combo.addItem(f"[원격] {display_name}", f"remote:{full_name}")
                # 기존 형식 처리 (문자열) - 호환성 유지
                else:
                    branch_name = branch_info
                    if branch_name not in local_branches:
                        self.branch_combo.addItem(f"[원격] {branch_name}", f"remote:origin/{branch_name}")

            # 현재 브랜치 선택
            for i in range(self.branch_combo.count()):
                item_data = self.branch_combo.itemData(i)
                if item_data and item_data.endswith(f":{current_branch}"):
                    self.branch_combo.setCurrentIndex(i)
                    break

            logging.debug(f"브랜치 목록 새로고침 완료: {len(local_branches)}개 로컬, {len(remote_branches)}개 원격")

        except Exception as e:
            logging.error(f"브랜치 목록 새로고침 중 오류: {e}")
            # 기본 브랜치 추가
            self.branch_combo.clear()
            self.branch_combo.addItem("[로컬] main (기본)", "local:main")
        finally:
            # 시그널 차단 해제
            self.branch_combo.blockSignals(False)

    def on_branch_changed(self, branch_text: str):
        """브랜치 선택 변경 시"""
        try:
            if not branch_text or "(현재)" in branch_text:
                return

            # 현재 선택된 항목의 데이터에서 브랜치 정보 추출
            current_index = self.branch_combo.currentIndex()
            if current_index < 0:
                return

            branch_data = self.branch_combo.itemData(current_index)
            if not branch_data:
                return

            # 브랜치 타입과 이름 분리
            branch_type, branch_ref = branch_data.split(':', 1)

            # 원격 브랜치인 경우 실제 브랜치 이름 추출
            if branch_type == "remote":
                if '/' in branch_ref:
                    # "main/master" 또는 "origin/master" 형식
                    branch_name = branch_ref.split('/', 1)[1]
                else:
                    # 단순 브랜치 이름
                    branch_name = branch_ref
            else:
                # 로컬 브랜치
                branch_name = branch_ref

            # 사용자 확인
            reply = QMessageBox.question(
                self, "브랜치 전환 확인",
                f"'{branch_name}' 브랜치로 전환하시겠습니까?\n\n"
                f"브랜치 타입: {branch_type}\n"
                f"현재 작업 중인 변경사항이 있다면 먼저 커밋하는 것을 권장합니다.",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )

            if reply == QMessageBox.Yes:
                # 브랜치 전환
                self.update_git_status("브랜치 전환 중...", "info")
                QApplication.processEvents()

                if self.git_manager.switch_branch(branch_name):
                    self.update_git_status(f"{branch_name} 브랜치로 전환 완료", "success")
                    self.statusBar.showMessage(f"{branch_name} 브랜치로 전환 완료")

                    # 브랜치 정보 업데이트
                    self.update_branch_display()
                    self.refresh_branches()

                    QMessageBox.information(self, "브랜치 전환 완료",
                                          f"'{branch_name}' 브랜치로 성공적으로 전환되었습니다.")
                else:
                    self.update_git_status("브랜치 전환 실패", "error")
                    self.statusBar.showMessage("브랜치 전환 실패")

                    QMessageBox.critical(self, "브랜치 전환 실패",
                                       f"'{branch_name}' 브랜치로 전환하는 중 오류가 발생했습니다.\n"
                                       f"로그를 확인해주세요.")

                    # 이전 선택으로 되돌리기
                    self.refresh_branches()
            else:
                # 사용자가 취소 → 이전 선택으로 되돌리기
                self.refresh_branches()

        except Exception as e:
            logging.error(f"브랜치 변경 처리 중 오류: {e}")
            QMessageBox.critical(self, "브랜치 변경 오류",
                               f"브랜치 변경 중 오류가 발생했습니다:\n{str(e)}")

    def safe_startup_routine(self):
        """안전한 앱 시작 루틴: 자동 Git pull 제거, DB 로드만 수행"""
        try:
            logging.info("=== 안전한 앱 시작 루틴 시작 (자동 Git pull 제거됨) ===")

            # 1단계: DB 시스템 초기화 (Git pull 제거)
            self.update_git_status("📁 파일 시스템 로드 중...", "info")
            self.statusBar.showMessage("파일 목록 로드 중...")
            QApplication.processEvents()

            # DB 관리자 초기화
            self.db_manager = DBManager()
            self.update_current_db_references()

            # 파일 목록 로드
            self.load_files()

            # 2단계: 이전 세션 복원
            self.update_git_status("🗄️ 이전 세션 복원 중...", "info")
            self.statusBar.showMessage("이전 DB 세션 복원 중...")
            QApplication.processEvents()

            self.auto_load_multi_db()

            # 3단계: 시작 완료
            self.update_git_status("✅ 시작 완료", "success")
            self.statusBar.showMessage("모든 초기화 완료")
            logging.info("안전한 앱 시작 루틴 완료 (자동 Git pull 없이)")

            logging.info("=== 안전한 앱 시작 루틴 완료 ===")

        except Exception as e:
            logging.error(f"안전한 앱 시작 루틴 중 오류: {e}")
            self.update_git_status("❌ 시작 오류", "error")
            self.statusBar.showMessage("시작 중 오류 발생")

            # 오류 발생 시에도 기본 로드는 시도
            try:
                logging.info("오류 복구: 기본 시스템 로드 시도")
                self.db_manager = DBManager()
                self.update_current_db_references()
                self.load_files()
                self.auto_load_multi_db()
                self.statusBar.showMessage("기본 로드 완료")
            except Exception as fallback_error:
                logging.error(f"기본 시스템 로드도 실패: {fallback_error}")
                QMessageBox.critical(self, "시스템 초기화 실패",
                                   "시스템 초기화에 실패했습니다.\n"
                                   "프로그램을 다시 시작해주세요.")

    def startup_routine_with_full_refresh(self):
        """완전한 시스템 새로고침: Git pull 먼저, 모든 파일 최신화 후 재로드"""
        try:
            logging.info("=== 완전한 시스템 새로고침 시작 ===")

            # 1단계: 모든 리소스 완전 해제
            self.update_git_status("🧹 모든 리소스 정리 중...", "info")
            QApplication.processEvents()

            self.complete_system_cleanup()

            # 2단계: Git pull 및 백업 (모든 파일 최신화)
            self.update_git_status("🔄 Git pull 실행 중...", "info")
            QApplication.processEvents()

            # 현재 디렉토리의 모든 .db 파일 찾기
            db_files = [f for f in os.listdir('.') if f.endswith('.db')]

            # Git pull 및 백업 실행
            git_success = self.history_manager.startup_routine(db_files)

            if git_success:
                self.update_git_status("✅ Git pull 및 백업 완료", "success")
                logging.info("Git pull 및 백업 완료 - 모든 파일이 최신 상태")
            else:
                self.update_git_status("❌ Git pull 실패", "error")
                logging.warning("Git pull 실패 - 로컬 파일로 계속 진행")

                # Git pull 실패 시 사용자에게 알림
                QMessageBox.warning(self, "Git Pull 실패",
                                  "Git pull에 실패했습니다.\n\n"
                                  "가능한 원인:\n"
                                  "• 인증 정보 오류\n"
                                  "• 네트워크 연결 문제\n"
                                  "• 저장소 접근 권한 문제\n\n"
                                  "로컬 파일로 작업을 계속합니다.\n"
                                  "Git → Git 설정에서 설정을 확인해주세요.")

            # 3단계: 전체 시스템 재초기화 (최신 파일들로)
            self.update_git_status("🔄 시스템 재초기화 중...", "info")
            QApplication.processEvents()

            self.complete_system_reinit()

            # 4단계: 시스템 새로고침 완료
            if git_success:
                self.update_git_status("✅ 모든 초기화 완료", "success")
                self.statusBar.showMessage("Git pull 완료 - 모든 파일이 최신 상태로 로드됨")
                logging.info("완전한 시스템 새로고침 완료")
            else:
                self.update_git_status("⚠️ 로컬 모드로 시작", "warning")
                self.statusBar.showMessage("로컬 파일로 시작 (Git 연결 실패)")

            logging.info("=== 완전한 시스템 새로고침 완료 ===")

        except Exception as e:
            logging.error(f"완전한 시스템 새로고침 중 오류: {e}")
            self.update_git_status("❌ 시스템 초기화 오류", "error")
            self.statusBar.showMessage("시스템 초기화 오류 발생")

            # 오류 발생 시에도 기본 로드는 시도
            try:
                logging.info("오류 복구: 기본 시스템 로드 시도")
                self.complete_system_reinit()
            except Exception as fallback_error:
                logging.error(f"기본 시스템 로드도 실패: {fallback_error}")
                QMessageBox.critical(self, "시스템 초기화 실패",
                                   "시스템 초기화에 실패했습니다.\n"
                                   "프로그램을 다시 시작해주세요.")

    def complete_system_cleanup(self):
        """모든 시스템 리소스 완전 정리"""
        try:
            logging.info("모든 시스템 리소스 정리 시작...")

            # 1. 모든 DB 연결 해제
            if hasattr(self, 'db_manager') and self.db_manager:
                self.db_manager.disconnect_all()
                logging.info("모든 DB 연결 해제 완료")

            if hasattr(self, 'db') and self.db:
                self.db.disconnect()
                logging.info("개별 DB 연결 해제 완료")

            # 2. UI 완전 초기화
            if hasattr(self, 'grid_view'):
                self.grid_view.clear_view()
                self.sheet_label.setText("선택된 시트 없음")
                logging.info("그리드뷰 초기화 완료")

            if hasattr(self, 'tree_view'):
                self.tree_view.clear_all()
                logging.info("트리뷰 초기화 완료")

            # 3. 현재 상태 초기화
            self.current_file_id = None
            self.current_sheet_id = None

            # 4. 파일 핸들 정리 (가능한 모든 열린 파일들)
            # Python의 가비지 컬렉터가 처리하도록 참조 해제
            import gc
            gc.collect()

            logging.info("모든 시스템 리소스 정리 완료")

        except Exception as e:
            logging.error(f"시스템 리소스 정리 중 오류: {e}")

    def complete_system_reinit(self):
        """전체 시스템 재초기화 (최신 파일들로)"""
        try:
            logging.info("전체 시스템 재초기화 시작...")

            # 1. DB 관리자 재생성
            self.db_manager = DBManager()
            self.update_current_db_references()
            logging.info("DB 관리자 재초기화 완료")

            # 2. 파일 목록 로드 (최신 파일들)
            self.load_files()
            logging.info("파일 목록 로드 완료")

            # 3. 마지막으로 열었던 다중 DB 자동 로드 (최신 파일들로)
            self.auto_load_multi_db()
            logging.info("이전 DB 세션 복원 완료")

            # 4. 브랜치 목록 새로고침 (Git 상태 변경 가능성)
            self.refresh_branches()
            logging.info("브랜치 목록 새로고침 완료")

            logging.info("전체 시스템 재초기화 완료")

        except Exception as e:
            logging.error(f"전체 시스템 재초기화 중 오류: {e}")
            raise  # 상위로 전파하여 오류 처리



    def update_current_db_references(self):
        """현재 DB 참조 업데이트 (강화된 버전)"""
        try:
            if self.db_manager and self.db_manager.current_db_name:
                current_db = self.db_manager.get_current_db()
                if current_db:
                    # 모든 참조 업데이트
                    self.db = current_db
                    self.importer = ExcelImporter(current_db)
                    self.exporter = ExcelExporter(current_db)
                    self.grid_view.set_db_handler(current_db)

                    # 현재 DB 정보 로깅
                    db_info = {
                        'name': self.db_manager.current_db_name,
                        'path': current_db.db_file_path,
                        'file_count': len(current_db.get_files()),
                        'sheet_count': len(current_db.get_sheets())
                    }

                    logging.info(f"현재 DB 참조 업데이트 완료: {db_info}")

                    # UI 상태 업데이트
                    self.update_git_status_display()

                else:
                    logging.error("현재 DB 핸들러를 가져올 수 없음")
                    self.clear_db_references()
            else:
                logging.warning("DB 관리자 또는 현재 DB 이름이 없음")
                self.clear_db_references()

        except Exception as e:
            logging.error(f"DB 참조 업데이트 중 오류: {e}")
            self.clear_db_references()

    def clear_db_references(self):
        """DB 참조 정리"""
        try:
            self.db = None
            self.importer = None
            self.exporter = None
            if hasattr(self, 'grid_view'):
                self.grid_view.clear_view()
            logging.info("DB 참조 정리 완료")
        except Exception as e:
            logging.error(f"DB 참조 정리 중 오류: {e}")

    def update_git_status_display(self):
        """Git 상태 표시 업데이트 (단순화된 버전)"""
        try:
            if not hasattr(self, 'git_manager') or not self.git_manager:
                self.update_git_status("Git 관리자 없음", "error")
                return

            # 현재 브랜치 정보만 표시
            try:
                current_branch = self.get_current_branch()
                if current_branch:
                    self.update_git_status(f"브랜치: {current_branch}", "success")
                else:
                    self.update_git_status("Git 저장소 없음", "warning")
            except Exception as branch_error:
                logging.debug(f"브랜치 정보 확인 실패: {branch_error}")
                self.update_git_status("Git 상태 확인 불가", "warning")

        except Exception as e:
            logging.error(f"Git 상태 표시 업데이트 실패: {e}")
            self.update_git_status("상태 확인 실패", "error")

    def cleanup(self):
        """애플리케이션 종료 시 정리 작업"""
        try:
            # 모든 DB 연결 해제
            if hasattr(self, 'db_manager') and self.db_manager:
                self.db_manager.disconnect_all()
                logging.info("모든 DB 연결 해제 완료")

            # 개별 DB 연결도 해제 (안전 장치)
            if hasattr(self, 'db') and self.db:
                self.db.disconnect()
                logging.info("개별 DB 연결 해제 완료")

        except Exception as e:
            logging.error(f"정리 작업 중 오류: {e}")
            # 정리 작업 실패는 프로그램 종료를 막지 않음

    def load_sheets(self, file_id: int):
        """
        특정 파일의 시트 목록 로드 및 트리뷰 업데이트

        Args:
            file_id: 파일 ID
        """
        try:
            sheets = self.db.get_sheets(file_id)
            self.tree_view.update_sheets(file_id, sheets)
            logging.info(f"Loaded {len(sheets)} sheets for file ID {file_id}")
        except Exception as e:
            error_msg = f"시트 목록 로드 중 오류 발생: {str(e)}"
            logging.error(f"{error_msg} (File ID: {file_id})")
            QMessageBox.critical(self, "시트 로드 오류", error_msg)


def main():
    """애플리케이션 메인 함수"""
    # 고해상도 디스플레이 지원 (선택사항)
    # QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
    # QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)

    app = QApplication(sys.argv)
    app.setStyle('Fusion')  # 일관된 UI 스타일 적용

    # 로깅 시작 메시지
    logging.info("=========================================")
    logging.info(f"Starting {Info.APP_NAME} Application v{Info.APP_VERSION}")
    if OPTIMIZED_PROCESSING_AVAILABLE:
        logging.info("🚀 성능 최적화 적용 버전 (61.1% 성능 향상)")
    logging.info(f"Python version: {sys.version}")
    logging.info(f"PySide6 version: {PySide6.__version__}") # PySide6 임포트 필요
    logging.info("=========================================")

    window = DBExcelEditor()
    window.show()

    sys.exit(app.exec())

# --- PySide6 버전 정보 임포트 ---
try:
    import PySide6
except ImportError:
    logging.critical("PySide6 모듈을 찾을 수 없습니다. 설치해주세요.")
    sys.exit("PySide6 모듈이 설치되지 않았습니다.")
# ---------------------------------

if __name__ == "__main__":
    # 성능 최적화 상태 확인
    if OPTIMIZED_PROCESSING_AVAILABLE:
        logging.info("✅ 성능 최적화 프로세서가 사용 가능합니다.")
        print("🚀 성능 최적화 활성화: 61.1% 성능 향상 적용")
    else:
        logging.warning("⚠️ 최적화된 프로세서를 사용할 수 없습니다. 기본 기능으로 작동합니다.")
        print("⚠️ 최적화 기능 없이 기본 기능으로 작동합니다.")

    main()