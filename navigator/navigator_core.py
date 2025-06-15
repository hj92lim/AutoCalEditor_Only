"""
네비게이터 핵심 로직

OpCode 기반 상대 위치 계산 및 네비게이터 아이템 파싱을 담당합니다.
"""

from typing import List, Optional, Tuple
from dataclasses import dataclass
import logging
import traceback

from .navigator_constants import (
    NavigatorConstants, OPCODE_MAPPING, ICON_MAPPING, DISPLAY_OPCODES, EMkMode
)

@dataclass
class NavigatorItem:
    """네비게이터 아이템 데이터 클래스"""
    name: str
    icon: str
    opcode: EMkMode
    row: int
    col: int
    size_info: str = ""
    level: int = 0  # 계층 레벨 (0=최상위)
    is_conditional_block: bool = False  # 조건부 컴파일 블록 여부
    block_type: str = ""  # 블록 타입 (#if, #elif, #else, #endif, #error 등)
    parent_row: int = -1  # 부모 블록의 행 번호

@dataclass
class ColumnPositions:
    """열 위치 정보 (cal_list.py의 dItem 구조 반영)"""
    opcode_col: int = -1
    name_col: int = -1
    value_col: int = -1
    type_col: int = -1

class NavigatorParser:
    """네비게이터 파서 (SRP 준수) - 계층구조 지원"""

    # 조건부 컴파일 패턴
    CONDITIONAL_PATTERNS = {
        '#if': 'conditional_start',
        '#ifdef': 'conditional_start',
        '#ifndef': 'conditional_start',
        '#elif': 'conditional_middle',
        '#else': 'conditional_middle',
        '#endif': 'conditional_end',
        '#error': 'conditional_error',
        '#warning': 'conditional_warning'
    }

    # 최대 중첩 깊이 (동적 확장 가능)
    MAX_NESTING_DEPTH = 10  # 기본값을 10으로 증가

    def _ensure_prjt_list_capacity(self, prjt_list: list, required_depth: int) -> None:
        """
        prjt_list 배열 용량을 필요한 깊이까지 확장

        Args:
            prjt_list: 프로젝트 리스트
            required_depth: 필요한 깊이
        """
        try:
            while len(prjt_list) <= required_depth:
                prjt_list.append({'Def': '', 'Val': []})
                logging.debug(f"prjt_list 확장: 새로운 크기 = {len(prjt_list)}")
        except Exception as e:
            logging.error(f"prjt_list 확장 실패: {e}")
            logging.error(traceback.format_exc())

    def _safe_prjt_list_access(self, prjt_list: list, index: int, operation: str = "read") -> bool:
        """
        prjt_list 안전 접근 검사

        Args:
            prjt_list: 프로젝트 리스트
            index: 접근할 인덱스
            operation: 작업 타입 ("read" 또는 "write")

        Returns:
            접근 가능 여부
        """
        try:
            if index < 0:
                logging.warning(f"prjt_list 음수 인덱스 접근 시도: {index}")
                return False

            if index >= len(prjt_list):
                if operation == "write":
                    # 쓰기 작업인 경우 배열 확장
                    self._ensure_prjt_list_capacity(prjt_list, index)
                    return True
                else:
                    # 읽기 작업인 경우 오류
                    logging.error(f"prjt_list 인덱스 범위 초과: index={index}, size={len(prjt_list)}")
                    return False

            return True

        except Exception as e:
            logging.error(f"prjt_list 접근 검사 실패: index={index}, operation={operation}, error={e}")
            return False

    def parse_items(self, sheet_data: List[List[str]]) -> List[NavigatorItem]:
        """시트 데이터에서 네비게이터 아이템 추출 (계층구조 지원)"""
        items = []

        # 열 위치 감지
        positions = self._detect_column_positions(sheet_data)

        if positions.opcode_col == -1:
            return items

        # 조건부 블록 감지
        conditional_blocks = self._detect_conditional_blocks(sheet_data)

        # DB 순서 기반 계층구조 파싱
        items = self._parse_hierarchical_items(sheet_data, positions, conditional_blocks)

        return items
    
    def _detect_column_positions(self, sheet_data: List[List[str]]) -> ColumnPositions:
        """열 위치 동적 감지"""
        positions = ColumnPositions()
        
        # 1. 헤더 기반 감지
        self._detect_by_headers(sheet_data, positions)
        
        # 2. OpCode 패턴 기반 감지
        if positions.opcode_col == -1:
            self._detect_opcode_by_pattern(sheet_data, positions)
        
        # 3. Name 열 추정
        if positions.name_col == -1 and positions.opcode_col != -1:
            self._estimate_name_column(sheet_data, positions)
        
        return positions

    def _detect_conditional_blocks(self, sheet_data: List[List[str]]) -> List[Tuple[int, str, str]]:
        """
        조건부 컴파일 블록 감지 (개선된 버전 - 우측 값 추출)

        Returns:
            List[Tuple[int, str, str]]: (행번호, 블록타입, 표시할_값) 리스트
        """
        blocks = []

        for row_idx, row_data in enumerate(sheet_data):
            for col_idx, cell_value in enumerate(row_data):
                if not cell_value or not isinstance(cell_value, str):
                    continue

                cell_value = cell_value.strip()

                # 조건부 컴파일 패턴 검사
                for pattern, block_type in self.CONDITIONAL_PATTERNS.items():
                    if cell_value.startswith(pattern):
                        # 우측 값 추출하여 표시
                        display_value = self._extract_right_value(cell_value)
                        blocks.append((row_idx, block_type, display_value))
                        break
                else:
                    # 프로젝트별 조건문 패턴 검사
                    if ('_PROJECT_NAME' in cell_value or
                        '_PERFORMANCE_TYPE' in cell_value or
                        '_DEVELOPMENT_PHASE' in cell_value or
                        '_MV_RWD_PROJ' in cell_value or
                        '_ME_RWD_PROJ' in cell_value or
                        '_NEN_RWD_PROJ' in cell_value):

                        display_value = self._extract_right_value(cell_value)

                        if cell_value.startswith('#if'):
                            blocks.append((row_idx, 'project_conditional_start', display_value))
                        elif cell_value.startswith('#elif'):
                            blocks.append((row_idx, 'project_conditional_middle', display_value))
                        elif cell_value.startswith('#else'):
                            blocks.append((row_idx, 'project_conditional_middle', display_value))
                        elif cell_value.startswith('#endif'):
                            blocks.append((row_idx, 'project_conditional_end', display_value))

        # $PRJT_DEF OpCode 처리 추가
        prjt_blocks = self._detect_prjt_def_blocks(sheet_data)
        blocks.extend(prjt_blocks)

        return blocks

    def _extract_right_value(self, condition: str) -> str:
        """
        조건문에서 우측 값(실제 의미있는 값) 추출

        Args:
            condition: 조건문 문자열 (예: "#if (_PROJECT_NAME == _MV_RWD_PROJ)")

        Returns:
            추출된 우측 값 (예: "_MV_RWD_PROJ")
        """
        # 기본값은 원본 조건문
        display_value = condition

        try:
            # == 패턴 처리 (가장 일반적)
            if '==' in condition:
                parts = condition.split('==')
                if len(parts) >= 2:
                    right_part = parts[1].strip()
                    # 괄호 제거
                    right_part = right_part.rstrip(')')

                    # OR 조건 처리 (첫 번째 값만 사용)
                    if '||' in right_part:
                        right_part = right_part.split('||')[0].strip()

                    # 언더스코어로 시작하는 값 우선
                    if right_part.startswith('_'):
                        display_value = right_part
                    else:
                        display_value = right_part

            # defined() 패턴 처리
            elif 'defined(' in condition:
                start = condition.find('defined(') + 8
                end = condition.find(')', start)
                if end > start:
                    defined_value = condition[start:end]
                    display_value = defined_value

            # ifdef/ifndef 패턴 처리
            elif condition.startswith('#ifdef') or condition.startswith('#ifndef'):
                parts = condition.split()
                if len(parts) >= 2:
                    macro_name = parts[1]
                    display_value = macro_name

            # #error, #warning 패턴 처리 (텍스트 기반)
            elif condition.startswith('#error') or condition.startswith('#warning'):
                # 전체 메시지 유지 (이모지 제거)
                display_value = condition

            # #else, #endif는 간소화
            elif condition.startswith('#else'):
                display_value = "#else"
            elif condition.startswith('#endif'):
                display_value = "#endif"

        except Exception:
            # 파싱 실패 시 원본 반환
            pass

        return display_value

    def _detect_prjt_def_blocks(self, sheet_data: List[List[str]]) -> List[Tuple[int, str, str]]:
        """
        $PRJT_DEF OpCode 블록 감지 (C 코드 생성 로직 기반 재구현)

        핵심 개념:
        - C 코드 생성 모듈의 prjtDepth, prjtList, currentPrjtDef 로직을 그대로 적용
        - 스택 기반 중첩 처리로 정확한 계층구조 생성
        - 실제 C 코드 생성과 동일한 원리로 동작

        Returns:
            List[Tuple[int, str, str]]: (행번호, 블록타입, 표시할_값) 리스트
        """
        blocks = []

        # C 코드 생성 로직과 동일한 상태 변수들
        prjt_depth = -1  # 중첩 깊이 (-1: 최상위)
        prjt_list = []   # 각 깊이별 프로젝트 정보
        current_prjt_def = ""  # 현재 활성 프로젝트 정의

        # SPrjtInfo 클래스 시뮬레이션 (동적 확장 가능)
        for _ in range(self.MAX_NESTING_DEPTH):
            prjt_list.append({'Def': '', 'Val': []})

        # 모든 $PRJT_DEF 행을 순차적으로 처리
        prjt_def_rows = self._extract_prjt_def_rows(sheet_data)

        for row_idx, var_name, value in prjt_def_rows:
            try:
                # 디버깅 정보 로깅
                self._log_prjt_state_debug_info("처리 전", prjt_depth, prjt_list, var_name, value, row_idx)

                # C 코드 생성 로직과 동일한 통합 처리 (상태 업데이트와 블록 생성 동시 수행)
                conditional_blocks, prjt_depth, current_prjt_def = self._process_prjt_def_unified(
                    row_idx, var_name, value, prjt_depth, prjt_list, current_prjt_def
                )

                # 디버깅 정보 로깅
                self._log_prjt_state_debug_info("처리 후", prjt_depth, prjt_list, var_name, value, row_idx)

                blocks.extend(conditional_blocks)

            except Exception as e:
                logging.error(f"$PRJT_DEF 처리 중 오류 발생: 행={row_idx}, 변수={var_name}, 값={value}, 오류={e}")
                logging.error(traceback.format_exc())
                # 오류 발생 시에도 계속 진행

        return blocks

    def _process_prjt_def_like_c_generator(self, row_idx: int, var_name: str, value: str,
                                          prjt_depth: int, prjt_list: list, current_prjt_def: str) -> List[Tuple[int, str, str]]:
        """
        C 코드 생성 로직과 완전히 동일한 $PRJT_DEF 처리 (수정된 버전)

        Args:
            row_idx: 행 번호
            var_name: 변수명 (예: _DEVELOPMENT_PHASE)
            value: 값 (예: _TCAR_VERSION, END)
            prjt_depth: 현재 중첩 깊이
            prjt_list: 프로젝트 리스트 (스택)
            current_prjt_def: 현재 활성 프로젝트 정의

        Returns:
            생성된 조건부 블록 리스트
        """
        blocks = []

        # END 처리 (C 코드 생성 로직과 동일)
        if value == "END":
            if prjt_depth >= 0 and self._safe_prjt_list_access(prjt_list, prjt_depth, "read"):
                # #endif 생성
                display_value = f"#endif  // {prjt_list[prjt_depth]['Def']}"
                blocks.append((row_idx, 'conditional_end', display_value))
            return blocks

        # 새로운 변수 시작 시 이전 변수들의 #endif 생성 (C 코드 생성 로직과 동일)
        if var_name != current_prjt_def:
            # 스택에서 같은 변수명 찾기
            for i in range(prjt_depth, -1, -1):
                if self._safe_prjt_list_access(prjt_list, i, "read") and prjt_list[i]['Def'] == var_name:
                    # 중간 변수들의 #endif 생성
                    temp_depth = prjt_depth
                    for j in range(prjt_depth - i):
                        if self._safe_prjt_list_access(prjt_list, temp_depth, "read"):
                            endif_display = f"#endif  // {prjt_list[temp_depth]['Def']}"
                            blocks.append((row_idx, 'conditional_end', endif_display))
                        temp_depth -= 1
                    break

        # 조건부 블록 시작/중간 처리 (C 코드 생성 로직과 완전히 동일)
        if var_name != current_prjt_def:
            # 새로운 조건부 블록 시작 (#if) - C 코드 생성기 1876번 라인과 동일
            if var_name == "1" or var_name == "0":
                display_value = f"#if {var_name}"
            else:
                display_value = f"#if ({var_name} == {value})"
            blocks.append((row_idx, 'conditional_start', display_value))
        else:
            # 기존 조건부 블록 계속 (#elif) - C 코드 생성기 1919번 라인과 동일
            display_value = f"#elif ({var_name} == {value})"
            blocks.append((row_idx, 'conditional_middle', display_value))

        return blocks

    def _update_prjt_state(self, var_name: str, value: str, prjt_depth: int,
                          prjt_list: list, current_prjt_def: str) -> tuple:
        """
        C 코드 생성 로직과 동일한 프로젝트 상태 업데이트

        Returns:
            (새로운_prjt_depth, 새로운_current_prjt_def)
        """
        if value == "END":
            if prjt_depth >= 0 and self._safe_prjt_list_access(prjt_list, prjt_depth, "write"):
                prjt_list[prjt_depth] = {'Def': '', 'Val': []}
                prjt_depth -= 1
                current_prjt_def = ""
            return prjt_depth, current_prjt_def

        if var_name != current_prjt_def:
            # 새로운 변수 시작 (C 코드 생성기 1853-1871번 라인과 동일)
            rt = False

            # 스택에서 같은 변수명 찾아서 정리 (C 코드 생성기 1854-1870번 라인)
            for i in range(prjt_depth, -1, -1):
                if self._safe_prjt_list_access(prjt_list, i, "read") and prjt_list[i]['Def'] == var_name:
                    # 중간 변수들의 #endif 생성 (C 코드 생성기 1856-1868번 라인)
                    temp_depth = prjt_depth
                    for j in range(prjt_depth - i):
                        if self._safe_prjt_list_access(prjt_list, temp_depth, "write"):
                            prjt_list[temp_depth] = {'Def': '', 'Val': []}
                        temp_depth -= 1

                    prjt_depth = temp_depth  # C 코드 생성기 1868번 라인
                    rt = True
                    break

            # 새로운 레벨 추가 (C 코드 생성기 1872-1888번 라인과 동일)
            if var_name != current_prjt_def and not rt:
                prjt_depth += 1

                # 배열 크기 검사 및 확장
                if not self._safe_prjt_list_access(prjt_list, prjt_depth, "write"):
                    logging.error(f"prjt_list 확장 실패: depth={prjt_depth}, var_name={var_name}")
                    return prjt_depth - 1, current_prjt_def  # 이전 상태로 복원

                prjt_list[prjt_depth] = {'Def': var_name, 'Val': [value]}
                current_prjt_def = var_name  # C 코드 생성기 1888번 라인과 동일
            else:
                # 기존 변수에 값 추가 (C 코드 생성기 1928번 라인과 동일)
                if prjt_depth >= 0 and self._safe_prjt_list_access(prjt_list, prjt_depth, "read"):
                    prjt_list[prjt_depth]['Val'].append(value)
                current_prjt_def = var_name  # C 코드 생성기 1929번 라인과 동일

        return prjt_depth, current_prjt_def

    def _extract_prjt_def_rows(self, sheet_data: List[List[str]]) -> List[Tuple[int, str, str]]:
        """
        모든 $PRJT_DEF 행을 추출

        Returns:
            List[Tuple[int, str, str]]: (행번호, 변수명, 값) 리스트
        """
        prjt_def_rows = []

        for row_idx, row_data in enumerate(sheet_data):
            # $PRJT_DEF 찾기 (열 0 또는 열 1에서 확인)
            prjt_def_found = False
            if len(row_data) > 0 and row_data[0] == '$PRJT_DEF':
                prjt_def_found = True
            elif len(row_data) > 1 and row_data[1] == '$PRJT_DEF':
                prjt_def_found = True

            if prjt_def_found:
                try:
                    # 열 7: 좌측 변수명, 열 10: 우측 값
                    if len(row_data) > 10:
                        left_var = row_data[7] if len(row_data) > 7 else ""
                        right_value = row_data[10] if len(row_data) > 10 else ""

                        if left_var and right_value:
                            prjt_def_rows.append((row_idx, left_var, right_value))

                except Exception:
                    # 파싱 실패 시 무시
                    pass

        return prjt_def_rows



    def _format_prjt_def_value(self, left_var: str, right_value: str) -> str:
        """
        $PRJT_DEF의 좌측 변수와 우측 값을 의미있는 형태로 포맷팅 (텍스트 기반)

        Args:
            left_var: 좌측 변수명 (예: "_PERFORMANCE_TYPE")
            right_value: 우측 값 (예: "_MV_RWD_PROJ")

        Returns:
            포맷팅된 표시 값 (이모지 제거)
        """
        if right_value == "END":
            return f"{left_var} END"
        elif right_value == "_UNDEFINED_OPTION":
            return f"{left_var} = UNDEFINED"
        elif '||' in right_value:
            # OR 조건인 경우 첫 번째 값만 표시
            first_value = right_value.split('||')[0].strip()
            return f"{left_var} = {first_value}..."
        else:
            return f"{left_var} = {right_value}"

    def _parse_hierarchical_items(self, sheet_data: List[List[str]],
                                 positions: ColumnPositions,
                                 conditional_blocks: List[Tuple[int, str, str]]) -> List[NavigatorItem]:
        """
        계층구조 기반 아이템 파싱 (C 코드 생성 로직 기반)

        Args:
            sheet_data: 시트 데이터
            positions: 열 위치 정보
            conditional_blocks: 조건부 블록 정보

        Returns:
            계층구조가 적용된 Navigator 아이템 리스트
        """
        items = []

        # C 코드 생성과 동일한 상태 추적
        prjt_depth = -1
        prjt_list = []
        for _ in range(self.MAX_NESTING_DEPTH):
            prjt_list.append({'Def': '', 'Val': []})

        # 행 번호별로 블록 정보 인덱싱
        block_by_row = {row: (block_type, condition) for row, block_type, condition in conditional_blocks}

        # DB 순서대로 처리 (행 번호 순)
        for row_idx, row_data in enumerate(sheet_data):
            # 1. 조건부 블록 처리
            if row_idx in block_by_row:
                block_type, condition = block_by_row[row_idx]

                # prjt_depth 업데이트 먼저 수행 (C 코드 생성 로직과 동일)
                new_prjt_depth = self._update_prjt_depth_for_navigator(
                    block_type, condition, prjt_depth, prjt_list
                )

                # 레벨 계산: conditional_start는 새로운 깊이, 나머지는 현재 깊이 사용
                if block_type == 'conditional_start':
                    level = max(0, new_prjt_depth)  # 새로운 깊이 사용
                else:
                    level = max(0, prjt_depth)      # 현재 깊이 사용

                block_item = self._create_conditional_block_item(row_idx, block_type, condition, level)

                if block_item:
                    items.append(block_item)

                # prjt_depth 업데이트 적용
                prjt_depth = new_prjt_depth

            # 2. 일반 아이템 처리
            item = self._parse_row(row_idx, row_data, positions)
            if item:
                # 변수들은 현재 prjt_depth + 1에 배치
                item.level = max(0, prjt_depth + 1)
                items.append(item)

        # 중복 노드 제거
        items = self._remove_duplicate_nodes(items)

        return items

    def _update_prjt_depth_for_navigator(self, block_type: str, condition: str,
                                        prjt_depth: int, prjt_list: list) -> int:
        """
        Navigator용 prjt_depth 업데이트 (C 코드 생성 로직 기반)

        Args:
            block_type: 블록 타입 (conditional_start, conditional_middle, conditional_end)
            condition: 조건문 텍스트
            prjt_depth: 현재 깊이
            prjt_list: 프로젝트 리스트

        Returns:
            업데이트된 prjt_depth
        """
        if block_type == 'conditional_start':
            # #if 시작 - 깊이 증가
            prjt_depth += 1
            if self._safe_prjt_list_access(prjt_list, prjt_depth, "write"):
                # 조건문에서 변수명 추출 (예: "#if (_PERFORMANCE_TYPE == _MV_RWD_PROJ)" -> "_PERFORMANCE_TYPE")
                var_name = self._extract_variable_name_from_condition(condition)
                prjt_list[prjt_depth] = {'Def': var_name, 'Val': []}
            else:
                # 배열 확장 실패 시 깊이 복원
                prjt_depth -= 1
                logging.error(f"prjt_depth 증가 실패: depth={prjt_depth + 1}, condition={condition}")

        elif block_type == 'conditional_middle':
            # #elif - 깊이 유지 (같은 레벨) - C 코드 생성기와 동일
            # 같은 변수의 다른 값이므로 깊이는 변경하지 않음
            pass

        elif block_type == 'conditional_end':
            # #endif - 깊이 감소
            if prjt_depth >= 0 and self._safe_prjt_list_access(prjt_list, prjt_depth, "write"):
                prjt_list[prjt_depth] = {'Def': '', 'Val': []}
                prjt_depth -= 1

        return prjt_depth

    def _extract_variable_name_from_condition(self, condition: str) -> str:
        """
        조건문에서 변수명 추출

        Args:
            condition: 조건문 (예: "#if (_PERFORMANCE_TYPE == _MV_RWD_PROJ)")

        Returns:
            변수명 (예: "_PERFORMANCE_TYPE")
        """
        import re

        # #if (변수명 == 값) 패턴에서 변수명 추출
        match = re.search(r'#(?:if|elif)\s*\(\s*([^=\s]+)', condition)
        if match:
            return match.group(1).strip()

        # #endif // 변수명 패턴에서 변수명 추출
        match = re.search(r'#endif\s*//\s*(.+)', condition)
        if match:
            return match.group(1).strip()

        return ""

    def _process_prjt_def_unified(self, row_idx: int, var_name: str, value: str,
                                 prjt_depth: int, prjt_list: list, current_prjt_def: str) -> Tuple[List[Tuple[int, str, str]], int, str]:
        """
        C 코드 생성기와 완전히 동일한 통합 $PRJT_DEF 처리
        상태 업데이트와 블록 생성을 동시에 수행

        Args:
            row_idx: 행 번호
            var_name: 변수명
            value: 값
            prjt_depth: 현재 중첩 깊이
            prjt_list: 프로젝트 리스트
            current_prjt_def: 현재 활성 프로젝트 정의

        Returns:
            (생성된 블록 리스트, 새로운 prjt_depth, 새로운 current_prjt_def)
        """
        blocks = []

        # END 처리 (C 코드 생성기 1902-1917번 라인과 동일)
        if value == "END":
            if prjt_depth >= 0 and self._safe_prjt_list_access(prjt_list, prjt_depth, "read"):
                # #endif 생성
                display_value = f"#endif  // {prjt_list[prjt_depth]['Def']}"
                blocks.append((row_idx, 'conditional_end', display_value))

                # 상태 업데이트
                prjt_list[prjt_depth] = {'Def': '', 'Val': []}
                prjt_depth -= 1
                current_prjt_def = ""

            return blocks, prjt_depth, current_prjt_def

        # 새로운 변수 vs 기존 변수 처리 (C 코드 생성기 1853-1929번 라인과 동일)
        rt = False

        # 스택에서 같은 변수명 찾기 (C 코드 생성기 1854-1870번 라인)
        if var_name != current_prjt_def:
            for i in range(prjt_depth, -1, -1):
                if self._safe_prjt_list_access(prjt_list, i, "read") and prjt_list[i]['Def'] == var_name:
                    # 중간 변수들의 #endif 생성
                    temp_depth = prjt_depth
                    for j in range(prjt_depth - i):
                        if self._safe_prjt_list_access(prjt_list, temp_depth, "write"):
                            endif_display = f"#endif  // {prjt_list[temp_depth]['Def']}"
                            blocks.append((row_idx, 'conditional_end', endif_display))
                            prjt_list[temp_depth] = {'Def': '', 'Val': []}
                        temp_depth -= 1

                    prjt_depth = temp_depth
                    rt = True
                    break

        # 블록 생성 및 상태 업데이트 (C 코드 생성기 1872-1929번 라인과 동일)
        if var_name != current_prjt_def and not rt:
            # 새로운 조건부 블록 시작 (#if) - C 코드 생성기 1876번 라인
            if var_name == "1" or var_name == "0":
                display_value = f"#if {var_name}"
            else:
                display_value = f"#if ({var_name} == {value})"
            blocks.append((row_idx, 'conditional_start', display_value))

            # 상태 업데이트 - C 코드 생성기 1885-1888번 라인
            prjt_depth += 1
            if not self._safe_prjt_list_access(prjt_list, prjt_depth, "write"):
                logging.error(f"prjt_list 확장 실패: depth={prjt_depth}, var_name={var_name}")
                prjt_depth -= 1
                return blocks, prjt_depth, current_prjt_def

            prjt_list[prjt_depth] = {'Def': var_name, 'Val': [value]}
            current_prjt_def = var_name
        else:
            # 기존 조건부 블록 계속 (#elif) - C 코드 생성기 1919번 라인
            display_value = f"#elif ({var_name} == {value})"
            blocks.append((row_idx, 'conditional_middle', display_value))

            # 상태 업데이트 - C 코드 생성기 1928-1929번 라인
            if prjt_depth >= 0 and self._safe_prjt_list_access(prjt_list, prjt_depth, "read"):
                prjt_list[prjt_depth]['Val'].append(value)
            current_prjt_def = var_name

        return blocks, prjt_depth, current_prjt_def

    def _log_prjt_state_debug_info(self, operation: str, prjt_depth: int, prjt_list: list,
                                  var_name: str = "", value: str = "", row_idx: int = -1) -> None:
        """
        prjt_state 디버깅 정보 로깅

        Args:
            operation: 작업 타입
            prjt_depth: 현재 깊이
            prjt_list: 프로젝트 리스트
            var_name: 변수명
            value: 값
            row_idx: 행 번호
        """
        try:
            debug_info = [
                f"🔍 Navigator prjt_state 디버깅 - {operation}",
                f"  행번호: {row_idx}",
                f"  변수명: {var_name}",
                f"  값: {value}",
                f"  prjt_depth: {prjt_depth}",
                f"  prjt_list 크기: {len(prjt_list)}",
                f"  prjt_list 상태:"
            ]

            for i, item in enumerate(prjt_list):
                if i <= prjt_depth + 2:  # 현재 깊이 주변만 출력
                    active_marker = " <-- 현재" if i == prjt_depth else ""
                    debug_info.append(f"    [{i}]: Def='{item['Def']}', Val={item['Val']}{active_marker}")

            logging.debug("\n".join(debug_info))

        except Exception as e:
            logging.error(f"디버깅 정보 로깅 실패: {e}")

    def _remove_duplicate_nodes(self, items: List[NavigatorItem]) -> List[NavigatorItem]:
        """
        중복 노드 제거

        부모 노드와 동일한 변수명을 가진 하위 노드를 제거하여
        깔끔한 트리 구조를 만듭니다.

        Args:
            items: 원본 NavigatorItem 리스트

        Returns:
            중복이 제거된 NavigatorItem 리스트
        """
        if not items:
            return items

        # 조건부 블록 정보 수집
        conditional_blocks = {}  # {row: NavigatorItem}
        for item in items:
            if item.is_conditional_block:
                conditional_blocks[item.row] = item

        # 중복 제거 대상 식별
        items_to_remove = set()

        for i, item in enumerate(items):
            # 조건부 블록도 중복 검사 대상에 포함
            if item.is_conditional_block:
                # 조건부 블록 간 중복 확인
                if self._is_duplicate_conditional_block(item, items):
                    items_to_remove.add(i)
                continue

            # 같은 행에 조건부 블록이 있는지 확인
            if item.row in conditional_blocks:
                conditional_item = conditional_blocks[item.row]

                # 중복 조건 확인
                if self._is_duplicate_node(item, conditional_item):
                    items_to_remove.add(i)
                    continue

                # 같은 내용의 조건부 블록과 일반 아이템이 있는 경우 조건부 블록 제거 (원본 텍스트 우선)
                if self._is_same_content(item, conditional_item):
                    # #error, #warning의 경우 원본 텍스트(일반 아이템)를 우선하고 조건부 블록을 제거
                    if (item.opcode.name == 'CODE' and
                        any(keyword in item.name.lower() for keyword in ['error', 'warning'])):
                        # 조건부 블록을 제거 대상으로 표시 (나중에 처리)
                        pass
                    else:
                        items_to_remove.add(i)
                    continue

            # 부모 노드와의 중복 확인
            if self._is_duplicate_with_parent(item, items, conditional_blocks):
                items_to_remove.add(i)

        # 중복 아이템 제거
        filtered_items = [item for i, item in enumerate(items) if i not in items_to_remove]

        return filtered_items

    def _is_duplicate_node(self, item: NavigatorItem, conditional_item: NavigatorItem) -> bool:
        """
        일반 아이템과 조건부 블록 아이템이 중복인지 확인

        Args:
            item: 일반 NavigatorItem
            conditional_item: 조건부 블록 NavigatorItem

        Returns:
            중복 여부
        """
        # 의미있는 노드는 보존 (중복으로 간주하지 않음)
        if self._is_meaningful_node(item):
            return False

        # $CODE OpCode의 경우 조건부 블록과 중복으로 간주 (의미있는 메시지 제외)
        if item.opcode.name == 'CODE':
            # #error, #warning 등 의미있는 메시지는 보존
            if not self._is_meaningful_node(item):
                return True

        # 변수명이 조건부 블록에 포함되어 있는지 확인
        if hasattr(conditional_item, 'block_type') and conditional_item.block_type:
            # $PRJT_DEF 블록의 경우 변수명 추출
            if conditional_item.block_type.startswith('prjt_def_'):
                if ':' in conditional_item.block_type:
                    _, var_name = conditional_item.block_type.split(':', 1)
                    # 변수명에서 언더스코어 제거하여 비교
                    clean_var_name = var_name.lstrip('_')
                    clean_item_name = item.name.lstrip('_')

                    if clean_var_name.lower() == clean_item_name.lower():
                        return True

        return False

    def _is_same_content(self, item: NavigatorItem, conditional_item: NavigatorItem) -> bool:
        """
        일반 아이템과 조건부 블록 아이템이 같은 내용인지 확인

        Args:
            item: 일반 NavigatorItem
            conditional_item: 조건부 블록 NavigatorItem

        Returns:
            같은 내용 여부
        """
        # 이름에서 아이콘과 공백 제거하여 비교
        clean_item_name = item.name.strip()
        clean_conditional_name = conditional_item.name.strip()

        # 이모지가 제거되었으므로 추가 정리 불필요

        # 내용이 동일하거나 포함 관계인 경우
        if (clean_item_name == clean_conditional_name or
            clean_item_name in clean_conditional_name or
            clean_conditional_name in clean_item_name):
            return True

        return False

    def _is_duplicate_with_parent(self, item: NavigatorItem, all_items: List[NavigatorItem],
                                 conditional_blocks: dict) -> bool:
        """
        부모 노드와 중복인지 확인

        Args:
            item: 확인할 NavigatorItem
            all_items: 전체 아이템 리스트
            conditional_blocks: 조건부 블록 딕셔너리

        Returns:
            부모와 중복 여부
        """
        # 의미있는 노드는 보존 (중복으로 간주하지 않음)
        if self._is_meaningful_node(item):
            return False

        if not hasattr(item, 'parent_row') or item.parent_row is None:
            return False

        # 부모 조건부 블록 찾기
        parent_conditional = conditional_blocks.get(item.parent_row)
        if not parent_conditional:
            return False

        # 부모가 $PRJT_DEF 블록인 경우
        if (hasattr(parent_conditional, 'block_type') and
            parent_conditional.block_type and
            parent_conditional.block_type.startswith('prjt_def_')):

            if ':' in parent_conditional.block_type:
                _, parent_var_name = parent_conditional.block_type.split(':', 1)

                # 변수명 정규화하여 비교
                clean_parent_name = parent_var_name.lstrip('_').lower()
                clean_item_name = item.name.lstrip('_').lower()

                # 부모 변수명과 동일한 경우 중복으로 간주
                if clean_parent_name == clean_item_name:
                    return True

                # 부모 변수명이 아이템 이름에 포함된 경우도 중복으로 간주
                if clean_parent_name in clean_item_name or clean_item_name in clean_parent_name:
                    return True

        return False

    def _is_duplicate_conditional_block(self, item: NavigatorItem, all_items: List[NavigatorItem]) -> bool:
        """
        조건부 블록 간 중복 확인

        Args:
            item: 확인할 조건부 블록 NavigatorItem
            all_items: 전체 아이템 리스트

        Returns:
            중복 여부
        """
        if not item.is_conditional_block:
            return False

        # 에러나 경고 블록은 제거 (원본 텍스트 우선)
        if hasattr(item, 'block_type') and item.block_type:
            base_type = item.block_type.split(':')[0] if ':' in item.block_type else item.block_type
            if base_type in ['conditional_error', 'conditional_warning']:
                # #error, #warning 조건부 블록은 항상 제거 (일반 아이템 우선)
                return True

        # 같은 변수명을 가진 다른 조건부 블록과 중복 확인
        if hasattr(item, 'block_type') and item.block_type and ':' in item.block_type:
            _, var_name = item.block_type.split(':', 1)

            # 단순한 변수명만 표시하는 블록은 중복으로 간주
            clean_name = item.name.strip().lstrip('❌').lstrip('!').lstrip('?').strip()
            if clean_name == var_name:
                # 같은 변수명을 가진 더 의미있는 블록이 있는지 확인
                for other_item in all_items:
                    if (other_item != item and
                        other_item.is_conditional_block and
                        hasattr(other_item, 'block_type') and
                        other_item.block_type and
                        ':' in other_item.block_type):

                        _, other_var_name = other_item.block_type.split(':', 1)

                        # 같은 변수명이고, 더 의미있는 정보를 가진 블록이 있는 경우
                        if (var_name == other_var_name and
                            other_item.row != item.row and
                            ('UNDEFINED' in other_item.name or '=' in other_item.name)):
                            return True

        return False

    def _is_meaningful_node(self, item: NavigatorItem) -> bool:
        """
        의미있는 노드인지 확인 (보존해야 할 노드)

        Args:
            item: 확인할 NavigatorItem

        Returns:
            의미있는 노드 여부
        """
        # 실제 정의값을 가진 OpCode들은 보존
        meaningful_opcodes = {
            'DEFINE',    # 매크로 정의
            'VARIABLE',  # 변수 정의
            'ARRAY',     # 배열 정의
            'ENUM',      # 열거형 정의
            'TYPEDEF',   # 타입 정의
            'TITLE',     # 제목
            'SUBTITLE'   # 부제목
        }

        if item.opcode.name in meaningful_opcodes:
            return True

        # #error, #warning 등 중요한 메시지는 보존
        if item.opcode.name == 'CODE':
            name_lower = item.name.lower()
            if any(keyword in name_lower for keyword in ['error', 'warning', 'pragma']):
                return True

        return False



    def _create_conditional_block_item(self, row_idx: int, block_type: str,
                                      condition: str, level: int) -> Optional[NavigatorItem]:
        """조건부 블록 아이템 생성 (단순화된 버전)"""
        return NavigatorItem(
            name=condition,  # 표시할 조건문 텍스트
            icon="",  # 텍스트 기반 인터페이스
            opcode=EMkMode.CODE,
            row=row_idx,
            col=0,
            level=level,
            is_conditional_block=True,
            block_type=block_type
        )

    def _update_stack_for_block(self, block_type: str, stack: List[NavigatorItem],
                               block_item: NavigatorItem) -> None:
        """조건부 블록에 따른 스택 업데이트 (수정된 버전)"""
        if block_type in ['conditional_start', 'project_conditional_start']:
            # 새로운 조건부 블록 시작 - 스택에 추가하여 자식들이 들어갈 수 있게 함
            stack.append(block_item)

        elif block_type in ['conditional_middle', 'project_conditional_middle']:
            # #elif, #else 처리 - 이전 블록 종료하고 새 블록 시작
            # 중요: #elif는 #if와 같은 레벨이므로 스택에서 이전 블록을 제거하고 새로 추가
            if stack:
                stack.pop()  # 이전 #if 또는 #elif 제거
            stack.append(block_item)  # 새로운 #elif 추가

        elif block_type in ['conditional_end', 'project_conditional_end']:
            # 조건부 블록 종료 - #endif는 스택에 추가하지 않음 (자식을 가지지 않음)
            if stack:
                stack.pop()  # 마지막 #if 또는 #elif 제거
            # #endif는 스택에 추가하지 않음

        elif block_type in ['conditional_error', 'conditional_warning']:
            # #error, #warning은 스택에 추가하지 않음 (단독 아이템)
            pass

    def _update_stack_for_nested_blocks(self, block_type: str, stack: List[NavigatorItem],
                                       block_item: NavigatorItem) -> None:
        """중첩 조건부 블록을 위한 스택 업데이트 (새로운 버전)"""
        if block_type in ['conditional_start', 'project_conditional_start']:
            # 새로운 조건부 블록 시작 - 스택에 추가하여 중첩 지원
            stack.append(block_item)

        elif block_type in ['conditional_middle', 'project_conditional_middle']:
            # #elif, #else 처리 - 같은 레벨의 이전 블록 교체
            if stack:
                # 현재 레벨의 마지막 블록을 새로운 블록으로 교체
                stack[-1] = block_item
            else:
                # 스택이 비어있으면 새로 추가
                stack.append(block_item)

        elif block_type in ['conditional_end', 'project_conditional_end']:
            # 조건부 블록 종료 - 해당 레벨의 블록 제거
            if stack:
                stack.pop()

        elif block_type in ['conditional_error', 'conditional_warning']:
            # #error, #warning은 스택에 추가하지 않음 (단독 아이템)
            pass





    def _detect_by_headers(self, sheet_data: List[List[str]], positions: ColumnPositions):
        """헤더 키워드로 열 위치 감지 (개선된 버전)"""
        header_keywords = {
            'opcode': ['opcode'],
            'name': ['name'],
            'value': ['value'],
            'type': ['type']
        }

        for row_idx in range(min(NavigatorConstants.MAX_HEADER_SEARCH_ROWS, len(sheet_data))):
            row = sheet_data[row_idx]

            for col_idx, cell_value in enumerate(row):
                if not cell_value:
                    continue

                cell_lower = cell_value.lower().strip()

                for header_type, keywords in header_keywords.items():
                    for keyword in keywords:
                        # 정확한 매칭 우선 (예: 'Name' == 'name')
                        if cell_lower == keyword:
                            if header_type == 'opcode' and positions.opcode_col == -1:
                                positions.opcode_col = col_idx
                            elif header_type == 'name' and positions.name_col == -1:
                                positions.name_col = col_idx
                                print(f"🔍 헤더 기반 Name 열 감지: Col {col_idx}")
                            elif header_type == 'value' and positions.value_col == -1:
                                positions.value_col = col_idx
                            elif header_type == 'type' and positions.type_col == -1:
                                positions.type_col = col_idx
    
    def _detect_opcode_by_pattern(self, sheet_data: List[List[str]], positions: ColumnPositions):
        """OpCode 패턴으로 열 위치 감지"""
        for col_idx in NavigatorConstants.OPCODE_COL_CANDIDATES:
            for row_idx in range(min(NavigatorConstants.MAX_OPCODE_SEARCH_ROWS, len(sheet_data))):
                if (row_idx < len(sheet_data) and 
                    col_idx < len(sheet_data[row_idx]) and
                    sheet_data[row_idx][col_idx] and 
                    sheet_data[row_idx][col_idx].startswith('$')):
                    positions.opcode_col = col_idx
                    return
    
    def _estimate_name_column(self, sheet_data: List[List[str]], positions: ColumnPositions):
        """Name 열 위치 추정 (개선된 버전)"""
        best_col = -1
        best_score = 0

        # 모든 후보 열을 평가하여 최고 점수 선택
        for offset in NavigatorConstants.NAME_COL_OFFSETS:
            test_col = positions.opcode_col + offset
            score = self._calculate_name_column_score(sheet_data, test_col)

            print(f"🔍 Name 열 후보 Col {test_col}: 점수 {score:.2f}")

            if score > best_score and score > NavigatorConstants.NAME_PATTERN_THRESHOLD:
                best_score = score
                best_col = test_col

        if best_col != -1:
            positions.name_col = best_col
            print(f"🔍 최종 선택된 Name 열: Col {best_col} (점수: {best_score:.2f})")
    
    def _calculate_name_column_score(self, sheet_data: List[List[str]], col_idx: int) -> float:
        """Name 열 점수 계산 (개선된 버전)"""
        name_count = 0
        total_count = 0

        for row_idx in range(min(NavigatorConstants.MAX_OPCODE_SEARCH_ROWS, len(sheet_data))):
            if (row_idx < len(sheet_data) and
                col_idx < len(sheet_data[row_idx]) and
                sheet_data[row_idx][col_idx] and
                sheet_data[row_idx][col_idx].strip()):

                total_count += 1
                cell_value = sheet_data[row_idx][col_idx]

                # 변수명 패턴 확인 (더 엄격한 기준)
                if self._is_valid_variable_name(cell_value):
                    name_count += 1

        # 점수 계산: 비율 * 가중치
        if total_count == 0:
            return 0.0

        ratio = name_count / total_count

        # 샘플 수가 적으면 신뢰도 낮춤
        if total_count < 5:
            ratio *= 0.5

        return ratio

    def _is_valid_variable_name(self, value: str) -> bool:
        """유효한 변수명인지 확인 (더 엄격한 기준)"""
        if not value or len(value) < 2:
            return False

        # OpCode나 헤더는 제외
        if value.startswith('$') or value.lower() in ['name', 'value', 'type', 'keyword']:
            return False

        # 한글이 포함된 설명문은 변수명으로 인정
        if any('\uac00' <= char <= '\ud7af' for char in value):
            return True

        # 영문 변수명 패턴 확인
        clean_value = value.replace('_', '').replace('[', '').replace(']', '').replace(',', '')
        return clean_value.isalnum() and not clean_value.isdigit()

    def _is_likely_name_column(self, sheet_data: List[List[str]], col_idx: int) -> bool:
        """해당 열이 Name 열일 가능성 확인 (하위 호환성)"""
        score = self._calculate_name_column_score(sheet_data, col_idx)
        return score > NavigatorConstants.NAME_PATTERN_THRESHOLD
    
    def _parse_row(self, row_idx: int, row_data: List[str], positions: ColumnPositions) -> Optional[NavigatorItem]:
        """단일 행 파싱"""
        if len(row_data) <= positions.opcode_col:
            return None
        
        # OpCode 추출
        opcode_str = row_data[positions.opcode_col].strip()
        if not opcode_str or not opcode_str.startswith('$'):
            return None
        
        opcode = OPCODE_MAPPING.get(opcode_str, EMkMode.NONE)
        if opcode not in DISPLAY_OPCODES:
            return None
        
        # Name 추출
        name_col = self._get_name_column_for_opcode(opcode, positions)
        name = self._extract_name(row_data, name_col)
        
        if not name:
            return None
        
        # 배열 크기 정보 추출
        size_info = self._extract_size_info(opcode, row_data, positions)
        
        # 아이콘 선택
        icon = ICON_MAPPING.get(opcode, "📄")
        
        # 표시명 생성
        display_name = f"{name}{size_info}" if size_info else name
        
        return NavigatorItem(
            name=display_name,
            icon=icon,
            opcode=opcode,
            row=row_idx,
            col=name_col,
            size_info=size_info
        )
    
    def _get_name_column_for_opcode(self, opcode: EMkMode, positions: ColumnPositions) -> int:
        """OpCode별 Name 열 위치 계산"""
        base_name_col = positions.name_col
        
        if opcode == EMkMode.PRJT_DEF:
            return base_name_col + 2 if base_name_col != -1 else positions.opcode_col + 6
        elif opcode in [EMkMode.STR_MEM, EMkMode.ENUM_MEM]:
            return base_name_col + 1 if base_name_col != -1 else positions.opcode_col + 5
        else:
            return base_name_col if base_name_col != -1 else positions.opcode_col + 4
    
    def _extract_name(self, row_data: List[str], name_col: int) -> str:
        """변수명 추출"""
        if name_col < len(row_data) and row_data[name_col].strip():
            return row_data[name_col].strip()
        return ""
    
    def _extract_size_info(self, opcode: EMkMode, row_data: List[str], positions: ColumnPositions) -> str:
        """배열 크기 정보 추출"""
        if (opcode == EMkMode.ARRAY and 
            positions.value_col != -1 and 
            positions.value_col < len(row_data)):
            value = row_data[positions.value_col].strip()
            if value.startswith("[") and value.endswith("]"):
                return f" {value}"
        return ""
