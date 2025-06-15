"""
네비게이터 핵심 로직

OpCode 기반 상대 위치 계산 및 네비게이터 아이템 파싱을 담당합니다.
"""

from typing import List, Optional
from dataclasses import dataclass

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

@dataclass
class ColumnPositions:
    """열 위치 정보 (cal_list.py의 dItem 구조 반영)"""
    opcode_col: int = -1
    name_col: int = -1
    value_col: int = -1
    type_col: int = -1

class NavigatorParser:
    """네비게이터 파서 (SRP 준수)"""
    
    def parse_items(self, sheet_data: List[List[str]]) -> List[NavigatorItem]:
        """시트 데이터에서 네비게이터 아이템 추출"""
        items = []
        
        # 열 위치 감지
        positions = self._detect_column_positions(sheet_data)
        
        if positions.opcode_col == -1:
            return items
        
        # 각 행 처리
        for row_idx, row_data in enumerate(sheet_data):
            item = self._parse_row(row_idx, row_data, positions)
            if item:
                items.append(item)
        
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
