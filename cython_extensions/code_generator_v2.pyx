# code_generator_v2.pyx
# cython: language_level=3
# cython: boundscheck=False
# cython: wraparound=False
# cython: cdivision=True
# cython: initializedcheck=False
# cython: nonecheck=False

import cython
from cython import boundscheck, wraparound
from libc.string cimport memcpy
from libc.stdlib cimport malloc, free

@boundscheck(False)
@wraparound(False)
def fast_read_cal_list_processing(cal_list_obj, int start_row, int end_row, list item_list):
    """
    ReadCalList의 핵심 반복문 최적화 - 완전한 데이터 처리 버전
    cal_list.py의 ReadCalList 메서드 최적화
    """
    cdef int row, i, item_count
    cdef object item
    cdef list processed_rows = []
    cdef object sht_data
    cdef bint process_success = False

    if not cal_list_obj or not item_list:
        return processed_rows

    sht_data = cal_list_obj.shtData
    if not sht_data:
        return processed_rows

    item_count = len(item_list)

    for row in range(start_row, min(end_row, len(sht_data))):
        try:
            # 🔥 핵심 수정: 실제 데이터 처리 로직 추가

            # 1. 아이템 행 설정
            for i in range(item_count):
                item = item_list[i]
                if item is not None:
                    item.Row = row

            # 2. 실제 데이터 처리 (Python 메서드 호출)
            # chk_op_code 호출
            if hasattr(cal_list_obj, 'chk_op_code'):
                cal_list_obj.chk_op_code()

            # readRow 또는 readArrMem 호출
            if hasattr(cal_list_obj, 'readRow'):
                cal_list_obj.readRow(row)

            # chkCalList 호출
            if hasattr(cal_list_obj, 'chkCalList'):
                cal_list_obj.chkCalList()

            # 3. 핵심: saveTempList 호출 (데이터를 dTempCode에 저장)
            if hasattr(cal_list_obj, 'saveTempList'):
                cal_list_obj.saveTempList()
                process_success = True

            processed_rows.append(row)

        except Exception as e:
            # 오류 발생 시 해당 행 건너뛰기
            continue

    return processed_rows if process_success else []


@boundscheck(False)
@wraparound(False)
def fast_write_cal_list_processing(list temp_code_items):
    """
    writeCalList의 코드 생성 최적화 (극한 최적화 버전)
    """
    cdef int i, length, line_length
    cdef list line_str
    cdef str op_code, key_str, type_str, name_str, val_str, desc_str
    cdef list processed_items
    cdef object line_item
    cdef bint has_float32
    cdef object item0, item1, item2, item3, item4, item5

    if not temp_code_items:
        return []

    length = len(temp_code_items)
    processed_items = [None] * length  # 미리 할당으로 성능 향상

    for i in range(length):
        line_item = temp_code_items[i]
        if line_item is not None:
            line_str = <list>line_item
            line_length = len(line_str)

            if line_length >= 6:
                # 직접 인덱스 접근으로 최적화
                item0 = line_str[0]
                item1 = line_str[1]
                item2 = line_str[2]
                item3 = line_str[3]
                item4 = line_str[4]
                item5 = line_str[5]

                # 타입 변환 최적화
                op_code = <str>item0 if item0 is not None else ""
                key_str = <str>item1 if item1 is not None else ""
                type_str = <str>item2 if item2 is not None else ""
                name_str = <str>item3 if item3 is not None else ""
                val_str = <str>item4 if item4 is not None else ""
                desc_str = <str>item5 if item5 is not None else ""

                # FLOAT32 타입 확인 최적화 (문자열 비교 최소화)
                if val_str and type_str:
                    # 빠른 문자열 체크: 첫 글자가 'F'인지 확인
                    if len(type_str) >= 7 and type_str[0] == 'F' and "FLOAT32" in type_str:
                        val_str = fast_add_float_suffix_ultra_optimized(val_str)

                processed_items[i] = [op_code, key_str, type_str, name_str, val_str, desc_str]
            else:
                processed_items[i] = line_str
        else:
            processed_items[i] = None

    return processed_items

@boundscheck(False)
@wraparound(False)
cdef str fast_add_float_suffix_ultra_optimized(str val_str):
    """극한 최적화된 float suffix 추가"""
    cdef int length = len(val_str)
    cdef int i = 0
    cdef char c
    cdef bint has_dot = False
    cdef bint has_digit = False
    cdef bint is_negative = False

    if length == 0:
        return val_str

    # 이미 접미사가 있는지 빠른 체크
    if val_str[length-1] == 'f' or val_str[length-1] == 'F':
        return val_str

    # 주석 체크 (빠른 체크)
    if '/' in val_str:
        return val_str

    # 음수 체크
    if val_str[0] == '-':
        is_negative = True
        i = 1

    # 숫자 패턴 확인 (C 수준 최적화)
    while i < length:
        c = val_str[i]
        if c >= '0' and c <= '9':
            has_digit = True
        elif c == '.':
            if has_dot:  # 소수점이 두 번 나오면 안됨
                return val_str
            has_dot = True
        else:
            return val_str  # 숫자가 아닌 문자 발견
        i += 1

    if not has_digit:
        return val_str

    # 접미사 추가 (최적화된 문자열 연산)
    if has_dot:
        return val_str + 'f'
    else:
        if val_str == '0' or val_str == '-0':
            return '0.f'
        else:
            return val_str + '.f'

@boundscheck(False)
@wraparound(False)
def ultra_fast_write_cal_list_processing(list temp_code_items):
    """
    극한 최적화된 배치 처리 버전
    """
    cdef int i, length, batch_size = 1000
    cdef list result = []

    if not temp_code_items:
        return result

    length = len(temp_code_items)

    # 배치 단위로 처리
    for i in range(0, length, batch_size):
        end_idx = min(i + batch_size, length)
        batch = temp_code_items[i:end_idx]
        processed_batch = process_batch_optimized(batch)
        result.extend(processed_batch)

    return result

@boundscheck(False)
@wraparound(False)
cdef list process_batch_optimized(list batch):
    """배치 최적화 처리"""
    cdef int i, batch_length = len(batch)
    cdef list processed_batch = [None] * batch_length
    cdef list line_str
    cdef object line_item
    cdef str op_code, key_str, type_str, name_str, val_str, desc_str
    cdef bint needs_float_processing

    for i in range(batch_length):
        line_item = batch[i]
        if line_item is not None and len(line_item) >= 6:
            line_str = <list>line_item

            # 직접 할당으로 최적화
            op_code = <str>line_str[0] if line_str[0] is not None else ""
            key_str = <str>line_str[1] if line_str[1] is not None else ""
            type_str = <str>line_str[2] if line_str[2] is not None else ""
            name_str = <str>line_str[3] if line_str[3] is not None else ""
            val_str = <str>line_str[4] if line_str[4] is not None else ""
            desc_str = <str>line_str[5] if line_str[5] is not None else ""

            # FLOAT32 처리 최적화
            needs_float_processing = (val_str and type_str and
                                    len(type_str) >= 7 and
                                    type_str[0] == 'F' and
                                    "FLOAT32" in type_str)

            if needs_float_processing:
                val_str = fast_add_float_suffix_ultra_optimized(val_str)

            processed_batch[i] = [op_code, key_str, type_str, name_str, val_str, desc_str]
        else:
            processed_batch[i] = line_item

    return processed_batch


@boundscheck(False)
@wraparound(False)
cdef bint is_digit_char(char c):
    """C 수준 숫자 문자 확인"""
    return c >= '0' and c <= '9'

@boundscheck(False)
@wraparound(False)
cdef bint is_float_number_cython(str val_str):
    """C 수준 float 숫자 패턴 확인"""
    cdef int length = len(val_str)
    cdef int i = 0
    cdef char c
    cdef bint has_dot = False
    cdef bint has_digit = False

    if length == 0:
        return False

    # 음수 처리
    if val_str[0] == '-':
        i = 1
        if length == 1:
            return False

    # 각 문자 확인
    while i < length:
        c = val_str[i]
        if is_digit_char(c):
            has_digit = True
        elif c == '.':
            if has_dot:  # 소수점이 두 번 나오면 안됨
                return False
            has_dot = True
        else:
            return False
        i += 1

    return has_digit

@boundscheck(False)
@wraparound(False)
def fast_add_float_suffix_with_type(str val_str, str type_str):
    """
    Float Suffix 추가 최적화 (C 수준 문자열 처리)
    """
    # float 타입이 아니면 원본 값 그대로 반환
    if "float" not in type_str.lower():
        return val_str

    # 빈 문자열이거나 이미 접미사가 있는 경우
    if not val_str or val_str.endswith('f') or val_str.endswith('F'):
        return val_str

    # 주석이 포함된 경우 처리하지 않음 (안전성 우선)
    if '/*' in val_str or '//' in val_str:
        return val_str

    # C 수준 숫자 패턴 확인
    if not is_float_number_cython(val_str):
        return val_str

    # 소수점 확인
    cdef bint has_dot = '.' in val_str

    if has_dot:
        # 이미 소수점이 있으면 f만 추가
        return val_str + 'f'
    else:
        # 정수인 경우
        if val_str == '0' or val_str == '-0':
            return '0.f'
        else:
            return val_str + '.f'


@boundscheck(False)
@wraparound(False)
def apply_simple_float_suffix(str val_str):
    """
    단순한 숫자에 Float Suffix 적용
    """
    cdef int length, i
    cdef bint has_dot = False
    cdef bint is_number = True
    cdef char c
    
    if not val_str:
        return val_str
    
    length = len(val_str)
    if length == 0:
        return val_str
    
    # 숫자인지 확인
    for i in range(length):
        c = val_str[i]
        if c == '.':
            if has_dot:
                is_number = False
                break
            has_dot = True
        elif c == '-' and i == 0:
            continue
        elif not (c >= '0' and c <= '9'):
            is_number = False
            break
    
    if not is_number:
        return val_str
    
    # Float suffix 추가
    if has_dot:
        return val_str + 'f'
    else:
        if val_str == '0':
            return '0.f'
        else:
            return val_str + '.f'


@boundscheck(False)
@wraparound(False)
cdef str extract_and_replace_comments_cython(str val_str, list comment_placeholders, list comment_values):
    """C 수준 주석 추출 및 치환"""
    cdef int i = 0
    cdef int length = len(val_str)
    cdef int comment_start = -1
    cdef int comment_count = 0
    cdef str result = ""
    cdef str placeholder
    cdef str comment_text

    while i < length:
        # 블록 주석 시작 확인
        if i < length - 1 and val_str[i] == '/' and val_str[i + 1] == '*':
            if comment_start == -1:
                comment_start = i
            i += 2
            continue

        # 블록 주석 끝 확인
        if comment_start != -1 and i < length - 1 and val_str[i] == '*' and val_str[i + 1] == '/':
            comment_text = val_str[comment_start:i + 2]
            placeholder = f"__COMMENT_BLOCK_{comment_count}__"
            comment_placeholders.append(placeholder)
            comment_values.append(comment_text)
            result += placeholder
            comment_count += 1
            comment_start = -1
            i += 2
            continue

        # 라인 주석 확인
        if comment_start == -1 and i < length - 1 and val_str[i] == '/' and val_str[i + 1] == '/':
            # 라인 끝까지 찾기
            line_end = i
            while line_end < length and val_str[line_end] != '\n':
                line_end += 1

            comment_text = val_str[i:line_end]
            placeholder = f"__COMMENT_LINE_{comment_count}__"
            comment_placeholders.append(placeholder)
            comment_values.append(comment_text)
            result += placeholder
            comment_count += 1
            i = line_end
            continue

        # 일반 문자 처리
        if comment_start == -1:
            result += val_str[i]

        i += 1

    return result

@boundscheck(False)
@wraparound(False)
def process_complex_float_suffix(str val_str):
    """
    복잡한 문자열의 Float Suffix 처리 (C 수준 주석 처리)
    """
    cdef list comment_placeholders = []
    cdef list comment_values = []
    cdef str modified_val
    cdef int i

    # C 수준 주석 추출
    modified_val = extract_and_replace_comments_cython(val_str, comment_placeholders, comment_values)

    # 주석이 제거된 부분에만 Float Suffix 적용
    modified_val = apply_simple_float_suffix(modified_val)

    # 주석 복원
    for i in range(len(comment_placeholders)):
        modified_val = modified_val.replace(comment_placeholders[i], comment_values[i])

    return modified_val


@boundscheck(False)
@wraparound(False)
def fast_code_line_processing(list src_list, bint tab_flag):
    """
    코드 라인 처리 최적화
    make_code.py의 코드 라인 처리 최적화
    """
    cdef int i, length
    cdef str line, tab_str
    cdef list result = []
    cdef object line_obj
    
    if not src_list:
        return result
    
    length = len(src_list)
    tab_str = "\t" if tab_flag else ""
    
    for i in range(length):
        line_obj = src_list[i]
        if line_obj is None:
            line = ""
        else:
            line = str(line_obj).rstrip()
        
        # 전처리 지시문 처리
        if line.strip().startswith("#"):
            result.append(tab_str + line)
        else:
            result.append(tab_str + line)
    
    return result


@boundscheck(False)
@wraparound(False)
def fast_string_replacement_batch(list string_list, str old_str, str new_str):
    """
    대량 문자열 치환 최적화
    """
    cdef int i, length
    cdef list result
    cdef str item
    cdef object item_obj
    
    if not string_list:
        return []
    
    length = len(string_list)
    result = [None] * length
    
    for i in range(length):
        item_obj = string_list[i]
        if item_obj is None:
            result[i] = None
        else:
            item = str(item_obj)
            if old_str in item:
                result[i] = item.replace(old_str, new_str)
            else:
                result[i] = item
    
    return result


@boundscheck(False)
@wraparound(False)
def fast_buffer_append_optimization(list buffer, list new_items):
    """
    버퍼 추가 최적화
    """
    cdef int i, length
    
    if not new_items:
        return
    
    length = len(new_items)
    for i in range(length):
        buffer.append(new_items[i])


@boundscheck(False)
@wraparound(False)
def fast_conditional_code_generation(str ifdef_str, str prjt_def_title, str prjt_name, str prjt_desc, int tab_size):
    """
    조건부 컴파일 코드 생성 최적화
    """
    cdef str def_str
    
    if prjt_name == "ELSE":
        def_str = ifdef_str
    else:
        def_str = ifdef_str + prjt_def_title + " == " + prjt_name + ")"
        if prjt_desc:
            if len(def_str) % tab_size >= 3:
                def_str += "\t"
            def_str += "\t// " + prjt_desc
    
    return def_str


@boundscheck(False)
@wraparound(False)
def fast_include_processing(str incl_str):
    """
    인클루드 문자열 처리 최적화
    """
    cdef list includes = []
    cdef list lines
    cdef int i, length
    cdef str line
    
    if not incl_str:
        return includes
    
    lines = incl_str.split('\r\n')
    length = len(lines)
    
    for i in range(length):
        line = lines[i]
        if line and line.strip():
            includes.append(line)
    
    return includes


@boundscheck(False)
@wraparound(False)
def fast_padding_calculation(int align, int str_len, bint type_flag, int add_tab, int tab_size):
    """
    패딩 계산 최적화 (C 수준 성능)
    """
    cdef int rt = 0
    
    if type_flag:
        align += 1
        str_len += 1
    
    rt = (align // tab_size) - (str_len // tab_size) + 1
    
    if type_flag:
        rt += 1
    else:
        rt += str_len
    
    if (align % tab_size) >= (tab_size - add_tab):
        rt += 1
    
    return rt


@boundscheck(False)
@wraparound(False)
def fast_define_code_generation(str name_str, str val_str, str desc_str, int name_align, int val_align, int tab_size):
    """
    #define 코드 생성 최적화
    """
    cdef str result = "#define\t" + name_str
    cdef int pad_tab_cnt
    
    # 패딩 계산
    pad_tab_cnt = (name_align // tab_size) - (len(name_str) // tab_size) + 1
    if (name_align % tab_size) >= (tab_size - 1):
        pad_tab_cnt += 1
    
    result += "\t" * pad_tab_cnt
    
    if desc_str:
        # val_str 패딩 계산
        pad_tab_cnt = (val_align // tab_size) - (len(val_str) // tab_size) + 1
        if (val_align % tab_size) >= (tab_size - 1):
            pad_tab_cnt += 1
        result += val_str + "\t" * pad_tab_cnt + desc_str
    else:
        result += val_str
    
    return result


@boundscheck(False)
@wraparound(False)
cdef int calculate_pad_cython(int align, int str_len, bint type_flag, int add_tab, int tab_size):
    """
    패딩 계산 함수 - Python의 calculatePad 로직을 Cython으로 포팅
    """
    cdef int rt = 0

    if type_flag:
        align += 1
        str_len += 1

    rt = (align // tab_size) - (str_len // tab_size) + 1

    if type_flag:
        rt += 1
    else:
        rt += str_len

    if (align % tab_size) >= (tab_size - add_tab):
        rt += 1

    return rt

@boundscheck(False)
@wraparound(False)
cdef str ljust_cython(str text, int width):
    """
    Python의 ljust() 함수를 Cython으로 구현
    """
    cdef str result = text
    while len(result) < width:
        result += " "
    return result

@boundscheck(False)
@wraparound(False)
cdef str ljust_with_tabs(str text, int target_width):
    """
    Python의 ljust(width, '\t') 함수를 Cython으로 구현
    """
    cdef str result = text
    while len(result) < target_width:
        result += "\t"
    return result

@boundscheck(False)
@wraparound(False)
def fast_variable_code_generation(str key_str, str type_str, str name_str, str val_str, str desc_str,
                                 int key_align, int type_align, int name_align, int val_align, int tab_size):
    """
    변수 선언 코드 생성 최적화 - Python 로직 정확히 포팅
    """
    cdef str src_data_str = ""
    cdef str hdr_data_str = "extern "
    cdef int pad_tab_cnt = 0

    # Python 로직과 동일: ljust(key_align + 1) - 공백으로 채움
    if key_str and key_str != "Empty":
        src_data_str = ljust_cython(key_str, key_align + 1)
        hdr_data_str += ljust_cython(key_str, key_align + 1)

    # Python 로직과 동일: ljust(type_align + 1) - 공백으로 채움
    src_data_str += ljust_cython(type_str, type_align + 1)
    hdr_data_str += ljust_cython(type_str, type_align + 1)

    # Python 로직과 동일: calculatePad 호출
    pad_tab_cnt = calculate_pad_cython(len(src_data_str) + name_align,
                                     len(src_data_str) + len(name_str),
                                     False, 0, tab_size)

    if not val_str:
        # 값이 없는 경우
        src_data_str += name_str + ";"
        hdr_data_str += name_str + ";"
        if desc_str:
            # Python 로직: "\t".ljust(pad_tab_cnt - len(src_data_str) - len(name_str), '\t')
            tab_padding_len = pad_tab_cnt - len(src_data_str) - len(name_str)
            if tab_padding_len > 0:
                src_data_str += ljust_with_tabs("\t", tab_padding_len) + desc_str
                hdr_data_str += ljust_with_tabs("\t", tab_padding_len) + desc_str
    else:
        # 값이 있는 경우 - Python 로직 정확히 포팅
        # Python: name_str.ljust(pad_tab_cnt - len(src_data_str), '\t') + "= "
        target_width = pad_tab_cnt - len(src_data_str)
        src_data_str += ljust_with_tabs(name_str, target_width) + "= "

        if desc_str:
            # 값 정렬 계산
            pad_tab_cnt = calculate_pad_cython(val_align - 1, len(val_str) - 1, False, 1, tab_size)
            # Python: val_str + ";".ljust(pad_tab_cnt - len(val_str) + 2, '\t') + desc_str
            semicolon_padding_len = pad_tab_cnt - len(val_str) + 2
            src_data_str += val_str + ljust_with_tabs(";", semicolon_padding_len) + desc_str

            # 헤더 처리
            pad_tab_cnt = calculate_pad_cython(len(hdr_data_str) + name_align + 1,
                                             len(hdr_data_str) + len(name_str) + 1,
                                             False, 1, tab_size)
            hdr_padding_len = pad_tab_cnt - len(hdr_data_str) - len(name_str)
            hdr_data_str += name_str + ljust_with_tabs(";", hdr_padding_len) + desc_str
        else:
            src_data_str += val_str + ";"
            hdr_data_str += name_str + ";"

    return (src_data_str, hdr_data_str)


@boundscheck(False)
@wraparound(False)
def fast_array_processing(list temp_arr, int row, int max_col, bint enable_float_suffix):
    """
    배열 처리 최적화
    """
    cdef str src_data_str = "\t"
    cdef str cell_str
    cdef int col
    cdef list temp_arr_row
    
    if row >= len(temp_arr) or not temp_arr[row]:
        return ""
    
    temp_arr_row = temp_arr[row]
    for col in range(min(max_col, len(temp_arr_row))):
        cell_str = str(temp_arr_row[col]) if temp_arr_row[col] is not None else ""
        
        # Float suffix 적용 (조건부)
        if enable_float_suffix and cell_str and not ('/*' in cell_str or '//' in cell_str):
            cell_str = apply_simple_float_suffix(cell_str)
        
        if col == max_col - 1:
            src_data_str += cell_str
        else:
            src_data_str += cell_str + ", "
    
    return src_data_str


# ========================================
# Float Suffix 최적화 함수들 (04_Python_Migration에서 이식)
# ========================================

@boundscheck(False)
@wraparound(False)
def fast_add_float_suffix(str block_str):
    """
    FLOAT32 블록에 Float Suffix 적용 (간단한 버전)
    """
    if not block_str:
        return block_str

    # Python 정규식을 사용한 안전한 처리
    import re

    # 주석 보호
    if '/*' in block_str or '//' in block_str:
        return block_str

    # 단어별로 분리해서 처리 (정규식 중복 적용 방지)
    words = re.split(r'(\s+|[^\w\.])', block_str)
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

    block_str = ''.join(result_words)

    return block_str



@boundscheck(True)
@wraparound(True)
def safe_apply_float_suffix_simple(str cell_str):
    """
    간단한 셀 값에 대한 안전한 Float Suffix 적용
    04_Python_Migration에서 이식
    """
    if not cell_str:
        return cell_str

    # 이미 f 또는 F 접미사가 있는지 확인
    if cell_str.endswith('f') or cell_str.endswith('F'):
        return cell_str

    # 간단한 숫자 패턴만 처리 (안전성 우선)
    import re

    # 소수점이 있는 숫자
    if re.match(r'^\d+\.\d*$', cell_str) or re.match(r'^\.\d+$', cell_str):
        return cell_str + 'f'

    # 소수점만 있는 숫자
    if re.match(r'^\d+\.$', cell_str):
        return cell_str + 'f'

    # 정수 (0 포함)
    if re.match(r'^\d+$', cell_str):
        if cell_str == '0':
            return '0.f'
        else:
            return cell_str + '.f'

    # 음수 처리
    if re.match(r'^-\d+\.\d*$', cell_str) or re.match(r'^-\.\d+$', cell_str):
        return cell_str + 'f'

    if re.match(r'^-\d+\.$', cell_str):
        return cell_str + 'f'

    if re.match(r'^-\d+$', cell_str):
        return cell_str + '.f'

    # 패턴에 맞지 않으면 원본 반환
    return cell_str

# ========================================
# 추가 성능 최적화 함수들 (누락된 병목 지점들)
# ========================================

@boundscheck(False)
@wraparound(False)
def fast_read_arr_mem_processing(list sht_data, int start_row, int start_col, int end_row, int end_col, str reading_rule):
    """
    readArrMem 메서드의 핵심 반복문 최적화
    배열 멤버 읽기 성능 최적화
    """
    cdef int row, col
    cdef str cell_str
    cdef list temp_line = []
    cdef list alignment_sizes = []
    cdef int cell_length

    if not sht_data or start_row < 0 or start_row >= len(sht_data):
        return temp_line, alignment_sizes

    for row in range(start_row, min(end_row + 1, len(sht_data))):
        row_data = sht_data[row] if row < len(sht_data) else None
        if not row_data:
            continue

        for col in range(start_col, min(end_col + 1, len(row_data))):
            # 셀 데이터 읽기
            if col < len(row_data):
                cell_str = str(row_data[col]) if row_data[col] is not None else ""
            else:
                cell_str = ""

            # 읽기 규칙 제거
            if reading_rule and reading_rule in cell_str:
                cell_str = cell_str.replace(reading_rule, "")

            temp_line.append(cell_str)

            # 문자열 길이 계산
            cell_length = len(cell_str.encode('utf-8'))
            alignment_sizes.append(cell_length)

    return temp_line, alignment_sizes


@boundscheck(False)
@wraparound(False)
def fast_write_arr_mem_processing(list temp_arr, list alignment_size, list annotate_row, list annotate_col,
                                 int row, int max_col, int arr_type, int tab_size, bint enable_float_suffix=True):
    """
    writeArrMem 메서드의 핵심 코드 생성 최적화
    배열 코드 생성 성능 최적화 (Float Suffix 지원 추가)
    """
    cdef str src_data_str = ""
    cdef str cell_str
    cdef str empty_or_comma
    cdef int col, antt_cnt = 0
    cdef int padding
    cdef bint is_annotate_row
    cdef bint is_annotate_col
    cdef bint next_col_in_annotate

    # 범위 검사
    if row >= len(temp_arr) or not temp_arr[row]:
        return ""

    # 주석 행 여부 확인 (set 변환으로 O(1) 검색)
    annotate_row_set = set(annotate_row)
    annotate_col_set = set(annotate_col)
    is_annotate_row = row in annotate_row_set

    # 시작 문자열 설정
    if is_annotate_row:
        src_data_str = "/*\t"
    else:
        src_data_str = "\t"

    # 최대 컬럼 수 계산
    if max_col <= 0:
        max_col = len(temp_arr[row]) if temp_arr[row] else 0

    # 열 처리
    temp_arr_row = temp_arr[row]
    for col in range(min(max_col, len(temp_arr_row))):
        cell_str = str(temp_arr_row[col]) if temp_arr_row[col] is not None else ""

        # Float suffix 적용 (조건부) - 주석 행/열 및 주석이 포함된 셀은 제외
        is_comment_context = (row in annotate_row_set or col in annotate_col_set or
                            '/*' in cell_str or '//' in cell_str)
        if enable_float_suffix and cell_str and not is_comment_context:
            cell_str = safe_apply_float_suffix_simple(cell_str)

        is_annotate_col = col in annotate_col_set

        # 다음 열이 주석 열인지 확인
        next_col_in_annotate = (col + 1) in annotate_col_set

        # 쉼표 또는 빈 문자열 결정
        if col == max_col - 1:
            empty_or_comma = ""
        elif next_col_in_annotate:
            empty_or_comma = ""
        else:
            empty_or_comma = ","

        # 주석 열 처리
        if is_annotate_col:
            if antt_cnt == 0:
                src_data_str += cell_str
                antt_cnt += 1
            else:
                src_data_str += cell_str + empty_or_comma
        else:
            # 정렬 처리
            if col < len(alignment_size) and alignment_size[col] > 0:
                padding = alignment_size[col] - len(cell_str.encode('utf-8'))
                if padding > 0:
                    cell_str += " " * padding

            src_data_str += cell_str + empty_or_comma

    # 주석 행 마무리
    if is_annotate_row:
        src_data_str += "\t*/"

    return src_data_str


@boundscheck(False)
@wraparound(False)
def fast_chk_cal_list_processing(str name_str, str val_str, str type_str, str key_str, str desc_str):
    """
    chkCalList 메서드의 검증 로직 최적화
    아이템 오류 체크 성능 최적화
    """
    cdef list errors = []
    cdef str error_msg

    # 빠른 검증 로직
    if not name_str or not name_str.strip():
        errors.append("Name is empty")

    if type_str and "FLOAT32" in type_str and val_str:
        # Float 타입 검증
        if not val_str.replace('.', '').replace('-', '').replace('f', '').replace('F', '').isdigit():
            if not ('/*' in val_str or '//' in val_str):  # 주석이 없는 경우만
                errors.append("Invalid FLOAT32 value")

    return errors


@boundscheck(False)
@wraparound(False)
def fast_save_temp_list_processing(str op_code_str, str key_str, str type_str, str name_str, str val_str, str desc_str):
    """
    saveTempList 메서드의 임시 저장 로직 최적화
    """
    cdef list temp_item = [op_code_str, key_str, type_str, name_str, val_str, desc_str]
    return temp_item
