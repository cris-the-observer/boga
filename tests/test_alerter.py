import json
from unittest.mock import MagicMock, patch

import config
from alerter import alert


def test_console_alert_prints(caplog):
    import logging

    with caplog.at_level(logging.WARNING, logger="alerter"):
        alert("HIGH", ["FEAR", "AUTHORITY"], ["Some obs"], "some text", log_file="/dev/null")
    assert "ALERT: HIGH" in caplog.text
    assert "FEAR, AUTHORITY" in caplog.text


def test_log_alert_writes_json(tmp_log_file):
    alert("MEDIUM", ["FEAR"], ["Obs"], "Hello text", log_file=tmp_log_file)
    with open(tmp_log_file) as f:
        data = json.loads(f.read())
    assert "timestamp" in data
    assert data["severity"] == "MEDIUM"
    assert data["triggered_groups"] == ["FEAR"]
    assert data["observations"] == ["Obs"]
    assert data["transcript"] == "Hello text"


def test_log_appends_not_overwrites(tmp_log_file):
    alert("MEDIUM", [], [], "", log_file=tmp_log_file)
    alert("HIGH", [], [], "", log_file=tmp_log_file)
    with open(tmp_log_file) as f:
        lines = f.readlines()
    assert len(lines) == 2


@patch("builtins.__import__")
def test_gpio_skipped_when_unavailable(mock_import):
    def side_effect(name, *args, **kwargs):
        if name == "RPi.GPIO":
            raise ImportError("No module named RPi.GPIO")
        return __import__(name, *args, **kwargs)

    mock_import.side_effect = side_effect

    alert("HIGH", [], [], "", log_file="/dev/null")


def test_gpio_pulses_when_available():
    import sys

    mock_gpio = MagicMock()
    mock_rpi = MagicMock()
    mock_rpi.__path__ = []
    mock_rpi.GPIO = mock_gpio

    with patch.dict(sys.modules, {"RPi": mock_rpi, "RPi.GPIO": mock_gpio}):
        alert("CRITICAL", [], [], "", log_file="/dev/null")

        mock_gpio.setmode.assert_called_with(mock_gpio.BCM)
        mock_gpio.setup.assert_called_with(config.GPIO_PIN, mock_gpio.OUT)
        mock_gpio.output.assert_any_call(config.GPIO_PIN, mock_gpio.HIGH)
        mock_gpio.output.assert_any_call(config.GPIO_PIN, mock_gpio.LOW)
        mock_gpio.cleanup.assert_called_once()
