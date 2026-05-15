from app import parse_open_command, resolve_app


def test_parse_open_command():
    assert parse_open_command("open notepad") == "notepad"
    assert parse_open_command("Hey Jarvis open chrome") == "chrome"
    assert parse_open_command("what is python") is None


def test_resolve_known_app_alias():
    label, command = resolve_app("Google Chrome")
    assert label == "google chrome"
    assert command == "chrome"
