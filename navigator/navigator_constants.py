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

# OpCode 색상 팔레트 (Navigator 전경색용 - 진한 색상)
OPCODE_COLORS = {
    EMkMode.TITLE: QColor(0, 100, 200),         # 진한 파란색
    EMkMode.TITLE_H: QColor(0, 100, 200),       # 헤더 타이틀
    EMkMode.TITLE_S: QColor(0, 100, 200),       # 소스 타이틀
    EMkMode.SUBTITLE: QColor(0, 80, 160),       # 더 진한 파란색
    EMkMode.DESCRIPT: QColor(100, 100, 100),    # 회색
    EMkMode.DEFINE: QColor(200, 0, 0),          # 진한 빨간색
    EMkMode.VARIABLE: QColor(0, 150, 0),        # 진한 초록색
    EMkMode.TYPEDEF: QColor(150, 100, 0),       # 진한 갈색
    EMkMode.ENUM: QColor(150, 0, 150),          # 진한 보라색
    EMkMode.ENUM_MEM: QColor(120, 0, 120),      # 더 진한 보라색
    EMkMode.ARRAY: QColor(200, 100, 0),         # 진한 주황색
    EMkMode.ARR_MEM: QColor(180, 90, 0),        # 더 진한 주황색
    EMkMode.STR_MEM: QColor(180, 90, 0),        # 구조체 멤버
    EMkMode.CODE: QColor(100, 100, 100),        # 회색
    EMkMode.PRGM_SET: QColor(150, 0, 150),      # 진한 보라색
    EMkMode.PRGM_END: QColor(150, 0, 150),      # 진한 보라색
    EMkMode.PRJT_DEF: QColor(100, 100, 100),    # 회색
    EMkMode.NONE: QColor(33, 33, 33),           # 기본 검정
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

# OpCode → 아이콘 매핑 (완전한 텍스트 기반 인터페이스)
ICON_MAPPING = {
    # 모든 이모지 제거 - 텍스트만으로 깔끔한 인터페이스
    EMkMode.TITLE: "", EMkMode.TITLE_H: "", EMkMode.TITLE_S: "",
    EMkMode.SUBTITLE: "",  # 필터링됨
    EMkMode.DESCRIPT: "",  # 필터링됨
    EMkMode.DEFINE: "",
    EMkMode.VARIABLE: "",
    EMkMode.ARRAY: "",     # 이모지 제거
    EMkMode.ENUM: "",
    EMkMode.TYPEDEF: "",
    EMkMode.CODE: "",
    EMkMode.PRGM_SET: "",
    EMkMode.PRGM_END: "",
    EMkMode.PRJT_DEF: ""   # 이모지 제거
}

# 네비게이터에 표시할 OpCode들 ($DESCRIPT, $SUBTITLE 제외)
DISPLAY_OPCODES = {
    EMkMode.TITLE, EMkMode.TITLE_H, EMkMode.TITLE_S,
    EMkMode.DEFINE,  # EMkMode.DESCRIPT, EMkMode.SUBTITLE 제거
    EMkMode.VARIABLE, EMkMode.ARRAY, EMkMode.ENUM,
    EMkMode.TYPEDEF, EMkMode.CODE, EMkMode.PRGM_SET,
    EMkMode.PRJT_DEF
}
