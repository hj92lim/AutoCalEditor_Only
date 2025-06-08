import datetime
import logging
import os
import sys
import time  # Moved from local imports
from typing import Callable, Dict, List, Optional, Tuple


# Third-party libraries (attempt import, handle if not present)
try:
    import psutil

    MEMORY_MONITORING_AVAILABLE = True
except ImportError:
    psutil = None  # Ensure psutil is defined for checks later, even if not available
    MEMORY_MONITORING_AVAILABLE = False
    # logging.warning("psutil 모듈이 설치되지 않아 메모리 모니터링을 사용할 수 없습니다.") # Consider moving to app init

# Local application/library specific imports
from code_generator.cal_list import CalList
from code_generator.file_info import FileInfo
from core.info import CellInfos, EErrType, EMkFile, EMkMode, Info

# Constants
HYUNDAI_COPYRIGHT = "*                             (C) by Hyundai Motor Company LTD.                             *"
MAX_MEMORY_MB = 2048
MAX_PROCESSING_TIME_SEC = 1800
DEFAULT_ERR_MSG_LEFT_ALIGN = 20
DEFAULT_HEADER_GUARD = "_DEFAULT_HEADER_GUARD_" # Defined in previous step, ensure consistency


# Cython 최적화 함수들을 필요할 때 동적으로 import (안전한 방식)
def safe_import_cython_function(module_name, function_name):
    """
    Cython으로 컴파일된 함수를 안전하게 import하는 헬퍼 함수입니다.
    Cython 확장이 빌드되지 않았거나 특정 함수를 찾을 수 없는 경우 None을 반환하여
    Python 폴백 로직을 사용할 수 있도록 합니다.

    Args:
        module_name (str): import할 Cython 모듈의 이름 (예: "excel_processor_v2").
                           "cython_extensions." 접두사는 자동으로 추가됩니다.
        function_name (str): 모듈 내에서 가져올 함수의 이름.

    Returns:
        Optional[Callable]: import에 성공하면 해당 함수 객체, 실패하면 None.
    """
    try:
        # cython_extensions 경로 추가
        if not module_name.startswith("cython_extensions."):
            module_name = f"cython_extensions.{module_name}"
        module = __import__(module_name, fromlist=[function_name])
        return getattr(module, function_name)
    except (ImportError, AttributeError) as e:
        logging.debug(f"Cython 함수 '{module_name}.{function_name}' 로드 실패: {e}")
        return None


# 로그 설정은 main.py에서 통합 관리됨


# 예외 처리를 위한 전역 핸들러 설정
def global_exception_handler(exc_type, exc_value, exc_traceback):
    """
    처리되지 않은 모든 예외를 로깅하기 위한 전역 예외 핸들러입니다.
    심각한 오류 발생 시 사용자에게 알리고, 상세 내용은 로그 파일에 기록됩니다.
    """
    logging.error("예외가 발생했습니다:", exc_info=(exc_type, exc_value, exc_traceback))
    logging.critical(
        f"처리되지 않은 심각한 오류 발생: {exc_value}. 스택 트레이스를 확인하십시오."
    )


sys.excepthook = global_exception_handler


class MakeCode:
    """
    Excel 파일로부터 데이터를 읽어 C 소스(.c) 및 헤더(.h) 파일을 생성하는 핵심 로직을 담당하는 클래스입니다.

    이 클래스는 UI 의존성을 제거하고, `FileInfo` 객체와 `CalList` 객체 리스트를 사용하여
    코드 생성 과정을 관리합니다. 생성된 코드 라인들은 내부 버퍼(`src_lines`, `hdr_lines`)에 저장됩니다.

    주요 기능:
    - Excel 시트 정보 유효성 검사 (`ChkShtInfo`, `chk_prjt_infos`).
    - Excel 데이터 읽기 및 파싱 위임 (`ReadXlstoCode`가 `CalList.ReadCalList` 호출).
    - 코드 생성 파이프라인 관리 (`ConvXlstoCode`가 각종 `make_*_code` 메소드 호출).
    - 생성된 코드 라인 반환.

    Attributes:
        of (Any): 처리할 Excel 파일 정보를 담고 있는 객체 (일반적으로 openpyxl Workbook 객체 또는 유사 인터페이스).
        src_lines (List[str]): 생성된 소스 코드 라인들을 저장하는 리스트.
        hdr_lines (List[str]): 생성된 헤더 코드 라인들을 저장하는 리스트.
        dFileInfo (Dict[str, CellInfos]): "FileInfo" 시트에서 읽어온 파일 메타데이터.
        titleList (Dict[str, int]): 코드 블록 타이틀과 해당 코드가 생성될 파일 유형(EMkFile) 매핑.
        PrjtList (List[str]): 처리된 프로젝트/단계 이름 목록.
        fi (Optional[FileInfo]): `FileInfo` 객체 인스턴스.
        cl (List[CalList]): 각 CAL 시트를 처리하는 `CalList` 객체의 리스트.
        ScrFileName (str): 생성될 소스 파일의 이름.
        HdrFileName (str): 생성될 헤더 파일의 이름.
        MkFilePath (str): 코드 파일이 생성될 기본 경로.
        prjt_def_title (str): 프로젝트 정의에 사용되는 주 매크로 이름 (예: "PRJT_STEP_DEF").
    """

    def __init__(self, of: Any):
        """
        MakeCode 객체를 초기화합니다.

        Args:
            of (Any): 처리할 Excel 파일 정보를 담고 있는 객체.
                      openpyxl Workbook 객체 또는 `FileInfoSht` (단일 시트) 및
                      `CalListSht` (시트 리스트) 속성을 포함해야 합니다.
        """
        self.of = of
        self.src_lines: List[str] = []
        self.hdr_lines: List[str] = []

        self.dFileInfo: Dict[str, CellInfos] = {}
        self.titleList: Dict[str, int] = {} # EMkFile enum 값 저장
        self.PrjtList: List[str] = []

        self.fi: Optional[FileInfo] = None
        self.cl: List[CalList] = []

        self.ScrFileName: str = ""
        self.HdrFileName: str = ""
        self.MkFilePath: str = ""
        self.prjt_def_title: str = ""

    def ChkShtInfo(self) -> bool:
        """
        Excel 파일의 "FileInfo" 시트와 각 CAL 목록 시트 정보의 유효성을 검사합니다.

        `FileInfo` 객체를 생성하여 파일 메타데이터를 읽고, 각 CAL 시트에 대해
        `CalList` 객체를 생성하여 기본 구조(항목 위치, 프로젝트 정의 등)를 확인합니다.
        오류 발생 시 `Info.ErrList`에 오류 메시지가 기록됩니다.

        Returns:
            bool: 모든 시트 정보가 유효하면 False, 오류가 하나라도 있으면 True를 반환합니다.
        """
        err_ret = False
        err_cnt = 0

        if not hasattr(self.of, "FileInfoSht"):
            logging.error("MakeCode.ChkShtInfo: 'of' 객체에 'FileInfoSht' 속성이 없습니다. FileInfo 처리 불가.")
            return True
        if not hasattr(self.of, "CalListSht"):
            logging.error("MakeCode.ChkShtInfo: 'of' 객체에 'CalListSht' 속성이 없습니다. CalList 처리 불가.")
            return True

        self.dFileInfo = {}
        self.fi = FileInfo(self.of.FileInfoSht, self.dFileInfo)

        if self.fi.Read():
            logging.error(f"MakeCode.ChkShtInfo: FileInfo.Read() 처리 중 오류 발생. FileInfo 시트: {getattr(self.of.FileInfoSht, 'name', '알 수 없음')}")
            err_cnt += 1
            err_ret = True
        else:
            self.ScrFileName = self.dFileInfo.get("S_FILE", CellInfos(Str="default.c")).Str
            self.HdrFileName = self.dFileInfo.get("H_FILE", CellInfos(Str="default.h")).Str
            self.MkFilePath = self.fi.MkFilePath if self.fi else ""

        self.titleList = {}
        self.cl = []

        if not err_ret:
            cal_list_sheets = self.of.CalListSht if isinstance(self.of.CalListSht, list) else []
            if not cal_list_sheets:
                 logging.warning("MakeCode.ChkShtInfo: self.of.CalListSht가 비어있거나 유효한 리스트가 아닙니다.")

            for idx, cal_list_sheet_data in enumerate(cal_list_sheets):
                if self.fi is None: # FileInfo 로드 실패 시 더 이상 진행 불가
                    logging.error("MakeCode.ChkShtInfo: FileInfo 객체(self.fi)가 초기화되지 않아 CalList 처리를 중단합니다.")
                    err_ret = True; break

                cal_item = CalList(self.fi, self.titleList, cal_list_sheet_data)
                if cal_item.ChkCalListPos():
                    sheet_name_attr = getattr(cal_list_sheet_data, 'name', f"인덱스 {idx}")
                    logging.error(f"MakeCode.ChkShtInfo: CalList.ChkCalListPos() 처리 중 오류 발생. CalList 시트: {sheet_name_attr}")
                    err_cnt += 1; err_ret = True; break
                self.cl.append(cal_item)

        if not err_ret and self.chk_prjt_infos():
            err_ret = True

        if err_ret:
            logging.info(f"ChkShtInfo 최종 실패: 총 {err_cnt}개의 주요 오류 지점 발견. 객체 상태를 초기화합니다.")
            self.fi = None; self.cl = []
            return True
        return False

    def chk_prjt_infos(self) -> bool:
        """
        여러 `CalList` 시트 간의 프로젝트/단계 정의 정보의 일관성을 검사합니다.

        - 모든 시트의 프로젝트 정의 매크로 이름(`prjt_def_title`)이 동일한지 확인합니다.
        - 프로젝트/단계 이름이 비어있거나 중복되는지 확인합니다.
        - "COMMON" 및 "DEFAULT" 프로젝트의 순서 규칙을 확인합니다.
        오류 발생 시 `Info.ErrList`에 오류 메시지가 기록됩니다.

        Returns:
            bool: 모든 프로젝트 정보가 유효하면 False, 오류가 있으면 True.
        """
        err_flag = False
        self.PrjtList = [] # chk_prjt_infos 호출 시 PrjtList 초기화

        for i, cal_list_item in enumerate(self.cl):
            sht_name = cal_list_item.ShtName
            prjt_def = cal_list_item.PrjtDefMain
            prjt_name = cal_list_item.PrjtNameMain

            prjt_row = cal_list_item.PrjtStartPos.Row
            prjt_def_col = cal_list_item.PrjtStartPos.Col + Info.PrjtDefCol
            prjt_name_col = cal_list_item.PrjtStartPos.Col + Info.PrjtNameCol

            if i == 0: self.prjt_def_title = prjt_def

            current_sheet_err = False
            if len(self.cl) > 1 and not prjt_def:
                Info.WriteErrCell(EErrType.PrjtEmpty, sht_name, prjt_row, prjt_def_col); current_sheet_err = True
            elif i > 0 and self.prjt_def_title != prjt_def:
                Info.WriteErrCell(EErrType.PrjtNotSame, sht_name, prjt_row, prjt_def_col); current_sheet_err = True

            if len(self.cl) > 1 and not prjt_name:
                Info.WriteErrCell(EErrType.PrjtEmpty, sht_name, prjt_row, prjt_name_col); current_sheet_err = True
            # 중복 검사: 첫 번째 non-common 프로젝트부터, 이전 유효한 시트에서 추가된 PrjtList와 비교
            elif i > 0 and prjt_name and prjt_name in self.PrjtList:
                Info.WriteErrCell(EErrType.PrjtSame, sht_name, prjt_row, prjt_name_col); current_sheet_err = True

            if current_sheet_err:
                err_flag = True
                self.PrjtList.append(f"ERROR_ENTRY_FOR_{sht_name}")
            else:
                 self.PrjtList.append(prjt_name)

        if not err_flag and self.PrjtList:
            if Info.CommPrjtName in self.PrjtList and self.PrjtList[0] != Info.CommPrjtName: err_flag = True
            if Info.ElsePrjtName in self.PrjtList and self.PrjtList[-1] != Info.ElsePrjtName: err_flag = True

            if err_flag and self.cl:
                first_cal_item = self.cl[0]
                Info.WriteErrCell(EErrType.PrjtDefOrder, first_cal_item.ShtName,
                                first_cal_item.PrjtStartPos.Row,
                                first_cal_item.PrjtStartPos.Col + Info.PrjtNameCol)
        return err_flag

    def ReadXlstoCode(self, progress_callback: Optional[Callable] = None) -> None:
        """
        Excel 파일의 각 CAL 시트를 읽고 파싱하여 코드 생성 준비를 합니다.

        `ChkShtInfo`가 먼저 성공적으로 호출되어야 합니다. 각 `CalList` 객체의
        `ReadCalList` 메소드를 호출하여 시트 데이터를 처리합니다.
        메모리 사용량 및 처리 시간 제한을 모니터링합니다.

        Args:
            progress_callback (Optional[Callable]): 진행 상태 보고용 콜백 함수.

        Raises:
            RuntimeError: 시트 정보가 초기화되지 않았거나 처리 중 오류 발생 시.
            MemoryError: 메모리 사용량 제한 초과 시.
            TimeoutError: 처리 시간 제한 초과 시.
        """
        if not MEMORY_MONITORING_AVAILABLE:
            logging.warning("psutil 모듈이 설치되지 않아 메모리 모니터링을 사용할 수 없습니다. (ReadXlstoCode)")

        if not self.cl: # self.cl이 비어있으면 ChkShtInfo 실패 또는 데이터 없음
            error_msg = "CalList 시트 정보가 준비되지 않았습니다. ChkShtInfo()를 먼저 성공적으로 호출해야 합니다."
            logging.error(error_msg)
            raise RuntimeError(error_msg)

        logging.info(f"ReadXlstoCode 시작: 처리할 시트 수 = {len(self.cl)}")
        start_time = time.time()
        process = psutil.Process(os.getpid()) if MEMORY_MONITORING_AVAILABLE and psutil else None
        initial_memory = process.memory_info().rss / (1024*1024) if process else 0

        # PrjtList는 chk_prjt_infos에서 채워지므로 여기서는 사용 준비만.

        for i, current_cal_item in enumerate(self.cl):
            sheet_display_name = current_cal_item.ShtName if current_cal_item.ShtName else f"인덱스 {i}"
            if progress_callback:
                progress = int(((i + 1) / len(self.cl)) * 50)
                try:
                    elapsed = time.time() - start_time
                    progress_callback(progress, f"시트 처리 중: {sheet_display_name} ({i+1}/{len(self.cl)}) - {elapsed:.1f}초 경과")
                except InterruptedError as e:
                    logging.info(f"사용자가 코드 생성을 취소했습니다 (콜백 중단): {e}")
                    raise
                except Exception as cb_e:
                    logging.warning(f"Progress callback 실행 중 예외 발생 (시트 처리 중): {cb_e}", exc_info=True)

            logging.info(f"시트 {i+1}/{len(self.cl)} 처리 중: {sheet_display_name}")

            if process: # 메모리 모니터링
                current_memory = process.memory_info().rss / (1024*1024)
                if current_memory > MAX_MEMORY_MB:
                    logging.warning(f"메모리 사용량 초과: {current_memory:.1f}MB (제한: {MAX_MEMORY_MB}MB)")
                    raise MemoryError(f"메모리 사용량이 {MAX_MEMORY_MB}MB를 초과했습니다. 현재: {current_memory:.1f}MB")

            elapsed_time = time.time() - start_time # 타임아웃 체크
            if elapsed_time > MAX_PROCESSING_TIME_SEC:
                logging.warning(f"ReadXlstoCode 타임아웃: {elapsed_time:.1f}초 경과 (제한: {MAX_PROCESSING_TIME_SEC}초)")
                raise TimeoutError(f"코드 생성이 {MAX_PROCESSING_TIME_SEC // 60}분을 초과했습니다.")

            try:
                current_cal_item.ReadCalList(progress_callback) # CalList 객체의 ReadCalList 호출
                if progress_callback: # 시트 처리 완료 후 콜백
                    try: progress_callback(progress, f"시트 처리 완료: {sheet_display_name}")
                    except InterruptedError: raise
                    except Exception as cb_e: logging.warning(f"Progress callback 실행 중 예외 발생 (시트 완료 알림): {cb_e}", exc_info=True)
                logging.info(f"시트 {sheet_display_name} 처리 완료.")
            except InterruptedError as user_e:
                logging.info(f"시트 {sheet_display_name} 처리 중 사용자가 취소함: {user_e}")
                raise
            except Exception as sheet_e:
                logging.error(f"시트 {sheet_display_name} 처리 중 예기치 않은 오류: {sheet_e}", exc_info=True)
                raise RuntimeError(f"시트 {sheet_display_name} 처리 실패. 원인: {sheet_e}") from sheet_e

        if process:
            final_memory = process.memory_info().rss / (1024*1024)
            logging.info(f"ReadXlstoCode 완료 (소요시간: {time.time() - start_time:.1f}초, 메모리 사용량: {final_memory - initial_memory:.1f}MB)")
        else:
            logging.info(f"ReadXlstoCode 완료 (소요시간: {time.time() - start_time:.1f}초)")


    def ConvXlstoCode(
        self,
        source_file_name: str = "",
        target_file_name: str = "",
        progress_callback: Optional[Callable] = None,
    ) -> Tuple[List[str], List[str]]:
        """
        파싱된 데이터를 바탕으로 C 소스 및 헤더 코드 라인을 생성합니다.

        `ReadXlstoCode`가 성공적으로 완료되어 `self.fi` (FileInfo) 및 `self.cl` (CalList 리스트)
        데이터가 준비되어 있어야 합니다. 코드 생성은 여러 단계(`make_*_code` 메소드 호출)로 진행되며,
        각 단계에서 진행률 콜백이 호출될 수 있습니다.

        Args:
            source_file_name (str): 원본 Excel 파일 이름 (주석 정보에 사용됨). 기본값은 빈 문자열.
            target_file_name (str): 생성될 C 파일의 기본 이름 (확장자 제외).
                                     제공되면 소스/헤더 파일명이 이에 맞춰 동적으로 설정됩니다. 기본값은 빈 문자열.
            progress_callback (Optional[Callable]): 코드 생성 진행 상태 보고용 콜백 함수.

        Returns:
            Tuple[List[str], List[str]]: 생성된 소스 코드 라인 리스트와 헤더 코드 라인 리스트의 튜플.

        Raises:
            RuntimeError: `self.fi` 또는 `self.cl`이 준비되지 않았을 경우.
            InterruptedError: 사용자에 의해 작업이 중단된 경우 (progress_callback을 통해 전달).
        """
        start_time = time.time()

        if self.fi is None or not self.cl:
            error_msg = ("MakeCode 객체 상태가 유효하지 않습니다 (FileInfo 또는 CalList 정보 누락). "
                         "ChkShtInfo()와 ReadXlstoCode()를 먼저 성공적으로 호출해야 합니다.")
            logging.error(error_msg)
            raise RuntimeError(error_msg)

        def _safe_progress_update(progress_value, message_template):
            if progress_callback:
                try:
                    elapsed = time.time() - start_time
                    progress_callback(progress_value, message_template.format(elapsed_time=elapsed))
                except InterruptedError:
                    logging.info(f"사용자에 의해 작업이 중단되었습니다 ({message_template.split('...')[0].strip()}).")
                    raise
                except Exception as cb_e:
                    logging.warning(f"Progress callback 실행 중 예외 발생 ({message_template.split('...')[0].strip()}): {cb_e}", exc_info=True)

        try:
            _safe_progress_update(50, "코드 변환 시작... (경과 시간: {elapsed_time:.1f}초)")
            self.make_conv_info_code(source_file_name)

            _safe_progress_update(60, "시작 코드 생성 중... (경과 시간: {elapsed_time:.1f}초)")
            self.make_start_code()

            _safe_progress_update(70, "파일 정보 코드 생성 중... (경과 시간: {elapsed_time:.1f}초)")
            self.make_file_info_code(target_file_name)

            _safe_progress_update(85, "CAL 리스트 코드 생성 중... (경과 시간: {elapsed_time:.1f}초)")
            self.make_cal_list_code() # This orchestrates calls to CalList objects

            _safe_progress_update(95, "종료 코드 생성 중... (경과 시간: {elapsed_time:.1f}초)")
            self.make_end_code()

            _safe_progress_update(100, "코드 생성 완료 (총 소요시간: {elapsed_time:.1f}초)")
        except InterruptedError:
            raise

        logging.info(f"ConvXlstoCode 완료 (소요시간: {time.time() - start_time:.1f}초)")
        return self.src_lines, self.hdr_lines

    def make_conv_info_code(self, source_file_name: str = "") -> None:
        """
        생성될 소스 및 헤더 파일의 상단에 포함될 파일 생성 정보를 작성합니다.

        정보에는 파일 생성일, 대상 파일 이름, 발견된 오류 요약 등이 포함됩니다.
        결과는 `self.src_lines`와 `self.hdr_lines`에 추가됩니다.

        Args:
            source_file_name (str): 원본 Excel 파일의 이름. 주석에 포함됩니다.
        """
        title = "<파일 생성 정보>"
        date_str = f"파일 생성일 : {datetime.datetime.now().strftime('%Y.%m.%d')}"
        effective_source_file_name = os.path.basename(source_file_name) if source_file_name else "Unknown Source File"
        file_name_str = f"대상 파일   : {effective_source_file_name}"
        err_list_title = "생성 시 발견된 오류 리스트"
        no_err_message = "\t\t >> 발견된 오류가 없습니다"
        start_line_prefix = "\t  * "

        conv_info_lines = [
            "/*", f"\t{title}", f"{start_line_prefix}{date_str}",
            f"{start_line_prefix}{file_name_str}", f"{start_line_prefix}{err_list_title}"
        ]

        if not Info.ErrList:
            conv_info_lines.append(no_err_message)
        else:
            conv_info_lines.append(f"\t\t=> {len(Info.ErrList)}개의 오류 발견")
            for i, err_msg in enumerate(Info.ErrList[:5]):
                parts = err_msg.split(":", 1) if ":" in err_msg else [err_msg]
                formatted_err = f"{parts[0]:<{DEFAULT_ERR_MSG_LEFT_ALIGN}}: {parts[1].strip()}" if len(parts) > 1 else parts[0]
                conv_info_lines.append(f"\t\t  {formatted_err}")
            if len(Info.ErrList) > 5:
                conv_info_lines.append("\t\t  ... (추가 오류는 로그를 확인하세요)")

        conv_info_lines.extend(["*/", ""])
        self.src_lines.extend(conv_info_lines)
        self.hdr_lines.extend(conv_info_lines)

    def make_start_code(self) -> None:
        """소스 및 헤더 파일의 시작 부분에 공통적으로 사용되는 주석 블록을 생성합니다."""
        common_lines = [Info.StartAnnotation[0], HYUNDAI_COPYRIGHT, Info.EndAnnotation[0], ""]
        src_specific = ["*                                   S O U R C E   F I L E                                   *"]
        hdr_specific = ["*                                   H E A D E R   F I L E                                   *"]

        self.src_lines.extend(common_lines[:1] + src_specific + common_lines[1:])
        self.hdr_lines.extend(common_lines[:1] + hdr_specific + common_lines[1:])

    def make_file_info_code(self, target_file_name: str = "") -> None:
        """
        `self.fi` (FileInfo 객체)에 저장된 정보를 바탕으로 파일 정보 주석을 생성하고,
        관련 #include 지시문을 추가합니다.

        `target_file_name`이 제공되면, `FileInfo` 객체 내의 소스/헤더 파일명을
        동적으로 업데이트한 후 주석을 생성하고 다시 원래대로 복원합니다.

        Args:
            target_file_name (str): 생성될 C 파일의 기본 이름 (확장자 제외).
                                     이에 따라 #include 할 헤더 파일명이 결정됩니다.

        Raises:
            RuntimeError: `self.fi` 또는 `self.fi.dFileInfo`가 초기화되지 않은 경우.
            KeyError: `self.fi.dFileInfo`에서 필수 키("S_FILE", "H_FILE")를 찾을 수 없는 경우.
        """
        if self.fi is None or not hasattr(self.fi, "dFileInfo") or self.fi.dFileInfo is None:
            error_msg = ("FileInfo 객체 또는 데이터가 준비되지 않았습니다. "
                         "ChkShtInfo()를 성공적으로 호출했는지 확인하십시오.")
            logging.error(error_msg)
            raise RuntimeError(error_msg)

        critical_keys = ["S_FILE", "H_FILE"]
        for key in critical_keys:
            if key not in self.fi.dFileInfo:
                error_msg = f"FileInfo의 dFileInfo에서 필수 키 '{key}'를 찾을 수 없습니다."
                logging.error(error_msg)
                raise KeyError(error_msg)

        original_src_file, original_hdr_file = None, None
        if target_file_name:
            original_src_file = self.fi.dFileInfo["S_FILE"].Str
            original_hdr_file = self.fi.dFileInfo["H_FILE"].Str
            base_name = os.path.splitext(target_file_name)[0]
            self.fi.dFileInfo["S_FILE"].Str = f"{base_name}.c"
            self.fi.dFileInfo["H_FILE"].Str = f"{base_name}.h"

        self.fi.Write() # FileInfo 객체가 내부적으로 SrcList, HdrList를 채움
        self.src_lines.extend(self.fi.SrcList)
        self.hdr_lines.extend(self.fi.HdrList)

        if target_file_name and original_src_file is not None and original_hdr_file is not None: # 원본 복원
            self.fi.dFileInfo["S_FILE"].Str = original_src_file
            self.fi.dFileInfo["H_FILE"].Str = original_hdr_file

        self.make_include_code(True, self.src_lines, target_file_name)
        self.make_include_code(False, self.hdr_lines, target_file_name)

    def make_include_code(self, is_src: bool, line_list: List[str], target_file_name: str = "") -> None:
        """
        소스 또는 헤더 파일에 필요한 #include 지시문을 생성하여 제공된 `line_list`에 추가합니다.

        헤더 파일의 경우 `#ifndef/#define` 헤더 가드를 추가합니다.
        소스 파일의 경우, 대응하는 헤더 파일을 먼저 인클루드하고, "FileInfo" 시트에 명시된
        추가 인클루드 파일들을 추가합니다.

        Args:
            is_src (bool): True이면 소스 파일용, False이면 헤더 파일용 #include 목록을 생성합니다.
            line_list (List[str]): 생성된 #include 라인들을 추가할 대상 리스트.
            target_file_name (str): 현재 생성 중인 C 파일의 기본 이름. 소스 파일이 자신의 헤더를
                                     인클루드할 때 사용됩니다.
        """
        if self.fi is None or self.fi.dFileInfo is None :
            logging.warning("make_include_code: FileInfo 데이터가 없어 #include를 생성할 수 없습니다.")
            return

        if not is_src: # Header file specific
            guard_name = self.get_hdr_upper_name()
            line_list.extend([f"#ifndef {guard_name}", f"#define {guard_name}", ""])

        self.make_code_title(line_list, "INCLUDES")

        current_header_file = ""
        if target_file_name: # 동적 타겟 파일명 사용
            current_header_file = f"{os.path.splitext(target_file_name)[0]}.h"
        elif "H_FILE" in self.fi.dFileInfo: # FileInfo 시트의 H_FILE 사용
             current_header_file = self.fi.dFileInfo["H_FILE"].Str

        if is_src:
            if current_header_file: line_list.append(f'#include "{current_header_file}"')
            incl_key = "S_INCL"
        else: # Header file
            incl_key = "H_INCL"

        incl_cellinfo = self.fi.dFileInfo.get(incl_key, CellInfos(Str=""))
        if incl_cellinfo.Str:
            includes = [inc.strip() for inc in incl_cellinfo.Str.splitlines() if inc.strip()]
            for inc_file in includes:
                if not (is_src and inc_file == current_header_file): # 소스파일에서 자기 헤더 중복 인클루드 방지
                    line_list.append(f'#include "{inc_file}"')
        line_list.append("")


    def make_code_title(self, line_list: List[str], title_str: str) -> None:
        """
        주어진 타이틀 문자열을 사용하여 표준 형식의 주석 블록(코드 제목)을 생성하고,
        제공된 `line_list`에 추가합니다.

        타이틀 문자열이 `Info.EndPrjtName`으로 끝나면 아무 작업도 하지 않습니다.
        '+' 문자가 포함된 경우, 그 이후의 문자열을 실제 타이틀로 사용합니다.
        리스트의 마지막 라인이 비어있지 않으면, 주석 블록 전에 빈 줄을 추가합니다.

        Args:
            line_list (List[str]): 생성된 코드 제목 라인들을 추가할 대상 리스트.
            title_str (str): 코드 제목으로 사용할 문자열.
        """
        if title_str.endswith(Info.EndPrjtName): return

        actual_title = title_str.split("+", 1)[-1] if "+" in title_str else title_str

        lines_to_add = []
        if line_list and line_list[-1] != "": lines_to_add.append("")
        lines_to_add.extend([Info.StartAnnotation[1], f"\t{actual_title}", Info.EndAnnotation[1]])
        line_list.extend(lines_to_add)

    def make_cal_list_code(self) -> None:
        """
        `self.cl` (CalList 객체 리스트)에 저장된 모든 CAL 시트 정보를 순회하며,
        각 `CalList` 객체의 `writeCalList` 메소드를 호출하여 실제 코드 내용을 생성하고,
        이를 `self.src_lines`와 `self.hdr_lines`에 추가합니다.

        이 메소드는 `CalList` 객체들이 이미 `ReadCalList`를 통해 파싱된 데이터를
        가지고 있다고 가정합니다. `make_code_title`을 호출하여 각 코드 섹션의 타이틀을 추가하고,
        필요한 조건부 컴파일 접미사도 추가합니다.
        """
        if not self.cl:
            logging.warning("make_cal_list_code: 처리할 CalList 객체가 없습니다.")
            return

        title_processing_info = self.cl[0]._prepare_title_processing_info() if self.cl else {} # Use one CalList to prepare title info

        for title_name_key, current_title_detail in title_processing_info.items(): # Renamed variables
            mk_file_type = current_title_detail['mk_file'] # Renamed variables

            if mk_file_type != EMkFile.Src: self.make_code_title(self.hdr_lines, title_name_key)
            if mk_file_type != EMkFile.Hdr: self.make_code_title(self.src_lines, title_name_key)

            src_buffer_title: List[str] = [] # Renamed variables
            hdr_buffer_title: List[str] = []

            first_if_src = True # Renamed variables
            first_if_hdr = True

            for sht_idx, cal_item_obj in enumerate(self.cl): # Renamed variables
                prjt_nm = self.PrjtList[sht_idx] if len(self.cl) > 1 and sht_idx < len(self.PrjtList) else ""
                prjt_ds = cal_item_obj.PrjtDescMain if len(self.cl) > 1 else ""

                # Call CalList's internal helper, which should now exist after its refactoring
                temp_src_lines, temp_hdr_lines = cal_item_obj._generate_code_lines_for_sheet(
                    title_name_key, cal_item_obj, prjt_nm, prjt_ds, current_title_detail,
                    first_if_src, first_if_hdr
                )

                if current_title_detail['has_non_common_src'] and any(l.strip().startswith(("#if", "#elif", "#else")) for l in temp_src_lines):
                    first_if_src = False
                if current_title_detail['has_non_common_hdr'] and any(l.strip().startswith(("#if", "#elif", "#else")) for l in temp_hdr_lines):
                    first_if_hdr = False

                src_buffer_title.extend(temp_src_lines)
                hdr_buffer_title.extend(temp_hdr_lines)

            # Use CalList's helper for suffix
            if self.cl: # Ensure cl is not empty
                 cal_item_obj_for_suffix = self.cl[0] # Use any CalList instance, as _append_conditional_compilation_suffix does not depend on instance data other than PrjtList and prjt_def_title from self (MakeCode)
                 needs_src_suffix = self.prjt_def_title and current_title_detail['has_non_common_src'] and src_buffer_title
                 cal_item_obj_for_suffix._append_conditional_compilation_suffix(src_buffer_title, needs_src_suffix) # This assumes prjt_def_title and PrjtList are accessible or passed if needed

                 needs_hdr_suffix = self.prjt_def_title and current_title_detail['has_non_common_hdr'] and hdr_buffer_title
                 cal_item_obj_for_suffix._append_conditional_compilation_suffix(hdr_buffer_title, needs_hdr_suffix)


            self.src_lines.extend(src_buffer_title)
            self.hdr_lines.extend(hdr_buffer_title)


    def make_end_code(self) -> None:
        """소스 및 헤더 파일의 끝에 표준 종료 주석과 헤더 가드 종료(#endif)를 추가합니다."""
        src_end_lines = ["", Info.StartAnnotation[0], "*                                        End of File                                        *", Info.EndAnnotation[0]]
        hdr_guard_name = self.get_hdr_upper_name()
        hdr_end_lines = ["", f"#endif /* #ifndef {hdr_guard_name} */", "", Info.StartAnnotation[0], "*                                        End of File                                        *", Info.EndAnnotation[0]]

        self.src_lines.extend(src_end_lines)
        self.hdr_lines.extend(hdr_end_lines)

    def get_hdr_upper_name(self) -> str:
        """
        현재 `self.fi.dFileInfo`에 저장된 헤더 파일명(`H_FILE`)을 기반으로
        C 헤더 가드에 사용될 대문자 문자열을 생성합니다.

        예: "my_header.h" -> "_MY_HEADER_H_"

        Returns:
            str: 생성된 헤더 가드용 이름. 필수 정보가 없으면 `DEFAULT_HEADER_GUARD`를 반환합니다.
        """
        if self.fi is None or not hasattr(self.fi, "dFileInfo") or self.fi.dFileInfo is None:
            logging.warning("get_hdr_upper_name: FileInfo 데이터가 없어 기본 헤더 가드를 사용합니다.")
            return DEFAULT_HEADER_GUARD

        h_file_info = self.fi.dFileInfo.get("H_FILE")
        if not h_file_info or not h_file_info.Str:
            logging.warning("get_hdr_upper_name: H_FILE 정보가 없어 기본 헤더 가드를 사용합니다.")
            return DEFAULT_HEADER_GUARD

        temp_str = h_file_info.Str.upper().replace(".", "_")
        return f"_{temp_str}_"

    def reset_for_new_file(self) -> None:
        """
        새로운 Excel 파일 처리를 위해 `MakeCode` 객체의 내부 상태를 초기화합니다.

        `FileInfo` 및 `CalList` 객체, 관련 데이터 목록, 파일명, 생성 경로 등을
        모두 기본 상태로 리셋합니다. 이는 다중 파일 처리 시 각 파일이 독립적으로
        처리될 수 있도록 보장합니다.
        """
        logging.info("새 파일 처리를 위한 MakeCode 상태 초기화 시작")
        self.fi = None
        self.cl = []
        self.dFileInfo = {}
        self.titleList = {}
        self.PrjtList = []
        self.ScrFileName = ""
        self.HdrFileName = ""
        self.MkFilePath = ""
        self.prjt_def_title = ""
        self.src_lines.clear()
        self.hdr_lines.clear()
        Info.ErrList.clear() # Clear global error list for new file
        Info.FileList.clear() # Clear global file list
        Info.MkFileNum = 0
        logging.info("MakeCode 상태 초기화 완료")
