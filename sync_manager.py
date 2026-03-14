import logging
import os
import threading

from git import Repo, exc
from watchdog.events import FileSystemEventHandler

logger = logging.getLogger("NoteSync")

class SyncManager:
    def __init__(self, common_cfg, git_cfg, on_status_change):
        repo_path = common_cfg['vault_path']
        self.repo_path = repo_path
        self.git_cfg = git_cfg
        self.on_status_change = on_status_change
        try:
            self.repo = Repo(repo_path)
            logger.info(f"Repository loaded successfully: {repo_path}")
        except exc.InvalidGitRepositoryError:
            logger.error(f"Invalid git repository: {repo_path}")
            self.repo = None
        self._notify("idle")

    def _notify(self, status):
        if self.on_status_change:
            self.on_status_change(status)

    def sync(self):
        if not self.repo: return

        remote_name = self.git_cfg['remote_name']
        branch_name = self.git_cfg['branch_name']
        commit_message = self.git_cfg['commit_message']

        self._notify("sync")  # TrayIconManager의 "sync" 키와 일치시킴

        try:
            logger.info("Synchronization process started")

            # 1. 로컬 변경사항 커밋
            if self.repo.is_dirty(untracked_files=True):
                self.repo.git.add(A=True)
                self.repo.index.commit(commit_message)
                logger.info(f"Local changes committed: {commit_message}")

            # 2. 원격 변경사항 Pull (rebase)
            logger.info("Checking remote changes (Pull/Rebase)")
            self.repo.git.pull(remote_name, branch_name, rebase=True)

            # 3. Push
            self.repo.git.push(remote_name, branch_name)
            logger.info("Synchronization completed successfully")

            self._notify("idle")
        except exc.GitCommandError as e:
            logger.error(f"Git command error: {e}")
            self._notify("error")
        except Exception:
            logger.exception("Unexpected error occurred during synchronization")
            self._notify("error")


class DebounceHandler(FileSystemEventHandler):
    def __init__(self, manager, common_cfg):
        self.manager = manager
        self.timer = None
        self.wait_time = common_cfg['wait_time']

    def on_modified(self, event):
        if not event.is_directory and event.src_path.endswith(".md"):
            if self.timer:
                self.timer.cancel()

            self.timer = threading.Timer(self.wait_time, self.manager.sync)
            self.timer.start()
            logger.debug(f"Change detected: {os.path.basename(event.src_path)}. Sync scheduled in {self.wait_time}s")
