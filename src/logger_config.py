import logging
from logging.handlers import RotatingFileHandler

from config_loader import LoggingConfig


def setup_logging(log_cfg: LoggingConfig):
    logger = logging.getLogger("NoteSync")
    logger.setLevel(getattr(logging, log_cfg.level.upper(), logging.INFO))

    # 로그 포맷 설정: 날짜 시간 [레벨] 메시지 형태
    formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

    # 콘솔 출력용 핸들러
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # 파일 기록용 핸들러
    file_handler = RotatingFileHandler(
        log_cfg.file_path,
        maxBytes=log_cfg.max_bytes,
        backupCount=log_cfg.backup_count,
        encoding="utf-8"
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger
