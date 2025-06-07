# data_processor.pyx
# cython: language_level=3
# cython: boundscheck=False
# cython: wraparound=False
# cython: cdivision=True

import cython
from cython import boundscheck, wraparound

@boundscheck(False)
@wraparound(False)
def fast_db_batch_processing(list cells_data):
    """
    DB 배치 처리 최적화
    db_handler_v2.py의 batch_insert_cells 최적화
    """
    cdef int i, length
    cdef list processed_data = []
    cdef tuple cell_tuple
    cdef int row, col
    cdef str value
    
    if not cells_data:
        return processed_data
    
    length = len(cells_data)
    for i in range(length):
        cell_tuple = cells_data[i]
        row = cell_tuple[0]
        col = cell_tuple[1]
        value = str(cell_tuple[2]) if cell_tuple[2] is not None else ""
        
        # 빈 값 제외 (성능 최적화)
        if value and value.strip():
            processed_data.append((row, col, value))
    
    return processed_data


@boundscheck(False)
@wraparound(False)
def fast_sheet_data_loading(list raw_data, int max_row, int max_col):
    """
    시트 데이터 로딩 최적화
    db_handler_v2.py의 get_sheet_data 최적화
    """
    cdef int i, j
    cdef list sheet_data = []
    cdef list row_data
    cdef dict cell
    cdef int row, col
    cdef str value
    
    # 메모리 사전 할당
    for i in range(max_row + 1):
        row_data = [None] * (max_col + 1)
        sheet_data.append(row_data)
    
    # 데이터 채우기
    for i in range(len(raw_data)):
        cell = raw_data[i]
        row = cell['row']
        col = cell['col']
        value = cell['value']
        
        if 0 <= row <= max_row and 0 <= col <= max_col:
            sheet_data[row][col] = value
    
    return sheet_data


@boundscheck(False)
@wraparound(False)
def fast_cell_cache_management(dict cache, int max_size):
    """
    셀 캐시 관리 최적화
    cal_list.py의 cached_read_cell 최적화
    """
    cdef int current_size, remove_count, i
    cdef list keys_to_remove
    
    current_size = len(cache)
    
    if current_size >= max_size:
        remove_count = max_size // 3  # 1/3 제거
        keys_to_remove = list(cache.keys())[:remove_count]
        
        for i in range(remove_count):
            del cache[keys_to_remove[i]]
    
    return len(cache)


@boundscheck(False)
@wraparound(False)
def fast_data_type_conversion(list data_list, str target_type):
    """
    데이터 타입 변환 최적화
    """
    cdef int i, length
    cdef list converted_data = []
    cdef object item
    cdef str str_item
    cdef int int_item
    cdef double float_item
    
    if not data_list:
        return converted_data
    
    length = len(data_list)
    
    if target_type == "string":
        for i in range(length):
            item = data_list[i]
            if item is None:
                converted_data.append("")
            else:
                converted_data.append(str(item))
    
    elif target_type == "integer":
        for i in range(length):
            item = data_list[i]
            if item is None:
                converted_data.append(0)
            elif isinstance(item, int):
                converted_data.append(item)
            elif isinstance(item, float):
                converted_data.append(int(item))
            elif isinstance(item, str):
                try:
                    int_item = int(float(item))
                    converted_data.append(int_item)
                except:
                    converted_data.append(0)
            else:
                converted_data.append(0)
    
    elif target_type == "float":
        for i in range(length):
            item = data_list[i]
            if item is None:
                converted_data.append(0.0)
            elif isinstance(item, (int, float)):
                converted_data.append(float(item))
            elif isinstance(item, str):
                try:
                    float_item = float(item)
                    converted_data.append(float_item)
                except:
                    converted_data.append(0.0)
            else:
                converted_data.append(0.0)
    
    return converted_data


@boundscheck(False)
@wraparound(False)
def fast_matrix_operations(list matrix_a, list matrix_b, str operation):
    """
    행렬 연산 최적화
    """
    cdef int i, j, rows_a, cols_a, rows_b, cols_b
    cdef list result = []
    cdef list row_result
    cdef double val_a, val_b
    
    if not matrix_a or not matrix_b:
        return result
    
    rows_a = len(matrix_a)
    cols_a = len(matrix_a[0]) if rows_a > 0 else 0
    rows_b = len(matrix_b)
    cols_b = len(matrix_b[0]) if rows_b > 0 else 0
    
    if operation == "add" and rows_a == rows_b and cols_a == cols_b:
        for i in range(rows_a):
            row_result = []
            for j in range(cols_a):
                val_a = float(matrix_a[i][j]) if matrix_a[i][j] is not None else 0.0
                val_b = float(matrix_b[i][j]) if matrix_b[i][j] is not None else 0.0
                row_result.append(val_a + val_b)
            result.append(row_result)
    
    elif operation == "subtract" and rows_a == rows_b and cols_a == cols_b:
        for i in range(rows_a):
            row_result = []
            for j in range(cols_a):
                val_a = float(matrix_a[i][j]) if matrix_a[i][j] is not None else 0.0
                val_b = float(matrix_b[i][j]) if matrix_b[i][j] is not None else 0.0
                row_result.append(val_a - val_b)
            result.append(row_result)
    
    return result


@boundscheck(False)
@wraparound(False)
def fast_data_filtering(list data_list, str filter_type, object filter_value):
    """
    데이터 필터링 최적화
    """
    cdef int i, length
    cdef list filtered_data = []
    cdef object item
    cdef str str_item, str_filter
    cdef double num_item, num_filter
    
    if not data_list:
        return filtered_data
    
    length = len(data_list)
    
    if filter_type == "not_null":
        for i in range(length):
            item = data_list[i]
            if item is not None:
                filtered_data.append(item)
    
    elif filter_type == "not_empty":
        for i in range(length):
            item = data_list[i]
            if item is not None:
                str_item = str(item)
                if str_item.strip():
                    filtered_data.append(item)
    
    elif filter_type == "equals":
        for i in range(length):
            item = data_list[i]
            if item == filter_value:
                filtered_data.append(item)
    
    elif filter_type == "contains":
        str_filter = str(filter_value)
        for i in range(length):
            item = data_list[i]
            if item is not None:
                str_item = str(item)
                if str_filter in str_item:
                    filtered_data.append(item)
    
    elif filter_type == "greater_than":
        num_filter = float(filter_value)
        for i in range(length):
            item = data_list[i]
            if isinstance(item, (int, float)):
                num_item = float(item)
                if num_item > num_filter:
                    filtered_data.append(item)
    
    elif filter_type == "less_than":
        num_filter = float(filter_value)
        for i in range(length):
            item = data_list[i]
            if isinstance(item, (int, float)):
                num_item = float(item)
                if num_item < num_filter:
                    filtered_data.append(item)
    
    return filtered_data


@boundscheck(False)
@wraparound(False)
def fast_data_sorting(list data_list, str sort_key, bint reverse):
    """
    데이터 정렬 최적화
    """
    cdef int i, j, length
    cdef list sorted_data = data_list.copy()
    cdef object temp, item_i, item_j
    cdef str str_i, str_j
    cdef double num_i, num_j
    cdef bint should_swap
    
    if not data_list:
        return sorted_data
    
    length = len(sorted_data)
    
    # 버블 정렬 (단순하지만 Cython에서 빠름)
    for i in range(length - 1):
        for j in range(length - 1 - i):
            item_i = sorted_data[j]
            item_j = sorted_data[j + 1]
            should_swap = False
            
            if sort_key == "string":
                str_i = str(item_i) if item_i is not None else ""
                str_j = str(item_j) if item_j is not None else ""
                should_swap = (str_i > str_j) if not reverse else (str_i < str_j)
            
            elif sort_key == "numeric":
                try:
                    num_i = float(item_i) if item_i is not None else 0.0
                    num_j = float(item_j) if item_j is not None else 0.0
                    should_swap = (num_i > num_j) if not reverse else (num_i < num_j)
                except:
                    should_swap = False
            
            if should_swap:
                temp = sorted_data[j]
                sorted_data[j] = sorted_data[j + 1]
                sorted_data[j + 1] = temp
    
    return sorted_data


@boundscheck(False)
@wraparound(False)
def fast_data_grouping(list data_list, str group_key):
    """
    데이터 그룹화 최적화
    """
    cdef int i, length
    cdef dict groups = {}
    cdef object item, key_value
    cdef str str_key
    cdef list group_list
    
    if not data_list:
        return groups
    
    length = len(data_list)
    
    for i in range(length):
        item = data_list[i]
        
        if group_key == "type":
            key_value = type(item).__name__
        elif group_key == "length":
            key_value = len(str(item)) if item is not None else 0
        elif group_key == "first_char":
            str_key = str(item) if item is not None else ""
            key_value = str_key[0] if str_key else ""
        else:
            key_value = str(item) if item is not None else ""
        
        if key_value not in groups:
            groups[key_value] = []
        groups[key_value].append(item)
    
    return groups


@boundscheck(False)
@wraparound(False)
def fast_memory_pool_management(list pool, int pool_size, int item_size):
    """
    메모리 풀 관리 최적화
    """
    cdef int i, current_size, target_size
    cdef list new_items
    
    current_size = len(pool)
    target_size = pool_size
    
    if current_size < target_size:
        # 풀 확장
        for i in range(target_size - current_size):
            new_items = [None] * item_size
            pool.append(new_items)
    elif current_size > target_size:
        # 풀 축소
        del pool[target_size:]
    
    return len(pool)


@boundscheck(False)
@wraparound(False)
def fast_hash_calculation(list data_list):
    """
    해시 계산 최적화
    """
    cdef int i, length, hash_value = 0
    cdef str str_item
    cdef object item
    
    if not data_list:
        return 0
    
    length = len(data_list)
    
    for i in range(length):
        item = data_list[i]
        if item is not None:
            str_item = str(item)
            hash_value = (hash_value * 31 + hash(str_item)) & 0x7FFFFFFF
    
    return hash_value


@boundscheck(False)
@wraparound(False)
def fast_data_compression(list data_list):
    """
    데이터 압축 최적화 (중복 제거 및 참조 압축)
    """
    cdef int i, length
    cdef dict value_map = {}
    cdef list compressed_data = []
    cdef object item
    cdef int value_id = 0
    
    if not data_list:
        return compressed_data, value_map
    
    length = len(data_list)
    
    for i in range(length):
        item = data_list[i]
        
        if item not in value_map:
            value_map[item] = value_id
            value_id += 1
        
        compressed_data.append(value_map[item])
    
    return compressed_data, value_map


# ========================================
# 추가 성능 최적화 함수들 (누락된 병목 지점들)
# ========================================

@boundscheck(False)
@wraparound(False)
def fast_regex_pattern_matching(str text, str pattern_type):
    """
    정규식 패턴 매칭 최적화
    add_float_suffix에서 사용되는 정규식 처리 최적화
    """
    cdef int i, length
    cdef char c
    cdef bint has_dot = False
    cdef bint is_number = True
    cdef bint has_comment = False

    if not text:
        return False

    length = len(text)

    # 주석 검사 (빠른 검사)
    if '/*' in text or '//' in text:
        has_comment = True

    if pattern_type == "simple_number":
        # 간단한 숫자 패턴 검사
        for i in range(length):
            c = text[i]
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

        return is_number and not has_comment

    elif pattern_type == "float_literal":
        # Float 리터럴 패턴 검사
        return has_dot and is_number and not has_comment

    elif pattern_type == "integer_literal":
        # 정수 리터럴 패턴 검사
        return not has_dot and is_number and not has_comment

    return False


@boundscheck(False)
@wraparound(False)
def fast_string_split_processing(str text, str delimiter, int max_splits):
    """
    문자열 분할 최적화
    대량 문자열 분할 작업 최적화
    """
    cdef list result = []
    cdef int start = 0
    cdef int pos = 0
    cdef int splits = 0
    cdef int text_len = len(text)
    cdef int delim_len = len(delimiter)

    if not text or not delimiter:
        return [text] if text else []

    while pos <= text_len - delim_len and splits < max_splits:
        if text[pos:pos + delim_len] == delimiter:
            result.append(text[start:pos])
            start = pos + delim_len
            pos = start
            splits += 1
        else:
            pos += 1

    # 마지막 부분 추가
    if start < text_len:
        result.append(text[start:])

    return result


@boundscheck(False)
@wraparound(False)
def fast_list_comprehension_replacement(list input_list, str operation, object filter_value):
    """
    리스트 컴프리헨션 대체 최적화
    대량 리스트 처리 작업 최적화
    """
    cdef int i, length
    cdef list result = []
    cdef object item
    cdef str str_item

    if not input_list:
        return result

    length = len(input_list)

    if operation == "filter_non_empty":
        for i in range(length):
            item = input_list[i]
            if item is not None:
                str_item = str(item)
                if str_item.strip():
                    result.append(item)

    elif operation == "map_to_string":
        for i in range(length):
            item = input_list[i]
            if item is not None:
                result.append(str(item))
            else:
                result.append("")

    elif operation == "filter_by_type":
        for i in range(length):
            item = input_list[i]
            if isinstance(item, type(filter_value)):
                result.append(item)

    elif operation == "strip_strings":
        for i in range(length):
            item = input_list[i]
            if isinstance(item, str):
                result.append(item.strip())
            else:
                result.append(item)

    return result


@boundscheck(False)
@wraparound(False)
def fast_nested_loop_optimization(list outer_list, list inner_list, str operation):
    """
    중첩 루프 최적화
    이중/삼중 반복문 성능 최적화
    """
    cdef int i, j, outer_len, inner_len
    cdef list result = []
    cdef object outer_item, inner_item
    cdef tuple pair

    if not outer_list or not inner_list:
        return result

    outer_len = len(outer_list)
    inner_len = len(inner_list)

    if operation == "cartesian_product":
        for i in range(outer_len):
            outer_item = outer_list[i]
            for j in range(inner_len):
                inner_item = inner_list[j]
                pair = (outer_item, inner_item)
                result.append(pair)

    elif operation == "find_matches":
        for i in range(outer_len):
            outer_item = outer_list[i]
            for j in range(inner_len):
                inner_item = inner_list[j]
                if outer_item == inner_item:
                    result.append(outer_item)
                    break  # 첫 번째 매치만

    return result
