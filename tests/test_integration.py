from unittest.mock import patch

import classifier
import config
from severity_scorer import score_severity
from transcript_buffer import TranscriptBuffer


def test_transcript_to_classification_to_scoring(sample_transcript_scam, mock_ollama_response_suspicious):
    buf = TranscriptBuffer()
    buf.append(sample_transcript_scam)

    with patch("classifier.classify_transcript") as mock_classify:
        mock_classify.return_value = mock_ollama_response_suspicious

        text = buf.get_window()
        llm_out = classifier.classify_transcript("qwen3:1.7b", text)
        score = score_severity(llm_out)

        assert score["severity"] == "CRITICAL"
        assert len(score["triggered_groups"]) >= 4


def test_benign_transcript_full_pipeline(sample_transcript_benign, mock_ollama_response_clean):
    buf = TranscriptBuffer()
    buf.append(sample_transcript_benign)

    with patch("classifier.classify_transcript") as mock_classify:
        mock_classify.return_value = mock_ollama_response_clean

        text = buf.get_window()
        llm_out = classifier.classify_transcript("qwen3:1.7b", text)
        score = score_severity(llm_out)

        assert score["severity"] == "LOW"
        assert len(score["triggered_groups"]) == 0


def test_buffer_trim_preserves_enough_for_classification():
    buf = TranscriptBuffer()
    long_text = "Benign start. " * 500
    important_end = " The officer told me to send cash."
    buf.append(long_text + important_end)

    # Pre-trim check
    assert len(buf.get_window()) > config.TRANSCRIPT_MAX_CHARS

    buf.trim()
    text = buf.get_window()

    assert len(text) <= config.TRANSCRIPT_MAX_CHARS
    assert len(text) > (config.TRANSCRIPT_MAX_CHARS - 100)  # Should preserve almost the full allowed window
    assert important_end in text


def test_multiple_classification_cycles():
    buf = TranscriptBuffer()

    cycles_data = [
        ("I am buying some bitcoin.", {"classification": "CLEAN", "observations": []}, "LOW"),
        ("The police called me.", {"classification": "SUSPICIOUS", "observations": ["police"]}, "HIGH"),
        (
            "They told me not to tell anyone.",
            {"classification": "SUSPICIOUS", "observations": ["police", "told not to tell anyone"]},
            "CRITICAL",
        ),
    ]

    with patch("classifier.classify_transcript") as mock_classify:
        for text_chunk, mock_resp, expected_severity in cycles_data:
            buf.append(text_chunk)
            mock_classify.return_value = mock_resp

            text = buf.get_window()
            llm_out = classifier.classify_transcript("qwen3:1.7b", text)
            score = score_severity(llm_out)

            assert score["severity"] == expected_severity

        # At the end, the buffer should have all text
        assert "police" in buf.get_window()
        assert "anyone" in buf.get_window()
