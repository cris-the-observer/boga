import config


def capture_audio():
    import pyaudio

    p = pyaudio.PyAudio()
    stream = None
    try:
        stream = p.open(format=pyaudio.paInt16, channels=1, rate=16000, input=True, frames_per_buffer=config.CHUNK_SIZE)
        while True:
            yield stream.read(config.CHUNK_SIZE, exception_on_overflow=False)
    except OSError as e:
        raise RuntimeError(f"Microphone error: {e}") from e
    finally:
        if stream is not None:
            stream.close()
        p.terminate()
