"""
애플리케이션 전반에서 사용되는 열거형(Enum), 데이터 구조 클래스,
그리고 전역 상수 및 유틸리티 함수를 정의하는 모듈입니다.

주요 내용:
- EMkFile, EArrType, EErrType, EMkMode: 코드 생성 및 오류 처리 시 사용되는 열거형.
- Info: 전역 상수 및 정적 유틸리티 함수들을 제공하는 클래스.
- CellInfos, ArrInfos, SCellPos, SPrjtInfo, SPragInfo, SShtInfo: 특정 데이터를 구조화하기 위한 데이터 클래스.
"""
from enum import Enum
from typing import Dict, List, Any


class EMkFile(Enum):
    """생성할 파일의 종류를 나타내는 열거형입니다."""
    Src = 0  # 소스 파일 (.c)
    Hdr = 1  # 헤더 파일 (.h)
    All = 2  # 소스 및 헤더 파일 모두


class EArrType(Enum):
    """배열의 구조 및 데이터 배치 유형을 나타내는 열거형입니다."""
    SizeErr = 0     # 배열 크기 정보 오류
    Type1 = 1       # n x m 형태의 일반 배열 (데이터가 행 우선 배치)
    Type2 = 2       # 1 x n 형태의 배열 (데이터가 단일 행에 배치)
    Type3 = 3       # 1 x n 형태의 배열 (데이터가 여러 줄에 걸쳐 분할 배치)
    Type4 = 4       # n x 1 형태의 배열 (데이터가 단일 열에 세로로 배치)


class EErrType(Enum):
    """코드 생성 또는 데이터 파싱 중 발생할 수 있는 오류 유형을 정의하는 열거형입니다."""
    EmptyCell = 0    # 셀 내용이 비어있음
    OpCode = 1       # 잘못된 OpCode
    ArrRowOver = 2   # 배열 행 크기 초과
    ArrRowUnder = 3  # 배열 행 크기 부족
    TitleName = 4    # 타이틀 이름 중복 또는 오류
    ArrSizeErr = 5   # 배열 크기 정의 오류
    FileName = 6     # 파일 이름 관련 오류
    PrgmEmpty = 7    # 프라그마 정보 누락
    PrgmKey = 8      # 프라그마 키 오류
    PrjtDefOrder = 9 # 프로젝트 정의 순서 오류
    ItemName = 10    # 아이템 이름 오류
    PrgmWrite = 11   # 프라그마 작성 오류
    PrjtEmpty = 12   # 프로젝트 정보 누락
    PrjtSame = 13    # 프로젝트 이름 중복
    PrjtNotSame = 14 # 프로젝트 정의 불일치
    PrjtErr = 15     # 기타 프로젝트 관련 오류
    FileExist = 16   # 파일이 이미 존재함
    FileExtension = 17 # 잘못된 파일 확장자


class EMkMode(Enum):
    """코드 생성 시 현재 처리 중인 아이템의 종류 또는 모드를 나타내는 열거형입니다."""
    TITLE = 0        # 일반 타이틀
    TITLE_S = 1      # 소스 파일 전용 타이틀
    TITLE_H = 2      # 헤더 파일 전용 타이틀
    SUBTITLE = 3     # 서브 타이틀
    DESCRIPT = 4     # 설명
    DEFINE = 5       # 매크로 정의 (#define)
    TYPEDEF = 6      # 타입 정의 (typedef struct)
    STR_MEM = 7      # 구조체 멤버
    STR_DEF = 8      # 구조체 정의 완료
    ENUM = 9         # 열거형 정의 시작
    ENUM_MEM = 10    # 열거형 멤버
    ARRAY = 11       # 배열 정의 시작
    ARR_MEM = 12     # 배열 멤버 (내용)
    VARIABLE = 13    # 일반 변수
    CODE = 14        # 직접 코드 삽입
    PRGM_SET = 15    # 프라그마 섹션 시작
    PRGM_END = 16    # 프라그마 섹션 종료
    NONE = 17        # 정의되지 않은 모드 또는 빈 줄
    ENUM_END = 18    # 열거형 정의 완료
    PRJT_DEF = 19    # 프로젝트 정의 시작/종료


class Info:
    """
    애플리케이션 전반에 사용되는 전역 상수 및 정적 유틸리티 함수를 제공하는 클래스입니다.

    이 클래스는 인스턴스화되지 않으며, 모든 멤버는 정적(static)으로 접근합니다.
    주로 코드 생성 규칙, 파일 정보, UI 텍스트, 오류 메시지 형식 등에 관련된
    상수들을 정의하고, 셀 데이터 읽기, 오류 메시지 기록 등의 유틸리티 함수를 포함합니다.
    """

    # 애플리케이션 정보
    APP_NAME = "AutoCalEditor"
    APP_VERSION = "2.2"  # 메이저.마이너.패치 형식 권장
    APP_TITLE = f"{APP_NAME} v{APP_VERSION}"

    # 파일 확장자 상수
    DB_EXTENSION = ".db"
    EXCEL_EXTENSIONS = (".xlsx", ".xls")
    CSV_EXTENSION = ".csv"
    C_EXTENSION = ".c"
    H_EXTENSION = ".h"

    # 기본 파일명 상수
    DEFAULT_DB_NAME = "cal_database"
    BACKUP_PREFIX = "backup"
    HISTORY_DIR = "history"
    LOGS_DIR = "logs"

    # 설정 관련 상수
    SETTINGS_ORG = "AutoCalEditor"
    SETTINGS_APP = "AutoCalEditor"
    LAST_DIRECTORY_KEY = "last_directory"

    # 파일 필터 상수
    DB_FILE_FILTER = f"SQLite 데이터베이스 (*{DB_EXTENSION})"
    EXCEL_FILE_FILTER = f"Excel 파일 (*{EXCEL_EXTENSIONS[0]} *{EXCEL_EXTENSIONS[1]})"
    CSV_FILE_FILTER = f"CSV 파일 (*{CSV_EXTENSION})"

    # UI 텍스트 상수
    EXCEL_TO_DB_MENU_TEXT = "Excel → DB 변환(&I)..."
    EXCEL_TO_DB_STATUS_TIP = (
        "Excel 파일을 SQLite 데이터베이스로 변환합니다 (다중 선택 지원)"
    )
    EXCEL_TO_DB_PROGRESS_TITLE = "Excel to DB Conversion"
    EXCEL_TO_DB_MULTI_PROGRESS_TITLE = "Converting Multiple Excel Files"

    MaxFileNum = 10  # 최대 파일 생성 갯수
    PrjtDefCol = 2  # 프로젝트/단계 define 명 col 위치(프로젝트명 + PrjtDefCol)
    PrjtNameCol = 5  # 프로젝트/단계 define 명 col 위치(프로젝트명 + PrjtNameCol)
    TabSize = 4

    ReadingXlsRule = "$"  # 엑셀 read 규칙 기호
    FileInfoShtName = "FileInfo"  # 시트명(파일정보) 규칙
    CommPrjtName = "COMMON"
    ElsePrjtName = "DEFAULT"
    EndPrjtName = "END"
    EmptyKey = "Empty"  # 배열이나 변수 정의 시 Keyword 누락을 오류로 인식안하기 위함

    # OpCode 정보
    dOpCode = {
        "$TITLE": EMkMode.TITLE,
        "$TITLE_S": EMkMode.TITLE_S,
        "$TITLE_H": EMkMode.TITLE_H,
        "$SUBTITLE": EMkMode.SUBTITLE,
        "$DESCRIPT": EMkMode.DESCRIPT,
        "$DEFINE": EMkMode.DEFINE,
        "$TYPEDEF": EMkMode.TYPEDEF,
        "$STR_MEM": EMkMode.STR_MEM,
        "$STR_DEF": EMkMode.STR_DEF,
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

    StartAnnotation = [
        "/********************************************************************************************",
        "/*===========================================================================================",
        "/*-------------------------------------------------------------------------------------------",
    ]

    EndAnnotation = [
        "********************************************************************************************/",
        "===========================================================================================*/",
        "-------------------------------------------------------------------------------------------*/",
    ]

    InterAnnotation = [
        "/*******************************************************************************************/",
        "/*=========================================================================================*/",
        "/*-----------------------------------------------------------------------------------------*/",
    ]

    FilePathTitle = "$파일 생성 경로"
    SrcInfoTitle = "$소스(.c) 파일 정보"
    HdrInfoTitle = "$헤더(.h) 파일 정보"
    PrgmInfoTitle = "$Pragma Section 정보"
    XlsInfoTitle = "$엑셀 작성용 리스트"

    ErrList: List[str] = []  # 에러리스트 기록용
    FileList: List[str] = []
    MkFileNum = 0
    ErrNameSize = 0 # 오류 메시지 포맷팅 시 사용되는 이름 부분의 최대 크기

    @staticmethod
    def ReadCell(data: List[List[Any]], row: int, col: int) -> str:
        """
        주어진 2차원 리스트(data)에서 특정 행(row)과 열(col)에 위치한 셀의 데이터를 읽어 문자열로 반환합니다.

        셀 값이 None이면 빈 문자열을 반환하고, 숫자(int, float)인 경우 문자열로 변환하여 반환합니다.
        인덱스가 범위를 벗어나면 빈 문자열을 반환합니다.

        Args:
            data (List[List[Any]]): 셀 데이터를 담고 있는 2차원 리스트.
            row (int): 읽어올 셀의 행 인덱스.
            col (int): 읽어올 셀의 열 인덱스.

        Returns:
            str: 공백이 제거된 셀 데이터 문자열. 유효하지 않은 경우 빈 문자열.
        """
        try:
            # 인덱스 범위 체크
            if row < len(data) and col < len(data[row]):
                cell_value = data[row][col]
                # None 값 처리
                if cell_value is None:
                    return ""
                # 숫자 값을 문자열로 변환
                if isinstance(cell_value, (int, float)):
                    return str(cell_value).strip()
                # 문자열 값 처리
                return str(cell_value).strip()
            else:
                return "" # 인덱스 범위를 벗어나면 빈 문자열 반환
        except Exception as ex:
            # 예외 발생 시 로깅을 고려할 수 있으나, 현재는 빈 문자열 반환 유지
            # logging.warning(f"ReadCell 중 예외 발생: data={data}, row={row}, col={col}, error={ex}")
            return ""

    @staticmethod
    def WriteErrMsg(err_msg: str):
        """
        전역 에러 리스트(`Info.ErrList`)에 주어진 에러 메시지를 추가합니다.

        메시지 앞에는 두 칸의 공백이 추가됩니다.

        Args:
            err_msg (str): 기록할 에러 메시지.
        """
        Info.ErrList.append(f"  {err_msg}")

    @staticmethod
    def WriteErrCell(err_type: EErrType, sht_name: str, row: int, col: int):
        """
        지정된 오류 유형과 셀 위치 정보를 바탕으로 포맷된 오류 메시지를 생성하여
        전역 에러 리스트(`Info.ErrList`)에 추가합니다.

        셀 위치는 "SheetName[A1]:"과 같은 형태로 변환됩니다.
        오류 메시지 포맷팅 시 이름 부분의 최대 길이를 `Info.ErrNameSize`를 통해 관리합니다.

        Args:
            err_type (EErrType): 발생한 오류의 유형 (Enum 값).
            sht_name (str): 오류가 발생한 시트의 이름.
            row (int): 오류가 발생한 셀의 행 번호 (1부터 시작하는 Excel 기준).
            col (int): 오류가 발생한 셀의 열 번호 (1부터 시작하는 Excel 기준).
        """
        err_str = ""
        err_cell_str = ""

        if col % 26 == 0:
            err_cell_str = "Z"
        else:
            err_cell_str = chr(col % 26 + 64)

        if col > 26 and col // 26 != 0:
            temp = col // 26
            if col % 26 == 0:
                temp -= 1

            err_cell_str = chr(temp + 64) + err_cell_str

        err_cell_str = f"{Info.ReadingXlsRule}{sht_name}[{err_cell_str}{row}]:"

        if len(err_cell_str.encode("utf-8")) > Info.ErrNameSize:
            Info.ErrNameSize = len(err_cell_str.encode("utf-8"))

        if err_type == EErrType.EmptyCell:
            err_str = "셀 내용 미기입"
        elif err_type == EErrType.OpCode:
            err_str = "OpCode 기입 오류"
        elif err_type == EErrType.ItemName:
            err_str = "아이템 항목 기입 오류"
        elif err_type == EErrType.TitleName:
            err_str = "한 시트에서 Title명 중복 사용"
        elif err_type == EErrType.ArrSizeErr:
            err_str = "배열 사이즈 기입 오류"
        elif err_type == EErrType.ArrRowOver:
            err_str = "배열 사이즈 기입 오류(행 초과)"
        elif err_type == EErrType.ArrRowUnder:
            err_str = "배열 사이즈 기입 오류(행 부족)"
        elif err_type == EErrType.PrgmEmpty:
            err_str = "Pragma section 정보 미기입"
        elif err_type == EErrType.PrgmWrite:
            err_str = "Pragma section 정보 기입 오류(SET, END 사용 오류)"
        elif err_type == EErrType.PrgmKey:
            err_str = "Pragma section 정보 기입 오류(Keyword명 중복)"
        elif err_type == EErrType.PrjtEmpty:
            err_str = "프로젝트/단계 정보 미기입"
        elif err_type == EErrType.PrjtSame:
            err_str = "프로젝트/단계 정보 기입 오류(동일한 명칭)"
        elif err_type == EErrType.PrjtNotSame:
            err_str = "프로젝트/단계 정보 기입 오류(상이한 define명)"
        elif err_type == EErrType.PrjtErr:
            err_str = "프로젝트/단계 정보 기입 오류(DEFAULT, END 사용 오류)"
        elif err_type == EErrType.PrjtDefOrder:
            err_str = "프로젝트/단계 정보의 순서 오류(COMMON->...->DEFAULT 순으로 기입)"
        elif err_type == EErrType.FileName:
            err_str = "생성 파일명 기입 오류(소스/헤더 파일명 불일치)"
        elif err_type == EErrType.FileExist:
            err_str = "생성 파일명 기입 오류(이미 정의된 파일명)"
        elif err_type == EErrType.FileExtension:
            err_str = "생성 파일명 기입 오류(*.c/*.h 확장자)"
        else:
            err_str = ""

        Info.ErrList.append(f"  {err_cell_str}{err_str}")

    @staticmethod
    def ExistEmptyStr(lst: List[str], cnt: int) -> bool:
        """
        주어진 리스트(`lst`)의 끝에서 `cnt` 번째 항목이 비어 있거나 개행 문자로 끝나는지 확인합니다.

        주로 코드 생성 시 연속된 빈 줄을 방지하기 위해 사용됩니다.

        Args:
            lst (List[str]): 검사할 문자열 리스트.
            cnt (int): 리스트의 끝에서부터 검사할 항목의 위치 (1은 마지막 항목, 2는 마지막에서 두 번째 항목 등).

        Returns:
            bool: 해당 항목이 비어 있거나 개행으로 끝나면 True, 그렇지 않으면 False.
                  리스트가 비어 있거나 항목이 충분하지 않은 경우에도 True를 반환할 수 있습니다.
        """
        exist_flag = False

        if isinstance(lst, list):
            if len(lst) > 0:
                try:
                    # Ensure cnt is positive and within bounds
                    if cnt <= 0 or cnt > len(lst):
                        # If cnt is invalid, default to checking the very last element or consider it as not empty.
                        # For safety, let's assume it means "not an empty line" if cnt is out of typical use.
                        # Or, more strictly, this case might indicate an issue with the caller.
                        # For now, let's check the last valid element if cnt is too large.
                        actual_cnt = min(cnt, len(lst))
                        last_str = lst[len(lst) - actual_cnt]

                    else:
                        last_str = lst[len(lst) - cnt]
                except IndexError: # Should be rare if logic above is correct
                    last_str = ""

                if last_str == "" or last_str.endswith("\r\n"):
                    exist_flag = True
            elif len(lst) == 0: # Empty list implies an "empty string" at the end for formatting purposes
                exist_flag = True
        # else:  # QListWidget - This part is no longer relevant as UI dependencies were removed.
        #     if lst.count() > 0:
        #         if cnt <= lst.count(): # Check if item exists
        #             last_str = lst.item(lst.count() - cnt).text()
        #             if last_str == "" or last_str.endswith("\r\n"):
        #                 exist_flag = True
        #         else: # cnt is out of bounds
        #             exist_flag = True # Treat as if an empty line exists for safety
        #     elif lst.count() == 0:
        #         exist_flag = True

        return exist_flag


class CellInfos:
    """
    셀의 위치(행, 열)와 해당 셀의 문자열 값을 저장하는 데이터 클래스입니다.

    Attributes:
        Row (int): 셀의 행 인덱스.
        Col (int): 셀의 열 인덱스.
        Str (str): 셀의 문자열 값.
    """

    def __init__(self, row: int = 0, col: int = 0, str_val: str = ""):
        self.Row = row
        self.Col = col
        self.Str = str_val


class ArrInfos:
    """
    배열 코드 생성에 필요한 다양한 정보를 저장하는 데이터 클래스입니다.

    Attributes:
        OrignalSize (SCellPos): Excel 시트에 정의된 배열의 원본 크기 (행, 열).
        ReadSize (SCellPos): 실제로 읽어야 할 배열 데이터의 크기 (주석 등을 포함할 수 있음).
        StartPos (SCellPos): 시트에서 배열 데이터가 시작되는 셀의 위치.
        EndPos (SCellPos): 시트에서 배열 데이터가 끝나는 셀의 위치.
        TempArr (List[List[str]]): 시트에서 읽어온 배열 데이터를 임시로 저장하는 2차원 리스트.
        AlignmentSize (List[int]): 각 열의 정렬을 위한 최대 너비 정보.
        AnnotateRow (List[int]): 주석으로 처리될 행의 인덱스 목록.
        AnnotateCol (List[int]): 주석으로 처리될 열의 인덱스 목록.
        ArrType (int): 배열의 타입 (EArrType 값).
        RowCnt (int): 현재 처리 중인 배열의 행 카운터 (주로 writeArrMem에서 사용).
        IdxOn (bool): 배열 인덱스 라인(예: "Idx") 존재 여부.
        LineAdd (bool): 추가 라인 생성 여부 (사용처 확인 필요).
        ElementType (str): 배열 요소의 C 데이터 타입 문자열 (예: "FLOAT32").
    """

    def __init__(self):
        self.OrignalSize = SCellPos()
        self.ReadSize = SCellPos()
        self.StartPos = SCellPos()
        self.EndPos = SCellPos()

        self.TempArr: List[List[str]] = []
        self.AlignmentSize: List[int] = []
        self.AnnotateRow: List[int] = []
        self.AnnotateCol: List[int] = []

        self.ArrType: int = 0 # EArrType value
        self.RowCnt: int = 0
        self.IdxOn: bool = False
        self.LineAdd: bool = False # This flag's usage needs to be clear from context.
        self.ElementType: str = ""  # 배열 요소의 타입 정보 저장


class SCellPos:
    """
    셀의 2차원 위치(행, 열)를 나타내는 간단한 데이터 클래스입니다.

    Attributes:
        Row (int): 행 번호.
        Col (int): 열 번호.
    """

    def __init__(self, row: int = 0, col: int = 0):
        self.Row = row
        self.Col = col


class SPrjtInfo:
    """
    프로젝트/단계별 조건부 컴파일 정보를 저장하는 데이터 클래스입니다.

    Attributes:
        Def (str): 프로젝트/단계 정의 매크로 이름 (예: "PROJECT_A_ENABLED").
        Val (List[str]): 해당 정의 매크로에 대한 값 목록 (예: ["FEATURE_X", "FEATURE_Y"]).
    """

    def __init__(self, def_val: str = "", val: Optional[List[str]] = None):
        self.Def = def_val
        self.Val = val if val is not None else []


class SPragInfo:
    """
    프라그마 섹션 정보를 저장하는 데이터 클래스입니다.

    Attributes:
        PreCode (str): 프라그마 섹션 앞에 위치할 코드.
        ClassName (str): 프라그마 섹션의 클래스 이름.
        SetIstring (str): 설정(SET) 시 사용될 Istring.
        SetUstring (str): 설정(SET) 시 사용될 Ustring.
        SetAddrMode (str): 설정(SET) 시 사용될 주소 모드.
        EndIstring (str): 종료(END) 시 사용될 Istring.
        EndUstring (str): 종료(END) 시 사용될 Ustring.
        EndCode (str): 프라그마 섹션 뒤에 위치할 코드.
    """

    def __init__(
        self,
        pre_code: str = "",
        class_name: str = "",
        set_istring: str = "",
        set_ustring: str = "",
        set_addr_mode: str = "",
        end_istring: str = "",
        end_ustring: str = "",
        end_code: str = "",
    ):
        self.PreCode = pre_code
        self.ClassName = class_name
        self.SetIstring = set_istring
        self.SetUstring = set_ustring
        self.SetAddrMode = set_addr_mode
        self.EndIstring = end_istring
        self.EndUstring = end_ustring
        self.EndCode = end_code


class SShtInfo:
    """
    Excel 시트의 이름과 데이터(셀 값들의 2차원 리스트)를 저장하는 데이터 클래스입니다.

    Attributes:
        Name (str): 시트의 이름.
        Data (List[List[Any]]): 시트의 셀 데이터를 담고 있는 2차원 리스트.
                                 `None`으로 초기화될 수 있으며, 실제 데이터가 할당됩니다.
    """

    def __init__(self, name: str = "", data: Optional[List[List[Any]]] = None):
        self.Name = name
        self.Data = data if data is not None else []
