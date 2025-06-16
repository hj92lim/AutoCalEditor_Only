"""
Git 연동 및 DB 히스토리 관리 시스템
- CSV 기반 DB 히스토리 저장
- Git 자동 pull/commit/push
- 로컬 Git 저장소 관리
"""

import os
import csv
import logging
import subprocess
import shutil
import re
import sys
from datetime import datetime
from typing import Dict, List
from pathlib import Path

# 중앙 집중식 상수 관리 모듈 import
from core.constants import GitConstants, DatabaseConstants

# Windows 콘솔창 숨김을 위한 subprocess 설정
def get_subprocess_kwargs_for_git():
    """Git 명령어용 subprocess 설정 (콘솔창 숨김)"""
    kwargs = {
        'encoding': 'utf-8',
        'errors': 'replace',
        'timeout': 30
    }

    # Windows에서 콘솔창 숨김 설정
    if sys.platform == "win32":
        kwargs['creationflags'] = subprocess.CREATE_NO_WINDOW

        # 환경변수 설정
        env = os.environ.copy()
        env['PYTHONIOENCODING'] = 'utf-8'
        env['PYTHONUTF8'] = '1'
        kwargs['env'] = env

    return kwargs


class GitManager:
    """Git 연동 관리 클래스"""

    def __init__(self):
        """
        GitManager 초기화 (로컬 Git 전용) - 🚀 성능 최적화 적용
        """
        self.project_root = Path.cwd()
        self.backup_dir = self.project_root / DatabaseConstants.BACKUP_DIR
        self.history_dir = self.project_root / DatabaseConstants.HISTORY_DIR

        # 🚀 성능 최적화: Git 루트 캐싱
        self._git_root_cache = None
        self._git_root_cache_time = 0
        self._git_root_cache_ttl = 300  # 5분 캐시

        # Git 실행 파일 경로 찾기
        self.git_executable = self._find_git_executable()

        # history 디렉토리만 미리 생성 (CSV 히스토리용)
        # backup 디렉토리는 실제 백업 시에만 생성
        self.history_dir.mkdir(exist_ok=True)

        # 🚀 성능 최적화: 로깅 레벨 조정 (WARNING 이상만 출력)
        # logging.info(f"GitManager 초기화 (로컬 Git 전용): {self.project_root}")
        # logging.info(f"Git 실행 파일: {self.git_executable}")

        # Git 실행 파일 테스트 (중요한 정보만 출력)
        if self.git_executable != "git":
            if not os.path.exists(self.git_executable):
                print(f"❌ Git 실행 파일 없음: {self.git_executable}")
        # 성공 메시지는 제거하여 성능 향상

    def _find_git_executable(self) -> str:
        """Git 실행 파일 경로 찾기"""
        import platform

        # Windows에서 일반적인 Git 설치 경로들 (constants에서 관리)
        if platform.system() == "Windows":
            possible_paths = GitConstants.WINDOWS_GIT_PATHS

            # 설치된 경로 확인
            for path in possible_paths:
                if os.path.exists(path):
                    return path

            # where 명령어로 찾기 시도 (콘솔창 숨김)
            try:
                kwargs = get_subprocess_kwargs_for_git()
                result = subprocess.run(['where', 'git'], capture_output=True, text=True, check=True, **kwargs)
                git_path = result.stdout.strip().split('\n')[0]
                if os.path.exists(git_path):
                    return git_path
            except:
                pass

        # 기본값 (PATH에서 찾기)
        return "git"



    def init_git_repo(self):
        """Git 저장소 초기화 (처음 실행 시)"""
        try:
            # .git 디렉토리가 없으면 초기화
            if not (self.project_root / ".git").exists():
                logging.info("Git 저장소 초기화 중...")
                subprocess.run([self.git_executable, 'init'], cwd=self.project_root, check=True,
                             encoding='utf-8', errors='replace')
                logging.info("Git 저장소 초기화 완료")

            return True

        except subprocess.CalledProcessError as e:
            logging.error(f"Git 저장소 초기화 실패: {e}")
            return False
        except Exception as e:
            logging.error(f"Git 초기화 중 오류: {e}")
            return False

    def get_default_branch(self) -> str:
        """기본 브랜치 이름 확인"""
        try:
            # 원격 브랜치 목록 가져오기
            result = subprocess.run([self.git_executable, 'branch', '-r'],
                                  cwd=self.project_root,
                                  capture_output=True, text=True, check=True,
                                  encoding='utf-8', errors='replace')

            remote_branches = result.stdout.strip().split('\n')

            # 브랜치 우선순위 (constants에서 관리)
            for priority_branch in GitConstants.DEFAULT_BRANCH_PRIORITY:
                for branch in remote_branches:
                    branch = branch.strip()
                    if f'origin/{priority_branch}' in branch:
                        return priority_branch

            # main/master가 없으면 첫 번째 브랜치 사용
            if remote_branches and remote_branches[0].strip():
                first_branch = remote_branches[0].strip()
                if 'origin/' in first_branch:
                    return first_branch.split('origin/')[-1]

            # 기본값 (constants에서 관리)
            return GitConstants.DEFAULT_BRANCH_PRIORITY[0]

        except Exception as e:
            logging.warning(f"기본 브랜치 확인 실패: {e}")
            return GitConstants.DEFAULT_BRANCH_PRIORITY[0]

    def get_all_branches(self) -> Dict[str, List[str]]:
        """모든 브랜치 목록 가져오기 (로컬 + 원격)"""
        try:
            branches = {
                'local': [],
                'remote': [],
                'current': ''
            }

            # 현재 브랜치 확인
            try:
                result = subprocess.run([self.git_executable, 'branch', '--show-current'],
                                      cwd=self.project_root,
                                      capture_output=True, text=True, check=True,
                                      encoding='utf-8', errors='replace')
                branches['current'] = result.stdout.strip()
            except:
                branches['current'] = GitConstants.DEFAULT_BRANCH_PRIORITY[0]

            # 로컬 브랜치 목록
            try:
                result = subprocess.run([self.git_executable, 'branch'],
                                      cwd=self.project_root,
                                      capture_output=True, text=True, check=True,
                                      encoding='utf-8', errors='replace')
                for line in result.stdout.strip().split('\n'):
                    branch = line.strip().replace('*', '').strip()
                    if branch and branch not in branches['local']:
                        branches['local'].append(branch)
            except:
                pass

            # 원격 브랜치 목록
            try:
                result = subprocess.run([self.git_executable, 'branch', '-r'],
                                      cwd=self.project_root,
                                      capture_output=True, text=True, check=True,
                                      encoding='utf-8', errors='replace')
                for line in result.stdout.strip().split('\n'):
                    branch = line.strip()
                    if not branch:
                        continue

                    # HEAD -> 같은 특별한 참조 제거
                    if 'HEAD ->' in branch:
                        continue

                    # 원격 저장소 이름과 브랜치 이름 분리
                    if '/' in branch:
                        parts = branch.split('/', 1)
                        if len(parts) == 2:
                            remote_name = parts[0]
                            remote_branch = parts[1]

                            # 빈 문자열이나 특별한 참조 제거
                            if remote_branch and remote_branch not in branches['remote']:
                                # 원격 저장소 이름과 함께 표시
                                display_name = f"{remote_branch} ({remote_name})"
                                branches['remote'].append({
                                    'name': remote_branch,
                                    'remote': remote_name,
                                    'display': display_name,
                                    'full_name': branch
                                })
            except:
                pass

            return branches

        except Exception as e:
            logging.error(f"브랜치 목록 가져오기 실패: {e}")
            default_branch = GitConstants.DEFAULT_BRANCH_PRIORITY[0]
            return {
                'local': [default_branch],
                'remote': [default_branch],
                'current': default_branch
            }

    def switch_branch(self, branch_name: str) -> bool:
        """브랜치 전환"""
        try:
            # 로컬 브랜치가 있는지 확인
            result = subprocess.run([self.git_executable, 'branch'],
                                  cwd=self.project_root,
                                  capture_output=True, text=True, check=True,
                                  encoding='utf-8', errors='replace')
            local_branches = [line.strip().replace('*', '').strip()
                            for line in result.stdout.strip().split('\n')]

            if branch_name in local_branches:
                # 로컬 브랜치로 전환
                subprocess.run([self.git_executable, 'checkout', branch_name],
                             cwd=self.project_root, check=True,
                             encoding='utf-8', errors='replace')
            else:
                # 원격 브랜치에서 새 로컬 브랜치 생성
                # 먼저 origin에서 찾고, 없으면 다른 원격 저장소에서 찾기
                remote_ref = None

                # 원격 브랜치 목록 확인
                remote_result = subprocess.run([self.git_executable, 'branch', '-r'],
                                             cwd=self.project_root,
                                             capture_output=True, text=True, check=True,
                                             encoding='utf-8', errors='replace')

                for line in remote_result.stdout.strip().split('\n'):
                    remote_branch = line.strip()
                    if remote_branch.endswith(f'/{branch_name}') and 'HEAD ->' not in remote_branch:
                        remote_ref = remote_branch
                        # origin을 우선적으로 선택
                        if remote_branch.startswith('origin/'):
                            break

                if remote_ref:
                    subprocess.run([self.git_executable, 'checkout', '-b', branch_name, remote_ref],
                                 cwd=self.project_root, check=True,
                                 encoding='utf-8', errors='replace')
                    logging.info(f"원격 브랜치 {remote_ref}에서 로컬 브랜치 {branch_name} 생성")
                else:
                    # 원격에도 없으면 새 브랜치 생성
                    subprocess.run([self.git_executable, 'checkout', '-b', branch_name],
                                 cwd=self.project_root, check=True,
                                 encoding='utf-8', errors='replace')
                    logging.info(f"새 브랜치 {branch_name} 생성")

            logging.info(f"브랜치 전환 완료: {branch_name}")
            return True

        except subprocess.CalledProcessError as e:
            logging.error(f"브랜치 전환 실패: {e}")
            return False

    def get_force_pull_preview(self):
        """강제 pull 시 변경될 파일 목록 미리보기"""
        try:
            logging.info("강제 pull 미리보기 시작...")

            # Git 저장소 초기화 확인
            if not self.init_git_repo():
                return None

            # 원격 저장소에서 최신 정보 가져오기
            try:
                subprocess.run([self.git_executable, 'fetch'], cwd=self.project_root, check=True,
                             capture_output=True, text=True,
                             encoding='utf-8', errors='replace')
                logging.info("Git fetch 완료")
            except subprocess.CalledProcessError as e:
                logging.error(f"Git fetch 실패: {e}")
                return None

            # 기본 브랜치 확인
            default_branch = self.get_default_branch()

            # 현재 상태와 원격 상태 비교
            changes = {
                'deleted_files': [],      # 삭제될 파일들 (로컬 전용 + 추적되지 않는 파일들)
                'modified_files': [],     # 수정될 파일들 (원격 버전으로 덮어쓰기)
                'new_files': []           # 새로 추가될 파일들 (원격에서 가져옴)
            }

            try:
                # 1. 현재 브랜치와 원격 브랜치 간의 차이점 확인
                result = subprocess.run(
                    [self.git_executable, 'diff', '--name-status', f'origin/{default_branch}'],
                    cwd=self.project_root, capture_output=True, text=True, check=True
                )

                for line in result.stdout.strip().split('\n'):
                    if not line:
                        continue

                    parts = line.split('\t')
                    if len(parts) >= 2:
                        status = parts[0]
                        filename = parts[1]

                        if status == 'D':
                            changes['new_files'].append(filename)  # 원격에서 삭제된 파일은 로컬에서 새로 생성됨
                        elif status == 'A':
                            changes['deleted_files'].append(filename)  # 원격에서 추가된 파일은 로컬에서 삭제됨
                        elif status.startswith('M'):
                            changes['modified_files'].append(filename)
                        elif status.startswith('R'):
                            # 이름 변경된 파일
                            if len(parts) >= 3:
                                old_name = parts[1]
                                new_name = parts[2]
                                changes['deleted_files'].append(old_name)
                                changes['new_files'].append(new_name)

            except subprocess.CalledProcessError as e:
                logging.warning(f"Git diff 실패: {e}")

            try:
                # 2. 추적되지 않는 파일들 확인 (git clean으로 삭제될 파일들)
                result = subprocess.run(
                    [self.git_executable, 'clean', '-n', '-fd'],  # -n: dry run
                    cwd=self.project_root, capture_output=True, text=True, check=True
                )

                for line in result.stdout.strip().split('\n'):
                    if line.startswith('Would remove '):
                        filename = line.replace('Would remove ', '')
                        changes['deleted_files'].append(filename)  # 삭제될 파일로 통합

            except subprocess.CalledProcessError as e:
                logging.warning(f"Git clean preview 실패: {e}")

            try:
                # 3. 로컬에만 있는 파일들 확인 (원격에 없어서 삭제될 파일들)
                result = subprocess.run(
                    [self.git_executable, 'ls-files', '--others', '--exclude-standard'],
                    cwd=self.project_root, capture_output=True, text=True, check=True
                )

                for line in result.stdout.strip().split('\n'):
                    if line and line not in changes['deleted_files']:
                        changes['deleted_files'].append(line)  # 삭제될 파일로 통합

            except subprocess.CalledProcessError as e:
                logging.warning(f"Git ls-files 실패: {e}")

            logging.info(f"강제 pull 미리보기 완료: {len(changes['deleted_files'])}개 삭제, "
                        f"{len(changes['modified_files'])}개 수정, {len(changes['new_files'])}개 추가")

            return changes

        except Exception as e:
            logging.error(f"강제 pull 미리보기 중 오류: {e}")
            return None

    def force_pull(self):
        """강제 pull (충돌 무시하고 원격 기준으로 덮어쓰기)"""
        try:
            logging.info("강제 Git pull 시작...")

            # Git 저장소 초기화 확인
            if not self.init_git_repo():
                return False

            # 단순한 Git 작업 - 보호 기능 없음
            try:
                subprocess.run([self.git_executable, 'reset', '--hard'], cwd=self.project_root, check=True,
                             encoding='utf-8', errors='replace')
                subprocess.run([self.git_executable, 'clean', '-fd'], cwd=self.project_root, check=True,
                             encoding='utf-8', errors='replace')
                logging.info("Git reset & clean 완료")
            except subprocess.CalledProcessError as e:
                logging.error(f"Git 명령 실패: {e}")
                return False

            # 원격에서 최신 정보 가져오기
            try:
                subprocess.run([self.git_executable, 'fetch', 'origin'], cwd=self.project_root, check=True,
                             encoding='utf-8', errors='replace')
                logging.info("Git fetch 완료")
            except subprocess.CalledProcessError as e:
                logging.error(f"Git fetch 실패: {e}")
                return False

            # 기본 브랜치 확인
            default_branch = self.get_default_branch()
            logging.info(f"기본 브랜치: {default_branch}")

            # 원격 기준으로 강제 리셋
            try:
                subprocess.run([self.git_executable, 'reset', '--hard', f'origin/{default_branch}'],
                             cwd=self.project_root, check=True)
                logging.info(f"origin/{default_branch} 기준으로 강제 리셋 완료")
            except subprocess.CalledProcessError as e:
                logging.error(f"Git reset 실패: {e}")
                error_msg = str(e).lower()
                if "unknown revision" in error_msg or "does not exist" in error_msg:
                    logging.info("원격 저장소가 비어있음. 초기 커밋이 필요합니다.")
                    return True  # 비어있는 저장소는 정상 상황
                return False

            logging.info("강제 Git pull 완료")
            return True

        except subprocess.CalledProcessError as e:
            logging.error(f"Git pull 실패: {e}")
            return False
        except Exception as e:
            logging.error(f"Git pull 중 오류: {e}")
            return False

    def reset_to_remote(self, target_branch: str = None) -> bool:
        """원격 기준으로 로컬 초기화 (clean 명령어 사용 안함)"""
        try:
            logging.info("원격 기준 로컬 초기화 시작...")

            # Git 저장소 초기화 확인
            if not self.init_git_repo():
                return False

            # 대상 브랜치 결정
            if not target_branch:
                target_branch = self.get_default_branch()

            logging.info(f"대상 브랜치: {target_branch}")

            # 원격에서 최신 정보 가져오기
            try:
                subprocess.run([self.git_executable, 'fetch', 'origin'], cwd=self.project_root, check=True)
                logging.info("Git fetch 완료")
            except subprocess.CalledProcessError as e:
                logging.error(f"Git fetch 실패: {e}")
                return False

            # 원격 기준으로 강제 리셋 (clean 명령어 제외)
            try:
                subprocess.run([self.git_executable, 'reset', '--hard', f'origin/{target_branch}'],
                             cwd=self.project_root, check=True)
                logging.info(f"origin/{target_branch} 기준으로 강제 리셋 완료")
            except subprocess.CalledProcessError as e:
                logging.error(f"Git reset 실패: {e}")
                error_msg = str(e).lower()
                if "unknown revision" in error_msg or "does not exist" in error_msg:
                    logging.info("원격 저장소가 비어있음. 초기 커밋이 필요합니다.")
                    return True  # 비어있는 저장소는 정상 상황
                return False

            logging.info("원격 기준 로컬 초기화 완료")
            return True

        except subprocess.CalledProcessError as e:
            logging.error(f"원격 기준 초기화 실패: {e}")
            return False
        except Exception as e:
            logging.error(f"원격 기준 초기화 중 오류: {e}")
            return False

    def create_backup(self, db_files: List[str]):
        """DB 파일들 백업 생성 (상위 디렉토리에)"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_count = 0

            # 백업할 파일이 없으면 폴더 생성하지 않음
            if not db_files:
                logging.info("백업할 DB 파일이 없음")
                return True

            for db_file in db_files:
                try:
                    # 절대 경로로 변환
                    if not os.path.isabs(db_file):
                        db_path = self.project_root / db_file
                    else:
                        db_path = Path(db_file)

                    if db_path.exists():
                        # 백업 폴더가 없으면 이때 생성
                        if not self.backup_dir.exists():
                            self.backup_dir.mkdir(exist_ok=True)
                            logging.info(f"백업 폴더 생성: {self.backup_dir}")

                        backup_name = f"{db_path.stem}_backup_{timestamp}{db_path.suffix}"
                        backup_path = self.backup_dir / backup_name
                        shutil.copy2(db_path, backup_path)
                        logging.info(f"백업 생성: {backup_path}")
                        backup_count += 1
                    else:
                        logging.warning(f"백업 대상 파일이 존재하지 않음: {db_path}")

                except Exception as file_error:
                    logging.error(f"개별 파일 백업 실패 ({db_file}): {file_error}")
                    continue

            logging.info(f"총 {backup_count}개 DB 파일 백업 완료 (위치: {self.backup_dir})")
            return backup_count > 0

        except Exception as e:
            logging.error(f"백업 생성 중 오류: {e}")
            return False

    def export_sheet_to_csv(self, db_handler, sheet_id: int, sheet_name: str,
                           history_dir: Path) -> bool:
        """시트 데이터를 CSV로 내보내기"""
        try:
            # CSV 파일 경로
            csv_file = history_dir / f"{sheet_name}.csv"

            # 시트 데이터 가져오기
            sheet_data = db_handler.get_sheet_data(sheet_id)

            if not sheet_data:
                logging.warning(f"시트 {sheet_name} 데이터가 비어있음")
                # 빈 CSV 파일 생성
                with open(csv_file, 'w', newline='', encoding='utf-8') as f:
                    pass
                return True

            # CSV 파일로 저장
            with open(csv_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerows(sheet_data)

            logging.info(f"CSV 내보내기 완료: {csv_file}")
            return True

        except Exception as e:
            logging.error(f"CSV 내보내기 실패 ({sheet_name}): {e}")
            return False

    def export_all_db_history(self, db_handlers: List):
        """모든 DB의 히스토리를 CSV로 내보내기"""
        try:
            export_count = 0

            for db_handler in db_handlers:
                if not db_handler or not hasattr(db_handler, 'db_file'):
                    continue

                # DB 파일명에서 히스토리 디렉토리명 생성 (상위 디렉토리에)
                db_name = Path(db_handler.db_file).stem
                history_dir = self.history_dir / db_name
                history_dir.mkdir(exist_ok=True)

                # 모든 시트 내보내기 (V2 방식)
                sheets = db_handler.get_sheets()  # V2에서는 파일 ID 없이 모든 시트 조회
                for sheet in sheets:
                    sheet_id = sheet['id']
                    sheet_name = sheet['name']

                    # $ 기호 제거 (파일명에 사용하기 위해)
                    safe_sheet_name = sheet_name.replace('$', '')

                    if self.export_sheet_to_csv(db_handler, sheet_id, safe_sheet_name, history_dir):
                        export_count += 1

                logging.info(f"DB {db_name} 히스토리 내보내기 완료")

            logging.info(f"총 {export_count}개 시트 CSV 내보내기 완료")
            return True

        except Exception as e:
            logging.error(f"DB 히스토리 내보내기 중 오류: {e}")
            return False

    def commit_and_push(self, commit_message: str, target_branch: str = None):
        """변경사항 커밋 및 푸시"""
        try:
            logging.info("Git add, commit, push 시작...")

            # 대상 브랜치 결정
            if not target_branch:
                target_branch = self.get_default_branch()

            logging.info(f"대상 브랜치: {target_branch}")

            # 모든 변경사항 스테이징
            subprocess.run([self.git_executable, 'add', '.'], cwd=self.project_root, check=True,
                         encoding='utf-8', errors='replace')

            # 커밋 (변경사항이 없으면 스킵)
            try:
                subprocess.run([self.git_executable, 'commit', '-m', commit_message],
                             cwd=self.project_root, check=True,
                             encoding='utf-8', errors='replace')
                logging.info(f"커밋 완료: {commit_message}")
            except subprocess.CalledProcessError:
                logging.info("커밋할 변경사항이 없음")
                return True

            # 푸시 (현재 브랜치를 원격으로)
            subprocess.run([self.git_executable, 'push', 'origin', target_branch],
                         cwd=self.project_root, check=True,
                         encoding='utf-8', errors='replace')

            logging.info(f"Git push 완료: {target_branch}")
            return True

        except subprocess.CalledProcessError as e:
            logging.error(f"Git 커밋/푸시 실패: {e}")
            return False
        except Exception as e:
            logging.error(f"Git 작업 중 오류: {e}")
            return False

    def get_git_root(self) -> str:
        """🚀 성능 최적화: Git 저장소 루트 디렉토리 찾기 (캐싱 적용)"""
        import time

        # 캐시 확인 (5분 TTL)
        current_time = time.time()
        if (self._git_root_cache and
            current_time - self._git_root_cache_time < self._git_root_cache_ttl):
            return self._git_root_cache

        try:
            # 현재 디렉토리에서 시작해서 Git 루트 찾기
            current_dir = os.getcwd()

            # 🚀 성능 최적화: 타임아웃을 3초로 단축 (기존 10초 → 3초)
            # 인코딩 문제 해결을 위한 환경변수 설정
            env = os.environ.copy()
            env['PYTHONIOENCODING'] = 'utf-8'
            if os.name == 'nt':  # Windows
                env['LANG'] = 'en_US.UTF-8'

            result = subprocess.run([self.git_executable, 'rev-parse', '--show-toplevel'],
                                  cwd=current_dir,
                                  capture_output=True,
                                  text=True,
                                  encoding='utf-8',
                                  errors='replace',
                                  env=env,
                                  timeout=3,  # 🚀 10초 → 3초로 단축
                                  check=True)
            git_root = result.stdout.strip()

            # Windows 경로 정규화 (슬래시 통일)
            git_root = git_root.replace('\\', '/')

            # 🚀 성능 최적화: 캐시에 저장
            self._git_root_cache = git_root
            self._git_root_cache_time = current_time

            # 🚀 성능 최적화: 로깅 제거 (성능 향상)
            # logging.info(f"Git 루트 찾음: {git_root} (현재 디렉토리: {current_dir})")
            return git_root
        except Exception as e:
            # Git 루트를 찾을 수 없으면 현재 디렉토리 사용
            current_dir = os.getcwd()

            # 🚀 성능 최적화: 캐시에 저장 (실패한 경우도 캐시하여 반복 호출 방지)
            self._git_root_cache = current_dir
            self._git_root_cache_time = current_time

            # 🚀 성능 최적화: 에러 시에만 로깅 (성능 향상)
            logging.error(f"Git 루트 찾기 실패: {e}, 현재 디렉토리 사용: {current_dir}")
            return current_dir

    def get_current_branch(self) -> str:
        """현재 브랜치 가져오기"""
        try:
            git_root = self.get_git_root()

            # 인코딩 문제 해결을 위한 환경변수 설정
            env = os.environ.copy()
            env['PYTHONIOENCODING'] = 'utf-8'
            if os.name == 'nt':  # Windows
                env['LANG'] = 'en_US.UTF-8'

            result = subprocess.run([self.git_executable, 'branch', '--show-current'],
                                  cwd=git_root,
                                  capture_output=True,
                                  text=True,
                                  encoding='utf-8',
                                  errors='replace',
                                  env=env,
                                  timeout=10,
                                  check=True)
            return result.stdout.strip() or "detached HEAD"
        except Exception as e:
            logging.warning(f"현재 브랜치 가져오기 실패: {e}")
            return "알 수 없음"

    def get_git_status(self) -> str:
        """Git 상태 확인"""
        try:
            # 인코딩 문제 해결을 위한 환경변수 설정
            env = os.environ.copy()
            env['PYTHONIOENCODING'] = 'utf-8'
            if os.name == 'nt':  # Windows
                env['LANG'] = 'en_US.UTF-8'

            result = subprocess.run([self.git_executable, 'status', '--porcelain'],
                                  cwd=self.project_root,
                                  capture_output=True,
                                  text=True,
                                  encoding='utf-8',
                                  errors='replace',
                                  env=env,
                                  timeout=10,
                                  check=True)
            return result.stdout.strip()
        except Exception as e:
            logging.warning(f"Git 상태 확인 실패: {e}")
            return "Git 상태 확인 실패"

    def get_changed_files(self, use_enhanced_encoding: bool = True) -> List[Dict[str, str]]:
        """변경된 파일 목록 가져오기 (인코딩 문제 해결 포함)"""
        try:
            # Git 저장소 루트 디렉토리 사용
            git_root = self.get_git_root()

            # Git 저장소 정리 시도 (인코딩 문제 해결)
            self._cleanup_git_encoding_issues(git_root)

            # 인코딩 문제 해결을 위한 환경변수 설정 (Windows 호환)
            env = os.environ.copy()
            if use_enhanced_encoding:
                env['PYTHONIOENCODING'] = 'utf-8'
                # Windows에서 LC_ALL 설정 문제 해결
                if os.name == 'nt':  # Windows
                    env['LANG'] = 'en_US.UTF-8'
                else:
                    env['LC_ALL'] = 'C.UTF-8'

            # Git 설정으로 인코딩 문제 해결 시도
            try:
                # 핵심 Git 인코딩 설정
                git_configs = [
                    [self.git_executable, 'config', 'core.quotepath', 'false'],  # 경로 인용 비활성화
                    [self.git_executable, 'config', 'core.precomposeunicode', 'true'],  # 유니코드 정규화
                    [self.git_executable, 'config', 'i18n.filesEncoding', 'utf-8'],  # 파일 인코딩
                    [self.git_executable, 'config', 'i18n.logOutputEncoding', 'utf-8'],  # 로그 출력 인코딩
                ]

                for config_cmd in git_configs:
                    try:
                        result = subprocess.run(config_cmd, cwd=git_root,
                                              capture_output=True, timeout=5)
                        if result.returncode == 0:
                            logging.debug(f"Git 설정 성공: {' '.join(config_cmd[2:])}")
                    except:
                        continue

            except:
                pass  # 설정 실패해도 계속 진행

            # Git status 명령어 실행 (인코딩 안전 모드)
            try:
                # 첫 번째 시도: UTF-8 인코딩
                result = subprocess.run(
                    [self.git_executable, 'status', '--porcelain', '--untracked-files=all'],
                    cwd=git_root,
                    capture_output=True,
                    text=True,
                    encoding='utf-8',
                    errors='replace',
                    env=env,
                    timeout=30
                )

                if result.returncode != 0:
                    raise subprocess.CalledProcessError(result.returncode, ['git', 'status'])

            except (subprocess.CalledProcessError, UnicodeDecodeError) as e:
                logging.warning(f"UTF-8 모드 Git status 실패: {e}")

                # 두 번째 시도: 바이너리 모드로 실행 후 안전 디코딩
                try:
                    result_binary = subprocess.run(
                        [self.git_executable, 'status', '--porcelain', '--untracked-files=all'],
                        cwd=git_root,
                        capture_output=True,
                        env=env,
                        timeout=30
                    )

                    if result_binary.returncode != 0:
                        raise subprocess.CalledProcessError(result_binary.returncode, ['git', 'status'])

                    # 안전한 디코딩
                    try:
                        stdout_text = result_binary.stdout.decode('utf-8', errors='replace')
                    except:
                        try:
                            stdout_text = result_binary.stdout.decode('cp949', errors='replace')
                        except:
                            stdout_text = result_binary.stdout.decode('latin1', errors='replace')

                    # 결과 객체 생성
                    class SafeResult:
                        def __init__(self, stdout, returncode):
                            self.stdout = stdout
                            self.returncode = returncode

                    result = SafeResult(stdout_text, result_binary.returncode)

                except Exception as binary_error:
                    logging.error(f"바이너리 모드도 실패: {binary_error}")
                    # 빈 결과 반환
                    class EmptyResult:
                        def __init__(self):
                            self.stdout = ""
                            self.returncode = 0

                    result = EmptyResult()

            # 🚀 성능 최적화: 디버깅 로깅 제거 (성능 향상)
            # stdout_preview = result.stdout[:200] if result.stdout else "(빈 출력)"
            # logging.info(f"Git status 원본 출력 (처음 200자): {repr(stdout_preview)}")

            changed_files = []
            if not result.stdout.strip():
                # 🚀 성능 최적화: 정상 상황 로깅 제거
                # logging.info("Git status 출력이 비어있음 - 변경된 파일 없음")
                return []

            lines = result.stdout.strip().split('\n')
            # 🚀 성능 최적화: 파싱 로깅 제거
            # logging.info(f"Git status 파싱: {len(lines)}개 라인")

            for line_num, line in enumerate(lines, 1):
                if not line.strip():
                    continue

                # Git status 형식: XY filename
                # 더 견고한 파싱을 위해 다양한 경우 처리
                if len(line) < 3:
                    logging.warning(f"라인 {line_num}: 너무 짧은 Git status 라인: '{line}'")
                    continue

                status = line[:2]

                # 파일명 추출 - 정규표현식 사용으로 더 견고하게
                filename = None

                # Git status 형식: XY filename (X, Y는 상태 문자, 그 다음 공백 또는 탭, 그 다음 파일명)
                # 정규표현식 패턴: 처음 2문자(상태) + 공백/탭 + 나머지(파일명)
                match = re.match(r'^(.{2})[\s\t](.+)$', line)
                if match:
                    status = match.group(1)
                    filename = match.group(2)
                else:
                    # 정규표현식이 실패한 경우 기존 방법 사용
                    # 방법 1: 정상적인 경우 (상태 코드 + 공백 + 파일명)
                    if len(line) > 2 and line[2] == ' ':
                        filename = line[3:]
                    # 방법 2: 공백이 없는 경우 (상태 코드 + 파일명)
                    elif len(line) > 2:
                        filename = line[2:]
                    # 방법 3: 탭으로 구분된 경우
                    elif '\t' in line:
                        parts = line.split('\t', 1)
                        if len(parts) >= 2:
                            status = parts[0][:2] if len(parts[0]) >= 2 else parts[0]
                            filename = parts[1]

                # 파일명이 추출되지 않은 경우
                if not filename:
                    logging.warning(f"라인 {line_num}: 파일명 추출 실패: '{line}'")
                    continue

                # 빈 파일명 체크
                if not filename.strip():
                    logging.warning(f"라인 {line_num}: 빈 파일명: '{line}'")
                    continue

                # 손상된 파일명 검사 제거 - 모든 파일명 허용

                # 디버깅을 위한 상세 로그
                logging.debug(f"라인 {line_num}: 원본='{line}', 상태='{status}', 파일명='{filename}'")

                # 인코딩 문제가 있는 파일명 감지
                if '/3' in filename and len(filename) > 50:
                    logging.warning(f"⚠️ 인코딩 문제 의심 파일 감지 - 라인 {line_num}: {filename[:50]}...")
                    # 실제 파일 시스템에서 확인
                    try:
                        git_root_path = Path(git_root)
                        if filename.endswith('.csv') and 'history' in filename:
                            # history 디렉토리의 최근 CSV 파일들로 대체
                            history_dir = git_root_path / 'history'
                            if history_dir.exists():
                                recent_csvs = sorted(history_dir.rglob('*.csv'),
                                                   key=lambda f: f.stat().st_mtime, reverse=True)
                                if recent_csvs:
                                    # 가장 최근 파일로 대체 (임시)
                                    corrected = recent_csvs[0].relative_to(git_root_path)
                                    filename = str(corrected).replace('\\', '/')
                                    logging.info(f"   🔧 인코딩 문제 파일 대체: -> '{filename}'")
                    except Exception as fix_error:
                        logging.debug(f"인코딩 문제 파일 수정 실패: {fix_error}")

                # 🚀 성능 최적화: main.py 관련 로깅 제거 (성능 향상)
                # main.py 관련 특별 로그
                if 'main.py' in filename:
                    # logging.info(f"🔍 main.py 발견 - 라인 {line_num}: 원본='{line}', 상태='{status}', 파일명='{filename}'")
                    # logging.info(f"   파일명 길이: {len(filename)}, 바이트: {filename.encode('utf-8')}")

                    # 경로 수정 시도 (임시 해결책)
                    if filename.startswith('7_Python_DB_Refactoring/') and not filename.startswith('07_'):
                        original_filename = filename
                        filename = '0' + filename  # 앞에 0 추가
                        # logging.info(f"   🔧 경로 수정: '{original_filename}' -> '{filename}'")

                # 파일명 정규화 (백슬래시를 슬래시로)
                filename = filename.replace('\\', '/')

                # 따옴표 제거 (Git이 특수 문자가 포함된 파일명을 따옴표로 감쌀 수 있음)
                filename = filename.strip('"\'')

                # 알려진 경로 패턴 수정
                filename = self._fix_known_path_issues(filename)

                # Git status에서 반환된 경로 정규화 (중복 제거)
                current_dir_name = Path.cwd().name
                if filename.startswith(f"{current_dir_name}/"):
                    original_filename = filename
                    filename = filename[len(current_dir_name)+1:]
                    logging.debug(f"Git status 경로 정규화: '{original_filename}' -> '{filename}'")

                # 상태 해석
                change_type = "수정됨"
                if status.startswith('A'):
                    change_type = "추가됨"
                elif status.startswith('D'):
                    change_type = "삭제됨"
                elif status.startswith('M'):
                    change_type = "수정됨"
                elif status.startswith('R'):
                    change_type = "이름변경"
                elif status.startswith('??'):
                    change_type = "추가됨"

                # 파일 타입 분류
                is_csv = filename.endswith('.csv')
                is_db = filename.endswith('.db') and not filename.startswith('backup') and 'backup' not in filename

                changed_files.append({
                    'filename': filename,
                    'status': status,
                    'change_type': change_type,
                    'is_csv': is_csv,
                    'is_db': is_db,
                    'default_check': is_csv or is_db  # CSV와 실제 DB 파일은 기본 체크
                })

            # 최종 필터링: 유효한 파일만 반환
            valid_files = []
            for file_info in changed_files:
                filename = file_info['filename']

                # 기본 유효성 검사
                if (len(filename) < 200 and  # 너무 긴 경로 제외
                    not '/3' in filename and  # 유니코드 이스케이프 제외
                    filename.strip()):  # 빈 파일명 제외
                    valid_files.append(file_info)
                else:
                    # 🚀 성능 최적화: 유효하지 않은 파일 로깅 제거
                    # logging.info(f"유효하지 않은 파일 제외: {filename[:50]}...")
                    pass

            # 🚀 성능 최적화: 파일 개수 로깅 제거 (성능 향상)
            # logging.info(f"유효한 파일 {len(valid_files)}개 / 전체 {len(changed_files)}개")
            return valid_files

        except Exception as e:
            logging.error(f"변경된 파일 목록 가져오기 실패: {e}")
            return []

    def _fix_known_path_issues(self, filename: str) -> str:
        """알려진 경로 문제 수정 (유니코드 이스케이프 디코딩)"""
        try:
            # 유니코드 이스케이프 시퀀스 디코딩
            if '/3' in filename:  # 한글 유니코드 범위
                decoded_filename = self._decode_unicode_escape_path(filename)
                if decoded_filename != filename:
                    logging.info(f"🔧 유니코드 디코딩: '{filename[:30]}...' -> '{decoded_filename}'")
                    filename = decoded_filename

            # 동적 경로 수정 - 현재 디렉토리 이름 기반
            current_dir_name = Path.cwd().name

            # 0이 빠진 디렉토리 이름 패턴 수정 (예: 7_Python_DB_Refactoring -> 07_Python_DB_Refactoring)
            if current_dir_name.startswith('0') and len(current_dir_name) > 1:
                # 현재 디렉토리가 0으로 시작하는 경우, 0이 빠진 패턴 찾기
                short_name = current_dir_name[1:]  # 0 제거
                if filename.startswith(f'{short_name}/'):
                    corrected = current_dir_name + filename[len(short_name):]
                    logging.info(f"🔧 동적 경로 수정: '{filename}' -> '{corrected}'")
                    return corrected

            return filename

        except Exception as e:
            logging.warning(f"경로 수정 중 오류: {e}")
            return filename

    def _decode_unicode_escape_path(self, path: str) -> str:
        """유니코드 이스케이프 시퀀스가 포함된 경로 디코딩"""
        try:
            import re

            # /숫자/숫자/숫자 패턴을 찾아서 유니코드 문자로 변환
            def replace_unicode_escape(match):
                try:
                    # /354/240/204 형태를 \354\240\204 형태로 변환
                    numbers = match.group(0).split('/')[1:]  # 첫 번째 빈 문자열 제거
                    if len(numbers) == 3:
                        # 8진수를 바이트로 변환
                        byte_values = [int(num, 8) for num in numbers]
                        # 바이트를 UTF-8 문자로 디코딩
                        char = bytes(byte_values).decode('utf-8', errors='ignore')
                        return char
                except:
                    return match.group(0)  # 변환 실패 시 원본 반환
                return match.group(0)

            # /숫자/숫자/숫자 패턴 찾기 (한글 유니코드 범위)
            pattern = r'/3[0-7][0-7]/[0-7][0-7][0-7]/[0-7][0-7][0-7]'
            decoded_path = re.sub(pattern, replace_unicode_escape, path)

            # 추가 패턴들도 처리
            patterns = [
                r'/3[0-7][0-7]/[0-7][0-7][0-7]/[0-7][0-7][0-7]',  # 한글
                r'/2[0-7][0-7]/[0-7][0-7][0-7]/[0-7][0-7][0-7]',  # 기타 문자
            ]

            for pattern in patterns:
                decoded_path = re.sub(pattern, replace_unicode_escape, decoded_path)

            return decoded_path

        except Exception as e:
            logging.debug(f"유니코드 이스케이프 디코딩 실패: {e}")
            return path

    def _find_similar_file(self, problematic_filename: str) -> str:
        """문제가 있는 파일명과 유사한 실제 파일 찾기"""
        try:
            # 파일명에서 확장자 추출
            if problematic_filename.endswith('.csv'):
                # CSV 파일인 경우 history 디렉토리에서 유사한 파일 찾기
                history_dir = Path(self.project_root) / 'history'
                if history_dir.exists():
                    # 최근 생성된 CSV 파일들 찾기
                    csv_files = list(history_dir.rglob('*.csv'))
                    if csv_files:
                        # 가장 최근 파일 반환 (임시 해결책)
                        latest_file = max(csv_files, key=lambda f: f.stat().st_mtime)
                        relative_path = latest_file.relative_to(self.project_root)
                        return str(relative_path).replace('\\', '/')

            return problematic_filename

        except Exception as e:
            logging.warning(f"유사 파일 찾기 실패: {e}")
            return problematic_filename

    def _find_actual_file(self, filename: str, git_root: str) -> str:
        """실제 존재하는 파일 찾기"""
        try:
            # 1. 원본 파일명 그대로 확인
            file_path = Path(git_root) / filename
            if file_path.exists():
                return filename

            # 2. 파일명에서 확장자와 기본 정보 추출
            if filename.endswith('.csv'):
                # CSV 파일인 경우
                base_name = Path(filename).name

                # history 디렉토리에서 유사한 이름의 파일 찾기
                history_dir = Path(git_root) / 'history'
                if history_dir.exists():
                    for csv_file in history_dir.rglob('*.csv'):
                        if csv_file.name == base_name:
                            relative_path = csv_file.relative_to(git_root)
                            return str(relative_path).replace('\\', '/')

                # 부분 매칭으로 유사한 파일 찾기
                for csv_file in history_dir.rglob('*.csv'):
                    if any(part in csv_file.name for part in base_name.split('_') if len(part) > 3):
                        relative_path = csv_file.relative_to(git_root)
                        logging.info(f"부분 매칭 파일 발견: {relative_path}")
                        return str(relative_path).replace('\\', '/')

            # 3. 찾지 못한 경우 원본 반환
            return filename

        except Exception as e:
            logging.warning(f"실제 파일 찾기 실패: {e}")
            return filename

    def _is_corrupted_filename(self, filename: str) -> bool:
        """손상된 파일명인지 확인 (수정된 버전)"""
        try:
            # 1. 유니코드 이스케이프 시퀀스 패턴만 감지 (더 정확한 패턴)
            import re
            # /354/240/204 같은 연속된 8진수 패턴만 감지
            if re.search(r'/3[0-7][0-7]/[0-7][0-7][0-7]/[0-7][0-7][0-7]', filename):
                logging.debug(f"유니코드 이스케이프 패턴 감지: {filename[:50]}...")
                return True

            # 2. 극도로 긴 경로만 제외 (500자 이상)
            if len(filename) > 500:
                logging.debug(f"극도로 긴 경로 감지: {len(filename)}자")
                return True

            # 3. 정상적인 한글 파일명은 허용
            # "전류제어", "Base Cal" 등은 정상적인 파일명

            return False

        except Exception as e:
            logging.debug(f"파일명 검증 중 오류: {e}")
            return False

    def _cleanup_git_encoding_issues(self, git_root: str):
        """Git 인코딩 문제 정리"""
        try:
            # Git 설정 정리
            cleanup_commands = [
                [self.git_executable, 'config', 'core.quotepath', 'false'],
                [self.git_executable, 'config', 'core.precomposeunicode', 'true'],
                [self.git_executable, 'config', 'core.autocrlf', 'false'],
                [self.git_executable, 'config', 'i18n.filesEncoding', 'utf-8'],
                [self.git_executable, 'config', 'i18n.logOutputEncoding', 'utf-8']
            ]

            for cmd in cleanup_commands:
                try:
                    subprocess.run(cmd, cwd=git_root, capture_output=True, timeout=5)
                except:
                    continue

            # Git 인덱스 새로고침 시도 (인코딩 안전)
            try:
                subprocess.run([self.git_executable, 'update-index', '--refresh'],
                             cwd=git_root, capture_output=True,
                             encoding='utf-8', errors='replace', timeout=10)
            except Exception as refresh_error:
                logging.debug(f"Git 인덱스 새로고침 실패 (무시됨): {refresh_error}")

            logging.debug("Git 인코딩 설정 정리 완료")

        except Exception as e:
            logging.debug(f"Git 정리 중 오류: {e}")

    def _normalize_git_path(self, filename: str, current_cwd: Path) -> str:
        """Git 경로 정규화 - 중복 경로 제거 및 따옴표 제거"""
        try:
            # 1. 따옴표 제거
            cleaned_filename = filename.strip('"\'')
            if cleaned_filename != filename:
                logging.debug(f"따옴표 제거: '{filename}' -> '{cleaned_filename}'")
                filename = cleaned_filename

            # 2. 현재 작업 디렉토리 이름 추출
            cwd_name = current_cwd.name  # 동적으로 현재 디렉토리 이름 사용

            # 3. 경로가 현재 디렉토리 이름으로 시작하는 경우 제거
            if filename.startswith(f"{cwd_name}/"):
                normalized = filename[len(cwd_name)+1:]  # "07_Python_DB_Refactoring/" 제거
                logging.debug(f"경로 중복 제거: '{filename}' -> '{normalized}'")
                return normalized

            # 4. 절대 경로인 경우 상대 경로로 변환
            if filename.startswith(str(current_cwd)):
                normalized = os.path.relpath(filename, current_cwd)
                logging.debug(f"절대 경로를 상대 경로로 변환: '{filename}' -> '{normalized}'")
                return normalized

            # 5. 이미 정규화된 경로
            return filename

        except Exception as e:
            logging.warning(f"경로 정규화 실패: {e}")
            return filename

    def _is_file_ignored(self, filename: str, git_execution_dir: Path) -> bool:
        """
        파일이 실제로 Git에 의해 무시되는지 확인 (이미 추적 중인 파일은 제외)

        Args:
            filename: 확인할 파일 경로
            git_execution_dir: Git 실행 디렉토리

        Returns:
            True if 파일이 무시되고 추적되지 않음, False otherwise
        """
        try:
            # 1. 먼저 파일이 이미 Git에 의해 추적되고 있는지 확인
            # git ls-files로 추적 중인 파일인지 확인
            ls_files_result = subprocess.run(
                [self.git_executable, 'ls-files', '--', filename],
                cwd=git_execution_dir,
                capture_output=True,
                text=True,
                timeout=10
            )

            # 파일이 이미 추적 중이면 무시되지 않음
            if ls_files_result.returncode == 0 and ls_files_result.stdout.strip():
                logging.debug(f"이미 추적 중인 파일: {filename}")
                return False

            # 2. 추적되지 않는 파일이면 .gitignore 확인
            check_ignore_result = subprocess.run(
                [self.git_executable, 'check-ignore', filename],
                cwd=git_execution_dir,
                capture_output=True,
                text=True,
                timeout=10
            )

            # 반환 코드가 0이면 파일이 무시됨
            is_ignored = check_ignore_result.returncode == 0

            if is_ignored:
                logging.debug(f"무시된 파일 감지: {filename}")
            else:
                logging.debug(f"추적 가능한 파일: {filename}")

            return is_ignored

        except subprocess.TimeoutExpired:
            logging.warning(f"git 파일 상태 확인 타임아웃: {filename}")
            return False  # 타임아웃 시 무시되지 않는 것으로 간주
        except Exception as e:
            logging.warning(f"git 파일 상태 확인 실패: {filename}, 오류: {e}")
            return False  # 오류 시 무시되지 않는 것으로 간주

    def _get_git_execution_directory(self, filenames: List[str] = None, single_file: str = None) -> Path:
        """Git 명령어 실행에 적합한 디렉토리 결정"""
        try:
            current_cwd = Path.cwd()

            # 단일 파일 처리
            if single_file:
                filenames = [single_file]

            if not filenames:
                return current_cwd

            # 실제 파일 위치를 확인하여 Git 실행 디렉토리 결정
            for filename in filenames:
                normalized_filename = self._normalize_git_path(filename, current_cwd)

                # 현재 디렉토리에서 파일 확인
                current_path = current_cwd / normalized_filename
                parent_path = current_cwd.parent / normalized_filename

                if current_path.exists():
                    # 현재 디렉토리에 파일이 있으면 현재 디렉토리 사용
                    logging.debug(f"파일 '{normalized_filename}' 현재 디렉토리에 존재")
                    continue
                elif parent_path.exists():
                    # 상위 디렉토리에 파일이 있으면 상위 디렉토리 사용
                    logging.debug(f"파일 '{normalized_filename}' 상위 디렉토리에 존재")
                    return current_cwd.parent
                else:
                    logging.debug(f"파일 '{normalized_filename}' 위치를 찾을 수 없음")

            # 모든 파일이 현재 디렉토리에 있거나 찾을 수 없으면 현재 디렉토리 사용
            return current_cwd

        except Exception as e:
            logging.warning(f"Git 실행 디렉토리 결정 실패: {e}")
            return Path.cwd()

    def _normalize_git_root(self, git_root: str) -> str:
        """Git 루트 경로 정규화 (네트워크 경로 처리)"""
        try:
            if git_root.startswith('//'):
                # 현재 작업 디렉토리를 기준으로 실제 경로 찾기
                current_cwd = Path.cwd()
                if str(current_cwd).replace('\\', '/') in git_root.replace('\\', '/'):
                    # 현재 디렉토리 기준으로 Git 루트 재계산
                    normalized_root = str(current_cwd)
                    while normalized_root and not (Path(normalized_root) / '.git').exists():
                        parent = str(Path(normalized_root).parent)
                        if parent == normalized_root:  # 루트에 도달
                            break
                        normalized_root = parent
                    logging.debug(f"네트워크 경로 정규화: {git_root} -> {normalized_root}")
                    return normalized_root

            return git_root

        except Exception as e:
            logging.warning(f"Git 루트 정규화 실패: {e}")
            return git_root

    def get_file_diff(self, filename: str) -> str:
        """특정 파일의 diff 가져오기 (경로 문제 해결)"""
        try:
            # Git 저장소 루트 디렉토리 사용 및 경로 정규화
            git_root = self.get_git_root()

            # 네트워크 경로를 로컬 경로로 변환 (동적)
            if git_root.startswith('//'):
                current_cwd = Path.cwd()
                if str(current_cwd).replace('\\', '/') in git_root.replace('\\', '/'):
                    git_root = str(current_cwd)
                    while git_root and not (Path(git_root) / '.git').exists():
                        parent = str(Path(git_root).parent)
                        if parent == git_root:
                            break
                        git_root = parent
                    logging.debug(f"diff용 네트워크 경로 변환: {git_root}")

            # 현재 작업 디렉토리 기준으로 Git 실행 디렉토리 결정
            current_cwd = Path.cwd()

            # 파일명 정규화
            normalized_filename = self._normalize_git_path(filename, current_cwd)
            logging.debug(f"diff용 파일명 정규화: '{filename}' -> '{normalized_filename}'")

            # 실제 파일 위치에 따라 Git 실행 디렉토리 결정
            current_path = current_cwd / normalized_filename
            parent_path = current_cwd.parent / normalized_filename

            if current_path.exists():
                git_execution_dir = current_cwd
                logging.debug(f"diff - 현재 디렉토리에서 파일 발견: {current_path}")
            elif parent_path.exists():
                git_execution_dir = current_cwd.parent
                logging.debug(f"diff - 상위 디렉토리에서 파일 발견: {parent_path}")
            else:
                # 파일을 찾을 수 없으면 현재 디렉토리 사용 (Git이 알고 있을 수 있음)
                git_execution_dir = current_cwd
                logging.debug(f"diff - 파일 위치 불명, 현재 디렉토리 사용: {current_cwd}")

            # 인코딩 문제 해결을 위한 환경변수 설정
            env = os.environ.copy()
            env['PYTHONIOENCODING'] = 'utf-8'
            env['LC_ALL'] = 'C.UTF-8'

            # 다양한 diff 명령어 시도 (정규화된 파일명 사용)
            diff_commands = [
                # Working directory 변경사항 (unstaged)
                [self.git_executable, 'diff', '--', normalized_filename],
                # Staged 변경사항 (cached)
                [self.git_executable, 'diff', '--cached', '--', normalized_filename],
                # HEAD와 비교 (모든 변경사항)
                [self.git_executable, 'diff', 'HEAD', '--', normalized_filename]
            ]

            for i, cmd in enumerate(diff_commands):
                try:
                    logging.info(f"diff 명령어 {i+1}/{len(diff_commands)}: {' '.join(cmd)} (디렉토리: {git_execution_dir})")

                    result = subprocess.run(
                        cmd,
                        cwd=git_execution_dir,  # 결정된 Git 실행 디렉토리 사용
                        capture_output=True,
                        text=True,
                        encoding='utf-8',
                        errors='replace',
                        env=env,
                        timeout=30
                    )

                    if result.stdout and result.stdout.strip():
                        logging.info(f"✅ diff 명령어 {i+1}에서 결과 발견: {len(result.stdout)} 문자")
                        return result.stdout
                    else:
                        logging.info(f"❌ diff 명령어 {i+1}: 결과 없음")

                except subprocess.CalledProcessError as cmd_error:
                    logging.warning(f"❌ diff 명령어 {i+1} 실패: {cmd_error}")
                    continue
                except subprocess.TimeoutExpired:
                    logging.warning(f"❌ diff 명령어 {i+1} 타임아웃")
                    continue

            # diff가 없는 경우 파일 상태 확인
            try:
                status_result = subprocess.run(
                    [self.git_executable, 'status', '--porcelain', '--', normalized_filename],
                    cwd=git_execution_dir,  # 결정된 Git 실행 디렉토리 사용
                    capture_output=True,
                    text=True,
                    encoding='utf-8',
                    errors='replace',
                    env=env,
                    timeout=10
                )

                status_output = status_result.stdout or ""

                if status_output.strip():
                    # 파일에 변경사항이 있음
                    if status_output.startswith('??') or status_output.startswith('A'):
                        # 새 파일인 경우 전체 내용 표시
                        try:
                            # 올바른 디렉토리에서 파일 찾기
                            file_path = git_execution_dir / normalized_filename
                            if file_path.exists():
                                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                                    content = f.read()
                                    if len(content) > 5000:  # 너무 큰 파일은 일부만 표시
                                        content = content[:5000] + "\n\n... (파일이 너무 커서 일부만 표시됨)"
                                    return f"새 파일: {normalized_filename}\n\n파일 크기: {len(content)} 문자\n{'='*50}\n\n{content}"
                            else:
                                return f"새 파일: {normalized_filename}\n\n(파일을 읽을 수 없습니다: {file_path})"
                        except Exception as read_error:
                            return f"새 파일: {normalized_filename}\n\n(파일 읽기 실패: {str(read_error)})"
                    else:
                        # 수정된 파일이지만 diff가 없는 경우
                        return f"파일 '{normalized_filename}'이 수정되었지만 diff를 가져올 수 없습니다.\n\n" + \
                               "가능한 원인:\n" + \
                               "• 바이너리 파일 (이미지, 실행파일 등)\n" + \
                               "• 파일 권한 변경만 있는 경우\n" + \
                               "• Git 설정 문제"
                else:
                    return f"파일 '{normalized_filename}'에 변경사항이 없습니다."

            except Exception as status_error:
                return f"파일 상태 확인 실패: {status_error}"

        except Exception as e:
            logging.error(f"파일 diff 가져오기 실패 ({filename}): {e}")
            return f"diff 가져오기 실패: {str(e)}"

    def commit_selected_files(self, selected_files: List[str], commit_message: str, target_branch: str = None) -> bool:
        """선택된 파일들만 커밋 및 푸시 (개선된 버전)"""
        try:
            logging.info(f"선택된 파일들 커밋 시작: {selected_files}")

            # 대상 브랜치 결정
            if not target_branch:
                target_branch = self.get_current_branch()

            logging.info(f"대상 브랜치: {target_branch}")

            # Git 저장소 루트 디렉토리 사용 (경로 정규화)
            git_root = self.get_git_root()

            # 네트워크 경로를 로컬 경로로 변환 (동적)
            original_git_root = git_root
            if git_root.startswith('//'):
                # 현재 작업 디렉토리를 기준으로 실제 경로 찾기
                current_cwd = Path.cwd()
                # 현재 디렉토리가 Git 저장소 내부인지 확인
                if str(current_cwd).replace('\\', '/') in git_root.replace('\\', '/'):
                    # 현재 디렉토리 기준으로 Git 루트 재계산
                    git_root = str(current_cwd)
                    while git_root and not (Path(git_root) / '.git').exists():
                        parent = str(Path(git_root).parent)
                        if parent == git_root:  # 루트에 도달
                            break
                        git_root = parent
                    logging.info(f"네트워크 경로를 로컬 경로로 변환: {original_git_root} -> {git_root}")
                else:
                    logging.debug(f"네트워크 경로 변환 실패, 원본 사용: {git_root}")

            # 인코딩 문제 해결을 위한 환경변수 설정
            env = os.environ.copy()
            env['PYTHONIOENCODING'] = 'utf-8'
            env['LC_ALL'] = 'C.UTF-8'

            # Git 명령어 실행 디렉토리 결정 (실제 파일 위치 기반)
            current_cwd = Path.cwd()
            git_execution_dir = current_cwd  # 기본값

            # 실제 파일 위치를 확인하여 Git 실행 디렉토리 결정
            for filename in selected_files:
                normalized_filename = self._normalize_git_path(filename, current_cwd)

                # 현재 디렉토리에서 파일 확인
                current_path = current_cwd / normalized_filename
                parent_path = current_cwd.parent / normalized_filename

                if current_path.exists():
                    # 현재 디렉토리에 파일이 있으면 현재 디렉토리 사용
                    git_execution_dir = current_cwd
                    logging.debug(f"파일 '{normalized_filename}' 현재 디렉토리에 존재")
                elif parent_path.exists():
                    # 상위 디렉토리에 파일이 있으면 상위 디렉토리 사용
                    git_execution_dir = current_cwd.parent
                    logging.info(f"파일 '{normalized_filename}' 상위 디렉토리에 존재 - Git 실행 디렉토리 변경: {git_execution_dir}")
                    break  # 하나라도 상위에 있으면 상위 디렉토리 사용
                else:
                    logging.warning(f"파일 '{normalized_filename}' 위치를 찾을 수 없음")

            logging.info(f"최종 Git 실행 디렉토리: {git_execution_dir}")

            logging.info(f"선택된 파일들: {selected_files}")

            # 선택된 파일들 중 .gitignore에 의해 무시되지 않는 파일만 필터링
            valid_files = []
            for filename in selected_files:
                try:
                    # 경로 정규화
                    normalized_filename = self._normalize_git_path(filename, current_cwd)

                    # .gitignore에 의해 무시되는 파일인지 확인
                    if self._is_file_ignored(normalized_filename, git_execution_dir):
                        logging.warning(f"⚠️ 무시된 파일 스킵: {normalized_filename}")
                        continue

                    valid_files.append(normalized_filename)
                except Exception as e:
                    logging.error(f"파일 검증 중 오류: {filename}, 오류: {e}")
                    continue

            if not valid_files:
                logging.error("❌ 스테이징할 유효한 파일이 없습니다 (모든 파일이 .gitignore에 의해 무시됨)")
                return False

            logging.info(f"📋 스테이징 대상 파일: {len(valid_files)}개 (전체 {len(selected_files)}개 중)")

            # 유효한 파일들만 스테이징
            staging_success_count = 0
            staging_total_count = len(valid_files)

            for normalized_filename in valid_files:
                try:
                    logging.info(f"경로 정규화: '{filename}' -> '{normalized_filename}'")

                    # 파일 존재 확인 및 경로 조정
                    file_path = current_cwd / normalized_filename
                    final_filename = normalized_filename
                    git_cwd = current_cwd

                    if file_path.exists():
                        logging.debug(f"✅ 현재 디렉토리에서 파일 발견: {file_path}")
                    else:
                        logging.debug(f"📁 현재 디렉토리에 파일 없음 (정상): {file_path}")
                        # 상위 디렉토리에서 찾기 시도
                        parent_path = current_cwd.parent / normalized_filename
                        if parent_path.exists():
                            logging.info(f"✅ 상위 디렉토리에서 파일 발견: {parent_path}")
                            # Git 명령어를 상위 디렉토리에서 실행
                            git_cwd = current_cwd.parent
                            logging.info(f"🔄 Git 실행 디렉토리 변경: {git_cwd}")
                        else:
                            logging.error(f"❌ 상위 디렉토리에도 파일 없음: {parent_path}")

                    # DB 파일인 경우 특별 처리
                    if final_filename.endswith('.db'):
                        logging.info(f"DB 파일 감지: {final_filename}")
                        # DB 파일이 잠겨있을 수 있으므로 강제 추가 시도
                        try:
                            # 먼저 일반적인 add 시도
                            result = subprocess.run(
                                [self.git_executable, 'add', final_filename],
                                cwd=git_cwd,
                                capture_output=True,
                                text=True,
                                encoding='utf-8',
                                errors='replace',
                                env=env,
                                timeout=30
                            )

                            if result.returncode != 0:
                                # 실패하면 강제 추가 시도
                                logging.warning(f"일반 add 실패, 강제 add 시도: {final_filename}")
                                result = subprocess.run(
                                    [self.git_executable, 'add', '--force', final_filename],
                                    cwd=git_cwd,
                                    capture_output=True,
                                    text=True,
                                    encoding='utf-8',
                                    errors='replace',
                                    env=env,
                                    timeout=30
                                )
                        except Exception as db_error:
                            logging.error(f"DB 파일 add 중 예외: {db_error}")
                            result = subprocess.run(['echo', 'DB add failed'], capture_output=True, text=True)
                            result.returncode = 1
                    else:
                        # 일반 파일 처리
                        logging.info(f"Git add 실행: '{final_filename}' (디렉토리: {git_cwd})")
                        result = subprocess.run(
                            [self.git_executable, 'add', final_filename],
                            cwd=git_cwd,
                            capture_output=True,
                            text=True,
                            encoding='utf-8',
                            errors='replace',
                            env=env,
                            timeout=30
                        )

                    if result.returncode == 0:
                        logging.info(f"✅ 스테이징 성공: {normalized_filename}")
                        staging_success_count += 1
                    else:
                        # 에러 메시지 그대로 출력 (디버깅을 위해)
                        logging.error(f"❌ 스테이징 실패: \"{normalized_filename}\"")
                        logging.error(f"Git add stderr: {result.stderr}")
                        logging.error(f"Git add stdout: {result.stdout}")

                except subprocess.TimeoutExpired:
                    logging.error(f"Git add 타임아웃: {filename}")
                    continue
                except Exception as e:
                    logging.error(f"Git add 예외: {filename}, 오류: {e}")
                    continue

            # 스테이징 결과 검증
            logging.info(f"📊 스테이징 결과: {staging_success_count}/{staging_total_count} 성공")

            if staging_success_count == 0:
                logging.error("❌ 모든 파일 스테이징 실패 - 커밋 중단")
                return False
            elif staging_success_count < staging_total_count:
                logging.warning(f"⚠️ 일부 파일만 스테이징 성공 ({staging_success_count}/{staging_total_count})")
                # 부분 성공도 계속 진행하지만 최종 결과에 반영

            # 커밋 (변경사항이 없으면 스킵)
            try:
                commit_result = subprocess.run(
                    [self.git_executable, 'commit', '-m', commit_message],
                    cwd=git_execution_dir,  # 결정된 Git 실행 디렉토리 사용
                    capture_output=True,
                    text=True,
                    encoding='utf-8',
                    errors='replace',
                    env=env,
                    timeout=60
                )

                if commit_result.returncode != 0:
                    if "nothing to commit" in commit_result.stdout or "nothing to commit" in commit_result.stderr:
                        logging.info("커밋할 새로운 변경사항이 없음")
                        return True
                    else:
                        logging.error(f"Git commit 실패: {commit_result.stderr}")
                        return False

                logging.info(f"커밋 완료: {commit_message}")

            except subprocess.TimeoutExpired:
                logging.error("Git commit 타임아웃 (60초)")
                return False

            # 푸시
            try:
                push_result = subprocess.run(
                    [self.git_executable, 'push', 'origin', target_branch],
                    cwd=git_execution_dir,  # 결정된 Git 실행 디렉토리 사용
                    capture_output=True,
                    text=True,
                    encoding='utf-8',
                    errors='replace',
                    env=env,
                    timeout=120
                )

                if push_result.returncode != 0:
                    logging.error(f"Git push 실패: {push_result.stderr}")
                    return False

                logging.info(f"선택된 파일들 Git push 완료: {target_branch}")

            except subprocess.TimeoutExpired:
                logging.error("Git push 타임아웃 (120초)")
                return False

            # 최종 결과 판정
            if staging_success_count == staging_total_count:
                logging.info(f"🎉 모든 작업 성공: {staging_total_count}개 파일 커밋/푸시 완료")
                return True
            else:
                logging.warning(f"⚠️ 부분 성공: {staging_success_count}/{staging_total_count} 파일만 처리됨")
                return False  # 부분 실패는 실패로 처리

        except subprocess.CalledProcessError as e:
            logging.error(f"선택된 파일들 Git 커밋/푸시 실패: {e}")
            return False
        except Exception as e:
            logging.error(f"선택된 파일들 Git 작업 중 오류: {e}")
            return False






class DBHistoryManager:
    """DB 히스토리 관리 클래스"""

    def __init__(self, git_manager: GitManager):
        """
        DBHistoryManager 초기화

        Args:
            git_manager: GitManager 인스턴스
        """
        self.git_manager = git_manager

    def startup_routine(self, db_files: List[str]) -> bool:
        """앱 시작 시 루틴 (강제 pull + 백업)"""
        try:
            logging.info("앱 시작 루틴 시작...")

            # 1. 강제 Git pull
            if not self.git_manager.force_pull():
                logging.error("Git pull 실패")
                return False

            # 2. DB 백업 생성
            if not self.git_manager.create_backup(db_files):
                logging.error("백업 생성 실패")
                return False

            logging.info("앱 시작 루틴 완료")
            return True

        except Exception as e:
            logging.error(f"앱 시작 루틴 중 오류: {e}")
            return False

    def commit_changes(self, commit_message: str) -> bool:
        """변경사항 커밋 (Git 상태 기반 단순 커밋)"""
        try:
            logging.info("변경사항 커밋 시작...")

            # Git 커밋 및 푸시 (실시간 CSV가 이미 업데이트되어 있음)
            if not self.git_manager.commit_and_push(commit_message):
                logging.error("Git 커밋/푸시 실패")
                return False

            logging.info("변경사항 커밋 완료")
            return True

        except Exception as e:
            logging.error(f"변경사항 커밋 중 오류: {e}")
            return False
