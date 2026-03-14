import logging
import os
import platform
import subprocess
import threading
from logging.handlers import RotatingFileHandler

import pystray
import yaml
from PIL import Image
from git import Repo, exc
from pystray import MenuItem as Item
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer


# --- 1. 설정 및 로깅 초기화 ---
def load_config():
    with open("config.yaml", "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


config = load_config()


def setup_logging():
    log_cfg = config['logging']
    logger = logging.getLogger("ObsidianSync")
    level_str = log_cfg.get('level', 'INFO')
    logger.setLevel(getattr(logging, level_str))

    # 로그 포맷 설정: 날짜 시간 [레벨] 메시지 형태
    formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

    # 콘솔 출력용 핸들러
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # 파일 기록용 핸들러
    file_handler = RotatingFileHandler(
        log_cfg['file_path'],
        maxBytes=log_cfg['max_bytes'],
        backupCount=log_cfg['backup_count'],
        encoding="utf-8"
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger


logger = setup_logging()


# --- 2. 동기화 로직 ---
class SyncManager:
    def __init__(self, repo_path, on_status_change):
        self.repo_path = repo_path
        try:
            self.repo = Repo(repo_path)
            logger.info(f"Repository loaded successfully: {repo_path}")
        except exc.InvalidGitRepositoryError:
            logger.error(f"Invalid git repository: {repo_path}")
            self.repo = None
        self.on_status_change = on_status_change
        self._notify("idle")

    def _notify(self, status):
        if self.on_status_change:
            self.on_status_change(status)

    def sync(self):
        if not self.repo: return
        git_cfg = config['git']

        self._notify("sync")  # TrayIconManager의 "sync" 키와 일치시킴

        try:
            logger.info("Synchronization process started")

            # 1. 로컬 변경사항 커밋
            if self.repo.is_dirty(untracked_files=True):
                self.repo.git.add(A=True)
                self.repo.index.commit(git_cfg['commit_message'])
                logger.info(f"Local changes committed: {git_cfg['commit_message']}")

            # 2. 원격 변경사항 Pull (rebase)
            logger.info("Checking remote changes (Pull/Rebase)")
            self.repo.git.pull(git_cfg['remote_name'], git_cfg['branch_name'], rebase=True)

            # 3. Push
            self.repo.git.push(git_cfg['remote_name'], git_cfg['branch_name'])
            logger.info("Synchronization completed successfully")

            self._notify("idle")
        except exc.GitCommandError as e:
            logger.error(f"Git command error: {e}")
            self._notify("error")
        except Exception:
            logger.exception("Unexpected error occurred during synchronization")
            self._notify("error")


# --- 3. 이벤트 핸들러 ---
class DebounceHandler(FileSystemEventHandler):
    def __init__(self, manager):
        self.manager = manager
        self.timer = None
        self.wait_time = config['common']['wait_time']

    def on_modified(self, event):
        if not event.is_directory and event.src_path.endswith(".md"):
            if self.timer:
                self.timer.cancel()

            self.timer = threading.Timer(self.wait_time, self.manager.sync)
            self.timer.start()
            logger.debug(f"Change detected: {os.path.basename(event.src_path)}. Sync scheduled in {self.wait_time}s")


# --- 4. UI 레이어: 트레이 아이콘 및 관련 유틸리티 ---
def open_file(path):
    if not os.path.exists(path):
        logger.error(f"File not found: {path}")
        return
    current_os = platform.system()
    if current_os == "Darwin":
        subprocess.run(["open", path])
    elif current_os == "Windows":
        os.startfile(path)


class TrayIconManager:
    def __init__(self):
        self.icon = self._load_image("icon.png")
        # 상태별 메뉴에 노출될 텍스트 맵
        self.status_texts = {
            "idle": "🟢 Status: Monitoring",
            "sync": "🔄 Status: Syncing...",
            "error": "❌ Status: Error!"
        }
        self.current_status = "idle"

    def _load_image(self, filename):
        try:
            return Image.open(filename)
        except FileNotFoundError:
            return Image.new('RGB', (64, 64), color=(128, 128, 128))

    def update_ui(self, status):
        """상태가 변하면 호출되어 메뉴 텍스트를 갱신합니다."""
        if not self.icon: return

        self.current_status = status

        self.icon.menu = self._create_menu()

        logger.debug(f"UI Status Updated to: {status}")

    def on_quit(self, icon, item):
        logger.info("Termination requested")
        icon.stop()

    def _create_menu(self):
        # 맵에서 현재 상태에 맞는 텍스트를 가져옴
        display_text = self.status_texts.get(self.current_status, self.status_texts["idle"])

        return pystray.Menu(
            Item(display_text, lambda: None, enabled=False),
            Item('Open Logs', lambda i, j: open_file(config['logging']['file_path'])),
            Item('Edit Config', lambda i, j: open_file("config.yaml")),
            Item('Quit', self.on_quit)
        )

    def setup(self):
        # 초기 메뉴 생성 및 아이콘 초기화
        self.icon = pystray.Icon(
            "ObsidianSync",
            self.icon,
            "Obsidian Sync",
            menu=self._create_menu()
        )
        return self.icon


# --- 5. 메인 실행부 ---
if __name__ == "__main__":
    vault_path = config['common']['vault_path']

    tray_manager = TrayIconManager()
    sync_manager = SyncManager(vault_path, tray_manager.update_ui)
    event_handler = DebounceHandler(sync_manager)

    # Watchdog 감시 시작
    observer = Observer()
    observer.schedule(event_handler, vault_path, recursive=True)
    observer.start()

    # 트레이 아이콘 실행 (메인 스레드 점유)
    icon = tray_manager.setup()
    logger.info(f"Agent started. Monitoring: {vault_path}")

    try:
        icon.run()
    finally:
        # 아이콘 종료 시(Quit 클릭 시) 감시자도 안전하게 종료
        observer.stop()
        observer.join()
        logger.info("Agent shutdown complete.")