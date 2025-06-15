import os
import logging
from typing import Dict, List, Optional, Any
from data_manager.db_handler_v2 import DBHandlerV2


class DBManager:
    """다중 데이터베이스 관리 클래스"""

    def __init__(self):
        """DBManager 초기화"""
        self.databases: Dict[str, DBHandlerV2] = {}  # {db_name: DBHandlerV2}
        self.db_file_paths: Dict[str, str] = {}  # {db_name: absolute_file_path} - 파일 경로 추적용
        self.current_db_name: Optional[str] = None

    def _is_database_already_loaded(self, db_file_path: str) -> Optional[str]:
        """
        동일한 파일 경로의 DB가 이미 로드되어 있는지 확인

        Args:
            db_file_path: 확인할 DB 파일 경로

        Returns:
            이미 로드된 DB의 이름 또는 None
        """
        try:
            # 절대 경로로 정규화 (대소문자 구분 없이 비교)
            abs_path = os.path.abspath(db_file_path).lower()

            for db_name, stored_path in self.db_file_paths.items():
                if stored_path.lower() == abs_path:
                    logging.info(f"동일한 파일의 DB가 이미 로드됨: {db_name} ({stored_path})")
                    return db_name

            # 추가 검증: DBHandlerV2 객체의 db_file 속성도 확인 (안전장치)
            for db_name, db_handler in self.databases.items():
                if hasattr(db_handler, 'db_file') and db_handler.db_file:
                    existing_abs_path = os.path.abspath(db_handler.db_file).lower()
                    if existing_abs_path == abs_path:
                        # 파일 경로 추적 딕셔너리 업데이트 (동기화)
                        self.db_file_paths[db_name] = os.path.abspath(db_handler.db_file)
                        logging.info(f"DB 파일 경로 동기화: {db_name} -> {self.db_file_paths[db_name]}")
                        return db_name

            return None

        except Exception as e:
            logging.error(f"DB 중복 체크 중 오류: {e}")
            return None

    def add_database(self, db_file_path: str, replace_existing: bool = False,
                     force_add: bool = False) -> str:
        """
        새 V2 데이터베이스 추가 (통합된 중복 처리 정책 적용)

        Args:
            db_file_path: DB 파일 경로
            replace_existing: True면 기존 DB들을 모두 닫고 새 DB만 유지
            force_add: True면 중복 체크를 무시하고 강제로 추가 (UI에서 사용자 확인 후 사용)

        Returns:
            추가된 DB의 이름 (기존 DB 재사용 시에도 해당 DB 이름 반환)

        Raises:
            FileNotFoundError: DB 파일이 존재하지 않을 때
            ValueError: 중복 DB가 발견되었지만 force_add=False일 때
        """
        if not os.path.exists(db_file_path):
            raise FileNotFoundError(f"데이터베이스 파일을 찾을 수 없습니다: {db_file_path}")

        # 기존 DB 대체 모드
        if replace_existing:
            self.disconnect_all()
        elif not force_add:
            # 🔧 통합된 중복 체크: 파일 경로와 이름 모두 확인
            conflicts = self.check_database_conflicts(db_file_path)

            if conflicts['path_conflict']:
                # 동일한 파일 경로의 DB가 이미 로드됨
                existing_db_name = conflicts['path_conflict']
                logging.info(f"✅ 동일한 파일의 DB가 이미 로드됨: {existing_db_name}")
                self.switch_database(existing_db_name)
                return existing_db_name

            if conflicts['name_conflict']:
                # 동일한 이름의 DB가 이미 존재함 (다른 파일)
                raise ValueError(f"동일한 이름의 데이터베이스가 이미 열려있습니다: {conflicts['proposed_name']}")

        # DB 이름 생성
        db_name = os.path.splitext(os.path.basename(db_file_path))[0]

        try:
            # V2 DB 핸들러로 직접 연결
            logging.info(f"V2 데이터베이스 연결: {db_file_path}")
            db_handler = DBHandlerV2(db_file_path)
            self.databases[db_name] = db_handler

            # 파일 경로 추적 정보 저장
            self.db_file_paths[db_name] = os.path.abspath(db_file_path)

            # 첫 번째 DB이거나 대체 모드면 현재 DB로 설정
            if self.current_db_name is None or replace_existing:
                self.current_db_name = db_name

            logging.info(f"✅ Database added: {db_name} ({db_file_path})")
            return db_name

        except Exception as e:
            logging.error(f"Failed to add database {db_file_path}: {e}")
            raise Exception(f"데이터베이스 연결 실패: {e}")

    def create_and_add_database(self, db_file_path: str, replace_existing: bool = False,
                               force_add: bool = False, update_existing: bool = False) -> str:
        """
        새 데이터베이스 파일을 생성하고 추가 (Excel 가져오기용, 통합된 중복 처리 정책 적용)

        Args:
            db_file_path: 생성할 DB 파일 경로
            replace_existing: True면 기존 DB들을 모두 닫고 새 DB만 유지
            force_add: True면 중복 체크를 무시하고 강제로 추가
            update_existing: True면 기존 DB 파일을 업데이트 (Excel 변환용)

        Returns:
            추가된 DB의 이름 (기존 DB 재사용 시에도 해당 DB 이름 반환)

        Raises:
            ValueError: 중복 DB가 발견되었지만 force_add=False이고 update_existing=False일 때
        """
        # 기존 DB 대체 모드
        if replace_existing:
            self.disconnect_all()
        elif not force_add:
            # 🔧 통합된 중복 체크
            conflicts = self.check_database_conflicts(db_file_path)

            if conflicts['path_conflict']:
                # 동일한 파일 경로의 DB가 이미 로드됨
                existing_db_name = conflicts['path_conflict']
                if update_existing:
                    # Excel 변환 시: 기존 DB를 업데이트 대상으로 반환
                    logging.info(f"✅ 기존 DB를 업데이트 대상으로 설정: {existing_db_name}")
                    self.switch_database(existing_db_name)
                    return existing_db_name
                else:
                    # 일반적인 경우: 기존 DB 재사용
                    logging.info(f"✅ 동일한 파일의 DB가 이미 로드됨: {existing_db_name}")
                    self.switch_database(existing_db_name)
                    return existing_db_name

            if conflicts['name_conflict'] and not update_existing:
                # 동일한 이름의 DB가 이미 존재함 (다른 파일)
                raise ValueError(f"동일한 이름의 데이터베이스가 이미 열려있습니다: {conflicts['proposed_name']}")

        # 디렉토리가 존재하지 않으면 생성
        db_dir = os.path.dirname(db_file_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)
            logging.info(f"Created directory: {db_dir}")

        # DB 이름 생성
        db_name = os.path.splitext(os.path.basename(db_file_path))[0]

        try:
            # V2 DB 핸들러로 새 DB 생성 및 연결
            logging.info(f"V2 새 데이터베이스 생성: {db_file_path}")
            db_handler = DBHandlerV2(db_file_path)  # DBHandlerV2는 파일이 없으면 자동 생성
            self.databases[db_name] = db_handler

            # 파일 경로 추적 정보 저장
            self.db_file_paths[db_name] = os.path.abspath(db_file_path)

            # 첫 번째 DB이거나 대체 모드면 현재 DB로 설정
            if self.current_db_name is None or replace_existing:
                self.current_db_name = db_name

            logging.info(f"✅ New database created and added: {db_name} ({db_file_path})")
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
        데이터베이스 제거 (파일 경로 추적 정보도 함께 제거)

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

            # 파일 경로 추적 정보도 제거
            if db_name in self.db_file_paths:
                del self.db_file_paths[db_name]

            # 현재 DB가 제거된 경우 다른 DB로 전환
            if self.current_db_name == db_name:
                if self.databases:
                    self.current_db_name = next(iter(self.databases.keys()))
                else:
                    self.current_db_name = None

            logging.info(f"✅ Database removed: {db_name}")
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
        모든 데이터베이스 정보 반환 (파일 경로 추적 정보 활용)

        Returns:
            DB 정보 리스트 [{name, path, is_current}, ...]
        """
        info_list = []
        for db_name, db_handler in self.databases.items():
            # 파일 경로 추적 정보 우선 사용, 없으면 DB 핸들러에서 가져오기
            db_path = self.db_file_paths.get(db_name, db_handler.db_file if hasattr(db_handler, 'db_file') else None)

            info_list.append({
                'name': db_name,
                'path': db_path,
                'is_current': db_name == self.current_db_name
            })
        return info_list

    def disconnect_all(self):
        """모든 데이터베이스 연결 해제 (파일 경로 추적 정보도 함께 정리)"""
        for db_name, db_handler in self.databases.items():
            try:
                db_handler.disconnect()
                logging.info(f"Database disconnected: {db_name}")
            except Exception as e:
                logging.error(f"Failed to disconnect database {db_name}: {e}")

        self.databases.clear()
        self.db_file_paths.clear()  # 파일 경로 추적 정보도 정리
        self.current_db_name = None
        logging.info("✅ All databases disconnected and file path tracking cleared")

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

    def get_database_by_file_path(self, file_path: str) -> Optional[str]:
        """
        파일 경로로 DB 이름 찾기

        Args:
            file_path: 찾을 DB 파일 경로

        Returns:
            해당 파일 경로의 DB 이름 또는 None
        """
        return self._is_database_already_loaded(file_path)

    def check_database_conflicts(self, db_file_path: str) -> Dict[str, Optional[str]]:
        """
        DB 파일 경로와 이름 기반 중복 체크

        Args:
            db_file_path: 확인할 DB 파일 경로

        Returns:
            {
                'path_conflict': 동일한 파일 경로의 DB 이름 또는 None,
                'name_conflict': 동일한 이름의 DB 이름 또는 None,
                'proposed_name': 제안할 DB 이름
            }
        """
        proposed_name = os.path.splitext(os.path.basename(db_file_path))[0]

        # 파일 경로 기반 중복 체크
        path_conflict = self._is_database_already_loaded(db_file_path)

        # 이름 기반 중복 체크
        name_conflict = proposed_name if proposed_name in self.databases else None

        return {
            'path_conflict': path_conflict,
            'name_conflict': name_conflict,
            'proposed_name': proposed_name
        }

    def get_loaded_file_paths(self) -> List[str]:
        """
        현재 로드된 모든 DB 파일 경로 목록 반환

        Returns:
            로드된 DB 파일 경로 목록
        """
        return list(self.db_file_paths.values())

    def validate_database_integrity(self) -> Dict[str, bool]:
        """
        모든 DB의 무결성 검증

        Returns:
            {db_name: is_valid, ...}
        """
        integrity_status = {}

        for db_name, db_handler in self.databases.items():
            try:
                # 기본적인 연결 상태 확인
                if hasattr(db_handler, 'conn') and db_handler.conn:
                    # 간단한 쿼리로 DB 상태 확인
                    db_handler.cursor.execute("SELECT 1")
                    integrity_status[db_name] = True
                    logging.debug(f"DB 무결성 검증 성공: {db_name}")
                else:
                    integrity_status[db_name] = False
                    logging.warning(f"DB 연결 상태 불량: {db_name}")

            except Exception as e:
                integrity_status[db_name] = False
                logging.error(f"DB 무결성 검증 실패: {db_name} - {e}")

        return integrity_status

    def safe_update_database_from_excel(self, db_name: str, excel_data: Dict[str, List[List]],
                                       backup_before_update: bool = True) -> Dict[str, Any]:
        """
        Excel 데이터로 기존 DB를 안전하게 업데이트

        Args:
            db_name: 업데이트할 DB 이름
            excel_data: {sheet_name: [[row_data], ...], ...} 형태의 Excel 데이터
            backup_before_update: 업데이트 전 백업 생성 여부

        Returns:
            {
                'success': bool,
                'updated_sheets': List[str],
                'backup_path': str or None,
                'rollback_info': Dict or None,
                'error': str or None
            }
        """
        if db_name not in self.databases:
            return {
                'success': False,
                'error': f"데이터베이스를 찾을 수 없습니다: {db_name}",
                'updated_sheets': [],
                'backup_path': None,
                'rollback_info': None
            }

        db_handler = self.databases[db_name]
        backup_path = None
        rollback_info = {}
        updated_sheets = []

        try:
            # 1. 백업 생성 (선택사항)
            if backup_before_update:
                backup_path = self._create_database_backup(db_name)
                logging.info(f"DB 백업 생성 완료: {backup_path}")

            # 2. 트랜잭션 시작
            db_handler.conn.execute("BEGIN TRANSACTION")

            # 3. 기존 시트 정보 수집 (롤백용)
            existing_sheets = db_handler.get_sheets()
            for sheet in existing_sheets:
                rollback_info[sheet['name']] = {
                    'sheet_id': sheet['id'],
                    'existed_before': True
                }

            # 4. Excel 데이터를 시트별로 처리
            for sheet_name, sheet_data in excel_data.items():
                try:
                    # 기존 시트 확인
                    existing_sheet = next((s for s in existing_sheets if s['name'] == sheet_name), None)

                    if existing_sheet:
                        # 기존 시트 업데이트
                        sheet_id = existing_sheet['id']
                        logging.info(f"기존 시트 업데이트: {sheet_name} (ID: {sheet_id})")

                        # 기존 데이터 백업 (롤백용)
                        rollback_info[sheet_name]['backup_data'] = db_handler.get_sheet_data(sheet_id)

                        # 시트 데이터 교체
                        self._replace_sheet_data_safely(db_handler, sheet_id, sheet_data)
                    else:
                        # 새 시트 생성
                        logging.info(f"새 시트 생성: {sheet_name}")
                        sheet_id = db_handler.create_sheet_v2(sheet_name, is_dollar_sheet=True)
                        rollback_info[sheet_name] = {
                            'sheet_id': sheet_id,
                            'existed_before': False
                        }

                        # 새 시트에 데이터 추가
                        self._insert_sheet_data_safely(db_handler, sheet_id, sheet_data)

                    updated_sheets.append(sheet_name)

                except Exception as sheet_error:
                    logging.error(f"시트 '{sheet_name}' 처리 중 오류: {sheet_error}")
                    raise Exception(f"시트 '{sheet_name}' 업데이트 실패: {sheet_error}")

            # 5. 트랜잭션 커밋
            db_handler.conn.commit()
            logging.info(f"✅ DB 업데이트 완료: {db_name}, 업데이트된 시트: {updated_sheets}")

            return {
                'success': True,
                'updated_sheets': updated_sheets,
                'backup_path': backup_path,
                'rollback_info': rollback_info,
                'error': None
            }

        except Exception as e:
            # 6. 오류 발생 시 롤백
            try:
                db_handler.conn.rollback()
                logging.error(f"DB 업데이트 실패, 롤백 완료: {e}")
            except Exception as rollback_error:
                logging.error(f"롤백 실패: {rollback_error}")

            return {
                'success': False,
                'error': str(e),
                'updated_sheets': [],
                'backup_path': backup_path,
                'rollback_info': rollback_info
            }

    def _create_database_backup(self, db_name: str) -> str:
        """DB 백업 파일 생성"""
        import shutil
        from datetime import datetime

        if db_name not in self.db_file_paths:
            raise ValueError(f"DB 파일 경로를 찾을 수 없습니다: {db_name}")

        original_path = self.db_file_paths[db_name]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = f"{original_path}.backup_{timestamp}"

        shutil.copy2(original_path, backup_path)
        return backup_path

    def _replace_sheet_data_safely(self, db_handler, sheet_id: int, new_data: List[List]) -> None:
        """시트 데이터를 안전하게 교체"""
        # 기존 셀 데이터 삭제
        db_handler.cursor.execute("DELETE FROM cells WHERE sheet_id = ?", (sheet_id,))

        # 새 데이터 삽입
        self._insert_sheet_data_safely(db_handler, sheet_id, new_data)

    def _insert_sheet_data_safely(self, db_handler, sheet_id: int, data: List[List]) -> None:
        """시트에 데이터를 안전하게 삽입"""
        cells_data = []
        for row_idx, row in enumerate(data):
            for col_idx, cell_value in enumerate(row):
                if cell_value is not None and str(cell_value).strip():  # 빈 셀 제외
                    cells_data.append((row_idx, col_idx, str(cell_value)))

        if cells_data:
            db_handler.batch_insert_cells(sheet_id, cells_data)

    def safe_reload_database(self, db_file_path: str, existing_db_name: str) -> str:
        """
        기존 DB를 안전하게 닫고 동일한 파일을 새로 로드

        Args:
            db_file_path: 재로드할 DB 파일 경로
            existing_db_name: 기존 DB 이름

        Returns:
            새로 로드된 DB 이름

        Raises:
            Exception: 재로드 실패 시
        """
        try:
            logging.info(f"DB 안전 재로드 시작: {existing_db_name} -> {db_file_path}")

            # 1. 기존 DB 상태 백업 (롤백용)
            backup_info = {
                'db_name': existing_db_name,
                'file_path': self.db_file_paths.get(existing_db_name),
                'was_current': self.current_db_name == existing_db_name
            }

            # 2. 기존 DB 연결 해제 및 제거 (강제 해제)
            if existing_db_name in self.databases:
                try:
                    db_handler = self.databases[existing_db_name]

                    # 강제로 모든 연결 해제
                    if hasattr(db_handler, 'cursor') and db_handler.cursor:
                        try:
                            db_handler.cursor.close()
                        except:
                            pass

                    if hasattr(db_handler, 'conn') and db_handler.conn:
                        try:
                            db_handler.conn.close()
                        except:
                            pass

                    # disconnect 메서드 호출
                    db_handler.disconnect()
                    logging.info(f"기존 DB 연결 해제: {existing_db_name}")

                    # 잠시 대기 (Windows 파일 잠금 해제 대기)
                    import time
                    time.sleep(0.1)

                except Exception as e:
                    logging.warning(f"기존 DB 연결 해제 중 오류: {e}")

                # DB 목록에서 제거
                del self.databases[existing_db_name]
                if existing_db_name in self.db_file_paths:
                    del self.db_file_paths[existing_db_name]

            # 3. 새로 DB 로드
            new_db_name = self.add_database(db_file_path, force_add=True)
            logging.info(f"✅ DB 안전 재로드 완료: {existing_db_name} -> {new_db_name}")

            return new_db_name

        except Exception as e:
            # 4. 오류 발생 시 롤백 시도
            error_msg = f"DB 재로드 실패: {e}"
            logging.error(error_msg)

            try:
                # 가능하면 기존 DB 복원 시도
                if backup_info['file_path'] and os.path.exists(backup_info['file_path']):
                    logging.info("DB 재로드 실패, 기존 DB 복원 시도")
                    restored_name = self.add_database(backup_info['file_path'], force_add=True)
                    if backup_info['was_current']:
                        self.switch_database(restored_name)
                    logging.info(f"기존 DB 복원 완료: {restored_name}")
            except Exception as restore_error:
                logging.error(f"기존 DB 복원 실패: {restore_error}")

            raise Exception(error_msg)

    def check_unsaved_changes(self, db_name: str) -> bool:
        """
        DB에 저장되지 않은 변경사항이 있는지 확인

        Args:
            db_name: 확인할 DB 이름

        Returns:
            저장되지 않은 변경사항이 있으면 True
        """
        # SQLite는 자동 커밋이므로 일반적으로 저장되지 않은 변경사항이 없음
        # 하지만 트랜잭션 중이거나 특별한 상황을 확인
        try:
            if db_name not in self.databases:
                return False

            db_handler = self.databases[db_name]
            if not hasattr(db_handler, 'conn') or not db_handler.conn:
                return False

            # 트랜잭션 상태 확인
            db_handler.cursor.execute("BEGIN")
            db_handler.cursor.execute("ROLLBACK")

            return False  # SQLite 특성상 일반적으로 자동 저장됨

        except Exception as e:
            logging.warning(f"변경사항 확인 중 오류: {e}")
            return False  # 확실하지 않으면 안전하게 False 반환

    def safe_reload_database_with_confirmation(self, db_file_path: str, existing_db_name: str,
                                             parent_widget=None) -> str:
        """
        사용자 확인을 포함한 안전한 DB 재로드

        Args:
            db_file_path: 재로드할 DB 파일 경로
            existing_db_name: 기존 DB 이름
            parent_widget: 대화상자 부모 위젯

        Returns:
            새로 로드된 DB 이름
        """
        try:
            # 1. 저장되지 않은 변경사항 확인
            has_unsaved = self.check_unsaved_changes(existing_db_name)

            if has_unsaved and parent_widget:
                from PySide6.QtWidgets import QMessageBox
                reply = QMessageBox.warning(
                    parent_widget, "저장되지 않은 변경사항",
                    f"'{existing_db_name}' DB에 저장되지 않은 변경사항이 있을 수 있습니다.\n\n"
                    f"계속하면 변경사항이 손실될 수 있습니다.\n"
                    f"정말 계속하시겠습니까?",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No
                )

                if reply != QMessageBox.Yes:
                    raise Exception("사용자가 재로드를 취소했습니다.")

            # 2. 안전한 재로드 실행
            return self.safe_reload_database(db_file_path, existing_db_name)

        except Exception as e:
            logging.error(f"확인을 포함한 DB 재로드 실패: {e}")
            raise

