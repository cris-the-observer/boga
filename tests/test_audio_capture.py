import sys
from unittest.mock import MagicMock

sys.modules["pyaudio"] = MagicMock()

from unittest.mock import MagicMock, patch

import config
from audio_capture import TARGET_RATE, capture_audio


def _setup_pyaudio(mock_pyaudio, native_rate=16000):
    """Configure mock PyAudio with a device reporting the given native rate."""
    mock_instance = mock_pyaudio.return_value
    mock_instance.get_device_count.return_value = 1
    mock_instance.get_default_input_device_info.return_value = {
        "name": "Test Mic",
        "index": 0,
        "defaultSampleRate": native_rate,
    }
    return mock_instance


@patch("pyaudio.PyAudio")
def test_stream_yields_chunks(mock_pyaudio):
    mock_instance = _setup_pyaudio(mock_pyaudio)
    mock_stream = MagicMock()
    mock_instance.open.return_value = mock_stream
    mock_stream.read.side_effect = [b"chunk1", b"chunk2", b"chunk3"]

    gen = capture_audio()
    assert next(gen) == b"chunk1"
    assert next(gen) == b"chunk2"
    assert next(gen) == b"chunk3"
    gen.close()


@patch("pyaudio.PyAudio")
def test_no_microphone_raises(mock_pyaudio):
    import pytest

    mock_instance = _setup_pyaudio(mock_pyaudio)
    mock_instance.open.side_effect = OSError("No mic")

    with pytest.raises(OSError):
        list(capture_audio())


@patch("pyaudio.PyAudio")
def test_chunk_size_matches_config(mock_pyaudio):
    import pyaudio

    mock_instance = _setup_pyaudio(mock_pyaudio, native_rate=16000)
    mock_stream = MagicMock()
    mock_instance.open.return_value = mock_stream
    mock_stream.read.side_effect = [b"chunk"]

    gen = capture_audio()
    next(gen)
    gen.close()

    mock_instance.open.assert_called_once_with(
        format=pyaudio.paInt16, channels=1, rate=TARGET_RATE, input=True, frames_per_buffer=config.CHUNK_SIZE
    )


@patch("pyaudio.PyAudio")
def test_chunk_size_scaled_for_native_rate(mock_pyaudio):
    import pyaudio

    mock_instance = _setup_pyaudio(mock_pyaudio, native_rate=44100)
    mock_stream = MagicMock()
    mock_instance.open.return_value = mock_stream
    mock_stream.read.side_effect = [b"\x00\x00" * 11025]

    gen = capture_audio()
    next(gen)
    gen.close()

    expected_chunk = int(config.CHUNK_SIZE * 44100 / TARGET_RATE)
    mock_instance.open.assert_called_once_with(
        format=pyaudio.paInt16, channels=1, rate=44100, input=True, frames_per_buffer=expected_chunk
    )


@patch("pyaudio.PyAudio")
def test_stream_closed_on_cleanup(mock_pyaudio):
    mock_instance = _setup_pyaudio(mock_pyaudio)
    mock_stream = MagicMock()
    mock_instance.open.return_value = mock_stream
    mock_stream.read.side_effect = [b"chunk"]

    gen = capture_audio()
    next(gen)
    gen.close()

    mock_stream.close.assert_called_once()
    mock_instance.terminate.assert_called_once()
