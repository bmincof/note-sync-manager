import logging
import os
import platform
import subprocess

import pystray
from PIL import Image
from pystray import MenuItem as Item

from config_loader import LoggingConfig

logger = logging.getLogger("NoteSync")


class TrayIconManager:
    def __init__(self, log_cfg: LoggingConfig):
        self.log_file_path = log_cfg.file_path
        self.icon = self._load_image("resources/icon.png")
        self.current_status = "idle"
        # 상태별 메뉴에 노출될 텍스트 맵
        self.status_texts = {
            "idle": "🟢 Status: Monitoring",
            "sync": "🔄 Status: Syncing...",
            "error": "❌ Status: Error!"
        }

    def open_file(self, path):
        if not os.path.exists(path):
            logger.error(f"File not found: {path}")
            return
        current_os = platform.system()
        if current_os == "Darwin":
            subprocess.run(["open", path])
        elif current_os == "Windows":
            os.startfile(path)

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
            Item('Open Logs', lambda i, j: self.open_file(self.log_file_path)),
            Item('Edit Config', lambda i, j: self.open_file("config.yaml")),
            Item('Quit', self.on_quit)
        )

    def setup(self):
        # 초기 메뉴 생성 및 아이콘 초기화
        self.icon = pystray.Icon(
            "NoteSync",
            self.icon,
            "NoteSync",
            menu=self._create_menu()
        )
        return self.icon
