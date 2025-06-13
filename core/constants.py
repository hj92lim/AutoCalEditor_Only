"""
AutoCalEditor 전역 상수 정의 모듈
모든 하드코딩된 값들을 중앙 집중식으로 관리 (SSOT 원칙)
"""

from enum import Enum
from typing import Dict, List, Tuple


class UIConstants:
    """UI 관련 상수들"""
    
    # 윈도우 크기
    MIN_WINDOW_WIDTH = 1200
    MIN_WINDOW_HEIGHT = 800
    
    # 스플리터 비율
    TREE_VIEW_WIDTH = 300
    GRID_VIEW_WIDTH = 900
    
    # 폰트 크기
    DEFAULT_FONT_SIZE = 11
    HEADER_FONT_SIZE = 12
    
    # 아이콘 크기
    TOOLBAR_ICON_SIZE = 24
    BUTTON_ICON_SIZE = 16
    
    # 간격 및 여백
    DEFAULT_MARGIN = 5
    DEFAULT_SPACING = 5
    PANEL_PADDING = 15
    
    # 색상 (스타일시트용)
    PRIMARY_COLOR = "#007bff"
    SUCCESS_COLOR = "#28a745"
    WARNING_COLOR = "#ffc107"
    DANGER_COLOR = "#dc3545"
    INFO_COLOR = "#17a2b8"
    
    BACKGROUND_LIGHT = "#f8f9fa"
    BACKGROUND_DARK = "#e9ecef"
    BORDER_COLOR = "#dee2e6"
    TEXT_COLOR = "#495057"
    TEXT_MUTED = "#6c757d"


class DatabaseConstants:
    """데이터베이스 관련 상수들"""
    
    # 파일 확장자
    DB_EXTENSION = ".db"
    BACKUP_EXTENSION = ".bak"
    
    # 기본 파일명
    DEFAULT_DB_NAME = "cal_database"
    BACKUP_PREFIX = "backup"
    
    # 디렉토리명
    DATABASE_DIR = "database"
    BACKUP_DIR = "backups"
    HISTORY_DIR = "history"
    LOGS_DIR = "logs"
    
    # SQLite 성능 최적화 설정
    PRAGMA_SETTINGS = [
        "PRAGMA journal_mode = WAL",
        "PRAGMA synchronous = NORMAL",
        "PRAGMA cache_size = 100000",
        "PRAGMA temp_store = MEMORY",
        "PRAGMA mmap_size = 268435456",
        "PRAGMA optimize"
    ]
    
    # 인덱스 정의
    PERFORMANCE_INDEXES = [
        "CREATE INDEX IF NOT EXISTS idx_cells_sheet_row ON cells(sheet_id, row)",
        "CREATE INDEX IF NOT EXISTS idx_cells_sheet_row_col ON cells(sheet_id, row, col)",
        "CREATE INDEX IF NOT EXISTS idx_sheets_name ON sheets(name)",
        "CREATE INDEX IF NOT EXISTS idx_sheets_dollar ON sheets(is_dollar_sheet)"
    ]
    
    # 배치 처리 크기
    BATCH_SIZE_SMALL = 1000
    BATCH_SIZE_MEDIUM = 10000
    BATCH_SIZE_LARGE = 50000
    
    # 메모리 관리
    GC_INTERVAL_CELLS = 200000  # 20만개 셀마다 가비지 컬렉션


class ExcelConstants:
    """Excel 관련 상수들"""
    
    # 파일 확장자
    EXCEL_EXTENSIONS = (".xlsx", ".xls")
    CSV_EXTENSION = ".csv"
    
    # 파일 필터 (QFileDialog용)
    EXCEL_FILE_FILTER = "Excel 파일 (*.xlsx *.xls)"
    CSV_FILE_FILTER = "CSV 파일 (*.csv)"
    
    # 시트 처리 규칙
    DOLLAR_SHEET_MARKER = "$"
    FILEINFO_SHEET_NAME = "FileInfo"
    
    # 셀 처리 한계
    MAX_ROWS = 1048576  # Excel 최대 행 수
    MAX_COLS = 16384    # Excel 최대 열 수
    
    # 기본 시트 크기 (빈 시트용)
    DEFAULT_ROWS = 100
    DEFAULT_COLS = 50


class CodeGenerationConstants:
    """코드 생성 관련 상수들"""
    
    # 파일 확장자
    C_SOURCE_EXT = ".c"
    C_HEADER_EXT = ".h"
    
    # 시트 타입 정의
    FILEINFO_SHEET_TYPE = "FileInfo"
    CALLIST_SHEET_TYPES = ["CalList", "CalData", "Caldata", "COMMON"]
    PROJECT_SHEET_PREFIX = "_"
    UNDEFINED_SHEET_TYPE = "UNDEFINED"
    END_SHEET_TYPE = "END"
    
    # 그룹 관련
    DEFAULT_GROUP_NAME = "Default"
    
    # FileInfo 시트에서 파일명 읽기 위치
    FILEINFO_FILENAME_ROW_PRIMARY = 9
    FILEINFO_FILENAME_COL_PRIMARY = 3
    FILEINFO_FILENAME_ROW_SECONDARY = 8
    FILEINFO_FILENAME_COL_SECONDARY = 2
    
    # 프로젝트 관련 상수
    MAX_FILE_NUM = 10
    PROJECT_DEF_COL = 2
    PROJECT_NAME_COL = 5
    TAB_SIZE = 4
    
    # 특수 프로젝트명
    COMMON_PROJECT_NAME = "COMMON"
    DEFAULT_PROJECT_NAME = "DEFAULT"
    END_PROJECT_NAME = "END"
    EMPTY_KEYWORD = "Empty"


class GitConstants:
    """Git 관련 상수들"""
    
    # 타임아웃 설정 (초)
    GIT_COMMAND_TIMEOUT = 10
    GIT_STATUS_UPDATE_INTERVAL = 3000  # 밀리초
    
    # 기본 브랜치명 우선순위
    DEFAULT_BRANCH_PRIORITY = ["main", "master"]
    
    # Git 실행 파일 경로 (Windows)
    WINDOWS_GIT_PATHS = [
        r"C:\Program Files\Git\bin\git.exe",
        r"C:\Program Files\Git\mingw64\bin\git.exe",
        r"C:\Program Files (x86)\Git\bin\git.exe",
        r"C:\Program Files (x86)\Git\mingw64\bin\git.exe",
    ]


class PerformanceConstants:
    """성능 관련 상수들"""
    
    # 타임아웃 설정
    MULTI_DB_TIMEOUT = 3600  # 1시간
    EXCEL_IMPORT_TIMEOUT = 1800  # 30분
    CODE_GENERATION_TIMEOUT = 600  # 10분
    
    # 병렬 처리 설정
    DEFAULT_MAX_WORKERS = 4
    CONNECTION_POOL_SIZE = 10
    MAX_MEMORY_MB = 1024
    
    # 진행률 범위
    PROGRESS_SHEET_CLASSIFICATION_START = 30
    PROGRESS_SHEET_CLASSIFICATION_END = 50
    PROGRESS_CODE_GENERATION_START = 50
    PROGRESS_CODE_GENERATION_END = 95
    
    # Cython 최적화 임계값
    CYTHON_THRESHOLD_CELLS = 10000
    CYTHON_THRESHOLD_SHEETS = 50


class ApplicationConstants:
    """애플리케이션 전반 상수들"""
    
    # 애플리케이션 정보
    APP_NAME = "AutoCalEditor"
    APP_VERSION = "2.2"
    APP_TITLE = f"{APP_NAME} v{APP_VERSION}"
    
    # 설정 관련
    SETTINGS_ORG = "AutoCalEditor"
    SETTINGS_APP = "AutoCalEditor"
    LAST_DIRECTORY_KEY = "last_directory"
    
    # 환경 변수
    QT_LOGGING_RULES = 'qt.qpa.fonts=false'
    
    # UI 스타일
    DEFAULT_UI_STYLE = 'Fusion'


class ValidationConstants:
    """검증 관련 상수들"""
    
    # 파일 크기 제한 (바이트)
    MIN_DB_FILE_SIZE = 50000  # 50KB
    MAX_EXCEL_FILE_SIZE = 100 * 1024 * 1024  # 100MB
    
    # 문자열 길이 제한
    MAX_SHEET_NAME_LENGTH = 255
    MAX_CELL_VALUE_LENGTH = 32767  # Excel 셀 최대 문자 수
    MAX_FILE_NAME_LENGTH = 255
    
    # 정규식 패턴
    VALID_SHEET_NAME_PATTERN = r'^[^\\/:*?"<>|]+$'
    VALID_FILE_NAME_PATTERN = r'^[^\\/:*?"<>|]+\.[a-zA-Z0-9]+$'
    
    # 인코딩 관련
    DEFAULT_ENCODING = 'utf-8'
    FALLBACK_ENCODING = 'cp949'


class ErrorConstants:
    """오류 관련 상수들"""
    
    # 오류 메시지 템플릿
    DB_CONNECTION_ERROR = "데이터베이스 연결 실패: {error}"
    EXCEL_IMPORT_ERROR = "Excel 파일 가져오기 실패: {error}"
    CODE_GENERATION_ERROR = "코드 생성 실패: {error}"
    GIT_OPERATION_ERROR = "Git 작업 실패: {error}"
    
    # 로그 레벨별 접두사
    LOG_PREFIXES = {
        'DEBUG': '🔍',
        'INFO': '✓',
        'WARNING': '⚠️',
        'ERROR': '❌',
        'CRITICAL': '🚨'
    }


# 하위 호환성을 위한 별칭들
class LegacyConstants:
    """기존 코드와의 호환성을 위한 상수들"""
    
    # Info 클래스에서 이전된 상수들
    ReadingXlsRule = ExcelConstants.DOLLAR_SHEET_MARKER
    FileInfoShtName = CodeGenerationConstants.FILEINFO_SHEET_TYPE
    CommPrjtName = CodeGenerationConstants.COMMON_PROJECT_NAME
    ElsePrjtName = CodeGenerationConstants.DEFAULT_PROJECT_NAME
    EndPrjtName = CodeGenerationConstants.END_PROJECT_NAME
    EmptyKey = CodeGenerationConstants.EMPTY_KEYWORD
    
    MaxFileNum = CodeGenerationConstants.MAX_FILE_NUM
    PrjtDefCol = CodeGenerationConstants.PROJECT_DEF_COL
    PrjtNameCol = CodeGenerationConstants.PROJECT_NAME_COL
    TabSize = CodeGenerationConstants.TAB_SIZE
