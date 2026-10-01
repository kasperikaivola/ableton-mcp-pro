import json

from MCP_Server.tools import devices_browser


class _FakeConnection:
    def send_command(self, command, params):
        assert command == "load_browser_item"
        return {
            "loaded": True,
            "item_name": "Serum 2",
            "track_name": "Lead",
            "uri": params["item_uri"],
        }


def test_load_instrument_reports_accepted_item_without_empty_device_claim(monkeypatch):
    monkeypatch.setattr(devices_browser, "get_ableton_connection", lambda: _FakeConnection())

    result = devices_browser.load_instrument_or_effect(None, 2, "browser://serum")

    assert "Serum 2" in result
    assert "Lead" in result
    assert "Devices on track" not in result


def test_plugin_parameter_read_requires_manual_settings_chat_handoff(monkeypatch):
    snapshot = {
        "device_name": "Serum 2", "is_plugin": True,
        "parameters": [{"name": "A WT Pos", "value": 0.25}],
    }

    class Connection:
        def send_command(self, command, params):
            assert command == "get_device_parameters"
            return snapshot

    monkeypatch.setattr(devices_browser, "get_ableton_connection", lambda: Connection())
    result = json.loads(devices_browser.get_device_parameters(None, 1, 0))

    reminder = result["manual_settings_handoff"]
    assert "always" in reminder.lower()
    assert "chat" in reminder.lower()
    assert "not applied" in reminder.lower()
    assert "wavetable" in reminder.lower() and "FX" in reminder
    assert result["parameters"] == snapshot["parameters"]
    assert "manual_settings_handoff" not in snapshot


def test_manual_settings_reminder_survives_plugin_rename(monkeypatch):
    class Connection:
        def send_command(self, command, params):
            return {"device_name": "Bass engine", "class_name": "PluginDevice", "parameters": []}

    monkeypatch.setattr(devices_browser, "get_ableton_connection", lambda: Connection())
    result = json.loads(devices_browser.get_device_parameters(None, 0, 0))
    assert "manual_settings_handoff" in result


def test_native_device_read_does_not_claim_plugin_control_gaps(monkeypatch):
    snapshot = {"device_name": "Wavetable", "is_plugin": False, "parameters": []}

    class Connection:
        def send_command(self, command, params):
            return snapshot

    monkeypatch.setattr(devices_browser, "get_ableton_connection", lambda: Connection())
    result = json.loads(devices_browser.get_device_parameters(None, 0, 0))
    assert result == snapshot


def test_skipped_parameter_write_requests_chat_handoff(monkeypatch):
    class Connection:
        def send_command(self, command, params):
            assert command == "batch_set_device_parameters"
            return {"updated_count": 0, "parameters": [], "skipped": [{"name": "FX Mix"}]}

    monkeypatch.setattr(devices_browser, "get_ableton_connection", lambda: Connection())
    result = devices_browser.batch_set_device_parameters(
        None, 0, 0, [0.25], parameter_names=["FX Mix"]
    )
    assert "FX Mix" in result
    assert "manual" in result.lower() and "chat" in result.lower()
