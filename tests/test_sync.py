from src.sync_manager import SyncManager


def test_sync_status_cycle(mocker):
    # given
    mock_repo = mocker.patch("sync_manager.Repo")
    mock_callback = mocker.Mock()

    manager = SyncManager(
        common_cfg=mocker.Mock(vault_path="/fake/path"),
        git_cfg=mocker.Mock(remote_name="origin", branch_name="main", commit_message="sync"),
        on_status_change=mock_callback
    )

    # when
    manager.sync()

    # then: idle -> sync -> idle 순서로 콜백이 호출되었는지
    expected_calls = [mocker.call("idle"), mocker.call("sync"), mocker.call("idle")]
    mock_callback.assert_has_calls(expected_calls)


def test_sync_error_status(mocker):
    # given
    mock_repo = mocker.patch("sync_manager.Repo")
    mock_repo.return_value.git.pull.side_effect = Exception("Network Error")

    mock_callback = mocker.Mock()

    manager = SyncManager(
        common_cfg=mocker.Mock(vault_path="/fake/path"),
        git_cfg=mocker.Mock(remote_name="origin", branch_name="main", commit_message="sync"),
        on_status_change=mock_callback
    )

    # when
    manager.sync()

    # then: 마지막 호출이 "error"여야 함
    assert mock_callback.call_args_list[-1] == mocker.call("error")
