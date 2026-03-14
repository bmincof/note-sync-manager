import yaml
from watchdog.observers import Observer

from config_loader import load_app_config
from logger_config import setup_logging
from sync_manager import SyncManager, DebounceHandler
from ui_manager import TrayIconManager


def load_config():
    with open("config.yaml", "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

if __name__ == "__main__":
    config = load_app_config()

    logger = setup_logging(config.logging)

    # 1. UI Manager 초기화
    tray_manager = TrayIconManager(config.logging)

    # 2. Sync Manager 초기화
    sync_manager = SyncManager(config.common, config.git, tray_manager.update_ui)

    # 3. 파일 감시 시작
    event_handler = DebounceHandler(sync_manager, config.common)
    observer = Observer()
    observer.schedule(event_handler, config.common.vault_path, recursive=True)
    observer.start()

    # 4. 트레이 실행
    icon = tray_manager.setup()
    logger.info(f"Agent started. Monitoring: {config.common.vault_path}")

    try:
        icon.run()
    finally:
        observer.stop()
        observer.join()
        logger.info("Agent shutdown complete.")