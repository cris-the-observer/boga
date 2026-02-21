import json


class Transcriber:
    def __init__(self, model_path):
        from vosk import KaldiRecognizer, Model

        self.model = Model(model_path)
        self.recognizer = KaldiRecognizer(self.model, 16000)
        self.results = []

    def feed(self, chunk):
        if self.recognizer.AcceptWaveform(chunk):
            result = json.loads(self.recognizer.Result())
            text = result.get("text", "")
            if text:
                self.results.append(text)

    def get_text(self):
        text = " ".join(self.results)
        self.results = []
        return text
