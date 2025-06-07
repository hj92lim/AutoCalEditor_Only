"""
Git 커밋 파일 선택 다이얼로그
"""

import logging
from typing import List, Dict
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QListWidget, QListWidgetItem, QTextEdit,
    QSplitter, QCheckBox, QMessageBox, QFrame
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QIcon


class CommitFileDialog(QDialog):
    """커밋할 파일 선택 다이얼로그"""

    def __init__(self, changed_files: List[Dict[str, str]], parent=None):
        """
        초기화

        Args:
            changed_files: 변경된 파일 목록
            parent: 부모 위젯
        """
        super().__init__(parent)
        self.changed_files = changed_files
        self.selected_files = []
        self.commit_message = ""

        self.init_ui()
        self.populate_file_list()

    def init_ui(self):
        """UI 초기화"""
        self.setWindowTitle("커밋할 파일 선택")
        self.setModal(True)
        self.resize(1600, 1200)  # 2배 크기로 변경 (800x600 -> 1600x1200)

        # 메인 레이아웃
        main_layout = QVBoxLayout(self)

        # 커밋 메시지 입력
        msg_layout = QHBoxLayout()
        msg_layout.addWidget(QLabel("📝 커밋 메시지:"))
        self.commit_message_edit = QLineEdit()
        self.commit_message_edit.setPlaceholderText("변경사항에 대한 설명을 입력하세요...")
        msg_layout.addWidget(self.commit_message_edit)
        main_layout.addLayout(msg_layout)

        # 구분선
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        main_layout.addWidget(line)

        # 스플리터 (파일 목록 + 미리보기)
        splitter = QSplitter(Qt.Horizontal)

        # 왼쪽: 파일 목록
        left_panel = self.create_file_list_panel()
        splitter.addWidget(left_panel)

        # 오른쪽: 미리보기
        right_panel = self.create_preview_panel()
        splitter.addWidget(right_panel)

        # 스플리터 비율 설정 (파일목록:미리보기 = 1:1) - 2배 크기
        splitter.setSizes([800, 800])
        main_layout.addWidget(splitter)

        # 버튼 영역
        button_layout = self.create_button_layout()
        main_layout.addLayout(button_layout)

    def create_file_list_panel(self):
        """파일 목록 패널 생성"""
        panel = QFrame()
        layout = QVBoxLayout(panel)

        # 제목
        title = QLabel("📁 변경된 파일들")
        title.setStyleSheet("font-weight: bold; font-size: 12px; margin-bottom: 5px;")
        layout.addWidget(title)

        # 파일 목록
        self.file_list = QListWidget()
        self.file_list.itemChanged.connect(self.on_file_selection_changed)
        self.file_list.currentItemChanged.connect(self.on_file_clicked)
        layout.addWidget(self.file_list)

        return panel

    def create_preview_panel(self):
        """미리보기 패널 생성"""
        panel = QFrame()
        layout = QVBoxLayout(panel)

        # 제목
        self.preview_title = QLabel("📄 변경사항 미리보기")
        self.preview_title.setStyleSheet("font-weight: bold; font-size: 12px; margin-bottom: 5px;")
        layout.addWidget(self.preview_title)

        # 미리보기 텍스트
        self.preview_text = QTextEdit()
        self.preview_text.setReadOnly(True)
        self.preview_text.setPlainText("파일을 선택하면 변경사항을 미리볼 수 있습니다.")

        # 고정폭 폰트 설정 (diff 보기 좋게)
        font = QFont("Consolas", 9)
        if not font.exactMatch():
            font = QFont("Courier New", 9)
        self.preview_text.setFont(font)

        layout.addWidget(self.preview_text)

        return panel

    def create_button_layout(self):
        """버튼 레이아웃 생성"""
        layout = QHBoxLayout()

        # 빠른 선택 버튼들
        select_all_btn = QPushButton("전체 선택")
        select_all_btn.clicked.connect(self.select_all_files)

        clear_btn = QPushButton("선택 해제")
        clear_btn.clicked.connect(self.clear_selection)

        layout.addWidget(select_all_btn)
        layout.addWidget(clear_btn)
        layout.addStretch()  # 공간 확보

        # 메인 버튼들
        cancel_btn = QPushButton("취소")
        cancel_btn.clicked.connect(self.reject)

        self.commit_btn = QPushButton("📤 커밋 & 푸시")
        self.commit_btn.clicked.connect(self.accept_commit)
        self.commit_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
                padding: 8px 16px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)

        layout.addWidget(cancel_btn)
        layout.addWidget(self.commit_btn)

        return layout

    def populate_file_list(self):
        """파일 목록 채우기"""
        for file_info in self.changed_files:
            filename = file_info['filename']
            change_type = file_info['change_type']
            is_csv = file_info.get('is_csv', False)
            is_db = file_info.get('is_db', False)
            default_check = file_info.get('default_check', False)

            # 리스트 아이템 생성
            item = QListWidgetItem()
            item.setText(f"{change_type}: {filename}")
            item.setData(Qt.UserRole, file_info)

            # 체크박스 설정
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)

            # 기본 체크 설정 (CSV와 실제 DB 파일)
            if default_check:
                item.setCheckState(Qt.Checked)
            else:
                item.setCheckState(Qt.Unchecked)

            # 아이콘 설정 (파일 타입별)
            if is_csv:
                item.setText(f"📊 {change_type}: {filename}")
            elif is_db:
                item.setText(f"🗄️ {change_type}: {filename}")
            elif filename.endswith('.py'):
                item.setText(f"🐍 {change_type}: {filename}")
            elif filename.endswith('.log'):
                item.setText(f"📋 {change_type}: {filename}")
            else:
                item.setText(f"📄 {change_type}: {filename}")

            self.file_list.addItem(item)

    def on_file_selection_changed(self, item):
        """파일 선택 상태 변경 시"""
        self.update_selected_files()

    def on_file_clicked(self, current_item, previous_item):
        """파일 클릭 시 미리보기 업데이트"""
        if current_item:
            file_info = current_item.data(Qt.UserRole)
            filename = file_info['filename']
            self.show_file_preview(filename)

    def show_file_preview(self, filename: str):
        """파일 미리보기 표시"""
        self.preview_title.setText(f"📄 {filename} - 변경사항")

        # Git diff 가져오기 (부모에서 git_manager 접근)
        if hasattr(self.parent(), 'git_manager'):
            diff_content = self.parent().git_manager.get_file_diff(filename)
            self.preview_text.setPlainText(diff_content)
        else:
            self.preview_text.setPlainText("미리보기를 사용할 수 없습니다.")

    def update_selected_files(self):
        """선택된 파일 목록 업데이트"""
        self.selected_files = []
        for i in range(self.file_list.count()):
            item = self.file_list.item(i)
            if item.checkState() == Qt.Checked:
                file_info = item.data(Qt.UserRole)
                self.selected_files.append(file_info['filename'])

        # 커밋 버튼 활성화/비활성화
        self.commit_btn.setEnabled(len(self.selected_files) > 0)

    def select_all_files(self):
        """모든 파일 선택"""
        for i in range(self.file_list.count()):
            item = self.file_list.item(i)
            item.setCheckState(Qt.Checked)

    def clear_selection(self):
        """선택 해제"""
        for i in range(self.file_list.count()):
            item = self.file_list.item(i)
            item.setCheckState(Qt.Unchecked)

    def accept_commit(self):
        """커밋 확인"""
        # 커밋 메시지 확인
        self.commit_message = self.commit_message_edit.text().strip()
        if not self.commit_message:
            QMessageBox.warning(self, "커밋 메시지 필요",
                              "커밋 메시지를 입력해주세요.")
            return

        # 선택된 파일 확인
        self.update_selected_files()
        if not self.selected_files:
            QMessageBox.warning(self, "파일 선택 필요",
                              "커밋할 파일을 선택해주세요.")
            return

        # 확인 다이얼로그
        file_list = '\n'.join([f"• {f}" for f in self.selected_files])
        reply = QMessageBox.question(
            self, "커밋 확인",
            f"다음 파일들을 커밋하시겠습니까?\n\n{file_list}\n\n"
            f"커밋 메시지: {self.commit_message}",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes
        )

        if reply == QMessageBox.Yes:
            self.accept()
