from unittest.mock import patch

import pytest

import config
from main import Orchestrator, check_startup


@patch("pathlib.Path.exists")
def test_startup_checks_vosk_model(mock_exists, capsys):
    mock_exists.return_value = False
    with pytest.raises(SystemExit):
        check_startup()
    captured = capsys.readouterr()
    assert "Vosk model not found" in captured.err


@patch("pathlib.Path.exists")
@patch("urllib.request.urlopen")
def test_startup_checks_ollama(mock_urlopen, mock_exists, capsys):
    mock_exists.return_value = True
    from urllib.error import URLError

    mock_urlopen.side_effect = URLError("Refused")
    with pytest.raises(SystemExit):
        check_startup()
    captured = capsys.readouterr()
    assert "Ollama is not running" in captured.err


def test_classification_skipped_when_buffer_empty():
    orchestrator = Orchestrator()
    orchestrator.buffer.clear()

    with patch("main.classify_transcript") as mock_classify:
        orchestrator.classification_cycle()
        mock_classify.assert_not_called()


def test_classification_fires_when_buffer_has_text():
    orchestrator = Orchestrator()
    orchestrator.buffer.append("Hello suspicious test")

    with patch("main.classify_transcript") as mock_classify, patch("main.score_severity") as mock_score:
        mock_classify.return_value = {"classification": "CLEAN", "observations": []}
        mock_score.return_value = {"severity": "LOW", "triggered_groups": [], "observations": []}

        orchestrator.classification_cycle()
        mock_classify.assert_called_once_with(config.OLLAMA_MODEL, "Hello suspicious test")


def test_concurrent_classification_skipped():
    orchestrator = Orchestrator()
    orchestrator.buffer.append("text")

    orchestrator.classification_lock.acquire()

    with patch("main.classify_transcript") as mock_classify:
        orchestrator.classification_cycle()
        mock_classify.assert_not_called()


def test_alert_fires_on_high_severity():
    orchestrator = Orchestrator()
    orchestrator.buffer.append("text")

    with (
        patch("main.classify_transcript") as mock_classify,
        patch("main.score_severity") as mock_score,
        patch("alerter.alert") as mock_alert,
    ):
        mock_classify.return_value = {"classification": "SUSPICIOUS", "observations": ["A"]}
        mock_score.return_value = {"severity": "HIGH", "triggered_groups": ["AUTHORITY"], "observations": ["A"]}

        orchestrator.classification_cycle()
        mock_alert.assert_called_once_with("HIGH", ["AUTHORITY"], ["A"], "text")


def test_alert_does_not_fire_on_low():
    orchestrator = Orchestrator()
    orchestrator.buffer.append("text")

    with (
        patch("main.classify_transcript") as mock_classify,
        patch("main.score_severity") as mock_score,
        patch("alerter.alert") as mock_alert,
    ):
        mock_classify.return_value = {"classification": "CLEAN", "observations": []}
        mock_score.return_value = {"severity": "LOW", "triggered_groups": [], "observations": []}

        orchestrator.classification_cycle()
        mock_alert.assert_not_called()
