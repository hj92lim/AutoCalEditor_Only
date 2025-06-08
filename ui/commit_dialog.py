"""
Git 커밋 대상 파일을 선택하고 커밋 메시지를 입력하는 대화상자 UI를 제공합니다.

이 모듈은 `CommitFileDialog` 클래스를 정의하며, 이 클래스는 PySide6를 사용하여
Git 변경사항 목록을 사용자에게 보여주고, 이 중 커밋할 파일들을 선택하며,
커밋 메시지를 작성할 수 있는 인터페이스를 제공합니다.
선택된 파일과 메시지는 주 애플리케이션으로 전달되어 Git 커밋 및 푸시 작업에 사용됩니다.
"""

import logging
from typing import List, Dict, Any # Any 추가
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QListWidget,
    QListWidgetItem,
    QTextEdit,
    QSplitter,
    # QCheckBox, # QCheckBox는 직접 사용되지 않음 (QListWidgetItem 플래그로 사용) -> Vulture가 미사용으로 감지
    QMessageBox,
    QFrame,
)
from PySide6.QtCore import Qt # Signal은 현재 사용되지 않음 -> Vulture가 미사용으로 감지할 수 있으나, 일단 유지 (QDialog 등에서 내부적으로 사용될 수도 있음)
from PySide6.QtGui import QFont # QIcon은 현재 사용되지 않음 -> Vulture가 미사용으로 감지


class CommitFileDialog(QDialog):
    """
    Git 커밋 대상 파일을 선택하고 커밋 메시지를 입력하는 대화상자 클래스입니다.

    사용자에게 변경된 파일 목록을 체크박스와 함께 보여주고, 선택된 파일들의 diff를 미리 볼 수 있게 합니다.
    커밋 메시지 입력 필드와 커밋 실행/취소 버튼을 제공합니다.

    Attributes:
        changed_files (List[Dict[str, str]]): Git에서 변경된 것으로 감지된 파일들의 정보 리스트.
                                               각 딕셔너리는 'filename', 'status', 'change_type' 등을 포함합니다.
        selected_files (List[str]): 사용자가 커밋 대상으로 선택한 파일 경로들의 리스트.
        commit_message (str): 사용자가 입력한 커밋 메시지.
    """

    def __init__(self, changed_files: List[Dict[str, str]], parent: Optional[QWidget] = None): # QWidget으로 타입 명시, Optional 추가
        """
        CommitFileDialog를 초기화합니다.

        Args:
            changed_files (List[Dict[str, str]]): Git 변경사항 감지 결과로 얻은 파일 정보 리스트.
                                                   각 파일 정보는 파일명, 상태, 변경 유형 등을 포함하는 딕셔너리입니다.
            parent (Optional[QWidget]): 부모 위젯. 기본값은 None입니다.
        """
        super().__init__(parent)
        self.changed_files: List[Dict[str, str]] = changed_files
        self.selected_files: List[str] = []
        self.commit_message: str = ""

        self.init_ui()
        self.populate_file_list()
        self.update_selected_files() # 초기 버튼 상태 업데이트
        self.commit_message_edit.textChanged.connect(self.update_selected_files) # 커밋 메시지 변경 시 버튼 상태 업데이트

    def init_ui(self) -> None:
        """
        대화상자의 전체 사용자 인터페이스(UI)를 초기화하고 구성합니다.

        커밋 메시지 입력란, 파일 목록 패널, 파일 미리보기 패널, 그리고
        확인/취소 버튼 등을 포함하는 메인 레이아웃을 설정합니다.
        """
        self.setWindowTitle("커밋할 파일 선택 및 메시지 입력")
        self.setModal(True)
        self.resize(1000, 700) # 크기 조정 (이전 1600x1200은 너무 클 수 있음)

        main_layout = QVBoxLayout(self)

        msg_layout = QHBoxLayout()
        msg_layout.addWidget(QLabel("📝 커밋 메시지:"))
        self.commit_message_edit = QLineEdit()
        self.commit_message_edit.setPlaceholderText("변경사항에 대한 설명을 여기에 입력하세요...")
        msg_layout.addWidget(self.commit_message_edit)
        main_layout.addLayout(msg_layout)

        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        main_layout.addWidget(line)

        splitter = QSplitter(Qt.Horizontal)
        left_panel = self.create_file_list_panel()
        splitter.addWidget(left_panel)
        right_panel = self.create_preview_panel()
        splitter.addWidget(right_panel)
        splitter.setSizes([400, 600]) # 파일 목록과 미리보기 영역 비율 조정
        main_layout.addWidget(splitter)

        button_layout = self.create_button_layout()
        main_layout.addLayout(button_layout)

    def create_file_list_panel(self) -> QFrame:
        """
        변경된 파일 목록을 표시하는 UI 패널을 생성합니다.

        패널에는 제목 라벨과 `QListWidget`을 사용한 파일 목록이 포함됩니다.

        Returns:
            QFrame: 생성된 파일 목록 패널 위젯.
        """
        panel = QFrame()
        panel.setFrameShape(QFrame.StyledPanel) # 패널 테두리 추가
        layout = QVBoxLayout(panel)

        title = QLabel("📁 변경된 파일 목록 (커밋할 파일 선택)")
        title.setStyleSheet("font-weight: bold; font-size: 12px; margin-bottom: 5px;")
        layout.addWidget(title)

        self.file_list = QListWidget()
        self.file_list.itemChanged.connect(self.on_file_selection_changed)
        self.file_list.currentItemChanged.connect(self.on_file_clicked)
        layout.addWidget(self.file_list)
        return panel

    def create_preview_panel(self) -> QFrame:
        """
        선택된 파일의 변경사항 미리보기를 표시하는 UI 패널을 생성합니다.

        패널에는 제목 라벨(`preview_title`)과 `QTextEdit`을 사용한 미리보기 영역(`preview_text`)이 포함됩니다.
        미리보기는 고정폭 폰트를 사용하여 diff 내용을 가독성 있게 표시합니다.

        Returns:
            QFrame: 생성된 미리보기 패널 위젯.
        """
        panel = QFrame()
        panel.setFrameShape(QFrame.StyledPanel) # 패널 테두리 추가
        layout = QVBoxLayout(panel)

        self.preview_title = QLabel("📄 변경사항 미리보기 (선택된 파일)")
        self.preview_title.setStyleSheet("font-weight: bold; font-size: 12px; margin-bottom: 5px;")
        layout.addWidget(self.preview_title)

        self.preview_text = QTextEdit()
        self.preview_text.setReadOnly(True)
        self.preview_text.setPlainText("파일 목록에서 파일을 선택하면 여기에 변경사항이 표시됩니다.")

        font = QFont("Consolas", 9) # 고정폭 폰트
        if not QFont.exactMatch(font): font = QFont("Courier New", 9) # 대체 폰트
        self.preview_text.setFont(font)
        layout.addWidget(self.preview_text)
        return panel

    def create_button_layout(self) -> QHBoxLayout:
        """
        대화상자 하단의 버튼들(전체 선택, 선택 해제, 취소, 커밋&푸시)을 포함하는 레이아웃을 생성합니다.

        Returns:
            QHBoxLayout: 생성된 버튼 레이아웃.
        """
        layout = QHBoxLayout()
        select_all_btn = QPushButton("전체 선택")
        select_all_btn.setToolTip("목록의 모든 파일을 선택합니다.")
        select_all_btn.clicked.connect(self.select_all_files)

        clear_btn = QPushButton("전체 해제")
        clear_btn.setToolTip("목록의 모든 파일 선택을 해제합니다.")
        clear_btn.clicked.connect(self.clear_selection)

        layout.addWidget(select_all_btn)
        layout.addWidget(clear_btn)
        layout.addStretch()

        cancel_btn = QPushButton("취소")
        cancel_btn.clicked.connect(self.reject)

        self.commit_btn = QPushButton("📤 커밋 & 푸시")
        self.commit_btn.setToolTip("선택된 파일들을 커밋하고 원격 저장소로 푸시합니다.")
        self.commit_btn.clicked.connect(self.accept_commit)
        self.commit_btn.setStyleSheet(
            "QPushButton { background-color: #28a745; color: white; font-weight: bold; padding: 8px 16px; border-radius: 4px; }"
            "QPushButton:hover { background-color: #218838; }"
            "QPushButton:disabled { background-color: #cccccc; }"
        )
        layout.addWidget(cancel_btn)
        layout.addWidget(self.commit_btn)
        return layout

    def populate_file_list(self) -> None:
        """
        `self.changed_files`에 저장된 파일 정보를 사용하여 파일 목록 위젯(`self.file_list`)을 채웁니다.

        각 파일은 변경 유형(추가, 수정, 삭제 등)과 함께 표시되며, 파일 확장자에 따라 아이콘이 할당됩니다.
        CSV 및 DB 파일은 기본적으로 선택(체크) 상태로 설정됩니다.
        """
        self.file_list.clear()
        for file_info in self.changed_files:
            filename = file_info["filename"]
            change_type = file_info.get("change_type", "변경됨") # 'change_type' 키 존재 확인
            default_check = file_info.get("default_check", False)

            item = QListWidgetItem()
            # 아이콘 설정
            icon_text = "📄" # 기본 아이콘
            if filename.endswith(".csv"): icon_text = "📊"
            elif filename.endswith(".db"): icon_text = "🗄️"
            elif filename.endswith(".py"): icon_text = "🐍"
            elif filename.endswith(".log"): icon_text = "📋"

            item.setText(f"{icon_text} {change_type}: {filename}")
            item.setData(Qt.UserRole, file_info) # 파일 전체 정보 저장
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked if default_check else Qt.Unchecked)
            self.file_list.addItem(item)

    def on_file_selection_changed(self, item: QListWidgetItem) -> None:
        """
        파일 목록에서 아이템의 체크 상태가 변경될 때 호출됩니다.

        선택된 파일 목록(`self.selected_files`)을 업데이트하고 커밋 버튼의 활성화 상태를 조정합니다.

        Args:
            item (QListWidgetItem): 상태가 변경된 리스트 아이템.
        """
        self.update_selected_files()

    def on_file_clicked(self, current_item: Optional[QListWidgetItem], _previous_item: Optional[QListWidgetItem] = None) -> None: # previous_item을 _previous_item으로 변경하고 Optional 기본값 None 설정
        """
        파일 목록에서 아이템이 클릭(선택)될 때 호출됩니다.

        선택된 파일의 변경사항 미리보기를 `self.preview_text`에 표시합니다.

        Args:
            current_item (Optional[QListWidgetItem]): 새로 선택된 리스트 아이템. None일 수 있습니다.
            previous_item (Optional[QListWidgetItem]): 이전에 선택되었던 리스트 아이템. None일 수 있습니다.
        """
        if current_item:
            file_info = current_item.data(Qt.UserRole)
            if file_info and isinstance(file_info, dict): # 데이터 유효성 확인
                filename = file_info.get("filename")
                if filename:
                    self.show_file_preview(filename)
                else:
                    self.preview_text.setPlainText("선택된 파일 정보를 가져올 수 없습니다.")
            else:
                 self.preview_text.setPlainText("선택된 파일 정보가 유효하지 않습니다.")
        else:
            self.preview_title.setText("📄 변경사항 미리보기")
            self.preview_text.setPlainText("파일을 선택하면 변경사항을 미리볼 수 있습니다.")


    def show_file_preview(self, filename: str) -> None:
        """
        지정된 파일의 Git diff 내용을 가져와 미리보기 영역에 표시합니다.

        부모 위젯에 `git_manager` 속성이 존재하고 `get_file_diff` 메소드를 호출할 수 있는 경우에만
        diff 내용을 가져옵니다. 그렇지 않으면 미리보기를 사용할 수 없다는 메시지를 표시합니다.

        Args:
            filename (str): 미리 볼 파일의 경로.
        """
        self.preview_title.setText(f"📄 {filename} - 변경사항 미리보기")
        parent_widget = self.parent() # 타입 캐스팅 없이 부모 직접 사용
        if hasattr(parent_widget, "git_manager") and parent_widget.git_manager:
            try:
                diff_content = parent_widget.git_manager.get_file_diff(filename)
                self.preview_text.setPlainText(diff_content if diff_content else "변경사항이 없거나 미리보기를 생성할 수 없습니다.")
            except Exception as e:
                logging.error(f"Diff 미리보기 생성 중 오류 ({filename}): {e}", exc_info=True)
                self.preview_text.setPlainText(f"미리보기를 생성하는 중 오류가 발생했습니다:\n{e}")
        else:
            self.preview_text.setPlainText("미리보기를 위한 Git 관리자 객체를 찾을 수 없습니다.")


    def update_selected_files(self) -> None:
        """
        현재 파일 목록 위젯에서 체크된 아이템들을 기반으로 `self.selected_files` 리스트를 업데이트하고,
        커밋 버튼의 활성화 상태를 결정합니다.
        """
        self.selected_files = []
        for i in range(self.file_list.count()):
            item = self.file_list.item(i)
            if item.checkState() == Qt.Checked:
                file_info = item.data(Qt.UserRole)
                if file_info and isinstance(file_info, dict) and "filename" in file_info:
                    self.selected_files.append(file_info["filename"])

        can_commit = bool(self.selected_files) and bool(self.commit_message_edit.text().strip())
        self.commit_btn.setEnabled(can_commit)


    def select_all_files(self) -> None:
        """파일 목록의 모든 아이템을 선택(체크) 상태로 변경합니다."""
        for i in range(self.file_list.count()):
            self.file_list.item(i).setCheckState(Qt.Checked)
        self.update_selected_files() # 선택 상태 변경 후 selected_files 업데이트 및 버튼 상태 갱신

    def clear_selection(self) -> None:
        """파일 목록의 모든 아이템을 선택 해제(체크 해제) 상태로 변경합니다."""
        for i in range(self.file_list.count()):
            self.file_list.item(i).setCheckState(Qt.Unchecked)
        self.update_selected_files() # 선택 상태 변경 후 selected_files 업데이트 및 버튼 상태 갱신

    def accept_commit(self) -> None:
        """
        커밋 메시지와 선택된 파일 유효성을 검사한 후, 사용자에게 최종 확인을 받고
        대화상자를 '수락(Accepted)' 상태로 닫습니다.
        """
        self.commit_message = self.commit_message_edit.text().strip()
        if not self.commit_message:
            QMessageBox.warning(self, "커밋 메시지 누락", "커밋 메시지를 입력해야 합니다.")
            self.commit_message_edit.setFocus()
            return

        self.update_selected_files() # 최신 선택 상태 반영
        if not self.selected_files:
            QMessageBox.warning(self, "파일 선택 누락", "커밋할 파일을 하나 이상 선택해야 합니다.")
            return

        # 사용자에게 최종 확인
        # (상세 파일 목록은 너무 길 수 있으므로, 파일 개수만 표시하거나 첫 몇 개만 표시)
        num_selected = len(self.selected_files)
        files_preview = "\n".join([f"• {f}" for f in self.selected_files[:5]]) # 최대 5개 미리보기
        if num_selected > 5: files_preview += "\n  ..."

        reply = QMessageBox.question(
            self,
            "커밋 및 푸시 확인",
            f"총 {num_selected}개의 파일을 다음 메시지로 커밋하고 푸시하시겠습니까?\n\n"
            f"메시지: {self.commit_message}\n\n"
            f"선택된 파일 (일부):\n{files_preview}",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes
        )

        if reply == QMessageBox.Yes:
            logging.info(f"커밋 수락: {self.commit_message}, 파일: {self.selected_files}")
            self.accept() # QDialog.accept() 호출
        else:
            logging.info("커밋 취소됨.")
            # self.reject() # 명시적으로 reject 호출 불필요, 사용자가 No를 누르면 자동으로 reject됨
            pass # 사용자가 'No'를 선택하면 아무것도 하지 않음
