import logging
import os
from typing import Any, Dict, List, Optional

from data_manager.db_handler_v2 import DBHandlerV2


class DBManager:
    """
    다중 SQLite 데이터베이스 연결을 관리하는 클래스입니다.

    애플리케이션 내에서 여러 데이터베이스 파일을 동시에 열고,
    현재 활성화된 데이터베이스를 전환하며, 각 데이터베이스에 대한 작업을
    `DBHandlerV2`를 통해 위임 실행합니다.

    Attributes:
        databases (Dict[str, DBHandlerV2]): 관리 중인 데이터베이스 핸들러들을 저장하는 딕셔너리.
                                             키는 데이터베이스 이름, 값은 `DBHandlerV2` 인스턴스입니다.
        current_db_name (Optional[str]): 현재 활성화된 데이터베이스의 이름.
    """

    def __init__(self):
        """
        DBManager를 초기화합니다.

        `databases` 딕셔너리와 `current_db_name`을 초기 상태로 설정합니다.
        """
        self.databases: Dict[str, DBHandlerV2] = {}
        self.current_db_name: Optional[str] = None

    def _generate_db_name(self, db_file_path: str) -> str:
        """
        주어진 데이터베이스 파일 경로로부터 고유한 데이터베이스 이름을 생성합니다.

        파일 경로에서 기본 이름을 추출하고, 만약 해당 이름이 이미 `self.databases`에 존재하면
        이름 뒤에 `_1`, `_2` 등을 붙여 고유성을 보장합니다.

        Args:
            db_file_path (str): 데이터베이스 파일의 전체 경로.

        Returns:
            str: 생성된 고유한 데이터베이스 이름.
        """
        original_name = os.path.splitext(os.path.basename(db_file_path))[0]
        db_name = original_name
        counter = 1
        while db_name in self.databases:
            db_name = f"{original_name}_{counter}"
            counter += 1
        return db_name

    def _add_db_handler(
        self, db_name: str, db_handler: DBHandlerV2, replace_existing: bool
    ):
        """
        데이터베이스 핸들러를 관리 목록에 추가하고, 필요한 경우 현재 활성 DB로 설정합니다.

        Args:
            db_name (str): 추가할 데이터베이스의 고유 이름.
            db_handler (DBHandlerV2): 추가할 데이터베이스 핸들러 인스턴스.
            replace_existing (bool): True인 경우, 이 DB를 유일한 활성 DB로 설정합니다.
                                     기존 `current_db_name`이 없어도 활성 DB로 설정됩니다.
        """
        self.databases[db_name] = db_handler
        if self.current_db_name is None or replace_existing:
            self.current_db_name = db_name

    def add_database(self, db_file_path: str, replace_existing: bool = False) -> str:
        """
        기존 SQLite 데이터베이스 파일을 시스템에 추가하고 연결합니다.

        파일이 존재하지 않으면 `FileNotFoundError`를 발생시킵니다.
        `replace_existing` 플래그가 True이면, 기존에 열려있던 모든 DB 연결을 닫고
        새로 추가하는 DB만 관리 목록에 유지하며 활성 DB로 설정합니다.

        Args:
            db_file_path (str): 추가할 데이터베이스 파일의 경로.
            replace_existing (bool): 기존 DB 연결들을 대체할지 여부. 기본값은 False.

        Returns:
            str: 성공적으로 추가된 데이터베이스의 내부 관리 이름.

        Raises:
            FileNotFoundError: `db_file_path`에 해당하는 파일이 존재하지 않을 경우.
            RuntimeError: 데이터베이스 연결 또는 내부 처리 중 오류 발생 시.
        """
        if not os.path.exists(db_file_path):
            raise FileNotFoundError(
                f"데이터베이스 파일을 찾을 수 없습니다: {db_file_path}"
            )

        if replace_existing:
            self.disconnect_all()

        db_name = self._generate_db_name(db_file_path)

        try:
            logging.info(f"V2 데이터베이스 연결 시도: {db_file_path}")
            db_handler = DBHandlerV2(db_file_path)
            self._add_db_handler(db_name, db_handler, replace_existing)
            logging.info(f"데이터베이스 추가 완료: {db_name} (경로: {db_file_path})")
            return db_name
        except Exception as e:
            logging.error(f"데이터베이스 연결 실패: {db_file_path}, 오류: {e}", exc_info=True)
            raise RuntimeError(f"데이터베이스 연결 실패: {db_file_path}, 오류: {e}")

    def create_and_add_database(
        self, db_file_path: str, replace_existing: bool = False
    ) -> str:
        """
        새로운 SQLite 데이터베이스 파일을 지정된 경로에 생성하고 시스템에 추가합니다.

        파일 경로의 디렉토리가 존재하지 않으면 생성합니다.
        `replace_existing` 플래그가 True이면, 기존 DB들을 모두 닫고 이 DB만 유지합니다.

        Args:
            db_file_path (str): 생성하고 추가할 데이터베이스 파일의 경로.
            replace_existing (bool): 기존 DB 연결들을 대체할지 여부. 기본값은 False.

        Returns:
            str: 성공적으로 생성 및 추가된 데이터베이스의 내부 관리 이름.

        Raises:
            RuntimeError: 데이터베이스 생성 또는 내부 처리 중 오류 발생 시.
        """
        if replace_existing:
            self.disconnect_all()

        db_dir = os.path.dirname(db_file_path)
        if db_dir and not os.path.exists(db_dir):
            try:
                os.makedirs(db_dir, exist_ok=True)
                logging.info(f"디렉토리 생성 완료: {db_dir}")
            except OSError as e:
                logging.error(f"디렉토리 생성 실패: {db_dir}, 오류: {e}", exc_info=True)
                raise RuntimeError(f"데이터베이스 경로 디렉토리 생성 실패: {db_dir}, 오류: {e}")


        db_name = self._generate_db_name(db_file_path)

        try:
            logging.info(f"V2 새 데이터베이스 생성 시도: {db_file_path}")
            db_handler = DBHandlerV2(db_file_path)  # 파일이 없으면 자동 생성
            self._add_db_handler(db_name, db_handler, replace_existing)
            logging.info(f"새 데이터베이스 생성 및 추가 완료: {db_name} (경로: {db_file_path})")
            return db_name
        except Exception as e:
            logging.error(f"데이터베이스 생성 실패: {db_file_path}, 오류: {e}", exc_info=True)
            raise RuntimeError(f"데이터베이스 생성 실패: {db_file_path}, 오류: {e}")

    def add_multiple_databases(self, db_file_paths: List[str]) -> List[str]:
        """
        여러 데이터베이스 파일을 동시에 시스템에 추가합니다.

        각 파일에 대해 `add_database`를 호출하며, `replace_existing`은 False로 설정됩니다.
        개별 파일 추가 실패 시 해당 파일은 건너뛰고 다음 파일을 처리합니다.

        Args:
            db_file_paths (List[str]): 추가할 데이터베이스 파일 경로들의 리스트.

        Returns:
            List[str]: 성공적으로 추가된 데이터베이스들의 내부 관리 이름 리스트.
        """
        added_names = []
        for db_path in db_file_paths:
            try:
                db_name = self.add_database(db_path, replace_existing=False)
                added_names.append(db_name)
            except Exception as e: # add_database에서 이미 로깅 및 RuntimeError 발생 가능성 있음
                logging.error(f"다중 DB 추가 중 '{db_path}' 데이터베이스 추가 실패: {e}", exc_info=True)
                # 실패한 DB는 건너뛰고 계속 진행
                continue
        return added_names

    def switch_database(self, db_name: str) -> bool:
        """
        현재 활성화된 데이터베이스를 지정된 이름의 데이터베이스로 전환합니다.

        Args:
            db_name (str): 전환할 대상 데이터베이스의 내부 관리 이름.

        Returns:
            bool: 전환에 성공하면 True, 해당 이름의 DB가 없으면 False.
        """
        if db_name not in self.databases:
            logging.warning(f"존재하지 않는 데이터베이스로 전환 시도: {db_name}")
            return False

        self.current_db_name = db_name
        logging.info(f"활성 데이터베이스 변경: {db_name}")
        return True

    def remove_database(self, db_name: str) -> bool:
        """
        지정된 이름의 데이터베이스를 관리 목록에서 제거하고 연결을 해제합니다.

        만약 제거되는 데이터베이스가 현재 활성 DB였다면,
        남아있는 다른 DB 중 하나를 새로운 활성 DB로 설정합니다.
        남아있는 DB가 없으면 활성 DB는 None으로 설정됩니다.

        Args:
            db_name (str): 제거할 데이터베이스의 내부 관리 이름.

        Returns:
            bool: 제거에 성공하면 True, 해당 이름의 DB가 없으면 False.

        Raises:
            RuntimeError: 데이터베이스 연결 해제 또는 내부 처리 중 오류 발생 시.
        """
        if db_name not in self.databases:
            logging.warning(f"존재하지 않는 데이터베이스 제거 시도: {db_name}")
            return False

        try:
            db_handler = self.databases.pop(db_name, None)
            if db_handler:
                db_handler.disconnect()
                logging.info(f"데이터베이스 연결 해제 및 제거 완료: {db_name}")

            if self.current_db_name == db_name:
                if self.databases:
                    self.current_db_name = next(iter(self.databases.keys()))
                    logging.info(
                        f"활성 데이터베이스 자동 전환: {self.current_db_name}"
                    )
                else:
                    self.current_db_name = None
                    logging.info("남아있는 데이터베이스가 없어 활성 DB가 없습니다.")
            return True
        except Exception as e:
            logging.error(f"데이터베이스 제거 실패: {db_name}, 오류: {e}", exc_info=True)
            raise RuntimeError(f"데이터베이스 제거 실패: {db_name}, 오류: {e}")

    def get_current_db(self) -> Optional[DBHandlerV2]:
        """
        현재 활성화된 데이터베이스의 `DBHandlerV2` 인스턴스를 반환합니다.

        Returns:
            Optional[DBHandlerV2]: 현재 활성 DB 핸들러. 활성 DB가 없으면 None.
        """
        if self.current_db_name and self.current_db_name in self.databases:
            return self.databases[self.current_db_name]
        logging.debug("현재 활성 데이터베이스가 없거나, current_db_name이 유효하지 않습니다.")
        return None

    def get_database(self, db_name: str) -> Optional[DBHandlerV2]:
        """
        지정된 이름의 데이터베이스 핸들러를 반환합니다.

        Args:
            db_name (str): 가져올 데이터베이스의 내부 관리 이름.

        Returns:
            Optional[DBHandlerV2]: 해당 DB 핸들러. 없으면 None.
        """
        logging.debug(f"데이터베이스 핸들러 요청: {db_name}")
        return self.databases.get(db_name)

    def get_database_names(self) -> List[str]:
        """
        현재 관리 중인 모든 데이터베이스의 이름 목록을 반환합니다.

        Returns:
            List[str]: 데이터베이스 이름 리스트.
        """
        return list(self.databases.keys())

    def get_database_count(self) -> int:
        """
        현재 관리 중인 데이터베이스의 개수를 반환합니다.

        Returns:
            int: 열려있는 데이터베이스의 수.
        """
        return len(self.databases)

    def get_database_info(self) -> List[Dict[str, Any]]:
        """
        관리 중인 모든 데이터베이스의 상세 정보를 리스트 형태로 반환합니다.

        각 정보에는 DB 이름, 파일 경로, 현재 활성 DB 여부가 포함됩니다.

        Returns:
            List[Dict[str, Any]]: 각 DB의 정보를 담은 딕셔너리 리스트.
                                 예: [{'name': 'db1', 'path': '/path/to/db1.db', 'is_current': True}, ...]
        """
        info_list = []
        for db_name, db_handler in self.databases.items():
            info_list.append(
                {
                    "name": db_name,
                    "path": db_handler.db_file if db_handler.db_file else "N/A",
                    "is_current": db_name == self.current_db_name,
                }
            )
        return info_list

    def disconnect_all(self):
        """
        관리 중인 모든 데이터베이스의 연결을 해제하고, 관리 목록을 비웁니다.
        """
        for db_name, db_handler in list(self.databases.items()): # Iterate over a copy for safe removal
            try:
                db_handler.disconnect()
                logging.info(f"데이터베이스 연결 해제: {db_name}")
            except Exception as e:
                logging.error(f"{db_name} 데이터베이스 연결 해제 실패: {e}", exc_info=True)

        self.databases.clear()
        self.current_db_name = None
        logging.info("모든 데이터베이스 연결 해제 및 목록 초기화 완료.")

    def has_databases(self) -> bool:
        """
        현재 관리 중인 데이터베이스가 하나 이상 있는지 확인합니다.

        Returns:
            bool: 데이터베이스가 하나 이상 열려있으면 True, 아니면 False.
        """
        return bool(self.databases)

    def get_all_sheets_info(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        관리 중인 모든 데이터베이스 각각의 시트 정보를 가져옵니다.

        Returns:
            Dict[str, List[Dict[str, Any]]]: 데이터베이스 이름을 키로 하고,
                                             해당 DB의 시트 정보 리스트를 값으로 하는 딕셔너리.
                                             각 시트 정보는 `DBHandlerV2.get_sheets()`가 반환하는 형식입니다.
                                             오류 발생 시 해당 DB의 시트 정보는 빈 리스트로 처리될 수 있습니다.
        """
        all_sheets: Dict[str, List[Dict[str, Any]]] = {}
        for db_name, db_handler in self.databases.items():
            try:
                sheets_list = db_handler.get_sheets()
                all_sheets[db_name] = sheets_list
            except Exception as e:
                logging.error(f"{db_name}에서 시트 정보를 가져오는데 실패했습니다: {e}", exc_info=True)
                # 오류 발생 시 해당 DB는 빈 시트 목록으로 처리 (기존 로직 유지)
                all_sheets[db_name] = []
        return all_sheets
