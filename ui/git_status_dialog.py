"""
Git 상태 확인 및 커밋 다이얼로그
- 변경된 파일 목록 표시
- 파일별 diff 뷰어
- 커밋 메시지 입력 및 커밋/푸시 기능
"""

import logging
import os
from pathlib import Path

# Git 관련 상세 로깅을 위한 전용 로거 생성
git_logger = logging.getLogger('GitStatusDialog')
git_logger.setLevel(logging.DEBUG)
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QSplitter,
    QListWidget, QListWidgetItem, QTextEdit, QLineEdit,
    QPushButton, QLabel, QCheckBox, QGroupBox,
    QMessageBox, QProgressBar, QFrame, QWidget, QApplication
)
from PySide6.QtCore import Qt, QThread, QTimer, Signal
from PySide6.QtGui import QFont, QTextCharFormat, QTextCursor, QColor


class GitStatusDialog(QDialog):
    """Git 상태 확인 및 커밋 다이얼로그"""

    def __init__(self, git_manager, parent=None, db_manager=None):
        super().__init__(parent)
        self.git_manager = git_manager
        self.db_manager = db_manager  # DB 관리자 추가
        self.changed_files = []
        self.selected_files = []
        self.files_before_db_close = []  # DB 닫기 전 파일 목록
        self.files_after_db_close = []   # DB 닫기 후 파일 목록
        self.new_files_from_db_close = []  # DB 닫기로 인해 새로 생긴 파일들

        self.setWindowTitle("Git 상태 확인 및 커밋")
        self.setMinimumSize(1000, 700)
        self.resize(1200, 800)

        self.setup_ui()
        self.load_git_status()

        # 디버깅을 위한 상태 출력
        self._debug_selection_state("초기화 완료")
        
    def setup_ui(self):
        """UI 구성"""
        layout = QVBoxLayout(self)
        layout.setSpacing(2)  # 간격 최소화
        layout.setContentsMargins(3, 3, 3, 3)  # 여백 최소화

        # 간단한 헤더 (최소 크기)
        self.setup_simple_header(layout)

        # 메인 스플리터 (좌: 파일 목록, 우: diff 뷰어) - 높이를 최대한 활용
        main_splitter = QSplitter(Qt.Horizontal)
        main_splitter.setMinimumHeight(600)  # 최소 높이 증가
        layout.addWidget(main_splitter, 10)  # stretch factor 10으로 공간 최대 활용

        # 왼쪽: 파일 목록 패널
        self.setup_file_list_panel(main_splitter)

        # 오른쪽: diff 뷰어 패널
        self.setup_diff_panel(main_splitter)

        # 스플리터 비율 설정 (25:75) - diff 영역을 더 크게
        main_splitter.setSizes([250, 750])

        # 하단: 커밋 패널 (최소 크기)
        self.setup_commit_panel(layout)

        # 버튼 패널 (최소 크기)
        self.setup_button_panel(layout)
        
    def setup_simple_header(self, layout):
        """간단한 헤더 설정 (최소 크기)"""
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(8)

        # 제목과 상태를 한 줄로 통합
        self.status_label = QLabel("Git 상태 | 로딩 중...")
        self.status_label.setStyleSheet("""
            QLabel {
                color: #666;
                font-size: 10px;
                font-weight: bold;
                padding: 2px 0;
            }
        """)
        header_layout.addWidget(self.status_label)

        header_layout.addStretch()
        layout.addLayout(header_layout)
        
    def setup_file_list_panel(self, splitter):
        """파일 목록 패널 설정"""
        file_widget = QWidget()
        file_layout = QVBoxLayout(file_widget)
        file_layout.setContentsMargins(5, 5, 5, 5)

        # 제목
        title_label = QLabel("변경된 파일")
        title_label.setStyleSheet("font-weight: bold; font-size: 12px; margin-bottom: 5px;")
        file_layout.addWidget(title_label)

        # 전체 선택/해제 체크박스
        self.select_all_checkbox = QCheckBox("전체 선택")
        # stateChanged 대신 clicked 신호 사용 (더 직관적)
        self.select_all_checkbox.clicked.connect(self.toggle_all_files_by_click)
        self.select_all_checkbox.setToolTip("모든 파일을 선택하거나 선택 해제합니다")
        self.select_all_checkbox.setTristate(True)  # 3상태 체크박스 활성화

        file_layout.addWidget(self.select_all_checkbox)

        # 파일 목록
        self.file_list = QListWidget()
        self.file_list.setStyleSheet("""
            QListWidget {
                border: 1px solid #ccc;
                background-color: white;
            }
            QListWidget::item {
                padding: 4px;
                border-bottom: 1px solid #eee;
            }
            QListWidget::item:selected {
                background-color: #e3f2fd;
            }
        """)
        self.file_list.itemClicked.connect(self.on_file_selected)
        file_layout.addWidget(self.file_list)

        splitter.addWidget(file_widget)
        
    def setup_diff_panel(self, splitter):
        """좌우 분할 diff 뷰어 패널 설정"""
        diff_widget = QWidget()
        diff_layout = QVBoxLayout(diff_widget)
        diff_layout.setContentsMargins(2, 2, 2, 2)  # 여백 최소화
        diff_layout.setSpacing(2)  # 간격 최소화

        # 선택된 파일 정보 (더 작게)
        self.selected_file_label = QLabel("파일을 선택하면 변경 내용이 표시됩니다")
        self.selected_file_label.setStyleSheet("""
            QLabel {
                color: #666;
                font-size: 9px;
                padding: 1px;
                max-height: 16px;
            }
        """)
        diff_layout.addWidget(self.selected_file_label)

        # 좌우 분할 diff 뷰어 컨테이너
        diff_splitter = QSplitter(Qt.Horizontal)
        diff_splitter.setStyleSheet("""
            QSplitter::handle {
                background-color: #ddd;
                width: 3px;
            }
            QSplitter::handle:hover {
                background-color: #bbb;
            }
        """)

        # 왼쪽 패널 (이전 버전 + 삭제된 라인)
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(2, 2, 2, 2)
        left_layout.setSpacing(2)

        left_header = QLabel("이전 (삭제된 라인)")
        left_header.setStyleSheet("""
            QLabel {
                background-color: #f8d7da;
                color: #721c24;
                padding: 2px 4px;
                font-size: 9px;
                font-weight: bold;
                border-radius: 2px;
                max-height: 18px;
            }
        """)
        left_layout.addWidget(left_header)

        self.left_diff_viewer = QTextEdit()
        self.left_diff_viewer.setReadOnly(True)
        self.left_diff_viewer.setFont(QFont("Consolas", 8))
        self.left_diff_viewer.setStyleSheet("""
            QTextEdit {
                border: 1px solid #f5c6cb;
                background-color: #fefefe;
                color: #333;
            }
        """)
        left_layout.addWidget(self.left_diff_viewer)

        # 오른쪽 패널 (현재 버전 + 추가된 라인)
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(2, 2, 2, 2)
        right_layout.setSpacing(2)

        right_header = QLabel("현재 (추가된 라인)")
        right_header.setStyleSheet("""
            QLabel {
                background-color: #d4edda;
                color: #155724;
                padding: 2px 4px;
                font-size: 9px;
                font-weight: bold;
                border-radius: 2px;
                max-height: 18px;
            }
        """)
        right_layout.addWidget(right_header)

        self.right_diff_viewer = QTextEdit()
        self.right_diff_viewer.setReadOnly(True)
        self.right_diff_viewer.setFont(QFont("Consolas", 8))
        self.right_diff_viewer.setStyleSheet("""
            QTextEdit {
                border: 1px solid #c3e6cb;
                background-color: #fefefe;
                color: #333;
            }
        """)
        right_layout.addWidget(self.right_diff_viewer)

        # 스플리터에 좌우 패널 추가
        diff_splitter.addWidget(left_widget)
        diff_splitter.addWidget(right_widget)
        diff_splitter.setSizes([1, 1])  # 50:50 비율

        diff_layout.addWidget(diff_splitter)
        splitter.addWidget(diff_widget)
        
    def setup_commit_panel(self, layout):
        """커밋 패널 설정 (최소 크기)"""
        commit_layout = QHBoxLayout()
        commit_layout.setSpacing(6)
        commit_layout.setContentsMargins(0, 2, 0, 2)

        # 커밋 메시지 레이블 (더 작게)
        commit_label = QLabel("커밋:")
        commit_label.setStyleSheet("font-weight: bold; font-size: 10px;")
        commit_layout.addWidget(commit_label)

        # 커밋 메시지 입력 (더 작게)
        self.commit_message_input = QLineEdit()
        self.commit_message_input.setPlaceholderText("변경 사항 설명...")
        self.commit_message_input.setStyleSheet("""
            QLineEdit {
                padding: 4px;
                font-size: 10px;
                border: 1px solid #ccc;
                border-radius: 2px;
                max-height: 24px;
            }
        """)
        commit_layout.addWidget(self.commit_message_input)

        layout.addLayout(commit_layout)
        
    def setup_button_panel(self, layout):
        """버튼 패널 설정 (최소 크기)"""
        button_layout = QHBoxLayout()
        button_layout.setSpacing(6)
        button_layout.setContentsMargins(0, 2, 0, 2)

        # 새로고침 버튼 (더 작게)
        self.refresh_button = QPushButton("🔄")
        self.refresh_button.clicked.connect(self.load_git_status)
        self.refresh_button.setStyleSheet(self.get_compact_button_style("#6c757d"))
        self.refresh_button.setToolTip("새로고침")

        # 커밋 & 푸시 버튼 (더 작게)
        self.commit_push_button = QPushButton("커밋 & 푸시")
        self.commit_push_button.clicked.connect(self.commit_and_push)
        self.commit_push_button.setStyleSheet(self.get_compact_button_style("#28a745"))

        # 닫기 버튼 (더 작게)
        close_button = QPushButton("❌")
        close_button.clicked.connect(self.close)
        close_button.setStyleSheet(self.get_compact_button_style("#dc3545"))
        close_button.setToolTip("닫기")

        button_layout.addWidget(self.refresh_button)
        button_layout.addStretch()
        button_layout.addWidget(self.commit_push_button)
        button_layout.addWidget(close_button)

        layout.addLayout(button_layout)
        
    def get_button_style(self, color):
        """버튼 스타일 생성"""
        return f"""
            QPushButton {{
                padding: 8px 16px;
                font-size: 12px;
                font-weight: bold;
                background-color: {color};
                color: white;
                border: none;
                border-radius: 4px;
                min-width: 100px;
            }}
            QPushButton:hover {{
                background-color: {self.darken_color(color)};
            }}
            QPushButton:pressed {{
                background-color: {self.darken_color(color, 0.2)};
            }}
        """

    def get_compact_button_style(self, color):
        """컴팩트 버튼 스타일 생성"""
        return f"""
            QPushButton {{
                padding: 4px 8px;
                font-size: 10px;
                font-weight: bold;
                background-color: {color};
                color: white;
                border: none;
                border-radius: 3px;
                min-width: 60px;
                max-height: 24px;
            }}
            QPushButton:hover {{
                background-color: {self.darken_color(color)};
            }}
            QPushButton:pressed {{
                background-color: {self.darken_color(color, 0.2)};
            }}
        """
        
    def darken_color(self, hex_color, factor=0.1):
        """색상을 어둡게 만들기"""
        # 간단한 색상 어둡게 하기 (실제로는 더 정교한 계산 필요)
        color_map = {
            "#6c757d": "#5a6268",
            "#28a745": "#218838", 
            "#dc3545": "#c82333"
        }
        return color_map.get(hex_color, hex_color)

    def load_git_status(self):
        """Git 상태 로드 (GitManager 활용)"""
        try:
            self.status_label.setText("상태 로딩 중...")

            # GitManager를 통해 변경된 파일 목록 가져오기
            self.changed_files = self.git_manager.get_changed_files(use_enhanced_encoding=True)

            # 현재 브랜치 정보 (GitManager 활용)
            try:
                current_branch = self.git_manager.get_current_branch()
                branch_info = f"현재 브랜치: {current_branch}"
            except:
                branch_info = "브랜치 정보 없음"

            # 상태 정보 업데이트
            file_count = len(self.changed_files)
            if file_count == 0:
                status_text = f"Git 상태 | {branch_info} | 변경된 파일 없음"
                self.status_label.setStyleSheet("""
                    QLabel {
                        color: #28a745;
                        font-size: 10px;
                        font-weight: bold;
                        padding: 2px 0;
                    }
                """)
            else:
                status_text = f"Git 상태 | {branch_info} | {file_count}개 파일 변경됨"
                self.status_label.setStyleSheet("""
                    QLabel {
                        color: #fd7e14;
                        font-size: 10px;
                        font-weight: bold;
                        padding: 2px 0;
                    }
                """)

            self.status_label.setText(status_text)

            # 파일 목록 업데이트
            self.update_file_list()

            # 커밋 버튼 상태 업데이트
            self.commit_push_button.setEnabled(file_count > 0)

        except Exception as e:
            git_logger.error(f"Git 상태 로드 실패: {e}")
            git_logger.debug(f"Git 상태 로드 실패 상세 정보: {e}", exc_info=True)
            self.status_label.setText(f"상태 로드 실패: {str(e)}")
            self.status_label.setStyleSheet("color: #dc3545; font-size: 10px;")





    def update_file_list(self):
        """파일 목록 업데이트 (개선된 버전)"""
        try:
            # 기존 연결 해제 (완전히 안전한 방법)
            if hasattr(self, 'file_list') and self.file_list is not None:
                # 신호 차단
                self.file_list.blockSignals(True)

                # 기존 위젯 완전 정리
                try:
                    # 모든 아이템 제거
                    self.file_list.clear()

                    # 신호 연결 상태 확인 후 해제
                    signal = self.file_list.itemChanged
                    try:
                        # 연결된 슬롯이 있는지 확인
                        if signal.receivers() > 0:
                            signal.disconnect()
                    except:
                        pass

                except Exception as e:
                    logging.debug(f"신호 해제 중 예외 (무시됨): {e}")

            # 신호 차단하고 목록 초기화
            self.file_list.blockSignals(True)
            self.file_list.clear()
            self.selected_files.clear()

            logging.info(f"파일 목록 업데이트: {len(self.changed_files)}개 파일")

            for i, file_info in enumerate(self.changed_files):
                filename = file_info['filename']
                change_type = file_info['change_type']

                # 간단한 텍스트 항목 생성
                display_text = f"[{change_type}] {filename}"
                item = QListWidgetItem(display_text)

                # 체크 가능하도록 설정
                item.setFlags(item.flags() | Qt.ItemIsUserCheckable)

                # 기본적으로 CSV와 DB 파일은 선택
                if file_info.get('default_check', False):
                    item.setCheckState(Qt.Checked)
                    self.selected_files.append(filename)
                    logging.debug(f"기본 선택: {filename}")
                else:
                    item.setCheckState(Qt.Unchecked)

                self.file_list.addItem(item)

            # 신호 차단 해제
            self.file_list.blockSignals(False)

            # 이벤트 연결 (한 번만)
            self.file_list.itemChanged.connect(self.on_item_changed)

            # 전체 선택 체크박스 상태 업데이트
            self.update_select_all_checkbox()

            logging.info(f"파일 목록 업데이트 완료: {len(self.selected_files)}개 기본 선택됨")

        except Exception as e:
            logging.error(f"파일 목록 업데이트 중 오류: {e}")
            import traceback
            logging.error(traceback.format_exc())

    def on_item_changed(self, item):
        """파일 아이템 체크 상태 변경 (개선된 버전)"""
        try:
            row = self.file_list.row(item)
            if row < 0 or row >= len(self.changed_files):
                logging.warning(f"잘못된 행 인덱스: {row}, 전체 파일 수: {len(self.changed_files)}")
                return

            filename = self.changed_files[row]['filename']
            is_checked = item.checkState() == Qt.Checked

            # 선택된 파일 목록 업데이트
            if is_checked:
                if filename not in self.selected_files:
                    self.selected_files.append(filename)
                    logging.debug(f"파일 선택: {filename}")
            else:
                if filename in self.selected_files:
                    self.selected_files.remove(filename)
                    logging.debug(f"파일 선택 해제: {filename}")

            # 전체 선택 체크박스 상태 업데이트
            self.update_select_all_checkbox()

            logging.debug(f"현재 선택된 파일 수: {len(self.selected_files)}/{len(self.changed_files)}")

        except Exception as e:
            logging.error(f"아이템 변경 처리 중 오류: {e}")
            import traceback
            logging.error(traceback.format_exc())

    def update_select_all_checkbox(self):
        """전체 선택 체크박스 상태 업데이트 (개선된 버전)"""
        try:
            total_files = len(self.changed_files)
            selected_count = len(self.selected_files)

            # 무한 루프 방지를 위해 모든 신호 차단
            self.select_all_checkbox.blockSignals(True)

            if selected_count == 0:
                new_state = Qt.Unchecked
                state_text = "선택 없음"
            elif selected_count == total_files:
                new_state = Qt.Checked
                state_text = "전체 선택"
            else:
                new_state = Qt.PartiallyChecked
                state_text = f"부분 선택 ({selected_count}/{total_files})"

            # 현재 상태와 다를 때만 업데이트
            current_state = self.select_all_checkbox.checkState()
            if current_state != new_state:
                self.select_all_checkbox.setCheckState(new_state)
                logging.debug(f"전체 선택 체크박스 상태 업데이트: {state_text} (이전: {current_state} → 현재: {new_state})")
            else:
                logging.debug(f"전체 선택 체크박스 상태 유지: {state_text}")

        except Exception as e:
            logging.error(f"전체 선택 체크박스 업데이트 중 오류: {e}")
        finally:
            # 신호 차단 해제
            self.select_all_checkbox.blockSignals(False)

    def toggle_all_files(self, state):
        """전체 파일 선택/해제 (수정된 버전)"""
        try:
            logging.info(f"🔄 toggle_all_files 호출됨: state={state} (Qt.Checked={Qt.Checked})")

            # 무한 루프 방지를 위해 itemChanged 신호 일시 차단
            self.file_list.blockSignals(True)

            # state는 정수 값이므로 Qt 상수와 비교
            if state == Qt.Checked:  # state == 2
                # 모든 파일 선택
                self.selected_files = [f['filename'] for f in self.changed_files]
                target_state = Qt.Checked
                logging.info(f"✅ 전체 선택: {len(self.selected_files)}개 파일")
            elif state == Qt.Unchecked:  # state == 0
                # 모든 파일 선택 해제
                self.selected_files.clear()
                target_state = Qt.Unchecked
                logging.info("❌ 전체 선택 해제")
            else:  # state == Qt.PartiallyChecked (1) 또는 기타
                # 부분 선택 상태에서는 전체 선택으로 변경
                self.selected_files = [f['filename'] for f in self.changed_files]
                target_state = Qt.Checked
                logging.info(f"🔄 부분 선택에서 전체 선택으로: {len(self.selected_files)}개 파일")

            # UI 업데이트 - 모든 아이템의 체크 상태 변경
            updated_count = 0
            for i in range(self.file_list.count()):
                item = self.file_list.item(i)
                if item:
                    old_state = item.checkState()
                    item.setCheckState(target_state)
                    if old_state != target_state:
                        updated_count += 1

            logging.info(f"🔧 UI 업데이트 완료: {self.file_list.count()}개 아이템 중 {updated_count}개 변경, 선택된 파일: {len(self.selected_files)}개")

            # 디버깅 상태 출력
            self._debug_selection_state("toggle_all_files 완료")

        except Exception as e:
            logging.error(f"전체 선택/해제 중 오류: {e}")
            import traceback
            logging.error(traceback.format_exc())
        finally:
            # 신호 차단 해제
            self.file_list.blockSignals(False)

    def toggle_all_files_by_click(self, checked):
        """전체 파일 선택/해제 (클릭 기반) - 최종 수정 버전"""
        try:
            logging.info(f"🖱️ 전체 선택 체크박스 클릭: checked={checked}")

            # 현재 체크박스 상태 확인
            current_checkbox_state = self.select_all_checkbox.checkState()
            logging.info(f"현재 체크박스 상태: {current_checkbox_state}")

            # 무한 루프 방지를 위해 모든 신호 일시 차단
            self.file_list.blockSignals(True)
            self.select_all_checkbox.blockSignals(True)

            # 체크박스 상태에 따라 동작 결정
            if current_checkbox_state == Qt.Checked or checked:
                # 전체 선택
                self.selected_files = [f['filename'] for f in self.changed_files]
                target_state = Qt.Checked
                final_checkbox_state = Qt.Checked
                logging.info(f"✅ 전체 선택: {len(self.selected_files)}개 파일")
            else:
                # 전체 선택 해제
                self.selected_files.clear()
                target_state = Qt.Unchecked
                final_checkbox_state = Qt.Unchecked
                logging.info("❌ 전체 선택 해제")

            # UI 업데이트 - 모든 아이템의 체크 상태 변경
            updated_count = 0
            for i in range(self.file_list.count()):
                item = self.file_list.item(i)
                if item:
                    old_state = item.checkState()
                    item.setCheckState(target_state)
                    if old_state != target_state:
                        updated_count += 1

            # 체크박스 상태도 명시적으로 설정
            self.select_all_checkbox.setCheckState(final_checkbox_state)

            logging.info(f"🔧 UI 업데이트 완료: {self.file_list.count()}개 아이템 중 {updated_count}개 변경")

            # 디버깅 상태 출력
            self._debug_selection_state("toggle_all_files_by_click 완료")

        except Exception as e:
            logging.error(f"전체 선택/해제 중 오류: {e}")
            import traceback
            logging.error(traceback.format_exc())
        finally:
            # 신호 차단 해제
            self.select_all_checkbox.blockSignals(False)
            self.file_list.blockSignals(False)

    def on_file_selected(self, item):
        """파일 선택 시 diff 표시"""
        try:
            # 선택된 파일명 찾기 - 간단한 방법 사용
            row = self.file_list.row(item)
            if row < 0 or row >= len(self.changed_files):
                return

            file_info = self.changed_files[row]
            filename = file_info['filename']

            # 선택된 파일 정보 업데이트
            self.selected_file_label.setText(f"파일: {filename}")

            # diff 로드
            self.load_file_diff(filename)

        except Exception as e:
            logging.error(f"파일 선택 처리 중 오류: {e}")

    def load_file_diff(self, filename):
        """파일의 diff 로드 및 좌우 분할 표시 (GitManager 활용)"""
        try:
            self.left_diff_viewer.setText("diff 로딩 중...")
            self.right_diff_viewer.setText("diff 로딩 중...")

            # GitManager를 통해 diff 가져오기
            diff_content = self.git_manager.get_file_diff(filename)

            if diff_content and diff_content.strip():
                # diff 내용을 좌우 분할로 표시
                self.display_split_diff(diff_content)
                logging.info(f"diff 표시 완료: {len(diff_content)} 문자")
            else:
                # diff가 없는 경우 기본 메시지 표시
                no_diff_message = f"파일 '{filename}'의 변경사항을 표시할 수 없습니다.\n\n가능한 원인:\n• 바이너리 파일\n• 파일 권한 변경만 있는 경우\n• Git 설정 문제\n\nVSCode나 다른 Git 클라이언트에서 확인해보세요."
                self.left_diff_viewer.setText(no_diff_message)
                self.right_diff_viewer.setText(no_diff_message)

        except Exception as e:
            logging.error(f"diff 로드 실패 ({filename}): {e}")
            error_message = f"diff 로드 실패: {str(e)}"
            self.left_diff_viewer.setText(error_message)
            self.right_diff_viewer.setText(error_message)



    def display_split_diff(self, diff_content):
        """diff 내용을 좌우 분할로 표시 (이전/현재 버전)"""
        self.left_diff_viewer.clear()
        self.right_diff_viewer.clear()

        # diff 파싱
        left_lines, right_lines = self.parse_diff_content(diff_content)

        # 왼쪽 뷰어 (이전 버전 + 삭제된 라인)
        self.populate_diff_viewer(self.left_diff_viewer, left_lines, "left")

        # 오른쪽 뷰어 (현재 버전 + 추가된 라인)
        self.populate_diff_viewer(self.right_diff_viewer, right_lines, "right")

        # 스크롤 동기화
        self.sync_scroll_bars()

    def parse_diff_content(self, diff_content):
        """diff 내용을 파싱하여 좌우 버전으로 분리"""
        lines = diff_content.split('\n')
        left_lines = []  # 이전 버전 (기본 + 삭제된 라인)
        right_lines = []  # 현재 버전 (기본 + 추가된 라인)

        current_file = ""
        in_content = False

        for line in lines:
            if line.startswith('diff --git'):
                current_file = line[11:]  # "diff --git " 제거
                left_lines.append(('header', f'파일: {current_file}'))
                right_lines.append(('header', f'파일: {current_file}'))
                in_content = False

            elif line.startswith('@@'):
                in_content = True
                # 청크 헤더는 건너뛰기
                continue

            elif in_content:
                if line.startswith('-'):
                    # 삭제된 라인 - 왼쪽에만 표시 (빨간색)
                    left_lines.append(('removed', line[1:]))
                    # 오른쪽에는 빈 라인 추가 (정렬 유지)
                    right_lines.append(('empty', ''))

                elif line.startswith('+'):
                    # 추가된 라인 - 오른쪽에만 표시 (녹색)
                    right_lines.append(('added', line[1:]))
                    # 왼쪽에는 빈 라인 추가 (정렬 유지)
                    left_lines.append(('empty', ''))

                elif line.startswith(' ') or line == '':
                    # 컨텍스트 라인 - 양쪽에 모두 표시
                    content = line[1:] if line.startswith(' ') else ''
                    left_lines.append(('context', content))
                    right_lines.append(('context', content))

        return left_lines, right_lines

    def populate_diff_viewer(self, viewer, lines, side):
        """diff 뷰어에 라인들을 채우기"""
        cursor = viewer.textCursor()

        # 포맷 설정
        header_format = QTextCharFormat()
        header_format.setForeground(QColor("#0056b3"))
        header_format.setFontWeight(QFont.Bold)

        context_format = QTextCharFormat()
        context_format.setForeground(QColor("#333"))

        removed_format = QTextCharFormat()
        removed_format.setForeground(QColor("#dc3545"))
        removed_format.setBackground(QColor("#f8d7da"))

        added_format = QTextCharFormat()
        added_format.setForeground(QColor("#28a745"))
        added_format.setBackground(QColor("#d4edda"))

        empty_format = QTextCharFormat()
        empty_format.setForeground(QColor("#f0f0f0"))

        for line_type, content in lines:
            if line_type == 'header':
                cursor.setCharFormat(header_format)
                cursor.insertText(f'{content}\n')
                cursor.insertText('-' * 50 + '\n')

            elif line_type == 'context':
                cursor.setCharFormat(context_format)
                cursor.insertText(f'{content}\n')

            elif line_type == 'removed' and side == 'left':
                cursor.setCharFormat(removed_format)
                cursor.insertText(f'- {content}\n')

            elif line_type == 'added' and side == 'right':
                cursor.setCharFormat(added_format)
                cursor.insertText(f'+ {content}\n')

            elif line_type == 'empty':
                cursor.setCharFormat(empty_format)
                cursor.insertText('\n')

        # 커서를 맨 위로 이동
        cursor.movePosition(QTextCursor.Start)
        viewer.setTextCursor(cursor)

    def sync_scroll_bars(self):
        """좌우 스크롤바 동기화"""
        def sync_left_to_right():
            right_scroll = self.right_diff_viewer.verticalScrollBar()
            left_value = self.left_diff_viewer.verticalScrollBar().value()
            right_scroll.setValue(left_value)

        def sync_right_to_left():
            left_scroll = self.left_diff_viewer.verticalScrollBar()
            right_value = self.right_diff_viewer.verticalScrollBar().value()
            left_scroll.setValue(right_value)

        # 스크롤바 연결
        self.left_diff_viewer.verticalScrollBar().valueChanged.connect(sync_left_to_right)
        self.right_diff_viewer.verticalScrollBar().valueChanged.connect(sync_right_to_left)

    def commit_and_push(self):
        """선택된 파일들을 커밋하고 푸시 (DB 닫기 → 새 파일 추적 → 커밋)"""
        try:
            # 커밋 메시지 확인
            commit_message = self.commit_message_input.text().strip()
            if not commit_message:
                QMessageBox.warning(self, "커밋 메시지 필요",
                                  "커밋 메시지를 입력해주세요.")
                self.commit_message_input.setFocus()
                return

            # 선택된 파일 확인
            if not self.selected_files:
                QMessageBox.warning(self, "파일 선택 필요",
                                  "커밋할 파일을 선택해주세요.")
                return

            # 1단계: DB 닫기 전 현재 변경된 파일 목록 저장
            self.files_before_db_close = [f['filename'] for f in self.changed_files]

            # 2단계: DB가 열려있다면 닫기 처리
            db_closed = self.close_db_if_open()

            # 3단계: DB 닫기 후 새로운 변경사항 확인
            if db_closed:
                self.check_new_files_after_db_close()

            # 4단계: 최종 커밋 확인 다이얼로그 (새로 생긴 파일 포함)
            reply = self.show_enhanced_commit_confirmation_dialog(commit_message)

            if reply != QMessageBox.Yes:
                return

            # 5단계: 커밋 & 푸시 실행
            self.perform_commit_and_push(commit_message)

        except Exception as e:
            logging.error(f"커밋 & 푸시 중 오류: {e}")
            QMessageBox.critical(self, "커밋 오류",
                               f"커밋 중 오류가 발생했습니다:\n{str(e)}")

    def perform_commit_and_push(self, commit_message):
        """실제 커밋 & 푸시 수행 (GitManager 활용, 새로 생긴 파일 포함)"""
        try:
            # 버튼 비활성화
            self.commit_push_button.setEnabled(False)
            self.commit_push_button.setText("커밋 & 푸시 중...")

            # GitManager를 통해 선택된 파일들 커밋 및 푸시
            success = self.git_manager.commit_selected_files(
                selected_files=self.selected_files,
                commit_message=commit_message
            )

            if success:
                # 현재 브랜치 정보 가져오기
                current_branch = self.git_manager.get_current_branch()

                # 새로 생긴 파일 수 계산
                new_files_count = len(self.new_files_from_db_close)
                existing_files_count = len(self.selected_files) - new_files_count

                # 성공 메시지 (새로 생긴 파일 정보 포함)
                success_message = (
                    f"성공적으로 커밋하고 푸시했습니다.\n\n"
                    f"커밋 메시지: {commit_message}\n"
                    f"총 파일 수: {len(self.selected_files)}개\n"
                    f"새로 생긴 파일: {new_files_count}개\n"
                    f"기존 파일: {existing_files_count}개\n"
                    f"브랜치: {current_branch}"
                )

                if new_files_count > 0:
                    success_message += f"\n\nDB 닫기로 인해 {new_files_count}개의 새로운 변경사항이 커밋되었습니다."

                QMessageBox.information(self, "커밋 & 푸시 완료", success_message)

                # 상태 새로고침
                self.load_git_status()

                # 커밋 메시지 초기화
                self.commit_message_input.clear()

                # 다이얼로그 성공적으로 완료
                self.accept()
            else:
                QMessageBox.critical(self, "커밋 실패",
                                   f"커밋 및 푸시에 실패했습니다.\n\n"
                                   f"선택한 파일 수: {len(self.selected_files)}개\n"
                                   f"새로 생긴 파일: {len(self.new_files_from_db_close)}개\n"
                                   f"일부 파일이 스테이징되지 않았을 수 있습니다.\n\n"
                                   f"자세한 내용은 로그를 확인해주세요.")

        except Exception as e:
            logging.error(f"커밋 & 푸시 실행 중 오류: {e}")
            QMessageBox.critical(self, "실행 오류",
                               f"커밋 & 푸시 실행 중 오류가 발생했습니다:\n{str(e)}")
        finally:
            # 버튼 복원
            self.commit_push_button.setEnabled(True)
            self.commit_push_button.setText("커밋 & 푸시")

    def show_commit_confirmation_dialog(self, commit_message: str, selected_files: list) -> int:
        """스크롤 가능한 커밋 확인 다이얼로그"""
        from PySide6.QtWidgets import QScrollArea

        # 커스텀 다이얼로그 생성
        dialog = QDialog(self)
        dialog.setWindowTitle("커밋 & 푸시 확인")
        dialog.setModal(True)

        # 화면 크기의 60% 정도로 설정
        screen = dialog.screen().availableGeometry()
        dialog_width = min(600, int(screen.width() * 0.6))
        dialog_height = min(500, int(screen.height() * 0.6))
        dialog.resize(dialog_width, dialog_height)

        # 메인 레이아웃
        layout = QVBoxLayout(dialog)

        # 제목 라벨
        title_label = QLabel("다음 파일들을 커밋하고 푸시하시겠습니까?")
        title_label.setStyleSheet("font-weight: bold; font-size: 14px; margin-bottom: 10px;")
        layout.addWidget(title_label)

        # 커밋 메시지 표시
        commit_info = QLabel(f"커밋 메시지: {commit_message}")
        commit_info.setStyleSheet("margin-bottom: 10px; padding: 5px; background-color: #f0f0f0; border-radius: 3px;")
        commit_info.setWordWrap(True)
        layout.addWidget(commit_info)

        # 파일 개수 표시
        file_count_label = QLabel(f"선택된 파일: {len(selected_files)}개")
        file_count_label.setStyleSheet("font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(file_count_label)

        # 스크롤 영역 생성
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setMinimumHeight(200)

        # 파일 목록 위젯
        file_list_widget = QWidget()
        file_list_layout = QVBoxLayout(file_list_widget)

        # 파일 목록 추가 (최대 50개까지만 표시, 나머지는 "... 외 N개" 형태)
        max_display = 50
        for i, filename in enumerate(selected_files):
            if i < max_display:
                file_label = QLabel(f"• {filename}")
                file_label.setStyleSheet("padding: 2px; margin: 1px;")
                file_list_layout.addWidget(file_label)
            else:
                remaining = len(selected_files) - max_display
                more_label = QLabel(f"... 외 {remaining}개 파일")
                more_label.setStyleSheet("padding: 2px; margin: 1px; font-style: italic; color: #666;")
                file_list_layout.addWidget(more_label)
                break

        scroll_area.setWidget(file_list_widget)
        layout.addWidget(scroll_area)

        # 버튼 레이아웃
        button_layout = QHBoxLayout()

        # 취소 버튼
        cancel_button = QPushButton("취소")
        cancel_button.clicked.connect(dialog.reject)
        cancel_button.setStyleSheet("""
            QPushButton {
                padding: 8px 16px;
                font-size: 12px;
                background-color: #6c757d;
                color: white;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #5a6268;
            }
        """)

        # 확인 버튼
        confirm_button = QPushButton("커밋 & 푸시")
        confirm_button.clicked.connect(dialog.accept)
        confirm_button.setStyleSheet("""
            QPushButton {
                padding: 8px 16px;
                font-size: 12px;
                font-weight: bold;
                background-color: #28a745;
                color: white;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #218838;
            }
        """)
        confirm_button.setDefault(True)  # Enter 키로 실행 가능

        button_layout.addStretch()
        button_layout.addWidget(cancel_button)
        button_layout.addWidget(confirm_button)
        layout.addLayout(button_layout)

        # 다이얼로그 실행
        result = dialog.exec()
        return QMessageBox.Yes if result == QDialog.Accepted else QMessageBox.No

    def _debug_selection_state(self, context: str):
        """선택 상태 디버깅 (개발용)"""
        try:
            total_files = len(self.changed_files)
            selected_count = len(self.selected_files)
            checkbox_state = self.select_all_checkbox.checkState()

            state_names = {
                Qt.Unchecked: "Unchecked",
                Qt.PartiallyChecked: "PartiallyChecked",
                Qt.Checked: "Checked"
            }

            logging.info(f"선택 상태 [{context}]: "
                        f"전체={total_files}, 선택={selected_count}, "
                        f"체크박스={state_names.get(checkbox_state, 'Unknown')}")

            # UI 아이템 상태도 확인
            ui_checked_count = 0
            for i in range(self.file_list.count()):
                item = self.file_list.item(i)
                if item and item.checkState() == Qt.Checked:
                    ui_checked_count += 1

            if ui_checked_count != selected_count:
                logging.warning(f"상태 불일치: UI 체크={ui_checked_count}, 내부 선택={selected_count}")

        except Exception as e:
            logging.error(f"디버깅 상태 확인 중 오류: {e}")

    def close_db_if_open(self) -> bool:
        """DB가 열려있다면 닫기 처리"""
        try:
            if not self.db_manager or not self.db_manager.current_db_name:
                logging.info("열린 DB가 없음 - DB 닫기 건너뛰기")
                return False

            current_db_name = self.db_manager.current_db_name
            current_db = self.db_manager.get_current_db()
            db_file_name = "알 수 없음"

            # DB 파일명 가져오기
            if current_db and hasattr(current_db, 'db_file'):
                db_file_name = os.path.basename(current_db.db_file)

            logging.info(f"커밋을 위해 DB 닫기 시작: {current_db_name} ({db_file_name})")

            # 버튼 텍스트 업데이트
            self.commit_push_button.setText("DB 닫는 중...")
            self.commit_push_button.setEnabled(False)
            QApplication.processEvents()

            # DB 닫기 실행
            if self.db_manager.remove_database(current_db_name):
                # 부모 윈도우의 DB 참조 업데이트
                try:
                    if hasattr(self.parent(), 'update_current_db_references'):
                        self.parent().update_current_db_references()
                    if hasattr(self.parent(), 'update_db_combo'):
                        self.parent().update_db_combo()
                    if hasattr(self.parent(), 'load_files'):
                        self.parent().load_files()
                except Exception as update_error:
                    logging.warning(f"DB 닫기 후 UI 업데이트 중 경고: {update_error}")

                logging.info(f"DB 닫기 완료: {current_db_name}")

                # 파일 시스템 동기화 대기
                QApplication.processEvents()
                import time
                time.sleep(0.5)

                return True
            else:
                logging.error(f"DB 닫기 실패: {current_db_name}")
                QMessageBox.warning(self, "DB 닫기 실패",
                                  f"'{current_db_name}' 데이터베이스를 닫을 수 없습니다.")
                return False

        except Exception as e:
            logging.error(f"DB 닫기 중 오류: {e}")
            QMessageBox.critical(self, "DB 닫기 오류",
                               f"DB 닫기 중 오류가 발생했습니다:\n{str(e)}")
            return False
        finally:
            # 버튼 복원
            self.commit_push_button.setText("커밋 & 푸시")
            self.commit_push_button.setEnabled(True)

    def check_new_files_after_db_close(self):
        """DB 닫기 후 새로운 변경사항 확인"""
        try:
            logging.info("DB 닫기 후 새로운 변경사항 확인 시작")

            # 버튼 텍스트 업데이트
            self.commit_push_button.setText("새 파일 확인 중...")
            QApplication.processEvents()

            # 새로운 Git 상태 가져오기
            self.files_after_db_close = self.git_manager.get_changed_files(use_enhanced_encoding=True)

            # 새로 생긴 파일들 찾기
            files_after_names = [f['filename'] for f in self.files_after_db_close]
            self.new_files_from_db_close = []

            for filename in files_after_names:
                if filename not in self.files_before_db_close:
                    # 새로 생긴 파일 찾기
                    file_info = next((f for f in self.files_after_db_close if f['filename'] == filename), None)
                    if file_info:
                        self.new_files_from_db_close.append(file_info)

            logging.info(f"DB 닫기로 인해 새로 생긴 파일: {len(self.new_files_from_db_close)}개")
            for new_file in self.new_files_from_db_close:
                logging.info(f"  - 새 파일: {new_file['filename']} ({new_file['change_type']})")

            # 새로 생긴 파일들을 선택된 파일 목록에 자동 추가
            for new_file in self.new_files_from_db_close:
                if new_file['filename'] not in self.selected_files:
                    self.selected_files.append(new_file['filename'])

            # 전체 변경된 파일 목록 업데이트
            self.changed_files = self.files_after_db_close

            # UI 새로고침
            self.update_file_list()

        except Exception as e:
            logging.error(f"새 파일 확인 중 오류: {e}")
        finally:
            # 버튼 복원
            self.commit_push_button.setText("커밋 & 푸시")

    def show_enhanced_commit_confirmation_dialog(self, commit_message: str) -> int:
        """향상된 커밋 확인 다이얼로그 (새로 생긴 파일 강조 표시)"""
        from PySide6.QtWidgets import QScrollArea

        # 커스텀 다이얼로그 생성
        dialog = QDialog(self)
        dialog.setWindowTitle("커밋 & 푸시 확인")
        dialog.setModal(True)
        dialog.setStyleSheet("""
            QDialog {
                background-color: #ffffff;
            }
        """)

        # 컴팩트한 크기로 설정
        dialog.resize(500, 380)

        # 메인 레이아웃
        layout = QVBoxLayout(dialog)
        layout.setSpacing(8)
        layout.setContentsMargins(12, 12, 12, 12)

        # 헤더 정보를 한 줄로 간단하게
        header_info = f"커밋 메시지: {commit_message}"
        total_files = len(self.selected_files)
        new_files_count = len(self.new_files_from_db_close)

        if new_files_count > 0:
            header_info += f" | 총 {total_files}개 파일 (새로 생긴 {new_files_count}개 포함)"
        else:
            header_info += f" | 총 {total_files}개 파일"

        header_label = QLabel(header_info)
        header_label.setStyleSheet("""
            QLabel {
                font-size: 11px;
                color: #666;
                background-color: #f8f8f8;
                padding: 6px;
                border-radius: 3px;
                margin-bottom: 6px;
            }
        """)
        header_label.setWordWrap(True)
        layout.addWidget(header_label)

        # 스크롤 영역 생성
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setMinimumHeight(200)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: 1px solid #ddd;
                border-radius: 3px;
                background-color: #ffffff;
            }
            QScrollBar:vertical {
                background-color: #f5f5f5;
                width: 8px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background-color: #ccc;
                border-radius: 4px;
                min-height: 12px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #999;
            }
        """)

        # 파일 목록 위젯
        file_list_widget = QWidget()
        file_list_widget.setStyleSheet("""
            QWidget {
                background-color: #ffffff;
            }
        """)
        file_list_layout = QVBoxLayout(file_list_widget)
        file_list_layout.setContentsMargins(8, 6, 8, 6)
        file_list_layout.setSpacing(3)

        # 새로 생긴 파일들
        if self.new_files_from_db_close:
            # 섹션 헤더
            new_header = QLabel("새로 생긴 파일")
            new_header.setStyleSheet("""
                QLabel {
                    font-size: 11px;
                    font-weight: bold;
                    color: #000;
                    margin: 2px 0;
                    padding: 2px 0;
                    border-bottom: 1px solid #28a745;
                }
            """)
            file_list_layout.addWidget(new_header)

            # 파일 목록
            for file_info in self.new_files_from_db_close:
                if file_info['filename'] in self.selected_files:
                    file_item = QLabel(f"{file_info['change_type']} • {file_info['filename']}")
                    file_item.setStyleSheet("""
                        QLabel {
                            font-size: 10px;
                            color: #000;
                            background-color: #f0f8f0;
                            padding: 3px 6px;
                            border-radius: 2px;
                            border-left: 3px solid #28a745;
                            margin-bottom: 1px;
                        }
                    """)
                    file_list_layout.addWidget(file_item)

        # 기존 파일들
        existing_selected_files = [f for f in self.selected_files
                                 if f not in [nf['filename'] for nf in self.new_files_from_db_close]]

        if existing_selected_files:
            # 섹션 헤더
            existing_header = QLabel("변경된 파일")
            existing_header.setStyleSheet("""
                QLabel {
                    font-size: 11px;
                    font-weight: bold;
                    color: #000;
                    margin: 6px 0 2px 0;
                    padding: 2px 0;
                    border-bottom: 1px solid #ccc;
                }
            """)
            file_list_layout.addWidget(existing_header)

            # 파일 목록
            for filename in existing_selected_files:
                file_info = next((f for f in self.changed_files if f['filename'] == filename), None)
                if file_info:
                    file_item = QLabel(f"{file_info['change_type']} • {filename}")
                    file_item.setStyleSheet("""
                        QLabel {
                            font-size: 10px;
                            color: #000;
                            background-color: #f8f8f8;
                            padding: 3px 6px;
                            border-radius: 2px;
                            border-left: 3px solid #007bff;
                            margin-bottom: 1px;
                        }
                    """)
                    file_list_layout.addWidget(file_item)

        scroll_area.setWidget(file_list_widget)
        layout.addWidget(scroll_area)



        # 버튼 영역
        button_layout = QHBoxLayout()
        button_layout.setContentsMargins(0, 8, 0, 0)
        button_layout.setSpacing(8)

        # 취소 버튼
        cancel_button = QPushButton("취소")
        cancel_button.clicked.connect(dialog.reject)
        cancel_button.setStyleSheet("""
            QPushButton {
                padding: 5px 12px;
                font-size: 11px;
                background-color: #f5f5f5;
                color: #666;
                border: 1px solid #ddd;
                border-radius: 3px;
                min-width: 60px;
            }
            QPushButton:hover {
                background-color: #e8e8e8;
            }
        """)

        # 확인 버튼
        confirm_button = QPushButton("커밋 & 푸시")
        confirm_button.clicked.connect(dialog.accept)
        confirm_button.setStyleSheet("""
            QPushButton {
                padding: 5px 12px;
                font-size: 11px;
                font-weight: bold;
                background-color: #007bff;
                color: white;
                border: none;
                border-radius: 3px;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #0056b3;
            }
        """)
        confirm_button.setDefault(True)

        button_layout.addStretch()
        button_layout.addWidget(cancel_button)
        button_layout.addWidget(confirm_button)
        layout.addLayout(button_layout)

        # 다이얼로그 실행
        result = dialog.exec()
        return QMessageBox.Yes if result == QDialog.Accepted else QMessageBox.No


