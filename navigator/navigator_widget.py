"""
네비게이터 위젯

기존 시스템과 완전히 독립적인 네비게이터 UI를 제공합니다.
"""

from typing import List
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QLineEdit, QTreeWidget, QTreeWidgetItem
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor

from .navigator_core import NavigatorParser

class NavigatorWidget(QWidget):
    """네비게이터 위젯 (기존 시스템과 완전 독립)"""
    
    item_clicked = Signal(int, int)  # row, col
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parser = NavigatorParser()
        self._setup_ui()
    
    def _setup_ui(self):
        """UI 설정"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # 제목
        title_label = QLabel("🧭 Navigator")
        title_label.setStyleSheet("""
            QLabel {
                font-weight: bold; 
                font-size: 12px; 
                color: #2c3e50;
                padding: 5px;
                background-color: #ecf0f1;
                border-radius: 3px;
            }
        """)
        layout.addWidget(title_label)
        
        # 검색박스
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("🔍 Search variables...")
        self.search_box.textChanged.connect(self._on_search_changed)
        self.search_box.setStyleSheet("""
            QLineEdit {
                padding: 5px;
                border: 1px solid #bdc3c7;
                border-radius: 3px;
                font-size: 11px;
            }
            QLineEdit:focus {
                border-color: #3498db;
            }
        """)
        layout.addWidget(self.search_box)
        
        # 트리 위젯 (완전한 트리 네비게이션 기능)
        self.tree_widget = QTreeWidget()
        self.tree_widget.setHeaderHidden(True)
        self.tree_widget.itemClicked.connect(self._on_item_clicked)

        # 트리 위젯 고급 설정 (진정한 트리 네비게이션)
        self.tree_widget.setAnimated(True)  # 펼치기/접기 애니메이션
        self.tree_widget.setIndentation(20)  # 들여쓰기 간격
        self.tree_widget.setRootIsDecorated(True)  # 루트 노드 장식 표시
        self.tree_widget.setExpandsOnDoubleClick(True)  # 더블클릭으로 펼치기
        self.tree_widget.setItemsExpandable(True)  # 아이템 펼치기 가능
        self.tree_widget.setAllColumnsShowFocus(True)  # 전체 열 포커스 표시

        # 트리 위젯 스타일 설정 (표준 토글 버튼 복원)
        self.tree_widget.setStyleSheet("""
            QTreeWidget {
                border: 1px solid #d0d0d0;
                border-radius: 4px;
                background-color: white;
                font-size: 11px;
                font-family: 'Segoe UI', Arial, sans-serif;
                outline: none;
                show-decoration-selected: 1;
            }
            QTreeWidget::item {
                padding: 3px 6px;
                border-bottom: 1px solid #f5f5f5;
                min-height: 18px;
            }
            QTreeWidget::item:hover {
                background-color: #f0f8ff;
                border-radius: 2px;
            }
            QTreeWidget::item:selected {
                background-color: #0078d4;
                color: white;
                border-radius: 2px;
            }
            QTreeWidget::branch {
                background: transparent;
            }
            QTreeWidget::branch:has-children:!has-siblings:closed,
            QTreeWidget::branch:closed:has-children:has-siblings {
                border-image: none;
                image: url(:/qt-project.org/styles/commonstyle/images/branch-closed.png);
            }
            QTreeWidget::branch:open:has-children:!has-siblings,
            QTreeWidget::branch:open:has-children:has-siblings {
                border-image: none;
                image: url(:/qt-project.org/styles/commonstyle/images/branch-open.png);
            }
            QTreeWidget::branch:has-children:closed {
                background: transparent;
            }
            QTreeWidget::branch:has-children:open {
                background: transparent;
            }
        """)
        layout.addWidget(self.tree_widget)
        
        # 상태 라벨
        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("""
            QLabel {
                color: #7f8c8d; 
                font-size: 10px;
                padding: 3px;
            }
        """)
        layout.addWidget(self.status_label)
    
    def populate_from_data(self, sheet_data: List[List[str]]):
        """
        시트 데이터에서 네비게이터 아이템 생성 (계층구조 지원)

        Args:
            sheet_data: DB에서 가져온 시트 데이터 (기존 get_sheet_data 결과 활용)
        """
        self.tree_widget.clear()

        if not sheet_data:
            self.status_label.setText("No data")
            return

        # 네비게이터 아이템 파싱 (계층구조 포함)
        items = self.parser.parse_items(sheet_data)

        if not items:
            self.status_label.setText("No navigator items found")
            return

        # DB 순서 기반 계층구조 생성
        self._build_hierarchical_tree(items)

        # 조건부 블록 개수 계산
        conditional_count = sum(1 for item in items if item.is_conditional_block)

        self.status_label.setText(f"{len(items)} items loaded ({conditional_count} conditional blocks)")

    def _build_hierarchical_tree(self, items: List):
        """
        DB 순서 기반 계층구조 트리 생성

        Args:
            items: NavigatorItem 리스트 (계층 정보 포함)
        """
        # 레벨별 부모 아이템 추적
        level_parents = {}  # {level: QTreeWidgetItem}

        for item in items:
            # 트리 아이템 생성
            display_text = f"{item.icon} {item.name}"

            # 조건부 블록인 경우 스타일 구분 (개선된 시각화)
            if item.is_conditional_block:
                # 이미 아이콘이 포함된 이름 사용
                display_text = item.name
            else:
                # 일반 아이템은 아이콘 + 이름
                display_text = f"{item.icon} {item.name}"

            tree_item = QTreeWidgetItem([display_text])
            tree_item.setData(0, Qt.UserRole, (item.row, item.col))

            # 조건부 블록 고급 스타일 적용
            if item.is_conditional_block:
                # 초기 상태는 모두 접힌 상태 (collapsed)
                tree_item.setExpanded(False)

                # 폰트 스타일 설정
                font = tree_item.font(0)
                font.setBold(True)
                tree_item.setFont(0, font)

                # 통일된 폰트 스타일 (색상 구분 최소화)
                base_type = item.block_type.split(':')[0] if ':' in item.block_type else item.block_type

                # 모든 조건부 블록에 일관된 스타일 적용
                tree_item.setForeground(0, QColor(60, 60, 60))  # 진한 회색으로 통일

                # 조건부 블록은 굵은 글씨로 구분
                font = tree_item.font(0)
                font.setBold(True)
                tree_item.setFont(0, font)
            else:
                # 일반 아이템 스타일
                tree_item.setForeground(0, QColor(33, 33, 33))  # 기본 검정

            # 계층 레벨에 따른 부모-자식 관계 설정 (개선된 로직)
            if item.level == 0:
                # 최상위 레벨
                self.tree_widget.addTopLevelItem(tree_item)
                if item.is_conditional_block:
                    level_parents[0] = tree_item
            else:
                # 하위 레벨 - 부모 찾기
                parent_level = item.level - 1
                parent_found = False

                # 역순으로 부모 찾기 (가장 가까운 부모)
                for level in range(parent_level, -1, -1):
                    if level in level_parents:
                        parent_item = level_parents[level]
                        parent_item.addChild(tree_item)
                        # 부모 아이템도 초기에는 접힌 상태 유지
                        parent_found = True
                        break

                if not parent_found:
                    # 부모를 찾을 수 없는 경우 최상위에 추가
                    self.tree_widget.addTopLevelItem(tree_item)

            # 현재 레벨의 부모로 등록 (조건부 블록인 경우)
            if item.is_conditional_block:
                # 블록 타입에서 기본 타입 추출
                base_type = item.block_type.split(':')[0] if ':' in item.block_type else item.block_type

                # 블록 종료가 아닌 경우에만 부모로 등록
                if base_type not in ['conditional_error', 'conditional_warning',
                                   'conditional_end', 'project_conditional_end', 'prjt_def_end']:
                    level_parents[item.level] = tree_item

                # 블록 종료 시 해당 레벨 정리
                if base_type in ['conditional_end', 'project_conditional_end', 'prjt_def_end']:
                    if item.level in level_parents:
                        del level_parents[item.level]

                    # 하위 레벨들도 정리
                    levels_to_remove = [level for level in level_parents.keys() if level > item.level]
                    for level in levels_to_remove:
                        del level_parents[level]
    
    def _on_item_clicked(self, item, _column):
        """아이템 클릭 처리"""
        data = item.data(0, Qt.UserRole)
        if data:
            row, col = data
            self.item_clicked.emit(row, col)
    
    def _on_search_changed(self, text: str):
        """검색 텍스트 변경 처리"""
        # 간단한 검색 구현
        for i in range(self.tree_widget.topLevelItemCount()):
            group_item = self.tree_widget.topLevelItem(i)
            group_visible = False
            
            for j in range(group_item.childCount()):
                child_item = group_item.child(j)
                child_text = child_item.text(0).lower()
                child_visible = text.lower() in child_text if text else True
                child_item.setHidden(not child_visible)
                
                if child_visible:
                    group_visible = True
            
            group_item.setHidden(not group_visible)
    
    def clear(self):
        """네비게이터 클리어"""
        self.tree_widget.clear()
        self.status_label.setText("Ready")

    def export_hierarchy_debug_info(self, output_path: str = None) -> str:
        """
        현재 Navigator 계층구조를 디버깅용 텍스트로 추출

        Args:
            output_path: 저장할 파일 경로 (None이면 문자열만 반환)

        Returns:
            계층구조 텍스트
        """
        from datetime import datetime

        debug_info = []
        debug_info.append("=" * 80)
        debug_info.append("Navigator 계층구조 디버깅 정보")
        debug_info.append(f"생성 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        debug_info.append("=" * 80)
        debug_info.append("")

        # 전체 아이템 수 정보
        total_items = self._count_all_items()
        debug_info.append(f"📊 전체 아이템 수: {total_items}")
        debug_info.append(f"📊 최상위 아이템 수: {self.tree_widget.topLevelItemCount()}")
        debug_info.append("")

        # 계층구조 추출
        debug_info.append("🌳 계층구조:")
        debug_info.append("-" * 60)

        for i in range(self.tree_widget.topLevelItemCount()):
            top_item = self.tree_widget.topLevelItem(i)
            self._extract_item_hierarchy(top_item, debug_info, level=0)

        debug_info.append("")
        debug_info.append("-" * 60)
        debug_info.append("범례:")
        debug_info.append("  [BLOCK] = 조건부 컴파일 블록 (#if, #elif, #endif 등)")
        debug_info.append("  [VAR]   = 변수 또는 일반 아이템")
        debug_info.append("  레벨    = 계층 깊이 (0=최상위)")
        debug_info.append("  행번호  = 원본 데이터에서의 행 위치")
        debug_info.append("=" * 80)

        result_text = "\n".join(debug_info)

        # 파일로 저장
        if output_path:
            try:
                from pathlib import Path
                output_file = Path(output_path)
                output_file.parent.mkdir(parents=True, exist_ok=True)

                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(result_text)

                print(f"✅ Navigator 계층구조 디버깅 정보가 저장되었습니다: {output_file}")

            except Exception as e:
                print(f"❌ 파일 저장 실패: {e}")

        return result_text

    def _count_all_items(self) -> int:
        """전체 아이템 수 계산 (재귀적)"""
        total = 0

        def count_recursive(item):
            nonlocal total
            total += 1
            for i in range(item.childCount()):
                count_recursive(item.child(i))

        for i in range(self.tree_widget.topLevelItemCount()):
            count_recursive(self.tree_widget.topLevelItem(i))

        return total

    def _extract_item_hierarchy(self, item, debug_info: list, level: int):
        """아이템 계층구조를 재귀적으로 추출"""
        # 들여쓰기
        indent = "  " * level

        # 아이템 데이터 추출
        item_text = item.text(0)
        user_data = item.data(0, Qt.UserRole)

        # 블록 타입 판단
        is_conditional = self._is_conditional_block_item(item)
        block_marker = "[BLOCK]" if is_conditional else "[VAR]  "

        # 행/열 정보
        if user_data and isinstance(user_data, tuple) and len(user_data) >= 2:
            row, col = user_data
            location_info = f"(행:{row}, 열:{col})"
        else:
            location_info = "(위치정보없음)"

        # 자식 수 정보
        child_count = item.childCount()
        child_info = f"자식:{child_count}개" if child_count > 0 else ""

        # 디버깅 정보 라인 구성
        debug_line = f"{indent}{block_marker} {item_text}"
        if child_info:
            debug_line += f" [{child_info}]"
        debug_line += f" {location_info} [레벨:{level}]"

        debug_info.append(debug_line)

        # 자식 아이템들 재귀 처리
        for i in range(child_count):
            child_item = item.child(i)
            self._extract_item_hierarchy(child_item, debug_info, level + 1)

    def _is_conditional_block_item(self, item) -> bool:
        """아이템이 조건부 블록인지 판단"""
        item_text = item.text(0).strip()

        # 조건부 컴파일 키워드 확인
        conditional_keywords = ['#if', '#elif', '#else', '#endif', '#error', '#warning']

        for keyword in conditional_keywords:
            if item_text.startswith(keyword):
                return True

        return False
