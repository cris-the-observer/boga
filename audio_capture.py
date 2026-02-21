import logging
import os

import numpy as np

import config

log = logging.getLogger(__name__)

TARGET_RATE = 16000


def _resample(data, from_rate, to_rate):
    """Resample 16-bit mono PCM using numpy linear interpolation."""
    if from_rate == to_rate:
        return data
    samples = np.frombuffer(data, dtype=np.int16).astype(np.float32)
    ratio = to_rate / from_rate
    new_len = int(len(samples) * ratio)
    indices = np.arange(new_len) / ratio
    indices = np.clip(indices, 0, len(samples) - 1)
    left = np.floor(indices).astype(int)
    right = np.clip(left + 1, 0, len(samples) - 1)
    frac = indices - left
    resampled = (samples[left] * (1 - frac) + samples[right] * frac).astype(np.int16)
    return resampled.tobytes()


def capture_audio():
    import pyaudio

    # Suppress ALSA/JACK warnings that PyAudio dumps to stderr during init
    devnull = os.open(os.devnull, os.O_WRONLY)
    old_stderr = os.dup(2)
    os.dup2(devnull, 2)
    os.close(devnull)
    try:
        p = pyaudio.PyAudio()
    finally:
        os.dup2(old_stderr, 2)
        os.close(old_stderr)
    stream = None

    device_count = p.get_device_count()
    log.info("PyAudio found %d audio device(s)", device_count)
    default_input = p.get_default_input_device_info()
    native_rate = int(default_input.get("defaultSampleRate"))
    log.info(
        "Default input device: %s (index=%d, rate=%d)",
        default_input.get("name"),
        default_input.get("index"),
        native_rate,
    )

    # Use 16kHz directly if supported, otherwise open at native rate and resample
    if native_rate == TARGET_RATE:
        actual_rate = TARGET_RATE
        chunk_size = config.CHUNK_SIZE
    else:
        actual_rate = native_rate
        chunk_size = int(config.CHUNK_SIZE * native_rate / TARGET_RATE)
        log.info("Device rate is %d Hz — will resample to %d Hz", native_rate, TARGET_RATE)

    stream = p.open(
        format=pyaudio.paInt16, channels=1, rate=actual_rate, input=True, frames_per_buffer=chunk_size
    )
    log.info("Opened audio stream at %d Hz (chunk_size=%d)", actual_rate, chunk_size)

    try:
        log.info("Recording — resampling: %s", "no" if actual_rate == TARGET_RATE else f"{actual_rate} → {TARGET_RATE}")
        while True:
            chunk = stream.read(chunk_size, exception_on_overflow=False)
            if actual_rate != TARGET_RATE:
                chunk = _resample(chunk, actual_rate, TARGET_RATE)
            yield chunk
    except OSError as e:
        log.error("Microphone error: %s", e)
        raise RuntimeError(f"Microphone error: {e}") from e
    finally:
        log.info("Closing audio stream")
        if stream is not None:
            stream.close()
        p.terminate()
