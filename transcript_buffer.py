import time

import config


class TranscriptBuffer:
    def __init__(self):
        self.buffer = ""
        self.last_append_time = 0

    def append(self, text):
        if not text:
            return
        if self.buffer:
            self.buffer += " " + text
        else:
            self.buffer = text
        self.last_append_time = time.time()

    def get_window(self):
        return self.buffer

    def trim(self):
        if len(self.buffer) <= config.TRANSCRIPT_MAX_CHARS:
            return
        # Keep the latest chars, trying to start at a space
        start_idx = len(self.buffer) - config.TRANSCRIPT_MAX_CHARS
        space_idx = self.buffer.find(" ", start_idx)
        if space_idx != -1:
            self.buffer = self.buffer[space_idx + 1 :]
        else:
            self.buffer = self.buffer[start_idx:]

    def is_empty(self):
        return len(self.buffer) == 0

    def clear(self):
        self.buffer = ""

    def seconds_since_last_append(self):
        if self.last_append_time == 0:
            return 0
        return time.time() - self.last_append_time
