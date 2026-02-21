import time

import config
from transcript_buffer import TranscriptBuffer


def test_append_and_get_window():
    buf = TranscriptBuffer()
    buf.append("Hello")
    buf.append("World")
    assert buf.get_window() == "Hello World"


def test_trim_drops_oldest():
    buf = TranscriptBuffer()
    # Assuming config.TRANSCRIPT_MAX_CHARS = 5000
    long_text = "A" * 6000
    buf.append(long_text)
    buf.trim()
    assert len(buf.get_window()) <= config.TRANSCRIPT_MAX_CHARS
    assert buf.get_window() == "A" * config.TRANSCRIPT_MAX_CHARS


def test_is_empty_on_init():
    buf = TranscriptBuffer()
    assert buf.is_empty()


def test_is_empty_after_append():
    buf = TranscriptBuffer()
    buf.append("Hey")
    assert not buf.is_empty()


def test_clear():
    buf = TranscriptBuffer()
    buf.append("Hey")
    buf.clear()
    assert buf.is_empty()


def test_get_window_preserves_order():
    buf = TranscriptBuffer()
    buf.append("A")
    buf.append("B")
    buf.append("C")
    assert buf.get_window() == "A B C"


def test_seconds_since_last_append(mocker):
    buf = TranscriptBuffer()

    # We will mock time.time instead of sleeping
    # It says "sleep 1 second" in instructions, we can just sleep
    buf.append("Hey")
    time.sleep(1.0)
    assert buf.seconds_since_last_append() >= 1.0


def test_trim_with_no_text():
    buf = TranscriptBuffer()
    buf.trim()
    assert buf.get_window() == ""


def test_unicode_handling():
    buf = TranscriptBuffer()
    buf.append("café 🌟")
    assert buf.get_window() == "café 🌟"
