# regex_optimizer.pyx
# cython: language_level=3
# cython: boundscheck=False
# cython: wraparound=False
# cython: cdivision=True

import cython
from cython import boundscheck, wraparound

@boundscheck(False)
@wraparound(False)
def fast_float_suffix_regex_replacement(str val_str):
    """
    Float Suffix 정규식 처리 최적화 (안전한 버전)
    cal_list.py의 add_float_suffix에서 사용되는 복잡한 정규식 대체
    """
    # 입력 검증
    if not val_str or not isinstance(val_str, str):
        return str(val_str) if val_str is not None else ""

    # 간단한 케이스 먼저 처리 (성능 최적화)
    if not val_str.strip():
        return val_str

    # 이미 접미사가 있는 경우
    if val_str.endswith(('f', 'F')):
        return val_str

    # 주석이 포함된 경우 복잡한 처리 필요
    if '/*' in val_str or '//' in val_str:
        return process_complex_float_suffix_safe(val_str)

    # 단순한 숫자에만 접미사 적용
    return apply_simple_float_suffix_safe(val_str)


@boundscheck(False)
@wraparound(False)
def apply_simple_float_suffix_safe(str val_str):
    """
    단순한 숫자에 Float Suffix 적용 (안전한 버전)
    """
    cdef int i, length
    cdef bint has_dot = False
    cdef bint is_number = True
    cdef str c

    if not val_str:
        return val_str

    length = len(val_str)
    if length == 0:
        return val_str

    # 숫자인지 확인 (안전한 문자열 처리)
    for i in range(length):
        c = val_str[i]  # 문자열 인덱싱으로 안전하게 처리
        
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
def process_complex_float_suffix_safe(str val_str):
    """
    복잡한 문자열의 Float Suffix 처리 (주석 포함) - 안전한 버전
    """
    # 복잡한 경우는 Python 정규식 사용 (안전성 우선)
    import re

    try:
        # 주석 보존을 위한 임시 치환
        comments = {}
        comment_count = 0
        modified_val = val_str

        # 블록 주석 처리
        block_comment_pattern = re.compile(r'/\*.*?\*/', re.DOTALL)
        block_comments = list(block_comment_pattern.finditer(modified_val))
        for comment in block_comments:
            placeholder = f"__COMMENT_BLOCK_{comment_count}__"
            comments[placeholder] = comment.group(0)
            modified_val = modified_val.replace(comment.group(0), placeholder)
            comment_count += 1

        # 라인 주석 처리
        line_comment_pattern = re.compile(r'//.*?(?=\n|$)')
        line_comments = list(line_comment_pattern.finditer(modified_val))
        for comment in line_comments:
            placeholder = f"__COMMENT_LINE_{comment_count}__"
            comments[placeholder] = comment.group(0)
            modified_val = modified_val.replace(comment.group(0), placeholder)
            comment_count += 1

        # 주석이 제거된 부분에만 Float Suffix 적용
        modified_val = apply_simple_float_suffix_safe(modified_val)

        # 주석 복원
        for placeholder, comment in comments.items():
            modified_val = modified_val.replace(placeholder, comment)

        return modified_val
    except Exception:
        # 오류 발생 시 원본 반환
        return val_str


@boundscheck(False)
@wraparound(False)
def fast_comment_preservation(str text):
    """
    주석 보존 최적화
    복잡한 주석 구조를 빠르게 파싱
    """
    cdef int i, length
    cdef char c
    cdef list segments = []
    cdef str current_segment = ""
    cdef bint in_block_comment = False
    cdef bint in_line_comment = False
    cdef str segment_type = "code"
    
    if not text:
        return []
    
    length = len(text)
    
    for i in range(length):
        c = text[i]  # 문자열 인덱싱으로 안전하게 처리
        
        if not in_block_comment and not in_line_comment:
            if i < length - 1 and c == '/' and text[i + 1] == '*':
                # 블록 주석 시작
                if current_segment:
                    segments.append((segment_type, current_segment))
                current_segment = "/*"
                in_block_comment = True
                segment_type = "block_comment"
                i += 1
                continue
            elif i < length - 1 and c == '/' and text[i + 1] == '/':
                # 라인 주석 시작
                if current_segment:
                    segments.append((segment_type, current_segment))
                current_segment = "//"
                in_line_comment = True
                segment_type = "line_comment"
                i += 1
                continue
        
        if in_block_comment and i > 0 and text[i-1] == '*' and c == '/':
            # 블록 주석 종료
            current_segment += c
            segments.append((segment_type, current_segment))
            current_segment = ""
            in_block_comment = False
            segment_type = "code"
            continue
        
        if in_line_comment and c == '\n':
            # 라인 주석 종료
            current_segment += c
            segments.append((segment_type, current_segment))
            current_segment = ""
            in_line_comment = False
            segment_type = "code"
            continue
        
        current_segment += c
    
    # 마지막 세그먼트 추가
    if current_segment:
        segments.append((segment_type, current_segment))
    
    return segments


@boundscheck(False)
@wraparound(False)
def fast_number_pattern_detection(str text):
    """
    숫자 패턴 빠른 감지
    정규식 없이 숫자 패턴을 빠르게 찾기
    """
    cdef int i, length
    cdef char c
    cdef list numbers = []
    cdef str current_number = ""
    cdef bint in_number = False
    cdef bint has_dot = False
    cdef int start_pos = 0
    
    if not text:
        return numbers
    
    length = len(text)
    
    for i in range(length):
        c = text[i]
        
        if (c >= '0' and c <= '9') or (c == '.' and not has_dot) or (c == '-' and not in_number):
            if not in_number:
                in_number = True
                start_pos = i
                has_dot = False

            current_number += c
            if c == '.':
                has_dot = True
        else:
            if in_number and current_number:
                # 숫자 완료
                numbers.append({
                    'value': current_number,
                    'start': start_pos,
                    'end': i - 1,
                    'has_dot': has_dot
                })
                current_number = ""
                in_number = False
                has_dot = False
    
    # 마지막 숫자 처리
    if in_number and current_number:
        numbers.append({
            'value': current_number,
            'start': start_pos,
            'end': length - 1,
            'has_dot': has_dot
        })
    
    return numbers


@boundscheck(False)
@wraparound(False)
def fast_array_pattern_detection(str text):
    """
    배열 패턴 빠른 감지
    {}, [] 패턴을 빠르게 찾기
    """
    cdef int i, length, brace_level = 0, bracket_level = 0
    cdef char c
    cdef list arrays = []
    cdef str current_array = ""
    cdef bint in_array = False
    cdef int start_pos = 0
    cdef str array_type = ""
    
    if not text:
        return arrays
    
    length = len(text)
    
    for i in range(length):
        c = text[i]
        
        if c == '{':
            if not in_array:
                in_array = True
                start_pos = i
                array_type = "brace"
            brace_level += 1
            current_array += c
        elif c == '}':
            brace_level -= 1
            current_array += c
            if brace_level == 0 and in_array and array_type == "brace":
                arrays.append({
                    'content': current_array,
                    'start': start_pos,
                    'end': i,
                    'type': 'brace'
                })
                current_array = ""
                in_array = False
        elif c == '[':
            if not in_array:
                in_array = True
                start_pos = i
                array_type = "bracket"
            bracket_level += 1
            current_array += c
        elif c == ']':
            bracket_level -= 1
            current_array += c
            if bracket_level == 0 and in_array and array_type == "bracket":
                arrays.append({
                    'content': current_array,
                    'start': start_pos,
                    'end': i,
                    'type': 'bracket'
                })
                current_array = ""
                in_array = False
        elif in_array:
            current_array += c
    
    return arrays


@boundscheck(False)
@wraparound(False)
def fast_string_literal_detection(str text):
    """
    문자열 리터럴 빠른 감지
    "", '' 패턴을 빠르게 찾기
    """
    cdef int i, length
    cdef char c, quote_char
    cdef list strings = []
    cdef str current_string = ""
    cdef bint in_string = False
    cdef bint escaped = False
    cdef int start_pos = 0
    
    if not text:
        return strings
    
    length = len(text)
    
    for i in range(length):
        c = text[i]
        
        if not in_string:
            if c == '"' or c == "'":
                in_string = True
                quote_char = c
                start_pos = i
                current_string = c
        else:
            current_string += c
            
            if escaped:
                escaped = False
            elif c == '\\':
                escaped = True
            elif c == quote_char:
                # 문자열 종료
                strings.append({
                    'content': current_string,
                    'start': start_pos,
                    'end': i,
                    'quote': quote_char
                })
                current_string = ""
                in_string = False
    
    return strings


@boundscheck(False)
@wraparound(False)
def fast_preprocessor_directive_detection(str text):
    """
    전처리기 지시문 빠른 감지
    #define, #include 등을 빠르게 찾기
    """
    cdef int i, length
    cdef char c
    cdef list directives = []
    cdef str current_directive = ""
    cdef bint in_directive = False
    cdef bint at_line_start = True
    cdef int start_pos = 0
    
    if not text:
        return directives
    
    length = len(text)
    
    for i in range(length):
        c = text[i]
        
        if at_line_start and c == '#':
            in_directive = True
            start_pos = i
            current_directive = c
            at_line_start = False
        elif in_directive:
            if c == '\n':
                # 지시문 종료
                directives.append({
                    'content': current_directive,
                    'start': start_pos,
                    'end': i - 1
                })
                current_directive = ""
                in_directive = False
                at_line_start = True
            else:
                current_directive += c
        else:
            if c == '\n':
                at_line_start = True
            elif c != ' ' and c != '\t':
                at_line_start = False
    
    # 마지막 지시문 처리
    if in_directive and current_directive:
        directives.append({
            'content': current_directive,
            'start': start_pos,
            'end': length - 1
        })
    
    return directives
