from ui_manager import TrayIconManager


def test_tray_menu_text_update(mocker):
    # given
    ui = TrayIconManager(mocker.Mock(file_path="/fake/path"))

    # when & then
    # 초기 상태 확인
    assert "Monitoring" in ui.status_texts["idle"]

    # 상태 변경 시
    ui.current_status = "sync"
    menu = ui._create_menu()

    # 첫 번째 메뉴 아이템의 텍스트가 "Syncing..."을 포함하는지 확인
    assert "Syncing" in menu.items[0].text
