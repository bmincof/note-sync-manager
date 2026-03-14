import yaml
from watchdog.observers import Observer

from logger_config import setup_logging
from sync_manager import SyncManager, DebounceHandler
from ui_manager import TrayIconManager


def load_config():
    with open("config.yaml", "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

if __name__ == "__main__":
    config = load_config()
    log_cfg = config['logging']
    common_cfg = config['common']
    git_cfg = config['git']

    logger = setup_logging(log_cfg)

    # 1. UI Manager 초기화
    tray_manager = TrayIconManager(log_cfg)

    # 2. Sync Manager 초기화
    sync_manager = SyncManager(common_cfg, git_cfg, tray_manager.update_ui)

    # 3. 파일 감시 시작
    event_handler = DebounceHandler(sync_manager, common_cfg)
    observer = Observer()
    observer.schedule(event_handler, common_cfg['vault_path'], recursive=True)
    observer.start()

    # 4. 트레이 실행
    icon = tray_manager.setup()
    logger.info(f"Agent started. Monitoring: {common_cfg['vault_path']}")

    try:
        icon.run()
    finally:
        observer.stop()
        observer.join()
        logger.info("Agent shutdown complete.")