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


def check_startup():
    if not Path(config.VOSK_MODEL_PATH).exists():
        print(f"Error: Vosk model not found at {config.VOSK_MODEL_PATH}", file=sys.stderr)
        sys.exit(1)

    try:
        urllib.request.urlopen(config.OLLAMA_TAGS_URL, timeout=2)
    except URLError:
        print("Error: Ollama is not running or reachable", file=sys.stderr)
        sys.exit(1)


class Orchestrator:
    def __init__(self):
        self.buffer = TranscriptBuffer()
        self.transcriber = None
        self.classification_lock = threading.Lock()
        self.running = False

    def classification_cycle(self):
        if self.buffer.is_empty():
            return

        if not self.classification_lock.acquire(blocking=False):
            return

        try:
            text = self.buffer.get_window()
            llm_output = classify_transcript(config.OLLAMA_MODEL, text)
            score = score_severity(llm_output)

            if score["severity"] in {"HIGH", "CRITICAL"}:
                alerter.alert(score["severity"], score["triggered_groups"], score["observations"], text)
        finally:
            self.classification_lock.release()

    def run(self):
        check_startup()
        self.transcriber = Transcriber(config.VOSK_MODEL_PATH)
        self.running = True

        def classifier_thread():
            while self.running:
                time.sleep(config.CLASSIFY_INTERVAL)
                self.classification_cycle()
                self.buffer.trim()

        t = threading.Thread(target=classifier_thread, daemon=True)
        t.start()

        try:
            for chunk in capture_audio():
                self.transcriber.feed(chunk)
                text = self.transcriber.get_text()
                if text:
                    self.buffer.append(text)
        except KeyboardInterrupt:
            self.running = False


if __name__ == "__main__":
    Orchestrator().run()
