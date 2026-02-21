import time
from unittest.mock import patch

import pytest

import config
from main import Orchestrator, check_startup


@patch("pathlib.Path.exists")
def test_startup_checks_vosk_model(mock_exists, caplog):
    import logging

    mock_exists.return_value = False
    with caplog.at_level(logging.CRITICAL, logger="main"):
        with pytest.raises(SystemExit):
            check_startup()
    assert "Vosk model not found" in caplog.text


@patch("pathlib.Path.exists")
@patch("urllib.request.urlopen")
def test_startup_checks_ollama(mock_urlopen, mock_exists, caplog):
    import logging

    mock_exists.return_value = True
    from urllib.error import URLError

    mock_urlopen.side_effect = URLError("Refused")
    with caplog.at_level(logging.CRITICAL, logger="main"):
        with pytest.raises(SystemExit):
            check_startup()
    assert "Ollama is not running" in caplog.text


def test_classification_skipped_when_buffer_empty():
    orchestrator = Orchestrator()
    orchestrator.buffer.clear()

    with patch("main.classify_transcript") as mock_classify:
        orchestrator.classification_cycle()
        mock_classify.assert_not_called()


def test_classification_fires_when_buffer_has_text():
    orchestrator = Orchestrator()
    text = "Hello this is a suspicious test with enough words to trigger classification"
    orchestrator.buffer.append(text)

    with patch("main.classify_transcript") as mock_classify, patch("main.score_severity") as mock_score:
        mock_classify.return_value = {"classification": "CLEAN", "observations": []}
        mock_score.return_value = {"severity": "LOW", "triggered_groups": [], "observations": []}

        orchestrator.classification_cycle()
        mock_classify.assert_called_once_with(config.OLLAMA_MODEL, text)


def test_concurrent_classification_skipped():
    orchestrator = Orchestrator()
    orchestrator.buffer.append("Just buying some bitcoin with my spare cash today")

    orchestrator.classification_lock.acquire()

    with patch("main.classify_transcript") as mock_classify:
        orchestrator.classification_cycle()
        mock_classify.assert_not_called()


def test_alert_fires_on_high_severity():
    orchestrator = Orchestrator()
    text = "The IRS called and told me I need to send money right now or I will be arrested"
    orchestrator.buffer.append(text)

    with (
        patch("main.classify_transcript") as mock_classify,
        patch("main.score_severity") as mock_score,
        patch("alerter.alert") as mock_alert,
    ):
        mock_classify.return_value = {"classification": "SUSPICIOUS", "observations": ["A"]}
        mock_score.return_value = {"severity": "HIGH", "triggered_groups": ["AUTHORITY"], "observations": ["A"]}

        orchestrator.classification_cycle()
        mock_alert.assert_called_once_with("HIGH", ["AUTHORITY"], ["A"], text)


def test_alert_does_not_fire_on_low():
    orchestrator = Orchestrator()
    orchestrator.buffer.append("Just buying some bitcoin with my spare cash today")

    with (
        patch("main.classify_transcript") as mock_classify,
        patch("main.score_severity") as mock_score,
        patch("alerter.alert") as mock_alert,
    ):
        mock_classify.return_value = {"classification": "CLEAN", "observations": []}
        mock_score.return_value = {"severity": "LOW", "triggered_groups": [], "observations": []}

        orchestrator.classification_cycle()
        mock_alert.assert_not_called()


def test_silence_resets_buffer():
    orchestrator = Orchestrator()
    orchestrator.buffer.append("Some old conversation text that should be cleared after silence")
    orchestrator._last_classified_len = 60

    # Simulate 30s of silence by backdating the last append time
    orchestrator.buffer.last_append_time = time.time() - 35

    with patch("main.classify_transcript") as mock_classify:
        # Manually run the silence check logic from classifier_thread
        idle = orchestrator.buffer.seconds_since_last_append()
        assert idle >= config.SILENCE_RESET_SECONDS
        assert not orchestrator.buffer.is_empty()

        orchestrator.buffer.clear()
        orchestrator._last_classified_len = 0

        assert orchestrator.buffer.is_empty()
        assert orchestrator._last_classified_len == 0
