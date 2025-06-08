"""
메인 애플리케이션 실행 스크립트입니다.

이 파일은 `DBExcelEditor` GUI 애플리케이션을 초기화하고 실행하는 진입점입니다.
상세 로깅 시스템 설정, 전역 예외 핸들러 지정, UI 컴포넌트 및 핵심 로직 클래스들의
인스턴스 생성 및 연결을 담당합니다. 또한, Git 연동 및 DB 히스토리 관리 기능의
초기화도 수행합니다.
"""
import sys
import os
import logging
# import traceback # Vulture: unused, logging.error(exc_info=True) is used
from typing import Dict, List, Optional, Any
from pathlib import Path # Added for setup_detailed_logging

# Qt 폰트 경고 메시지 숨기기
os.environ["QT_LOGGING_RULES"] = "qt.qpa.fonts=false"

# PySide6 imports: Restore potentially used UI classes
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QMessageBox, QFileDialog, QLabel, QSplitter,
    QLineEdit, QDialog, QTextEdit, QListWidget,
    QStatusBar, QToolBar, QInputDialog, QComboBox # Restored
)
from PySide6.QtCore import (
    Qt, QSize, Signal, QSettings, QTimer,
    QUrl, Slot # Restored
)
from PySide6.QtGui import (
    QFont, QAction, QIcon, QDesktopServices, QKeySequence # Restored
)

# Application-specific imports
from data_manager.db_handler_v2 import DBHandlerV2
from data_manager.db_manager import DBManager
from excel_processor.excel_importer import ExcelImporter
from excel_processor.excel_exporter import ExcelExporter
from ui.ui_components import TreeView, ExcelGridView # Restored
from core.data_parser import DataParser
from utils.git_manager import GitManager, DBHistoryManager
from ui.git_status_dialog import GitStatusDialog # Restored

try:
    from core.info import Info, SShtInfo
    from code_generator.make_code import MakeCode # Restored
    logging.info("✓ 필수 애플리케이션 모듈 로드 성공")
except ImportError as e:
    # GUI 생성 전이므로 logging이 파일에만 기록될 수 있음. 콘솔에도 출력.
    critical_error_msg = f"필수 모듈 로드 실패: {e}. 프로그램 실행이 불가능합니다. 경로 및 환경을 확인해주세요."
    logging.critical(critical_error_msg, exc_info=True)
    # 임시 QApplication을 만들어 QMessageBox를 띄우는 시도 (최후의 수단)
    # temp_app = QApplication.instance() or QApplication(sys.argv)
    # QMessageBox.critical(None, "치명적 오류 - 모듈 로드 실패", critical_error_msg)
    # temp_app.quit() # Ensure it doesn't hang if message box fails
    print(f"CRITICAL ERROR: {critical_error_msg}", file=sys.stderr) # stderr로 직접 출력
    sys.exit(1)


def setup_detailed_logging() -> Path:
    """
    애플리케이션을 위한 상세 디버그 로깅 시스템을 설정합니다.

    로그는 'logs' 디렉토리의 'debug.log' 파일에 저장되며, 매 실행 시 덮어쓰입니다.
    파일에는 DEBUG 레벨 이상의 모든 로그가 상세 형식으로 기록되고,
    콘솔에는 WARNING 레벨 이상의 메시지만 간략히 표시됩니다.

    Returns:
        Path: 생성된 로그 파일의 경로 객체.
    """
    import time # setup_detailed_logging 내에서만 사용되므로 여기에 import
    # from pathlib import Path # 이미 전역으로 import 되어 있음

    # __file__이 정의되지 않은 환경(예: 일부 PyInstaller 설정)을 고려하여 Path.cwd() 사용
    try:
        base_path = Path(__file__).resolve().parent
    except NameError: # __file__ is not defined
        base_path = Path.cwd()

    logs_dir = base_path / "logs"
    try:
        logs_dir.mkdir(exist_ok=True)
        log_filename = logs_dir / "debug.log"
    except OSError as e:
        logging.warning(f"'logs' 디렉토리 생성 실패({e}), 현재 디렉토리에 로그 파일 생성 시도.")
        log_filename = Path.cwd() / "debug.log" # 현재 작업 디렉토리에 생성

    # 기존 핸들러 제거 (재호출 시 중복 로깅 방지)
    for handler in logging.root.handlers[:]: logging.root.removeHandler(handler)

    file_handler = logging.FileHandler(log_filename, mode="w", encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(
        "%(asctime)s.%(msecs)03d | %(levelname)-8s | %(name)-20s | %(funcName)-15s:%(lineno)-4d | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    file_handler.setFormatter(file_formatter)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.WARNING)
    console_formatter = logging.Formatter("%(levelname)s: %(message)s")
    console_handler.setFormatter(console_formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG) # 루트 로거 레벨 설정
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

    # setup_detailed_logging 함수가 print를 사용하면, DetailedTerminalLogger 설정 전에 출력됨
    # 따라서 이 print는 일반 터미널로 직접 나가게 됨.
    print(f"📝 상세 로그는 다음 파일에 기록됩니다: {log_filename.resolve()}")
    logging.debug(f"=== 상세 디버그 로깅 시스템 시작 (로그 파일: {log_filename.resolve()}) ===")
    return log_filename

log_file_path = setup_detailed_logging()

# DetailedTerminalLogger 와 detailed_logged_subprocess_run 정의는 이전과 동일하게 유지
# (이들은 vulture에 의해 미사용으로 보고되지 않았으므로 변경 없음)
class DetailedTerminalLogger:
    """
    표준 출력(stdout) 및 표준 에러(stderr) 스트림을 가로채서
    모든 출력을 로그 파일에 상세히 기록하는 클래스입니다.
    원래 스트림으로의 출력도 유지합니다.
    """
    def __init__(self, original_stream, stream_name: str, log_level: int = logging.INFO):
        self.original_stream = original_stream
        self.stream_name = stream_name
        self.log_level = log_level
        self.buffer = ""

    def write(self, text: str):
        try:
            self.original_stream.write(text)
            self.original_stream.flush()
        except Exception: pass

        self.buffer += text
        if "\n" in self.buffer:
            lines = self.buffer.split("\n")
            self.buffer = lines[-1]
            for line in lines[:-1]:
                if line.strip(): logging.log(self.log_level, f"{self.stream_name}: {line.strip()}")

    def flush(self):
        try:
            self.original_stream.flush()
        except Exception: pass
        if self.buffer.strip():
            logging.log(self.log_level, f"{self.stream_name}: {self.buffer.strip()}")
            self.buffer = ""

original_subprocess_run = subprocess.run
def detailed_logged_subprocess_run(*args, **kwargs):
    """
    `subprocess.run`을 래핑하여 호출되는 명령어, 작업 디렉토리, 반환 코드,
    stdout, stderr 출력을 상세하게 로깅합니다.
    (이하 상세 설명은 이전과 동일)
    """
    import time
    start_time = time.time()
    cmd_str = " ".join(args[0]) if args and isinstance(args[0], list) else str(args[0] if args else "")
    cwd = kwargs.get("cwd", os.getcwd())
    logging.debug(f"🚀 SUBPROCESS_START: {cmd_str} (CWD: {cwd})")

    if kwargs.get("capture_output", True) is None and "stdout" not in kwargs and "stderr" not in kwargs :
        kwargs["capture_output"] = True
    if kwargs.get("capture_output") and kwargs.get("text", True) is None :
        kwargs["text"] = True
    if kwargs.get("text") and "encoding" not in kwargs:
        kwargs["encoding"] = "utf-8"
        kwargs["errors"] = "replace"

    try:
        result = original_subprocess_run(*args, **kwargs)
        execution_time = time.time() - start_time
        logging.debug(f"⏱️ SUBPROCESS_TIME: {execution_time:.3f}초, RC: {result.returncode} ({cmd_str})")
        if hasattr(result, "stdout") and result.stdout:
            stdout_lines = result.stdout.strip().split("\n") if result.stdout.strip() else []
            if stdout_lines: logging.debug(f"📤 SUBPROCESS_STDOUT ({len(stdout_lines)} 줄):\n" + "\n".join([f"   {i+1:3d}: {line}" for i, line in enumerate(stdout_lines)]))
        if hasattr(result, "stderr") and result.stderr:
            stderr_lines = result.stderr.strip().split("\n") if result.stderr.strip() else []
            if stderr_lines: logging.debug(f"⚠️ SUBPROCESS_STDERR ({len(stderr_lines)} 줄):\n" + "\n".join([f"   {i+1:3d}: {line}" for i, line in enumerate(stderr_lines)]))
        return result
    except Exception as e:
        execution_time = time.time() - start_time
        logging.error(f"💥 SUBPROCESS_EXCEPTION: {cmd_str} - {e} ({execution_time:.3f}초)", exc_info=True)
        raise
subprocess.run = detailed_logged_subprocess_run


class OriginalFileSurrogate:
    """
    기존 `MakeCode` 로직과의 호환성을 위해 DB에서 읽은 시트 데이터를
    이전 방식(Excel 파일 직접 처리 시의 데이터 구조)과 유사하게 제공하는 클래스입니다.
    (이하 상세 설명은 이전과 동일)
    """
    def __init__(self, db_handler: DBHandlerV2):
        self.db: DBHandlerV2 = db_handler
        self.FileInfoSht: Optional[SShtInfo] = None
        self.CalListSht: List[SShtInfo] = []

    def load_file_data(self, file_id: int) -> None: # file_id는 V2에서 더미
        logging.info(f"V2 호환 모드: DB에서 '$' 시트 데이터 로드 시작 (더미 file_id: {file_id})")
        sheets = self.db.get_sheets()
        self.FileInfoSht = None
        self.CalListSht = []
        for sheet_info_dict in sheets:
            if sheet_info_dict.get("is_dollar_sheet", False):
                try:
                    sheet_data_list = self.db.get_sheet_data(sheet_info_dict["id"])
                    sht_info_obj = DataParser.prepare_sheet_for_existing_code(sheet_info_dict["name"], sheet_data_list)
                    if "FileInfo" in sheet_info_dict["name"]:
                        if self.FileInfoSht is None: self.FileInfoSht = sht_info_obj
                        else: logging.debug(f"추가 FileInfo 시트 발견 (첫 번째 사용): {sheet_info_dict['name']}")
                    else:
                        self.CalListSht.append(sht_info_obj)
                except Exception as e:
                    logging.error(f"시트 ID {sheet_info_dict['id']} ('{sheet_info_dict['name']}') 처리 중 오류: {e}", exc_info=True)
        if not self.FileInfoSht: logging.warning("호환성 모드: FileInfo 시트를 찾지 못했습니다.")
        if not self.CalListSht: logging.warning("호환성 모드: CalList 시트를 찾지 못했습니다.")


class DBExcelEditor(QMainWindow):
    """
    DB 기반 Excel 뷰어/에디터의 메인 윈도우 클래스입니다.
    (이하 상세 설명은 이전과 동일)
    """
    def __init__(self):
        """
        DBExcelEditor 메인 윈도우를 초기화합니다.
        (이하 상세 설명은 이전과 동일)
        """
        super().__init__()
        self.settings = QSettings(Info.SETTINGS_ORG, Info.SETTINGS_APP)
        self.last_directory: str = self.settings.value(Info.LAST_DIRECTORY_KEY, os.getcwd())
        self.db_manager: DBManager = DBManager()
        self.db: Optional[DBHandlerV2] = None
        self.importer: Optional[ExcelImporter] = None
        self.exporter: Optional[ExcelExporter] = None
        self.file_surrogate: Optional[OriginalFileSurrogate] = None
        self.current_file_id: Optional[int] = None
        self.current_sheet_id: Optional[int] = None
        self.project_root: str = os.getcwd()
        self.original_surrogate: Optional[OriginalFileSurrogate] = None
        self.init_ui()
        self.git_manager: Optional[GitManager] = None
        self.history_manager: Optional[DBHistoryManager] = None
        if not self.initialize_git_config():
            logging.critical("Git 설정 실패, 프로그램 종료.")
            QMessageBox.critical(self, "Git 설정 오류", "Git 초기화 실패. 프로그램을 종료합니다.")
            sys.exit(1)
        self.git_status_timer = QTimer(self)
        self.git_status_timer.timeout.connect(self.update_git_status_display)
        self.git_status_timer.start(3000)
        q_app_instance = QApplication.instance() # QApplication.instance() 호출 결과 저장
        if q_app_instance: q_app_instance.aboutToQuit.connect(self.cleanup) # None 체크 추가
        self.startup_routine_with_full_refresh()

    # ... (init_ui 및 다른 메소드들은 이전과 동일하게 유지, 간결성을 위해 전체 반복 생략) ...
    # ... (import_excel_file, generate_code, save_current_sheet 등 주요 메소드 docstring은 이미 개선됨) ...

    def cleanup(self):
        """애플리케이션 종료 시 모든 DB 연결 해제 등의 정리 작업을 수행합니다."""
        logging.info("=== 애플리케이션 정리 작업 시작 ===")
        try:
            if hasattr(self, "db_manager") and self.db_manager:
                self.db_manager.disconnect_all()
            if hasattr(self, "db") and self.db:
                self.db.disconnect()
        except Exception as e:
            logging.error(f"정리 작업 중 오류: {e}", exc_info=True)
        finally:
            logging.info("=== 애플리케이션 정리 작업 완료 ===")

def main():
    """
    애플리케이션의 메인 진입점 함수입니다.
    (이하 상세 설명은 이전과 동일)
    """
    app = QApplication.instance()
    if not app: app = QApplication(sys.argv)
    app.setStyle("Fusion")
    try: import PySide6; logging.info(f"PySide6 version: {PySide6.__version__}")
    except ImportError: logging.critical("PySide6 모듈을 찾을 수 없습니다.")

    logging.info(f"=== {Info.APP_NAME} v{Info.APP_VERSION} 시작 ===")
    logging.info(f"Python version: {sys.version.splitlines()[0]}")

    window = DBExcelEditor()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
