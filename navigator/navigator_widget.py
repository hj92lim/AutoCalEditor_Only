"""
네비게이터 위젯

기존 시스템과 완전히 독립적인 네비게이터 UI를 제공합니다.
"""

from typing import List
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QLineEdit, QTreeWidget, QTreeWidgetItem
)
from PySide6.QtCore import Qt, Signal

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
        
        # 트리 위젯
        self.tree_widget = QTreeWidget()
        self.tree_widget.setHeaderHidden(True)
        self.tree_widget.itemClicked.connect(self._on_item_clicked)
        self.tree_widget.setStyleSheet("""
            QTreeWidget {
                border: 1px solid #bdc3c7;
                border-radius: 3px;
                background-color: white;
                font-size: 11px;
            }
            QTreeWidget::item {
                padding: 3px;
                border-bottom: 1px solid #ecf0f1;
            }
            QTreeWidget::item:hover {
                background-color: #f8f9fa;
            }
            QTreeWidget::item:selected {
                background-color: #3498db;
                color: white;
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
        시트 데이터에서 네비게이터 아이템 생성
        
        Args:
            sheet_data: DB에서 가져온 시트 데이터 (기존 get_sheet_data 결과 활용)
        """
        self.tree_widget.clear()
        
        if not sheet_data:
            self.status_label.setText("No data")
            return
        
        # 네비게이터 아이템 파싱
        items = self.parser.parse_items(sheet_data)
        
        if not items:
            self.status_label.setText("No navigator items found")
            return
        
        # OpCode별 그룹화
        opcode_groups = {}
        for item in items:
            opcode_name = item.opcode.name
            if opcode_name not in opcode_groups:
                opcode_groups[opcode_name] = []
            opcode_groups[opcode_name].append(item)
        
        # 트리 아이템 생성
        for opcode_name, group_items in sorted(opcode_groups.items()):
            # 그룹 아이템 (OpCode별)
            group_item = QTreeWidgetItem([f"📁 {opcode_name} ({len(group_items)})"])
            group_item.setExpanded(True)
            
            # 자식 아이템들 (개별 변수/배열)
            for item in group_items:
                child_item = QTreeWidgetItem([f"{item.icon} {item.name}"])
                child_item.setData(0, Qt.UserRole, (item.row, item.col))
                group_item.addChild(child_item)
            
            self.tree_widget.addTopLevelItem(group_item)
        
        self.status_label.setText(f"{len(items)} items loaded")
    
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
