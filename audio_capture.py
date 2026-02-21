import config


def capture_audio():
    import pyaudio

    p = pyaudio.PyAudio()
    try:
        stream = p.open(format=pyaudio.paInt16, channels=1, rate=16000, input=True, frames_per_buffer=config.CHUNK_SIZE)
        while True:
            try:
                yield stream.read(config.CHUNK_SIZE, exception_on_overflow=False)
            except StopIteration:
                break
    except OSError as e:
        raise RuntimeError(f"Microphone error: {e}") from e
    finally:
        p.terminate()
