import os
import tempfile

import pytest


@pytest.fixture
def sample_transcript_scam():
    return "I don't even know what Bitcoin is honestly. Okay, okay, I'm at the machine. It says enter amount. How much do I put? Five thousand? I don't have that much on me. Okay let me check. I have about thirty-two hundred in cash. The officer said I have to pay today or there's a warrant? Okay. Okay I'm putting in thirty-two hundred. It's asking for a wallet address now. Okay go ahead. 3... F... x... capital B..."


@pytest.fixture
def sample_transcript_benign():
    return "Yeah I'm just buying some Bitcoin. I've done this before, putting in about two hundred bucks. My Coinbase wallet, I have the QR code right here. Cool, almost done."


@pytest.fixture
def sample_transcript_subtle():
    return "Okay I did the three hundred at the other place already. He said I need to do five hundred more here. No I don't really get how this works but he said just follow the steps. Don't worry about what it is just put the cash in."


@pytest.fixture
def mock_ollama_response_suspicious():
    return {
        "classification": "SUSPICIOUS",
        "observations": [
            "The officer said I have to pay today or there's a warrant",
            "How much do I put? Five thousand?",
            "It's asking for a wallet address now. Okay go ahead. 3... F... x... capital B...",
            "What to do next",
        ],
        "inference_time_seconds": 1.2,
    }


@pytest.fixture
def mock_ollama_response_clean():
    return {"classification": "CLEAN", "observations": [], "inference_time_seconds": 0.8}


@pytest.fixture
def mock_ollama_response_error():
    return {"classification": "ERROR", "observations": [], "inference_time_seconds": 0.5}


@pytest.fixture
def mock_audio_chunk():
    return os.urandom(4000)


@pytest.fixture
def tmp_log_file():
    with tempfile.NamedTemporaryFile(delete=False, suffix=".log") as tmp:
        path = tmp.name
    yield path
    if os.path.exists(path):
        os.remove(path)
