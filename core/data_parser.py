from typing import Dict, List, Any, Optional
import logging
from core.info import Info, SCellPos, SShtInfo, CellInfos

class DataParser:
    """DB ↔ Excel 데이터 변환 클래스"""
    
    @staticmethod
    def parse_to_excel_format(sheet_data: List[List[str]]) -> List[List[str]]:
        """
        DB 데이터를 Excel 형식으로 변환
        
        Args:
            sheet_data: DB에서 가져온 시트 데이터
            
        Returns:
            Excel 형식으로 변환된 데이터
        """
        # DB에서 가져온 데이터는 이미 2차원 배열 형태이므로 그대로 반환
        return sheet_data
    
    @staticmethod
    def prepare_sheet_for_existing_code(sheet_name: str, sheet_data: List[List[str]]) -> SShtInfo:
        """
        기존 코드에서 사용할 수 있는 형태로 시트 데이터 준비
        
        Args:
            sheet_name: 시트 이름
            sheet_data: 시트 데이터
            
        Returns:
            SShtInfo 객체
        """
        sht_info = SShtInfo(sheet_name, sheet_data)
        return sht_info
    
    @staticmethod
    def read_cell_value(data: List[List[str]], row: int, col: int) -> str:
        """
        데이터에서 셀 값 읽기 (Info.ReadCell 함수와 호환)
        
        Args:
            data: 시트 데이터
            row: 행 번호
            col: 열 번호
            
        Returns:
            셀 값
        """
        return Info.ReadCell(data, row, col)
    
    @staticmethod
    def cell_infos_to_db_format(cell_infos: Dict[str, CellInfos]) -> List[tuple]:
        """
        CellInfos 딕셔너리를 DB 형식으로 변환
        
        Args:
            cell_infos: CellInfos 딕셔너리
            
        Returns:
            (row, col, value) 튜플 리스트
        """
        result = []
        for key, info in cell_infos.items():
            result.append((info.Row, info.Col, info.Str))
        return result