from typing import Dict, List, Optional
from core.info import Info, EErrType, CellInfos, SCellPos, SPragInfo


class FileInfo:
    """파일정보 셀 읽기/주석 생성"""
    def __init__(self, sht_info, d_file_info):
        self.SrcList = []
        self.HdrList = []
        
        self.dPragma: Dict[str, List[SPragInfo]] = {}  # 프라그마 정보
        self.dFileInfo = d_file_info  # FileInfo 정보
        
        self.file_path_read = SCellPos(0, 0)  # 파일 생성 경로 셀 위치
        self.src_info_read = SCellPos(0, 0)  # 소스 파일 정보 셀 위치
        self.hdr_info_read = SCellPos(0, 0)  # 헤더 파일 정보 셀 위치
        self.prgm_info_read = SCellPos(0, 0)  # 프라그마 정보 셀 위치
        
        self.MkFilePath = ""
        self.sht_name = sht_info.Name
        self.sht_data = sht_info.Data
    
    def chk_position(self):
        """셀 위치 확인"""
        for row in range(1, len(self.sht_data)):
            for col in range(1, len(self.sht_data[row]) if row < len(self.sht_data) else 0):
                cell_str = Info.ReadCell(self.sht_data, row, col)
                if cell_str == Info.FilePathTitle:
                    self.file_path_read.Row = row
                    self.file_path_read.Col = col + 1
                if cell_str == Info.SrcInfoTitle:
                    self.src_info_read.Row = row + 1
                    self.src_info_read.Col = col + 1
                if cell_str == Info.HdrInfoTitle:
                    self.hdr_info_read.Row = row + 1
                    self.hdr_info_read.Col = col + 1
                if cell_str == Info.PrgmInfoTitle:
                    self.prgm_info_read.Row = row + 3
                    self.prgm_info_read.Col = col
                if cell_str == Info.XlsInfoTitle:
                    break
    
    def read_file_path(self):
        """파일 경로 읽기"""
        file_path = ""
        
        if self.file_path_read.Row != 0 and self.file_path_read.Col != 0:
            file_path = Info.ReadCell(self.sht_data, self.file_path_read.Row, self.file_path_read.Col)
            
            if file_path:
                if not file_path.startswith("/"):
                    file_path = "/" + self.MkFilePath
                if file_path.endswith("/"):
                    file_path = file_path[:-1]
        
        return file_path
    
    def read_src_hdr_info(self):
        """소스/헤더 파일 정보 읽기"""
        err_cnt = 0
        info_str = ""
        
        if self.src_info_read.Row != 0 and self.src_info_read.Col != 0:
            self.dFileInfo["S_FILE"] = CellInfos(self.src_info_read.Row, self.src_info_read.Col, "")
            self.dFileInfo["S_BRIF"] = CellInfos(self.src_info_read.Row, self.src_info_read.Col + 3, "")
            self.dFileInfo["S_AUTH"] = CellInfos(self.src_info_read.Row + 1, self.src_info_read.Col, "")
            self.dFileInfo["S_DATE"] = CellInfos(self.src_info_read.Row + 1, self.src_info_read.Col + 3, "")
            self.dFileInfo["S_REMA"] = CellInfos(self.src_info_read.Row + 2, self.src_info_read.Col, "")
            self.dFileInfo["S_VERS"] = CellInfos(self.src_info_read.Row + 2, self.src_info_read.Col + 3, "")
            self.dFileInfo["S_HIST"] = CellInfos(self.src_info_read.Row + 3, self.src_info_read.Col, "")
            self.dFileInfo["S_INCL"] = CellInfos(self.src_info_read.Row + 5, self.src_info_read.Col, "")
        else:
            err_cnt += 1
            Info.WriteErrMsg(f"\"{Info.SrcInfoTitle}\"를 찾을 수 없음")
        
        if self.hdr_info_read.Row != 0 and self.hdr_info_read.Col != 0:
            self.dFileInfo["H_FILE"] = CellInfos(self.hdr_info_read.Row, self.hdr_info_read.Col, "")
            self.dFileInfo["H_BRIF"] = CellInfos(self.hdr_info_read.Row, self.hdr_info_read.Col + 3, "")
            self.dFileInfo["H_AUTH"] = CellInfos(self.hdr_info_read.Row + 1, self.hdr_info_read.Col, "")
            self.dFileInfo["H_DATE"] = CellInfos(self.hdr_info_read.Row + 1, self.hdr_info_read.Col + 3, "")
            self.dFileInfo["H_REMA"] = CellInfos(self.hdr_info_read.Row + 2, self.hdr_info_read.Col, "")
            self.dFileInfo["H_VERS"] = CellInfos(self.hdr_info_read.Row + 2, self.hdr_info_read.Col + 3, "")
            self.dFileInfo["H_HIST"] = CellInfos(self.hdr_info_read.Row + 3, self.hdr_info_read.Col, "")
            self.dFileInfo["H_INCL"] = CellInfos(self.hdr_info_read.Row + 5, self.hdr_info_read.Col, "")
        else:
            err_cnt += 1
            Info.WriteErrMsg(f"\"{Info.HdrInfoTitle}\"를 찾을 수 없음")
        
        if err_cnt > 0:
            return True
        
        for d_i_key, d_i_value in self.dFileInfo.items():
            if d_i_key == "S_HIST" or d_i_key == "H_HIST":
                temp_col = d_i_value.Col
                info_str = ""
                
                while True:
                    his_date = Info.ReadCell(self.sht_data, d_i_value.Row, temp_col)
                    his_desc = Info.ReadCell(self.sht_data, d_i_value.Row + 1, temp_col)
                    
                    if not his_date and not his_desc:
                        break
                    else:
                        info_str += "\n"
                        info_str += f"\t\t-#{his_date}\n"
                        
                        his_desc = his_desc.replace("\n", "\n\t\t\t")
                        info_str += f"\t\t\t{his_desc}\n"
                    
                    temp_col += 1
            else:
                info_str = Info.ReadCell(self.sht_data, d_i_value.Row, d_i_value.Col)
            
            if info_str.endswith("\n"):
                info_str = info_str[:-1]
            
            info_str = info_str.replace("\n", "\r\n")
            
            if d_i_key == "S_INCL" or d_i_key == "H_INCL":
                if "," in info_str:
                    splt_inc = info_str.split(',')
                    temp_inc = ""
                    
                    for i in range(len(splt_inc)):
                        splt_inc[i] = splt_inc[i].strip()
                        temp_inc += splt_inc[i]
                        if i < len(splt_inc) - 1:
                            temp_inc += "\r\n"
                    info_str = temp_inc
                
                if "\"" in info_str:
                    info_str = info_str.replace("\"", "")
            
            d_i_value.Str = info_str
        
        if not self.dFileInfo["S_FILE"].Str.endswith(".c") and not self.dFileInfo["S_FILE"].Str.endswith(".C"):
            err_cnt += 1
            Info.WriteErrCell(EErrType.FileExtension, self.sht_name, self.dFileInfo["S_FILE"].Row, self.dFileInfo["S_FILE"].Col)
        
        if not self.dFileInfo["H_FILE"].Str.endswith(".h") and not self.dFileInfo["H_FILE"].Str.endswith(".H"):
            err_cnt += 1
            Info.WriteErrCell(EErrType.FileExtension, self.sht_name, self.dFileInfo["H_FILE"].Row, self.dFileInfo["H_FILE"].Col)
        
        temp_src_name = self.dFileInfo["S_FILE"].Str[:-2]
        temp_hdr_name = self.dFileInfo["H_FILE"].Str[:-2]
        
        if temp_src_name != temp_hdr_name:
            err_cnt += 1
            Info.WriteErrCell(EErrType.FileName, self.sht_name, self.dFileInfo["S_FILE"].Row, self.dFileInfo["S_FILE"].Col)
        
        if temp_src_name in Info.FileList:
            err_cnt += 1
            Info.WriteErrCell(EErrType.FileExist, self.sht_name, self.dFileInfo["S_FILE"].Row, self.dFileInfo["S_FILE"].Col)
        else:
            Info.FileList.append(temp_src_name)
        
        if err_cnt > 0:
            return True
        else:
            return False
    
    def Read(self):
        """파일정보 시트 읽기"""
        err_cnt = 0
        err_flag = False
        
        self.chk_position()
        
        self.MkFilePath = self.read_file_path()
        
        err_flag = self.read_src_hdr_info()
        if err_flag:
            err_cnt += 1
        
        err_flag = self.read_prgm_info()
        if err_flag:
            err_cnt += 1
        
        if err_cnt > 0:
            return True
        else:
            return False
    
    def read_prgm_info(self):
        """프라그마 정보 읽기"""
        err_flag = False
        
        if self.prgm_info_read.Row != 0 and self.prgm_info_read.Col != 0:
            row = self.prgm_info_read.Row
            col = self.prgm_info_read.Col
            
            while row < len(self.sht_data):
                keyword = Info.ReadCell(self.sht_data, row, col)
                
                class_1 = SPragInfo()
                class_1.PreCode = Info.ReadCell(self.sht_data, row, col + 1)
                class_1.ClassName = Info.ReadCell(self.sht_data, row, col + 2)
                class_1.SetIstring = Info.ReadCell(self.sht_data, row, col + 3)
                class_1.SetUstring = Info.ReadCell(self.sht_data, row, col + 4)
                class_1.SetAddrMode = Info.ReadCell(self.sht_data, row, col + 5)
                class_1.EndIstring = Info.ReadCell(self.sht_data, row, col + 6)
                class_1.EndUstring = Info.ReadCell(self.sht_data, row, col + 7)
                class_1.EndCode = Info.ReadCell(self.sht_data, row, col + 8)
                
                row += 1
                
                class_2 = SPragInfo()
                class_2.PreCode = class_1.PreCode
                class_2.ClassName = Info.ReadCell(self.sht_data, row, col + 2)
                class_2.SetIstring = Info.ReadCell(self.sht_data, row, col + 3)
                class_2.SetUstring = Info.ReadCell(self.sht_data, row, col + 4)
                class_2.SetAddrMode = Info.ReadCell(self.sht_data, row, col + 5)
                class_2.EndIstring = Info.ReadCell(self.sht_data, row, col + 6)
                class_2.EndUstring = Info.ReadCell(self.sht_data, row, col + 7)
                class_2.EndCode = class_1.EndCode
                
                if not keyword and not class_1.ClassName and not class_2.ClassName:
                    break
                else:
                    local_err_flag = False
                    
                    if not keyword:
                        Info.WriteErrCell(EErrType.PrgmEmpty, self.sht_name, row - 1, col)
                        local_err_flag = True
                    elif keyword in self.dPragma:
                        # 이미 존재하는 키워드는 오류로 표시하지만 덮어쓰지 않음
                        Info.WriteErrCell(EErrType.PrgmKey, self.sht_name, row - 1, col)
                        local_err_flag = True
                    
                    if not class_1.ClassName:
                        Info.WriteErrCell(EErrType.PrgmEmpty, self.sht_name, row - 1, col + 1)
                        local_err_flag = True
                    if not class_1.SetIstring:
                        Info.WriteErrCell(EErrType.PrgmEmpty, self.sht_name, row - 1, col + 2)
                        local_err_flag = True
                    if not class_1.SetUstring:
                        Info.WriteErrCell(EErrType.PrgmEmpty, self.sht_name, row - 1, col + 3)
                        local_err_flag = True
                    if not class_1.EndIstring:
                        Info.WriteErrCell(EErrType.PrgmEmpty, self.sht_name, row - 1, col + 5)
                        local_err_flag = True
                    if not class_1.EndUstring:
                        Info.WriteErrCell(EErrType.PrgmEmpty, self.sht_name, row - 1, col + 6)
                        local_err_flag = True
                    if not class_2.ClassName:
                        Info.WriteErrCell(EErrType.PrgmEmpty, self.sht_name, row, col + 1)
                        local_err_flag = True
                    if not class_2.SetIstring:
                        Info.WriteErrCell(EErrType.PrgmEmpty, self.sht_name, row, col + 2)
                        local_err_flag = True
                    if not class_2.SetUstring:
                        Info.WriteErrCell(EErrType.PrgmEmpty, self.sht_name, row, col + 3)
                        local_err_flag = True
                    if not class_2.EndIstring:
                        Info.WriteErrCell(EErrType.PrgmEmpty, self.sht_name, row, col + 5)
                        local_err_flag = True
                    if not class_2.EndUstring:
                        Info.WriteErrCell(EErrType.PrgmEmpty, self.sht_name, row, col + 6)
                        local_err_flag = True
                    
                    # C# 코드와 동일하게 local_err_flag가 False일 때만 추가
                    if not local_err_flag and keyword and keyword not in self.dPragma:
                        self.dPragma[keyword] = [class_1, class_2]
                
                row += 1
            
        return err_flag
    
    def Write(self):
        """파일정보 코드 생성"""
        src_info = [
            self.dFileInfo["S_FILE"].Str,
            self.dFileInfo["S_BRIF"].Str,
            self.dFileInfo["S_AUTH"].Str,
            self.dFileInfo["S_DATE"].Str,
            self.dFileInfo["S_REMA"].Str,
            self.dFileInfo["S_VERS"].Str,
            self.dFileInfo["S_HIST"].Str
        ]
        
        hdr_info = [
            self.dFileInfo["H_FILE"].Str,
            self.dFileInfo["H_BRIF"].Str,
            self.dFileInfo["H_AUTH"].Str,
            self.dFileInfo["H_DATE"].Str,
            self.dFileInfo["H_REMA"].Str,
            self.dFileInfo["H_VERS"].Str,
            self.dFileInfo["H_HIST"].Str
        ]
        
        self.write_file_info(True, src_info)
        self.write_file_info(False, hdr_info)
    
    def write_file_info(self, src, info):
        """파일 정보 작성"""
        code_list = []
        
        code_list.append(Info.StartAnnotation[1])
        code_list.append("\t\tOriganization")
        code_list.append(Info.EndAnnotation[1])
        
        code_list.append("/**")
        code_list.append(f"\t@file\t\t:\t{info[0]}")
        code_list.append(f"\t@brief\t\t:\t{info[1]}")
        code_list.append(f"\t@author\t\t:\t{info[2]}")
        code_list.append(f"\t@date\t\t:\t{info[3]}")
        
        if info[4]:
            code_list.append(f"\t@remarks\t:\t{info[4]}")
        if info[5]:
            code_list.append(f"\t@version\t:\t{info[5]}")
        if info[6]:
            code_list.append("\t@par History")
        
        code_list.append(info[6])
        code_list.append("*/")
        code_list.append(Info.InterAnnotation[1])
        code_list.append("")
        
        if src:
            self.SrcList = code_list
        else:
            self.HdrList = code_list