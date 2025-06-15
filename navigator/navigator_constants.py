"""
네비게이터 관련 상수 정의

모든 OpCode 매핑, 색상, 아이콘을 중앙 집중화하여 관리합니다.
"""

from PySide6.QtGui import QColor

try:
    from core.info import EMkMode
except ImportError:
    # 테스트 환경을 위한 모의 EMkMode
    from enum import Enum
    class EMkMode(Enum):
        TITLE = 0
        TITLE_H = 1
        TITLE_S = 2
        SUBTITLE = 3
        DESCRIPT = 4
        DEFINE = 5
        TYPEDEF = 6
        STR_MEM = 7
        ENUM = 9
        ENUM_MEM = 10
        ENUM_END = 11
        ARRAY = 12
        ARR_MEM = 13
        VARIABLE = 14
        CODE = 15
        PRGM_SET = 16
        PRGM_END = 17
        NONE = 18
        PRJT_DEF = 19

# 네비게이터 설정 상수
class NavigatorConstants:
    """네비게이터 관련 상수"""
    OPCODE_COL_CANDIDATES = [0, 1]  # OpCode가 있을 수 있는 열 위치
    NAME_COL_OFFSETS = [3, 4, 5]   # OpCode 기준 Name 열 오프셋
    MAX_HEADER_SEARCH_ROWS = 10    # 헤더 검색할 최대 행 수
    MAX_OPCODE_SEARCH_ROWS = 50    # OpCode 검색할 최대 행 수
    NAME_PATTERN_THRESHOLD = 0.3   # 변수명 패턴 임계값

# OpCode 색상 팔레트 (기존 시스템과 호환)
OPCODE_COLORS = {
    EMkMode.TITLE: QColor(173, 216, 230, 102),      # 연한 파란색
    EMkMode.TITLE_H: QColor(173, 216, 230, 102),    # 헤더 타이틀
    EMkMode.TITLE_S: QColor(173, 216, 230, 102),    # 소스 타이틀
    EMkMode.SUBTITLE: QColor(173, 216, 230, 77),    # 더 연한 파란색
    EMkMode.DESCRIPT: QColor(173, 216, 230, 51),    # 매우 연한 파란색
    EMkMode.DEFINE: QColor(144, 238, 144, 102),     # 연한 초록색
    EMkMode.VARIABLE: QColor(144, 238, 144, 77),    # 더 연한 초록색
    EMkMode.TYPEDEF: QColor(255, 255, 224, 128),    # 연한 노란색
    EMkMode.ENUM: QColor(255, 255, 224, 102),       # 더 연한 노란색
    EMkMode.ENUM_MEM: QColor(255, 255, 224, 77),    # 매우 연한 노란색
    EMkMode.ARRAY: QColor(255, 218, 185, 102),      # 연한 주황색
    EMkMode.ARR_MEM: QColor(255, 218, 185, 77),     # 더 연한 주황색
    EMkMode.STR_MEM: QColor(255, 218, 185, 77),     # 구조체 멤버
    EMkMode.CODE: QColor(221, 160, 221, 102),       # 연한 보라색
    EMkMode.PRGM_SET: QColor(221, 160, 221, 77),    # 프라그마 시작
    EMkMode.PRGM_END: QColor(221, 160, 221, 77),    # 프라그마 종료
    EMkMode.PRJT_DEF: QColor(211, 211, 211, 102),   # 연한 회색
    EMkMode.NONE: QColor(255, 255, 255, 255),       # 흰색 (기본)
}

# OpCode 문자열 → EMkMode 매핑
OPCODE_MAPPING = {
    "$TITLE": EMkMode.TITLE,
    "$TITLE_S": EMkMode.TITLE_S,
    "$TITLE_H": EMkMode.TITLE_H,
    "$SUBTITLE": EMkMode.SUBTITLE,
    "$DESCRIPT": EMkMode.DESCRIPT,
    "$DEFINE": EMkMode.DEFINE,
    "$TYPEDEF": EMkMode.TYPEDEF,
    "$STR_MEM": EMkMode.STR_MEM,
    "$ENUM": EMkMode.ENUM,
    "$ENUM_MEM": EMkMode.ENUM_MEM,
    "$ENUM_END": EMkMode.ENUM_END,
    "$ARRAY": EMkMode.ARRAY,
    "$ARR_MEM": EMkMode.ARR_MEM,
    "$VARIABLE": EMkMode.VARIABLE,
    "$PRGM_SET": EMkMode.PRGM_SET,
    "$PRGM_END": EMkMode.PRGM_END,
    "$CODE": EMkMode.CODE,
    "$PRJT_DEF": EMkMode.PRJT_DEF,
}

# OpCode → 아이콘 매핑
ICON_MAPPING = {
    EMkMode.TITLE: "📘", EMkMode.TITLE_H: "📘", EMkMode.TITLE_S: "📘",
    EMkMode.SUBTITLE: "📄", EMkMode.DESCRIPT: "📝",
    EMkMode.DEFINE: "🔧", EMkMode.VARIABLE: "💾",
    EMkMode.ARRAY: "🔲", EMkMode.ENUM: "📊",
    EMkMode.TYPEDEF: "📋", EMkMode.CODE: "⚙️",
    EMkMode.PRGM_SET: "🔧", EMkMode.PRGM_END: "🔧",
    EMkMode.PRJT_DEF: "📁"
}

# 네비게이터에 표시할 OpCode들
DISPLAY_OPCODES = {
    EMkMode.TITLE, EMkMode.TITLE_H, EMkMode.TITLE_S,
    EMkMode.SUBTITLE, EMkMode.DESCRIPT, EMkMode.DEFINE,
    EMkMode.VARIABLE, EMkMode.ARRAY, EMkMode.ENUM,
    EMkMode.TYPEDEF, EMkMode.CODE, EMkMode.PRGM_SET,
    EMkMode.PRJT_DEF
}
