from dataclasses import dataclass

import yaml


@dataclass(frozen=True)
class LoggingConfig:
    file_path: str
    max_bytes: int
    backup_count: int
    level: str = "INFO"


@dataclass(frozen=True)
class GitConfig:
    remote_name: str
    branch_name: str
    commit_message: str


@dataclass(frozen=True)
class CommonConfig:
    vault_path: str
    wait_time: int


@dataclass(frozen=True)
class AppConfig:
    logging: LoggingConfig
    git: GitConfig
    common: CommonConfig


def load_app_config(config_path="resources/config.yaml") -> AppConfig:
    with open(config_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    return AppConfig(
        logging=LoggingConfig(**data['logging']),
        git=GitConfig(**data['git']),
        common=CommonConfig(**data['common'])
    )
