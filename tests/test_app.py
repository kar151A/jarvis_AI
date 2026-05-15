from app import needs_current_info, parse_open_command, resolve_app, to_ps_string


def test_parse_open_command():
    assert parse_open_command("open notepad") == "notepad"
    assert parse_open_command("Hey Jarvis open chrome") == "chrome"
    assert parse_open_command("what is python") is None


def test_resolve_known_app_alias():
    label, command = resolve_app("Google Chrome")
    assert label == "google chrome"
    assert command == "chrome"


def test_resolve_whatsapp_alias():
    label, command = resolve_app("Whats App")
    assert label == "whats app"
    assert command == "whatsapp"


def test_current_info_detection():
    assert needs_current_info("who is the cm of tamil nadu")
    assert needs_current_info("what is the latest cricket score")
    assert not needs_current_info("explain recursion simply")


def test_powershell_string_escape():
    assert to_ps_string("Bob's App") == "'Bob''s App'"
