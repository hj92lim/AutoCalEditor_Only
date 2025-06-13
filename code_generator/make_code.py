from typing import Dict, List, Optional
from PySide6.QtWidgets import QListWidget
import os
from datetime import datetime

from core.info import Info, EErrType, EMkFile, EMkMode, CellInfos
from code_generator.file_info import FileInfo
from code_generator.cal_list import CalList

# 메인 코드 최상단에 추가
import traceback
import logging
import sys

# Cython 최적화 함수들을 필요할 때 동적으로 import (안전한 방식)
def safe_import_cython_function(module_name, function_name):
    """Cython 함수를 안전하게 import하는 헬퍼 함수"""
    try:
        # cython_extensions 경로 추가
        if not module_name.startswith('cython_extensions.'):
            module_name = f'cython_extensions.{module_name}'
        module = __import__(module_name, fromlist=[function_name])
        return getattr(module, function_name)
    except (ImportError, AttributeError):
        return None

# 성능 설정 안전 import
try:
    from core.performance_settings import USE_CYTHON_CODE_GEN
except ImportError:
    USE_CYTHON_CODE_GEN = True

# 로그 설정은 main.py에서 통합 관리됨

# 예외 처리를 위한 전역 핸들러 설정
def global_exception_handler(exc_type, exc_value, exc_traceback):
    logging.error("예외가 발생했습니다:", exc_info=(exc_type, exc_value, exc_traceback))
    print(f"오류가 발생했습니다: {exc_value}")
    print("자세한 내용은 debug.log 파일을 확인하세요.")

sys.excepthook = global_exception_handler

class MakeCode:
    """코드 생성 클래스"""
    def __init__(self, of, lb_src, lb_hdr):
        self.of = of
        self.lb_src = lb_src
        self.lb_hdr = lb_hdr

        self.dFileInfo: Dict[str, CellInfos] = {}
        self.titleList: Dict[str, int] = {}
        self.PrjtList: List[str] = []

        self.fi: Optional[FileInfo] = None
        self.cl: List[Optional[CalList]] = []

        self.ScrFileName = ""
        self.HdrFileName = ""
        self.MkFilePath = ""
        self.prjt_def_title = ""  # 추가된 변수

    def ChkShtInfo(self):
        """시트 정보 체크"""
        err_ret = False
        err_cnt = 0

        # FileInfo 시트 체크
        self.dFileInfo = {}
        self.fi = FileInfo(self.of.FileInfoSht, self.dFileInfo)

        err_ret = self.fi.Read()
        if err_ret:
            err_cnt += 1
        else:
            self.ScrFileName = self.dFileInfo["S_FILE"].Str
            self.HdrFileName = self.dFileInfo["H_FILE"].Str
            self.MkFilePath = self.fi.MkFilePath

        # CalList 시트 체크
        self.titleList = {}
        self.cl = []

        for i in range(len(self.of.CalListSht)):
            self.cl.append(CalList(self.fi, self.titleList, self.of.CalListSht[i]))
            err_ret = self.cl[i].ChkCalListPos()

            if err_ret:
                err_cnt += 1
                break

        if err_cnt == 0:
            err_ret = self.chk_prjt_infos()

        # C# 버전과 동일하게 오류 시 객체 상태 초기화
        if err_cnt != 0 or err_ret:
            logging.error(f"ChkShtInfo 실패: err_cnt={err_cnt}, err_ret={err_ret}")
            # 오류 발생 시 객체들을 None으로 설정 (C# 버전과 동일)
            self.fi = None
            self.cl = []
            return True
        else:
            return False

    def chk_prjt_infos(self):
        """프로젝트/단계 정보 읽기"""
        err_flag = False

        for i in range(len(self.cl)):
            sht_name = self.cl[i].ShtName
            prjt_def = self.cl[i].PrjtDefMain
            prjt_name = self.cl[i].PrjtNameMain
            prjt_desc = self.cl[i].PrjtDescMain

            prjt_row = self.cl[i].PrjtStartPos.Row
            prjt_def_col = self.cl[i].PrjtStartPos.Col + Info.PrjtDefCol
            prjt_name_col = self.cl[i].PrjtStartPos.Col + Info.PrjtNameCol

            if i == 0:
                self.prjt_def_title = prjt_def

            if len(self.cl) > 1 and not prjt_def:
                Info.WriteErrCell(EErrType.PrjtEmpty, sht_name, prjt_row, prjt_def_col)
            elif i > 0 and self.prjt_def_title != prjt_def:
                Info.WriteErrCell(EErrType.PrjtNotSame, sht_name, prjt_row, prjt_def_col)

            if len(self.cl) > 1 and not prjt_name:
                Info.WriteErrCell(EErrType.PrjtEmpty, sht_name, prjt_row, prjt_name_col)
            elif i > 0 and prjt_name in self.PrjtList:
                Info.WriteErrCell(EErrType.PrjtSame, sht_name, prjt_row, prjt_name_col)

            if not err_flag:
                self.PrjtList.append(prjt_name)

        if not err_flag:
            if Info.CommPrjtName in self.PrjtList and self.PrjtList[0] != Info.CommPrjtName:
                err_flag = True
            if Info.ElsePrjtName in self.PrjtList and self.PrjtList[-1] != Info.ElsePrjtName:
                err_flag = True

            if err_flag:
                Info.WriteErrCell(EErrType.PrjtDefOrder, self.cl[0].ShtName,
                                self.cl[0].PrjtStartPos.Row,
                                self.cl[0].PrjtStartPos.Col + Info.PrjtNameCol)

        return err_flag

    def ReadXlstoCodeBatch(self, batch_sheet_data, progress_callback=None):
        """🚀 획기적인 배치 처리: 모든 시트를 동시에 고속 처리"""
        import time
        from concurrent.futures import ThreadPoolExecutor, as_completed

        try:
            start_time = time.time()
            total_sheets = len(batch_sheet_data)
            processed_sheets = 0

            if progress_callback:
                progress_callback(10, f"배치 처리 시작: {total_sheets}개 시트")

            # 🔥 핵심: 병렬 처리로 모든 시트를 동시에 처리
            with ThreadPoolExecutor(max_workers=min(4, total_sheets)) as executor:
                # 각 시트별로 병렬 작업 제출
                future_to_sheet = {}
                for sheet_name, sheet_data in batch_sheet_data.items():
                    # CalList 객체 찾기
                    cal_list_obj = None
                    for cl in self.cl:
                        if cl.ShtName == sheet_name:
                            cal_list_obj = cl
                            break

                    if cal_list_obj:
                        future = executor.submit(self._process_single_sheet_fast, cal_list_obj, sheet_data)
                        future_to_sheet[future] = sheet_name

                # 완료된 작업들 수집
                for future in as_completed(future_to_sheet):
                    sheet_name = future_to_sheet[future]
                    try:
                        result = future.result()
                        processed_sheets += 1

                        if progress_callback:
                            progress_percent = 10 + int((processed_sheets / total_sheets) * 60)  # 10-70%
                            progress_callback(progress_percent, f"시트 처리 완료: {sheet_name} ({processed_sheets}/{total_sheets})")

                    except Exception as e:
                        logging.error(f"시트 '{sheet_name}' 배치 처리 실패: {e}")

            elapsed = time.time() - start_time
            logging.info(f"🚀 배치 처리 완료: {total_sheets}개 시트, {elapsed:.2f}초")

            if progress_callback:
                progress_callback(70, f"배치 처리 완료 ({elapsed:.1f}초)")

        except Exception as e:
            logging.error(f"배치 처리 중 오류: {e}")
            # 폴백: 기존 방식으로 처리
            self.ReadXlstoCode(progress_callback)

    def _process_single_sheet_fast(self, cal_list_obj, sheet_data):
        """단일 시트 고속 처리 (병렬 처리용)"""
        try:
            # 시트 데이터 설정
            cal_list_obj.shtData = sheet_data

            # 🔥 핵심: 대량 배치로 한 번에 처리
            total_rows = len(sheet_data) if sheet_data else 0
            if total_rows > 0:
                # 배치 크기를 크게 설정 (전체 시트를 한 번에)
                cal_list_obj.ReadCalList(batch_size=min(total_rows, 5000))

            return True
        except Exception as e:
            logging.error(f"시트 '{cal_list_obj.ShtName}' 고속 처리 실패: {e}")
            return False

    def ReadXlstoCode(self, progress_callback=None):
        """엑셀 파일 읽고 코드 생성 - 응답성 개선"""
        import time
        import os
        from PySide6.QtWidgets import QApplication

        # psutil 모듈 확인 및 메모리 모니터링 설정
        try:
            import psutil
            memory_monitoring = True
        except ImportError:
            logging.warning("psutil 모듈이 설치되지 않아 메모리 모니터링을 사용할 수 없습니다.")
            memory_monitoring = False

        # 시트 정보가 초기화되지 않은 경우 먼저 초기화
        if not self.cl or len(self.cl) == 0:
            logging.warning("CalList 시트가 초기화되지 않았습니다. ChkShtInfo()를 먼저 호출합니다.")
            if self.ChkShtInfo():
                error_msg = "시트 정보 초기화에 실패했습니다."
                logging.error(error_msg)
                raise RuntimeError(error_msg)

        logging.info(f"ReadXlstoCode 시작: 처리할 시트 수 = {len(self.cl)}")
        start_time = time.time()

        if memory_monitoring:
            process = psutil.Process(os.getpid())
            initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        else:
            initial_memory = 0

        # PrjtList 초기화
        self.PrjtList = []

        try:
            for i in range(len(self.cl)):
                # 진행률 콜백 호출 - 더 자주 업데이트
                if progress_callback:
                    progress = int((i / len(self.cl)) * 50)  # ReadXlstoCode는 전체의 50%
                    try:
                        # 더 상세한 정보 제공
                        elapsed = time.time() - start_time
                        progress_callback(progress, f"시트 처리 중: {self.cl[i].ShtName} ({i+1}/{len(self.cl)}) - {elapsed:.1f}초 경과")
                    except InterruptedError as e:
                        # 사용자가 취소한 경우
                        logging.info(f"사용자가 코드 생성을 취소했습니다: {str(e)}")
                        raise  # 예외를 상위로 전파

                logging.info(f"시트 {i+1}/{len(self.cl)} 처리 중: {self.cl[i].ShtName}")

                # UI 응답성 유지 - 더 자주 호출
                QApplication.processEvents()

                # 메모리 사용량 체크 (2GB 제한)
                if memory_monitoring:
                    current_memory = process.memory_info().rss / 1024 / 1024  # MB
                    if current_memory > 2048:  # 2GB
                        logging.warning(f"메모리 사용량 초과: {current_memory:.1f}MB")
                        raise MemoryError(f"메모리 사용량이 2GB를 초과했습니다. 현재: {current_memory:.1f}MB")

                # 타임아웃 체크 (30분 제한)
                elapsed_time = time.time() - start_time
                if elapsed_time > 1800:  # 30분
                    logging.warning(f"ReadXlstoCode 타임아웃: {elapsed_time:.1f}초 경과")
                    raise TimeoutError(f"코드 생성이 30분을 초과했습니다. 현재까지 {i}/{len(self.cl)} 시트 처리 완료")

                try:
                    # 시트 처리 시작 알림
                    if progress_callback:
                        try:
                            progress_callback(progress, f"시트 데이터 읽는 중: {self.cl[i].ShtName}...")
                        except InterruptedError:
                            raise

                    # UI 응답성 유지
                    QApplication.processEvents()

                    try:
                        self.cl[i].ReadCalList(progress_callback)
                    except InterruptedError as e:
                        # 사용자가 취소한 경우
                        logging.info(f"시트 {self.cl[i].ShtName} 처리 중 사용자가 취소함: {str(e)}")
                        raise  # 예외를 상위로 전파

                    # 시트 처리 완료 알림
                    if progress_callback:
                        try:
                            progress_callback(progress, f"시트 처리 완료: {self.cl[i].ShtName}")
                        except InterruptedError:
                            raise

                    logging.info(f"시트 {self.cl[i].ShtName} 처리 완료")

                    # 프로젝트명 추가 (시트별로 처리하여 인덱스 일치 보장)
                    if self.cl[i].PrjtNameMain:
                        self.PrjtList.append(self.cl[i].PrjtNameMain)
                    else:
                        # 프로젝트명이 없는 경우에도 리스트에 추가하여 인덱스 맞추기
                        self.PrjtList.append("")

                except IndexError as e:
                    logging.error(f"시트 {self.cl[i].ShtName} 처리 중 인덱스 오류: {e}")
                    logging.error(traceback.format_exc())
                    print(f"시트 {self.cl[i].ShtName} 처리 중 인덱스 오류가 발생했습니다.")
                    # 오류가 있어도 배열 크기는 맞춰줌
                    self.PrjtList.append("")

        except Exception as e:
            logging.error(f"ReadXlstoCode 전체 오류: {e}")
            logging.error(traceback.format_exc())
            raise

        if memory_monitoring:
            final_memory = process.memory_info().rss / 1024 / 1024  # MB
            memory_used = final_memory - initial_memory
            logging.info(f"ReadXlstoCode 완료 (소요시간: {time.time() - start_time:.1f}초, 메모리 사용량: {memory_used:.1f}MB)")
        else:
            logging.info(f"ReadXlstoCode 완료 (소요시간: {time.time() - start_time:.1f}초)")

    def ConvXlstoCode(self, source_file_name="", target_file_name="", progress_callback=None):
        """엑셀 파일 변환하여 코드 생성 - 응답성 개선"""
        import time
        from PySide6.QtWidgets import QApplication

        start_time = time.time()

        # 필수 객체 유효성 검사
        if self.fi is None:
            error_msg = "FileInfo 객체가 초기화되지 않았습니다. ReadXlstoCode()를 먼저 호출하세요."
            logging.error(error_msg)
            raise RuntimeError(error_msg)

        # 진행률 콜백 호출 - 더 상세한 정보 제공
        if progress_callback:
            try:
                elapsed = time.time() - start_time
                progress_callback(50, f"코드 변환 시작... ({elapsed:.1f}초 경과)")
            except InterruptedError as e:
                # 사용자가 취소한 경우
                logging.info(f"코드 변환 시작 전 사용자가 취소함: {str(e)}")
                raise  # 예외를 상위로 전파

        self.make_conv_info_code(source_file_name)
        QApplication.processEvents()

        if progress_callback:
            try:
                elapsed = time.time() - start_time
                progress_callback(60, f"시작 코드 생성 중... ({elapsed:.1f}초 경과)")
            except InterruptedError as e:
                logging.info(f"시작 코드 생성 중 사용자가 취소함: {str(e)}")
                raise
        self.make_start_code()
        QApplication.processEvents()

        if progress_callback:
            try:
                elapsed = time.time() - start_time
                progress_callback(70, f"파일 정보 코드 생성 중... ({elapsed:.1f}초 경과)")
            except InterruptedError as e:
                logging.info(f"파일 정보 코드 생성 중 사용자가 취소함: {str(e)}")
                raise
        self.make_file_info_code(target_file_name)
        QApplication.processEvents()

        if progress_callback:
            try:
                elapsed = time.time() - start_time
                progress_callback(85, f"CAL 리스트 코드 생성 중... ({elapsed:.1f}초 경과)")
            except InterruptedError as e:
                logging.info(f"CAL 리스트 코드 생성 중 사용자가 취소함: {str(e)}")
                raise
        self.make_cal_list_code()
        QApplication.processEvents()

        if progress_callback:
            try:
                elapsed = time.time() - start_time
                progress_callback(95, f"종료 코드 생성 중... ({elapsed:.1f}초 경과)")
            except InterruptedError as e:
                logging.info(f"종료 코드 생성 중 사용자가 취소함: {str(e)}")
                raise
        self.make_end_code()
        QApplication.processEvents()

        if progress_callback:
            try:
                elapsed = time.time() - start_time
                progress_callback(100, f"코드 생성 완료 (총 소요시간: {elapsed:.1f}초)")
            except InterruptedError as e:
                logging.info(f"코드 생성 완료 단계에서 사용자가 취소함: {str(e)}")
                raise

        logging.info(f"ConvXlstoCode 완료 (소요시간: {time.time() - start_time:.1f}초)")

    def make_conv_info_code(self, source_file_name=""):
        """소스/헤더 파일 앞 부분에 파일 생성 정보 작성"""
        title = "<파일 생성 정보>"
        date = "파일 생성일 : " + datetime.now().strftime("%Y.%m.%d")

        # 소스 파일명이 제공되지 않은 경우 기본값 사용
        if not source_file_name:
            source_file_name = "Unknown Source File"
        else:
            # 파일명만 추출 (경로 제거)
            source_file_name = os.path.basename(source_file_name)

        file_name = "대상 파일   : " + source_file_name
        err_list = "생성 시 발견된 오류 리스트"
        no_err = "\t\t >> 발견된 오류가 없습니다"
        start_line = "\t  * "

        # 파일 생성 정보 라인들 생성
        conv_info_lines = [
            "/*",
            "\t" + title,
            start_line + date,
            start_line + file_name,
            start_line + err_list
        ]

        # 오류 리스트 처리
        if not Info.ErrList:
            conv_info_lines.append(no_err)
        else:
            conv_info_lines.append(f"\t\t=> {len(Info.ErrList)}개의 오류 발견")

            # 최대 5개까지만 표시
            for i, err_msg in enumerate(Info.ErrList[:5]):
                if ':' in err_msg:
                    temp_err_msg = err_msg.split(':')
                    formatted_err = temp_err_msg[0].ljust(Info.ErrNameSize + 2) + ": " + temp_err_msg[1]
                else:
                    formatted_err = err_msg
                conv_info_lines.append(f"\t\t  {formatted_err}")

            # 5개 초과 시 추가 메시지
            if len(Info.ErrList) > 5:
                conv_info_lines.append("\t\t  ... (추가 오류는 로그를 확인하세요)")

        conv_info_lines.append("*/")
        conv_info_lines.append("")

        # 소스 및 헤더 파일 모두에 추가 - UI 배치 최적화 (한 번에 추가)
        for line in conv_info_lines:
            self.lb_src.addItem(line)
        for line in conv_info_lines:
            self.lb_hdr.addItem(line)

    def make_start_code(self):
        """시작 코드 생성 - 성능 최적화"""
        # 소스 및 헤더 파일 시작 부분에 공통적으로 사용되는 라인
        common_lines = [
            Info.StartAnnotation[0],
            "*                             (C) by Hyundai Motor Company LTD.                             *",
            Info.EndAnnotation[0],
            ""
        ]

        # 소스 파일 라인
        src_lines = common_lines.copy()
        src_lines[1:1] = ["*                                   S O U R C E   F I L E                                   *"]

        # 헤더 파일 라인
        hdr_lines = common_lines.copy()
        hdr_lines[1:1] = ["*                                   H E A D E R   F I L E                                   *"]

        # 한 번에 추가
        for line in src_lines:
            self.lb_src.addItem(line)

        for line in hdr_lines:
            self.lb_hdr.addItem(line)

    def make_file_info_code(self, target_file_name=""):
        """파일 정보 코드 생성 - 안전성 강화"""
        # FileInfo 객체 유효성 검사
        if self.fi is None:
            error_msg = "FileInfo 객체가 초기화되지 않았습니다. ChkShtInfo()를 먼저 호출하세요."
            logging.error(error_msg)
            raise RuntimeError(error_msg)

        if not hasattr(self.fi, 'dFileInfo') or self.fi.dFileInfo is None:
            error_msg = "FileInfo 데이터가 로드되지 않았습니다."
            logging.error(error_msg)
            raise RuntimeError(error_msg)

        # 필수 키 존재 확인
        required_keys = ["S_FILE", "H_FILE"]
        for key in required_keys:
            if key not in self.fi.dFileInfo:
                error_msg = f"FileInfo에서 필수 키 '{key}'를 찾을 수 없습니다."
                logging.error(error_msg)
                raise KeyError(error_msg)

        # 타겟 파일명이 제공된 경우 파일 정보를 동적으로 수정
        if target_file_name:
            # 원본 파일 정보 백업
            original_src_file = self.fi.dFileInfo["S_FILE"].Str
            original_hdr_file = self.fi.dFileInfo["H_FILE"].Str

            # 파일명 동적 설정
            base_name = target_file_name.replace(".c", "").replace(".h", "")
            self.fi.dFileInfo["S_FILE"].Str = f"{base_name}.c"
            self.fi.dFileInfo["H_FILE"].Str = f"{base_name}.h"

            # 파일 정보 생성
            self.fi.Write()

            # 원본 파일 정보 복원 (다음 파일 생성을 위해)
            self.fi.dFileInfo["S_FILE"].Str = original_src_file
            self.fi.dFileInfo["H_FILE"].Str = original_hdr_file
        else:
            # 기본 파일 정보 생성
            self.fi.Write()

        # 소스/헤더 리스트를 한 번에 추가 - UI 배치 최적화
        for src in self.fi.SrcList:
            self.lb_src.addItem(src)
        for hdr in self.fi.HdrList:
            self.lb_hdr.addItem(hdr)

        # 인클루드 코드 생성 (최적화된 버전 사용)
        self.make_include_code(True, self.lb_src, target_file_name)
        self.make_include_code(False, self.lb_hdr, target_file_name)

    def make_include_code(self, is_src, lb, target_file_name=""):
        """인클루드 코드 생성"""
        incl_str = ""

        if not is_src:
            incl_str = self.get_hdr_upper_name()

            lb.addItem(f"#ifndef {incl_str}")
            lb.addItem(f"#define {incl_str}")

        self.make_code_title(lb, "INCLUDES")

        if is_src:
            # 소스 파일의 경우 먼저 해당 헤더 파일을 인클루드
            if target_file_name:
                # 타겟 파일명이 제공된 경우 동적으로 헤더 파일명 생성
                base_name = target_file_name.replace(".c", "").replace(".h", "")
                header_file = f"{base_name}.h"
                lb.addItem(f'#include "{header_file}"')
            else:
                header_file = self.dFileInfo["H_FILE"].Str
                if header_file:
                    lb.addItem(f'#include "{header_file}"')

            # 추가 인클루드 파일들
            incl_str = self.dFileInfo["S_INCL"].Str
            if incl_str:
                includes = [inc for inc in incl_str.split('\r\n') if inc.strip()]
                for inc in includes:
                    if target_file_name:
                        base_name = target_file_name.replace(".c", "").replace(".h", "")
                        header_file = f"{base_name}.h"
                    else:
                        header_file = self.dFileInfo["H_FILE"].Str

                    if inc != header_file:  # 중복 방지
                        lb.addItem(f'#include "{inc}"')
        else:
            incl_str = self.dFileInfo["H_INCL"].Str
            if incl_str:
                # 줄바꿈으로 분리하고 각 인클루드 파일 처리
                includes = [inc for inc in incl_str.split('\r\n') if inc.strip()]

                # C# 출력과 같이 인클루드 문장들이 연속적으로 출력되도록 처리
                if includes:
                    includes_formatted = '\n'.join([f'#include "{inc}"' for inc in includes])
                    lb.addItem(includes_formatted)


    def make_code_title(self, lb, title_str):
        """코드 제목 생성 - 성능 최적화"""
        if title_str.endswith(Info.EndPrjtName):
            return

        # 타이틀 이름 파싱 (한 번만 수행)
        if "+" in title_str:
            title_name = title_str.split('+')
            title_str = title_name[1]

        # 라인 리스트에 빈 줄이 있는지 확인
        empty_line = False
        if lb.count() > 0:
            last_item = lb.item(lb.count() - 1)
            if last_item and not last_item.text():
                empty_line = True

        # 미리 모든 라인을 생성
        lines = []
        if not empty_line:
            lines.append("")

        lines.append(Info.StartAnnotation[1])
        lines.append(f"\t{title_str}")
        lines.append(Info.EndAnnotation[1])

        # 한 번에 추가
        for line in lines:
            lb.addItem(line)

    def make_cal_list_code(self):
        """Cal 리스트를 코드로 생성 - Cython 성능 최적화"""
        # Cython 최적화 적용 가능한 경우 빠른 처리
        if USE_CYTHON_CODE_GEN:
            # 대량 데이터 처리를 위한 Cython 최적화
            all_temp_code_items = []
            for title_name in self.titleList:
                for sht in range(len(self.cl)):
                    if title_name in self.cl[sht].dTempCode:
                        all_temp_code_items.extend(self.cl[sht].dTempCode[title_name])

            # Cython 최적화 버전으로 대량 처리 (임시 비활성화 - Float Suffix 오류 회피)
            if False and all_temp_code_items:  # 임시로 비활성화
                processed_items = fast_write_cal_list_processing(all_temp_code_items)
                logging.info(f"✓ Cython 최적화로 {len(processed_items)}개 코드 항목 처리 완료")

        # 기존 Python 버전 (상세 처리)
        # 사전 처리 - 각 타이틀에 대한 정보 미리 수집
        title_info = {}

        for title_name, mk_file in self.titleList.items():
            # 각 타이틀에 대한 정보 초기화
            title_info[title_name] = {
                'mk_file': mk_file,
                'has_non_common_src': False,
                'has_non_common_hdr': False,
                'sheets_with_src': [],
                'sheets_with_hdr': []
            }

            # 먼저 이 타이틀에 COMMON이 아닌 코드가 있는지 확인
            for sht in range(len(self.cl)):
                # 안전한 인덱스 접근
                prjt_name = ""
                if len(self.cl) > 1 and sht < len(self.PrjtList):
                    prjt_name = self.PrjtList[sht]

                if len(self.cl) > 1 and prjt_name != Info.CommPrjtName:
                    if title_name in self.cl[sht].dSrcCode and self.cl[sht].dSrcCode[title_name]:
                        title_info[title_name]['has_non_common_src'] = True
                        title_info[title_name]['sheets_with_src'].append(sht)

                    if title_name in self.cl[sht].dHdrCode and self.cl[sht].dHdrCode[title_name]:
                        title_info[title_name]['has_non_common_hdr'] = True
                        title_info[title_name]['sheets_with_hdr'].append(sht)

        # 각 타이틀 처리
        for title_name, info in title_info.items():
            mk_file = info['mk_file']

            # 타이틀 추가
            if mk_file != EMkFile.Src:
                self.make_code_title(self.lb_hdr, title_name)
            if mk_file != EMkFile.Hdr:
                self.make_code_title(self.lb_src, title_name)

            # 코드 생성 - 먼저 버퍼에 모아서 한 번에 처리
            src_buffer = []
            hdr_buffer = []

            # 시트별로 처리
            for sht in range(len(self.cl)):
                # 안전한 인덱스 접근
                prjt_name = ""
                prjt_desc = ""

                if len(self.cl) > 1:
                    if sht < len(self.PrjtList):
                        prjt_name = self.PrjtList[sht]
                    prjt_desc = self.cl[sht].PrjtDescMain

                tab_flag = False
                src_list = None
                hdr_list = None

                if title_name in self.cl[sht].dSrcCode:
                    src_list = self.cl[sht].dSrcCode[title_name]

                if title_name in self.cl[sht].dHdrCode:
                    hdr_list = self.cl[sht].dHdrCode[title_name]

                # 조건부 컴파일 코드 생성 여부 확인
                need_conditional = (len(self.cl) > 1 and prjt_name != Info.CommPrjtName and
                                self.prjt_def_title and (src_list or hdr_list))

                # 조건부 컴파일 시작
                if need_conditional:
                    ifdef_str = ""
                    if sht == 0 or (sht == 1 and self.PrjtList[0] == Info.CommPrjtName):
                        ifdef_str = "#if ("
                    elif prjt_name == Info.ElsePrjtName:
                        ifdef_str = "#else"
                    else:
                        ifdef_str = "#elif ("

                    if prjt_name == Info.ElsePrjtName:
                        def_str = ifdef_str
                    else:
                        def_str = f"{ifdef_str}{self.prjt_def_title} == {prjt_name})"
                        if prjt_desc:
                            if len(def_str) % Info.TabSize >= 3:
                                def_str += "\t"
                            def_str += f"\t// {prjt_desc}"

                    # 조건부 코드를 각 버퍼에 추가
                    if info['has_non_common_src'] and src_list:
                        src_buffer.append("")
                        src_buffer.append(def_str)
                        if not (src_list[0].strip().startswith("\r\n") if src_list else False):
                            src_buffer.append("")

                    if info['has_non_common_hdr'] and hdr_list:
                        hdr_buffer.append("")
                        hdr_buffer.append(def_str)
                        if not (hdr_list[0].strip().startswith("\r\n") if hdr_list else False):
                            hdr_buffer.append("")

                    tab_flag = True

                tab_str = "\t" if tab_flag else ""

                # 소스 코드 처리
                if src_list:
                    for line in src_list:
                        src_buffer.append(f"{tab_str}{line.rstrip()}")

                # 헤더 코드 처리
                if hdr_list:
                    for line in hdr_list:
                        hdr_buffer.append(f"{tab_str}{line.rstrip()}")

            # 조건부 컴파일 종료 추가
            if self.prjt_def_title:
                # 소스 코드 조건부 컴파일 종료
                if info['has_non_common_src'] and src_buffer:
                    else_lines = []
                    if Info.ElsePrjtName not in self.PrjtList:
                        else_lines.append("#else")
                        else_lines.append(f"\t#error undefined {self.prjt_def_title} MACRO")
                        else_lines.append("")
                    else_lines.append("#endif")
                    else_lines.append("")

                    src_buffer.append("")
                    src_buffer.extend(else_lines)

                # 헤더 코드 조건부 컴파일 종료
                if info['has_non_common_hdr'] and hdr_buffer:
                    else_lines = []
                    if Info.ElsePrjtName not in self.PrjtList:
                        else_lines.append("#else")
                        else_lines.append(f"\t#error undefined {self.prjt_def_title} MACRO")
                        else_lines.append("")
                    else_lines.append("#endif")
                    else_lines.append("")

                    hdr_buffer.append("")
                    hdr_buffer.extend(else_lines)

            # 버퍼의 모든 라인을 한 번에 추가 - UI 배치 최적화
            for line in src_buffer:
                self.lb_src.addItem(line)
            for line in hdr_buffer:
                self.lb_hdr.addItem(line)



    def make_end_code(self):
        """파일 끝 작성 - 성능 최적화"""
        # 소스 파일 끝 라인
        src_lines = [
            "",
            Info.StartAnnotation[0],
            "*                                        End of File                                        *",
            Info.EndAnnotation[0]
        ]

        # 헤더 파일 끝 라인
        hdr_lines = [
            "",
            f"#endif /* #ifndef {self.get_hdr_upper_name()} */",
            "",
            Info.StartAnnotation[0],
            "*                                        End of File                                        *",
            Info.EndAnnotation[0]
        ]

        # 한 번에 추가 - UI 배치 최적화
        for line in src_lines:
            self.lb_src.addItem(line)
        for line in hdr_lines:
            self.lb_hdr.addItem(line)

    def get_hdr_upper_name(self):
        """헤더 파일 이름 대문자 변환"""
        temp_str = self.dFileInfo["H_FILE"].Str.upper()
        temp_str = temp_str.replace(".", "_")
        temp_str = "_" + temp_str + "_"

        return temp_str

    def reset_for_new_file(self):
        """새 파일 처리를 위한 상태 초기화 - 다중 DB 처리 시 필수"""
        logging.info("새 파일 처리를 위한 상태 초기화")

        # 핵심 객체들 초기화
        self.fi = None
        self.cl = []

        # 데이터 구조 초기화
        self.dFileInfo = {}
        self.titleList = {}
        self.PrjtList = []

        # 파일 정보 초기화
        self.ScrFileName = ""
        self.HdrFileName = ""
        self.MkFilePath = ""
        self.prjt_def_title = ""

        # 출력 리스트 초기화
        if self.lb_src:
            self.lb_src.clear()
        if self.lb_hdr:
            self.lb_hdr.clear()

        logging.info("MakeCode 상태 초기화 완료")