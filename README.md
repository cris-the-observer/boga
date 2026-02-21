# Scam Detector

Real-time crypto ATM scam detection on Raspberry Pi. Listens to conversations at a cryptocurrency ATM, transcribes speech locally, classifies intent with a local LLM, and triggers alerts when scam patterns are detected.

## How It Works

The system runs a continuous pipeline that processes live audio into actionable alerts:

```
audio_capture → transcriber → transcript_buffer → classifier → severity_scorer → alerter
```

1. **Audio capture** — Records microphone input as raw PCM (16 kHz, mono, 4000-sample chunks)
2. **Transcriber** — Feeds audio to Vosk's `KaldiRecognizer` for local speech-to-text
3. **Transcript buffer** — Accumulates recognized text in a sliding window (max 5000 chars), trimming at word boundaries
4. **Classifier** — Sends the buffered transcript to a local Ollama LLM every 5 seconds, which returns a structured JSON verdict (`SUSPICIOUS` or `CLEAN`) with observations
5. **Severity scorer** — Matches observations against keyword groups to determine threat level
6. **Alerter** — Logs to console and `alerts.log`; pulses GPIO pin 18 for HIGH/CRITICAL alerts

The main thread captures audio and feeds the transcriber. A daemon thread runs classification cycles at a configurable interval.

## Severity Scoring

Observations from the LLM are matched against 7 keyword groups:

| Group | Examples |
|---|---|
| **AUTHORITY** | warrant, arrest, IRS, FBI, government, fraud department |
| **FEAR** | scared, panic, lose everything, prison, urgent, deadline |
| **PHONE_DIRECTION** | told to, instructed, next step, walked through, reading back |
| **WALLET_DICTATION** | wallet, address, characters, QR, starts with |
| **LARGE_AMOUNT** | thousand, $5000, another machine, more cash, already sent |
| **SECRECY** | don't tell, keep quiet, secret, told not to |
| **CONFUSION** | don't know what bitcoin, never used, first time, gift card |

Severity levels are determined by these rules:

- **CRITICAL** — SECRECY triggered, PHONE_DIRECTION + FEAR, or 4+ groups triggered
- **HIGH** — 3 groups triggered, PHONE_DIRECTION + LARGE_AMOUNT, or AUTHORITY triggered
- **MEDIUM** — 2 groups triggered, or SUSPICIOUS classification with 0-1 groups
- **LOW** — Anything else

## Prerequisites

- Python 3
- [PyAudio](https://pypi.org/project/PyAudio/) (and its system dependency `portaudio`)
- [Vosk](https://alphacephei.com/vosk/) with a downloaded language model
- [Ollama](https://ollama.com/) running locally with the `qwen3:1.7b` model
- RPi.GPIO (optional — only needed for GPIO alerts on Raspberry Pi)

## Installation

```bash
git clone <repo-url>
cd scam-detector
pip install vosk pyaudio requests
```

Download a Vosk model and place it at `models/vosk-model`:

```bash
mkdir -p models
# Example: English small model
wget https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip
unzip vosk-model-small-en-us-0.15.zip
mv vosk-model-small-en-us-0.15 models/vosk-model
```

Pull the Ollama model:

```bash
ollama pull qwen3:1.7b
```

## Usage

Start the detector (requires a microphone, Vosk model, and Ollama running):

```bash
python main.py
```

The system will:
- Verify the Vosk model exists and Ollama is reachable
- Begin capturing audio and transcribing speech
- Run classification cycles every 5 seconds
- Print alerts to the console and append them to `alerts.log`

Stop with `Ctrl+C`.

### Integration Tests

Run the integration test suite against a live Ollama instance:

```bash
python test_runner.py
```

## Configuration

All constants live in `config.py`:

| Constant | Default | Description |
|---|---|---|
| `CHUNK_SIZE` | `4000` | Audio frames per capture chunk |
| `TRANSCRIPT_MAX_CHARS` | `5000` | Max characters in the sliding transcript buffer |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server address |
| `OLLAMA_MODEL` | `qwen3:1.7b` | LLM model for classification |
| `OLLAMA_TIMEOUT` | `30` | Seconds before an Ollama request times out |
| `CLASSIFY_INTERVAL` | `5.0` | Seconds between classification cycles |
| `VOSK_MODEL_PATH` | `models/vosk-model` | Path to the Vosk language model |
| `GPIO_PIN` | `18` | BCM pin number for alert output |

## Testing

Tests use pytest with all external dependencies mocked (no hardware or services required):

```bash
# Run all tests
python -m pytest tests/

# Run a single test file
python -m pytest tests/test_severity_scorer.py

# Run with coverage (85% threshold)
python -m pytest tests/ --cov --cov-config=.coveragerc
```

## Linting

Uses [ruff](https://docs.astral.sh/ruff/) for linting and formatting:

```bash
ruff check .
ruff format .
```

## Project Structure

```
scam-detector/
├── main.py                 # Orchestrator — threads, startup checks, main loop
├── audio_capture.py        # Generator yielding raw PCM chunks from PyAudio
├── transcriber.py          # Vosk KaldiRecognizer wrapper
├── transcript_buffer.py    # Sliding text buffer with word-boundary trimming
├── classifier.py           # Sends transcript to Ollama, parses structured JSON
├── severity_scorer.py      # Keyword-group heuristic scoring
├── alerter.py              # Console, log file, and GPIO alerts
├── config.py               # All configurable constants
├── test_runner.py          # Integration tests against live Ollama
├── tests/                  # Unit tests (pytest, fully mocked)
│   ├── conftest.py
│   ├── test_alerter.py
│   ├── test_audio_capture.py
│   ├── test_classifier.py
│   ├── test_integration.py
│   ├── test_main.py
│   ├── test_severity_scorer.py
│   ├── test_transcriber.py
│   └── test_transcript_buffer.py
├── ruff.toml               # Ruff linter configuration
└── CLAUDE.md               # Developer guidance for Claude Code
```

## Alerts

Alerts are written to `alerts.log` as newline-delimited JSON:

```json
{
  "timestamp": "2026-02-21T14:30:00.123456",
  "severity": "CRITICAL",
  "triggered_groups": ["AUTHORITY", "FEAR", "PHONE_DIRECTION", "SECRECY"],
  "observations": ["Mentions IRS demanding payment", "Expressing fear of arrest"],
  "transcript": "..."
}
```

For HIGH and CRITICAL alerts, GPIO pin 18 is pulsed high for 1 second (on Raspberry Pi with RPi.GPIO installed). On other platforms, the GPIO step is silently skipped.
