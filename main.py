import logging
import sys
import threading
import time
import urllib.request
from pathlib import Path
from urllib.error import URLError

import alerter
import config
from audio_capture import capture_audio
from classifier import classify_transcript
from severity_scorer import score_severity
from transcriber import Transcriber
from transcript_buffer import TranscriptBuffer

log = logging.getLogger(__name__)


def check_startup():
    log.info("Checking Vosk model at %s ...", config.VOSK_MODEL_PATH)
    if not Path(config.VOSK_MODEL_PATH).exists():
        log.critical("Vosk model not found at %s", config.VOSK_MODEL_PATH)
        sys.exit(1)
    log.info("Vosk model found")

    log.info("Checking Ollama at %s ...", config.OLLAMA_TAGS_URL)
    try:
        urllib.request.urlopen(config.OLLAMA_TAGS_URL, timeout=2)
    except URLError:
        log.critical("Ollama is not running or reachable at %s", config.OLLAMA_BASE_URL)
        sys.exit(1)
    log.info("Ollama is reachable")


class Orchestrator:
    def __init__(self):
        self.buffer = TranscriptBuffer()
        self.transcriber = None
        self.classification_lock = threading.Lock()
        self.running = False
        self.chunk_count = 0

    def classification_cycle(self):
        if self.buffer.is_empty():
            log.debug("Classification cycle skipped — buffer is empty")
            return

        if not self.classification_lock.acquire(blocking=False):
            log.debug("Classification cycle skipped — previous cycle still running")
            return

        try:
            text = self.buffer.get_window()
            log.info("=== Classification cycle start (buffer %d chars) ===", len(text))
            log.debug("Buffer contents: %.200s%s", text, "..." if len(text) > 200 else "")

            llm_output = classify_transcript(config.OLLAMA_MODEL, text)
            log.info(
                "LLM result: classification=%s, observations=%d, inference=%.2fs",
                llm_output.get("classification"),
                len(llm_output.get("observations", [])),
                llm_output.get("inference_time_seconds", 0),
            )
            for obs in llm_output.get("observations", []):
                log.debug("  observation: %s", obs)

            score = score_severity(llm_output)
            log.info(
                "Severity: %s | triggered groups: %s",
                score["severity"],
                ", ".join(score["triggered_groups"]) or "(none)",
            )

            if score["severity"] in {"HIGH", "CRITICAL"}:
                log.warning(">>> ALERT triggered: %s <<<", score["severity"])
                alerter.alert(score["severity"], score["triggered_groups"], score["observations"], text)
            log.info("=== Classification cycle end ===")
        finally:
            self.classification_lock.release()

    def run(self):
        check_startup()

        log.info("Loading Vosk model from %s ...", config.VOSK_MODEL_PATH)
        self.transcriber = Transcriber(config.VOSK_MODEL_PATH)
        log.info("Vosk model loaded")
        self.running = True

        def classifier_thread():
            log.info("Classifier thread started (interval=%.1fs)", config.CLASSIFY_INTERVAL)
            while self.running:
                time.sleep(config.CLASSIFY_INTERVAL)
                self.classification_cycle()
                self.buffer.trim()

        t = threading.Thread(target=classifier_thread, daemon=True)
        t.start()

        log.info("Starting audio capture loop — listening on microphone ...")
        try:
            for chunk in capture_audio():
                self.chunk_count += 1
                self.transcriber.feed(chunk)
                text = self.transcriber.get_text()
                if text:
                    log.info("[Transcribed] %s", text)
                    self.buffer.append(text)
                elif self.chunk_count % 40 == 0:
                    # Log every ~10s of silence (40 chunks * 0.25s each) so user knows it's alive
                    log.debug("... listening (chunks processed: %d, buffer: %d chars)", self.chunk_count, len(self.buffer.buffer))
        except KeyboardInterrupt:
            log.info("KeyboardInterrupt received — shutting down")
            self.running = False


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s [%(levelname)-8s] %(name)-20s | %(message)s",
        datefmt="%H:%M:%S",
    )
    log.info("Scam Detector starting up")
    log.info("Config: chunk_size=%d, buffer_max=%d, classify_interval=%.1fs, model=%s",
             config.CHUNK_SIZE, config.TRANSCRIPT_MAX_CHARS, config.CLASSIFY_INTERVAL, config.OLLAMA_MODEL)
    Orchestrator().run()
