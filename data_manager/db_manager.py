import os
import logging
from typing import Dict, List, Optional, Any
from data_manager.db_handler_v2 import DBHandlerV2


class DBManager:
    """다중 데이터베이스 관리 클래스"""

    def __init__(self):
        """DBManager 초기화"""
        self.databases: Dict[str, DBHandlerV2] = {}  # {db_name: DBHandlerV2}
        self.current_db_name: Optional[str] = None

    def add_database(self, db_file_path: str, replace_existing: bool = False) -> str:
        """
        새 V2 데이터베이스 추가

        Args:
            db_file_path: DB 파일 경로
            replace_existing: True면 기존 DB들을 모두 닫고 새 DB만 유지

        Returns:
            추가된 DB의 이름
        """
        if not os.path.exists(db_file_path):
            raise FileNotFoundError(f"데이터베이스 파일을 찾을 수 없습니다: {db_file_path}")

        # 기존 DB 대체 모드
        if replace_existing:
            self.disconnect_all()

        # DB 이름 생성 (파일명에서 확장자 제거)
        original_name = os.path.splitext(os.path.basename(db_file_path))[0]
        db_name = original_name

        # 중복 이름 처리
        counter = 1
        while db_name in self.databases:
            db_name = f"{original_name}_{counter}"
            counter += 1

        try:
            # V2 DB 핸들러로 직접 연결
            logging.info(f"V2 데이터베이스 연결: {db_file_path}")
            db_handler = DBHandlerV2(db_file_path)
            self.databases[db_name] = db_handler

            # 첫 번째 DB이거나 대체 모드면 현재 DB로 설정
            if self.current_db_name is None or replace_existing:
                self.current_db_name = db_name

            logging.info(f"Database added: {db_name} ({db_file_path})")
            return db_name

        except Exception as e:
            logging.error(f"Failed to add database {db_file_path}: {e}")
            raise Exception(f"데이터베이스 연결 실패: {e}")

    def create_and_add_database(self, db_file_path: str, replace_existing: bool = False) -> str:
        """
        새 데이터베이스 파일을 생성하고 추가 (Excel 가져오기용)

        Args:
            db_file_path: 생성할 DB 파일 경로
            replace_existing: True면 기존 DB들을 모두 닫고 새 DB만 유지

        Returns:
            추가된 DB의 이름
        """
        # 기존 DB 대체 모드
        if replace_existing:
            self.disconnect_all()

        # 디렉토리가 존재하지 않으면 생성
        db_dir = os.path.dirname(db_file_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)
            logging.info(f"Created directory: {db_dir}")

        # DB 이름 생성 (파일명에서 확장자 제거)
        original_name = os.path.splitext(os.path.basename(db_file_path))[0]
        db_name = original_name

        # 중복 이름 처리
        counter = 1
        while db_name in self.databases:
            db_name = f"{original_name}_{counter}"
            counter += 1

        try:
            # V2 DB 핸들러로 새 DB 생성 및 연결
            logging.info(f"V2 새 데이터베이스 생성: {db_file_path}")
            db_handler = DBHandlerV2(db_file_path)  # DBHandlerV2는 파일이 없으면 자동 생성
            self.databases[db_name] = db_handler

            # 첫 번째 DB이거나 대체 모드면 현재 DB로 설정
            if self.current_db_name is None or replace_existing:
                self.current_db_name = db_name

            logging.info(f"New database created and added: {db_name} ({db_file_path})")
            return db_name

        except Exception as e:
            logging.error(f"Failed to create database {db_file_path}: {e}")
            raise Exception(f"데이터베이스 생성 실패: {e}")

    def add_multiple_databases(self, db_file_paths: List[str]) -> List[str]:
        """
        여러 데이터베이스를 동시에 추가

        Args:
            db_file_paths: DB 파일 경로 목록

        Returns:
            추가된 DB 이름 목록
        """
        added_names = []
        for db_path in db_file_paths:
            try:
                db_name = self.add_database(db_path, replace_existing=False)
                added_names.append(db_name)
            except Exception as e:
                logging.error(f"Failed to add database {db_path}: {e}")
                # 실패한 DB는 건너뛰고 계속 진행
                continue

        return added_names

    def remove_database(self, db_name: str) -> bool:
        """
        데이터베이스 제거

        Args:
            db_name: 제거할 DB 이름

        Returns:
            성공 여부
        """
        if db_name not in self.databases:
            return False

        try:
            # DB 연결 해제
            self.databases[db_name].disconnect()
            del self.databases[db_name]

            # 현재 DB가 제거된 경우 다른 DB로 전환
            if self.current_db_name == db_name:
                if self.databases:
                    self.current_db_name = next(iter(self.databases.keys()))
                else:
                    self.current_db_name = None

            logging.info(f"Database removed: {db_name}")
            return True

        except Exception as e:
            logging.error(f"Failed to remove database {db_name}: {e}")
            return False

    def switch_database(self, db_name: str) -> bool:
        """
        현재 활성 데이터베이스 전환

        Args:
            db_name: 전환할 DB 이름

        Returns:
            성공 여부
        """
        if db_name not in self.databases:
            return False

        self.current_db_name = db_name
        logging.info(f"Switched to database: {db_name}")
        return True

    def remove_database(self, db_name: str) -> bool:
        """
        데이터베이스 제거 및 연결 해제

        Args:
            db_name: 제거할 DB 이름

        Returns:
            성공 여부
        """
        if db_name not in self.databases:
            return False

        try:
            # DB 연결 해제
            db_handler = self.databases[db_name]
            if db_handler:
                db_handler.disconnect()
                logging.info(f"Database disconnected: {db_name}")

            # DB 목록에서 제거
            del self.databases[db_name]

            # 현재 활성 DB가 제거된 경우 다른 DB로 전환
            if self.current_db_name == db_name:
                if self.databases:
                    # 남은 DB 중 첫 번째를 활성 DB로 설정
                    self.current_db_name = next(iter(self.databases.keys()))
                    logging.info(f"Switched to new active database: {self.current_db_name}")
                else:
                    # 모든 DB가 제거된 경우
                    self.current_db_name = None
                    logging.info("No databases remaining")

            logging.info(f"Database removed: {db_name}")
            return True

        except Exception as e:
            logging.error(f"Failed to remove database {db_name}: {e}")
            return False

    def get_current_db(self) -> Optional[DBHandlerV2]:
        """현재 활성 데이터베이스 핸들러 반환"""
        if self.current_db_name and self.current_db_name in self.databases:
            return self.databases[self.current_db_name]
        return None

    def get_database(self, db_name: str) -> Optional[DBHandlerV2]:
        """특정 데이터베이스 핸들러 반환"""
        return self.databases.get(db_name)

    def get_database_names(self) -> List[str]:
        """모든 데이터베이스 이름 목록 반환"""
        return list(self.databases.keys())

    def get_database_count(self) -> int:
        """열린 데이터베이스 개수 반환"""
        return len(self.databases)

    def get_database_info(self) -> List[Dict[str, Any]]:
        """
        모든 데이터베이스 정보 반환

        Returns:
            DB 정보 리스트 [{name, path, is_current}, ...]
        """
        info_list = []
        for db_name, db_handler in self.databases.items():
            info_list.append({
                'name': db_name,
                'path': db_handler.db_file,
                'is_current': db_name == self.current_db_name
            })
        return info_list

    def disconnect_all(self):
        """모든 데이터베이스 연결 해제"""
        for db_name, db_handler in self.databases.items():
            try:
                db_handler.disconnect()
                logging.info(f"Database disconnected: {db_name}")
            except Exception as e:
                logging.error(f"Failed to disconnect database {db_name}: {e}")

        self.databases.clear()
        self.current_db_name = None
        logging.info("All databases disconnected")

    def has_databases(self) -> bool:
        """데이터베이스가 하나 이상 열려있는지 확인"""
        return len(self.databases) > 0

    def get_all_sheets_info(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        모든 DB의 시트 정보 반환 (V2 방식)

        Returns:
            {db_name: [sheet_info, ...], ...}
        """
        all_sheets = {}

        for db_name, db_handler in self.databases.items():
            try:
                # V2 방식: 직접 모든 시트 조회
                sheets_list = db_handler.get_sheets()
                all_sheets[db_name] = sheets_list

            except Exception as e:
                logging.error(f"Failed to get sheets from database {db_name}: {e}")
                all_sheets[db_name] = []

        return all_sheets

