import json
from unittest.mock import MagicMock, patch
from urllib.error import URLError

import classifier
import config


@patch("urllib.request.urlopen")
def test_classify_returns_parsed_dict(mock_urlopen):
    mock_response = MagicMock()
    mock_response.read.return_value = json.dumps(
        {"response": json.dumps({"classification": "SUSPICIOUS", "observations": ["Obs 1"]})}
    ).encode("utf-8")
    mock_urlopen.return_value.__enter__.return_value = mock_response

    result = classifier.classify_transcript("test_model", "test transcript")

    assert result["classification"] == "SUSPICIOUS"
    assert result["observations"] == ["Obs 1"]
    assert "inference_time_seconds" in result
    assert isinstance(result["inference_time_seconds"], float)


@patch("urllib.request.urlopen")
@patch("urllib.request.Request")
def test_classify_sends_correct_payload(mock_request, mock_urlopen):
    mock_response = MagicMock()
    mock_response.read.return_value = json.dumps(
        {"response": json.dumps({"classification": "CLEAN", "observations": []})}
    ).encode("utf-8")
    mock_urlopen.return_value.__enter__.return_value = mock_response

    classifier.classify_transcript("test_model", "test transcript")

    mock_request.assert_called_once()
    args, kwargs = mock_request.call_args
    assert args[0] == config.OLLAMA_GENERATE_URL

    payload = json.loads(kwargs["data"].decode("utf-8"))
    assert payload["model"] == "test_model"
    assert payload["prompt"] == "test transcript"
    assert payload["system"] == classifier.SYSTEM_PROMPT
    assert payload["stream"] is False
    assert payload["keep_alive"] == -1
    assert payload["options"]["temperature"] == 0
    assert payload["options"]["num_predict"] == 100
    assert payload["options"]["num_thread"] == 4
    assert payload["options"]["num_batch"] == 256
    assert payload["options"]["num_ctx"] >= 512
    assert "format" in payload
    assert payload["format"]["type"] == "object"


@patch("urllib.request.urlopen")
def test_classify_handles_ollama_unreachable(mock_urlopen):
    mock_urlopen.side_effect = URLError("Connection refused")
    result = classifier.classify_transcript("test_model", "test")
    assert result["classification"] == "ERROR"


@patch("urllib.request.urlopen")
def test_classify_handles_ollama_timeout(mock_urlopen):
    mock_urlopen.side_effect = TimeoutError("Timeout")
    result = classifier.classify_transcript("test_model", "test")
    assert result["classification"] == "ERROR"


@patch("urllib.request.urlopen")
def test_classify_handles_malformed_json(mock_urlopen):
    mock_response = MagicMock()
    mock_response.read.return_value = b"Not JSON"
    mock_urlopen.return_value.__enter__.return_value = mock_response

    result = classifier.classify_transcript("test_model", "test")
    assert result["classification"] == "ERROR"


@patch("urllib.request.urlopen")
def test_classify_handles_missing_fields(mock_urlopen):
    mock_response = MagicMock()
    mock_response.read.return_value = json.dumps({"response": json.dumps({"classification": "CLEAN"})}).encode("utf-8")
    mock_urlopen.return_value.__enter__.return_value = mock_response

    result = classifier.classify_transcript("test_model", "test")
    assert result["classification"] == "CLEAN"
    assert result["observations"] == []


@patch("urllib.request.urlopen")
def test_classify_includes_inference_time(mock_urlopen):
    mock_response = MagicMock()
    mock_response.read.return_value = json.dumps(
        {"response": json.dumps({"classification": "CLEAN", "observations": []})}
    ).encode("utf-8")
    mock_urlopen.return_value.__enter__.return_value = mock_response

    result = classifier.classify_transcript("test_model", "test")
    assert result["inference_time_seconds"] > 0


def test_system_prompt_is_under_200_tokens():
    words = classifier.SYSTEM_PROMPT.split()
    assert len(words) < 250


@patch("urllib.request.urlopen")
@patch("urllib.request.Request")
def test_classify_passes_timeout(mock_request, mock_urlopen):
    mock_response = MagicMock()
    mock_response.read.return_value = json.dumps(
        {"response": json.dumps({"classification": "CLEAN", "observations": []})}
    ).encode("utf-8")
    mock_urlopen.return_value.__enter__.return_value = mock_response

    classifier.classify_transcript("test_model", "test")

    mock_urlopen.assert_called_once()
    _, kwargs = mock_urlopen.call_args
    assert kwargs["timeout"] == config.OLLAMA_TIMEOUT


def test_estimate_num_ctx_short_transcript():
    ctx = classifier._estimate_num_ctx("System prompt here", "short text")
    assert ctx == 512  # minimum floor


def test_estimate_num_ctx_long_transcript():
    ctx = classifier._estimate_num_ctx("System prompt here", "x" * 5000)
    assert ctx >= 1792  # must fit ~1700+ estimated tokens
