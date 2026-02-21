import sys
from unittest.mock import MagicMock

sys.modules["vosk"] = MagicMock()

from unittest.mock import patch

from transcriber import Transcriber


@patch("vosk.Model")
@patch("vosk.KaldiRecognizer")
def test_feed_calls_recognizer(mock_rec, mock_model):
    instance = mock_rec.return_value
    instance.AcceptWaveform.return_value = False

    t = Transcriber("fake_path")
    t.feed(b"chunk")

    instance.AcceptWaveform.assert_called_with(b"chunk")


@patch("vosk.Model")
@patch("vosk.KaldiRecognizer")
def test_get_text_returns_finalized(mock_rec, mock_model):
    import json

    instance = mock_rec.return_value
    instance.AcceptWaveform.return_value = True
    instance.Result.return_value = json.dumps({"text": "hello world"})

    t = Transcriber("fake_path")
    t.feed(b"chunk")

    assert t.get_text() == "hello world"


@patch("vosk.Model")
@patch("vosk.KaldiRecognizer")
def test_get_text_clears_buffer(mock_rec, mock_model):
    import json

    instance = mock_rec.return_value
    instance.AcceptWaveform.return_value = True
    instance.Result.return_value = json.dumps({"text": "hello"})

    t = Transcriber("fake_path")
    t.feed(b"chunk")

    assert t.get_text() == "hello"
    assert t.get_text() == ""


@patch("vosk.Model")
@patch("vosk.KaldiRecognizer")
def test_partial_results_ignored(mock_rec, mock_model):
    instance = mock_rec.return_value
    instance.AcceptWaveform.return_value = False

    t = Transcriber("fake_path")
    t.feed(b"chunk")

    assert t.get_text() == ""


@patch("vosk.Model")
@patch("vosk.KaldiRecognizer")
def test_multiple_utterances_joined(mock_rec, mock_model):
    import json

    instance = mock_rec.return_value
    instance.AcceptWaveform.return_value = True
    instance.Result.side_effect = [json.dumps({"text": "hello"}), json.dumps({"text": "world"})]

    t = Transcriber("fake_path")
    t.feed(b"chunk1")
    t.feed(b"chunk2")

    assert t.get_text() == "hello world"


@patch("vosk.Model")
@patch("vosk.KaldiRecognizer")
def test_empty_finalized_text_skipped(mock_rec, mock_model):
    import json

    instance = mock_rec.return_value
    instance.AcceptWaveform.return_value = True
    instance.Result.side_effect = [json.dumps({"text": ""}), json.dumps({"text": "hello"})]

    t = Transcriber("fake_path")
    t.feed(b"chunk1")
    t.feed(b"chunk2")

    assert t.get_text() == "hello"
