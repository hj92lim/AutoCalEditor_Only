#!/usr/bin/env python3
"""
UI 성능 테스트 스크립트
행/열 삽입 시 UI 응답성 테스트
"""

import sys
import logging
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, QLabel
from PySide6.QtCore import QTimer
from ui.ui_components import VirtualizedGridModel, ExcelGridView
from data_manager.db_handler_v2 import DatabaseHandler

class PerformanceTestWindow(QMainWindow):
    """성능 테스트용 윈도우"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("UI 성능 테스트 - 행/열 삽입")
        self.setGeometry(100, 100, 1200, 800)
        
        # 중앙 위젯 설정
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # 상태 라벨
        self.status_label = QLabel("테스트 준비 중...")
        layout.addWidget(self.status_label)
        
        # 테스트 버튼들
        self.test_row_insert_btn = QPushButton("행 삽입 테스트 (10개)")
        self.test_row_insert_btn.clicked.connect(self.test_row_insertion)
        layout.addWidget(self.test_row_insert_btn)
        
        self.test_col_insert_btn = QPushButton("열 삽입 테스트 (5개)")
        self.test_col_insert_btn.clicked.connect(self.test_column_insertion)
        layout.addWidget(self.test_col_insert_btn)
        
        # 그리드 뷰
        self.grid_view = ExcelGridView()
        layout.addWidget(self.grid_view)
        
        # DB 및 모델 초기화
        self.init_database()
        
    def init_database(self):
        """테스트용 데이터베이스 초기화"""
        try:
            # 테스트 DB 파일 경로
            test_db_path = "test_performance.db"
            
            # DB 핸들러 생성
            self.db = DatabaseHandler(test_db_path)
            
            # 그리드 뷰에 DB 핸들러 설정
            self.grid_view.set_db_handler(self.db)
            
            # 테스트 시트 생성 또는 로드
            sheets = self.db.get_sheets()
            if not sheets:
                # 새 시트 생성
                sheet_id = self.db.create_sheet("테스트시트", "test_file.xlsx")
                
                # 테스트 데이터 추가 (100x50 크기)
                test_data = []
                for row in range(100):
                    for col in range(50):
                        value = f"R{row}C{col}"
                        test_data.append((row, col, value))
                
                self.db.update_cells(sheet_id, test_data)
                logging.info(f"테스트 데이터 생성 완료: {len(test_data)}개 셀")
            else:
                sheet_id = sheets[0]['id']
            
            # 시트 로드
            self.grid_view.load_sheet(sheet_id)
            self.sheet_id = sheet_id
            
            self.status_label.setText(f"테스트 준비 완료 - 시트 ID: {sheet_id}")
            
        except Exception as e:
            logging.error(f"데이터베이스 초기화 오류: {e}")
            self.status_label.setText(f"오류: {e}")
    
    def test_row_insertion(self):
        """행 삽입 성능 테스트"""
        if not hasattr(self, 'sheet_id'):
            self.status_label.setText("시트가 로드되지 않음")
            return
            
        self.status_label.setText("행 삽입 테스트 시작...")
        self.test_row_insert_btn.setEnabled(False)
        
        # 타이머로 지연 실행하여 UI 업데이트 확인
        QTimer.singleShot(100, self._perform_row_insertion)
    
    def _perform_row_insertion(self):
        """실제 행 삽입 수행"""
        try:
            import time
            start_time = time.time()
            
            # 10개 행을 5번째 위치에 삽입
            success = self.grid_view.model.insertRows(5, 10)
            
            end_time = time.time()
            elapsed = end_time - start_time
            
            if success:
                self.status_label.setText(f"행 삽입 완료 - 소요시간: {elapsed:.3f}초")
            else:
                self.status_label.setText("행 삽입 실패")
                
        except Exception as e:
            logging.error(f"행 삽입 테스트 오류: {e}")
            self.status_label.setText(f"행 삽입 오류: {e}")
        finally:
            self.test_row_insert_btn.setEnabled(True)
    
    def test_column_insertion(self):
        """열 삽입 성능 테스트"""
        if not hasattr(self, 'sheet_id'):
            self.status_label.setText("시트가 로드되지 않음")
            return
            
        self.status_label.setText("열 삽입 테스트 시작...")
        self.test_col_insert_btn.setEnabled(False)
        
        # 타이머로 지연 실행하여 UI 업데이트 확인
        QTimer.singleShot(100, self._perform_column_insertion)
    
    def _perform_column_insertion(self):
        """실제 열 삽입 수행"""
        try:
            import time
            start_time = time.time()
            
            # 5개 열을 3번째 위치에 삽입
            success = self.grid_view.model.insertColumns(3, 5)
            
            end_time = time.time()
            elapsed = end_time - start_time
            
            if success:
                self.status_label.setText(f"열 삽입 완료 - 소요시간: {elapsed:.3f}초")
            else:
                self.status_label.setText("열 삽입 실패")
                
        except Exception as e:
            logging.error(f"열 삽입 테스트 오류: {e}")
            self.status_label.setText(f"열 삽입 오류: {e}")
        finally:
            self.test_col_insert_btn.setEnabled(True)

def main():
    """메인 함수"""
    # 로깅 설정
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s | %(levelname)-8s | %(name)-20s | %(funcName)-15s:%(lineno)-4d | %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('test_performance.log', encoding='utf-8')
        ]
    )
    
    # Qt 애플리케이션 생성
    app = QApplication(sys.argv)
    
    # 테스트 윈도우 생성 및 표시
    window = PerformanceTestWindow()
    window.show()
    
    # 이벤트 루프 실행
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
