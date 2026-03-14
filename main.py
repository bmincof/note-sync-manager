import logging
import os
import platform
import subprocess
import threading
from logging.handlers import RotatingFileHandler

import pystray
import yaml
from PIL import Image, ImageDraw
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
    def __init__(self, repo_path):
        self.repo_path = repo_path
        try:
            self.repo = Repo(repo_path)
            logger.info(f"Repository loaded successfully: {repo_path}")
        except exc.InvalidGitRepositoryError:
            logger.error(f"Invalid git repository: {repo_path}")
            self.repo = None

    def sync(self):
        if not self.repo: return
        git_cfg = config['git']

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

        except exc.GitCommandError as e:
            logger.error(f"Git command error: {e}")
        except Exception as e:
            logger.exception("Unexpected error occurred during synchronization")


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


# --- 4. 트레이 아이콘 및 유틸리티 ---
def open_file(path):
    """OS별 파일 열기 기능 (윈도우/맥 범용)"""
    if not os.path.exists(path):
        logger.error(f"File not found: {path}")
        return
    current_os = platform.system()
    if current_os == "Darwin":  # macOS
        subprocess.run(["open", path])
    elif current_os == "Windows":
        os.startfile(path)


def create_placeholder_image():
    """임시 아이콘 생성"""
    width, height = 64, 64
    image = Image.new('RGB', (width, height), color=(73, 109, 137))
    dc = ImageDraw.Draw(image)
    dc.rectangle([width // 4, height // 4, width * 3 // 4, height * 3 // 4], fill=(255, 255, 255))
    return image


def on_quit(icon, item):
    logger.info("Agent termination requested via tray menu")
    icon.stop()


def setup_tray():
    menu = (
        Item('Status: Monitoring', lambda: None, enabled=False),
        Item('Open Logs', lambda: open_file(config['logging']['file_path'])),
        Item('Edit Config', lambda: open_file("config.yaml")),
        Item('Quit', on_quit)
    )
    icon = pystray.Icon("ObsidianSync", create_placeholder_image(), "Obsidian Sync Agent", menu)
    return icon


# --- 5. 메인 실행부 ---
if __name__ == "__main__":
    vault_path = config['common']['vault_path']
    manager = SyncManager(vault_path)
    event_handler = DebounceHandler(manager)

    # Watchdog 감시 시작
    observer = Observer()
    observer.schedule(event_handler, vault_path, recursive=True)
    observer.start()

    # 트레이 아이콘 실행 (메인 스레드 점유)
    icon = setup_tray()
    logger.info(f"Agent started. Monitoring: {vault_path}")

    try:
        icon.run()
    finally:
        # 아이콘 종료 시(Quit 클릭 시) 감시자도 안전하게 종료
        observer.stop()
        observer.join()
        logger.info("Agent shutdown complete.")