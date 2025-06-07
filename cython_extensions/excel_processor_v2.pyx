# excel_processor_v2.pyx
# cython: language_level=3
# cython: boundscheck=False
# cython: wraparound=False
# cython: cdivision=True

import cython
from cython import boundscheck, wraparound

@boundscheck(False)
@wraparound(False)
def fast_process_excel_data(values):
    """
    엑셀 데이터를 빠르게 처리하는 Cython 함수
    excel_importer.py의 이중 반복문 최적화
    """
    cdef int i, j, rows, cols
    cdef list cells_data = []
    cdef object val, row
    cdef str value_str
    
    if values is None:
        return cells_data
    
    if not isinstance(values, (list, tuple)):
        # 단일 값인 경우
        value_str = process_cell_value_fast(values)
        cells_data.append((0, 0, value_str))
        return cells_data
    
    # 크기 계산
    rows = len(values)
    if rows == 0:
        return cells_data
    
    # 2차원 데이터 처리
    for i in range(rows):
        row = values[i]
        if isinstance(row, (list, tuple)):
            cols = len(row)
            for j in range(cols):
                val = row[j]
                if val is not None:
                    value_str = process_cell_value_fast(val)
                    cells_data.append((i, j, value_str))
        elif row is not None:
            # 1차원 데이터인 경우
            value_str = process_cell_value_fast(row)
            cells_data.append((0, i, value_str))
    
    return cells_data


@boundscheck(False)
@wraparound(False)
def process_cell_value_fast(cell_value):
    """
    셀 값을 빠르게 처리하여 적절한 형태로 변환 (Cython 최적화)
    excel_importer.py의 process_cell_value 메서드 최적화
    """
    cdef str result
    cdef double float_val
    cdef int int_val
    
    if cell_value is None:
        return ""
    
    # 숫자 타입 최적화 처리
    if isinstance(cell_value, int):
        return str(cell_value)
    elif isinstance(cell_value, float):
        # 정수로 표현 가능한지 빠르게 확인
        int_val = <int>cell_value
        if cell_value == int_val:
            return str(int_val)
        else:
            result = str(cell_value)
            # .0 제거 최적화
            if result.endswith('.0'):
                return result[:-2]
            return result
    elif isinstance(cell_value, str):
        return cell_value
    else:
        return str(cell_value)


@boundscheck(False)
@wraparound(False)
def fast_batch_cell_processing(list cells_data):
    """
    대량 셀 데이터 배치 처리 최적화
    """
    cdef int i, length
    cdef list processed_data = []
    cdef tuple cell_tuple
    cdef int row, col
    cdef str value, processed_value
    
    if not cells_data:
        return processed_data
    
    length = len(cells_data)
    for i in range(length):
        cell_tuple = cells_data[i]
        row = cell_tuple[0]
        col = cell_tuple[1]
        value = cell_tuple[2]
        
        # 빈 값 제외 (성능 최적화)
        if value and value.strip():
            processed_data.append((row, col, value))
    
    return processed_data


@boundscheck(False)
@wraparound(False)
def fast_sheet_data_conversion(list sheet_data):
    """
    시트 데이터 변환 최적화
    data_parser.py의 변환 로직 최적화
    """
    cdef int i, j, rows, cols
    cdef list converted_data = []
    cdef list row_data, converted_row
    cdef object cell_value
    cdef str cell_str
    
    if not sheet_data:
        return converted_data
    
    rows = len(sheet_data)
    for i in range(rows):
        row_data = sheet_data[i]
        if row_data is None:
            converted_data.append([])
            continue
        
        cols = len(row_data) if isinstance(row_data, list) else 0
        converted_row = []
        
        for j in range(cols):
            cell_value = row_data[j]
            if cell_value is not None:
                cell_str = str(cell_value)
            else:
                cell_str = ""
            converted_row.append(cell_str)
        
        converted_data.append(converted_row)
    
    return converted_data


@boundscheck(False)
@wraparound(False)
def fast_memory_optimization(int rows, int cols):
    """
    메모리 할당 최적화 함수
    대용량 데이터 처리를 위한 사전 할당
    """
    cdef int i, j
    cdef list data_matrix = []
    cdef list row_data
    
    for i in range(rows):
        row_data = [None] * cols
        data_matrix.append(row_data)
    
    return data_matrix


@boundscheck(False)
@wraparound(False)
def fast_string_join_optimization(list string_list, str separator):
    """
    문자열 조인 최적화
    """
    cdef int i, length
    cdef list filtered_list = []
    cdef str item
    
    if not string_list:
        return ""
    
    length = len(string_list)
    for i in range(length):
        item = string_list[i]
        if item and item.strip():
            filtered_list.append(item)
    
    return separator.join(filtered_list)


@boundscheck(False)
@wraparound(False)
def fast_data_validation(list data_list):
    """
    데이터 유효성 검사 최적화
    """
    cdef int i, length, valid_count = 0
    cdef object item
    cdef list valid_data = []
    
    if not data_list:
        return valid_data, 0
    
    length = len(data_list)
    for i in range(length):
        item = data_list[i]
        if item is not None:
            if isinstance(item, str):
                if item.strip():
                    valid_data.append(item)
                    valid_count += 1
            else:
                valid_data.append(item)
                valid_count += 1
    
    return valid_data, valid_count


@boundscheck(False)
@wraparound(False)
def fast_cell_range_processing(list sheet_data, int start_row, int end_row, int start_col, int end_col):
    """
    셀 범위 처리 최적화
    특정 범위의 셀들을 빠르게 처리
    """
    cdef int row, col
    cdef list result = []
    cdef list row_data
    cdef object cell_value
    cdef str cell_str
    
    if not sheet_data:
        return result
    
    for row in range(start_row, min(end_row + 1, len(sheet_data))):
        row_data = sheet_data[row]
        if row_data is None:
            continue
        
        for col in range(start_col, min(end_col + 1, len(row_data))):
            cell_value = row_data[col]
            if cell_value is not None:
                cell_str = str(cell_value)
                if cell_str.strip():
                    result.append((row, col, cell_str))
    
    return result


@boundscheck(False)
@wraparound(False)
def fast_duplicate_removal(list data_list):
    """
    중복 제거 최적화
    """
    cdef int i, length
    cdef set seen = set()
    cdef list unique_data = []
    cdef object item
    
    if not data_list:
        return unique_data
    
    length = len(data_list)
    for i in range(length):
        item = data_list[i]
        if item not in seen:
            seen.add(item)
            unique_data.append(item)
    
    return unique_data


@boundscheck(False)
@wraparound(False)
def fast_data_aggregation(list data_list, str operation):
    """
    데이터 집계 최적화
    """
    cdef int i, length, count = 0
    cdef double sum_val = 0.0, min_val = float('inf'), max_val = float('-inf')
    cdef object item
    cdef double num_val
    
    if not data_list:
        return None
    
    length = len(data_list)
    
    if operation == "count":
        return length
    
    for i in range(length):
        item = data_list[i]
        if isinstance(item, (int, float)):
            num_val = <double>item
            count += 1
            sum_val += num_val
            if num_val < min_val:
                min_val = num_val
            if num_val > max_val:
                max_val = num_val
    
    if count == 0:
        return None
    
    if operation == "sum":
        return sum_val
    elif operation == "avg":
        return sum_val / count
    elif operation == "min":
        return min_val
    elif operation == "max":
        return max_val
    else:
        return None


@boundscheck(False)
@wraparound(False)
def fast_text_processing(str text, str operation):
    """
    텍스트 처리 최적화
    """
    cdef str result = text
    
    if not text:
        return ""
    
    if operation == "trim":
        result = text.strip()
    elif operation == "upper":
        result = text.upper()
    elif operation == "lower":
        result = text.lower()
    elif operation == "remove_spaces":
        result = text.replace(" ", "")
    elif operation == "normalize":
        result = text.strip().replace("\r\n", "\n").replace("\r", "\n")
    
    return result
