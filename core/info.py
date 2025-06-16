from enum import Enum
from typing import Dict, List, Any

# 새로운 중앙 집중식 상수 관리 모듈 import
from core.constants import (
    ApplicationConstants, DatabaseConstants, ExcelConstants,
    CodeGenerationConstants, LegacyConstants
)


class EMkFile(Enum):
    """파일 생성 모드"""
    Src = 0
    Hdr = 1
    All = 2


class EArrType(Enum):
    """배열 타입 정의"""
    SizeErr = 0
    Type1 = 1  # n by n 배열
    Type2 = 2  # 1 by n 배열
    Type3 = 3  # 1 by n 배열 분할
    Type4 = 4  # 1 by n 배열 세로 정렬


class EErrType(Enum):
    """오류 타입 정의"""
    EmptyCell = 0
    OpCode = 1
    ArrRowOver = 2
    ArrRowUnder = 3
    TitleName = 4
    ArrSizeErr = 5
    FileName = 6
    PrgmEmpty = 7
    PrgmKey = 8
    PrjtDefOrder = 9
    ItemName = 10
    PrgmWrite = 11
    PrjtEmpty = 12
    PrjtSame = 13
    PrjtNotSame = 14
    PrjtErr = 15
    FileExist = 16
    FileExtension = 17


class EMkMode(Enum):
    """코드 생성 모드"""
    TITLE = 0
    TITLE_S = 1
    TITLE_H = 2
    SUBTITLE = 3
    DESCRIPT = 4
    DEFINE = 5
    TYPEDEF = 6
    STR_MEM = 7
    STR_DEF = 8
    ENUM = 9
    ENUM_MEM = 10
    ARRAY = 11
    ARR_MEM = 12
    VARIABLE = 13
    CODE = 14
    PRGM_SET = 15
    PRGM_END = 16
    NONE = 17
    ENUM_END = 18
    PRJT_DEF = 19


class Info:
    """
    애플리케이션 정보 및 설정 관리 클래스
    중앙 집중식 상수 관리를 위해 constants 모듈 사용
    """

    # 애플리케이션 정보 (constants 모듈에서 가져오기)
    APP_NAME = ApplicationConstants.APP_NAME
    APP_VERSION = ApplicationConstants.APP_VERSION
    APP_TITLE = ApplicationConstants.APP_TITLE

    # 파일 확장자 상수
    DB_EXTENSION = DatabaseConstants.DB_EXTENSION
    EXCEL_EXTENSIONS = ExcelConstants.EXCEL_EXTENSIONS
    CSV_EXTENSION = ExcelConstants.CSV_EXTENSION
    C_EXTENSION = CodeGenerationConstants.C_SOURCE_EXT
    H_EXTENSION = CodeGenerationConstants.C_HEADER_EXT

    # 기본 파일명 상수
    DEFAULT_DB_NAME = DatabaseConstants.DEFAULT_DB_NAME
    BACKUP_PREFIX = DatabaseConstants.BACKUP_PREFIX
    HISTORY_DIR = DatabaseConstants.HISTORY_DIR
    LOGS_DIR = DatabaseConstants.LOGS_DIR

    # 설정 관련 상수
    SETTINGS_ORG = ApplicationConstants.SETTINGS_ORG
    SETTINGS_APP = ApplicationConstants.SETTINGS_APP
    LAST_DIRECTORY_KEY = ApplicationConstants.LAST_DIRECTORY_KEY

    # 파일 필터 상수
    DB_FILE_FILTER = f"SQLite 데이터베이스 (*{DB_EXTENSION})"
    EXCEL_FILE_FILTER = ExcelConstants.EXCEL_FILE_FILTER
    CSV_FILE_FILTER = ExcelConstants.CSV_FILE_FILTER

    # 🚀 MCU Calibration 데이터베이스 저장소 경로
    MCU_CALIBRATION_DB_DIR = "MCU_Calibration_Database"  # 프로그램 실행 경로 기준

    # UI 텍스트 상수
    EXCEL_TO_DB_MENU_TEXT = "Excel → DB 변환(&I)..."
    EXCEL_TO_DB_STATUS_TIP = "Excel 파일을 SQLite 데이터베이스로 변환합니다 (다중 선택 지원)"
    EXCEL_TO_DB_PROGRESS_TITLE = "Excel to DB Conversion"
    EXCEL_TO_DB_MULTI_PROGRESS_TITLE = "Converting Multiple Excel Files"

    # 하위 호환성을 위한 레거시 상수들 (constants 모듈에서 가져오기)
    MaxFileNum = LegacyConstants.MaxFileNum
    PrjtDefCol = LegacyConstants.PrjtDefCol
    PrjtNameCol = LegacyConstants.PrjtNameCol
    TabSize = LegacyConstants.TabSize

    ReadingDBRule = LegacyConstants.ReadingDBRule
    FileInfoShtName = LegacyConstants.FileInfoShtName
    CommPrjtName = LegacyConstants.CommPrjtName
    ElsePrjtName = LegacyConstants.ElsePrjtName
    EndPrjtName = LegacyConstants.EndPrjtName
    EmptyKey = LegacyConstants.EmptyKey
    
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
        "-------------------------------------------------------------------------------------------*/"
    ]
    
    InterAnnotation = [
        "/*******************************************************************************************/",
        "/*=========================================================================================*/",
        "/*-----------------------------------------------------------------------------------------*/"
    ]
    
    FilePathTitle = "$파일 생성 경로"
    SrcInfoTitle = "$소스(.c) 파일 정보"
    HdrInfoTitle = "$헤더(.h) 파일 정보"
    PrgmInfoTitle = "$Pragma Section 정보"
    XlsInfoTitle = "$엑셀 작성용 리스트"
    
    ErrList: List[str] = []  # 에러리스트 기록용
    FileList: List[str] = []
    MkFileNum = 0
    ErrNameSize = 0
    
    @staticmethod
    def ReadCell(data, row, col):
        """셀 데이터 읽기"""
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
                return ""
        except Exception as ex:
            # print(f"DEBUG: Exception in ReadCell - {str(ex)}")
            return ""
    
    @staticmethod
    def WriteErrMsg(err_msg):
        """에러 메시지 기록"""
        Info.ErrList.append(f"  {err_msg}")
    
    @staticmethod
    def WriteErrCell(err_type, sht_name, row, col):
        """셀 에러 기록"""
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
        
        err_cell_str = f"{Info.ReadingDBRule}{sht_name}[{err_cell_str}{row}]:"
        
        if len(err_cell_str.encode('utf-8')) > Info.ErrNameSize:
            Info.ErrNameSize = len(err_cell_str.encode('utf-8'))
        
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
    def ExistEmptyStr(lst, cnt):
        """이전 라인에 빈줄이 있는지 체크"""
        exist_flag = False
        
        if isinstance(lst, list):
            if len(lst) > 0:
                try:
                    last_str = lst[len(lst) - cnt]
                except:
                    last_str = ""
                
                if last_str == "" or last_str.endswith("\r\n"):
                    exist_flag = True
            elif len(lst) == 0:
                exist_flag = True
        else:  # QListWidget
            if lst.count() > 0:
                last_str = lst.item(lst.count() - cnt).text()
                if last_str == "" or last_str.endswith("\r\n"):
                    exist_flag = True
            elif lst.count() == 0:
                exist_flag = True
        
        return exist_flag

class CellInfos:
    """셀 정보 클래스"""
    def __init__(self, row=0, col=0, str_val=""):
        self.Row = row
        self.Col = col
        self.Str = str_val

class ArrInfos:
    """배열 정보 클래스"""
    def __init__(self):
        self.OrignalSize = SCellPos()
        self.ReadSize = SCellPos()
        self.StartPos = SCellPos()
        self.EndPos = SCellPos()
        
        self.TempArr = []
        self.AlignmentSize = []
        self.AnnotateRow = []
        self.AnnotateCol = []
        
        self.ArrType = 0
        self.RowCnt = 0
        self.IdxOn = False
        self.LineAdd = False
        self.ElementType = ""  # 배열 요소의 타입 정보 저장

class SCellPos:
    """셀 위치 구조체"""
    def __init__(self, row=0, col=0):
        self.Row = row
        self.Col = col

class SPrjtInfo:
    """프로젝트 정보 구조체"""
    def __init__(self, def_val="", val=None):
        self.Def = def_val
        self.Val = val if val is not None else []

class SPragInfo:
    """프라그마 정보 구조체"""
    def __init__(self, pre_code="", class_name="", set_istring="", set_ustring="", 
                 set_addr_mode="", end_istring="", end_ustring="", end_code=""):
        self.PreCode = pre_code
        self.ClassName = class_name
        self.SetIstring = set_istring
        self.SetUstring = set_ustring
        self.SetAddrMode = set_addr_mode
        self.EndIstring = end_istring
        self.EndUstring = end_ustring
        self.EndCode = end_code

class SShtInfo:
    """시트 정보 구조체"""
    def __init__(self, name="", data=None):
        self.Name = name
        self.Data = data if data is not None else []