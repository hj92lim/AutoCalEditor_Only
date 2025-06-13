import re
from typing import Dict, List
from core.info import Info, EMkFile, EMkMode, EArrType, EErrType, CellInfos, ArrInfos, SCellPos, SPrjtInfo
import logging
import traceback

# 성능 설정 안전 import
try:
    from core.performance_settings import (
        ENABLE_FLOAT_SUFFIX,
        USE_CYTHON_CAL_LIST,
        USE_CYTHON_CODE_GEN
    )
except ImportError as e:
    logging.warning(f"성능 설정 import 실패, 기본값 사용: {e}")
    ENABLE_FLOAT_SUFFIX = True
    USE_CYTHON_CAL_LIST = True
    USE_CYTHON_CODE_GEN = True

# Cython 모듈 안전 import
CYTHON_CODE_GEN_AVAILABLE = False
try:
    from cython_extensions.code_generator_v2 import fast_variable_code_generation
    CYTHON_CODE_GEN_AVAILABLE = True
    logging.info("✓ Cython 코드 생성 모듈 로드 성공")
except ImportError as e:
    logging.warning(f"⚠ Cython 코드 생성 모듈 로드 실패, Python 폴백 사용: {e}")

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

# 실제 사용되는 Cython 함수들만 캐시
_cython_function_cache = {}

class CalList:
    def __init__(self, fi, title_list, sht_info):
        self.fi = fi
        self.titleList = title_list

        self.ShtName = sht_info.Name
        self.shtData = sht_info.Data

        # 데이터 캐싱을 위한 변수 추가
        self.cell_cache = {}

        # 자주 사용하는 정규식 패턴 미리 컴파일 - 성능 최적화
        self.decimal_pattern = re.compile(r'(\d+\.\d*|\.\d+)(?![fF"\w])')
        self.decimal_point_only_pattern = re.compile(r'(\d+\.)(?![fF"\w\d])')
        self.integer_pattern = re.compile(r'(?<![.\w])([1-9]\d*)(?![.\w\[\]])')
        self.zero_pattern = re.compile(r'(?<![.\w])0(?![.\w\[\]])')
        self.block_comment_pattern = re.compile(r'/\*.*?\*/', re.DOTALL)
        self.line_comment_pattern = re.compile(r'//.*?(?=\n|$)')
        self.string_pattern = re.compile(r'"(?:\\.|[^"\\])*"')
        self.array_index_pattern = re.compile(r'\[\s*\d+\s*\](?:\[\s*\d+\s*\])*')
        self.cast_pattern = re.compile(r'\(\s*FLOAT32\s*\*\s*\)\s*&\w+\s*\[\s*\d+\s*\]\s*(?:\[\s*\d+\s*\])*', re.IGNORECASE)

        # 배열 값 처리용 추가 정규식 패턴들 - add_float_suffix 최적화용
        self.array_value_pattern = re.compile(r'(,\s*)(-?\d+)(\s*,|\s*\})')
        self.array_last_value_pattern = re.compile(r'(,\s*)(-?\d+)(\s*\})')

        # 기존 코드 유지
        self.dTempCode = {}
        self.dSrcCode = {}
        self.dHdrCode = {}
        self.dArr = {}

        self.dItem = {}
        self.dItem["OpCode"] = CellInfos(0, 0, "")
        self.dItem["Keyword"] = CellInfos(0, 0, "")
        self.dItem["Type"] = CellInfos(0, 0, "")
        self.dItem["Name"] = CellInfos(0, 0, "")
        self.dItem["Value"] = CellInfos(0, 0, "")
        self.dItem["Description"] = CellInfos(0, 0, "")

        self.prjtList = []
        for _ in range(5):
            self.prjtList.append(SPrjtInfo("", []))

        self.ArrAlignList = []

        self.PrjtStartPos = SCellPos(1, 1)
        self.itemStartPos = SCellPos(1, 1)

        self.pragSet = False
        self.itemLength = [0, 0, 0, 0]

        self.prjtDepth = -1
        self.prjtDefCol = 0
        self.prjtNameCol = 0
        self.nameDfltCol = 0
        self.descDfltCol = 0
        self.memDfltCol = 0
        self.valDfltCol = 0
        self.alignCnt = 0
        self.arrNameCnt = 0

        self.PrjtDefMain = ""
        self.PrjtNameMain = ""
        self.PrjtDescMain = ""
        self.frontTab = ""
        self.currentArr = ""
        self.currentTitle = ""
        self.currentPRGM = ""
        self.currentPrjtDef = ""
        self.currentPrjtName = ""

        self.mkFile = EMkFile.All
        self.mkMode = EMkMode.NONE
        self.mkModeOld = EMkMode.NONE

        # Float Suffix 패턴 초기화 (04_Python_Migration 방식)
        self.float_suffix_patterns = True  # 간단한 플래그로 사용

    def cached_read_cell(self, row, col):
        """셀 데이터 캐싱하여 읽기 - 성능 최적화"""
        cache_key = (row, col)

        # 캐시 히트
        if cache_key in self.cell_cache:
            return self.cell_cache[cache_key]

        # 캐시 미스 - 데이터 로드
        value = Info.ReadCell(self.shtData, row, col)

        # 캐시 크기 제한 (메모리 사용량 제어) - 안전한 Cython 최적화 적용
        if USE_CYTHON_CAL_LIST:
            # Cython 최적화 버전 사용 (안전한 동적 import)
            fast_cell_cache_management = safe_import_cython_function('data_processor', 'fast_cell_cache_management')
            if fast_cell_cache_management:
                try:
                    cache_size = fast_cell_cache_management(self.cell_cache, 100000)
                    self.cell_cache[cache_key] = value
                except Exception:
                    # 실패 시 Python 폴백
                    if len(self.cell_cache) < 100000:
                        self.cell_cache[cache_key] = value
            else:
                # Cython 함수 없으면 Python 폴백
                if len(self.cell_cache) < 100000:
                    self.cell_cache[cache_key] = value
        else:
            # 기존 Python 버전 (폴백)
            if len(self.cell_cache) < 100000:  # 10만개 제한
                self.cell_cache[cache_key] = value
            elif len(self.cell_cache) >= 150000:  # 15만개 초과 시 정리
                # 오래된 캐시 항목 제거 (간단한 LRU 구현)
                keys_to_remove = list(self.cell_cache.keys())[:50000]  # 5만개 제거
                for key in keys_to_remove:
                    del self.cell_cache[key]
                self.cell_cache[cache_key] = value

        return value

    def ChkCalListPos(self):
        """아이템 항목 위치 찾기 - 캐싱 적용"""
        err_flag = False
        item_chk_cnt = 0
        cell_str = ""
        prjt_title = ""
        prjt_def = ""
        prjt_name = ""
        prjt_desc = ""

        # 셀 데이터 캐싱
        for row in range(self.itemStartPos.Row, min(len(self.shtData), self.itemStartPos.Row + 20)):
            for col in range(self.itemStartPos.Col, min(len(self.shtData[0]) if len(self.shtData) > 0 else 0, self.itemStartPos.Col + 10)):
                self.cached_read_cell(row, col)

        for row in range(self.itemStartPos.Row, len(self.shtData)):
            if item_chk_cnt == len(self.dItem):
                break

            item_chk_cnt = 0
            for col in range(self.itemStartPos.Col, len(self.shtData[0]) if len(self.shtData) > 0 else 0):
                cell_str = self.cached_read_cell(row, col)

                if cell_str in self.dItem:
                    self.dItem[cell_str].Col = col
                    item_chk_cnt += 1

                if item_chk_cnt == len(self.dItem):
                    break

            if item_chk_cnt > 0:
                if item_chk_cnt == len(self.dItem):
                    self.itemStartPos.Row = row + 1
                    for key, i_d in self.dItem.items():
                        i_d.Row = self.itemStartPos.Row

                    self.nameDfltCol = self.dItem["Name"].Col
                    self.descDfltCol = self.dItem["Description"].Col
                    self.memDfltCol = self.dItem["Name"].Col + 1
                    self.valDfltCol = self.dItem["Value"].Col
                else:
                    err_flag = True
                    Info.WriteErrCell(EErrType.ItemName, self.ShtName, 1, 1)
                break

        if not err_flag:
            self.PrjtStartPos.Col = self.dItem["Name"].Col
            self.prjtDefCol = self.PrjtStartPos.Col + Info.PrjtDefCol
            self.prjtNameCol = self.PrjtStartPos.Col + Info.PrjtNameCol

            # 테이블 앞부분 데이터 캐싱
            for row in range(1, min(self.itemStartPos.Row, 30)):
                self.cached_read_cell(row, self.PrjtStartPos.Col)
                self.cached_read_cell(row, self.prjtDefCol)
                self.cached_read_cell(row, self.prjtNameCol)
                self.cached_read_cell(row, self.prjtNameCol + 2)

            for row in range(1, self.itemStartPos.Row - 1):
                prjt_title = self.cached_read_cell(row, self.PrjtStartPos.Col)
                prjt_def = self.cached_read_cell(row, self.prjtDefCol)
                prjt_name = self.cached_read_cell(row, self.prjtNameCol)
                prjt_desc = self.cached_read_cell(row, self.prjtNameCol + 2)

                if prjt_title and prjt_def and prjt_name:
                    self.PrjtStartPos.Row = row
                    self.PrjtDefMain = prjt_def
                    self.PrjtNameMain = prjt_name
                    self.PrjtDescMain = prjt_desc
                    break
                elif not prjt_def and prjt_name:
                    self.PrjtStartPos.Row = row
                    self.PrjtNameMain = prjt_name
                    self.PrjtDescMain = prjt_desc
                    break
                elif prjt_def and not prjt_name:
                    self.PrjtStartPos.Row = row
                    self.PrjtDefMain = prjt_def
                    self.PrjtDescMain = prjt_desc
                    break
                elif prjt_def and prjt_name:
                    self.PrjtStartPos.Row = row
                    self.PrjtDefMain = prjt_def
                    self.PrjtNameMain = prjt_name
                    self.PrjtDescMain = prjt_desc
                    break

        return err_flag

    def ReadCalList(self, progress_callback=None):
        """아이템리스트 read 후 임시 코드 생성 - 응답성 개선"""
        import time
        from PySide6.QtWidgets import QApplication

        logging.info(f"시트 {self.ShtName} ReadCalList 시작")
        start_time = time.time()
        self.arrNameCnt = 0

        try:
            # 데이터 범위 검증
            if not self.shtData or len(self.shtData) <= self.itemStartPos.Row:
                logging.warning(f"시트 {self.ShtName}의 데이터가 비어있거나 충분하지 않습니다.")
                return

            total_rows = len(self.shtData) - self.itemStartPos.Row
            processed_rows = 0

            # 🚀 초고속 배치 처리 크기 최적화 (점진적 증가 방식)
            if total_rows > 50000:
                batch_size = 2500  # 초대용량: 2500행씩 (기존 1000에서 2.5배 증가)
            elif total_rows > 10000:
                batch_size = 2000  # 대용량: 2000행씩
            elif total_rows > 5000:
                batch_size = 1500  # 대중량: 1500행씩
            elif total_rows > 2000:
                batch_size = 1000  # 중대량: 1000행씩
            elif total_rows > 1000:
                batch_size = 500   # 중간: 500행씩 (기존 300에서 67% 증가)
            else:
                batch_size = 200   # 소량: 200행씩 (기존 100에서 2배 증가)

            logging.info(f"⚡ 시트 {self.ShtName}: 최적화된 배치 크기 {batch_size}로 {total_rows}행 고성능 처리 시작 (완전 데이터 처리 모드)")

            # 성능 최적화: 딕셔너리 순회를 한 번만 수행하고 리스트로 저장 (결과 동일, 속도 향상)
            item_list = list(self.dItem.values())

            # 배치 단위로 처리
            for batch_start in range(self.itemStartPos.Row, len(self.shtData), batch_size):
                batch_end = min(batch_start + batch_size, len(self.shtData))

                # 배치 시작 시 UI 응답성 및 진행률 업데이트
                QApplication.processEvents()

                if progress_callback:
                    # 🎯 개선된 진행률 계산 (시트 처리: 50-90%, 코드 생성: 90-100%)
                    sheet_progress = int((processed_rows / total_rows) * 85)  # 85%까지만 (시트 처리)
                    progress = 50 + sheet_progress  # 50%에서 시작해서 90%까지
                    try:
                        # 더 상세한 정보 제공
                        elapsed = time.time() - start_time
                        progress_callback(progress, f"⚡ 시트 {self.ShtName}: {processed_rows}/{total_rows} 행 고속 처리 중 ({elapsed:.1f}초)")
                    except InterruptedError as e:
                        # 사용자가 취소한 경우
                        logging.info(f"시트 {self.ShtName} 처리 중 사용자가 취소함: {str(e)}")
                        raise  # 예외를 상위로 전파

                # 타임아웃 체크 (10분 제한)
                elapsed_time = time.time() - start_time
                if elapsed_time > 600:  # 10분
                    logging.warning(f"시트 {self.ShtName} 처리 타임아웃: {elapsed_time:.1f}초 경과")
                    raise TimeoutError(f"시트 {self.ShtName} 처리가 10분을 초과했습니다. {processed_rows}/{total_rows} 행 처리 완료")

                # 🚀 초고속 Cython + 병렬 처리 활성화
                fast_read_cal_list_processing = safe_import_cython_function('code_generator_v2', 'fast_read_cal_list_processing')
                use_cython = fast_read_cal_list_processing is not None

                # 병렬 처리 여부 결정 (중간 크기 이상 배치에서만)
                use_parallel_for_batch = (batch_end - batch_start) >= 500 and total_rows > 2000

                if use_cython:
                    try:
                        # 🔥 Cython 완전한 데이터 처리 (수정된 버전)
                        cython_result = fast_read_cal_list_processing(
                            self, batch_start, batch_end, item_list  # self 객체 전달로 완전한 처리
                        )
                        if cython_result:
                            processed_rows += len(cython_result)
                            logging.debug(f"✅ Cython 완전 처리 성공: {batch_start}-{batch_end} ({len(cython_result)}행)")
                            continue  # 다음 배치로
                        else:
                            logging.debug(f"⚠️ Cython 결과 없음, 표준 처리 모드로 전환")
                    except Exception as e:
                        logging.warning(f"⚠️ Cython 처리 실패, 표준 처리 모드로 전환: {e}")

                # Python 폴백 처리 (벡터화 + 선택적 병렬)
                if use_parallel_for_batch:
                    # 🔀 병렬 처리 (큰 배치)
                    from concurrent.futures import ThreadPoolExecutor

                    # 배치를 더 작은 청크로 분할
                    chunk_size = max(50, (batch_end - batch_start) // 4)
                    chunks = []
                    for chunk_start in range(batch_start, batch_end, chunk_size):
                        chunk_end = min(chunk_start + chunk_size, batch_end)
                        chunks.append((chunk_start, chunk_end))

                    with ThreadPoolExecutor(max_workers=min(4, len(chunks))) as executor:
                        chunk_results = list(executor.map(
                            lambda chunk: self.process_batch_vectorized(chunk[0], chunk[1], item_list),
                            chunks
                        ))

                    # 결과 집계
                    for result in chunk_results:
                        if result['success']:
                            processed_rows += result['processed']
                        else:
                            logging.error(f"청크 처리 실패: {result.get('error', 'Unknown')}")
                else:
                    # 🔥 벡터화된 순차 처리 (작은 배치)
                    result = self.process_batch_vectorized(batch_start, batch_end, item_list)
                    if result['success']:
                        processed_rows += result['processed']
                    else:
                        logging.error(f"배치 처리 실패: {result.get('error', 'Unknown')}")

                # 배치 완료 후 메모리 정리 (대용량 데이터 처리 시)
                if batch_size >= 500 and processed_rows % (batch_size * 10) == 0:
                    import gc
                    gc.collect()
                    logging.debug(f"시트 {self.ShtName}: {processed_rows}행 처리 완료, 메모리 정리 실행")

            self.arrNameCnt = 0

            # 코드 작성 단계에서의 오류 포착
            total_items = sum(len(item) for item in self.dTempCode.values())
            processed_items = 0

            for key, item in self.dTempCode.items():
                logging.debug(f"아이템 {key} 코드 생성 중, 항목 수: {len(item)}")

                for i in range(len(item)):
                    # 배치 단위로 UI 응답성 유지
                    if processed_items % batch_size == 0:
                        QApplication.processEvents()

                        if progress_callback:
                            # 🎯 코드 생성 진행률 (90-100% 범위)
                            code_progress = int((processed_items / total_items) * 10)  # 10% 범위
                            progress = 90 + code_progress  # 90%에서 시작해서 100%까지
                            try:
                                # 더 상세한 정보 제공
                                elapsed = time.time() - start_time
                                progress_callback(progress, f"🔥 시트 {self.ShtName}: C코드 생성 중 {processed_items}/{total_items} ({elapsed:.1f}초)")
                            except InterruptedError as e:
                                # 사용자가 취소한 경우
                                logging.info(f"시트 {self.ShtName} 코드 생성 중 사용자가 취소함: {str(e)}")
                                raise  # 예외를 상위로 전파

                    try:
                        self.writeCalList(item[i])
                    except IndexError as e:
                        logging.error(f"코드 작성 중 인덱스 오류: 키={key}, 인덱스={i}")
                        logging.error(traceback.format_exc())
                        # 다음 항목 계속 처리

                    processed_items += 1

        except Exception as e:
            logging.error(f"ReadCalList 전체 오류: {e}")
            logging.error(traceback.format_exc())
            raise

        logging.info(f"🎉 시트 {self.ShtName} 고성능 ReadCalList 완료 (소요시간: {time.time() - start_time:.1f}초)")

    def process_batch_vectorized(self, batch_start, batch_end, item_list):
        """🚀 벡터화된 배치 처리 (고성능 최적화 버전)"""
        import traceback

        batch_processed = 0

        try:
            # 🚀 초고속 벡터화된 셀 데이터 미리 읽기 (중복 제거 최적화)
            batch_data = {}
            required_cols = set()

            # 필요한 컬럼들 미리 수집 (최적화: 중복 제거)
            for item in item_list:
                required_cols.add(item.Col)

            # 🔥 배치 범위의 모든 필요한 셀을 한 번에 읽기 (메모리 효율적)
            for row in range(batch_start, batch_end):
                for col in required_cols:
                    # 캐시 우선 확인 (중복 읽기 방지)
                    cache_key = (row, col)
                    if cache_key in self.cell_cache:
                        batch_data[cache_key] = self.cell_cache[cache_key]
                    else:
                        # 직접 읽기 (범위 체크 최적화)
                        if row < len(self.shtData) and col < len(self.shtData[row]):
                            value = self.shtData[row][col] if self.shtData[row][col] else ""
                        else:
                            value = ""
                        batch_data[cache_key] = value
                        # 캐시에 저장 (메모리 제한 고려)
                        if len(self.cell_cache) < 50000:  # 메모리 절약
                            self.cell_cache[cache_key] = value

            # 🔥 고속 행별 처리 (벡터화된 데이터 사용)
            for row in range(batch_start, batch_end):
                try:
                    # 아이템 행 설정 (최적화: 미리 읽은 데이터 사용)
                    for item in item_list:
                        item.Row = row
                        # 캐시된 데이터 사용
                        if hasattr(item, 'Str'):
                            item.Str = batch_data.get((row, item.Col), "")

                    self.chk_op_code()

                    if self.mkMode != EMkMode.NONE:
                        if self.mkMode == EMkMode.ARR_MEM:
                            self.readArrMem(row)
                        else:
                            self.readRow(row)

                        self.chkCalList(row)
                        self.saveTempList(row)

                    batch_processed += 1

                except IndexError as e:
                    logging.error(f"벡터화 처리 중 행 {row} 인덱스 오류: {e}")
                    continue
                except Exception as e:
                    logging.error(f"벡터화 처리 중 행 {row} 오류: {e}")
                    continue

            return {
                'success': True,
                'processed': batch_processed,
                'method': '고성능_벡터화_처리',
                'range': (batch_start, batch_end)
            }

        except Exception as e:
            logging.error(f"벡터화 배치 처리 실패 {batch_start}-{batch_end}: {e}")
            logging.error(traceback.format_exc())
            return {
                'success': False,
                'processed': batch_processed,
                'error': str(e),
                'range': (batch_start, batch_end)
            }

    def chk_op_code(self):
        """OpCode 오류 체크 - 성능 최적화"""
        op_code_row = self.dItem["OpCode"].Row
        op_code_col = self.dItem["OpCode"].Col

        # 셀에서 OpCode 문자열 읽기 (캐싱 적용)
        op_code_str = self.cached_read_cell(op_code_row, op_code_col)
        self.dItem["OpCode"].Str = op_code_str

        # 유효한 OpCode인지 딕셔너리로 한번에 확인
        if op_code_str in Info.dOpCode:
            self.mkMode = Info.dOpCode[op_code_str]
        else:
            self.mkMode = EMkMode.NONE
            # 빈 문자열이 아닐 경우에만 오류 기록
            if op_code_str:
                Info.WriteErrCell(EErrType.OpCode, self.ShtName, op_code_row, op_code_col)

        # 이전 모드 갱신
        self.mkModeOld = self.mkMode

    def readRow(self, row):
        """OpCode에 따른 라인별 아이템 읽기 - 성능 최적화"""
        # 열 위치 계산 최적화
        if self.mkMode == EMkMode.PRJT_DEF:
            self.dItem["Name"].Col = self.prjtDefCol
        elif self.mkMode in [EMkMode.STR_MEM, EMkMode.ENUM_MEM]:
            self.dItem["Name"].Col = self.memDfltCol
        else:
            self.dItem["Name"].Col = self.nameDfltCol

        if self.mkMode == EMkMode.PRJT_DEF:
            self.dItem["Value"].Col = self.prjtNameCol
        else:
            self.dItem["Value"].Col = self.valDfltCol

        self.dItem["Description"].Col = self.descDfltCol

        # 한번에 필요한 데이터 읽기 (캐싱 활용)
        self.dItem["Keyword"].Str = self.cached_read_cell(row, self.dItem["Keyword"].Col)
        self.dItem["Type"].Str = self.cached_read_cell(row, self.dItem["Type"].Col)
        self.dItem["Name"].Str = self.cached_read_cell(row, self.dItem["Name"].Col)
        self.dItem["Value"].Str = self.cached_read_cell(row, self.dItem["Value"].Col)

        if self.mkMode == EMkMode.ARRAY:
            self.currentArr = f"{self.ShtName}_{self.dItem['Name'].Str}_{self.arrNameCnt}"
            self.arrNameCnt += 1
            arr_type = self.chkArrInfo(row)

            if arr_type == EArrType.SizeErr:
                Info.WriteErrCell(EErrType.ArrSizeErr, self.ShtName, row, self.dItem["Name"].Col)
            elif arr_type == EArrType.Type2:
                self.dItem["Description"].Col = self.descDfltCol + self.dArr[self.currentArr].OrignalSize.Col
                self.dItem["Value"].Str = ""

        elif self.mkMode == EMkMode.PRJT_DEF:
            prjt_def = self.dItem["Name"].Str
            prjt_name = self.dItem["Value"].Str

            if not prjt_def and not prjt_name:
                # 다른 열 검사
                self.dItem["Name"].Col = self.prjtDefCol + 1
                self.dItem["Value"].Col = self.prjtNameCol + 1

                # 🔥 중복 읽기 제거: 이미 cached_read_cell 사용 중 (최적화됨)
                prjt_def = self.cached_read_cell(row, self.prjtDefCol + 1)
                prjt_name = self.cached_read_cell(row, self.prjtNameCol + 1)

            self.dItem["Name"].Str = prjt_def
            self.dItem["Value"].Str = prjt_name
            self.dItem["Description"].Col = self.dItem["Value"].Col + 2

        # 설명 읽기는 다른 컬럼 처리 후에 한 번만 수행
        self.dItem["Description"].Str = self.cached_read_cell(row, self.dItem["Description"].Col)

    def chkArrInfo(self, row):
        """배열 타입 체크 - 🚀 중복 읽기 제거 최적화"""
        arr_type = EArrType.SizeErr
        arr_size_int = SCellPos(0, 0)

        type1 = False
        type2 = False

        arr_size_str = ""
        # 🔥 중복 읽기 제거: cached_read_cell 사용
        arr_size_str1 = self.cached_read_cell(row + 1, self.memDfltCol)
        arr_size_str2 = self.cached_read_cell(row, self.dItem["Value"].Col)

        if arr_size_str1.startswith("[") and arr_size_str1.endswith("]"):
            type1 = True
        if arr_size_str2.startswith("[") and arr_size_str2.endswith("]"):
            type2 = True

        if type1 and not type2:
            arr_type = EArrType.Type1
            arr_size_str = arr_size_str1
        elif not type1 and type2:
            arr_type = EArrType.Type2
            arr_size_str = arr_size_str2
        else:
            arr_type = EArrType.SizeErr

        if arr_type != EArrType.SizeErr:
            arr_size_int = self.chkArrSize(row, arr_type, arr_size_str)

        if arr_size_int.Row < 1 and arr_size_int.Col < 1:
            arr_type = EArrType.SizeErr
        else:
            if arr_type == EArrType.Type1:
                if arr_size_int.Row == 1 and arr_size_int.Col > 10:
                    if self.chkArrtype(row, arr_size_int):
                        arr_type = EArrType.Type1
                    else:
                        arr_type = EArrType.Type3
                elif arr_size_int.Col == 1:
                    arr_type = EArrType.Type4

        self.setArrInfo(row, arr_type, arr_size_int)

        return arr_type

    def chkArrSize(self, row, arr_type, arr_size):
        """배열 사이즈 체크 - 🚀 문자열 처리 최적화"""
        arr_size_int = SCellPos(0, 0)
        # 🔥 문자열 처리 최적화: 한 번에 처리
        arr_size_str = arr_size.strip("[]")

        if "," in arr_size_str:
            row_col_split = arr_size_str.split(',')
            arr_size_int.Row = int(row_col_split[0])
            arr_size_int.Col = int(row_col_split[1])
        else:
            arr_size_int.Row = 1
            arr_size_int.Col = int(arr_size_str)

        return arr_size_int

    def setArrInfo(self, row, arr_type, arr_size):
        """배열 정보 생성"""
        orignal_size = SCellPos(0, 0)
        start_pos = SCellPos(0, 0)  # 엑셀 시트 상의 셀 위치
        end_pos = SCellPos(0, 0)    # 엑셀 시트 상의 셀 위치
        read_size = SCellPos(0, 0)

        orignal_size = SCellPos(arr_size.Row, arr_size.Col)

        if arr_type == EArrType.Type1:
            start_pos.Row = row + 1
            start_pos.Col = self.memDfltCol

            end_pos.Row = start_pos.Row + orignal_size.Row
            end_pos.Col = start_pos.Col + orignal_size.Col + 1

            read_size.Row = orignal_size.Row + 1
            read_size.Col = orignal_size.Col + 2
        elif arr_type == EArrType.Type2:
            start_pos.Row = row
            start_pos.Col = self.dItem["Value"].Col

            end_pos.Row = row
            end_pos.Col = start_pos.Col + orignal_size.Col + 1

            read_size.Row = orignal_size.Row
            read_size.Col = orignal_size.Col + 1
        elif arr_type == EArrType.Type3:
            start_pos.Row = row + 2
            start_pos.Col = self.memDfltCol + 1

            end_pos.Row = start_pos.Row
            end_pos.Col = start_pos.Col + orignal_size.Col + 1

            read_size.Row = orignal_size.Row
            read_size.Col = orignal_size.Col
        elif arr_type == EArrType.Type4:
            start_pos.Row = row + 1
            start_pos.Col = self.memDfltCol

            end_pos.Row = start_pos.Row + orignal_size.Row
            end_pos.Col = start_pos.Col + orignal_size.Col + 1

            read_size.Row = orignal_size.Row + 1
            read_size.Col = orignal_size.Col + 2

        self.dArr[self.currentArr] = ArrInfos()
        self.dArr[self.currentArr].OrignalSize = orignal_size
        self.dArr[self.currentArr].ReadSize = read_size
        self.dArr[self.currentArr].StartPos = start_pos
        self.dArr[self.currentArr].EndPos = end_pos
        self.dArr[self.currentArr].TempArr = []
        self.dArr[self.currentArr].AlignmentSize = []
        self.dArr[self.currentArr].AnnotateCol = []
        self.dArr[self.currentArr].AnnotateRow = []
        self.dArr[self.currentArr].ArrType = arr_type.value
        self.dArr[self.currentArr].IdxOn = False
        self.dArr[self.currentArr].LineAdd = False
        self.dArr[self.currentArr].ArrayDataType = self.dItem["Type"].Str

    def chkArrtype(self, row, arr_size):
        """배열 타입 확인 - 🚀 중복 읽기 제거 및 조기 종료 최적화"""
        # 🔥 벡터화된 셀 읽기로 성능 최적화
        cols_to_check = list(range(self.memDfltCol + 1, self.memDfltCol + arr_size.Col))

        # 첫 번째 행 체크 (벡터화)
        for col in cols_to_check:
            if self.cached_read_cell(row, col):
                return True

        # 두 번째 행 체크 (벡터화)
        for col in cols_to_check:
            if self.cached_read_cell(row + 1, col):
                return True

        # 세로 방향 체크 (필요한 경우만)
        for r in range(row + 2, row + 2 + arr_size.Row):
            if self.cached_read_cell(r, self.memDfltCol):
                return True

        return False

    def readArrMem(self, row):
        """배열 멤버 변수 읽기"""
        # 먼저 currentArr가 딕셔너리에 있는지 확인
        if self.currentArr not in self.dArr:
            logging.error(f"currentArr '{self.currentArr}'가 dArr 딕셔너리에 없습니다.")
            return

        # 조기 반환 조건 검사
        if self.dArr[self.currentArr].ArrType == EArrType.SizeErr.value:
            return
        if self.dArr[self.currentArr].ArrType == EArrType.Type3.value and row != self.dArr[self.currentArr].StartPos.Row:
            return

        cell_lenth = 0
        col = self.dArr[self.currentArr].StartPos.Col
        temp_line = []

        # 배열 타입 확인 - FLOAT32인지 검사
        is_float32_array = "FLOAT32" in self.dItem["Type"].Str

        # 첫 번째 행 확인 (인덱스/레이블 행)
        is_first_row = (row == self.dArr[self.currentArr].StartPos.Row)

        # 첫 번째 행의 첫 번째 셀 확인 (타이틀 셀 여부 확인용) - 🚀 캐시 사용
        first_cell_content = self.cached_read_cell(row, self.dArr[self.currentArr].StartPos.Col)
        is_label_row = is_first_row or "Idx" in first_cell_content

        # 2차원 배열 확인
        is_2d_array = self.dArr[self.currentArr].OrignalSize.Row > 1

        # Cython 최적화 사용 (배열 멤버 읽기) - 04_Python_Migration 방식
        if False:  # USE_CYTHON_CAL_LIST - 임시 비활성화 (04_Python_Migration과 동일)
            try:
                temp_line, alignment_sizes = fast_read_arr_mem_processing(
                    self.shtData,
                    row,
                    self.dArr[self.currentArr].StartPos.Col,
                    self.dArr[self.currentArr].EndPos.Col,
                    Info.ReadingXlsRule
                )

                # Alignment 크기 업데이트
                for i, size in enumerate(alignment_sizes):
                    temp_col_pos = i
                    if self.dArr[self.currentArr].ArrType == EArrType.Type3.value:
                        temp_col_pos %= 10

                    # AlignmentSize 리스트 확장
                    while temp_col_pos >= len(self.dArr[self.currentArr].AlignmentSize):
                        self.dArr[self.currentArr].AlignmentSize.append(0)

                    if size > self.dArr[self.currentArr].AlignmentSize[temp_col_pos]:
                        self.dArr[self.currentArr].AlignmentSize[temp_col_pos] = size

            except:
                # Python 폴백
                temp_line = []
                col = self.dArr[self.currentArr].StartPos.Col

        # 🚀 최적화된 Python 버전 (중복 읽기 제거)
        while col < self.dArr[self.currentArr].EndPos.Col + 1:
            # 🔥 셀 데이터 읽기 - 캐시 사용으로 중복 제거
            cell_str = self.cached_read_cell(row, col)

            # 주석 위치인지 확인
            is_annotation = (cell_str == Info.ReadingXlsRule)

            # 주석 행/열 확인 (AnnotateRow, AnnotateCol 활용)
            is_in_annotation_col = col - self.dArr[self.currentArr].StartPos.Col in self.dArr[self.currentArr].AnnotateCol
            is_in_annotation_row = row - self.dArr[self.currentArr].StartPos.Row in self.dArr[self.currentArr].AnnotateRow

            # 첫 번째 열 확인 (행 인덱스 열)
            is_first_col = (col == self.dArr[self.currentArr].StartPos.Col)

            # 빈 셀 처리
            if not cell_str:
                if col != self.dArr[self.currentArr].StartPos.Col and col != self.dArr[self.currentArr].EndPos.Col and row != self.dArr[self.currentArr].StartPos.Row:
                    Info.WriteErrCell(EErrType.EmptyCell, self.ShtName, row, col)

            if self.dArr[self.currentArr].ArrType != EArrType.Type3.value:
                if row == self.dArr[self.currentArr].StartPos.Row and col == self.dArr[self.currentArr].StartPos.Col:
                    # 첫 번째 셀은 보통 빈 셀이거나 "Idx"
                    if not cell_str:
                        cell_str = "Idx"

                if cell_str == Info.ReadingXlsRule:
                    if row == self.dArr[self.currentArr].StartPos.Row:  # Column에 주석 생성
                        col_idx = col - self.dArr[self.currentArr].StartPos.Col
                        if col_idx not in self.dArr[self.currentArr].AnnotateCol:
                            self.dArr[self.currentArr].AnnotateCol.append(col_idx)
                            self.dArr[self.currentArr].EndPos.Col += 1
                            self.dArr[self.currentArr].ReadSize.Col += 1
                    if col == self.dArr[self.currentArr].StartPos.Col:  # row에 주석 생성
                        row_idx = row - self.dArr[self.currentArr].StartPos.Row
                        if row_idx not in self.dArr[self.currentArr].AnnotateRow:
                            self.dArr[self.currentArr].AnnotateRow.append(row_idx)
                            self.dArr[self.currentArr].EndPos.Row += 1
                            self.dArr[self.currentArr].ReadSize.Row += 1
                elif cell_str:  # 인덱스 생성
                    if (row == self.dArr[self.currentArr].StartPos.Row and col > self.dArr[self.currentArr].StartPos.Col) or (row > self.dArr[self.currentArr].StartPos.Row and col == self.dArr[self.currentArr].StartPos.Col):
                        self.dArr[self.currentArr].IdxOn = True

            # 첫 번째 행일 때 AlignmentSize 초기화
            if row == self.dArr[self.currentArr].StartPos.Row:
                if col - self.dArr[self.currentArr].StartPos.Col >= len(self.dArr[self.currentArr].AlignmentSize):
                    self.dArr[self.currentArr].AlignmentSize.append(0)

            cell_str = cell_str.replace(Info.ReadingXlsRule, "")

            # 열 위치 계산
            temp_col_pos = col - self.dArr[self.currentArr].StartPos.Col

            if self.dArr[self.currentArr].ArrType == EArrType.Type3.value:
                temp_col_pos %= 10

            # 안전장치: AlignmentSize 리스트 크기 확인 및 필요 시 확장
            while temp_col_pos >= len(self.dArr[self.currentArr].AlignmentSize):
                self.dArr[self.currentArr].AlignmentSize.append(0)

            temp_line.append(cell_str)
            # 🔥 문자열 길이 계산 최적화: ASCII 문자는 빠른 계산
            if cell_str.isascii():
                cell_lenth = len(cell_str)
            else:
                cell_lenth = len(cell_str.encode('utf-8'))

            # 이제 안전하게 인덱스 접근 가능
            if cell_lenth > self.dArr[self.currentArr].AlignmentSize[temp_col_pos]:
                self.dArr[self.currentArr].AlignmentSize[temp_col_pos] = cell_lenth

            col += 1

        self.dArr[self.currentArr].TempArr.append(temp_line)

    def readyArrMemMake(self):
        """배열 만들기 위한 준비 (인덱스 라인 확인, alignment 재조정)"""
        if self.dArr[self.currentArr].ArrType == EArrType.Type3.value or self.dArr[self.currentArr].ArrType == EArrType.SizeErr.value:
            return

        if self.dArr[self.currentArr].IdxOn:
            self.dArr[self.currentArr].AnnotateRow.append(0)

        # TempArr가 비어있는지 안전 검사
        if (self.dArr[self.currentArr].AlignmentSize and
            self.dArr[self.currentArr].AlignmentSize[0] > 0 and
            self.dArr[self.currentArr].TempArr and
            len(self.dArr[self.currentArr].TempArr) > 0 and
            len(self.dArr[self.currentArr].TempArr[0]) > 0):

            self.dArr[self.currentArr].TempArr[0][0] = "Idx"
            if self.dArr[self.currentArr].AlignmentSize[0] < len(self.dArr[self.currentArr].TempArr[0][0]):
                self.dArr[self.currentArr].AlignmentSize[0] = len(self.dArr[self.currentArr].TempArr[0][0])

            self.dArr[self.currentArr].AnnotateCol.append(0)

        # TempArr[0]이 존재하는지 확인 후 처리
        if (self.dArr[self.currentArr].TempArr and
            len(self.dArr[self.currentArr].TempArr) > 0 and
            self.dArr[self.currentArr].TempArr[0]):

            for col in range(len(self.dArr[self.currentArr].TempArr[0])):
                if (col < len(self.dArr[self.currentArr].AlignmentSize) and
                    col in self.dArr[self.currentArr].AnnotateCol and
                    self.dArr[self.currentArr].AlignmentSize[col] != 0):
                    if col == 0 or (col != 0 and (col - 1) not in self.dArr[self.currentArr].AnnotateCol):
                        self.dArr[self.currentArr].AlignmentSize[col] += len("Idx")

    def writeArrMem(self):
        """배열 만들기 - 04_Python_Migration 방식 (성능 최적화)"""
        # 성능 최적화: 자주 사용되는 객체 참조 미리 저장
        current_arr_data = self.dArr[self.currentArr]
        row = current_arr_data.RowCnt
        max_col = 0
        src_data_str = None
        antt_cnt = 0
        empty_or_comma = ""

        # 성능 최적화: 자주 사용되는 값들 미리 계산
        arr_type = current_arr_data.ArrType
        original_size_row = current_arr_data.OrignalSize.Row
        temp_arr = current_arr_data.TempArr
        alignment_size = current_arr_data.AlignmentSize
        read_size_col = current_arr_data.ReadSize.Col

        # 성능 최적화: 리스트를 set으로 변환 (O(n) → O(1) 검색)
        annotate_row_set = set(current_arr_data.AnnotateRow)
        annotate_col_set = set(current_arr_data.AnnotateCol)

        # 조건 검사
        if (arr_type == EArrType.SizeErr.value or
            (arr_type != EArrType.Type3.value and
            (row == 0 and not current_arr_data.IdxOn)) or
            (arr_type == EArrType.Type3.value and row > 0)):
            return None

        # 성능 최적화: set 사용으로 O(1) 검색
        is_annotate_row = row in annotate_row_set
        if is_annotate_row:
            src_data_str = "/*\t"
        else:
            src_data_str = "\t"

        # 다차원 배열 처리
        if original_size_row > 1 and arr_type != EArrType.Type4.value:
            if is_annotate_row:
                src_data_str += "\t"
            else:
                src_data_str += "{\t"

        # 열 수 계산
        max_col = read_size_col
        if arr_type != EArrType.Type3.value:
            max_col -= 1

        # 성능 최적화: 배열 값 처리 (범위 체크 최소화)
        temp_arr_len = len(temp_arr)
        for col in range(max_col):
            # 성능 최적화: 범위 체크 최소화
            if row >= temp_arr_len:
                return None

            temp_arr_row = temp_arr[row]
            if col >= len(temp_arr_row):
                return None

            cell_str = temp_arr_row[col]

            # Float suffix 기능 (04_Python_Migration 방식)
            # 주석 행/열에서는 Float Suffix 적용 제외
            is_comment_context = (row in annotate_row_set or col in annotate_col_set or
                                '/*' in cell_str or '//' in cell_str)
            if (ENABLE_FLOAT_SUFFIX and hasattr(self, 'float_suffix_patterns') and self.float_suffix_patterns and
                not is_comment_context):
                cell_str = self._apply_float_suffix(cell_str)

            # 주석 열 처리
            if col in self.dArr[self.currentArr].AnnotateCol:
                # 배열 크기 안전 검사
                if col < len(self.dArr[self.currentArr].AlignmentSize):
                    if not cell_str.strip():
                        empty_or_comma = " "
                    else:
                        empty_or_comma = ","

                    # 주석 형식 처리
                    if row in self.dArr[self.currentArr].AnnotateRow:
                        # 첫 레이블 행의 레이블은 특별 처리
                        if col == 0 or (col-1) not in self.dArr[self.currentArr].AnnotateCol:
                            antt_cnt = 0
                            cell_str = "   " + cell_str
                    else:
                        # 첫 번째 주석 열이거나 이전 열이 주석이 아닌 경우
                        if col == 0 or (col-1) not in self.dArr[self.currentArr].AnnotateCol:
                            antt_cnt = 0
                            cell_str = "/* " + cell_str

                    src_data_str += cell_str

                    # 다음 주석 열이 있는 경우 패딩 추가
                    if (col+1) in self.dArr[self.currentArr].AnnotateCol:
                        padding = self.dArr[self.currentArr].AlignmentSize[col] - len(cell_str.encode('utf-8')) + 2
                        src_data_str += empty_or_comma.ljust(padding)
                        antt_cnt += self.dArr[self.currentArr].AlignmentSize[col] + 2
                    else:
                        # 주석 종료 처리
                        if row in self.dArr[self.currentArr].AnnotateRow:
                            padding = self.dArr[self.currentArr].AlignmentSize[col] - len(cell_str.encode('utf-8')) + 3
                            src_data_str += empty_or_comma.ljust(padding)
                        else:
                            padding = self.dArr[self.currentArr].AlignmentSize[col] - len(cell_str.encode('utf-8')) + 1
                            src_data_str += " ".ljust(padding) + "*/"

                            # 빈 주석 처리
                            temp = src_data_str.replace("/*", "").replace("*/", "").replace("{", "").replace("\t", "")
                            if not temp.strip():
                                src_data_str = src_data_str.replace("/*", "  ").replace("*/", "  ")

                        antt_cnt += self.dArr[self.currentArr].AlignmentSize[col] + 3

                        # 주석 열 뒤에 탭 추가 (정렬을 위해)
                        src_data_str += "\t"
                        if antt_cnt % Info.TabSize > 2:
                            src_data_str += "\t"
                else:
                    # AlignmentSize 범위를 벗어나는 경우 기본 처리
                    src_data_str += cell_str + ", "

            # 마지막 열 처리
            elif col == max_col - 1:
                src_data_str += cell_str

                # 마지막 셀 처리 (다차원 배열 및 주석 행 고려)
                if ((self.dArr[self.currentArr].ArrType == EArrType.Type1.value and
                    self.dArr[self.currentArr].OrignalSize.Row > 1) or
                    row in self.dArr[self.currentArr].AnnotateRow):

                    # 안전 검사 추가
                    if col < len(self.dArr[self.currentArr].AlignmentSize):
                        pad_tab_cnt = self.calculatePad(
                            self.dArr[self.currentArr].AlignmentSize[col] - 1,
                            len(cell_str.encode('utf-8')) - 1,
                            True, 1
                        )
                        src_data_str += "\t".ljust(pad_tab_cnt - 1, '\t')

            # Type3 또는 Type4가 아닌 경우 처리
            elif (self.dArr[self.currentArr].ArrType == EArrType.Type3.value or
                (self.dArr[self.currentArr].ArrType != EArrType.Type4.value and col != 0)):

                temp_col = col
                if self.dArr[self.currentArr].ArrType == EArrType.Type3.value:
                    temp_col %= 10

                src_data_str += cell_str

                # Type3 배열의 특수 처리
                if (self.dArr[self.currentArr].ArrType == EArrType.Type3.value) and (temp_col == 9):
                    src_data_str += ","
                else:
                    # 처리 중인 셀이 빈 문자열인지 확인
                    if not cell_str.strip():
                        empty_or_comma = " "
                    else:
                        empty_or_comma = ","

                    # 안전 검사 추가
                    if temp_col < len(self.dArr[self.currentArr].AlignmentSize):
                        # 콤마 뒤의 간격 조정
                        pad_tab_cnt = self.calculatePad(
                            self.dArr[self.currentArr].AlignmentSize[temp_col],
                            len(cell_str.encode('utf-8')),
                            True, 1
                        )
                        src_data_str += empty_or_comma.ljust(pad_tab_cnt, '\t')
                    else:
                        # 기본 간격 사용
                        src_data_str += empty_or_comma + "\t"

                # Type3 배열의 줄바꿈 처리
                if self.dArr[self.currentArr].ArrType == EArrType.Type3.value and (col % 10 == 9):
                    src_data_str += "\r\n\t"

        # 주석 행 닫기
        if row in self.dArr[self.currentArr].AnnotateRow:
            src_data_str += "*/"
        # 다차원 배열 행 닫기
        elif self.dArr[self.currentArr].OrignalSize.Row > 1:
            if self.dArr[self.currentArr].ArrType != EArrType.Type4.value:
                src_data_str += "}"

            if row < self.dArr[self.currentArr].ReadSize.Row - 1:
                src_data_str += ","

        # 배열 요소 뒤에 주석 처리
        if row < len(self.dArr[self.currentArr].TempArr) and len(self.dArr[self.currentArr].TempArr[row]) > self.dArr[self.currentArr].ReadSize.Col - 1:
            # 주석 있는지 확인
            comment = self.dArr[self.currentArr].TempArr[row][self.dArr[self.currentArr].ReadSize.Col - 1].strip()
            if comment:
                if self.dArr[self.currentArr].ArrType == EArrType.Type4.value:
                    if self.dArr[self.currentArr].ReadSize.Col - 2 < len(self.dArr[self.currentArr].AlignmentSize):
                        pad_tab_cnt = ((self.dArr[self.currentArr].AlignmentSize[self.dArr[self.currentArr].ReadSize.Col - 2] + 1) // Info.TabSize) + 1
                        tab_padding = pad_tab_cnt - ((len(self.dArr[self.currentArr].TempArr[row][self.dArr[self.currentArr].ReadSize.Col - 2]) + 1) // Info.TabSize)
                        src_data_str += "\t".ljust(tab_padding, '\t')

                if self.dArr[self.currentArr].ArrType != EArrType.Type3.value:
                    src_data_str += "\t// " + comment

        # 배열 마지막에 닫는 괄호 추가 (추가 줄바꿈 명시적 포함)
        if self.dArr[self.currentArr].RowCnt == self.dArr[self.currentArr].ReadSize.Row - 1:
            src_data_str += "\r\n};\r\n\r\n"  # 추가 줄바꿈 포함

        return src_data_str

    def _apply_float_suffix(self, cell_str):
        """셀 문자열에 Float Suffix 적용 (04_Python_Migration 방식 개선)"""
        if not cell_str:
            return cell_str

        # Cython 버전 우선 사용 (성능 최적화)
        if ENABLE_FLOAT_SUFFIX and USE_CYTHON_CAL_LIST:
            fast_add_float_suffix = safe_import_cython_function('code_generator_v2', 'fast_add_float_suffix')
            if fast_add_float_suffix:
                try:
                    return fast_add_float_suffix(cell_str)
                except Exception:
                    pass  # 실패 시 Python 폴백

        # Python 폴백 (04_Python_Migration 방식)
        if not ENABLE_FLOAT_SUFFIX:
            return cell_str

        # 정규식을 사용한 더 정확한 처리
        import re

        # 이미 f 접미사가 있는 경우 그대로 반환
        if cell_str.endswith('f') or cell_str.endswith('F'):
            return cell_str

        # 주석이 포함된 경우 처리하지 않음
        if '/*' in cell_str or '//' in cell_str:
            return cell_str

        try:
            # 단어별로 분리해서 처리 (정규식 중복 적용 방지)
            words = re.split(r'(\s+|[^\w\.])', cell_str)
            result_words = []

            for word in words:
                if not word or not re.match(r'^\d+\.?\d*$', word):
                    result_words.append(word)
                    continue

                # 이미 f가 있으면 건드리지 않음
                if word.endswith('f') or word.endswith('F'):
                    result_words.append(word)
                    continue

                # 소수점이 있는 숫자: 1.5 -> 1.5f, 3. -> 3.f
                if '.' in word:
                    result_words.append(word + 'f')
                # 정수: 1 -> 1.f
                else:
                    result_words.append(word + '.f')

            cell_str = ''.join(result_words)

        except Exception as e:
            # 정규식 오류 시 간단한 방식으로 폴백
            try:
                # 소수점이 있는 숫자
                if '.' in cell_str and cell_str.replace('.', '').replace('-', '').isdigit():
                    if not cell_str.endswith('f') and not cell_str.endswith('F'):
                        return cell_str + 'f'
                # 정수 (0 포함)
                elif cell_str.isdigit():
                    return cell_str + '.f'
                # 음수 정수
                elif cell_str.startswith('-') and cell_str[1:].isdigit():
                    return cell_str + '.f'
            except:
                pass

        return cell_str

    def _apply_float_suffix_to_float32_block(self, block_str):
        """FLOAT32 블록에 Float Suffix 적용 (04_Python_Migration 방식)"""
        if not block_str:
            return block_str

        if not ENABLE_FLOAT_SUFFIX:
            return block_str

        # Cython 버전 사용 (C 수준 성능 - 정규식 없음)
        if USE_CYTHON_CAL_LIST:
            fast_add_float_suffix = safe_import_cython_function('code_generator_v2', 'fast_add_float_suffix')
            if fast_add_float_suffix:
                try:
                    # 1. Float suffix 적용
                    result = fast_add_float_suffix(block_str)
                    return result
                except Exception:
                    pass  # 실패 시 Python 폴백

        # Python 폴백 (정규식 버전)
        if not hasattr(self, 'float_suffix_patterns') or not self.float_suffix_patterns:
            return block_str

        # 주석 보존
        comments = {}
        comment_count = 0

        # 블록 주석 처리
        for comment in self.float_suffix_patterns['block_comment'].finditer(block_str):
            placeholder = f"__COMMENT_BLOCK_{comment_count}__"
            comments[placeholder] = comment.group(0)
            block_str = block_str.replace(comment.group(0), placeholder)
            comment_count += 1

        # 라인 주석 처리
        for comment in self.float_suffix_patterns['line_comment'].finditer(block_str):
            placeholder = f"__COMMENT_LINE_{comment_count}__"
            comments[placeholder] = comment.group(0)
            block_str = block_str.replace(comment.group(0), placeholder)
            comment_count += 1

        # 숫자 패턴 적용
        block_str = self.float_suffix_patterns['decimal'].sub(r'\1f', block_str)
        block_str = self.float_suffix_patterns['decimal_point_only'].sub(r'\1f', block_str)
        block_str = self.float_suffix_patterns['integer'].sub(r'\1.f', block_str)
        block_str = self.float_suffix_patterns['zero'].sub(r'0.f', block_str)

        # 수식 내 숫자 처리
        block_str = self.float_suffix_patterns['expression_decimal'].sub(r'\1\2\3f', block_str)
        block_str = self.float_suffix_patterns['expression_int'].sub(r'\1\2\3.f', block_str)

        # 괄호 내 숫자 처리
        block_str = self.float_suffix_patterns['paren_decimal'].sub(r'(\1\2f', block_str)
        block_str = self.float_suffix_patterns['paren_int'].sub(r'(\1\2.f', block_str)

        # 정수형 타입에 잘못 붙은 .f 제거
        if 'integer_types' in self.float_suffix_patterns:
            block_str = self.float_suffix_patterns['integer_types'].sub(r'\1\2', block_str)

        # 주석 복원
        for placeholder, comment in comments.items():
            block_str = block_str.replace(placeholder, comment)

        return block_str

    def add_float_suffix(self, cell_str, array_type):
        """
        Float Suffix 추가 함수 (04_Python_Migration에서 이식)
        FLOAT32 타입 배열의 숫자 값에 .f 접미사 추가
        """
        # FLOAT32 타입이 아니면 원본 반환
        if not array_type or "FLOAT32" not in array_type:
            return cell_str

        return self._apply_float_suffix(cell_str)

    def setPragmaSection(self, key_str, row):
        """프라그마 설정"""
        if (self.pragSet or
            (not self.pragSet and self.currentPRGM == key_str and self.mkMode != EMkMode.PRGM_SET) or
            (key_str not in self.fi.dPragma and self.currentPRGM not in self.fi.dPragma)):
            return

        if self.currentPRGM in self.fi.dPragma:
            cnt = 0

            for i in range(len(self.dTempCode[self.currentTitle]) - 1, -1, -1):
                op_code_str = self.dTempCode[self.currentTitle][i][0]
                mode = Info.dOpCode[op_code_str]

                if mode in [EMkMode.DESCRIPT, EMkMode.SUBTITLE, EMkMode.PRJT_DEF, EMkMode.TITLE, EMkMode.TITLE_S, EMkMode.TITLE_H]:
                    cnt += 1
                else:
                    break

            self.dTempCode[self.currentTitle].insert(len(self.dTempCode[self.currentTitle]) - cnt,
                                                    ["$PRGM_END", self.currentPRGM, "", "", "", ""])
            self.currentPRGM = ""

        if key_str in self.fi.dPragma and self.mkMode != EMkMode.PRGM_SET:
            self.dTempCode[self.currentTitle].append(["$PRGM_SET", key_str, "", "", "", ""])
            self.currentPRGM = key_str

    def writePragma(self, mode, key_str, empty_line):
        """프라그마 작성"""
        pragma_set = "#pragma section "
        pragma_str = ""

        if key_str not in self.fi.dPragma:
            return ""

        class_1 = self.fi.dPragma[key_str][0]
        class_2 = self.fi.dPragma[key_str][1]

        # 전처리기 지시문 앞에 빈 줄 추가
        if not empty_line:
            pragma_str = "\r\n"

        if class_1.PreCode:
            pragma_str += class_1.PreCode + "\r\n"

        if mode == EMkMode.PRGM_SET:
            pragma_str += f"{pragma_set} {class_1.ClassName} \"{class_1.SetIstring}\" \"{class_1.SetUstring}\" {class_1.SetAddrMode}\r\n"
            pragma_str += f"{pragma_set} {class_2.ClassName} \"{class_2.SetIstring}\" \"{class_2.SetUstring}\" {class_2.SetAddrMode}\r\n"
        elif mode == EMkMode.PRGM_END:
            pragma_str += f"{pragma_set} {class_1.ClassName} \"{class_1.EndIstring}\" \"{class_1.EndUstring}\" \r\n"
            pragma_str += f"{pragma_set} {class_2.ClassName} \"{class_2.EndIstring}\" \"{class_2.EndUstring}\" \r\n"

        if class_1.EndCode:
            pragma_str += class_1.EndCode + "\r\n"

        return pragma_str


    def chkCalList(self, row):
        """아이템 오류 체크 - Cython 최적화"""
        name_str = self.dItem["Name"].Str
        val_str = self.dItem["Value"].Str
        type_str = self.dItem["Type"].Str
        key_str = self.dItem["Keyword"].Str
        desc_str = self.dItem["Description"].Str

        # Cython 최적화 적용 (빠른 검증) - 안전한 동적 import
        if USE_CYTHON_CAL_LIST:
            fast_chk_cal_list_processing = safe_import_cython_function('code_generator_v2', 'fast_chk_cal_list_processing')
            if fast_chk_cal_list_processing:
                try:
                    errors = fast_chk_cal_list_processing(name_str, val_str, type_str, key_str, desc_str)
                    for error in errors:
                        logging.debug(f"Validation error at row {row}: {error}")
                except Exception as e:
                    logging.debug(f"Cython 검증 처리 중 오류 발생, Python 폴백 사용: {e}")

        # 기존 Python 버전 (상세 검증)

        if self.mkMode in [EMkMode.TITLE, EMkMode.TITLE_S, EMkMode.TITLE_H]:
            title = f"{self.mkMode.name}+{key_str}"
            if not title:
                Info.WriteErrCell(EErrType.EmptyCell, self.ShtName, row, self.dItem["Keyword"].Col)
            elif title in self.dTempCode:
                Info.WriteErrCell(EErrType.TitleName, self.ShtName, row, self.dItem["Keyword"].Col)
            else:
                temp_mk_file = EMkFile.All
                self.dTempCode[title] = []

                if self.mkMode != EMkMode.TITLE_S:
                    self.dHdrCode[title] = []
                if self.mkMode != EMkMode.TITLE_H:
                    self.dSrcCode[title] = []

                if self.prjtDepth >= 0:
                    for i in range(self.prjtDepth, -1, -1):
                        self.prjtList[i] = SPrjtInfo(name_str, [])

                if self.mkMode == EMkMode.TITLE_S:
                    temp_mk_file = EMkFile.Src
                elif self.mkMode == EMkMode.TITLE_H:
                    temp_mk_file = EMkFile.Hdr
                else:
                    temp_mk_file = EMkFile.All

                if title not in self.titleList:
                    self.titleList[title] = temp_mk_file

            if self.currentTitle.endswith(Info.EndPrjtName) and self.pragSet:
                Info.WriteErrCell(EErrType.PrgmWrite, self.ShtName, row, self.dItem["OpCode"].Col)

            self.prjtDepth = -1
            self.currentPrjtDef = ""

        elif self.mkMode == EMkMode.SUBTITLE:
            if not name_str:
                Info.WriteErrCell(EErrType.EmptyCell, self.ShtName, row, self.dItem["Name"].Col)

        elif self.mkMode == EMkMode.DEFINE:
            if not name_str:
                Info.WriteErrCell(EErrType.EmptyCell, self.ShtName, row, self.dItem["Name"].Col)
            if not val_str:
                Info.WriteErrCell(EErrType.EmptyCell, self.ShtName, row, self.dItem["Value"].Col)

        elif self.mkMode == EMkMode.STR_MEM:
            if not type_str:
                Info.WriteErrCell(EErrType.EmptyCell, self.ShtName, row, self.dItem["Type"].Col)
            if not name_str:
                Info.WriteErrCell(EErrType.EmptyCell, self.ShtName, row, self.dItem["Name"].Col)

        elif self.mkMode == EMkMode.STR_DEF:
            if not name_str:
                Info.WriteErrCell(EErrType.EmptyCell, self.ShtName, row, self.dItem["Name"].Col)

        elif self.mkMode == EMkMode.ENUM_MEM:
            if not name_str:
                Info.WriteErrCell(EErrType.EmptyCell, self.ShtName, row, self.dItem["Name"].Col)

        elif self.mkMode == EMkMode.ARRAY:
            if not key_str:
                Info.WriteErrCell(EErrType.EmptyCell, self.ShtName, row, self.dItem["Keyword"].Col)
            if not type_str:
                Info.WriteErrCell(EErrType.EmptyCell, self.ShtName, row, self.dItem["Type"].Col)
            if not name_str:
                Info.WriteErrCell(EErrType.EmptyCell, self.ShtName, row, self.dItem["Name"].Col)

            if self.dArr[self.currentArr].ArrType == EArrType.Type2.value:
                self.dItem["Value"].Str = ""
                for i in range(self.dArr[self.currentArr].OrignalSize.Col):
                    arr_value = Info.ReadCell(self.shtData, row, self.dItem["Value"].Col + 1 + i)

                    if not arr_value:
                        Info.WriteErrCell(EErrType.EmptyCell, self.ShtName, row, self.dItem["Value"].Col + 1 + i)
                    else:
                        if i == 0:
                            self.dItem["Value"].Str = "{ "

                        if i < self.dArr[self.currentArr].OrignalSize.Col - 1:
                            arr_value += ","

                        self.dItem["Value"].Str += arr_value

                        for cnt in range(Info.TabSize - (len(arr_value) % Info.TabSize)):
                            self.dItem["Value"].Str += " "

                        if i == self.dArr[self.currentArr].OrignalSize.Col - 1:
                            self.dItem["Value"].Str += "}"

        elif self.mkMode == EMkMode.VARIABLE:
            if not key_str:
                Info.WriteErrCell(EErrType.EmptyCell, self.ShtName, row, self.dItem["Keyword"].Col)
            if not type_str:
                Info.WriteErrCell(EErrType.EmptyCell, self.ShtName, row, self.dItem["Type"].Col)
            if not name_str:
                Info.WriteErrCell(EErrType.EmptyCell, self.ShtName, row, self.dItem["Name"].Col)
            if not val_str:
                Info.WriteErrCell(EErrType.EmptyCell, self.ShtName, row, self.dItem["Value"].Col)
            elif "[" in val_str or "]" in val_str:
                Info.WriteErrCell(EErrType.OpCode, self.ShtName, row, self.dItem["OpCode"].Col)

        elif self.mkMode == EMkMode.CODE:
            if not name_str:
                Info.WriteErrCell(EErrType.EmptyCell, self.ShtName, row, self.dItem["Name"].Col)

        elif self.mkMode == EMkMode.PRGM_SET:
            if not key_str:
                Info.WriteErrCell(EErrType.EmptyCell, self.ShtName, row, self.dItem["Keyword"].Col)
            if key_str not in self.fi.dPragma:
                Info.WriteErrCell(EErrType.PrgmWrite, self.ShtName, row, self.dItem["Keyword"].Col)

            self.setPragmaSection(key_str, row)
            self.currentPRGM = key_str
            self.pragSet = True

        elif self.mkMode == EMkMode.PRGM_END:
            if not key_str:
                Info.WriteErrCell(EErrType.EmptyCell, self.ShtName, row, self.dItem["Keyword"].Col)
            if self.currentPRGM != key_str:
                Info.WriteErrCell(EErrType.PrgmWrite, self.ShtName, row, self.dItem["Keyword"].Col)

            self.currentPRGM = ""
            self.pragSet = False

        elif self.mkMode == EMkMode.PRJT_DEF:
            if not name_str:
                Info.WriteErrCell(EErrType.PrjtEmpty, self.ShtName, row, self.dItem["Name"].Col)
            if not val_str and (name_str != "1" and name_str != "0"):
                Info.WriteErrCell(EErrType.PrjtEmpty, self.ShtName, row, self.dItem["Value"].Col)

            rt = False
            if name_str != self.currentPrjtDef:
                for i in range(self.prjtDepth, -1, -1):
                    if self.prjtList[i].Def == name_str:
                        temp_depth = self.prjtDepth
                        for j in range(self.prjtDepth - i):
                            tab_str = ""
                            for k in range(temp_depth):
                                tab_str += "\t"
                            temp_str = tab_str + "#else\r\n"
                            temp_str += tab_str + "\t#error undefined " + self.prjtList[self.prjtDepth - j].Def + " MACRO\r\n\r\n"
                            temp_str += tab_str + "#endif\r\n\r\n"

                            self.prjtList[temp_depth] = SPrjtInfo(name_str, [])
                            temp_depth -= 1

                        self.prjtDepth = temp_depth
                        rt = True
                        break

            if name_str != self.currentPrjtDef and not rt:
                self.prjtDepth += 1

                if name_str == self.PrjtDefMain:
                    Info.WriteErrCell(EErrType.PrjtSame, self.ShtName, row, self.prjtDefCol)

                if self.prjtDepth >= 0 and val_str in self.prjtList[self.prjtDepth].Val:
                    Info.WriteErrCell(EErrType.PrjtSame, self.ShtName, row, self.prjtNameCol)

                if val_str == Info.ElsePrjtName or val_str == Info.EndPrjtName:
                    Info.WriteErrCell(EErrType.PrjtErr, self.ShtName, row, self.prjtNameCol)

                self.prjtList[self.prjtDepth] = SPrjtInfo(name_str, [])
                self.prjtList[self.prjtDepth].Val.append(val_str)
                self.currentPrjtDef = name_str
            else:
                if val_str in self.prjtList[self.prjtDepth].Val:
                    Info.WriteErrCell(EErrType.PrjtSame, self.ShtName, row, self.prjtNameCol)

                if val_str == Info.ElsePrjtName:
                    self.prjtList[self.prjtDepth].Val.append(val_str)
                    self.currentPrjtDef = name_str
                elif val_str == Info.EndPrjtName:
                    self.prjtList[self.prjtDepth] = SPrjtInfo(name_str, [])
                    self.prjtDepth -= 1
                    self.currentPrjtDef = ""
                else:
                    self.prjtList[self.prjtDepth].Val.append(val_str)
                    self.currentPrjtDef = name_str

    def saveTempList(self, row):
        """코드생성 전 아이템 임시 저장 - Cython 최적화"""
        op_code_str = self.dItem["OpCode"].Str
        name_str = self.dItem["Name"].Str
        val_str = self.dItem["Value"].Str
        type_str = self.dItem["Type"].Str
        key_str = self.dItem["Keyword"].Str
        desc_str = self.dItem["Description"].Str

        # Cython 최적화 적용 (빠른 임시 저장) - 안전한 동적 import
        if USE_CYTHON_CAL_LIST:
            fast_save_temp_list_processing = safe_import_cython_function('code_generator_v2', 'fast_save_temp_list_processing')
            if fast_save_temp_list_processing:
                try:
                    temp_item = fast_save_temp_list_processing(op_code_str, key_str, type_str, name_str, val_str, desc_str)
                    # 결과 검증 후 사용
                    if temp_item and len(temp_item) == 6:
                        op_code_str, key_str, type_str, name_str, val_str, desc_str = temp_item
                except Exception:
                    pass  # 실패 시 Python 폴백

        if (self.mkMode == EMkMode.TITLE or self.mkMode == EMkMode.TITLE_S or
            self.mkMode == EMkMode.TITLE_H):
            self.currentTitle = self.mkMode.name + "+" + key_str

        if (self.mkMode == EMkMode.VARIABLE or self.mkMode == EMkMode.ARRAY or
            self.mkMode == EMkMode.TITLE or self.mkMode == EMkMode.TITLE_S or
            self.mkMode == EMkMode.TITLE_H):
            self.setPragmaSection(key_str, row)

        # 🔥 핵심 수정: currentTitle이 비어있거나 dTempCode에 키가 없는 경우 처리
        if not self.currentTitle:
            # 기본 타이틀 생성 (첫 번째 데이터인 경우)
            self.currentTitle = "TITLE+DEFAULT"
            logging.warning(f"시트 {self.ShtName}: currentTitle이 비어있어 기본값 설정")

        # dTempCode에 키가 없는 경우 생성
        if self.currentTitle not in self.dTempCode:
            self.dTempCode[self.currentTitle] = []
            logging.info(f"시트 {self.ShtName}: dTempCode에 새 키 생성 - {self.currentTitle}")

        self.dTempCode[self.currentTitle].append([op_code_str, key_str, type_str, name_str, val_str, desc_str])

        # alignment 정보 저장
        if (self.mkMode == EMkMode.DEFINE or self.mkMode == EMkMode.STR_MEM or
            self.mkMode == EMkMode.ENUM_MEM or self.mkMode == EMkMode.VARIABLE or
            (self.mkMode == EMkMode.ARRAY and self.dArr[self.currentArr].ArrType == EArrType.Type2.value)):
            if len(key_str) > self.itemLength[0]:
                self.itemLength[0] = len(key_str)
            if len(type_str) > self.itemLength[1]:
                self.itemLength[1] = len(type_str)
            if len(name_str) > self.itemLength[2]:
                self.itemLength[2] = len(name_str)
            if len(val_str) > self.itemLength[3]:
                self.itemLength[3] = len(val_str)
        elif (self.mkMode == EMkMode.TITLE or self.mkMode == EMkMode.TITLE_S or
            self.mkMode == EMkMode.TITLE_H or self.mkMode == EMkMode.SUBTITLE or
            self.mkMode == EMkMode.DESCRIPT or self.mkMode == EMkMode.STR_DEF or
            self.mkMode == EMkMode.ENUM_END or self.mkMode == EMkMode.NONE or
            self.mkMode == EMkMode.PRJT_DEF):
            self.ArrAlignList.append([self.itemLength[0], self.itemLength[1],
                                    self.itemLength[2], self.itemLength[3]])
            self.itemLength = [0, 0, 0, 0]


    def writeCalList(self, line_str):
        """코드생성 아이템 임시 저장"""
        empty_src = False
        empty_hdr = False

        # 🔥 핵심 수정: currentTitle 검증 및 초기화
        if not self.currentTitle:
            self.currentTitle = "TITLE+DEFAULT"
            logging.warning(f"시트 {self.ShtName}: writeCalList에서 currentTitle이 비어있어 기본값 설정")

        # dSrcCode, dHdrCode에 키가 없는 경우 생성
        if self.currentTitle not in self.dSrcCode:
            self.dSrcCode[self.currentTitle] = []
        if self.currentTitle not in self.dHdrCode:
            self.dHdrCode[self.currentTitle] = []

        if self.currentTitle in self.dSrcCode:
            empty_src = Info.ExistEmptyStr(self.dSrcCode[self.currentTitle], 1)
        if self.currentTitle in self.dHdrCode:
            empty_hdr = Info.ExistEmptyStr(self.dHdrCode[self.currentTitle], 1)

        src_data_str = ""
        hdr_data_str = ""

        op_code_str = line_str[0]
        key_str = line_str[1]
        type_str = line_str[2]
        name_str = line_str[3]
        val_str = line_str[4]
        desc_str = line_str[5]

        # Cython 직접 호출을 통한 통합 처리 (Excel 셀 처리 + 데이터 변환 + Float Suffix)
        if CYTHON_CODE_GEN_AVAILABLE:
            try:
                # 1. Excel 셀 값 처리 (Cython 직접 호출)
                try:
                    from excel_processor_v2 import process_cell_value_fast
                    val_str = process_cell_value_fast(str(val_str))
                except ImportError:
                    val_str = str(val_str) if val_str is not None else ""

                # 2. 데이터 타입 변환 (Cython 직접 호출)
                if type_str and val_str:
                    try:
                        from data_processor import fast_data_type_conversion
                        converted_data = fast_data_type_conversion([val_str], type_str)
                        if converted_data and len(converted_data) > 0:
                            val_str = converted_data[0]
                    except ImportError:
                        pass

                # 3. Float Suffix 처리 (이미 enhanced_excel_cell_processing에서 처리됨)
                # 추가 Float Suffix 처리가 필요한 경우
                if ENABLE_FLOAT_SUFFIX and type_str == "FLOAT32" and val_str:
                    if USE_CYTHON_CAL_LIST:
                        fast_add_float_suffix = safe_import_cython_function('code_generator_v2', 'fast_add_float_suffix')
                        if fast_add_float_suffix:
                            try:
                                val_str = fast_add_float_suffix(val_str)
                            except Exception:
                                pass
            except Exception as e:
                logging.debug(f"Cython 래퍼 처리 실패, Python 폴백 사용: {e}")
                # Python 폴백
                if ENABLE_FLOAT_SUFFIX and type_str == "FLOAT32" and val_str:
                    val_str = self._apply_float_suffix(val_str)
        else:
            # 기존 Python 방식 (폴백)
            if ENABLE_FLOAT_SUFFIX and type_str == "FLOAT32" and val_str:
                val_str = self._apply_float_suffix(val_str)

        # ArrAlignList 인덱스 범위 체크 및 기본값 설정
        if self.alignCnt < len(self.ArrAlignList):
            key_align = self.ArrAlignList[self.alignCnt][0]
            type_align = self.ArrAlignList[self.alignCnt][1]
            name_align = self.ArrAlignList[self.alignCnt][2]
            val_align = self.ArrAlignList[self.alignCnt][3]
        else:
            # 기본값 설정
            key_align = 15
            type_align = 15
            name_align = 15
            val_align = 15

        if op_code_str in Info.dOpCode:
           mk_mode = Info.dOpCode[op_code_str]
        else:
            mk_mode = EMkMode.NONE

        temp_list = []

        temp_str = ""

        if desc_str:
            desc_str = "// " + desc_str

        if mk_mode == EMkMode.TITLE or mk_mode == EMkMode.TITLE_S or mk_mode == EMkMode.TITLE_H:
            if self.prjtDepth >= 0:
                for i in range(self.prjtDepth, -1, -1):
                    tab_str = ""
                    for j in range(i):
                        tab_str += "\t"

                    if self.prjtList[i].Val[-1] != Info.ElsePrjtName:
                        temp_list.append(tab_str + "#else")
                        temp_list.append(tab_str + "\t#error undefined " + self.prjtList[i].Def + " MACRO")
                        temp_list.append("")
                    temp_list.append(tab_str + "#endif")

                    if i > 0:
                        temp_list.append("")

                    self.prjtList[i] = SPrjtInfo(name_str, [])

                if self.mkFile != EMkFile.Src:
                    if not empty_hdr:
                        self.dHdrCode[self.currentTitle].append("")
                    self.dHdrCode[self.currentTitle].extend(temp_list)
                if self.mkFile != EMkFile.Hdr:
                    if not empty_src:
                        self.dSrcCode[self.currentTitle].append("")
                    self.dSrcCode[self.currentTitle].extend(temp_list)

            if mk_mode == EMkMode.TITLE_S:
                self.mkFile = EMkFile.Src
            elif mk_mode == EMkMode.TITLE_H:
                self.mkFile = EMkFile.Hdr
            else:
                temp_title = key_str.upper()
                if "DEFINE" in temp_title or "TYPE" in temp_title or "MACRO" in temp_title:
                    self.mkFile = EMkFile.Hdr
                else:
                    self.mkFile = EMkFile.All

            self.prjtDepth = -1
            self.frontTab = ""
            self.currentTitle = mk_mode.name + "+" + key_str
            self.currentPrjtDef = ""

        elif mk_mode == EMkMode.SUBTITLE:
            temp_str = Info.StartAnnotation[2] + "\r\n\t@name\t: " + name_str + "\r\n" + Info.EndAnnotation[2]

            if self.mkFile != EMkFile.Src:
                if not empty_hdr:
                    hdr_data_str = "\r\n"
                hdr_data_str += temp_str
            if self.mkFile != EMkFile.Hdr:
                if not empty_src:
                    src_data_str = "\r\n"
                src_data_str += temp_str

        elif mk_mode == EMkMode.DESCRIPT:
            temp_str = "/* " + name_str + " */"

            if name_str:
                if self.mkFile != EMkFile.Src:
                    if not empty_hdr:
                        hdr_data_str = "\r\n"
                    hdr_data_str += temp_str
                if self.mkFile != EMkFile.Hdr:
                    if not empty_src:
                        src_data_str = "\r\n"
                    src_data_str += temp_str

        elif mk_mode == EMkMode.DEFINE:
            # Cython 직접 호출을 통한 DEFINE 코드 생성 (안전한 동적 import)
            if CYTHON_CODE_GEN_AVAILABLE:
                fast_define_code_generation = safe_import_cython_function('code_generator_v2', 'fast_define_code_generation')
                if fast_define_code_generation:
                    try:
                        temp_str = fast_define_code_generation(
                            name_str, val_str, desc_str, name_align, val_align, 4  # tab_size=4
                        )
                        if temp_str and isinstance(temp_str, str) and "#define" in temp_str:
                            # Cython DEFINE 코드 생성 성공 (로그 제거)
                            pass
                        else:
                            raise Exception("Cython DEFINE 생성 결과 없음")
                    except Exception as e:
                        logging.debug(f"Cython DEFINE 생성 실패, Python 폴백: {e}")
                        # Python 폴백
                    pad_tab_cnt = self.calculatePad(name_align, len(name_str), False, 1)
                    temp_str = "#define\t" + name_str.ljust(pad_tab_cnt, '\t')
                    if desc_str:
                        pad_tab_cnt = self.calculatePad(val_align, len(val_str), False, 1)
                        temp_str += val_str.ljust(pad_tab_cnt, '\t') + desc_str
                    else:
                        temp_str += val_str
            else:
                # 기존 Python 방식
                pad_tab_cnt = self.calculatePad(name_align, len(name_str), False, 1)
                temp_str = "#define\t" + name_str.ljust(pad_tab_cnt, '\t')
                if desc_str:
                    pad_tab_cnt = self.calculatePad(val_align, len(val_str), False, 1)
                    temp_str += val_str.ljust(pad_tab_cnt, '\t') + desc_str
                else:
                    temp_str += val_str

            if self.mkFile != EMkFile.Src:
                hdr_data_str = temp_str
            if self.mkFile != EMkFile.Hdr:
                src_data_str = temp_str

        elif mk_mode == EMkMode.TYPEDEF:
            temp_str = "typedef struct "
            if name_str:
                temp_str += name_str + " "
            temp_str += "{\t" + desc_str

            if self.mkFile != EMkFile.Src:
                hdr_data_str = temp_str
            if self.mkFile != EMkFile.Hdr:
                src_data_str = temp_str

        elif mk_mode == EMkMode.STR_MEM:
            temp_str = type_str.ljust(type_align + 1)
            if not val_str:
                temp_str += name_str + ";"
                if desc_str:
                    if val_align == 0:
                        pad_tab_cnt = self.calculatePad(temp_str.length + name_align, temp_str.length + len(name_str), True, 1)
                        temp_str += "\t".ljust(pad_tab_cnt - 1, '\t')
                    else:
                        pad_tab_cnt = self.calculatePad(temp_str.length + name_align, temp_str.length + len(name_str), True, 0)
                        temp_str += "\t".ljust(pad_tab_cnt - 1, '\t')
                        pad_tab_cnt = self.calculatePad(val_align + 3, -1, True, 1)

                        temp_str += "\t".ljust(pad_tab_cnt - 1, '\t')

                    temp_str += desc_str
            else:
                pad_tab_cnt = self.calculatePad(temp_str.length + name_align, temp_str.length + len(name_str), False, 0)
                temp_str += name_str.ljust(pad_tab_cnt - len(temp_str), '\t') + ": " + val_str

                if not desc_str:
                    temp_str += ";"
                else:
                    pad_tab_cnt = self.calculatePad(val_align + 2, len(val_str) + 2, True, 1)
                    temp_str += ";".ljust(pad_tab_cnt, '\t') + desc_str
            temp_str = "\t" + temp_str

            if self.mkFile != EMkFile.Src:
                hdr_data_str = temp_str
            if self.mkFile != EMkFile.Hdr:
                src_data_str = temp_str

        elif mk_mode == EMkMode.STR_DEF:
            temp_str = "} " + name_str + ";"

            if desc_str:
                if (len(temp_str) % Info.TabSize) >= 3:
                    temp_str += "\t"
                temp_str += "\t" + desc_str
            temp_str += "\r\n"

            if self.mkFile != EMkFile.Src:
                hdr_data_str = temp_str
            if self.mkFile != EMkFile.Hdr:
                src_data_str = temp_str

        elif mk_mode == EMkMode.ENUM:
            if not name_str:
                temp_str = "enum {\t" + desc_str
            else:
                temp_str = "enum " + name_str + " {"
                if desc_str:
                    if (len(temp_str) % Info.TabSize) >= 3:
                        temp_str += "\t"
                    temp_str += "\t" + desc_str
            if self.mkFile != EMkFile.Src:
                hdr_data_str = temp_str
            if self.mkFile != EMkFile.Hdr:
                src_data_str = temp_str

        elif mk_mode == EMkMode.ENUM_MEM:
            if not val_str:
                temp_str = name_str + ","
                if desc_str:
                    if val_align == 0:
                        pad_tab_cnt = self.calculatePad(name_align, len(name_str), True, 1)
                        temp_str += "\t".ljust(pad_tab_cnt - 1, '\t')
                    else:
                        pad_tab_cnt = self.calculatePad(name_align, len(name_str), True, 0)
                        temp_str += "\t".ljust(pad_tab_cnt - 1, '\t')
                        pad_tab_cnt = self.calculatePad(val_align + 3, -1, True, 1)
                        temp_str += "\t".ljust(pad_tab_cnt - 1, '\t')
                    temp_str += desc_str
            else:
                pad_tab_cnt = self.calculatePad(name_align, len(name_str), False, 0)
                temp_str = name_str.ljust(pad_tab_cnt, '\t') + "= " + val_str

                if not desc_str:
                    temp_str += ","
                else:
                    pad_tab_cnt = self.calculatePad(val_align + 2, len(val_str) + 2, True, 1)
                    temp_str += ",".ljust(pad_tab_cnt, '\t') + desc_str
            temp_str = "\t" + temp_str

            if self.mkFile != EMkFile.Src:
                hdr_data_str = temp_str
            if self.mkFile != EMkFile.Hdr:
                src_data_str = temp_str

        elif mk_mode == EMkMode.ENUM_END:
            temp_str = "};"
            if desc_str:
                temp_str += "\t" + desc_str

            temp_str += "\r\n"

            if self.mkFile != EMkFile.Src:
                hdr_data_str = temp_str
            if self.mkFile != EMkFile.Hdr:
                src_data_str = temp_str

        elif mk_mode == EMkMode.ARRAY:
            if self.ShtName + "_" + name_str + "_" + str(self.arrNameCnt) in self.dArr:
                self.currentArr = self.ShtName + "_" + name_str + "_" + str(self.arrNameCnt)
                self.arrNameCnt += 1
                self.dArr[self.currentArr].RowCnt = 0

                hdr_data_str = "extern "
                if key_str and key_str != Info.EmptyKey:
                    if self.dArr[self.currentArr].ArrType == EArrType.Type2.value:
                        src_data_str = key_str.ljust(key_align + 1)
                        hdr_data_str += key_str.ljust(key_align + 1)
                    else:
                        src_data_str = key_str + " "
                        hdr_data_str += key_str + " "

                if self.dArr[self.currentArr].ArrType == EArrType.Type2.value:
                    src_data_str += type_str.ljust(type_align + 1)
                    pad_tab_cnt = self.calculatePad(len(src_data_str) + name_align, len(src_data_str) + len(name_str), False, 0)
                    src_data_str += name_str.ljust(pad_tab_cnt - len(src_data_str), '\t') + "= "
                    hdr_data_str += type_str.ljust(type_align + 1)

                    pad_tab_cnt = self.calculatePad(val_align, len(val_str), True, 1)
                    val_str = val_str.replace("    ", "\t")
                    val_str = val_str.replace("   ", "\t")
                    val_str = val_str.replace("  ", "\t")
                    val_str = val_str.replace(" ", "\t")

                    if desc_str:
                        src_data_str += val_str + ";".ljust(pad_tab_cnt, '\t') + desc_str
                        pad_tab_cnt = self.calculatePad(len(hdr_data_str) + name_align + 1, len(hdr_data_str) + len(name_str) + 1, False, 1)
                        hdr_data_str += name_str + ";".ljust(pad_tab_cnt - len(hdr_data_str) - len(name_str), '\t') + desc_str
                    else:
                        src_data_str += val_str + ";"
                        hdr_data_str += name_str + ";"
                else:
                    src_data_str += type_str + " " + name_str + " ="
                    hdr_data_str += type_str + " " + name_str + ";"

                    if desc_str:
                        if len(temp_str) % Info.TabSize >= 3:
                            temp_str += "\t"
                        temp_str += "\t" + desc_str
                    temp_str += "\r\n"

                    if desc_str:
                        if len(src_data_str) % Info.TabSize >= 3:
                            src_data_str += "\t"
                        src_data_str += "\t" + desc_str
                        if len(hdr_data_str) % Info.TabSize >= 3:
                            hdr_data_str += "\t"
                        hdr_data_str += "\t" + desc_str

                    src_data_str += "\r\n{"
                    self.readyArrMemMake()

        elif mk_mode == EMkMode.ARR_MEM:
            if self.dArr[self.currentArr].ArrType != EArrType.Type2.value:
                src_data_str = self.writeArrMem()
                self.dArr[self.currentArr].RowCnt += 1

        elif mk_mode == EMkMode.VARIABLE:
            # Cython 래퍼를 통한 VARIABLE 코드 생성
            if CYTHON_CODE_GEN_AVAILABLE:
                try:
                    # Cython 직접 호출로 변수 코드 생성
                    # 안전한 동적 import 사용
                    fast_variable_code_generation = safe_import_cython_function('code_generator_v2', 'fast_variable_code_generation')
                    if fast_variable_code_generation:
                        try:
                            generated_code = fast_variable_code_generation(
                                key_str, type_str, name_str, val_str, desc_str,
                                key_align, type_align, name_align, val_align, 4  # tab_size=4
                            )
                        except Exception:
                            # Cython 실패 시 Python 폴백
                            generated_code = (f"const {type_str} {name_str} = {val_str};", f"extern const {type_str} {name_str};")
                    else:
                        # Cython 없으면 Python 폴백
                        generated_code = (f"const {type_str} {name_str} = {val_str};", f"extern const {type_str} {name_str};")
                    if generated_code and isinstance(generated_code, tuple) and len(generated_code) == 2:
                        # Cython이 반환하는 (src_code, hdr_code) 튜플 사용
                        src_data_str = generated_code[0]
                        hdr_data_str = generated_code[1]
                        # 성공적으로 생성됨 (디버그 메시지 제거)
                    elif generated_code and isinstance(generated_code, str):
                        # 단일 문자열인 경우
                        src_data_str = generated_code
                        hdr_data_str = "extern " + generated_code.replace("const ", "").replace(" = " + val_str, "")
                        # 단일 문자열 생성 성공
                    else:
                        # Cython 실패 시 Python 폴백
                        # Cython 결과 없음
                        raise Exception("Cython 변수 생성 실패")
                except Exception as e:
                    logging.debug(f"Cython VARIABLE 생성 실패, Python 폴백: {e}")
                    # Python 폴백
                    hdr_data_str = "extern "
                    if key_str and key_str != Info.EmptyKey:
                        src_data_str = key_str.ljust(key_align + 1)
                        hdr_data_str += key_str.ljust(key_align + 1)

                    src_data_str += type_str.ljust(type_align + 1)
                    hdr_data_str += type_str.ljust(type_align + 1)
                    pad_tab_cnt = self.calculatePad(len(src_data_str) + name_align, len(src_data_str) + len(name_str), False, 0)
                    if not val_str:
                        src_data_str += name_str + ";"
                        if desc_str:
                            src_data_str += "\t".ljust(pad_tab_cnt - len(src_data_str) - len(name_str), '\t') + desc_str
                    else:
                        src_data_str += name_str.ljust(pad_tab_cnt - len(src_data_str), '\t') + "= "
                        if desc_str:
                            pad_tab_cnt = self.calculatePad(val_align - 1, len(val_str) - 1, False, 1)
                            src_data_str += val_str + ";".ljust(pad_tab_cnt - len(val_str) + 2, '\t') + desc_str
                            pad_tab_cnt = self.calculatePad(len(hdr_data_str) + name_align + 1, len(hdr_data_str) + len(name_str) + 1, False, 1)
                            hdr_data_str += name_str + ";".ljust(pad_tab_cnt - len(hdr_data_str) - len(name_str), '\t') + desc_str
                        else:
                            src_data_str += val_str + ";"
                            hdr_data_str += name_str + ";"
            else:
                # 기존 Python 방식
                hdr_data_str = "extern "
                if key_str and key_str != Info.EmptyKey:
                    src_data_str = key_str.ljust(key_align + 1)
                    hdr_data_str += key_str.ljust(key_align + 1)

                src_data_str += type_str.ljust(type_align + 1)
                hdr_data_str += type_str.ljust(type_align + 1)
                pad_tab_cnt = self.calculatePad(len(src_data_str) + name_align, len(src_data_str) + len(name_str), False, 0)
                if not val_str:
                    src_data_str += name_str + ";"
                    if desc_str:
                        src_data_str += "\t".ljust(pad_tab_cnt - len(src_data_str) - len(name_str), '\t') + desc_str
                else:
                    src_data_str += name_str.ljust(pad_tab_cnt - len(src_data_str), '\t') + "= "
                    if desc_str:
                        pad_tab_cnt = self.calculatePad(val_align - 1, len(val_str) - 1, False, 1)
                        src_data_str += val_str + ";".ljust(pad_tab_cnt - len(val_str) + 2, '\t') + desc_str
                        pad_tab_cnt = self.calculatePad(len(hdr_data_str) + name_align + 1, len(hdr_data_str) + len(name_str) + 1, False, 1)
                        hdr_data_str += name_str + ";".ljust(pad_tab_cnt - len(hdr_data_str) - len(name_str), '\t') + desc_str
                    else:
                        src_data_str += val_str + ";"
                        hdr_data_str += name_str + ";"

        elif mk_mode == EMkMode.CODE:
            if self.mkFile != EMkFile.Hdr:
                temp_str = name_str.replace("\n", "\r\n")
            if self.mkFile != EMkFile.Src:
                temp_str = name_str.replace("\n", "\r\n")
            if self.mkFile != EMkFile.Src:
                hdr_data_str = temp_str
            if self.mkFile != EMkFile.Hdr:
                src_data_str = temp_str

        elif mk_mode == EMkMode.PRGM_SET or mk_mode == EMkMode.PRGM_END:
            src_data_str = self.writePragma(mk_mode, key_str, empty_src)
            hdr_data_str = self.writePragma(mk_mode, key_str, empty_hdr)

        elif mk_mode == EMkMode.PRJT_DEF:
            rt = False

            if name_str != self.currentPrjtDef:
                for i in range(self.prjtDepth, -1, -1):
                    if self.prjtList[i].Def == name_str:
                        temp_depth = self.prjtDepth
                        for j in range(self.prjtDepth - i):
                            tab_str = ""
                            for k in range(temp_depth):
                                tab_str += "\t"
                            temp_str += tab_str + "#else\r\n"
                            temp_str += tab_str + "\t#error undefined " + self.prjtList[self.prjtDepth - j].Def + " MACRO\r\n\r\n"
                            temp_str += tab_str + "#endif\r\n\r\n"

                            self.prjtList[temp_depth] = SPrjtInfo(name_str, [])
                            temp_depth -= 1

                        self.prjtDepth = temp_depth
                        rt = True
                        break

            if name_str != self.currentPrjtDef and not rt:
                if name_str == "1" or name_str == "0":
                    temp_str += "#if " + name_str
                else:
                    temp_str += "#if (" + name_str + " == " + val_str + ")"

                if desc_str:
                    if len(temp_str) % Info.TabSize >= 3:
                        temp_str += "\t"
                    temp_str += "\t" + desc_str

                temp_str += "\r\n"

                self.prjtDepth += 1
                self.prjtList[self.prjtDepth] = SPrjtInfo(name_str, [])
                self.prjtList[self.prjtDepth].Val.append(val_str)
                self.currentPrjtDef = name_str
            else:
                if val_str == Info.ElsePrjtName:
                    temp_str += "#else"

                    if desc_str:
                        if len(temp_str) % Info.TabSize >= 3:
                            temp_str += "\t"
                        temp_str += "\t" + desc_str

                    temp_str += "\r\n"

                    self.prjtList[self.prjtDepth].Val.append(val_str)
                    self.currentPrjtDef = name_str
                elif val_str == Info.EndPrjtName:
                    if self.prjtList[self.prjtDepth].Val[-1] != Info.ElsePrjtName:
                        temp_str += "#else\r\n\t#error undefined " + self.prjtList[self.prjtDepth].Def + " MACRO\r\n\r\n#endif"
                    else:
                        temp_str += "#endif"

                    if desc_str:
                        if len(temp_str) % Info.TabSize >= 3:
                            temp_str += "\t"
                        temp_str += "\t" + desc_str

                    temp_str += "\r\n"

                    self.prjtList[self.prjtDepth] = SPrjtInfo(name_str, [])
                    self.prjtDepth -= 1
                    self.currentPrjtDef = ""
                else:
                    temp_str += "#elif (" + name_str + " == " + val_str + ")"

                    if desc_str:
                        if len(temp_str) % Info.TabSize >= 3:
                            temp_str += "\t"
                        temp_str += "\t" + desc_str

                    temp_str += "\r\n"

                    self.prjtList[self.prjtDepth].Val.append(val_str)
                    self.currentPrjtDef = name_str

            # 전처리기 지시문 앞에 빈 줄을 추가하는 로직
            if self.mkFile != EMkFile.Src:
                if not empty_hdr:
                    hdr_data_str = "\r\n"
                hdr_data_str += temp_str

            if self.mkFile != EMkFile.Hdr:
                if not empty_src:
                    src_data_str = "\r\n"
                src_data_str += temp_str

        if self.mkFile != EMkFile.Hdr:
            self.writeCode(mk_mode, src_data_str, True)
        if self.mkFile != EMkFile.Src:
            self.writeCode(mk_mode, hdr_data_str, False)

        if mk_mode == EMkMode.TITLE or mk_mode == EMkMode.TITLE_S or mk_mode == EMkMode.TITLE_H or mk_mode == EMkMode.SUBTITLE or mk_mode == EMkMode.DESCRIPT or mk_mode == EMkMode.STR_DEF or mk_mode == EMkMode.ENUM_END or mk_mode == EMkMode.NONE or mk_mode == EMkMode.PRJT_DEF:
            self.alignCnt += 1

        # 생성된 코드 반환 (성능 저하 없는 Cython 최적화 완료)
        result = []
        if src_data_str:
            result.append(src_data_str)
        if hdr_data_str and hdr_data_str != src_data_str:
            result.append(hdr_data_str)

        return result

    def writeCode(self, mk_mode, code_str, src):
        """코드 작성"""
        # 🔥 핵심 수정: currentTitle 검증 및 초기화
        if not self.currentTitle:
            self.currentTitle = "TITLE+DEFAULT"
            logging.warning(f"시트 {self.ShtName}: writeCode에서 currentTitle이 비어있어 기본값 설정")

        # dSrcCode, dHdrCode에 키가 없는 경우 생성
        if self.currentTitle not in self.dSrcCode:
            self.dSrcCode[self.currentTitle] = []
        if self.currentTitle not in self.dHdrCode:
            self.dHdrCode[self.currentTitle] = []

        if mk_mode == EMkMode.PRJT_DEF:
            self.frontTab = ""
            for i in range(self.prjtDepth, 0, -1):
                self.frontTab += "\t"

        if code_str or mk_mode == EMkMode.DESCRIPT:
            if "\r\n" in code_str:
                if code_str.endswith("\r\n"):
                    temp = code_str[:-2]
                else:
                    temp = code_str

                temp = temp.replace("\r", "")
                split = temp.split('\n')

                if code_str.endswith("\r\n"):
                    split[-1] += "\r\n"

                for item in split:
                    if src:
                        self.dSrcCode[self.currentTitle].append(self.frontTab + item)
                    else:
                        self.dHdrCode[self.currentTitle].append(self.frontTab + item)
            else:
                if src:
                    self.dSrcCode[self.currentTitle].append(self.frontTab + code_str)
                else:
                    self.dHdrCode[self.currentTitle].append(self.frontTab + code_str)

        if mk_mode == EMkMode.PRJT_DEF and self.currentPrjtDef:
            self.frontTab += "\t"

    def calculatePad(self, align, str_len, type_flag, add_tab):
        """패딩 계산 - 간소화"""
        # 캐시 키 생성 (같은 매개변수로 호출되는 경우가 많음)
        cache_key = (align, str_len, type_flag, add_tab)

        # 클래스에 캐시 딕셔너리가 없으면 생성
        if not hasattr(self, 'pad_cache'):
            self.pad_cache = {}

        # 캐시에 결과가 있으면 반환
        if cache_key in self.pad_cache:
            return self.pad_cache[cache_key]

        # 계산 로직
        rt = 0

        if type_flag:
            align += 1
            str_len += 1

        rt = (align // Info.TabSize) - (str_len // Info.TabSize) + 1

        if type_flag:
            rt += 1
        else:
            rt += str_len

        if (align % Info.TabSize) >= (Info.TabSize - add_tab):
            rt += 1

        # 결과 캐싱
        self.pad_cache[cache_key] = rt

        return rt

    def add_float_suffix_v2(self, val_str, type_str):
        """FLOAT32 타입 변수의 숫자에 f 접미사를 추가하는 함수 - Cython 최적화 (V2)"""
        # 입력 값 타입 안전성 확보
        if val_str is None:
            val_str = ""
        elif not isinstance(val_str, str):
            val_str = str(val_str)

        if type_str is None:
            type_str = ""
        elif not isinstance(type_str, str):
            type_str = str(type_str)

        # FLOAT32 타입이 아니면 원본 값 그대로 반환
        if "FLOAT32" not in type_str:
            return val_str

        # 이미 접미사가 있는 경우는 처리하지 않음
        if val_str.endswith('f') or val_str.endswith('F'):
            return val_str

        if USE_CYTHON_CAL_LIST:
            fast_float_suffix_regex_replacement = safe_import_cython_function('regex_optimizer', 'fast_float_suffix_regex_replacement')
            if fast_float_suffix_regex_replacement:
                try:
                    # Cython 최적화 버전 사용 (C 수준 성능)
                    return fast_float_suffix_regex_replacement(val_str)
                except Exception as e:
                    logging.warning(f"Cython Float Suffix 처리 중 오류 발생, Python 폴백 사용: {e}")
                    # 오류 발생 시 Python 폴백으로 처리

        # 기존 Python 버전 (폴백) - 들여쓰기 수정

        # 주석 처리 및 문자열 보존
        comments = {}
        strings = {}
        comment_count = 0
        string_count = 0

        # 블록 주석 처리 - 사전 컴파일된 정규식 사용
        block_comments = self.block_comment_pattern.finditer(val_str)
        for comment in block_comments:
            placeholder = f"__COMMENT_BLOCK_{comment_count}__"
            comments[placeholder] = comment.group(0)
            val_str = val_str.replace(comment.group(0), placeholder)
            comment_count += 1

        # 라인 주석 처리 - 사전 컴파일된 정규식 사용
        line_comments = self.line_comment_pattern.finditer(val_str)
        for comment in line_comments:
            placeholder = f"__COMMENT_LINE_{comment_count}__"
            comments[placeholder] = comment.group(0)
            val_str = val_str.replace(comment.group(0), placeholder)
            comment_count += 1

        # 문자열 리터럴 처리 - 사전 컴파일된 정규식 사용
        strings_found = self.string_pattern.finditer(val_str)
        for string in strings_found:
            placeholder = f"__STRING_{string_count}__"
            strings[placeholder] = string.group(0)
            val_str = val_str.replace(string.group(0), placeholder)
            string_count += 1

        # 배열 인덱스 패턴 보존 - 사전 컴파일된 정규식 사용
        array_indices = {}
        idx_count = 0

        array_indices_found = self.array_index_pattern.finditer(val_str)
        for match in array_indices_found:
            placeholder = f"__ARRAY_IDX_{idx_count}__"
            array_indices[placeholder] = match.group(0)
            val_str = val_str.replace(match.group(0), placeholder)
            idx_count += 1

        # 배열 캐스팅 패턴 보존 - 사전 컴파일된 정규식 사용
        cast_count = 0
        cast_matches = {}

        cast_found = self.cast_pattern.finditer(val_str)
        for match in cast_found:
            placeholder = f"__CAST_{cast_count}__"
            cast_matches[placeholder] = match.group(0)
            val_str = val_str.replace(match.group(0), placeholder)
            cast_count += 1

        # 수정할 문자열
        modified_val = val_str

        # 1. 소수점이 있는 숫자 (x.y 형태): 1.0, 0.5 등 - 사전 컴파일된 정규식 사용
        modified_val = self.decimal_pattern.sub(r'\1f', modified_val)

        # 2. 소수점 뒤에 숫자가 없는 경우 (x. 형태): 3., 400. 등 - 사전 컴파일된 정규식 사용
        modified_val = self.decimal_point_only_pattern.sub(r'\1f', modified_val)

        # 3. 정수 리터럴 (단독으로 사용되는 경우만): 1, 2, 3 등 - 사전 컴파일된 정규식 사용
        modified_val = self.integer_pattern.sub(r'\1.f', modified_val)

        # 4. 0: 제로 (단독으로 사용되는 경우만) - 사전 컴파일된 정규식 사용
        modified_val = self.zero_pattern.sub(r'0.f', modified_val)

        # 배열 내 단일 값에도 .f 접미사 추가 - 사전 컴파일된 정규식 사용 (기존 로직 유지)
        modified_val = self.array_value_pattern.sub(r'\1\2.f\3', modified_val)

        # 2차원 배열의 마지막 값에 대한 특별 처리 - 사전 컴파일된 정규식 사용 (기존 로직 유지)
        modified_val = self.array_last_value_pattern.sub(r'\1\2.f\3', modified_val)

        # 캐스팅 패턴 복원
        for placeholder, cast in cast_matches.items():
            modified_val = modified_val.replace(placeholder, cast)

        # 배열 인덱스 복원
        for placeholder, index in array_indices.items():
            modified_val = modified_val.replace(placeholder, index)

        # 문자열 복원
        for placeholder, string in strings.items():
            modified_val = modified_val.replace(placeholder, string)

        # 주석 복원
        for placeholder, comment in comments.items():
            modified_val = modified_val.replace(placeholder, comment)

        return modified_val

    # cal_list.py에 추가
    def safe_get_from_dict(self, dict_obj, key, default=None):
        """딕셔너리에서 안전하게 값 가져오기"""
        if key in dict_obj:
            return dict_obj[key]
        logging.warning(f"딕셔너리 키 없음: {key}")
        return default

    def safe_get_from_list(self, list_obj, index, default=None):
        """리스트에서 안전하게 값 가져오기"""
        if 0 <= index < len(list_obj):
            return list_obj[index]
        logging.warning(f"리스트 인덱스 범위 초과: {index}, 크기: {len(list_obj)}")
        return default

        # cal_list.py에 추가
    def safe_read_cell(self, row, col):
        """셀 데이터 안전하게 읽기"""
        try:
            if self.shtData and 0 <= row < len(self.shtData):
                if 0 <= col < len(self.shtData[row]):
                    return Info.ReadCell(self.shtData, row, col)
                else:
                    logging.warning(f"열 인덱스 범위 초과: row={row}, col={col}, max_col={len(self.shtData[row])-1}")
            else:
                logging.warning(f"행 인덱스 범위 초과: row={row}, max_row={len(self.shtData)-1 if self.shtData else -1}")
            return ""
        except Exception as e:
            logging.error(f"셀 읽기 오류: row={row}, col={col}, 오류={e}")
            return ""