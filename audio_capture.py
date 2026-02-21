import logging

import config

log = logging.getLogger(__name__)


def capture_audio():
    import pyaudio

    p = pyaudio.PyAudio()
    stream = None

    device_count = p.get_device_count()
    log.info("PyAudio found %d audio device(s)", device_count)
    default_input = p.get_default_input_device_info()
    log.info("Default input device: %s (index=%d, rate=%.0f)",
             default_input.get("name"), default_input.get("index"), default_input.get("defaultSampleRate"))

    try:
        log.info("Opening audio stream: 16kHz, mono, chunk_size=%d", config.CHUNK_SIZE)
        stream = p.open(format=pyaudio.paInt16, channels=1, rate=16000, input=True, frames_per_buffer=config.CHUNK_SIZE)
        log.info("Audio stream opened — recording")
        while True:
            yield stream.read(config.CHUNK_SIZE, exception_on_overflow=False)
    except OSError as e:
        log.error("Microphone error: %s", e)
        raise RuntimeError(f"Microphone error: {e}") from e
    finally:
        log.info("Closing audio stream")
        if stream is not None:
            stream.close()
        p.terminate()
