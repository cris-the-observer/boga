# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A real-time crypto ATM scam detector designed for Raspberry Pi. Captures microphone audio, transcribes speech locally with Vosk, classifies transcripts via a local Ollama LLM (qwen3:1.7b), scores severity using keyword-group heuristics, and triggers alerts (console, log file, GPIO pin 18) for HIGH/CRITICAL scams.

## Commands

- **Run tests:** `python -m pytest tests/`
- **Run a single test file:** `python -m pytest tests/test_severity_scorer.py`
- **Run a single test:** `python -m pytest tests/test_severity_scorer.py::test_function_name`
- **Run tests with coverage:** `python -m pytest tests/ --cov --cov-config=.coveragerc`
- **Lint:** `ruff check .`
- **Format:** `ruff format .`
- **Run the app:** `python main.py` (requires Vosk model at `models/vosk-model` and Ollama running on localhost:11434)
- **Run integration test suite against live Ollama:** `python test_runner.py`

## Architecture

The pipeline flows: **audio_capture → transcriber → transcript_buffer → classifier → severity_scorer → alerter**, orchestrated by `main.py:Orchestrator`.

- **`main.py`** — `Orchestrator` class runs two threads: main thread captures audio and feeds the transcriber/buffer; a daemon thread runs classification cycles every 5 seconds.
- **`audio_capture.py`** — Generator yielding raw PCM chunks from PyAudio (16kHz, mono, 4000-sample chunks).
- **`transcriber.py`** — Wraps Vosk's `KaldiRecognizer`; feeds audio chunks and accumulates recognized text.
- **`transcript_buffer.py`** — Sliding text buffer (max 5000 chars via `config.TRANSCRIPT_MAX_CHARS`); `trim()` drops oldest text at word boundaries.
- **`classifier.py`** — Sends transcript to Ollama `/api/generate` with a structured JSON schema enforcing `{classification, observations}`. Returns SUSPICIOUS/CLEAN/ERROR.
- **`severity_scorer.py`** — Pure-function scorer with 7 keyword groups (AUTHORITY, FEAR, PHONE_DIRECTION, WALLET_DICTATION, LARGE_AMOUNT, SECRECY, CONFUSION). Severity rules: CRITICAL if SECRECY triggered, PHONE_DIRECTION+FEAR, or ≥4 groups; HIGH if 3 groups, PHONE_DIRECTION+LARGE_AMOUNT, or AUTHORITY; MEDIUM if 2 groups or SUSPICIOUS with ≤1 group; else LOW.
- **`alerter.py`** — Prints to console, appends JSON to `alerts.log`, and pulses GPIO 18 for HIGH/CRITICAL (gracefully skips if RPi.GPIO unavailable).
- **`config.py`** — Constants: `CHUNK_SIZE=4000`, `TRANSCRIPT_MAX_CHARS=5000`.

## Testing

Tests use pytest with fixtures in `tests/conftest.py`. External dependencies (Vosk, PyAudio, Ollama, RPi.GPIO) are mocked — tests run without hardware or services. Coverage threshold is 85% (configured in `.coveragerc`).

## Linting

Uses ruff (config in `ruff.toml`): line length 120, rule sets E/F/W/I/N/UP/B/SIM/RUF, E501 ignored. `assert` allowed in tests (B011 ignored for `tests/*`).
