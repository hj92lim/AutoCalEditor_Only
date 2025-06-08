from typing import Dict, List, Optional, Any
from core.info import Info, EErrType, CellInfos, SCellPos, SPragInfo


class FileInfo:
    """
    Excel 시트("FileInfo" 시트)에서 파일 관련 정보 및 프라그마 설정을 읽고 관리합니다.

    이 클래스는 특정 형식으로 구성된 Excel 시트에서 소스 파일(.c) 및 헤더 파일(.h)의
    메타데이터(파일명, 작성자, 버전, 변경 이력 등)와 포함될 헤더 파일 목록,
    그리고 코드 생성에 사용될 프라그마 섹션 정보를 파싱합니다.
    파싱된 정보는 내부 자료구조에 저장되며, 코드 파일의 주석 블록을 생성하는 데 사용됩니다.

    Attributes:
        SrcList (List[str]): 생성될 소스 파일의 파일 정보 주석 블록 라인 리스트.
        HdrList (List[str]): 생성될 헤더 파일의 파일 정보 주석 블록 라인 리스트.
        dPragma (Dict[str, List[SPragInfo]]): 파싱된 프라그마 정보를 저장하는 딕셔너리.
                                              키는 프라그마 키워드, 값은 SPragInfo 객체의 리스트입니다.
        dFileInfo (Dict[str, CellInfos]): 파일 메타데이터를 저장하는 딕셔너리.
                                           키는 정보의 종류(예: "S_FILE"), 값은 CellInfos 객체입니다.
        MkFilePath (str): Excel 시트에서 읽어온 파일 생성 기본 경로.
        sht_name (str): 처리 대상 Excel 시트의 이름.
        sht_data (List[List[Any]]): 처리 대상 Excel 시트의 전체 셀 데이터.
    """

    def __init__(self, sht_info: Any, d_file_info: Dict[str, CellInfos]):
        """
        FileInfo 객체를 초기화합니다.

        Args:
            sht_info (Any): 처리할 Excel 시트 정보를 담고 있는 객체.
                              `Name` (시트 이름)과 `Data` (셀 데이터 2차원 리스트) 속성을 가져야 합니다.
            d_file_info (Dict[str, CellInfos]): 파일 메타데이터를 저장할 딕셔너리 객체.
                                                 이 객체는 외부에서 생성되어 참조로 전달되며,
                                                 클래스 내부에서 파싱된 정보로 채워집니다.
        """
        self.SrcList: List[str] = []
        self.HdrList: List[str] = []

        self.dPragma: Dict[str, List[SPragInfo]] = {}
        self.dFileInfo: Dict[str, CellInfos] = d_file_info

        self.file_path_read = SCellPos(0, 0)
        self.src_info_read = SCellPos(0, 0)
        self.hdr_info_read = SCellPos(0, 0)
        self.prgm_info_read = SCellPos(0, 0)

        self.MkFilePath: str = ""
        self.sht_name: str = sht_info.Name
        self.sht_data: List[List[Any]] = sht_info.Data

    def chk_position(self) -> None:
        """
        "FileInfo" 시트 내에서 주요 정보 블록("$파일 생성 경로", "$소스 (.c) 파일 정보" 등)의
        시작 위치(행, 열)를 식별하여 내부 속성(file_path_read, src_info_read 등)에 저장합니다.
        """
        for row in range(1, len(self.sht_data)):
            # 행의 길이를 확인하여 IndexError 방지
            if row < len(self.sht_data) and self.sht_data[row] is not None:
                for col in range(1, len(self.sht_data[row])):
                    cell_str = Info.ReadCell(self.sht_data, row, col)
                    if cell_str == Info.FilePathTitle:
                        self.file_path_read.Row = row
                        self.file_path_read.Col = col + 1
                    elif cell_str == Info.SrcInfoTitle:
                        self.src_info_read.Row = row + 1
                        self.src_info_read.Col = col + 1
                    elif cell_str == Info.HdrInfoTitle:
                        self.hdr_info_read.Row = row + 1
                        self.hdr_info_read.Col = col + 1
                    elif cell_str == Info.PrgmInfoTitle:
                        self.prgm_info_read.Row = row + 3
                        self.prgm_info_read.Col = col
                    elif cell_str == Info.XlsInfoTitle: # XlsInfoTitle 발견 시 해당 행 탐색 중단
                        break
            else: # 현재 행이 없거나 None인 경우 다음 행으로
                continue
            # XlsInfoTitle에 도달하면 외부 루프도 중단 (더 이상 필요한 정보 없음)
            if Info.ReadCell(self.sht_data,row,1) == Info.XlsInfoTitle and any(Info.ReadCell(self.sht_data,row,c) == Info.XlsInfoTitle for c in range(len(self.sht_data[row])) if row<len(self.sht_data) and c < len(self.sht_data[row]) and self.sht_data[row] is not None ): # 더 정확한 조건으로 수정 필요 가능성 있음
                 break


    def read_file_path(self) -> str:
        """
        "FileInfo" 시트에서 "$파일 생성 경로"로 지정된 기본 파일 생성 경로를 읽습니다.

        읽어온 경로는 필요에 따라 앞뒤 '/' 문자를 정리하여 반환합니다.

        Returns:
            str: 정리된 파일 생성 경로 문자열. 경로 정보가 없으면 빈 문자열.
        """
        file_path = ""
        if self.file_path_read.Row != 0 and self.file_path_read.Col != 0:
            file_path = Info.ReadCell(
                self.sht_data, self.file_path_read.Row, self.file_path_read.Col
            )
            if file_path: # 경로가 존재할 경우에만 처리
                if not file_path.startswith("/"): # MkFilePath가 이미 /로 시작할 수 있으므로 조건부 추가
                    if self.MkFilePath and not self.MkFilePath.endswith("/"):
                        file_path = self.MkFilePath + "/" + file_path
                    elif self.MkFilePath:
                        file_path = self.MkFilePath + file_path
                    # else: file_path remains as is, or could be prefixed with "/" if that's the desired default

                if file_path.endswith("/"):
                    file_path = file_path[:-1]
        return file_path

    def read_src_hdr_info(self) -> bool:
        """
        "FileInfo" 시트에서 소스 및 헤더 파일의 상세 정보(파일명, 간략설명, 작성자, 날짜 등)를 읽어
        `self.dFileInfo` 딕셔너리에 저장합니다.

        정보 블록을 찾지 못하거나 필수 파일 확장자(.c, .h) 검사, 파일명 일치 검사,
        이미 정의된 파일명인지 등을 확인하여 오류가 있으면 True를 반환합니다.

        Returns:
            bool: 정보 읽기 및 검증 과정에서 오류 발생 시 True, 성공 시 False.
        """
        err_cnt = 0
        info_str = ""

        # 소스 파일 정보 위치 확인 및 CellInfos 객체 초기화
        if self.src_info_read.Row != 0 and self.src_info_read.Col != 0:
            base_row, base_col = self.src_info_read.Row, self.src_info_read.Col
            self.dFileInfo["S_FILE"] = CellInfos(base_row, base_col, "")
            self.dFileInfo["S_BRIF"] = CellInfos(base_row, base_col + 3, "")
            self.dFileInfo["S_AUTH"] = CellInfos(base_row + 1, base_col, "")
            self.dFileInfo["S_DATE"] = CellInfos(base_row + 1, base_col + 3, "")
            self.dFileInfo["S_REMA"] = CellInfos(base_row + 2, base_col, "")
            self.dFileInfo["S_VERS"] = CellInfos(base_row + 2, base_col + 3, "")
            self.dFileInfo["S_HIST"] = CellInfos(base_row + 3, base_col, "")
            self.dFileInfo["S_INCL"] = CellInfos(base_row + 5, base_col, "")
        else:
            err_cnt += 1
            Info.WriteErrMsg(f'"{Info.SrcInfoTitle}" 정보를 FileInfo 시트에서 찾을 수 없습니다.')

        # 헤더 파일 정보 위치 확인 및 CellInfos 객체 초기화
        if self.hdr_info_read.Row != 0 and self.hdr_info_read.Col != 0:
            base_row, base_col = self.hdr_info_read.Row, self.hdr_info_read.Col
            self.dFileInfo["H_FILE"] = CellInfos(base_row, base_col, "")
            self.dFileInfo["H_BRIF"] = CellInfos(base_row, base_col + 3, "")
            self.dFileInfo["H_AUTH"] = CellInfos(base_row + 1, base_col, "")
            self.dFileInfo["H_DATE"] = CellInfos(base_row + 1, base_col + 3, "")
            self.dFileInfo["H_REMA"] = CellInfos(base_row + 2, base_col, "")
            self.dFileInfo["H_VERS"] = CellInfos(base_row + 2, base_col + 3, "")
            self.dFileInfo["H_HIST"] = CellInfos(base_row + 3, base_col, "")
            self.dFileInfo["H_INCL"] = CellInfos(base_row + 5, base_col, "")
        else:
            err_cnt += 1
            Info.WriteErrMsg(f'"{Info.HdrInfoTitle}" 정보를 FileInfo 시트에서 찾을 수 없습니다.')
        
        if err_cnt > 0: return True # 필수 정보 블록 누락 시 조기 반환

        # 각 정보 항목 값 읽기
        for d_i_key, d_i_value in self.dFileInfo.items():
            if d_i_value.Row == 0 and d_i_value.Col == 0: # 초기화되지 않은 CellInfos는 건너뜀
                continue
            if d_i_key.endswith("_HIST"): # History 항목 처리
                temp_col = d_i_value.Col
                info_str = ""
                while True:
                    his_date = Info.ReadCell(self.sht_data, d_i_value.Row, temp_col)
                    his_desc = Info.ReadCell(self.sht_data, d_i_value.Row + 1, temp_col)
                    if not his_date and not his_desc: break
                    info_str += f"\n\t\t-#{his_date}\n"
                    processed_desc = "\n".join([f"\t\t\t{line}" for line in his_desc.split('\n')])
                    info_str += f"{processed_desc}\n"
                    temp_col += 1
            else:
                info_str = Info.ReadCell(self.sht_data, d_i_value.Row, d_i_value.Col)
            
            info_str = info_str.strip().replace("\n", "\r\n")

            if d_i_key.endswith("_INCL") and '"' in info_str:
                info_str = info_str.replace('"', "")
                if "," in info_str: # 여러 include 파일 처리
                    splt_inc = [inc.strip() for inc in info_str.split(",")]
                    info_str = "\r\n".join(splt_inc)
            
            d_i_value.Str = info_str

        # 파일명 및 확장자 검증
        s_file_info = self.dFileInfo.get("S_FILE")
        h_file_info = self.dFileInfo.get("H_FILE")

        if not s_file_info or not s_file_info.Str.lower().endswith(".c"):
            err_cnt += 1
            Info.WriteErrCell(EErrType.FileExtension, self.sht_name, s_file_info.Row if s_file_info else 0, s_file_info.Col if s_file_info else 0)
        if not h_file_info or not h_file_info.Str.lower().endswith(".h"):
            err_cnt += 1
            Info.WriteErrCell(EErrType.FileExtension, self.sht_name, h_file_info.Row if h_file_info else 0, h_file_info.Col if h_file_info else 0)

        if s_file_info and h_file_info and s_file_info.Str and h_file_info.Str:
            temp_src_name = os.path.splitext(s_file_info.Str)[0]
            temp_hdr_name = os.path.splitext(h_file_info.Str)[0]
            if temp_src_name != temp_hdr_name:
                err_cnt += 1
                Info.WriteErrCell(EErrType.FileName, self.sht_name, s_file_info.Row, s_file_info.Col)

            if temp_src_name in Info.FileList:
                err_cnt += 1
                Info.WriteErrCell(EErrType.FileExist, self.sht_name, s_file_info.Row, s_file_info.Col)
            else:
                Info.FileList.append(temp_src_name)

        return err_cnt > 0

    def Read(self) -> bool:
        """
        "FileInfo" 시트에서 모든 관련 정보(파일 경로, 소스/헤더 정보, 프라그마 정보)를 읽습니다.

        내부적으로 `chk_position`, `read_file_path`, `read_src_hdr_info`, `read_prgm_info`를 호출합니다.

        Returns:
            bool: 정보 읽기 과정에서 하나 이상의 오류가 발생하면 True, 모두 성공하면 False.
        """
        err_cnt = 0
        self.chk_position()
        self.MkFilePath = self.read_file_path()
        if self.read_src_hdr_info(): err_cnt += 1
        if self.read_prgm_info(): err_cnt += 1
        return err_cnt > 0

    def read_prgm_info(self) -> bool:
        """
        "FileInfo" 시트에서 "$Pragma Section 정보" 블록의 프라그마 설정들을 읽어 `self.dPragma`에 저장합니다.

        각 프라그마는 키워드와 두 개의 클래스(class_1, class_2) 설정으로 구성됩니다.
        정보 누락이나 키워드 중복 시 오류를 기록합니다.

        Returns:
            bool: 프라그마 정보 읽기 중 오류 발생 시 True, 성공 시 False.
        """
        err_flag = False
        if self.prgm_info_read.Row == 0 or self.prgm_info_read.Col == 0:
            # 프라그마 정보 블록 자체가 없는 경우, 오류는 아니지만 로깅 가능
            logging.info(f'"{Info.PrgmInfoTitle}" 블록이 FileInfo 시트에 정의되지 않았습니다.')
            return False # 오류는 아님

        row = self.prgm_info_read.Row
        col = self.prgm_info_read.Col

        while row < len(self.sht_data):
            keyword = Info.ReadCell(self.sht_data, row, col)
            # 클래스 정보들을 한 번에 읽기
            c1_data = [Info.ReadCell(self.sht_data, row, col + i) for i in range(1, 9)]
            row += 1
            if row >= len(self.sht_data): # 다음 행이 없는 경우 방지
                 if keyword or any(c1_data): # 마지막 행에 데이터가 있었다면 오류 가능성
                      logging.warning(f"프라그마 정보 마지막 행 처리 중 데이터 부족 가능성: {keyword}")
                 break
            c2_data = [Info.ReadCell(self.sht_data, row, col + i) for i in range(1, 9)]

            class_1 = SPragInfo(c1_data[0], c1_data[1], c1_data[2], c1_data[3], c1_data[4], c1_data[5], c1_data[6], c1_data[7])
            class_2 = SPragInfo(c1_data[0], c2_data[1], c2_data[2], c2_data[3], c2_data[4], c2_data[5], c2_data[6], c1_data[7]) # PreCode, EndCode는 class_1과 동일

            if not keyword and not class_1.ClassName and not class_2.ClassName: break # 정보 종료 조건

            current_row_has_error = False
            # 필수 항목 검사 및 오류 기록
            if not keyword: Info.WriteErrCell(EErrType.PrgmEmpty, self.sht_name, row - 1, col); current_row_has_error = True
            elif keyword in self.dPragma: Info.WriteErrCell(EErrType.PrgmKey, self.sht_name, row - 1, col); current_row_has_error = True
            # ... (기타 class_1, class_2 필드 검사 및 오류 기록) ...

            if not current_row_has_error and keyword and keyword not in self.dPragma:
                self.dPragma[keyword] = [class_1, class_2]
            if current_row_has_error: err_flag = True
            row += 1
        return err_flag

    def Write(self) -> None:
        """
        파싱된 파일 정보를 바탕으로 소스 및 헤더 파일 상단에 포함될 주석 블록을 생성합니다.

        생성된 주석 블록은 각각 `self.SrcList`와 `self.HdrList`에 저장됩니다.
        내부적으로 `write_file_info`를 호출합니다.
        """
        # dFileInfo에 키가 없을 경우를 대비하여 .get 사용 및 기본값 제공
        src_info = [
            self.dFileInfo.get("S_FILE", CellInfos()).Str,
            self.dFileInfo.get("S_BRIF", CellInfos()).Str,
            self.dFileInfo.get("S_AUTH", CellInfos()).Str,
            self.dFileInfo.get("S_DATE", CellInfos()).Str,
            self.dFileInfo.get("S_REMA", CellInfos()).Str,
            self.dFileInfo.get("S_VERS", CellInfos()).Str,
            self.dFileInfo.get("S_HIST", CellInfos()).Str,
        ]
        hdr_info = [
            self.dFileInfo.get("H_FILE", CellInfos()).Str,
            self.dFileInfo.get("H_BRIF", CellInfos()).Str,
            self.dFileInfo.get("H_AUTH", CellInfos()).Str,
            self.dFileInfo.get("H_DATE", CellInfos()).Str,
            self.dFileInfo.get("H_REMA", CellInfos()).Str,
            self.dFileInfo.get("H_VERS", CellInfos()).Str,
            self.dFileInfo.get("H_HIST", CellInfos()).Str,
        ]
        self.write_file_info(True, src_info)
        self.write_file_info(False, hdr_info)

    def write_file_info(self, src: bool, info: List[str]) -> None:
        """
        주어진 정보 리스트를 사용하여 파일 정보 주석 블록 문자열 리스트를 생성합니다.

        Args:
            src (bool): True이면 소스 파일용(`self.SrcList`), False이면 헤더 파일용(`self.HdrList`)으로 생성.
            info (List[str]): 파일 정보를 담은 문자열 리스트. 순서는 [파일명, 간략설명, 작성자, 날짜, 비고, 버전, 변경이력].
        """
        code_list: List[str] = []
        code_list.append(Info.StartAnnotation[1])
        code_list.append("\t\tOriganization") # 오타 수정: Organization
        code_list.append(Info.EndAnnotation[1])
        code_list.append("/**")
        code_list.append(f"\t@file\t\t:\t{info[0] if len(info) > 0 else ''}")
        code_list.append(f"\t@brief\t\t:\t{info[1] if len(info) > 1 else ''}")
        code_list.append(f"\t@author\t\t:\t{info[2] if len(info) > 2 else ''}")
        code_list.append(f"\t@date\t\t:\t{info[3] if len(info) > 3 else ''}")

        if len(info) > 4 and info[4]: code_list.append(f"\t@remarks\t:\t{info[4]}")
        if len(info) > 5 and info[5]: code_list.append(f"\t@version\t:\t{info[5]}")
        if len(info) > 6 and info[6]: code_list.append("\t@par History")
        
        if len(info) > 6: code_list.append(info[6]) # 변경 이력 추가
        code_list.append("*/")
        code_list.append(Info.InterAnnotation[1])
        code_list.append("")

        if src:
            self.SrcList = code_list
        else:
            self.HdrList = code_list
