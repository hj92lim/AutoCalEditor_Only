# AutoCalEditor 네비게이터 통합 구현 계획서

## 📋 프로젝트 개요

AutoCalEditor의 기존 시스템에 **네비게이터 기능**을 **최소한의 코드 변경**으로 통합하여 사용자 경험을 향상시키는 프로젝트입니다.

## 🎯 핵심 설계 원칙

### 1. **기존 기능 무손상 (Zero Impact)**
- 기존 TreeView, ExcelGridView 기능에 전혀 영향 없음
- 기존 시그널/슬롯 연결 구조 그대로 유지
- 기존 DB 핸들러, 모델 구조 변경 없음

### 2. **최소 코드 변경 (Minimal Change)**
- 기존 `on_sheet_selected` 메서드에 네비게이터 업데이트 로직 1줄 추가
- 기존 왼쪽 패널에 스플리터로 네비게이터 영역 추가
- 새로운 클래스들은 완전히 독립적으로 구현

### 3. **기존 로직 최대 활용 (Reuse Existing)**
- 기존 DB 핸들러의 `get_sheet_data()` 메서드 활용
- 기존 OpCode 색상 시스템 확장
- 기존 시트 선택 이벤트 흐름 그대로 활용

## 🗂️ 기존 시스템 구조 분석

### 현재 UI 구조
```python
# main.py - init_ui() 메서드
left_panel = QWidget()
left_layout = QVBoxLayout(left_panel)
left_layout.addWidget(self.tree_view)  # 현재는 TreeView만 있음

# 시트 선택 이벤트 흐름
self.tree_view.sheet_selected.connect(self.on_sheet_selected)
→ on_sheet_selected(sheet_id, sheet_name)
→ self.grid_view.load_sheet(sheet_id)
```

### 기존 데이터 흐름
```
TreeView 클릭 → sheet_selected 시그널 → on_sheet_selected 슬롯 
→ grid_view.load_sheet() → DB에서 데이터 로드 → Excel 뷰어 업데이트
```

## 🏗️ 통합 구현 계획

### Phase 1: 네비게이터 컴포넌트 구현 (독립적)

#### 1.1 핵심 클래스 구현
```python
# navigator/navigator_core.py
class NavigatorParser:
    """네비게이터 파서 (SRP 준수)"""
    def parse_items(self, sheet_data: List[List[str]]) -> List[NavigatorItem]

class NavigatorWidget(QWidget):
    """네비게이터 위젯 (완전 독립적)"""
    item_clicked = Signal(int, int)  # row, col
    
class NavigatorItemDelegate(QStyledItemDelegate):
    """OpCode 색상 + 하이라이트 델리게이트"""
```

#### 1.2 상수 및 설정 중앙화
```python
# navigator/navigator_constants.py
OPCODE_COLORS = {...}      # OpCode별 색상 팔레트
OPCODE_MAPPING = {...}     # OpCode 문자열 → EMkMode 매핑
ICON_MAPPING = {...}       # OpCode → 아이콘 매핑
DISPLAY_OPCODES = {...}    # 표시할 OpCode 집합
```

### Phase 2: 기존 시스템 통합 (최소 변경)

#### 2.1 main.py 수정 (3줄 추가)
```python
# 기존 코드
left_layout.addWidget(self.tree_view)

# 수정 후
navigator_splitter = QSplitter(Qt.Vertical)
navigator_splitter.addWidget(self.tree_view)

from navigator.navigator_widget import NavigatorWidget
self.navigator = NavigatorWidget()
self.navigator.item_clicked.connect(self._on_navigator_clicked)
navigator_splitter.addWidget(self.navigator)
navigator_splitter.setSizes([400, 300])  # TreeView:Navigator = 4:3

left_layout.addWidget(navigator_splitter)
```

#### 2.2 on_sheet_selected 메서드 수정 (1줄 추가)
```python
def on_sheet_selected(self, sheet_id: int, sheet_name: str):
    # 기존 코드 그대로 유지
    self.current_sheet_id = sheet_id
    self.grid_view.load_sheet(sheet_id)
    self.sheet_label.setText(f"현재 시트: {sheet_name}")
    
    # 네비게이터 업데이트 (1줄 추가)
    self._update_navigator(sheet_id)
```

#### 2.3 네비게이터 클릭 처리 메서드 추가
```python
def _update_navigator(self, sheet_id: int):
    """네비게이터 업데이트 (기존 DB 핸들러 활용)"""
    sheet_data = self.db.get_sheet_data(sheet_id)
    self.navigator.populate_from_data(sheet_data)

def _on_navigator_clicked(self, row: int, col: int):
    """네비게이터 클릭 처리 (기존 그리드뷰 활용)"""
    # 기존 그리드뷰의 스크롤/하이라이트 기능 활용
    self.grid_view.scroll_to_cell(row, col)
    self.grid_view.highlight_cell(row, col)
```

### Phase 3: OpCode 색상 시스템 통합

#### 3.1 기존 델리게이트 확장
```python
# ui/ui_components.py - ExcelItemDelegate 클래스 수정
def paint(self, painter, option, index):
    # 기존 코드 유지
    super().paint(painter, option, index)
    
    # OpCode 색상 오버레이 추가
    opcode = self._get_opcode_for_cell(index)
    if opcode in OPCODE_COLORS:
        self._paint_opcode_background(painter, option.rect, opcode)
```

## 📁 파일 구조

```
navigator/
├── __init__.py
├── navigator_constants.py    # 상수 정의
├── navigator_core.py         # 핵심 파서 로직
├── navigator_widget.py       # UI 위젯
└── navigator_delegate.py     # 아이템 델리게이트

main.py                       # 3줄 수정
ui/ui_components.py          # 델리게이트 확장
```

## 🎯 구현 우선순위

### 1단계: 독립 컴포넌트 구현
- [ ] NavigatorParser 클래스 구현
- [ ] NavigatorWidget 클래스 구현  
- [ ] 상수 파일 정리

### 2단계: 기존 시스템 통합
- [ ] main.py 왼쪽 패널 스플리터 추가
- [ ] on_sheet_selected 메서드 1줄 추가
- [ ] 네비게이터 클릭 처리 메서드 추가

### 3단계: OpCode 색상 시스템
- [ ] 기존 델리게이트 확장
- [ ] 하이라이트 애니메이션 추가

## 🔍 핵심 장점

### 1. **기존 기능 완전 보존**
- TreeView 기능 그대로 유지
- Excel 뷰어 기능 그대로 유지
- DB 핸들러 로직 그대로 활용

### 2. **최소한의 코드 변경**
- main.py: 단 3줄 추가
- on_sheet_selected: 단 1줄 추가
- 새로운 기능은 완전히 독립적인 모듈로 구현

### 3. **확장성 보장**
- 새로운 OpCode 쉽게 추가 가능
- 네비게이터 기능 독립적 확장 가능
- 기존 시스템에 영향 없이 기능 추가/제거 가능

### 4. **성능 최적화**
- 기존 DB 쿼리 재사용
- 기존 가상화 시스템 활용
- 메모리 효율적인 파싱

## 🚀 예상 효과

1. **사용자 경험 향상**: 직관적인 변수 네비게이션
2. **개발 효율성 증대**: OpCode별 시각적 구분
3. **코드 품질 향상**: SOLID 원칙 준수한 모듈화
4. **유지보수성 향상**: 기존 코드 영향 없는 독립적 구조
