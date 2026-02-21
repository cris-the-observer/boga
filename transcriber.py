import json
import logging

log = logging.getLogger(__name__)


class Transcriber:
    def __init__(self, model_path):
        from vosk import KaldiRecognizer, Model

        log.info("Loading Vosk model from %s ...", model_path)
        self.model = Model(model_path)
        self.recognizer = KaldiRecognizer(self.model, 16000)
        self.results = []
        self.chunks_fed = 0
        log.info("Vosk recognizer ready (16kHz)")

    def feed(self, chunk):
        self.chunks_fed += 1
        if self.recognizer.AcceptWaveform(chunk):
            result = json.loads(self.recognizer.Result())
            text = result.get("text", "")
            if text:
                words = text.split()
                if len(words) == 1 and len(words[0]) <= 3:
                    log.debug("Vosk noise filtered (chunk #%d): %s", self.chunks_fed, text)
                    return
                log.debug("Vosk recognized (chunk #%d): %s", self.chunks_fed, text)
                self.results.append(text)
            else:
                log.debug("Vosk accepted waveform but text was empty (chunk #%d)", self.chunks_fed)

    def get_text(self):
        text = " ".join(self.results)
        self.results = []
        return text
