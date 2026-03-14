from src.config_loader import load_app_config, AppConfig


def test_config_loading(tmp_path):
    # given: 가짜 yaml 파일 생성
    config_file = tmp_path / "config.yaml"
    config_file.write_text("""
logging:
  level: "DEBUG"
  file_path: "test.log"
  max_bytes: 1024
  backup_count: 5
git:
  remote_name: "origin"
  branch_name: "main"
  commit_message: "test commit"
common:
  vault_path: "/tmp/notes"
  wait_time: 1
    """, encoding="utf-8")

    # when
    config = load_app_config(str(config_file))

    # then
    assert isinstance(config, AppConfig)
    assert config.logging.level == "DEBUG"
    assert config.common.wait_time == 1
