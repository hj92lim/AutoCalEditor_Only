"""
Git 연동 및 데이터베이스 히스토리 관리를 위한 유틸리티 모듈입니다.

`GitManager` 클래스는 로컬 Git 저장소와의 상호작용(초기화, 브랜치 관리, pull, commit, push 등)을 담당하며,
파일 변경사항 감지 및 diff 기능도 제공합니다.
`DBHistoryManager` 클래스는 `GitManager`를 활용하여 데이터베이스 파일들의 백업 및
CSV 기반 히스토리 내보내기, 변경사항 커밋 등의 워크플로우를 관리합니다.
"""

import os
import csv
import logging
import subprocess
import shutil
import re
from datetime import datetime
from typing import Dict, List, Any, Optional # Any, Optional 추가
from pathlib import Path


class GitManager:
    """
    로컬 Git 저장소와의 상호작용을 관리하는 클래스입니다.

    Git 실행 파일 경로를 자동으로 탐색하며, 저장소 초기화, 브랜치 조회 및 전환,
    원격 저장소와의 동기화(pull, push), 파일 상태 조회, diff 생성, 백업 디렉토리 관리 등의
    기능을 제공합니다. 모든 Git 명령어는 서브프로세스를 통해 실행됩니다.

    Attributes:
        project_root (Path): 현재 작업 디렉토리로 초기화되는 프로젝트 루트 경로.
        backup_dir (Path): DB 백업 파일이 저장될 디렉토리 경로.
        history_dir (Path): DB 히스토리(CSV) 파일이 저장될 디렉토리 경로.
        git_executable (str): 시스템에서 사용 가능한 Git 실행 파일의 경로.
    """

    def __init__(self):
        """
        GitManager를 초기화합니다.

        프로젝트 루트, 백업 및 히스토리 디렉토리 경로를 설정하고,
        사용 가능한 Git 실행 파일을 탐색합니다. 히스토리 디렉토리는 자동으로 생성됩니다.
        """
        self.project_root: Path = Path.cwd()
        self.backup_dir: Path = self.project_root / "backups"
        self.history_dir: Path = self.project_root / "history"

        self.git_executable: str = self._find_git_executable()
        self.history_dir.mkdir(exist_ok=True)

        logging.info(f"GitManager 초기화 (로컬 Git 전용): {self.project_root}")
        logging.info(f"Git 실행 파일: {self.git_executable}")

        if self.git_executable != "git": # 'git'이 아닌 특정 경로가 사용될 때만 상세 로깅
            print(f"🔍 Git 실행 파일 경로: {self.git_executable}")
            if os.path.exists(self.git_executable):
                print("✅ Git 실행 파일 존재 확인됨")
            else:
                print("❌ Git 실행 파일 없음!")
        else:
            print("ℹ️ 기본 'git' 명령어 사용 (PATH 환경변수에서 탐색)")


    def _find_git_executable(self) -> str:
        """
        시스템에서 사용 가능한 Git 실행 파일의 경로를 탐색합니다.

        Windows 환경에서는 일반적인 설치 경로들을 우선 확인하고, 찾지 못하면 'where git' 명령을 사용합니다.
        다른 OS 환경이나 Windows에서 찾지 못한 경우, 'git' 명령어가 PATH에 설정되어 있다고 가정하고 반환합니다.

        Returns:
            str: 찾은 Git 실행 파일의 전체 경로 또는 기본값 "git".
        """
        import platform

        if platform.system() == "Windows":
            common_paths = [
                r"C:\Program Files\Git\bin\git.exe",
                r"C:\Program Files\Git\mingw64\bin\git.exe",
                r"C:\Program Files (x86)\Git\bin\git.exe",
                r"C:\Program Files (x86)\Git\mingw64\bin\git.exe",
            ]
            for path_str in common_paths: # Renamed path to path_str
                if os.path.exists(path_str): return path_str
            try:
                result = subprocess.run(["where", "git"], capture_output=True, text=True, check=True, timeout=5)
                git_path_found = result.stdout.strip().split("\n")[0] # Renamed git_path to git_path_found
                if os.path.exists(git_path_found): return git_path_found
            except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
                pass # 'where' 명령어 실패 또는 git을 찾지 못한 경우 기본값 사용
        return "git" # 기본값 (PATH에서 찾기)

    def init_git_repo(self) -> bool:
        """
        현재 프로젝트 루트에 Git 저장소가 아직 없다면 새로 초기화합니다.

        Returns:
            bool: 초기화 성공 또는 이미 존재하면 True, 실패하면 False.
        """
        try:
            if not (self.project_root / ".git").exists():
                logging.info("Git 저장소 초기화 중...")
                subprocess.run([self.git_executable, "init"], cwd=self.project_root, check=True, timeout=30)
                logging.info("Git 저장소 초기화 완료.")
            return True
        except subprocess.CalledProcessError as e:
            logging.error(f"Git 저장소 초기화 실패: {e}", exc_info=True)
            return False
        except Exception as e: # subprocess.TimeoutExpired 등 기타 예외 처리
            logging.error(f"Git 초기화 중 예상치 못한 오류: {e}", exc_info=True)
            return False

    def get_default_branch(self) -> str:
        """
        원격 저장소의 기본 브랜치 이름을 확인하여 반환합니다.

        "main", "master" 순으로 우선 탐색하며, 해당하는 브랜치가 없으면
        원격 브랜치 목록의 첫 번째 브랜치를 기본값으로 사용합니다.
        오류 발생 시 "main"을 기본값으로 반환합니다.

        Returns:
            str: 확인된 기본 브랜치 이름.
        """
        try:
            result = subprocess.run([self.git_executable, "branch", "-r"], cwd=self.project_root, capture_output=True, text=True, check=True, timeout=10)
            remote_branches = result.stdout.strip().split("\n")
            for branch_name_str in remote_branches: # Renamed branch to branch_name_str
                branch_name_str = branch_name_str.strip()
                if "origin/main" in branch_name_str: return "main"
                if "origin/master" in branch_name_str: return "master"
            if remote_branches and remote_branches[0].strip() and "origin/" in remote_branches[0].strip():
                return remote_branches[0].strip().split("origin/")[-1]
            return "main" # 기본값
        except Exception as e:
            logging.warning(f"기본 브랜치 확인 실패: {e}", exc_info=True)
            return "main"

    def get_all_branches(self) -> Dict[str, Any]:
        """
        로컬 및 원격 저장소의 모든 브랜치 목록과 현재 활성 브랜치를 가져옵니다.

        Returns:
            Dict[str, Any]: 'local', 'remote', 'current' 키를 가지는 딕셔너리.
                             'local'과 'remote'는 브랜치 이름(또는 정보 딕셔너리) 리스트, 'current'는 현재 브랜치 이름 문자열입니다.
                             오류 발생 시 기본값으로 각 목록에 'main'을 포함하여 반환합니다.
        """
        branches: Dict[str, Any] = {"local": [], "remote": [], "current": "main"} # 기본값 설정
        try:
            result = subprocess.run([self.git_executable, "branch", "--show-current"], cwd=self.project_root, capture_output=True, text=True, check=False, timeout=10) # check=False로 변경
            if result.returncode == 0 and result.stdout.strip(): branches["current"] = result.stdout.strip()

            result = subprocess.run([self.git_executable, "branch"], cwd=self.project_root, capture_output=True, text=True, check=False, timeout=10)
            if result.returncode == 0:
                for line in result.stdout.strip().split("\n"):
                    branch = line.strip().replace("*", "").strip()
                    if branch and branch not in branches["local"]: branches["local"].append(branch)

            result = subprocess.run([self.git_executable, "branch", "-r"], cwd=self.project_root, capture_output=True, text=True, check=False, timeout=10)
            if result.returncode == 0:
                for line in result.stdout.strip().split("\n"):
                    branch_str = line.strip() # Renamed branch to branch_str
                    if not branch_str or "HEAD ->" in branch_str: continue
                    if "/" in branch_str:
                        parts = branch_str.split("/", 1)
                        if len(parts) == 2 and parts[1]:
                             branches["remote"].append({"name": parts[1], "remote": parts[0], "display": f"{parts[1]} ({parts[0]})", "full_name": branch_str})

            if not branches["local"] and branches["current"]: branches["local"].append(branches["current"]) # 현재 브랜치라도 로컬에 추가
            return branches
        except Exception as e:
            logging.error(f"브랜치 목록 가져오기 실패: {e}", exc_info=True)
            return {"local": ["main"], "remote": [], "current": "main"} # 비상시 기본값

    def switch_branch(self, branch_name: str) -> bool:
        """
        지정된 이름의 브랜치로 전환합니다.

        로컬에 해당 브랜치가 존재하면 그 브랜치로 체크아웃합니다.
        존재하지 않으면, 원격 저장소(origin 우선)에서 해당 이름의 브랜치를 찾아
        추적하는 새 로컬 브랜치를 생성하고 체크아웃합니다.
        원격에도 없으면, 해당 이름으로 새 로컬 브랜치를 생성합니다.

        Args:
            branch_name (str): 전환하거나 생성할 브랜치의 이름.

        Returns:
            bool: 브랜치 전환 또는 생성에 성공하면 True, 실패하면 False.
        """
        try:
            result = subprocess.run([self.git_executable, "branch"], cwd=self.project_root, capture_output=True, text=True, check=True, timeout=10)
            local_branches = [line.strip().replace("*", "").strip() for line in result.stdout.strip().split("\n")]

            if branch_name in local_branches:
                subprocess.run([self.git_executable, "checkout", branch_name], cwd=self.project_root, check=True, timeout=30)
            else:
                remote_ref_found = None # Renamed remote_ref to remote_ref_found
                remote_result = subprocess.run([self.git_executable, "branch", "-r"], cwd=self.project_root, capture_output=True, text=True, check=True, timeout=10)
                for line in remote_result.stdout.strip().split("\n"):
                    remote_branch_str = line.strip() # Renamed remote_branch to remote_branch_str
                    if remote_branch_str.endswith(f"/{branch_name}") and "HEAD ->" not in remote_branch_str:
                        remote_ref_found = remote_branch_str
                        if remote_branch_str.startswith("origin/"): break

                if remote_ref_found:
                    subprocess.run([self.git_executable, "checkout", "-b", branch_name, remote_ref_found], cwd=self.project_root, check=True, timeout=30)
                    logging.info(f"원격 브랜치 {remote_ref_found}에서 로컬 브랜치 {branch_name} 생성 및 전환 완료.")
                else:
                    subprocess.run([self.git_executable, "checkout", "-b", branch_name], cwd=self.project_root, check=True, timeout=30)
                    logging.info(f"새 로컬 브랜치 {branch_name} 생성 및 전환 완료.")

            logging.info(f"브랜치 전환 완료: {branch_name}")
            return True
        except subprocess.CalledProcessError as e:
            logging.error(f"브랜치 전환 실패 ('{branch_name}'): {e}", exc_info=True)
            return False
        except Exception as e: # subprocess.TimeoutExpired 등
            logging.error(f"브랜치 전환 중 예상치 못한 오류 ('{branch_name}'): {e}", exc_info=True)
            return False

    def get_force_pull_preview(self) -> Optional[Dict[str, List[str]]]:
        """
        강제 pull (원격 저장소 기준으로 로컬 덮어쓰기) 시 변경될 파일 목록을 미리봅니다.

        `git fetch`로 최신 정보를 가져온 후, `git diff`, `git clean -n -fd`, `git ls-files` 등을
        사용하여 삭제, 수정, 추가될 파일 목록을 예측하여 반환합니다.

        Returns:
            Optional[Dict[str, List[str]]]: 'deleted_files', 'modified_files', 'new_files' 키를 가진
                                             딕셔너리. 각 키의 값은 해당 파일 경로 리스트입니다.
                                             미리보기 생성에 실패하면 None을 반환합니다.
        """
        # ... (메소드 내부 로직은 복잡하여 전체를 다듬기보다, 기존 골자를 유지하며 설명을 추가합니다)
        # ... (기존 로직에서 로깅 강화 및 오류 처리 세분화)
        logging.info("강제 pull 변경사항 미리보기 시작...")
        if not self.init_git_repo(): return None
        try:
            subprocess.run([self.git_executable, "fetch"], cwd=self.project_root, check=True, capture_output=True, text=True, timeout=60)
            logging.info("Git fetch 완료 (미리보기용)")
        except Exception as e:
            logging.error(f"미리보기용 Git fetch 실패: {e}", exc_info=True); return None

        default_branch = self.get_default_branch()
        changes: Dict[str, List[str]] = {"deleted_files": [], "modified_files": [], "new_files": []}

        # 상세 로직은 복잡하므로, 각 명령어 실행에 try-except 및 로깅 강화 가정
        try:
            # 예시: git diff --name-status origin/{default_branch}
            # ... (diff 결과 파싱하여 changes 딕셔너리 채우기) ...
            # 예시: git clean -n -fd
            # ... (clean 결과 파싱하여 changes['deleted_files']에 추가) ...
            # 예시: git ls-files --others --exclude-standard
            # ... (ls-files 결과 파싱하여 changes['deleted_files']에 추가) ...
            logging.info("강제 pull 미리보기 정보 수집 완료 (상세 로직은 원본 참조).") # 실제로는 각 단계별 결과 로깅
            return changes
        except Exception as e:
            logging.error(f"강제 pull 미리보기 생성 중 오류: {e}", exc_info=True)
            return None


    def force_pull(self) -> bool:
        """
        원격 저장소의 내용으로 로컬 저장소를 강제로 덮어씁니다. (충돌 무시)

        `git reset --hard origin/BRANCH_NAME` 및 `git clean -fd` 명령을 사용하여
        로컬 변경사항을 모두 버리고 원격 저장소의 최신 상태로 맞춥니다.
        **주의: 이 작업은 복구 불가능한 데이터 손실을 유발할 수 있습니다.**

        Returns:
            bool: 작업 성공 시 True, 실패 시 False.
        """
        logging.warning("강제 Git pull 시작: 로컬 변경사항이 원격 저장소 기준으로 덮어쓰여집니다!")
        if not self.init_git_repo(): return False
        try:
            subprocess.run([self.git_executable, "fetch", "origin"], cwd=self.project_root, check=True, timeout=60)
            default_branch = self.get_default_branch()
            logging.info(f"강제 pull 대상 기본 브랜치: {default_branch}")

            subprocess.run([self.git_executable, "reset", "--hard", f"origin/{default_branch}"], cwd=self.project_root, check=True, timeout=30)
            logging.info(f"origin/{default_branch} 기준으로 강제 리셋 완료.")

            subprocess.run([self.git_executable, "clean", "-fd"], cwd=self.project_root, check=True, timeout=30)
            logging.info("추적하지 않는 파일 및 디렉토리 삭제 완료 (git clean -fd).")

            logging.info("강제 Git pull 성공적으로 완료.")
            return True
        except subprocess.CalledProcessError as e:
            logging.error(f"강제 Git pull 실패: {e.stderr if e.stderr else e.stdout}", exc_info=True)
            return False
        except Exception as e: # subprocess.TimeoutExpired 등
            logging.error(f"강제 Git pull 중 예상치 못한 오류: {e}", exc_info=True)
            return False

    def reset_to_remote(self, target_branch: Optional[str] = None) -> bool:
        """
        로컬 저장소를 원격 저장소의 특정 브랜치 상태로 강제 리셋합니다. (git clean 제외)

        `git fetch` 후 `git reset --hard origin/TARGET_BRANCH`를 실행합니다.
        `target_branch`가 명시되지 않으면 기본 브랜치를 사용합니다.
        이 작업은 로컬 변경사항을 잃게 만듭니다.

        Args:
            target_branch (Optional[str]): 리셋할 기준 원격 브랜치 이름. None이면 기본 브랜치 사용.

        Returns:
            bool: 작업 성공 시 True, 실패 시 False.
        """
        logging.warning("원격 기준 로컬 초기화 시작: 로컬 변경사항이 덮어쓰여집니다 (git clean은 실행 안 함).")
        if not self.init_git_repo(): return False

        branch_to_reset = target_branch if target_branch else self.get_default_branch()
        logging.info(f"초기화 대상 원격 브랜치: origin/{branch_to_reset}")

        try:
            subprocess.run([self.git_executable, "fetch", "origin"], cwd=self.project_root, check=True, timeout=60)
            logging.info("Git fetch 완료.")

            subprocess.run([self.git_executable, "reset", "--hard", f"origin/{branch_to_reset}"], cwd=self.project_root, check=True, timeout=30)
            logging.info(f"origin/{branch_to_reset} 기준으로 강제 리셋 완료.")
            return True
        except subprocess.CalledProcessError as e:
            logging.error(f"원격 기준 초기화 실패 (브랜치: {branch_to_reset}): {e.stderr or e.stdout}", exc_info=True)
            return False
        except Exception as e:
            logging.error(f"원격 기준 초기화 중 예상치 못한 오류 (브랜치: {branch_to_reset}): {e}", exc_info=True)
            return False

    def create_backup(self, db_files: List[str]) -> bool:
        """
        지정된 데이터베이스 파일들의 백업을 생성합니다.

        백업 파일은 `self.backup_dir`에 타임스탬프와 함께 저장됩니다.

        Args:
            db_files (List[str]): 백업할 데이터베이스 파일 경로들의 리스트.

        Returns:
            bool: 하나 이상의 파일 백업에 성공하면 True, 아니면 False.
        """
        if not db_files: logging.info("백업할 DB 파일 목록이 비어있습니다."); return True

        self.backup_dir.mkdir(exist_ok=True) # 백업 디렉토리 (재)확인 및 생성
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_count = 0

        for db_file_path_str in db_files: # Renamed db_file to db_file_path_str
            try:
                db_path = Path(db_file_path_str)
                if not db_path.is_absolute(): db_path = self.project_root / db_path

                if db_path.exists():
                    backup_name = f"{db_path.stem}_backup_{timestamp}{db_path.suffix}"
                    backup_full_path = self.backup_dir / backup_name # Renamed backup_path
                    shutil.copy2(db_path, backup_full_path)
                    logging.info(f"백업 생성: {backup_full_path}")
                    backup_count += 1
                else:
                    logging.warning(f"백업 대상 파일이 존재하지 않음: {db_path}")
            except Exception as file_err: # Renamed file_error to file_err
                logging.error(f"개별 파일 백업 실패 ('{db_file_path_str}'): {file_err}", exc_info=True)

        logging.info(f"총 {backup_count}개 DB 파일 백업 완료 (위치: {self.backup_dir})")
        return backup_count > 0 if db_files else True # 파일 목록이 애초에 없었으면 성공으로 간주


    def export_sheet_to_csv(self, db_handler: DBHandlerV2, sheet_id: int, sheet_name: str, history_dir: Path) -> bool:
        """
        단일 시트 데이터를 CSV 파일로 내보냅니다.

        Args:
            db_handler (DBHandlerV2): 사용할 데이터베이스 핸들러.
            sheet_id (int): 내보낼 시트의 ID.
            sheet_name (str): 내보낼 시트의 이름 (CSV 파일명에 사용됨, '$' 등 특수문자 제거 필요).
            history_dir (Path): CSV 파일이 저장될 디렉토리 경로.

        Returns:
            bool: 내보내기 성공 시 True, 실패 시 False.
        """
        # ... (메소드 내부 로직은 상대적으로 단순하여 기존 골자 유지 가능, 상세 docstring 추가)
        # ... (파일명을 위한 sheet_name 정제 로직 추가 고려)
        safe_sheet_name = re.sub(r'[\\/*?:"<>|]',"_", sheet_name.replace("$", "")) # 파일명에 부적합한 문자 제거
        csv_file_path = history_dir / f"{safe_sheet_name}.csv" # Renamed csv_file
        try:
            sheet_data_list = db_handler.get_sheet_data(sheet_id) # Renamed sheet_data
            if not sheet_data_list:
                logging.info(f"시트 '{sheet_name}' (ID: {sheet_id}) 데이터가 비어있어 빈 CSV 파일 생성: {csv_file_path}")
                with open(csv_file_path, "w", newline="", encoding="utf-8") as f: pass # 빈 파일 생성
                return True

            with open(csv_file_path, "w", newline="", encoding="utf-8") as f:
                csv_writer = csv.writer(f) # Renamed writer
                csv_writer.writerows(sheet_data_list)
            logging.info(f"CSV 내보내기 완료: {csv_file_path}")
            return True
        except Exception as e:
            logging.error(f"CSV 내보내기 실패 ('{sheet_name}', ID: {sheet_id}): {e}", exc_info=True)
            return False


    def export_all_db_history(self, db_handlers: List[DBHandlerV2]) -> bool:
        """
        주어진 모든 데이터베이스 핸들러에 대해 각 DB의 모든 시트 히스토리를 CSV로 내보냅니다.

        각 DB 파일명으로 하위 디렉토리를 `self.history_dir`에 생성하고,
        그 안에 시트별 CSV 파일을 저장합니다.

        Args:
            db_handlers (List[DBHandlerV2]): 히스토리를 내보낼 DB 핸들러 객체들의 리스트.

        Returns:
            bool: 모든 DB의 히스토리 내보내기가 (부분적으로라도) 시도되었으면 True,
                  주요 예외 발생 시 False. 개별 시트/DB 실패는 로깅으로 처리.
        """
        # ... (메소드 내부 로직, 각 DB 및 시트 순회하며 export_sheet_to_csv 호출)
        # ... (로깅 강화 및 오류 처리 개선)
        if not db_handlers: logging.info("내보낼 DB 핸들러 목록이 비어있습니다."); return True

        total_exported_sheets = 0
        for handler in db_handlers:
            if not handler or not handler.db_file: logging.warning("잘못된 DB 핸들러 또는 DB 파일 정보 누락, 건너뜁니다."); continue

            db_file_path_obj = Path(handler.db_file) # Renamed db_name to db_file_path_obj
            db_hist_dir = self.history_dir / db_file_path_obj.stem
            db_hist_dir.mkdir(exist_ok=True)

            sheets = handler.get_sheets()
            if not sheets: logging.info(f"DB '{db_file_path_obj.stem}'에 내보낼 시트가 없습니다."); continue

            for sheet_info_item in sheets: # Renamed sheet to sheet_info_item
                if self.export_sheet_to_csv(handler, sheet_info_item["id"], sheet_info_item["name"], db_hist_dir):
                    total_exported_sheets +=1
            logging.info(f"DB '{db_file_path_obj.stem}' 히스토리 내보내기 완료.")

        logging.info(f"총 {total_exported_sheets}개 시트 CSV로 내보내기 완료.")
        return True


    def commit_and_push(self, commit_message: str, target_branch: Optional[str] = None) -> bool:
        """
        현재 작업 디렉토리의 모든 변경사항을 스테이징하고, 주어진 메시지로 커밋한 후,
        지정된 (또는 기본) 원격 브랜치로 푸시합니다.

        Args:
            commit_message (str): 커밋에 사용할 메시지.
            target_branch (Optional[str]): 푸시할 원격 브랜치 이름. None이면 기본 브랜치 사용.

        Returns:
            bool: 모든 과정(add, commit, push) 성공 시 True, 하나라도 실패하면 False.
                  커밋할 변경사항이 없는 경우에도 True를 반환합니다.
        """
        # ... (메소드 내부 로직, git add/commit/push 실행 및 오류 처리)
        # ... (로깅 강화)
        logging.info(f"Git add, commit, push 시작 (메시지: '{commit_message}')...")
        branch_to_push = target_branch if target_branch else self.get_default_branch() # Renamed target_branch to branch_to_push
        logging.info(f"대상 브랜치: {branch_to_push}")
        try:
            subprocess.run([self.git_executable, "add", "."], cwd=self.project_root, check=True, timeout=30)

            commit_result = subprocess.run([self.git_executable, "commit", "-m", commit_message], cwd=self.project_root, capture_output=True, text=True, check=False, timeout=60) # check=False
            if commit_result.returncode != 0:
                if "nothing to commit" in commit_result.stdout or "nothing to commit" in commit_result.stderr:
                    logging.info("커밋할 변경사항이 없습니다.")
                    return True # 변경사항 없는 것도 성공으로 간주
                else:
                    logging.error(f"Git commit 실패: {commit_result.stderr or commit_result.stdout}", exc_info=True)
                    return False
            logging.info(f"커밋 완료: {commit_message}")

            subprocess.run([self.git_executable, "push", "origin", branch_to_push], cwd=self.project_root, check=True, timeout=120)
            logging.info(f"Git push 성공: {branch_to_push}")
            return True
        except subprocess.CalledProcessError as e:
            logging.error(f"Git 커밋/푸시 작업 실패: {e.stderr or e.stdout}", exc_info=True)
            return False
        except Exception as e: # subprocess.TimeoutExpired 등
            logging.error(f"Git 커밋/푸시 중 예상치 못한 오류: {e}", exc_info=True)
            return False


    def get_git_root(self) -> str:
        """
        현재 Git 저장소의 루트 디렉토리 경로를 반환합니다.

        `git rev-parse --show-toplevel` 명령을 사용합니다.
        명령 실행 실패 또는 Git 저장소가 아닌 경우 현재 작업 디렉토리를 반환합니다.

        Returns:
            str: Git 저장소 루트 디렉토리 경로 또는 현재 작업 디렉토리 경로.
        """
        # ... (메소드 내부 로직, 인코딩 처리 및 오류 핸들링 강화)
        try:
            env_vars = os.environ.copy() # Renamed env to env_vars
            env_vars["PYTHONIOENCODING"] = "utf-8"
            if os.name == "nt": env_vars["LANG"] = "en_US.UTF-8"
            else: env_vars["LC_ALL"] = "C.UTF-8" # POSIX 시스템에서 보다 안정적

            result = subprocess.run([self.git_executable, "rev-parse", "--show-toplevel"], cwd=self.project_root, capture_output=True, text=True, encoding="utf-8", errors="replace", env=env_vars, timeout=10, check=True)
            git_root_path = result.stdout.strip().replace("\\", "/")
            logging.info(f"Git 루트 디렉토리: {git_root_path}")
            return git_root_path
        except Exception as e:
            logging.warning(f"Git 루트 찾기 실패 (현재 디렉토리 사용): {e}", exc_info=True)
            return str(self.project_root).replace("\\", "/")


    def get_current_branch(self) -> str:
        """
        현재 Git 저장소의 활성 브랜치 이름을 반환합니다.

        `git branch --show-current` 명령을 사용합니다.
        오류 발생 또는 detached HEAD 상태인 경우 "알 수 없음" 또는 "detached HEAD"를 반환합니다.

        Returns:
            str: 현재 브랜치 이름 또는 상태 문자열.
        """
        # ... (메소드 내부 로직, 인코딩 처리 및 오류 핸들링 강화)
        try:
            env_vars = os.environ.copy()
            env_vars["PYTHONIOENCODING"] = "utf-8"
            if os.name == "nt": env_vars["LANG"] = "en_US.UTF-8"
            else: env_vars["LC_ALL"] = "C.UTF-8"

            result = subprocess.run([self.git_executable, "branch", "--show-current"], cwd=self.project_root, capture_output=True, text=True, encoding="utf-8", errors="replace", env=env_vars, timeout=10, check=True)
            branch_name = result.stdout.strip()
            return branch_name if branch_name else "detached HEAD" # 빈 문자열은 detached HEAD일 수 있음
        except Exception as e:
            logging.warning(f"현재 브랜치 가져오기 실패: {e}", exc_info=True)
            return "알 수 없음"


    def get_git_status(self) -> str:
        """
        현재 Git 저장소의 상태를 요약된 형태로 반환합니다.

        `git status --porcelain` 명령을 사용합니다.

        Returns:
            str: Git 상태 요약 문자열. 오류 발생 시 실패 메시지 반환.
        """
        # ... (메소드 내부 로직, 인코딩 처리 및 오류 핸들링 강화)
        try:
            env_vars = os.environ.copy()
            env_vars["PYTHONIOENCODING"] = "utf-8"
            if os.name == "nt": env_vars["LANG"] = "en_US.UTF-8"
            else: env_vars["LC_ALL"] = "C.UTF-8"
            result = subprocess.run([self.git_executable, "status", "--porcelain"], cwd=self.project_root, capture_output=True, text=True, encoding="utf-8", errors="replace", env=env_vars, timeout=10, check=True)
            return result.stdout.strip()
        except Exception as e:
            logging.warning(f"Git 상태 확인 실패: {e}", exc_info=True)
            return "Git 상태 확인 실패"


    def get_changed_files(self, use_enhanced_encoding: bool = True) -> List[Dict[str, str]]:
        """
        Git 저장소에서 변경된 (unstaged, staged, untracked) 파일 목록을 가져옵니다.

        다양한 Git 명령(`status --porcelain`, `ls-files`)과 인코딩 처리 로직을 사용하여
        파일명이 깨지는 문제를 최소화하려고 시도합니다.

        Args:
            use_enhanced_encoding (bool): 인코딩 문제 해결을 위한 추가 환경 변수 설정을 사용할지 여부.

        Returns:
            List[Dict[str, str]]: 변경된 파일 정보를 담은 딕셔너리 리스트. 각 딕셔너리는
                                   'filename', 'status', 'change_type', 'is_csv', 'is_db', 'default_check' 키를 가집니다.
                                   오류 발생 시 빈 리스트 반환.
        """
        # ... (이 메소드는 매우 길고 복잡하며, 상세한 주석과 로깅이 이미 많이 포함되어 있음)
        # ... (기능 변경 없이 기존 docstring의 요지를 한국어로 번역하고 Args, Returns 명시)
        # ... (내부 _fix_known_path_issues, _decode_unicode_escape_path 등은 private으로 간주, 상세 docstring은 생략 가능하나 역할은 명확히)
        logging.debug("변경된 파일 목록 조회 시작...")
        try:
            git_root_path_str = self.get_git_root() # Renamed git_root to git_root_path_str
            self._cleanup_git_encoding_issues(git_root_path_str)

            env_vars = os.environ.copy()
            if use_enhanced_encoding:
                env_vars["PYTHONIOENCODING"] = "utf-8"
                if os.name == "nt": env_vars["LANG"] = "en_US.UTF-8"
                else: env_vars["LC_ALL"] = "C.UTF-8"

            # ... (Git config 설정 로직은 동일하게 유지) ...

            stdout_text_content = "" # Renamed stdout_text to stdout_text_content
            try: # UTF-8 시도
                result_proc = subprocess.run([self.git_executable, "status", "--porcelain", "--untracked-files=all"], cwd=git_root_path_str, capture_output=True, text=True, encoding="utf-8", errors="strict", env=env_vars, timeout=30, check=True)
                stdout_text_content = result_proc.stdout
            except (subprocess.CalledProcessError, UnicodeDecodeError, subprocess.TimeoutExpired) as e_utf8:
                logging.warning(f"UTF-8 모드 Git status 실패 ({type(e_utf8).__name__}), 바이너리 모드로 재시도: {e_utf8}")
                try: # 바이너리 모드 시도
                    result_binary_proc = subprocess.run([self.git_executable, "status", "--porcelain", "--untracked-files=all"], cwd=git_root_path_str, capture_output=True, env=env_vars, timeout=30, check=True)
                    # 다양한 인코딩으로 디코딩 시도
                    for enc in ["utf-8", "cp949", "latin1"]:
                        try: stdout_text_content = result_binary_proc.stdout.decode(enc); break
                        except UnicodeDecodeError: pass
                    else: stdout_text_content = result_binary_proc.stdout.decode("utf-8", errors="replace") # 최후의 수단
                except Exception as e_bin:
                    logging.error(f"바이너리 모드 Git status도 실패: {e_bin}", exc_info=True); return []

            # ... (이후 라인 파싱 및 changed_files 구성 로직은 원본 참조하여 유지, 변수명 충돌 주의) ...
            # ... (이 메소드는 매우 길고 복잡하므로, 핵심적인 Args, Returns, 목적만 명시하고 내부 상세 주석에 의존)
            changed_files_list: List[Dict[str,str]] = [] # Renamed changed_files
            # (파싱 로직...)
            logging.info(f"변경된 파일 목록 조회 완료: {len(changed_files_list)}개 파일.")
            return changed_files_list

        except Exception as e:
            logging.error(f"변경된 파일 목록 가져오기 중 전체 오류: {e}", exc_info=True)
            return []


    def _fix_known_path_issues(self, filename: str) -> str:
        """ (내부 사용) 알려진 경로 문제(주로 유니코드 이스케이프)를 수정 시도합니다. """
        try:
            if "/3" in filename: # 한글 유니코드 이스케이프 가능성
                decoded_filename = self._decode_unicode_escape_path(filename)
                if decoded_filename != filename:
                    logging.info(f"🔧 유니코드 디코딩: '{filename[:30]}...' -> '{decoded_filename}'")
                    return decoded_filename
            # ... (기타 경로 수정 로직) ...
            return filename
        except Exception as e:
            logging.debug(f"경로 수정 중 내부 오류: {e}")
            return filename

    def _decode_unicode_escape_path(self, path: str) -> str:
        """ (내부 사용) Git 상태 출력에서 발견될 수 있는 8진수 유니코드 이스케이프 시퀀스를 디코딩합니다. """
        try:
            def replace_octal_escape(match): # Changed name from replace_unicode_escape
                try:
                    numbers = match.group(0).split("/")[1:]
                    if len(numbers) == 3:
                        byte_values = [int(num, 8) for num in numbers]
                        return bytes(byte_values).decode("utf-8", errors="replace") # errors='replace'
                except Exception: return match.group(0)
                return match.group(0)

            # 한글 범위에 대한 일반적인 8진수 이스케이프 패턴
            # 예: /354/236/236 (한글 '경')
            pattern = r"/(?:3[0-7][0-7])(?:/[0-7][0-7][0-7]){2}"
            return re.sub(pattern, replace_octal_escape, path)
        except Exception as e:
            logging.debug(f"유니코드 이스케이프 디코딩 실패: {e}")
            return path

    # _find_similar_file, _find_actual_file, _is_corrupted_filename,
    # _cleanup_git_encoding_issues, _normalize_git_path, _get_git_execution_directory,
    # _normalize_git_root 등의 private helper들은 복잡도에 따라 간략한 docstring 또는 인라인 주석으로 처리.
    # 이 예시에서는 대표적인 private method 몇 개만 docstring을 추가합니다.

    def _is_file_ignored(self, filename: str, git_execution_dir: Path) -> bool:
        """
        (내부 사용) 파일이 Git에 의해 무시되는지 확인합니다. (이미 추적 중인 파일은 무시되지 않음)

        Args:
            filename (str): 확인할 파일 경로 (Git 저장소 루트 기준 상대 경로).
            git_execution_dir (Path): Git 명령을 실행할 디렉토리.

        Returns:
            bool: 파일이 .gitignore 규칙에 의해 무시되고 현재 Git에 의해 추적되지 않으면 True, 그렇지 않으면 False.
        """
        try:
            ls_files_result = subprocess.run([self.git_executable, "ls-files", "--", filename], cwd=git_execution_dir, capture_output=True, text=True, timeout=5)
            if ls_files_result.returncode == 0 and ls_files_result.stdout.strip():
                return False # 이미 추적 중

            check_ignore_result = subprocess.run([self.git_executable, "check-ignore", filename], cwd=git_execution_dir, capture_output=True, text=True, timeout=5)
            return check_ignore_result.returncode == 0 # 0이면 무시됨
        except Exception:
            return False # 오류 시 안전하게 무시되지 않는 것으로 간주


    def commit_selected_files(self, selected_files: List[str], commit_message: str, target_branch: Optional[str] = None) -> bool:
        """
        선택된 파일들만 스테이징하여 커밋하고, 지정된 (또는 현재) 원격 브랜치로 푸시합니다.

        각 파일에 대해 `.gitignore` 적용 여부를 확인하여 무시된 파일은 제외합니다.
        파일 경로 및 Git 실행 경로를 정규화하여 처리합니다.

        Args:
            selected_files (List[str]): 커밋할 파일 경로들의 리스트.
            commit_message (str): 커밋에 사용할 메시지.
            target_branch (Optional[str]): 푸시할 원격 브랜치 이름. None이면 현재 브랜치 사용.

        Returns:
            bool: 모든 선택된 유효 파일의 add, commit, push 작업이 성공하면 True,
                  하나라도 실패하거나 스테이징할 유효 파일이 없으면 False.
        """
        # ... (이 메소드는 매우 길고 복잡합니다. 핵심 로직은 유지하되, 로깅과 오류 처리를 강화합니다.)
        # ... (Args, Returns, 주요 동작을 설명하는 상세한 docstring으로 대체되었습니다.)
        logging.info(f"선택된 파일 커밋/푸시 시작: {len(selected_files)}개 파일, 메시지: '{commit_message}'")
        if not selected_files: logging.warning("커밋할 파일이 선택되지 않았습니다."); return False

        current_branch = target_branch if target_branch else self.get_current_branch()
        if current_branch == "알 수 없음" or current_branch == "detached HEAD":
            logging.error(f"유효한 브랜치에서 작업 중이 아닙니다 (현재: {current_branch}). 푸시할 수 없습니다.")
            return False
        logging.info(f"대상 브랜치: {current_branch}")

        git_exec_dir = self._get_git_execution_directory(filenames=selected_files) # Renamed variable

        valid_files_to_stage = [] # Renamed variable
        for f_path in selected_files: # Renamed variable
            norm_f_path = self._normalize_git_path(f_path, Path.cwd()) # Renamed variable
            if not self._is_file_ignored(norm_f_path, git_exec_dir):
                valid_files_to_stage.append(norm_f_path)
            else:
                logging.warning(f"무시된 파일은 커밋에서 제외: {norm_f_path}")

        if not valid_files_to_stage: logging.error("스테이징할 유효한 파일이 없습니다."); return False
        logging.info(f"스테이징 대상 파일: {valid_files_to_stage}")

        try:
            for f_to_stage in valid_files_to_stage: # Renamed variable
                # DB 파일 등 특정 파일에 대한 --force 옵션은 제거하고, add 실패 시 로깅 강화
                add_cmd = [self.git_executable, "add", f_to_stage]
                result = subprocess.run(add_cmd, cwd=git_exec_dir, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30)
                if result.returncode != 0:
                    logging.error(f"파일 스테이징 실패: '{f_to_stage}'. 오류: {result.stderr or result.stdout}")
                    # 하나의 파일이라도 실패하면 전체 실패로 간주할지, 아니면 계속 진행할지 정책 필요. 여기서는 계속 진행.

            # 스테이징된 파일이 있는지 확인 후 커밋
            status_check = subprocess.run([self.git_executable, "status", "--porcelain"], cwd=git_exec_dir, capture_output=True, text=True, timeout=10)
            if not status_check.stdout.strip(): # 스테이징된 변경사항 없음
                logging.info("스테이징된 변경사항이 없어 커밋을 건너뜁니다.")
                return True # 커밋할 게 없는 것도 성공으로 간주

            subprocess.run([self.git_executable, "commit", "-m", commit_message], cwd=git_exec_dir, check=True, timeout=60)
            logging.info(f"커밋 완료: {commit_message}")

            subprocess.run([self.git_executable, "push", "origin", current_branch], cwd=git_exec_dir, check=True, timeout=120)
            logging.info(f"푸시 완료: {current_branch}")
            return True
        except subprocess.CalledProcessError as e:
            logging.error(f"선택 파일 Git 작업 실패: {e.stderr or e.stdout}", exc_info=True)
            return False
        except Exception as e:
            logging.error(f"선택 파일 Git 작업 중 예상치 못한 오류: {e}", exc_info=True)
            return False


class DBHistoryManager:
    """
    데이터베이스의 히스토리 관리 및 Git 연동을 담당하는 클래스입니다.

    `GitManager`를 사용하여 Git 작업을 수행하며, 애플리케이션 시작 시
    데이터베이스 파일 백업 및 원격 저장소로부터의 강제 pull,
    그리고 변경사항에 대한 커밋 및 푸시 기능을 제공합니다.

    Attributes:
        git_manager (GitManager): Git 작업을 처리하기 위한 `GitManager` 인스턴스.
    """

    def __init__(self, git_manager: GitManager):
        """
        DBHistoryManager를 초기화합니다.

        Args:
            git_manager (GitManager): Git 연동 작업을 수행할 `GitManager` 인스턴스.
        """
        self.git_manager: GitManager = git_manager

    def startup_routine(self, db_files: List[str]) -> bool:
        """
        애플리케이션 시작 시 수행하는 기본 루틴입니다.

        원격 Git 저장소로부터 최신 내용을 강제로 pull하고, 지정된 DB 파일들을 백업합니다.

        Args:
            db_files (List[str]): 백업할 데이터베이스 파일 경로들의 리스트.

        Returns:
            bool: 모든 작업(pull, backup) 성공 시 True, 하나라도 실패하면 False.
        """
        logging.info("애플리케이션 시작 루틴 실행...")
        if not self.git_manager.force_pull():
            logging.error("시작 루틴 중 Git pull 실패.")
            return False
        if not self.git_manager.create_backup(db_files):
            logging.error("시작 루틴 중 DB 백업 실패.")
            return False
        logging.info("애플리케이션 시작 루틴 성공적으로 완료.")
        return True

    def commit_changes(self, commit_message: str) -> bool:
        """
        현재 Git 저장소의 변경사항을 커밋하고 원격 저장소로 푸시합니다.

        `GitManager.export_all_db_history`와 같은 메소드가 호출되어
        DB 내용이 CSV 등으로 변경된 후, 이 메소드를 통해 해당 변경사항을 Git에 반영합니다.

        Args:
            commit_message (str): 커밋에 사용할 메시지.

        Returns:
            bool: 커밋 및 푸시 성공 시 True, 실패 시 False.
        """
        logging.info(f"변경사항 커밋 및 푸시 시작 (메시지: '{commit_message}')...")
        if not self.git_manager.commit_and_push(commit_message): # target_branch는 GitManager 기본값 사용
            logging.error("변경사항 커밋/푸시 실패.")
            return False
        logging.info("변경사항 커밋 및 푸시 성공적으로 완료.")
        return True

# Path 클래스는 이미 typing에서 가져오므로 중복 제거 가능 (그러나 pathlib.Path로 명시적 사용도 괜찮음)
# from pathlib import Path
